# bash-guard

Safety checks for Bash commands in Claude Code - prevents dangerous operations, enforces timeouts, blocks commits to protected branches, and rate limits BashOutput polling.

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

bash-guard is a PreToolUse hook plugin that intercepts Bash and BashOutput tool calls before execution, checking them against configurable safety rules. It acts as a safety net to prevent dangerous commands, enforce git workflow conventions, ensure adequate timeouts for long-running operations, and prevent excessive polling of background processes.

**Hook Type**: PreToolUse (Bash, BashOutput)
**Blocks Execution**: Yes
**Configuration File**: `bash-guard.json`

## Prerequisites

- **uv**: Required for running hook scripts with PEP 723 inline dependencies
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Python 3.11+**: Available on system (uv will use it automatically)

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

### 5. BashOutput Rate Limiting

Prevent excessive polling of background process output:

- Limits BashOutput calls to 2 per minute
- Limits BashOutput calls to 3 per 5 minutes
- Prevents unnecessary resource consumption from rapid polling
- Configurable thresholds and can be disabled if needed
- Uses transcript analysis to track call frequency

### 6. Auto-Fix / Suggestion Mode

bash-guard can suggest command modifications instead of just blocking:

- **Command Rewrites**: Transform problematic commands into safer alternatives
- **Timeout Auto-Setting**: Automatically add or increase timeouts as needed
- **Background Flag Fixes**: Change run_in_background to false when required

**Current Status**: Suggestion mode is enabled by default (`use_updated_input: false`)

The plugin uses Claude Code's `updatedInput` feature to modify commands before execution. However, this feature is currently broken in Claude Code v2.0.34 (see [GitHub issue #4368](https://github.com/anthropics/claude-code/issues/4368)). When disabled (default), the plugin blocks commands but provides detailed suggestions showing exactly what needs to be fixed.

**Example Suggestion Output**:
```
• Command needs modifications:
• Auto-setting timeout to 5 minutes for this command
•   Reason: pytest requires at least 5 minutes for comprehensive test execution
•
• Suggested command:
•   pytest tests/
•   timeout: 300000
```

**When the bug is fixed**, you can enable auto-fix by setting `use_updated_input: true` in your configuration. The plugin will then automatically apply modifications instead of blocking with suggestions.

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
  "use_updated_input": false,
  "default_timeout_ms": 120000,
  "command_rules": [
    {
      "regexp": "\\bnpm\\s+run\\s+dev\\b",
      "action": "block",
      "explanation": "The dev server is already running. Do not start another instance."
    }
  ],
  "timeout_requirements": [
    {
      "regexp": "^npm\\s+test\\b",
      "minimum_timeout_ms": 300000,
      "explanation": "npm test requires at least 5 minutes for comprehensive testing"
    }
  ]
}
```

### Configuration Options

#### Global Settings

```json
{
  "use_updated_input": false,
  "default_timeout_ms": 120000
}
```

**Options**:
- `use_updated_input` (boolean): Enable auto-fix mode (currently disabled due to Claude Code bug)
- `default_timeout_ms` (number): Default timeout in milliseconds for commands without explicit timeout

#### Command Rules (Block or Replace)

```json
{
  "command_rules": [
    {
      "regexp": "^\\s*rm\\s+-rf\\s+/\\s*$",
      "action": "block",
      "explanation": "This command would delete the entire filesystem."
    },
    {
      "regexp": "python\\s+-m\\s+pytest",
      "action": "replace",
      "replacement": "pytest",
      "explanation": "Use pytest directly instead of python -m pytest for better performance"
    }
  ]
}
```

**Options**:
- `regexp` (string): Regular expression pattern to match commands
- `action` (string): Either "block" (prevent execution) or "replace" (suggest rewrite)
- `explanation` (string): Human-readable explanation shown to Claude
- `replacement` (string, required for "replace" action): Replacement pattern (supports regex capture groups)

**Actions**:
- `block`: Command is blocked with explanation
- `replace`: Command is rewritten (or suggested for rewrite if use_updated_input is false)

#### Timeout Requirements

```json
{
  "timeout_requirements": [
    {
      "regexp": "^pytest\\b",
      "minimum_timeout_ms": 300000,
      "explanation": "pytest requires at least 5 minutes for comprehensive test execution"
    },
    {
      "regexp": "^poe\\s+test\\b",
      "minimum_timeout_ms": 900000,
      "explanation": "poe test requires at least 15 minutes for full test suite"
    },
    {
      "regexp": "^npm\\s+run\\s+e2e\\b",
      "minimum_timeout_ms": 600000,
      "explanation": "E2E tests require at least 10 minutes"
    }
  ]
}
```

**Options**:
- `regexp` (string): Pattern to match commands requiring specific timeout
- `minimum_timeout_ms` (number): Minimum timeout in milliseconds
- `explanation` (string): Explanation shown when timeout is insufficient

**Timeout values**:
- 120000ms = 2 minutes
- 300000ms = 5 minutes
- 600000ms = 10 minutes
- 900000ms = 15 minutes

#### Background Restrictions

```json
{
  "background_restrictions": [
    {
      "regexp": "^poe\\s+test\\b",
      "explanation": "poe test must run in foreground to ensure proper output capture"
    },
    {
      "regexp": "^npm\\s+test\\b",
      "explanation": "npm test must run in foreground for test result visibility"
    }
  ]
}
```

**Options**:
- `regexp` (string): Pattern to match commands that should not run in background
- `explanation` (string): Explanation shown when command is run in background

#### BashOutput Rate Limiting

```json
{
  "bashoutput_rate_limit": {
    "enabled": true,
    "max_calls_per_minute": 2,
    "max_calls_per_5_minutes": 3
  }
}
```

**Options**:
- `enabled` (boolean): Enable or disable BashOutput rate limiting (default: true)
- `max_calls_per_minute` (number): Maximum BashOutput calls allowed per minute (default: 2)
- `max_calls_per_5_minutes` (number): Maximum BashOutput calls allowed per 5 minutes (default: 3)

**Use cases**:
- Prevent Claude from rapidly polling background processes
- Reduce unnecessary resource consumption
- Encourage proper wait strategies for long-running commands

**To disable rate limiting**:
```json
{
  "bashoutput_rate_limit": {
    "enabled": false
  }
}
```

**To adjust thresholds**:
```json
{
  "bashoutput_rate_limit": {
    "enabled": true,
    "max_calls_per_minute": 5,
    "max_calls_per_5_minutes": 10
  }
}
```

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

### Example 5: BashOutput Rate Limiting

```bash
Claude attempts: BashOutput for background shell (3rd call in 1 minute)

Result: ❌ Blocked
• BashOutput rate limit exceeded: 3 calls in the last minute (maximum: 2).
  Please wait before checking output again.
  Excessive polling can slow down Claude Code and consume unnecessary resources.
```

**Why this helps**:
- Prevents rapid polling loops
- Encourages waiting for processes to complete naturally
- Reduces transcript size and processing overhead
- Improves overall session performance

## Advanced Configuration

### Command Replacement (Replace Action)

Use the `replace` action to automatically rewrite commands to safer or better alternatives:

```json
{
  "command_rules": [
    {
      "regexp": "python\\s+-m\\s+pytest(.*)",
      "action": "replace",
      "replacement": "pytest\\1",
      "explanation": "Use pytest directly instead of python -m pytest"
    },
    {
      "regexp": "npm\\s+run\\s+build\\s+--\\s+--mode=(\\w+)",
      "action": "replace",
      "replacement": "npm run build:\\1",
      "explanation": "Use build scripts for different modes"
    }
  ]
}
```

**Regex capture groups**:
- `\\1`, `\\2`, etc. in `replacement` refer to captured groups from `regexp`
- Example: `(.*)` captures everything, `\\1` inserts it in replacement

**When use_updated_input is false** (current default):
- Command is blocked with suggestions showing the rewritten version
- Claude sees the suggestion and can manually apply it

**When use_updated_input is true** (when bug is fixed):
- Command is automatically rewritten and executed
- More seamless but less transparent

### Enabling Auto-Fix Mode (Experimental)

To test the `updatedInput` feature (for when the bug is fixed):

```json
{
  "use_updated_input": true
}
```

**Warning**: This currently doesn't work in Claude Code v2.0.34. The JSON output is generated correctly but not applied to tool execution. Keep this disabled unless you're testing with a newer version.

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
  "command_rules": [
    {
      "regexp": "\\bsudo\\s+rm\\b",
      "action": "block",
      "explanation": "Using sudo with rm is dangerous. Double-check what you're deleting."
    },
    {
      "regexp": "\\bcurl\\s+.*\\|\\s*bash",
      "action": "block",
      "explanation": "Piping curl to bash is a security risk. Download and inspect first."
    }
  ]
}
```

This applies to all your projects using bash-guard!

**Note**: Main branch protection is handled by a separate script (`check-main-branch-commit.py`) and doesn't use this configuration file.

### Environment-Specific Configuration

Use different timeout requirements based on environment:

```json
{
  "timeout_requirements": [
    {
      "regexp": "^poe\\s+test\\b",
      "minimum_timeout_ms": 900000,
      "explanation": "Full test suite needs 15 minutes in development"
    }
  ]
}
```

In CI (where resources may differ):
```bash
# CI typically has more resources - reduce timeout requirement
echo '{"timeout_requirements": [{"regexp": "^poe\\\\s+test\\\\b", "minimum_timeout_ms": 300000}]}' > .claude/bash-guard.json
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

**Solution**: Check which pattern is matching by reviewing the explanation. You can:

1. Remove the specific pattern from your project config by creating an empty `command_rules` array:

```json
{
  "command_rules": []
}
```

2. Or override with more specific patterns that don't match your use case

3. Or use the `replace` action instead of `block` to suggest a rewrite

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

**Solution**: Override the specific timeout requirement in your project config:

```json
{
  "timeout_requirements": [
    {
      "regexp": "^poe\\s+test\\b",
      "minimum_timeout_ms": 300000,
      "explanation": "Reduced timeout for faster tests"
    }
  ]
}
```

Or remove all timeout requirements:

```json
{
  "timeout_requirements": []
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

### Auto-Fix Not Working

**Problem**: Set `use_updated_input: true` but commands aren't being auto-fixed

**Solution**: This is a known bug in Claude Code v2.0.34. The `updatedInput` feature is broken - the hook generates correct JSON output but Claude Code doesn't apply the modifications.

**Workaround**: Keep `use_updated_input: false` (the default). The plugin will block commands with detailed suggestions showing exactly what needs to be fixed. Claude can then manually apply the suggestions.

**Tracking**: See [GitHub issue #4368](https://github.com/anthropics/claude-code/issues/4368)

**When fixed**: Update to a newer Claude Code version and set `use_updated_input: true` to enable seamless auto-fixing.

## API Reference

### Configuration Schema

```typescript
interface BashGuardConfig {
  // Global settings
  use_updated_input?: boolean;        // Enable auto-fix mode (default: false)
  default_timeout_ms?: number;        // Default timeout in ms (default: 120000)

  // Command rules (block or replace)
  command_rules?: Array<{
    regexp: string;                   // Pattern to match
    action: "block" | "replace";      // Action to take
    explanation: string;              // Explanation shown to Claude
    replacement?: string;             // Required for "replace" action
  }>;

  // Timeout requirements
  timeout_requirements?: Array<{
    regexp: string;                   // Pattern to match
    minimum_timeout_ms: number;       // Minimum timeout in ms
    explanation: string;              // Explanation shown when insufficient
  }>;

  // Background execution restrictions
  background_restrictions?: Array<{
    regexp: string;                   // Pattern to match
    explanation: string;              // Explanation shown when run in background
  }>;

  // BashOutput rate limiting
  bashoutput_rate_limit?: {
    enabled?: boolean;                // Enable rate limiting (default: true)
    max_calls_per_minute?: number;    // Max calls per minute (default: 2)
    max_calls_per_5_minutes?: number; // Max calls per 5 minutes (default: 3)
  };
}
```

### Default Configuration

See `config/bash-guard-config.json` for complete defaults.

### Environment Variables

- `CLAUDE_PLUGIN_ROOT`: Plugin installation directory (set automatically by Claude Code)

## Related Documentation

- [Main Repository README](../../README.md)
- [Configuration Philosophy](../../README.md#configuration-philosophy)
- [format-and-lint Plugin](../format-and-lint/README.md) - Code quality checks
- [guardian Plugin](../guardian/README.md) - Test verification

## License

MIT - Personal use

---

**Need help?** Check the [main repository README](../../README.md) or create an issue with your question.
