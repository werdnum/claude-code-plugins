# bash-guard

Safety checks for Bash commands in Claude Code - prevents dangerous operations, enforces timeouts, and blocks commits to protected branches.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Advanced Configuration](#advanced-configuration)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

## Overview

bash-guard is a PreToolUse hook plugin that intercepts Bash tool calls before execution, checking them against configurable safety rules. It acts as a safety net to prevent dangerous commands, enforce git workflow conventions, and ensure adequate timeouts for long-running operations.

**Hook Type**: PreToolUse (Bash)
**Blocks Execution**: Yes
**Configuration File**: `bash-guard.json`

## Features

### 1. Banned Command Patterns

Block dangerous commands with customizable patterns and helpful explanations:

- System-destroying commands (rm -rf /, fork bombs)
- Dangerous disk operations (dd, mkfs)
- Security risks (chmod 777 /)
- Claude-specific anti-patterns (cd usage, 2>&1 redirects)
- Custom project-specific patterns

### 2. Main Branch Protection

Prevent direct commits to protected branches:

- Blocks `git commit` on main/master branches by default
- Configurable list of protected branches
- Helpful suggestions for creating feature branches
- Can be disabled if needed

### 3. Timeout Enforcement

Ensure minimum timeouts for long-running commands:

- pytest: 5 minutes (300,000ms) by default
- poe test: 15 minutes (900,000ms) by default
- Custom patterns with custom timeouts
- Detects both missing and insufficient timeouts

### 4. Background Restrictions

Prevent specific commands from running in background:

- Blocks `poe test` from running with `run_in_background: true`
- Custom patterns for project-specific restrictions
- Ensures critical operations complete before continuing

## Installation

```bash
# Add the marketplace (if not already added)
/plugin marketplace add /data/ssd/sync/workspace/src/claude-code-plugins

# Install bash-guard
/plugin install bash-guard@claude-code-plugins

# Verify installation
/plugin list
```

## Quick Start

The plugin works immediately after installation with sensible defaults. No configuration required!

**What's protected by default:**

```bash
# ❌ Blocked: Dangerous system commands
rm -rf /
mkfs.ext4 /dev/sda
chmod -R 777 /

# ❌ Blocked: Git commits to main branch
git checkout main
git commit -m "Fix"

# ❌ Blocked: Insufficient timeouts
pytest  # Requires timeout: 300000 (5 minutes)
poe test  # Requires timeout: 900000 (15 minutes)

# ❌ Blocked: Background execution
poe test  # With run_in_background: true

# ✅ Allowed: Safe operations
pytest tests/unit/  # With timeout: 300000
git checkout -b feature/my-feature
git commit -m "Add feature"
```

## Configuration

### Configuration Locations

bash-guard supports a layered configuration system:

1. **Plugin Defaults**: `<plugin-root>/config/bash-guard-config.json`
2. **Global Overrides**: `~/.config/claude-code/bash-guard.json`
3. **Project Overrides**: `.claude/bash-guard.json`

Configuration merges: Project → Global → Defaults

### Basic Configuration

Create `.claude/bash-guard.json` in your project:

```json
{
  "bannedCommands": {
    "enabled": true,
    "customPatterns": [
      {
        "regexp": "\\bnpm\\s+run\\s+dev\\b",
        "explanation": "The dev server is already running. Do not start another instance."
      }
    ]
  },
  "mainBranchProtection": {
    "enabled": true,
    "protectedBranches": ["main", "master", "staging"]
  },
  "timeouts": {
    "minimums": {
      "^npm\\s+test": 300000
    }
  }
}
```

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

**Options**:
- `enabled` (boolean): Enable/disable banned command checking
- `patterns` (array): Built-in patterns (can be overridden)
- `customPatterns` (array): Additional project-specific patterns

#### Main Branch Protection

```json
{
  "mainBranchProtection": {
    "enabled": true,
    "protectedBranches": ["main", "master", "production", "staging"]
  }
}
```

**Options**:
- `enabled` (boolean): Enable/disable branch protection
- `protectedBranches` (array): List of branch names to protect

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
      "^npm\\s+run\\s+e2e\\b": 600000
    }
  }
}
```

**Options**:
- `defaults.bash` (number): Default timeout in milliseconds
- `minimums` (object): Map of regex patterns to minimum timeout in milliseconds

**Timeout values**:
- 120000ms = 2 minutes
- 300000ms = 5 minutes
- 600000ms = 10 minutes
- 900000ms = 15 minutes

#### Background Restrictions

```json
{
  "bannedInBackground": [
    "^poe\\s+test\\b",
    "^npm\\s+test\\b",
    "^pytest\\b"
  ]
}
```

**Options**:
- Array of regex patterns that should not run in background

## Usage Examples

### Example 1: Preventing System Damage

```bash
User: "Remove all log files"
Claude attempts: rm -rf /var/log

Result: ❌ Blocked
• Using rm with -rf on /var/log could delete important system logs.
  Please use a more specific path.
```

### Example 2: Enforcing Git Workflow

```bash
User: "Commit the changes"
Claude attempts: git commit -m "Update feature"
Current branch: main

Result: ❌ Blocked
• You're currently on the 'main' branch. Direct commits to protected branches are not allowed.
• Please create a feature branch first: git checkout -b feature-name
• Then you can commit your changes and create a pull request.
```

### Example 3: Ensuring Adequate Test Timeouts

```bash
Claude attempts: poe test

Result: ❌ Blocked
• Command 'poe test' requires a minimum timeout of 15 minutes.
  No timeout was specified, using default timeout of 2.0 minutes.
  Please add 'timeout: 900000' to your Bash tool call.
```

### Example 4: Project-Specific Restrictions

Create `.claude/bash-guard.json`:

```json
{
  "bannedCommands": {
    "customPatterns": [
      {
        "regexp": "localhost:5173",
        "explanation": "Use devcontainer-backend-1:5173 instead. The frontend runs in a container."
      },
      {
        "regexp": "\\bpkill\\b.*\\bpoe\\b",
        "explanation": "Don't kill the dev server - it's auto-reloading. Check logs if needed."
      }
    ]
  }
}
```

Now bash-guard enforces your project-specific conventions!

## Advanced Configuration

### Disabling Specific Features

Disable individual features while keeping others active:

```json
{
  "bannedCommands": {"enabled": false},
  "mainBranchProtection": {"enabled": true},
  "timeouts": {
    "minimums": {
      "^pytest\\b": 300000
    }
  }
}
```

### Regular Expression Tips

Patterns use Python's `re` module syntax:

- `^` - Start of string
- `$` - End of string
- `\\b` - Word boundary
- `\\s` - Whitespace
- `.*` - Any characters
- `+` - One or more
- `?` - Zero or one
- `[abc]` - Character class

**Examples**:

```regexp
^\\s*cd\\s+            # Matches cd commands at start
\\bgit\\s+commit\\b.*--no-verify  # git commit with --no-verify
localhost:(8000|5173)  # localhost with specific ports
2>&1                   # stderr redirect (literal)
```

### Global Configuration Example

Set up global rules in `~/.config/claude-code/bash-guard.json`:

```json
{
  "bannedCommands": {
    "customPatterns": [
      {
        "regexp": "\\bsudo\\s+rm\\b",
        "explanation": "Using sudo with rm is dangerous. Double-check what you're deleting."
      },
      {
        "regexp": "\\bcurl\\s+.*\\|\\s*bash",
        "explanation": "Piping curl to bash is a security risk. Download and inspect first."
      }
    ]
  },
  "mainBranchProtection": {
    "enabled": true,
    "protectedBranches": ["main", "master"]
  }
}
```

This applies to all your projects using bash-guard!

### Environment-Specific Configuration

Use different configurations based on environment:

```json
{
  "timeouts": {
    "minimums": {
      "^poe\\s+test\\b": 900000
    }
  }
}
```

In CI:
```bash
# CI typically has more resources
echo '{"timeouts": {"minimums": {"^poe\\\\s+test\\\\b": 300000}}}' > .claude/bash-guard.json
```

## How It Works

### Architecture

```
Bash Tool Call
    ↓
bash-guard PreToolUse Hook
    ↓
1. Load Configuration (Plugin → Global → Project)
2. Check Banned Commands
3. Check Main Branch Protection
4. Check Background Restrictions
5. Check Timeout Requirements
    ↓
Allow (exit 0) or Block (exit 2) with message
```

### Script Files

- **check-banned-commands.py**: Checks all banned patterns, background restrictions, and timeouts
- **check-main-branch-commit.py**: Checks git branch for commit commands

### Configuration Loading

```python
# 1. Load plugin defaults
config = load_json("config/bash-guard-config.json")

# 2. Merge global overrides
global_config = load_json("~/.config/claude-code/bash-guard.json")
config = merge_config(config, global_config)

# 3. Merge project overrides
project_config = load_json(".claude/bash-guard.json")
config = merge_config(config, project_config)
```

### Exit Codes

- **0**: Command allowed, proceed with execution
- **2**: Command blocked, display message to Claude

## Troubleshooting

### Command Blocked Unexpectedly

**Problem**: A safe command is being blocked

**Solution**: Check which pattern is matching by reviewing the explanation. Override the specific pattern in your project config:

```json
{
  "bannedCommands": {
    "patterns": [
      {
        "regexp": "^\\s*cd\\s+",
        "explanation": "disabled"
      }
    ]
  }
}
```

Or disable banned commands entirely:

```json
{
  "bannedCommands": {"enabled": false}
}
```

### Configuration Not Loading

**Problem**: Changes to configuration aren't taking effect

**Solution**:

1. Verify JSON is valid: `cat .claude/bash-guard.json | jq .`
2. Check file location:
   - Global: `~/.config/claude-code/bash-guard.json`
   - Project: `.claude/bash-guard.json` (repository root)
3. Restart Claude Code session
4. Check for typos in configuration keys

### Timeout Too Strict

**Problem**: Timeout requirement is too high for your needs

**Solution**: Override the specific pattern in your project config:

```json
{
  "timeouts": {
    "minimums": {
      "^poe\\s+test\\b": 300000
    }
  }
}
```

Or remove the requirement:

```json
{
  "timeouts": {
    "minimums": {}
  }
}
```

### Branch Protection Too Restrictive

**Problem**: Need to commit to main branch for hotfix

**Solution**: Temporarily disable:

```json
{
  "mainBranchProtection": {"enabled": false}
}
```

Or adjust protected branches:

```json
{
  "mainBranchProtection": {
    "protectedBranches": ["production"]
  }
}
```

### Custom Pattern Not Working

**Problem**: Your regex pattern isn't matching

**Solution**: Test your regex:

```python
import re
pattern = r"your-pattern-here"
command = "your-test-command"
print(bool(re.search(pattern, command)))
```

Remember to escape special characters: `\\b`, `\\s`, etc.

## API Reference

### Configuration Schema

```typescript
interface BashGuardConfig {
  bannedCommands: {
    enabled: boolean;
    patterns: Array<{
      regexp: string;
      explanation: string;
    }>;
    customPatterns: Array<{
      regexp: string;
      explanation: string;
    }>;
  };
  mainBranchProtection: {
    enabled: boolean;
    protectedBranches: string[];
  };
  timeouts: {
    defaults: {
      bash: number;  // milliseconds
    };
    minimums: {
      [pattern: string]: number;  // milliseconds
    };
  };
  bannedInBackground: string[];  // regex patterns
}
```

### Default Configuration

See `config/bash-guard-config.json` for complete defaults.

### Environment Variables

- `CLAUDE_PLUGIN_ROOT`: Plugin installation directory (set automatically)
- `BASH_DEFAULT_TIMEOUT_MS`: Override default bash timeout

## Related Documentation

- [Main Repository README](../../README.md)
- [Configuration Philosophy](../../README.md#configuration-philosophy)
- [format-and-lint Plugin](../format-and-lint/README.md) - Code quality checks
- [guardian Plugin](../guardian/README.md) - Test verification

## License

MIT - Personal use

---

**Need help?** Check the [main repository README](../../README.md) or create an issue with your question.
