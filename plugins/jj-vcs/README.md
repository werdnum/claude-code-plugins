# jj-vcs

A Claude Code skill that teaches the "jj way" of version control. Activates in any repo with a `.jj/` directory or whenever the user mentions jj / jujutsu.

## What it provides

A single skill, `jj-vcs`, with:

- **`SKILL.md`** — core tenets (working copy is a commit, describe-first, change IDs, moving changes between commits, first-class conflicts, universal undo, bookmarks).
- **`references/workflows.md`** — stacked changes, interactive squash, split, absorb, rebase, push, review-comment handling.
- **`references/git-equivalents.md`** — cheat sheet mapping git commands to jj.
- **`references/revsets.md`** — revset syntax for `-r` flags.
- **`references/recovery.md`** — operation-log recipes for undoing mistakes.

SKILL.md stays lean; detail lives in `references/` and is loaded on demand. For authoritative CLI details, consult `jj help <command>`.

## Install

```
/plugin install jj-vcs@werdnum-plugins
```
