#!/usr/bin/env python3
"""Point every marketplace entry at its plugin's latest release.

Each plugin lives in its own repo and cuts its own releases. This marketplace
pins each one to a tag, which is the property that makes an install
reproducible, and is also the property that goes stale in silence: nothing in
this repo changes when a plugin ships, so the index keeps serving an old tag
until someone notices.

What this reads, per entry, is derived from the entry itself. There is no table
of plugins here to keep in step with the index:

  source: github     -> .claude-plugin/plugin.json at the repo root
  source: git-subdir -> <path>/.claude-plugin/plugin.json
  source: url        -> .claude-plugin/plugin.json at the repo root

What it writes is the pinned tag and the version beside it, in both indexes and
in the README's version columns.

What it deliberately does NOT write is any description. The text in the indexes
and in the README table is shortened by hand from the plugin's own manifest, so
overwriting it with the manifest text would undo that editing every time a
plugin ships. Description drift is reported instead, for a person to apply.

  python3 scripts/sync_marketplace.py             # write the updates
  python3 scripts/sync_marketplace.py --dry-run   # print, change nothing
  python3 scripts/sync_marketplace.py --check     # exit 1 if anything is stale

Set GITHUB_TOKEN to raise the API rate limit. Stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent.parent
CLAUDE_INDEX = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_INDEX = ROOT / ".agents" / "plugins" / "marketplace.json"
README = ROOT / "README.md"
MANIFEST = ".claude-plugin/plugin.json"
# A leading "v" is conventional here but not universal, so it is optional.
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "synaptic-labs-marketplace-sync",
    })
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def repo_of(source: dict) -> str | None:
    """Owner/name for an entry, from either the repo or the url form."""
    if source.get("repo"):
        return source["repo"].strip("/")
    url = source.get("url", "")
    match = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git)?/*$", url)
    return match.group(1) if match else None


def latest_tag(repo: str) -> str | None:
    """The newest release tag, falling back to the newest semver tag.

    A repo can carry tags with no release attached, and can carry a release
    that is not the highest tag. The release is what a user installs, so it
    wins; the tag list is only a fallback for a repo that tags without
    releasing.
    """
    try:
        return json.loads(fetch(f"{API}/repos/{repo}/releases/latest"))["tag_name"]
    except (urllib.error.HTTPError, KeyError):
        pass
    try:
        tags = json.loads(fetch(f"{API}/repos/{repo}/tags?per_page=100"))
    except urllib.error.HTTPError:
        return None
    versioned = [t["name"] for t in tags if SEMVER.match(t["name"])]
    if not versioned:
        return None
    return max(versioned, key=lambda n: tuple(int(p) for p in SEMVER.match(n).groups()))


def manifest_at(repo: str, tag: str, subdir: str | None) -> dict | None:
    """The plugin's own manifest, read at the tag being pinned."""
    prefix = (subdir or "").strip("/.")
    path = f"{prefix}/{MANIFEST}" if prefix else MANIFEST
    try:
        blob = json.loads(fetch(f"{API}/repos/{repo}/contents/{path}?ref={tag}"))
        return json.loads(base64.b64decode(blob["content"]))
    except (urllib.error.HTTPError, KeyError, ValueError):
        return None


def load(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def resolve(indexes: list[tuple[str, dict]]) -> dict[str, dict]:
    """One upstream lookup per plugin, shared across the indexes it appears in."""
    resolved: dict[str, dict] = {}
    for _, index in indexes:
        for entry in index.get("plugins", []):
            name = entry.get("name")
            if not name or name in resolved:
                continue
            source = entry.get("source", {})
            repo = repo_of(source)
            if not repo:
                resolved[name] = {"error": "no GitHub repo in source"}
                continue
            tag = latest_tag(repo)
            if not tag:
                resolved[name] = {"error": f"no release or semver tag on {repo}"}
                continue
            manifest = manifest_at(repo, tag, source.get("path"))
            resolved[name] = {
                "repo": repo, "tag": tag,
                "version": (manifest or {}).get("version") or tag.lstrip("v"),
                "description": (manifest or {}).get("description"),
                "manifest_found": manifest is not None,
            }
    return resolved


def apply_to_index(label: str, index: dict, resolved: dict) -> list[str]:
    """Update ref and version in place. Only keys already present are written,
    so an index that does not carry versions does not grow them.

    Every line is labeled with the index it came from. The same pin usually
    moves in both, and two identical lines read as one change reported twice.
    """
    changes: list[str] = []
    for entry in index.get("plugins", []):
        found = resolved.get(entry.get("name", ""), {})
        if found.get("error"):
            continue
        source = entry.setdefault("source", {})
        if source.get("ref") and source["ref"] != found["tag"]:
            changes.append(
                f"{entry['name']}: {label} ref {source['ref']} -> {found['tag']}")
            source["ref"] = found["tag"]
        if "version" in entry and entry["version"] != found["version"]:
            changes.append(f"{entry['name']}: {label} version "
                           f"{entry['version']} -> {found['version']}")
            entry["version"] = found["version"]
    return changes


def apply_to_readme(text: str, claude: dict | None, codex: dict | None,
                    resolved: dict) -> tuple[str, list[str]]:
    """Rewrite the tag cells in the plugin table.

    The Description column is left alone; it is an editorial summary, not the
    manifest text. A plugin absent from an index keeps whatever placeholder the
    row already has, because absence is a real state here and not a gap to fill.
    """
    changes: list[str] = []
    listed = {
        "claude": {e["name"] for e in (claude or {}).get("plugins", [])},
        "codex": {e["name"] for e in (codex or {}).get("plugins", [])},
    }

    def rewrite(match: re.Match) -> str:
        name = match.group("name")
        found = resolved.get(name, {})
        if found.get("error"):
            return match.group(0)
        cells = [match.group("claude"), match.group("codex")]
        for position, index_name in enumerate(("claude", "codex")):
            if name not in listed[index_name]:
                continue  # not carried there; leave the placeholder as written
            want = f"`{found['tag']}`"
            if cells[position].strip() != want:
                changes.append(f"README {name} ({index_name}): "
                               f"{cells[position].strip()} -> {want}")
                cells[position] = f" {want} "
        return (f"|{match.group('pad1')}`{name}`{match.group('pad2')}|"
                f"{cells[0]}|{cells[1]}|{match.group('rest')}")

    pattern = re.compile(
        r"^\|(?P<pad1> *)`(?P<name>[a-z0-9-]+)`(?P<pad2> *)\|"
        r"(?P<claude>[^|]*)\|(?P<codex>[^|]*)\|(?P<rest>.*)$",
        re.MULTILINE)
    return pattern.sub(rewrite, text), changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sync_marketplace.py",
        description="Point every marketplace entry at its plugin's latest release.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would change and write nothing")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if anything is stale; write nothing")
    args = parser.parse_args(argv)

    claude, codex = load(CLAUDE_INDEX), load(CODEX_INDEX)
    if claude is None and codex is None:
        print("no marketplace index found", file=sys.stderr)
        return 2

    present = [(name, index) for name, index in
               (("claude", claude), ("codex", codex)) if index]
    resolved = resolve(present)

    changes: list[str] = []
    for label, index in present:
        changes += apply_to_index(label, index, resolved)

    readme = README.read_text() if README.is_file() else None
    if readme is not None:
        readme, readme_changes = apply_to_readme(readme, claude, codex, resolved)
        changes += readme_changes

    problems = [f"{name}: {found['error']}"
                for name, found in sorted(resolved.items()) if found.get("error")]
    # Reported, never applied. These summaries are shortened by hand and
    # overwriting them with the manifest text would undo that on every release.
    #
    # Only raised for a plugin whose pin actually moved. Every summary here
    # differs from its manifest by design, so reporting that unconditionally
    # would print four notes on every run and teach the reader to skip them.
    # Tied to a release, the note means something: this plugin just shipped, so
    # its description is worth a look.
    moved = {name for name in resolved
             if any(change.startswith((f"{name}:", f"README {name} "))
                    for change in changes)}
    drift = [f"{name}: shipped {found['tag']}; its manifest description differs "
             "from the summary here"
             for name, found in sorted(resolved.items())
             if name in moved and found.get("description") and any(
                 e.get("description") and e["description"] != found["description"]
                 for _, index in present for e in index.get("plugins", [])
                 if e.get("name") == name)]
    missing = [f"{name}: no manifest at {found['tag']}, version taken from the tag"
               for name, found in sorted(resolved.items())
               if not found.get("error") and not found.get("manifest_found")]

    for name, found in sorted(resolved.items()):
        if not found.get("error"):
            print(f"  {name:<22}{found['repo']:<44}{found['tag']}")
    print()
    for note in missing + problems:
        print(f"  WARN  {note}")
    for note in drift:
        print(f"  NOTE  {note} (not changed; edit by hand if it should be)")
    if missing or problems or drift:
        print()

    if not changes:
        print("up to date: every entry already points at the latest release")
        return 1 if problems else 0

    for change in changes:
        print(f"  {change}")
    print()

    if args.check:
        print(f"STALE: {len(changes)} update(s) pending", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"dry run: {len(changes)} update(s) not written")
        return 0

    for path, index in (("claude", claude), ("codex", codex)):
        target = CLAUDE_INDEX if path == "claude" else CODEX_INDEX
        if index:
            save(target, index)
    if readme is not None:
        README.write_text(readme)
    print(f"wrote {len(changes)} update(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
