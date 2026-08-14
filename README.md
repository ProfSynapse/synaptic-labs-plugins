# Synaptic Labs — plugin marketplace

A marketplace of Synaptic Labs plugins for both
[Claude Code](https://code.claude.com) and [OpenAI Codex](https://developers.openai.com/codex).
One repo address serves both: Claude reads `.claude-plugin/marketplace.json`,
Codex reads `.agents/plugins/marketplace.json`.

## Use it

**Claude Code:**
```
/plugin marketplace add ProfSynapse/synaptic-labs-plugins
/plugin install <plugin-name>@synaptic-labs
```

**Codex:**
```
codex plugin marketplace add ProfSynapse/synaptic-labs-plugins
# then open the /plugins TUI in a session to install + enable
```

Each index lives on `main`, so the bare address always resolves. Every plugin
entry pins its `source` to a **release tag** of that plugin's own repo, so what
you install comes from a tagged release — never from whatever happens to be on a
plugin's `main`. Bump the pinned tag here to ship an update (`/plugin update` in
Claude; `codex plugin marketplace upgrade` in Codex).

## Plugins

| Plugin | Claude | Codex | Description |
| --- | --- | --- | --- |
| `skill-crafter` | `v0.2.0` | `v0.2.0` | Build, improve, modularize, validate, and package skills the right way. |
| `deslop` | `v1.1.0` | `v1.1.0` | Remove the signs of AI-generated writing: catalogued tells, per-pattern fixes, delivery gates. |
| `agentic-guardrails` | `v0.4.3` | `v0.4.3` | Enterprise guardrails: CRUA, bounded automatic recovery retention, agent workspace, sync-aware safety, policy-driven blocking. |
| `professor-synapse` | `v3.3.0` | — | A router that summons expert agents on demand, with agent-tagged memory and a summon-gate. |

Repos: [skill-crafter](https://github.com/ProfSynapse/skill-crafter) ·
[DeSlop](https://github.com/ProfSynapse/DeSlop) ·
[agentic-guardrails-plugin](https://github.com/ProfSynapse/agentic-guardrails-plugin) (`plugin/`) ·
[Professor-Synapse](https://github.com/ProfSynapse/Professor-Synapse) (`professor-synapse-plugin/`)

## Add a plugin to this marketplace

Each plugin lives in its **own** repo with its own manifest and releases, and is
listed here pinned to a release tag.

**Claude** — add to `.claude-plugin/marketplace.json`:
```json
{
  "name": "your-plugin",
  "description": "What it does.",
  "version": "1.0.0",
  "source": { "source": "github", "repo": "ProfSynapse/your-plugin", "ref": "v1.0.0" }
}
```

**Codex** — add to `.agents/plugins/marketplace.json` (use `git-subdir` when the
plugin lives in a subdirectory of its repo, `url` when it's at the repo root):
```json
{
  "name": "your-plugin",
  "source": { "source": "git-subdir", "url": "https://github.com/ProfSynapse/your-plugin.git", "path": "./plugin", "ref": "v1.0.0" },
  "interface": { "displayName": "Your Plugin" },
  "category": "Productivity",
  "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" }
}
```

To ship a new release: tag a release in the plugin's repo. The pins here are
updated for you, as below.

## Keeping the pins current

A plugin ships from its own repo, and nothing in this repo changes when it does.
That is the failure mode this marketplace had: `agentic-guardrails` sat pinned at
`v0.2.2` while its repo was four releases ahead at `v0.3.6`, and installs kept
resolving the old tag because the index was the only thing that had not moved.

`.github/workflows/sync-marketplace.yml` runs daily and opens a pull request when
any pin is behind its plugin's latest release. It touches versions and tags in
both indexes and in the table above. It never rewrites descriptions, which are
shortened by hand here and would otherwise be clobbered on every release; when a
plugin ships something worth re-summarizing, the run says so and leaves the edit
to you.

Run it yourself any time:

```bash
python3 scripts/sync_marketplace.py --dry-run   # print what is behind
python3 scripts/sync_marketplace.py             # write the updates
python3 scripts/sync_marketplace.py --check     # exit 1 if anything is stale
```

Nothing needs configuring per plugin. Where to look is derived from each entry's
own `source`, so adding a plugin to an index is enough to put it under sync.

**For same-day propagation**, have the plugin repo poke this one when it
publishes a release instead of waiting for the next daily run. Add this to the
plugin repo, with `MARKETPLACE_DISPATCH_TOKEN` a PAT holding `contents: write`
on this repo, since the built-in `GITHUB_TOKEN` cannot dispatch across repos:

```yaml
name: notify marketplace
on:
  release:
    types: [published]
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - env:
          GH_TOKEN: ${{ secrets.MARKETPLACE_DISPATCH_TOKEN }}
        run: |
          gh api repos/ProfSynapse/synaptic-labs-plugins/dispatches \
            -f event_type=plugin-released
```

This is optional. Without it a release is picked up within a day; the schedule is
the floor, and the dispatch only makes it immediate.
