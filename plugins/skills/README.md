# skills

Catch-all plugin for assorted Claude Code skills maintained in this repo. Add a new skill by dropping a `skills/<name>/SKILL.md` (plus any `references/`, `scripts/`, `assets/`) into this plugin — no marketplace re-registration needed for the skill itself, only the plugin.

## Skills included

- **jj-vcs** — Teaches the "jj way" of version control: working copy as commit, move changes between commits with `squash --into`, first-class conflicts, undo via operation log, bookmarks instead of branches. Loads on any repo with `.jj/` or when the user mentions jj / jujutsu.

## Install

```
/plugin install skills@werdnum-plugins
```

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
2. Optional: `references/` for detail loaded on demand, `scripts/` for executables, `assets/` for output templates.
3. Bump this plugin's version in `.claude-plugin/plugin.json` and in the top-level `.claude-plugin/marketplace.json`.

See `plugins/development-agents/skills/skill-creator/SKILL.md` in this repo for the authoring guide.

