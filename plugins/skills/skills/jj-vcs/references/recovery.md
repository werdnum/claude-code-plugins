# Recovery Recipes

jj's operation log makes almost every mistake reversible. Reach for these before anything destructive.

## The golden rule

When something surprises you, run:
```
jj op log
```
Then pick the operation you want to be "at" and either:
- `jj undo` — reverse the single most recent operation
- `jj op restore <op-id>` — jump the whole repo back to that point
- `jj op revert <op-id>` — apply the inverse of a specific past operation, without discarding the ops after it

`jj op log -p` shows what each operation changed.

## "I just rewrote the wrong commit"

```
jj undo
```
Done. The operation log tracked the rewrite, so undo restores the old commit IDs and re-points bookmarks.

## "I abandoned a commit I needed"

Abandoned commits are hidden but not gone. Find them:
```
jj op log -p | less                        # browse
jj log -r <commit-id>                      # direct lookup if you know the hash
```

Restore by either `jj op restore <op-id>` (rewinds the abandon) or cherry-pick the hash:
```
jj new <commit-id>                         # fresh @ based on the recovered commit
```

## "I squashed hunks into the wrong commit"

```
jj undo
```
Because the squash was a single op. If there have been operations since, use `jj op log` to find the op just before the bad squash and `jj op restore <that-op>`.

## "Working copy shows 'stale' warnings"

Another workspace or tool rewrote `@`.
```
jj workspace update-stale
```

## "I have a bookmark conflict (`??`)"

The bookmark points at multiple places because a fetch or rewrite introduced divergence.
```
jj bookmark list                                    # shows the conflicting commits
jj bookmark move <name> --to <desired-commit-id>    # pick a winner
```

## "I ran `git <something>` in a colocated repo and jj is confused"

```
jj git import        # re-read git's refs into jj's view
```
And if jj state needs to be reflected into git:
```
jj git export
```

## "Push failed because remote moved"

That's jj's safety check. Do:
```
jj git fetch
jj rebase -b <bookmark> -d trunk()         # or wherever
jj git push --bookmark <bookmark>
```
Don't bypass the check unless you know the remote is wrong.

## "I want to see what the repo looked like before all of today"

```
jj op log                                  # find an op from yesterday
jj log --at-op <op-id>                     # inspect only — no state change
```
`--at-op` disables working-copy snapshotting, so it's safe to run read-only commands without perturbing state.

## "I accidentally committed secrets"

If not yet pushed: `jj abandon <change>` or `jj restore -r <change> <path>` to unstage.
If pushed: that's beyond jj's remit — rotate the secret and use git's history-rewriting tooling (e.g., `git filter-repo`) on the git-side refs, then `jj git import`.

## Escape hatch

If the repo state seems genuinely corrupt and `jj op log` isn't helping:
```
ls .jj/repo/op_heads/heads                 # look at operation heads directly
jj debug operation <op-id>                 # inspect raw op details
```
Only reach for this when normal commands fail.
