# format-and-lint

Auto-format and lint files after edits with support for Python, TypeScript/JavaScript, and Angular projects.

## Features

- **File Formatting**: Ensure newline at EOF, trim trailing whitespace (configurable)
- **Python Linting**: ruff (format + check), basedpyright, ast-grep conformance/hints
- **TypeScript Linting**: prettier, eslint (for `frontend/` directory)
- **Angular Linting**: prettier, eslint (for `app/` directory)
- **Informational Only**: PostToolUse hooks don't block - they provide feedback

All features are individually toggleable via configuration.

## Installation

```bash
/plugin install format-and-lint@claude-code-plugins
```

## Quick Start

Works out of the box for Python projects. Configure for TypeScript/Angular as needed.

## Configuration

Layered configuration system: Project → Global → Defaults

### Python Configuration

Create `.claude/format-lint.json`:

```json
{
  "linting": {
    "python": {
      "enabled": true,
      "venvPath": "${VIRTUAL_ENV:-.venv}",
      "tools": {
        "ruff-format": { "enabled": true, "timeout": 5000 },
        "ruff-check": { "enabled": true, "showDiff": true },
        "basedpyright": { "enabled": true, "maxErrorsShown": 5 },
        "ast-grep-hints": { "enabled": true, "filterMode": "new-code-only" }
      }
    }
  }
}
```

### TypeScript Configuration

For React/Next.js projects with `frontend/` directory:

```json
{
  "linting": {
    "typescript": {
      "enabled": true,
      "projectDir": "frontend",
      "tools": {
        "prettier": { "enabled": true, "npmScript": "format" },
        "eslint": { "enabled": true, "npmScript": "lint:fix" }
      }
    }
  }
}
```

### Angular Configuration

For Angular projects with `app/` directory:

```json
{
  "linting": {
    "angular": {
      "enabled": true,
      "projectDir": "app",
      "tools": {
        "prettier": { "enabled": true },
        "eslint": { "enabled": true }
      }
    }
  }
}
```

### Formatting Configuration

```json
{
  "formatting": {
    "enabled": true,
    "formatters": {
      "ensure_newline": {
        "enabled": true,
        "patterns": ["*.py", "*.js", "*.ts", "*.md"],
        "command": "sed -i -e '${ /./s/$/\\n/ }' {}"
      }
    },
    "exclude": ["*.min.js", "dist/*", "node_modules/*"]
  }
}
```

## Filter Modes for ast-grep-hints

- `all`: Show all hints
- `new-code-only`: (default) Only show hints in newly added code (Edit tool)
- `new-files-only`: Only show hints in new files (Write tool)

## Timeouts

All timeouts in milliseconds:
- ruff-format: 5000ms (5 seconds)
- ruff-check: 2000ms (2 seconds)
- basedpyright: 8000ms (8 seconds)
- ast-grep: 2000ms (2 seconds)
- prettier/eslint: 5000-8000ms

## Disabling Features

Disable entire categories or specific tools:

```json
{
  "formatting": { "enabled": false },
  "linting": {
    "python": {
      "tools": {
        "basedpyright": { "enabled": false }
      }
    }
  }
}
```

## How It Works

Registers a PostToolUse hook that runs after Edit, Write, or NotebookEdit operations:

1. **Formatting**: Runs configured formatters based on file patterns
2. **Linting**: Runs appropriate linters based on file type and project structure
3. **Feedback**: Provides informational output (doesn't block operations)

## Virtual Environment

Python tools use `venvPath` configuration. Default: `${VIRTUAL_ENV:-.venv}`

The `${VIRTUAL_ENV:-.venv}` syntax means: use VIRTUAL_ENV environment variable if set, otherwise use `.venv`.

## Troubleshooting

**Linters not running**: Check that tools are installed in your virtual environment or node_modules

**Wrong project directory**: Override `projectDir` in configuration

**Too slow**: Disable expensive linters or increase timeouts

**ast-grep not found**: Set correct `scriptPath` or disable ast-grep tools
