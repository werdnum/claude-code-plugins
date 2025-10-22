# Claude Code Plugin Architecture Plan

## Overview

This repository will contain 4 plugins extracted from the family-assistant and websidian projects, consolidating hook functionality with rich configuration support.

## Configuration Philosophy

Each plugin supports a **layered configuration system**:

1. **Plugin defaults** (`config/defaults.json`) - Works out of the box
2. **Global overrides** (`~/.config/claude-code/plugin-name.json`) - User preferences
3. **Project overrides** (`.claude/plugin-name.json`) - Project-specific settings

Configuration merges: Project → Global → Defaults (deep merge for objects, override for primitives)

Plugins use `${CLAUDE_PLUGIN_ROOT}` for path resolution and load project config from working directory.

---

## Plugin 1: bash-guard

**Prevent dangerous commands, enforce timeouts, block main branch commits**

### Structure
```
bash-guard/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── check-banned-commands.py
│   └── check-main-branch-commit.py
├── config/
│   └── bash-guard-config.json
└── README.md
```

### hooks/hooks.json
```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "/usr/bin/env python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-banned-commands.py"
        },
        {
          "type": "command",
          "command": "/usr/bin/env python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-main-branch-commit.py"
        }
      ]
    }
  ]
}
```

### Configuration (bash-guard-config.json)
```json
{
  "bannedCommands": {
    "enabled": true,
    "patterns": [
      {
        "regexp": "\\bgit\\s+commit\\b.*--no-verify",
        "explanation": "Using --no-verify bypasses important pre-commit hooks."
      },
      {
        "regexp": "^\\s*rm\\s+-rf\\s+/\\s*$",
        "explanation": "This command would delete the entire filesystem."
      },
      {
        "regexp": "timeout\\s+\\d+\\s+.*",
        "explanation": "Use the Bash tool's timeout parameter instead of the timeout command."
      },
      {
        "regexp": "^\\s*cd\\s+",
        "explanation": "Using cd changes the working directory. Use subshells or absolute paths instead."
      },
      {
        "regexp": "2>&1",
        "explanation": "Redirecting stderr to stdout can cause issues with the Bash tool."
      }
    ],
    "customPatterns": []
  },
  "mainBranchProtection": {
    "enabled": true,
    "protectedBranches": ["main", "master"]
  },
  "timeouts": {
    "defaults": {
      "bash": 120000
    },
    "minimums": {
      "pytest": 300000,
      "poe test": 900000
    }
  },
  "bannedInBackground": ["poe test"]
}
```

### Features (all individually toggleable)
- **Banned command patterns** - Prevent dangerous commands with custom explanations
- **Main branch protection** - Block direct commits to main/master
- **Timeout enforcement** - Ensure minimum timeouts for long-running commands
- **Background restrictions** - Prevent specific commands from running in background

### Configuration Knobs Extracted
- All timeout values (currently hardcoded: 120000, 300000, 900000)
- Protected branch names
- Banned command patterns (extensible)
- Background execution restrictions (simplified to flat list)

---

## Plugin 2: format-and-lint

**Auto-format and lint files after edits (PostToolUse, informational only)**

### Structure
```
format-and-lint/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── format-and-lint.py
│   └── linters/
│       ├── python.py
│       ├── typescript.py
│       └── angular.py
├── config/
│   └── format-lint-config.json
└── README.md
```

### hooks/hooks.json
```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [
        {
          "type": "command",
          "command": "/usr/bin/env python3 ${CLAUDE_PLUGIN_ROOT}/scripts/format-and-lint.py",
          "timeout": 15000
        }
      ]
    }
  ]
}
```

### Configuration (format-lint-config.json)
```json
{
  "formatting": {
    "enabled": true,
    "formatters": {
      "ensure_newline": {
        "enabled": true,
        "patterns": ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.md", "*.json"],
        "command": "sed -i -e '${ /./s/$/\\n/ }'"
      },
      "trim_trailing_whitespace": {
        "enabled": false,
        "patterns": ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"],
        "command": "sed -i 's/[[:space:]]*$//'"
      }
    },
    "exclude": [
      "*.min.js", "*.min.css",
      "build/*", "dist/*", "node_modules/*",
      ".venv/*", "__pycache__/*", "*.pyc"
    ]
  },
  "linting": {
    "enabled": true,
    "informationalOnly": true,
    "python": {
      "enabled": true,
      "venvPath": "${VIRTUAL_ENV:-.venv}",
      "tools": {
        "ruff-format": {
          "enabled": true,
          "command": "{venv}/bin/ruff format {file}",
          "timeout": 5000
        },
        "ruff-check": {
          "enabled": true,
          "command": "{venv}/bin/ruff check --preview --ignore=E501 {file}",
          "timeout": 2000,
          "showDiff": true
        },
        "basedpyright": {
          "enabled": true,
          "command": "{venv}/bin/basedpyright {file}",
          "timeout": 8000,
          "maxErrorsShown": 5
        },
        "ast-grep-conformance": {
          "enabled": true,
          "scriptPath": ".ast-grep/check-conformance.py",
          "timeout": 2000
        },
        "ast-grep-hints": {
          "enabled": true,
          "scriptPath": ".ast-grep/check-hints.py",
          "timeout": 2000,
          "filterMode": "new-code-only"
        }
      }
    },
    "typescript": {
      "enabled": true,
      "projectDir": "frontend",
      "tools": {
        "prettier": {
          "enabled": true,
          "npmScript": "format",
          "timeout": 5000
        },
        "eslint": {
          "enabled": true,
          "npmScript": "lint:fix",
          "timeout": 8000
        }
      }
    },
    "angular": {
      "enabled": false,
      "projectDir": "app",
      "tools": {
        "prettier": {
          "enabled": true,
          "npmScript": "format",
          "timeout": 5000
        },
        "eslint": {
          "enabled": true,
          "npmScript": "lint:fix",
          "timeout": 8000
        }
      }
    }
  }
}
```

### Features (all individually toggleable)
- **Formatting** - ensure newline, trim whitespace, custom sed formatters
- **Python linting** - ruff (format + check), basedpyright, ast-grep conformance/hints
- **TypeScript linting** - prettier, eslint (frontend directory)
- **Angular linting** - prettier, eslint (app directory)

### Notes
- PostToolUse hooks are **informational only** - cannot block
- Combines format-files.py and lint-hook.py into single hook
- Async parallel execution for linters
- Intelligent filtering (Edit shows hints only for new code, Write shows all)

### Configuration Knobs Extracted
- Linter tool timeouts (5000, 2000, 8000 ms)
- Virtual environment path
- Project directory names (frontend vs app)
- npm script names
- Ruff flags (--ignore=E501)
- Hint filter modes (new-code-only, all, new-files-only)
- basedpyright error display limit
- File patterns and exclusions

---

## Plugin 3: guardian

**Test verification, pre-commit review, and stop validation**

### Structure
```
guardian/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── test-verification-hook.sh
│   ├── test-verification-core.sh
│   ├── review-workflow-hook.py
│   └── stop-validation-hook.sh
├── config/
│   └── guardian-config.json
└── README.md
```

### hooks/hooks.json
```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "/bin/bash ${CLAUDE_PLUGIN_ROOT}/scripts/test-verification-hook.sh",
          "timeout": 60000
        },
        {
          "type": "command",
          "command": "/usr/bin/env python3 ${CLAUDE_PLUGIN_ROOT}/scripts/review-workflow-hook.py",
          "timeout": 300000
        }
      ]
    }
  ],
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "/bin/bash ${CLAUDE_PLUGIN_ROOT}/scripts/stop-validation-hook.sh",
          "timeout": 300000
        }
      ]
    }
  ]
}
```

### Configuration (guardian-config.json)
```json
{
  "testVerification": {
    "enabled": true,
    "skipInRemote": true,
    "testCommands": {
      "local": [
        {
          "pattern": "^(\\.?/?\\.\\.?venv/bin/)?poe\\s+test(\\s+(-[xqvs]+|--[a-z-]+|-n\\s*[0-9]+))*\\s*$",
          "name": "poe test"
        },
        {
          "pattern": "^pytest\\b",
          "name": "pytest"
        }
      ],
      "remote": [
        {
          "pattern": "^poe\\s+lint-fast",
          "name": "poe lint-fast"
        }
      ]
    },
    "environmentSelector": "CLAUDE_CODE_REMOTE",
    "triggerCommands": [
      "git commit",
      "gh pr create",
      "echo done"
    ],
    "excludeFromTestRequirement": [
      "^docs/",
      "^\\.claude/",
      "^\\.github/",
      "^\\.devcontainer/",
      "^deploy/",
      "^contrib/",
      "^scripts/review-changes\\.(py|sh)",
      "^scripts/format-and-lint\\.sh",
      "^\\.pre-commit-config\\.yaml",
      "^\\.gitignore",
      "^\\.dockerignore",
      "\\.(md|txt)$",
      "^scratch/",
      "^tmp/",
      "^README",
      "^LICENSE",
      "^CHANGELOG",
      "^Dockerfile$",
      "^\\.devcontainer/Dockerfile$",
      "^\\.devcontainer/Dockerfile\\.ci$"
    ],
    "testReportFallback": {
      "enabled": true,
      "reportFile": ".report.json",
      "transcriptStaleThreshold": 300
    }
  },
  "preCommitReview": {
    "enabled": true,
    "skipInRemote": true,
    "triggers": {
      "gitCommit": true,
      "prCreate": true
    },
    "workflow": {
      "executeGitAdds": true,
      "stashUnstaged": true,
      "runFormatLint": {
        "enabled": false,
        "scriptPath": "scripts/format-and-lint.sh"
      },
      "runPreCommitHooks": {
        "enabled": true,
        "maxIterations": 5
      },
      "runCodeReview": {
        "enabled": false,
        "scriptPath": "scripts/review-changes.py",
        "cacheKeyLength": 12
      }
    },
    "bypassMechanisms": {
      "reviewedSentinel": "Reviewed: cache-{id}",
      "bypassSentinel": "Bypass-Review: {reason}",
      "allowReviewedForMinor": true,
      "requireBypassForBlocking": true
    }
  },
  "stopValidation": {
    "enabled": true,
    "returnCode": 2,
    "skipInRemote": false,
    "validation": {
      "formatAndLint": {
        "enabled": true,
        "commands": [
          ".venv/bin/poe format",
          ".venv/bin/poe lint-fast"
        ]
      },
      "uncommittedChanges": "warn",
      "unpushedCommits": "warn",
      "testStatus": "error",
      "checkRequestFulfilled": true
    },
    "oneshotMode": {
      "enabled": true,
      "strictRequirements": {
        "gitRepo": true,
        "featureBranch": true,
        "cleanWorkingDir": true,
        "allCommitsPushed": true,
        "testsPass": true
      },
      "allowFailureFile": ".claude/FAILURE_REASON"
    }
  }
}
```

### Features (all individually toggleable)

#### Test Verification (PreToolUse)
- Ensures tests run and pass before commits
- Environment-specific test commands (local vs remote)
- Transcript parsing to track modifications and test runs
- Fallback to test report file when transcript is stale

#### Pre-Commit Review (PreToolUse)
- Triggers on git commit and gh pr create
- Executes git add commands
- Stashes unstaged changes
- Optional external format-and-lint script
- Runs pre-commit hooks with auto-fix iterations
- Optional external code review script
- Bypass mechanisms (Reviewed/Bypass-Review sentinels)

#### Stop Validation (Stop)
- "Keep going" prompts to ensure work is complete
- Format/lint validation
- Check for uncommitted changes
- Check for unpushed commits
- Verify tests passed
- Oneshot mode with strict requirements

### Implementation Notes

**test-verification-core.sh** is shared logic used by both test-verification-hook.sh and stop-validation-hook.sh.

**stop-validation-hook.sh** sources it using:
```bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/test-verification-core.sh"
```

### Why Bundled Together
- All validate work quality and completeness
- Share test verification logic
- Share test command configuration
- Related "keep working until done right" philosophy
- Stop hook naturally extends test verification to session end

### Configuration Knobs Extracted
- Test command patterns with environment support (Option A: explicit local/remote)
- File exclusion patterns (currently scattered in jq/bash)
- Pre-commit iteration limit (5)
- Cache key length (12)
- External script paths (optional)
- Transcript staleness threshold (300 seconds)
- Validation severity levels (warn vs error)
- Oneshot mode requirements
- Failure acknowledgment file path

---

## Plugin 4: development-agents

**Distribution of specialized agents and commands**

### Structure
```
development-agents/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── systematic-debugger.md
│   ├── focused-coder.md
│   ├── mechanical-coder.md
│   ├── codebase-researcher.md
│   ├── external-research-specialist.md
│   ├── playwright-qa-tester.md
│   └── parallel-coder.md
├── commands/
│   └── test.md
└── README.md
```

### Features
- Collection of specialized agents for development workflows
- Slash command for running tests
- **No configuration needed** - agents are prompt-based

### Agents Included
- **systematic-debugger** - Methodical debugging and root cause analysis
- **focused-coder** - Self-contained implementation tasks
- **mechanical-coder** - Repetitive changes with ast-grep
- **codebase-researcher** - Code exploration and understanding
- **external-research-specialist** - Web research and external resources
- **playwright-qa-tester** - UI testing with Playwright
- **parallel-coder** - (from websidian) Parallel development coordination

---

## Implementation Plan

### Phase 1: Foundation (Days 1-2)
1. Repository structure and documentation
2. **bash-guard** plugin

### Phase 2: Quality Tools (Days 3-4)
3. **format-and-lint** plugin

### Phase 3: Guardian (Days 5-8)
4. **guardian** plugin
   - test-verification-hook.sh + test-verification-core.sh
   - review-workflow-hook.py
   - stop-validation-hook.sh

### Phase 4: Distribution (Day 9)
5. **development-agents** plugin

### Phase 5: Testing & Documentation (Day 10)
- Test all plugins in family-assistant
- Test all plugins in websidian
- Comprehensive READMEs for each plugin
- Configuration guides with examples
- Update repository CLAUDE.md

---

## Summary

**4 Plugins:**
1. **bash-guard** - Safety checks on bash commands (PreToolUse)
2. **format-and-lint** - Auto-format and lint (PostToolUse, informational)
3. **guardian** - Test verification + Review + Stop validation (2 PreToolUse + 1 Stop)
4. **development-agents** - Agent/command distribution

**Key Design Principles:**
- All features independently toggleable
- Rich configuration with sensible defaults
- Layered configuration (plugin → global → project)
- Environment-aware (CLAUDE_CODE_REMOTE, ONESHOT_MODE, VIRTUAL_ENV)
- Graceful degradation when optional features unavailable
- Clear separation of concerns between plugins
