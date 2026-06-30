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
| `skill-crafter` | `v0.1.3` | — | Build, improve, modularize, and validate skills the right way. |
| `agentic-guardrails` | `v0.2.2` | `v0.2.2` | Enterprise guardrails: CRUA, agent workspace, sync-aware safety, policy-driven blocking. |
| `professor-synapse` | `v3.3.0` | — | A router that summons expert agents on demand, with agent-tagged memory and a summon-gate. |

Repos: [skill-crafter](https://github.com/ProfSynapse/skill-crafter) ·
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

To ship a new release: tag a release in the plugin's repo, then bump the entry's
`ref` (and `version`) in the relevant index here and commit to `main`.
