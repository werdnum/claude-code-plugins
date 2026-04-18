# jj Workflows

Detailed recipes for common situations. Assumes the Core Tenets in SKILL.md.

## Stacked changes for review

jj makes stacked PRs cheap because descendants auto-rebase when you rewrite an ancestor.

```
jj new trunk() -m "part 1: refactor helpers"
# edit, auto-snapshot
jj new -m "part 2: use helpers in module X"
# edit
jj new -m "part 3: use helpers in module Y"
# edit
```

Push each part with its own bookmark:
```
jj bookmark create part1 -r 'trunk()+'       # first commit after trunk
jj bookmark create part2 -r 'part1+'
jj bookmark create part3 -r 'part2+'
jj git push --all
```

When review comments come on `part1`, fix them without checking out:
```
# edit files in current @ (on top of part3 or wherever)
jj squash --into part1                       # resolution lands in part1; parts 2 and 3 auto-rebase
jj git push --all                            # safe force-push via --force-with-lease semantics
```

## Interactive squash (move hunks between commits)

When `@` contains a mix of work that belongs to several ancestors:
```
jj squash -i --into <change>      # pick hunks from @ to send into <change>
```
The TUI shows a diff; toggle hunks/lines with space, confirm with `c` (or similar — the tool varies).

To use a three-way diff editor like meld or vscode:
```
jj config set --user ui.diff-editor meld
```

## Split a commit into pieces

Interactive split of `@`:
```
jj split
# Picks hunks for the first piece; remainder becomes the second commit.
```

Split by path (non-interactive):
```
jj split path/to/file other/path
```

Split a non-`@` commit:
```
jj split -r <change>
```

To split into more than two pieces, repeat `jj split` on the remainder.

## Absorb (move hunks to the commits that last touched each line)

```
jj absorb
```
Analyzes `@`'s diff and auto-sends each hunk to the most recent ancestor that touched those lines. Like `git absorb` but built in and branch-aware. Especially useful for fixup commits.

## Reorder commits

```
jj rebase -r A --after B            # move A to after B
jj rebase -r A --before C           # move A to before C
jj rebase -r A -d <new-parent>      # set A's parent explicitly
jj parallelize A..B                 # make a linear range into siblings of a common parent
```

`jj rebase -b <branch>` rebases the whole branch containing that commit. `-s <commit>` rebases the subtree starting at `<commit>`.

## Resolve conflicts

Conflicts never block. When one appears:

1. `jj log` shows `(conflict)` on affected commits.
2. `jj status` and `jj resolve --list` show which files.
3. Two ways to resolve:
   - **Edit directly**: open files at the conflicted commit (or on any descendant and propagate with `jj squash`), edit out the markers, and the next jj command snapshots the fix.
   - **Use `jj resolve`**: launches a merge tool per file.
4. If the conflict is on an ancestor and you're currently past it, do your resolution in `@`, then `jj squash --into <conflicted-change>`. Descendants auto-rebase clean.

Marker styles (configure in `ui.conflict-marker-style`):
- `diff` (default): shows the change each side made
- `snapshot`: shows each side's full content
- `git`: uses git diff3 format (2-sided only)

## Rewriting descriptions in bulk

```
jj describe <change>                       # edit one
jj describe <change> -m "new message"      # non-interactive
```

Multiple commits: iterate with a revset, or `jj log -r <revset> -T builtin_log_oneline` to find IDs first.

## Pushing to GitHub / GitLab

```
jj git fetch                                # pull remote refs
jj git push --bookmark <name>               # push a named bookmark
jj git push --change @                      # quick-push: auto-creates a bookmark named "push-<change-id>"
jj git push --allow-new                     # required when pushing a bookmark that doesn't exist on remote
```

Push safety: jj refuses if the remote bookmark has moved since last fetch. Re-fetch and rebase, don't bypass unless you know why.

## Address review feedback on a stacked branch

Option 1 — keep history clean (preferred):
```
# from anywhere — no checkout needed
# make the fix in @
jj squash --into <feature-change>
jj git push --bookmark <feature-bookmark>   # force-pushed safely
```

Option 2 — add commits on top:
```
jj new <feature-bookmark> -m "address review"
# edit
jj bookmark move <feature-bookmark> --to @
jj git push --bookmark <feature-bookmark>
```

## "Stash" equivalent

No stash needed — `@` is already a commit. Just:
```
jj new @-                  # abandon @ as a save point, fresh @ to work in
# later:
jj edit <change-id>        # resume by editing the saved commit
```

## Working copy is stale

If another workspace or process rewrote the commit at `@`:
```
jj workspace update-stale
```

## Inspecting change evolution

```
jj evolog               # history of how a change was rewritten
jj evolog -p            # with diffs
jj op log               # all operations
jj op log -p            # with what each operation changed
```

## Private / local-only commits

Add machine-specific config/credentials in a commit that never gets pushed. Configure:
```toml
# ~/.config/jj/config.toml
[git]
private-commits = "description(glob:'PRIVATE:*')"
```
Any commit whose description starts with `PRIVATE:` (or matches whatever revset you pick) is blocked from push.

## Clone a GitHub repo

```
jj git clone https://github.com/foo/bar.git
# or for an existing git repo:
cd existing-repo && jj git init --colocate
```

Colocated (`.git` and `.jj` side by side) is convenient for tooling but mixing git commands requires care. Non-colocated (`.git` hidden inside `.jj`) is cleaner but needs `jj git import`/`export` for manual syncs.
