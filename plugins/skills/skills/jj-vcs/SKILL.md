---
name: jj-vcs
description: This skill should be used when working in a Jujutsu (jj) repository or when the user asks about jj commands, workflows, or idioms. It encodes the "jj way" of doing things - working copy as commit, moving changes between commits with squash, splitting with split, first-class conflicts, and undo via the operation log. Use this skill instead of git habits whenever a `.jj/` directory is present, when the user says "jj" or "jujutsu", or when translating a git workflow into jj.
---

# Jujutsu (jj) VCS

Jujutsu is a Git-compatible VCS with a different model: **the working copy is a commit, every command auto-snapshots, history is freely rewritable, and conflicts are first-class**. Most git habits (staging, amend, stash, rebase --continue) translate to simpler jj primitives. Follow this skill's idioms rather than porting git workflows verbatim.

Detailed references in `references/` should be loaded when a workflow requires them. `jj help <command>` and `jj <command> --help` remain the authoritative reference for flags.

## Core Tenets

Read these before running any jj command. They are the mental model that makes every other command make sense.

### 1. The working copy is a commit

There is no staging area and no "dirty working tree". The files on disk ARE a commit, referenced as `@`. Its parent is `@-`. Editing a file is equivalent to amending `@` — jj snapshots the working copy automatically before (almost) every command.

Practical consequences:
- Never `git add`. Just edit files.
- `jj status` / `jj diff` show what's in `@` vs `@-`.
- To "stash", just `jj new @-` — your current `@` stays as a commit, and you get a fresh empty commit to work in.
- To discard unstaged work, `jj restore` pulls `@-`'s content back into `@`.

### 2. Describe first, then edit

The idiomatic flow is **describe a change, then make it** — opposite of git's "edit then write a commit message". This keeps intent clear in `jj log` even while work is in progress.

```
jj describe -m "add foo feature"   # label current @
# ... edit files, snapshot is automatic ...
jj new -m "next thing"             # finish current, start new @
# or equivalently:
jj commit -m "add foo feature"     # = describe + new, labels current @ and starts fresh
```

Do NOT describe-after-the-fact unless recovering from a mistake; the habit of describing upfront is what makes stacked work legible.

### 3. Change IDs are stable; commit IDs are not

Every commit has two IDs:
- **Change ID** (letters, e.g. `olurzuwu`): the identity of a *change*, stable across rewrites. Use this when referring to commits in commands.
- **Commit ID** (hex, e.g. `a3373947`): the specific content hash, changes on every rewrite.

Rewriting a commit (squash, rebase, describe, edit-and-snapshot) produces a new commit ID but the same change ID. All descendants auto-rebase. Refer to commits by change ID prefix.

### 4. Move changes between commits; don't re-checkout to fix them

The killer feature. You rarely need to "check out" an older commit to modify it. Instead, make the fix in `@` (or anywhere), then move it into the target change:

```
jj squash --into <change>              # move @'s diff into <change>
jj squash -f <src> -t <dst>            # move content from src to dst
jj squash -i --into <change>           # interactively pick hunks to move
jj squash --from <src> <filepath>      # move only a path
```

Defaults: `jj squash` with no flags moves `@` → `@-` (the git-amend equivalent). `--use-destination-message` (`-u`) keeps the destination's description when squashing.

### 5. Conflicts are first-class

Conflicts don't block operations. A rebase / abandon / squash that creates a conflict succeeds; the conflicted commit is just marked `(conflict)` in `jj log` and descendants continue to rebase on top. You resolve them when convenient.

To resolve:
- Edit the conflicted files directly (markers are in the working copy once you're on or past the conflict), OR run `jj resolve` for an interactive merge tool.
- Snapshotting is automatic — there is no `--continue` step.
- If you fixed the conflict in a descendant, `jj squash` moves the resolution into the conflicted commit.

### 6. Undo is cheap and universal

Every operation (snapshots, rebases, pushes, abandons) is recorded in the **operation log**. Reach for undo *liberally* rather than trying to reason your way out.

```
jj undo                    # reverse last op
jj op log                  # list operations
jj op restore <op-id>      # jump repo state back to any op
jj op revert <op-id>       # revert a specific non-recent op
jj log --at-op <op-id>     # inspect past state without changing current
```

### 7. Rewrite history freely — except `immutable_heads()`

Unlike git, rewriting published commits is normal and safe locally. jj auto-rebases descendants. The only commits protected by default are ancestors of `trunk()` and tags (the `immutable_heads()` revset). Override with `--ignore-immutable` only if deliberate.

### 8. Bookmarks, not branches

jj has no "current branch". Bookmarks are named pointers that don't auto-advance with new commits. To push work:

```
jj bookmark create my-feature -r @-     # or @ — point at a commit
jj bookmark move my-feature --to @-     # update pointer
jj git push --bookmark my-feature       # push it
jj git push --change @                  # auto-create bookmark named after change ID
```

Bookmarks need explicit maintenance. A fresh commit doesn't advance any bookmark.

## When to Use This Skill

Invoke this skill when ANY of:
- A `.jj/` directory exists in the repo (run `ls .jj` or `jj root` to confirm).
- The user says "jj", "jujutsu", or references jj commands.
- The user asks to reorganize / split / reorder / absorb commits (jj does this better than git).
- The user wants to undo something (jj op log beats git reflog).

If the repo is colocated (both `.jj/` and `.git/` present), prefer `jj` commands over `git` ones to avoid creating divergent refs.

## Everyday Playbook

### Start new work
```
jj new trunk() -m "add new widget"     # new @ off trunk, with description
# edit files...
jj commit -m "add new widget"          # labels @ and starts fresh @
# or keep going and let auto-snapshot amend @ until you're done
```

### Amend the current change
Just edit — snapshot is automatic. To change the description: `jj describe`.

### Amend an earlier change (no checkout)
Edit whatever files need changing in `@`, then:
```
jj squash --into <change-id>
```
Or the legacy shortcuts: `jj squash -B @` (before `@`), `jj squash -A @-` (after `@-`), but `--into` is usually clearer.

### Split a change
```
jj split                      # interactive: pick which hunks go to new commit
jj split <paths>              # by path
jj split -r <change>          # split a non-@ commit
```
The result is two commits with the same parent; the original change ID stays on the first.

### Reorder / parallelize
```
jj rebase -r <change> --after <target>     # move change after another
jj rebase -r <change> --before <target>    # move change before
jj parallelize <range>                     # siblings instead of a line
```

### Update a feature against trunk
```
jj git fetch
jj rebase -b @ -d trunk()             # rebase branch containing @
```

### Push to a remote
```
jj bookmark create feat -r @           # or point at @-
jj git push --bookmark feat            # safe by default: aborts if remote diverged
jj git push --change @                 # auto-bookmark shortcut for quick pushes
```

### Fix a mistake
```
jj undo                # first try — works for most cases
jj op log              # find the op you want to go back to
jj op restore <op>     # jump there
```

## Anti-patterns to Avoid

- **Don't mix `git` and `jj` commands in a colocated repo** without reason — this can cause bookmark conflicts. If you must, `jj git import` / `jj git export` to sync.
- **Don't describe work after doing it** as a default habit — describe first.
- **Don't `jj edit` a commit just to amend it** — `jj squash --into` from `@` is usually cleaner.
- **Don't resolve conflicts in a hurry** — they persist across rebases. Fix them when you have the context.
- **Don't manually "continue" after a rebase conflict** — there is no continue. Conflicts just land in the commit; edit and snapshot when ready.
- **Don't force-push after rewriting** without understanding that `jj git push` already does the right safety check (`--force-with-lease` semantics).
- **Don't `jj abandon` trying to "reset hard"** if the change has descendants you care about — they'll rebase onto the parent, possibly with conflicts. Use `jj restore` or `jj undo` instead.

## References

Load these when a workflow needs more detail. Grep or read directly — they are short.

- `references/workflows.md` — detailed workflows (stacked PRs, interactive squash, split by hunks, resolving divergent bookmarks, cleaning up `@`).
- `references/git-equivalents.md` — cheat sheet mapping common git commands to jj.
- `references/revsets.md` — revset syntax used by `-r` flags (`@`, `@-`, `trunk()`, `::`, `|`, etc.).
- `references/recovery.md` — operation log recipes for fixing mistakes.

For authoritative CLI details, always consult `jj help <command>` or `jj <command> --help`. Online: https://jj-vcs.github.io/jj/ and https://github.com/jj-vcs/jj/tree/main/docs.

## Installation Check

If `jj --version` fails, jj is not installed. Install via:
- Cargo: `cargo install --locked jj-cli`
- macOS: `brew install jj`
- Arch/Nix/openSUSE/FreeBSD packages available
- Pre-built binaries: https://github.com/jj-vcs/jj/releases

After install, set identity once:
```
jj config set --user user.name  "Your Name"
jj config set --user user.email "you@example.com"
```
