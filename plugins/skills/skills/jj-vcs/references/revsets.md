# jj Revsets

A revset is a functional expression that selects commits. Used anywhere a `-r` flag appears.

## Single-commit symbols

| Symbol | Meaning |
|--------|---------|
| `@` | Working copy commit |
| `@-` | Parent of working copy (like `HEAD~1`) |
| `@--` | Grandparent |
| `@+` | Child (only unambiguous if one) |
| `<change-id>` | Commit by change ID prefix (stable across rewrites) |
| `<commit-id>` | Commit by commit hash prefix |
| `<bookmark>` | The commit a bookmark points to |
| `<bookmark>@origin` | The remote-tracking version of a bookmark |
| `root()` | The virtual root commit |
| `trunk()` | The configured trunk head (typically `main@origin`) |

## Operators

| Operator | Meaning |
|----------|---------|
| `x-` | Parents of x |
| `x+` | Children of x |
| `::x` | All ancestors of x (including x) |
| `x::` | All descendants of x (including x) |
| `x..y` | Ancestors of y that aren't ancestors of x (like `git log x..y`) |
| `x::y` | Commits that are descendants of x AND ancestors of y |
| `x \| y` | Union |
| `x & y` | Intersection |
| `x ~ y` | Difference (x but not y) |

## Useful functions

| Function | Meaning |
|----------|---------|
| `all()` | Every visible commit |
| `none()` | Empty set |
| `heads(x)` | Tips within x |
| `roots(x)` | Bottoms within x |
| `ancestors(x, depth)` | Bounded ancestors |
| `author(pattern)` | Commits by author matching pattern |
| `description(pattern)` | Commits whose description matches |
| `files(fileset)` | Commits touching these paths |
| `bookmarks()` / `bookmarks(pattern)` | Commits with a bookmark |
| `remote_bookmarks()` | Commits with a remote-tracking bookmark |
| `tags()` | Commits with tags |
| `conflicts()` | Conflicted commits |
| `empty()` | Commits with no diff vs parent |
| `merges()` | Merge commits |
| `immutable_heads()` | Heads of the immutable set (trunk, tags by default) |
| `mutable()` | Everything NOT immutable — safe to rewrite |
| `visible_heads()` | All current branch tips |

## Common recipes

```
jj log -r '::@'                         # history leading to @
jj log -r '@ | @-'                      # @ and its parent
jj log -r 'trunk()..@'                  # commits on my branch not in trunk
jj log -r 'trunk()..@ | trunk()..@-'    # your stack plus immediate parent
jj log -r 'mutable()'                   # everything I can still edit
jj log -r 'conflicts()'                 # what's broken
jj log -r 'author("me@") & description("WIP")'
jj log -r 'files("src/foo.py")'
```

## Patterns in string arguments

Most functions that take strings accept glob / regex prefixes:
- `"exact"` — exact match
- `glob:"pattern*"` — glob
- `regex:"pat.*"` — regex
- `substring:"sub"` — substring (default for many functions)

Example: `jj log -r 'description(glob:"fix:*")'`.

## Configuring defaults

Default log revset:
```toml
[revsets]
log = "main@origin.."
```

Aliases for reuse:
```toml
[revset-aliases]
"mine()" = "author(your@email)"
"immutable_heads()" = "builtin_immutable_heads() | tags()"
```
