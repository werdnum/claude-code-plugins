# bash-guard

Safety checks for Bash commands in Claude Code - prevents dangerous operations, enforces timeouts, and blocks commits to protected branches.

## Features

- **Banned Command Patterns**: Block dangerous commands with customizable patterns and helpful explanations
- **Main Branch Protection**: Prevent direct commits to main/master branches
- **Timeout Enforcement**: Ensure minimum timeouts for long-running commands
- **Background Restrictions**: Prevent specific commands from running in background mode

All features are individually toggleable via configuration.

## Installation

```bash
# Add this marketplace (if not already added)
/plugin marketplace add /data/ssd/sync/workspace/src/claude-code-plugins

# Install the plugin
/plugin install bash-guard@claude-code-plugins
```

## Quick Start

The plugin works out of the box with sensible defaults. It will:

- Block dangerous system commands (rm -rf /, fork bombs, etc.)
- Prevent commits to main/master branches
- Require 5-minute minimum timeout for pytest
- Require 15-minute minimum timeout for `poe test`
- Prevent `poe test` from running in background

## Configuration

The plugin supports a **layered configuration system**:

1. **Plugin defaults** (`config/bash-guard-config.json`) - Works out of the box
2. **Global overrides** (`~/.config/claude-code/bash-guard.json`) - Your preferences across all projects
3. **Project overrides** (`.claude/bash-guard.json`) - Project-specific settings

Configuration merges: Project → Global → Defaults (deep merge for objects, override for primitives)

### Configuration Options

#### Banned Commands

```json
{
  "bannedCommands": {
    "enabled": true,
    "patterns": [
      {
        "regexp": "^\\s*rm\\s+-rf\\s+/\\s*$",
        "explanation": "This command would delete the entire filesystem."
      }
    ],
    "customPatterns": [
      {
        "regexp": "\\bmy-dangerous-command\\b",
        "explanation": "Custom explanation for why this is blocked."
      }
    ]
  }
}
```

#### Main Branch Protection

```json
{
  "mainBranchProtection": {
    "enabled": true,
    "protectedBranches": ["main", "master", "production"]
  }
}
```

#### Timeout Enforcement

```json
{
  "timeouts": {
    "defaults": {
      "bash": 120000
    },
    "minimums": {
      "^pytest\\b": 300000,
      "^poe\\s+test\\b": 900000,
      "^npm\\s+run\\s+test\\b": 180000
    }
  }
}
```

Timeouts are specified in milliseconds:
- 120000ms = 2 minutes
- 300000ms = 5 minutes
- 900000ms = 15 minutes

#### Background Restrictions

```json
{
  "bannedInBackground": [
    "^poe\\s+test\\b",
    "^npm\\s+test\\b"
  ]
}
```

### Example: Project-Specific Configuration

Create `.claude/bash-guard.json` in your project:

```json
{
  "bannedCommands": {
    "customPatterns": [
      {
        "regexp": "\\bnpm\\s+run\\s+dev\\b",
        "explanation": "The dev server is already running. Do not start another instance."
      },
      {
        "regexp": "localhost:3000",
        "explanation": "Use docker-backend:3000 instead. The app runs in a container."
      }
    ]
  },
  "mainBranchProtection": {
    "protectedBranches": ["main", "staging", "production"]
  },
  "timeouts": {
    "minimums": {
      "^npm\\s+run\\s+e2e\\b": 600000
    }
  }
}
```

### Example: Global Configuration

Create `~/.config/claude-code/bash-guard.json`:

```json
{
  "bannedCommands": {
    "patterns": [
      {
        "regexp": "\\bsudo\\s+rm\\b",
        "explanation": "Using sudo with rm is dangerous. Please review what you're deleting."
      }
    ]
  },
  "mainBranchProtection": {
    "enabled": true
  }
}
```

## Disabling Features

To disable a feature, set `enabled: false` in your configuration:

```json
{
  "mainBranchProtection": {
    "enabled": false
  }
}
```

Or disable all banned commands:

```json
{
  "bannedCommands": {
    "enabled": false
  }
}
```

## How It Works

The plugin registers PreToolUse hooks that intercept Bash tool calls before execution:

1. **check-banned-commands.py**: Checks command against banned patterns, background restrictions, and timeout requirements
2. **check-main-branch-commit.py**: Checks if git commits are being made to protected branches

If a check fails, the command is blocked and Claude receives an explanation of why.

## Regular Expressions

Patterns use Python's `re` module syntax. Common patterns:

- `^` - Start of string
- `$` - End of string
- `\\b` - Word boundary
- `\\s` - Whitespace
- `.*` - Any characters
- `+` - One or more
- `?` - Zero or one
- `[abc]` - Character class

Examples:
- `^\\s*cd\\s+` - Matches cd commands at start of line
- `\\bgit\\s+commit\\b.*--no-verify` - Matches git commit with --no-verify flag
- `2>&1` - Matches stderr redirect

## Troubleshooting

### Command blocked unexpectedly

Check which pattern is matching by reviewing the explanation. You can override or disable specific patterns in your project config.

### Configuration not loading

Ensure your JSON is valid and the file is in the correct location:
- Global: `~/.config/claude-code/bash-guard.json`
- Project: `.claude/bash-guard.json` (in repository root)

### Timeouts too strict

Override the minimum timeout for specific commands in your project configuration:

```json
{
  "timeouts": {
    "minimums": {
      "^poe\\s+test\\b": 300000
    }
  }
}
```

## License

Personal use - Part of claude-code-plugins repository
