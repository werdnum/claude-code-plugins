# Claude Code Plugins

Personal collection of Claude Code plugins for development workflows, extracted from real-world projects and designed for reusability across codebases.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Available Plugins](#available-plugins)
- [Configuration Philosophy](#configuration-philosophy)
- [Plugin Comparison](#plugin-comparison)
- [Installation Guide](#installation-guide)
- [Usage Examples](#usage-examples)
- [Continuous Integration](#continuous-integration)
- [Development](#development)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## Overview

This repository serves as a local plugin marketplace for Claude Code, containing four production-ready plugins that enhance development workflows:

1. **bash-guard** - Safety enforcement for shell commands
2. **format-and-lint** - Automated code quality checks
3. **guardian** - Test verification and quality gates
4. **development-agents** - Specialized AI agents for development tasks

All plugins were extracted from the `family-assistant` and `websidian` projects, refactored for reusability, and enhanced with comprehensive configuration systems.

### Why These Plugins?

These plugins solve real development workflow challenges:

- **Prevent mistakes** before they happen (bash-guard)
- **Maintain code quality** automatically (format-and-lint)
- **Enforce testing discipline** without manual checking (guardian)
- **Delegate specialized tasks** to focused agents (development-agents)

## Quick Start

### 1. Add the Marketplace

```bash
# Local path (for development)
/plugin marketplace add /data/ssd/sync/workspace/src/claude-code-plugins

# Or from git remote
/plugin marketplace add https://github.com/your-username/claude-code-plugins
```

### 2. Install Plugins

```bash
# Install all plugins
/plugin install bash-guard@werdnum-plugins
/plugin install format-and-lint@werdnum-plugins
/plugin install guardian@werdnum-plugins
/plugin install development-agents@werdnum-plugins

# Or browse and install interactively
/plugin
```

### 3. Verify Installation

```bash
/plugin list
```

### 4. Bootstrap Configuration (Recommended)

Use the `/bootstrap-plugins` command to automatically configure all plugins:

```bash
/bootstrap-plugins
```

This command will:
- Auto-detect your project type and characteristics
- Ask a few critical configuration questions
- Generate optimal configurations for all plugins
- Set up the marketplace in `.claude/settings.json`

### 5. Manual Configuration (Alternative)

If you prefer manual setup, each plugin works out of the box with sensible defaults. To customize:

```bash
# Create project-specific config
mkdir -p .claude
echo '{"bannedCommands": {"enabled": true}}' > .claude/bash-guard.json

# Or create global config
mkdir -p ~/.config/claude-code
echo '{"linting": {"enabled": true}}' > ~/.config/claude-code/format-lint.json
```

## Available Plugins

### bash-guard

**Category**: Safety & Protection
**Hook Type**: PreToolUse (Bash)
**Configuration**: `bash-guard.json`

Prevents dangerous shell commands from executing and enforces best practices. Supports automatic command rewriting and timeout enforcement with suggestion-based feedback.

**Key Features**:
- Block dangerous commands (rm -rf /, fork bombs, etc.)
- Prevent commits to protected branches (main/master)
- Enforce minimum timeouts for long-running commands
- Block specific commands from running in background
- **Auto-fix/Suggestion mode**: Suggest command rewrites and timeout adjustments
- **Command replacement**: Transform problematic commands into safer alternatives

**Use Cases**:
- Prevent accidental system damage
- Enforce git workflow conventions
- Ensure adequate test timeouts
- Project-specific command restrictions

**[Full Documentation →](plugins/bash-guard/README.md)**

---

### format-and-lint

**Category**: Code Quality
**Hook Type**: PostToolUse (Edit/Write)
**Configuration**: `format-lint.json`

Automatically format and lint code after edits, providing immediate feedback on code quality issues.

**Key Features**:
- **Python**: ruff format, ruff check, basedpyright, ast-grep
- **TypeScript/JavaScript**: prettier, eslint
- **Angular**: prettier, eslint for .ts/.html/.css
- File formatters: ensure newline at EOF, trim whitespace
- Informational only (doesn't block)

**Use Cases**:
- Maintain consistent code style
- Catch type errors immediately
- Enforce project-specific patterns (ast-grep)
- Multi-language projects

**[Full Documentation →](plugins/format-and-lint/README.md)**

---

### guardian

**Category**: Quality Gates
**Hook Types**: PreToolUse (Bash), Stop
**Configuration**: `guardian.json`

Ensures code quality through test verification, pre-commit workflows, and completion validation.

**Key Features**:
- **Test Verification**: Ensures tests run and pass before commits
- **Pre-Commit Review**: Executes git adds, runs pre-commit hooks, optional code review
- **Stop Validation**: "Keep going" prompts to ensure work completeness
- **Oneshot Mode**: Strict requirements for automated/CI environments

**Use Cases**:
- Enforce testing discipline
- Automate pre-commit workflows
- Prevent incomplete work sessions
- CI/CD integration with oneshot mode

**[Full Documentation →](plugins/guardian/README.md)**

---

### development-agents

**Category**: Specialized Agents
**Hook Type**: None (agents & commands)
**Configuration**: None required

Collection of specialized AI agents for focused development tasks.

**Included Agents**:
- **systematic-debugger** (Opus): Methodical bug investigation
- **focused-coder** (Sonnet): Self-contained implementation tasks
- **mechanical-coder**: Repetitive changes with ast-grep
- **codebase-researcher**: Code exploration and understanding
- **external-research-specialist**: Web research and documentation
- **playwright-qa-tester**: UI testing with Playwright
- **parallel-coder**: Coordinating parallel development

**Included Commands**:
- **/bootstrap-plugins**: Auto-configure all plugins for your project
- **/test**: Run tests and display output

**Use Cases**:
- Delegate debugging to specialized agent
- Parallel implementation across files
- Research unfamiliar APIs
- Systematic code exploration

**[Full Documentation →](plugins/development-agents/README.md)**

## Configuration Philosophy

All plugins (except development-agents) support a **layered configuration system**:

```
Project Override (.claude/plugin-name.json)
           ↓
Global Override (~/.config/claude-code/plugin-name.json)
           ↓
Plugin Defaults (config/plugin-name-config.json)
```

### How Configuration Merging Works

1. **Plugin defaults** provide sensible out-of-the-box behavior
2. **Global overrides** customize behavior across all your projects
3. **Project overrides** handle project-specific requirements

**Merge Strategy**:
- Objects: Deep merge (recursive)
- Arrays/Primitives: Complete replacement

**Example**:

```json
// Plugin defaults
{"timeouts": {"pytest": 300000}, "enabled": true}

// Global override
{"timeouts": {"pytest": 600000}}

// Result
{"timeouts": {"pytest": 600000}, "enabled": true}
```

### Environment Variables

Plugins respect environment variables:

- `CLAUDE_CODE_REMOTE`: Skip resource-intensive checks in remote sessions
- `ONESHOT_MODE`: Enable strict validation for CI/CD
- `VIRTUAL_ENV`: Python virtual environment path
- `CLAUDE_PLUGIN_ROOT`: Plugin installation directory (set automatically)

## Plugin Comparison

| Feature | bash-guard | format-and-lint | guardian | development-agents |
|---------|-----------|-----------------|----------|-------------------|
| **Hook Type** | PreToolUse | PostToolUse | PreToolUse + Stop | None |
| **Blocks Execution** | Yes | No | Yes | N/A |
| **Configuration** | Required | Recommended | Recommended | None |
| **Language Support** | Shell | Python/TS/Angular | Language-agnostic | All |
| **Use Case** | Prevention | Quality | Enforcement | Delegation |
| **Performance Impact** | Low | Medium | High | Variable |

## Installation Guide

### Prerequisites

- Claude Code CLI installed
- Git repository (optional, for guardian plugin)
- Development tools installed in your project:
  - Python: ruff, basedpyright (for format-and-lint)
  - Node: prettier, eslint (for format-and-lint)
  - pre-commit (optional, for guardian)

### Step-by-Step Installation

#### 1. Add the Marketplace

For local development:
```bash
/plugin marketplace add /data/ssd/sync/workspace/src/claude-code-plugins
```

For remote repository:
```bash
/plugin marketplace add https://github.com/your-username/claude-code-plugins
```

#### 2. List Available Marketplaces

```bash
/plugin marketplace list
```

You should see `werdnum-plugins` in the list.

#### 3. Browse Plugins

```bash
/plugin
```

Select "Browse Plugins" and choose the "werdnum-plugins" marketplace.

#### 4. Install Desired Plugins

```bash
# Install individually
/plugin install bash-guard@werdnum-plugins

# Or install all
/plugin install bash-guard@werdnum-plugins
/plugin install format-and-lint@werdnum-plugins
/plugin install guardian@werdnum-plugins
/plugin install development-agents@werdnum-plugins
```

#### 5. Verify Installation

```bash
/plugin list
```

You should see all installed plugins with their status (enabled/disabled).

#### 6. Enable/Disable Plugins

```bash
/plugin enable bash-guard
/plugin disable format-and-lint
```

### Uninstalling Plugins

```bash
/plugin uninstall bash-guard@werdnum-plugins
```

## Usage Examples

### Example 1: Bootstrapping Plugin Configuration

**Scenario**: Setting up a new Python project with all plugins

```bash
# After installing plugins
/bootstrap-plugins
```

**Interactive prompts**:
```
Q: Should commits to the main branch be blocked?
A: Enable protection

Q: How strict should test verification be?
A: Strict - Always require tests before commits

Q: Enable LLM code review before commits?
A: Enable code review

Q: How thorough should completion checks be?
A: Strict - Verify formatting, tests, and commits
```

**Result**:
```
✅ Detected Configuration:
   - Language: Python (pytest detected)
   - Test command: pytest
   - Virtual environment: .venv/
   - Pre-commit framework: pre-commit
   - Main branch: main

✅ Files Created/Updated:
   - .claude/settings.json (marketplace + plugins enabled)
   - .claude/bash-guard.json (branch protection + timeouts)
   - .claude/format-lint.json (Python tools enabled)
   - .claude/guardian.json (test verification configured)

✅ All plugins configured and ready to use!
```

### Example 2: Preventing Dangerous Commands

**Scenario**: Prevent accidental deletion of entire filesystem

```bash
# With bash-guard installed
Claude attempts: rm -rf /

# Result: ❌ Blocked
• This command would delete the entire filesystem. Please use a more specific path.
```

### Example 2: Automatic Code Formatting

**Scenario**: Python code formatting after edits

```python
# Before (messy formatting)
def hello( name ):
    print(f"hello {name}")

# Claude edits file with format-and-lint installed
# After (automatically formatted)
def hello(name):
    print(f"hello {name}")
```

**Output**:
```
✅ ruff format (0.3s)
✅ ruff check (0.2s)
✅ basedpyright (1.5s)
```

### Example 3: Test Verification Before Commit

**Scenario**: Attempt to commit without running tests

```bash
# With guardian installed
Claude attempts: git commit -m "Add new feature"

# Result: ❌ Blocked
❌ Tests have not been run since modifying src/feature.py at 2025-10-22T14:30:00
You MUST run 'poe test' before finishing
```

### Example 4: Using Specialized Agents

**Scenario**: Debug an intermittent test failure

```
User: "The test_calendar_sync test fails 30% of the time with a timeout"

Claude: I'll use the systematic-debugger agent to investigate this methodically.

# Launches systematic-debugger agent
# Agent performs hypothesis-driven debugging
# Returns with root cause analysis and fix
```

### Example 5: Project-Specific Configuration

**Scenario**: Custom banned commands for containerized app

Create `.claude/bash-guard.json`:
```json
{
  "bannedCommands": {
    "customPatterns": [
      {
        "regexp": "localhost:3000",
        "explanation": "Use docker-backend:3000 instead. The app runs in a container."
      }
    ]
  }
}
```

Now when Claude tries to use `localhost:3000`, it's blocked with your custom message.

### Example 6: Oneshot Mode for CI/CD

**Scenario**: Strict validation in automated environment

```bash
export ONESHOT_MODE=true

# Claude works on task
# At session end, guardian validates:
# ✓ Git repository initialized
# ✓ On feature branch (not main)
# ✓ All changes committed
# ✓ All commits pushed
# ✓ Tests passing

# Only allows exit when ALL requirements met
```

## Continuous Integration

### Plugin Validation

![Validate Plugins](https://github.com/werdnum/claude-code-plugins/actions/workflows/validate-plugins.yml/badge.svg)

This repository includes automated CI that validates all plugins on every push and pull request.

**What Gets Validated**:
- ✅ Marketplace manifest (`.claude-plugin/marketplace.json`) is valid JSON
- ✅ All plugins listed in the marketplace exist
- ✅ Each plugin passes `claude plugin validate` checks
- ✅ Plugin manifests are well-formed and complete

**Workflow**: [`.github/workflows/validate-plugins.yml`](.github/workflows/validate-plugins.yml)

**When It Runs**:
- Every push to `main`, `master`, or `claude/**` branches
- Every pull request to `main` or `master`

**Local Validation**:
```bash
# Validate a specific plugin
claude plugin validate plugins/bash-guard

# Validate all plugins
for plugin in plugins/*/; do
  echo "Validating $plugin..."
  claude plugin validate "$plugin"
done
```

## Development

### Repository Structure

```
claude-code-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace manifest
├── plugins/
│   ├── bash-guard/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json       # Plugin manifest
│   │   ├── hooks/
│   │   │   └── hooks.json        # Hook definitions
│   │   ├── scripts/              # Hook scripts
│   │   ├── config/               # Default configuration
│   │   └── README.md
│   ├── format-and-lint/
│   ├── guardian/
│   └── development-agents/
├── PLUGIN_PLAN.md                # Implementation plan
├── CLAUDE.md                     # Project instructions
└── README.md                     # This file
```

### Creating a New Plugin

1. **Create directory structure**:
   ```bash
   mkdir -p plugins/my-plugin/{.claude-plugin,hooks,scripts,config}
   ```

2. **Create plugin manifest** (`plugins/my-plugin/.claude-plugin/plugin.json`):
   ```json
   {
     "name": "my-plugin",
     "version": "1.0.0",
     "description": "What this plugin does",
     "author": "Your Name",
     "tags": ["tag1", "tag2"],
     "hooks": "hooks/hooks.json"
   }
   ```

3. **Define hooks** (if applicable) (`plugins/my-plugin/hooks/hooks.json`):
   ```json
   {
     "PreToolUse": [
       {
         "matcher": "Bash",
         "hooks": [
           {
             "type": "command",
             "command": "/usr/bin/env python3 ${CLAUDE_PLUGIN_ROOT}/scripts/my-script.py"
           }
         ]
       }
     ]
   }
   ```

4. **Create hook scripts** in `scripts/` directory

5. **Add default configuration** in `config/` directory

6. **Write comprehensive README.md**

7. **Update marketplace.json**:
   ```json
   {
     "plugins": [
       {
         "name": "my-plugin",
         "path": "plugins/my-plugin",
         "version": "1.0.0",
         "description": "What this plugin does"
       }
     ]
   }
   ```

8. **Test locally**:
   ```bash
   /plugin marketplace update werdnum-plugins
   /plugin install my-plugin@werdnum-plugins
   ```

### Hook Types Reference

- **PreToolUse**: Runs before tool execution (can block)
- **PostToolUse**: Runs after tool execution (informational)
- **Stop**: Runs when user tries to stop session
- **SessionStart**: Runs at session start

### Testing Guidelines

1. **Test with defaults**: Ensure plugin works without configuration
2. **Test with overrides**: Verify configuration merging
3. **Test error handling**: Ensure graceful failures
4. **Test in both projects**: family-assistant and websidian
5. **Test environment variables**: CLAUDE_CODE_REMOTE, ONESHOT_MODE, etc.

## Architecture

### Configuration Loading

All plugins use a common pattern for configuration:

```python
def load_config() -> dict[str, Any]:
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", ...))

    # 1. Load defaults
    config = load_json(plugin_root / "config" / "plugin-config.json")

    # 2. Merge global overrides
    global_config = load_json(Path.home() / ".config" / "claude-code" / "plugin.json")
    config = merge_config(config, global_config)

    # 3. Merge project overrides
    project_config = load_json(Path.cwd() / ".claude" / "plugin.json")
    config = merge_config(config, project_config)

    return config
```

### Hook Execution Flow

```
Tool Call
    ↓
PreToolUse Hooks (in order)
    ↓ (if not blocked)
Tool Execution
    ↓
PostToolUse Hooks (informational)
    ↓
Result Returned
```

### Plugin Interactions

Plugins are designed to work independently but can complement each other:

- **bash-guard** prevents dangerous commands
- **format-and-lint** ensures code quality after edits
- **guardian** enforces testing discipline before commits
- **development-agents** provides specialized capabilities

## Contributing

### Guidelines

1. **Follow existing patterns**: Use the same configuration system
2. **Write comprehensive READMEs**: Include examples and troubleshooting
3. **Make features toggleable**: Everything should be configurable
4. **Provide sensible defaults**: Plugins should work out of the box
5. **Test thoroughly**: In multiple environments and configurations

### Commit Message Format

Write descriptive, detailed commit messages. Explain **what** was done and **why**.

Good example:
```
Add support for custom timeout patterns in bash-guard

Allow users to specify minimum timeouts for custom command patterns
through the configuration file. This enables project-specific timeout
requirements beyond the built-in pytest/poe test patterns.

The implementation uses the same regex matching as banned commands,
making it consistent with existing configuration patterns.
```

## Documentation

- [Claude Code Plugins Guide](https://docs.claude.com/en/docs/claude-code/plugins.md)
- [Plugin Marketplaces Guide](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces.md)
- [Plugin PLAN.md](PLUGIN_PLAN.md) - Original implementation plan

## License

MIT - Personal use

## Acknowledgments

Extracted from real-world usage in:
- **family-assistant**: FastAPI + React application
- **websidian**: Angular application

These plugins represent patterns that proved valuable across multiple projects and are now available for reuse.

