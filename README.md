# Synaptic Labs — Claude Code plugin marketplace

A marketplace of [Claude Code](https://code.claude.com) plugins by Synaptic Labs.

## Use it

```
/plugin marketplace add ProfSynapse/synaptic-labs-plugins
/plugin install <plugin-name>@synaptic-labs
```

The marketplace index (`.claude-plugin/marketplace.json`) lives on `main`, so the
bare address above always resolves. Each plugin entry pins its `source` to a
**release tag** of that plugin's own repo, so what you install comes from a tagged
release — never from whatever happens to be on a plugin's `main`. Run
`/plugin update` to pick up new releases as the pointers are bumped.

## Plugins

| Plugin | Description | Pinned | Repo |
| --- | --- | --- | --- |
| `skill-crafter` | Build, improve, modularize, and validate Claude Code skills the right way. | `v0.1.2` | [ProfSynapse/skill-crafter](https://github.com/ProfSynapse/skill-crafter) |

## Add a plugin to this marketplace

Each plugin lives in its **own** repo with its own `.claude-plugin/plugin.json`
and its own releases. To list one here, add an entry to the `plugins` array in
`.claude-plugin/marketplace.json`, pinned to a release tag:

```json
{
  "name": "your-plugin",
  "description": "What it does.",
  "version": "1.0.0",
  "source": { "source": "github", "repo": "ProfSynapse/your-plugin", "ref": "v1.0.0" }
}
```

To ship a new release of a listed plugin: tag a release in that plugin's repo,
then bump the entry's `ref` (and `version`) here and commit to `main`.
