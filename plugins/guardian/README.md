# guardian

Ensures code quality through test verification, pre-commit review workflows, and stop validation.

## Features

- **Test Verification** (PreToolUse): Ensures tests run and pass before commits
- **Pre-Commit Review** (PreToolUse): Executes git adds, runs pre-commit hooks, optional code review
- **Stop Validation** (Stop hook): "Keep going" prompts to ensure work is complete

All features are individually toggleable via configuration.

## Installation

```bash
/plugin install guardian@claude-code-plugins
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

### Pre-Commit Review

Runs workflow before git commits and PR creation:

1. Executes any `git add` commands in the commit command
2. Stashes unstaged changes to isolate staged changes
3. Runs pre-commit hooks with auto-fix iterations (max 5)
4. Optional external code review script
5. Restores stashed changes after workflow

Bypass mechanisms:
- `Reviewed: cache-{id}` for minor issues
- `Bypass-Review: {reason}` for escalation to user

### Stop Validation

Validates work is complete before stopping session:

**Regular Mode**:
- Runs format/lint commands
- Warns about uncommitted changes
- Warns about unpushed commits
- Checks test status
- Prompts "Have you fulfilled the user's request?"

**Oneshot Mode** (ONESHOT_MODE=true):
- Strict requirements: git repo, feature branch, clean working dir, all commits pushed, tests pass
- Blocks exit until all requirements met
- Allow acknowledged failure with `.claude/FAILURE_REASON` file

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
    "triggerCommands": ["git commit", "echo done"]
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
- Stop validation provides "keep going" feedback to ensure completeness
