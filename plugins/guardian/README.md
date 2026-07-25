# guardian

Ensures code quality through test verification, pre-commit review workflows, and stop validation.

## Features

- **Test Verification** (PreToolUse): Ensures tests run and pass before commits
- **Pre-Commit Workflow** (PreToolUse): Executes git adds, runs formatters/linters and pre-commit hooks
- **Stop Validation** (Stop hook): Quality checks (lint, commits, tests, PR) before the session ends

All features are individually toggleable via configuration.

## Prerequisites

- **uv**: Required for running hook scripts with PEP 723 inline dependencies
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Python 3.11+**: Available on system (uv will use it automatically)

No hook in this plugin calls an LLM.

## Installation

```bash
/plugin install guardian@werdnum-plugins
```

## Quick Start

Works out of the box with:
- Test verification for `poe test` and `pytest` commands
- Pre-commit hook execution (if `.pre-commit-config.yaml` exists)
- Stop validation for uncommitted changes and test status

## Features

### Test Verification

Ensures tests have been run successfully since the last file modification before allowing commits:

- Tracks file modifications in transcript
- Verifies test commands ran after modifications
- Falls back to `.report.json` file when transcript is stale (>5 minutes)
- Skips verification in remote Claude Code sessions (CLAUDE_CODE_REMOTE=true)
- Excludes documentation and config files from test requirements

#### Relaxed Test File Verification

When only test files have been modified since the last full test run, the hook allows individual test verification instead of requiring a full test suite re-run. This is useful when:

1. You run the full test suite (`poe test`)
2. Code review suggests minor formatting fixes in a test file
3. You can now verify just the modified test file instead of the entire suite

**Requirements:**
- At least one full passing test run must exist as a baseline
- Only test files (matching `testFilePatterns`) have been modified since that baseline
- Each modified test file must have been individually run and passed after its modification

**Configuration:**
```json
{
  "testVerification": {
    "relaxedTestFileVerification": {
      "enabled": true,
      "testFilePatterns": [
        "^tests?/",
        "_test\\.py$",
        "test_[^/]*\\.py$"
      ],
      "singleTestCommand": {
        "local": "pytest {file}",
        "remote": null
      }
    }
  }
}
```

The `singleTestCommand` uses `{file}` as a placeholder for the test file path. If not configured, the hook suggests appropriate commands based on file extension.

### Pre-Commit Workflow

Runs before git commits and PR creation:

1. Executes any `git add` commands in the commit command
2. Stashes unstaged changes to isolate staged changes
3. Runs formatters/linters (disabled by default)
4. Runs pre-commit hooks with auto-fix iterations (max 5)
5. Restores stashed changes after workflow

Every gate here is deterministic — it either runs a real command or does nothing.

> **Note:** This hook no longer runs an automatic LLM code review. The review shelled
> out to `review-changes.py` (defaulting to Gemini) on every commit, and with no API key
> configured it failed open: the hook reported "no specific issues available" and let the
> commit through regardless of the diff, which reads like a review that passed. The
> `Reviewed: cache-{id}` and `Bypass-Review: {reason}` commit-message sentinels went with
> it — there is nothing left to acknowledge or bypass.
>
> The review script itself was worth keeping and now lives outside the plugin, at
> `scripts/review-changes.py` in the marketplace repository. Run it by hand when you want
> a review, where a missing API key is a visible error rather than a silent pass.

### Stop Validation

Runs concrete quality checks against repository state before the session ends:

**Regular Mode**:
- Runs format/lint commands
- Warns about uncommitted changes
- Warns about unpushed commits
- Warns when a branch with unmerged work has no PR
- Checks test status

**Levels**: each check is configured as `ignore`, `warn`, or `error`.

| Level | Behaviour |
| ----- | --------- |
| `ignore` | Check does not run |
| `warn` | Issue is reported to you as a system message; **the session still stops** |
| `error` | Stop is blocked and the issue is sent back to Claude to fix |

Only `error` blocks. `uncommittedChanges`, `unpushedCommits` and `noPr` all
default to `warn`, so out of the box stop validation reports but never blocks.
Raise a specific check to `error` if you want it enforced.

**When the git checks stay quiet**: these checks only fire when there is
genuinely something left to do, and stay silent whenever they cannot determine
the answer rather than guessing. Specifically, the "no PR created" check is
skipped on a detached HEAD, on the trunk/default branch, when the branch has no
commits ahead of its base branch, when HEAD has not yet reached its upstream —
whether never pushed or pushed and since added to (the unpushed-commits check
covers those instead, so you don't get told to push *and* to open a PR for the
same missing step) — and when the PR lookup itself fails: `gh` missing,
unauthenticated, no GitHub remote, or an API error.

"Has this been pushed?" is answered by asking whether HEAD is contained in any
remote-tracking ref — not by counting commits against the base branch, and not
by looking for tracking configuration. A base comparison misreads a local-only
`main` (the base ref *is* HEAD, so zero commits ahead reads as "already
pushed"), and an `@{u}` check misses `git push origin HEAD:feature`, which
publishes the branch without setting up tracking. Push advice names an existing
remote (`origin` when present, otherwise the first configured one) and says so
plainly when there is no remote at all.

Nothing assumes the remote is called `origin` or the trunk is called
`main`/`master`. The base branch resolves through each remote's recorded
default (`refs/remotes/<remote>/HEAD`) first, then conventional names on each
remote, then local ones — so an `upstream`/`develop` layout is handled.

A closed or merged PR only counts as "this branch has a PR" while its head
commit is still the branch's head. That keeps a branch from being re-nagged
once its PR lands, without letting a stale PR vouch for new commits pushed to a
branch that was reused after its previous PR merged.

**Oneshot Mode** (ONESHOT_MODE=true):
- Strict requirements: git repo, feature branch, clean working dir, all commits pushed, tests pass
- Blocks exit until all requirements met
- Allow acknowledged failure with `.claude/FAILURE_REASON` file
- Requires *both* `oneshotMode.enabled` in config and the `ONESHOT_MODE`
  environment variable; with only the config flag set, validation falls through
  to regular mode
- Unlike regular mode, oneshot mode does **not** let uncertainty satisfy a
  requirement. Where regular mode stays quiet if it cannot resolve a base
  branch, oneshot mode falls back to "does this branch have any commits at all"
  so a single-branch checkout or a repo with no remote still has its push and
  PR requirements enforced
- A detached HEAD is reported as its own failure. There is no branch to name,
  no upstream to track and nothing for a PR to target, so the branch, push and
  PR requirements would otherwise all skip and let a detached commit report
  success. (Regular mode stays quiet on a detached HEAD, as before.)
- Turning off `gitRepo` does not implicitly satisfy the other requirements.
  Outside a repository with `featureBranch`, `allCommitsPushed` or `prCreated`
  still enabled, that is reported as its own failure rather than passing by
  virtue of being uncheckable
- `prCreated` requires positive confirmation: only a successful lookup that
  finds a PR satisfies it. If `gh` is missing, unauthenticated, or the lookup
  fails, the requirement is reported as unverified rather than passed. Use the
  failure file to record a legitimate reason it can't be met

Each entry under `strictRequirements` can be set to `false` to drop that
requirement:

```json
{
  "stopValidation": {
    "oneshotMode": {
      "enabled": true,
      "strictRequirements": { "prCreated": false, "testsPass": false }
    }
  }
}
```

**Background tasks**: When background tasks or scheduled (cron) tasks are still
in flight, the hook allows the session to stop instead of running validation.
Claude Code re-awakens the session when that work completes, so stopping is
expected rather than premature — and blocking would only busy-wait.

> **Note:** Stop validation no longer includes an LLM "keep going" prompt that
> judged whether to block stopping when actionable work remained. That
> overlapped with Claude Code's built-in [`/goal`](https://code.claude.com/docs/en/goal)
> (itself a session-scoped prompt-based Stop hook). Use `/goal` to keep a
> session working toward a completion condition.

## Configuration

Example `.claude/guardian.json`:

```json
{
  "testVerification": {
    "enabled": true,
    "testCommands": {
      "local": [
        {"pattern": "^poe\\s+test", "name": "poe test"},
        {"pattern": "^pytest\\b", "name": "pytest"}
      ]
    },
    "triggerCommands": ["git commit", "echo done"],
    "relaxedTestFileVerification": {
      "enabled": true,
      "testFilePatterns": [
        "^tests?/",
        "_test\\.py$",
        "test_[^/]*\\.py$"
      ],
      "singleTestCommand": {
        "local": "pytest {file}"
      }
    }
  },
  "preCommitReview": {
    "enabled": true,
    "workflow": {
      "runPreCommitHooks": {"enabled": true, "maxIterations": 5}
    }
  },
  "stopValidation": {
    "enabled": true,
    "validation": {
      "formatAndLint": {
        "enabled": false
      }
    }
  }
}
```

## Disabling Features

Disable in `.claude/guardian.json`:

```json
{
  "testVerification": {"enabled": false},
  "preCommitReview": {"enabled": false},
  "stopValidation": {"enabled": false}
}
```

## Environment Variables

- `CLAUDE_CODE_REMOTE`: Skip test verification and review when true
- `ONESHOT_MODE`: Enable strict stop validation requirements
- `VIRTUAL_ENV`: Python virtual environment path (default: `.venv`)

## File Exclusions

Files matching these patterns don't require tests:
- Documentation: `docs/`, `*.md`, `*.txt`, `README`, `LICENSE`
- Config: `.claude/`, `.github/`, `.devcontainer/`, `.gitignore`
- Deployment: `deploy/`, `contrib/`, `scripts/`
- Temporary: `scratch/`, `tmp/`

## Troubleshooting

**Tests required for docs changes**: Override `excludeFromTestRequirement` in config

**Pre-commit hooks fail**: Check `.pre-commit-config.yaml` and hook implementations

**Stop hook disabled**: Check line 4 of `stop-validation-hook.sh` - may be disabled due to Claude bug

**Oneshot mode too strict**: Use `.claude/FAILURE_REASON` file to acknowledge inability to complete

## Notes

- Test verification uses transcript parsing (Claude Code session history)
- Falls back to `.report.json` when transcript >5 minutes old
- Pre-commit workflow stashes/restores unstaged changes automatically
- Stop validation runs quality checks (lint, git state, tests) and is skipped while background or scheduled tasks are still in flight
