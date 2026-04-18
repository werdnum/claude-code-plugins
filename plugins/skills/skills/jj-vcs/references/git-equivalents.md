# Git → jj Cheat Sheet

Concrete command translations. The jj form is often shorter because there's no index and no detached-HEAD dance.

## Setup

| Git | jj |
|-----|-----|
| `git init` | `jj git init` |
| `git init` (with jj on top of existing git) | `jj git init --colocate` |
| `git clone <url>` | `jj git clone <url>` |
| `git config --global user.email X` | `jj config set --user user.email X` |

## Inspection

| Git | jj |
|-----|-----|
| `git status` | `jj st` |
| `git diff` | `jj diff` |
| `git diff HEAD` | `jj diff` (same — `@` is "HEAD") |
| `git diff <rev>` | `jj diff -r <rev>` |
| `git diff A B` | `jj diff --from A --to B` |
| `git log --oneline --graph` | `jj log` |
| `git log <file>` | `jj log <file>` |
| `git show <rev>` | `jj show <rev>` |
| `git blame` | `jj file annotate <path>` |
| `git reflog` | `jj op log` |

## Committing

| Git | jj |
|-----|-----|
| `git add <f>` | (not needed — auto-snapshot) |
| `git add -p` | `jj split -i` / `jj squash -i` |
| `git commit -m X` | `jj commit -m X`  (= describe `@` + new `@`) |
| `git commit --amend` | `jj squash` (no flags — moves `@` into `@-`) |
| `git commit --amend -m X` | `jj describe -m X` (just retitles `@`) |
| `git commit -a` | `jj commit` (working copy is already snapshotted) |

## Branches / Bookmarks

| Git | jj |
|-----|-----|
| `git branch` | `jj bookmark list` |
| `git branch <name>` | `jj bookmark create <name> -r @-` |
| `git branch -f <n> <rev>` | `jj bookmark move <n> --to <rev>` |
| `git branch -d <name>` | `jj bookmark delete <name>` |
| `git checkout <branch>` | `jj new <bookmark>` (starts new @ on it) |
| `git checkout <branch>` (to edit) | `jj edit <bookmark>` |
| `git switch -c new-branch` | `jj new trunk()` then `jj bookmark create new-branch -r @` |

## Rewriting

| Git | jj |
|-----|-----|
| `git rebase main` | `jj rebase -d main` (while @ is on branch) |
| `git rebase -i` (squash / reorder / edit) | `jj squash` / `jj rebase -r ... --after/--before` / `jj describe` |
| `git rebase --continue` | (no-op — conflicts don't block) |
| `git cherry-pick X` | `jj new X` then `jj rebase -d <target>` or `jj duplicate X --destination <target>` |
| `git revert X` | `jj revert -r X` |
| `git reset --hard HEAD` | `jj restore` |
| `git reset --hard <rev>` | `jj edit <rev>` then `jj restore` if needed |
| `git stash` | `jj new @-` (current @ is already saved as a commit) |
| `git stash pop` | `jj edit <stashed-change-id>` |

## Remotes

| Git | jj |
|-----|-----|
| `git fetch` | `jj git fetch` |
| `git pull` | `jj git fetch` + `jj rebase -d trunk()` |
| `git push` | `jj git push --bookmark <name>` |
| `git push -u origin HEAD` | `jj git push --change @` |
| `git push --force-with-lease` | `jj git push` (already does this by default) |

## Undo / Recovery

| Git | jj |
|-----|-----|
| `git reflog` + `git reset` | `jj op log` + `jj op restore <op>` |
| `git reset --soft HEAD^` | `jj undo` (if it was the last op) |
| `git reset --hard HEAD^` | `jj abandon @` |
| `git checkout HEAD -- <f>` | `jj restore <f>` |

## Conceptual swaps

- **Staging area** → just move hunks between commits (`jj squash -i`, `jj split -i`).
- **HEAD** → `@`. **HEAD~1** → `@-`.
- **Detached HEAD** → always. jj never has a "current branch".
- **"fixup" commit + autosquash** → `jj absorb` or `jj squash --into <rev>`.
- **`rerere`** → not needed; conflict resolutions survive rebases natively.
