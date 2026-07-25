---
description: Bootstrap project configuration for all installed plugins
---

# Project Configuration Bootstrap

This command configures all werdnum-plugins for your project through intelligent auto-detection and minimal user interaction.

## Your Task

Configure the following plugins for this project:
- **bash-guard**: Safety checks, timeouts, branch protection
- **format-and-lint**: Auto-formatting and linting
- **guardian**: Pre-commit workflow and stop validation (commit/push/PR completion checks)
- **development-agents**: Already configured (provides this command)

### Step 1: Auto-Detect Project Characteristics

Detect the following using Read and Grep tools (DO NOT use Bash for detection):

1. **Repository Root**:
   - Find the absolute path to this repository (where .claude-plugin/marketplace.json exists)
   - This will be used for the marketplace configuration

2. **Programming Languages**:
   - Python: Check for `setup.py`, `pyproject.toml`, `requirements.txt`, `.py` files
   - TypeScript: Check for `tsconfig.json`, `.ts` files
   - Angular: Check for `angular.json`

3. **Test Commands**:
   - Look for `pytest`, `poe test`, `npm test`, `npm run test`, `pnpm test`, `yarn test`
   - Check `pyproject.toml`, `package.json`, `Makefile` for test scripts

4. **Virtual Environments**:
   - Check for `venv/`, `.venv/`, `.env/`, `virtualenv/`

5. **Project Structure**:
   - Look for directories: `frontend/`, `app/`, `src/`, `backend/`

6. **Git Configuration**:
   - Run `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'` to detect main branch
   - Or check `git branch -r` for main/master

7. **Pre-Commit Framework**:
   - `.pre-commit-config.yaml` → Python's pre-commit
   - `.husky/` directory or `"husky"` in `package.json` → Husky
   - `lefthook.yml` → Lefthook
   - Executable `.git/hooks/pre-commit` → Manual git hooks
   - None found → No framework

### Step 2: Ask Critical Questions

Use the AskUserQuestion tool to ask about:

1. **Main Branch Protection**: "Should commits to the main branch be blocked?"
   - Options: "Enable protection", "Disable protection"

2. **Stop Validation**: "How thorough should completion checks be?"
   - Options:
     - "Strict - Verify formatting, tests, and commits"
     - "Moderate - Check uncommitted changes and tests"
     - "Relaxed - Minimal validation"

### Step 3: Generate/Update Configuration Files

Create or intelligently merge these files:

#### `.claude/settings.json`

Configure the marketplace and enable all plugins:

```json
{
  "extraKnownMarketplaces": {
    "werdnum-plugins": {
      "source": {
        "source": "local",
        "path": "<absolute path to this repository>"
      }
    }
  },
  "enabledPlugins": {
    "bash-guard@werdnum-plugins": true,
    "format-and-lint@werdnum-plugins": true,
    "guardian@werdnum-plugins": true,
    "development-agents@werdnum-plugins": true
  }
}
```

**Path detection**: Use the current working directory (or the repository root if CWD is a subdirectory) as the marketplace path.

**Merge strategy**: If file exists, preserve other settings and only update/add the `extraKnownMarketplaces` and `enabledPlugins` sections.

#### `.claude/bash-guard.json`

Configure based on detected test commands and user preferences:

```json
{
  "mainBranchProtection": {
    "enabled": <user choice>,
    "protectedBranches": ["<detected main branch>"]
  },
  "timeout_requirements": [
    // Add entries for detected test commands, e.g.:
    // {"pattern": "pytest", "min_timeout": 300000},
    // {"pattern": "poe test", "min_timeout": 900000},
    // {"pattern": "npm test", "min_timeout": 300000}
  ]
}
```

**Merge strategy**: Preserve existing rules, only add new timeout requirements if not already configured.

#### `.claude/format-lint.json`

Configure based on detected languages:

```json
{
  "formatting": {
    "enabled": true,
    "formatters": {
      "ensure_newline": true,
      "trim_trailing_whitespace": true
    },
    "exclude": ["*.min.js", "*.min.css", "node_modules/**", ".venv/**", "__pycache__/**"]
  },
  "linting": {
    "enabled": true,
    "informationalOnly": true,
    "python": {
      "enabled": <true if Python detected>,
      "venvPath": "<detected venv path or null>",
      "tools": {
        "ruff": {"enabled": true},
        "basedpyright": {"enabled": true},
        "ast-grep": {"enabled": true}
      }
    },
    "typescript": {
      "enabled": <true if TypeScript detected>,
      "projectDir": "<detected frontend/app directory or null>",
      "tools": {
        "prettier": {"enabled": true},
        "eslint": {"enabled": true}
      }
    },
    "angular": {
      "enabled": <true if Angular detected>,
      "projectDir": "<detected Angular directory or null>",
      "tools": {
        "prettier": {"enabled": true},
        "eslint": {"enabled": true}
      }
    }
  }
}
```

**Merge strategy**: Preserve existing tool configurations, only enable/configure detected languages.

#### `.claude/guardian.json`

Configure based on the detected pre-commit framework and user preferences:

```json
{
  "preCommitReview": {
    "enabled": <true if pre-commit framework detected>,
    "workflow": {
      "runPreCommitHooks": {
        "enabled": <true if pre-commit framework detected>,
        "framework": "<detected framework: 'pre-commit', 'husky', 'lefthook', 'manual', or null>",
        "maxIterations": 3
      }
    }
  },
  "stopValidation": {
    "enabled": true,
    "validation": {
      "formatAndLint": {
        "enabled": <true if strict or moderate>
      },
      "uncommittedChanges": "<based on user choice: 'error' if strict, 'warn' if moderate, 'ignore' if relaxed>",
      "unpushedCommits": "warn",
      "noPr": "<based on user choice: 'error' if strict, 'warn' if moderate/relaxed>"
    }
  }
}
```

Levels: `ignore` skips the check, `warn` reports it without blocking the stop, `error`
blocks the stop. Only `error` blocks.

**Merge strategy**: Preserve existing workflow settings, only update enabled flags and detected values.

### Step 4: Provide Summary

After creating/updating files, show the user:

1. **Detected Configuration**:
   - Languages found
   - Test commands detected
   - Pre-commit framework (if any)
   - Project structure
   - Main branch

2. **Files Created/Updated**:
   - List each config file and what was changed
   - Note any merge conflicts or preserved settings

3. **Marketplace and Plugins**:
   - Marketplace configured in settings.json
   - All four plugins enabled: bash-guard, format-and-lint, guardian, development-agents

4. **Next Steps** (if applicable):
   - Any missing dependencies (ruff, prettier, etc.)
   - Recommendations for tool installation
   - Suggestions for further customization

## Important Notes

- Use Read and Grep tools for detection, NOT Bash (except for git commands)
- Always merge intelligently - don't overwrite user customizations
- Ask only the 2 critical questions - auto-detect everything else
- Provide clear, actionable feedback about what was configured
- If a config file already exists and is well-configured, just note that and preserve it

