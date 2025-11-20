# Linter Ignore Guard Plugin

A Claude Code plugin that discourages silencing linter warnings without proper justification.

## Overview

This plugin monitors file edits and writes to detect when linter ignore comments are added (such as `type: ignore`, `noqa`, `eslint-disable`, `ast-grep-ignore`, etc.). When detected, it provides educational feedback encouraging developers to:

1. **Fix the underlying issue** (always preferred)
2. **Add clear justification** if suppression is truly necessary

## Features

- **Multi-language support**: Detects ignore patterns across Python, TypeScript/JavaScript, Rust, Go, Ruby, Java, and more
- **Justification detection**: Differentiates between justified and unjustified ignore comments
- **Educational feedback**: Provides helpful guidance on when and how to use ignore comments appropriately
- **Non-blocking**: Warnings are informational and won't prevent edits

## Detected Patterns

The plugin detects common linter ignore patterns including:

### Python
- `# type: ignore` (mypy/pyright)
- `# noqa` (flake8/ruff)
- `# pylint: disable`
- `# fmt: off` / `# fmt: skip` (black/yapf)

### JavaScript/TypeScript
- `// @ts-ignore`
- `// @ts-expect-error`
- `// @ts-nocheck`
- `// eslint-disable`
- `/* eslint-disable */`
- `// prettier-ignore`

### Other Languages
- `// ast-grep-ignore` (ast-grep)
- `#[allow(` (Rust)
- `// nolint` (Go)
- `# rubocop:disable` (Ruby)
- `@SuppressWarnings` (Java)

## How It Works

The plugin uses a PostToolUse hook that triggers after `Edit` or `Write` tool calls. It:

1. Scans the modified content for linter ignore patterns
2. Checks if each ignore comment has a justification
3. Displays appropriate feedback based on what was found

### Justification Detection

The plugin considers an ignore comment "justified" if it contains keywords like:
- `because`, `reason:`, `justification:`
- `todo:`, `fixme:`, `note:`
- `workaround`, `temporary`, `legacy`
- `third-party`, `external`, `issue:`, `bug:`

## Examples

### Unjustified Ignore (Discouraged)
```python
result = unsafe_operation()  # type: ignore
```

**Warning**: This will trigger a strong warning message encouraging you to either fix the type error or add a justification.

### Justified Ignore (Acceptable)
```python
# type: ignore  # Third-party library has incomplete type stubs, tracked in issue #123
result = unsafe_operation()
```

**Response**: Gentle reminder shown, acknowledging the justification.

### Better Solution (Preferred)
```python
# Fix the underlying type issue instead of suppressing the warning
result: Expected[Type] = unsafe_operation()
```

**Response**: No warning - the proper solution!

## Installation

### From Local Marketplace

1. Add this marketplace to Claude Code:
   ```
   /plugin marketplace add /path/to/claude-code-plugins
   ```

2. Install the plugin:
   ```
   /plugin install linter-ignore-guard@claude-code-plugins
   ```

3. The plugin is automatically enabled after installation

## Configuration

Currently, the plugin has no configuration options. It runs automatically on all file edits and writes.

Future versions may add:
- Ability to exclude specific patterns or file types
- Custom justification keywords
- Severity levels

## Philosophy

This plugin embodies the principle that **linter warnings exist for a reason**. They help catch bugs, enforce best practices, and maintain code quality. Silencing them should be a last resort, not a first response.

When you encounter a linter warning:
1. **Understand why the warning exists** - Read the documentation
2. **Fix the underlying issue** - This is almost always possible
3. **Only suppress if truly necessary** - And always explain why

## Development

### Structure
```
linter-ignore-guard/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── hooks/
│   └── hooks.json               # Hook configuration
├── scripts/
│   └── check-linter-ignores.py  # Main detection script
└── README.md                    # This file
```

### Testing

To test changes locally:
1. Update the marketplace: `/plugin marketplace update claude-code-plugins`
2. Reinstall the plugin: `/plugin uninstall linter-ignore-guard@claude-code-plugins && /plugin install linter-ignore-guard@claude-code-plugins`
3. Make an edit with an ignore comment to trigger the hook

## Contributing

Contributions are welcome! Please ensure:
- New ignore patterns are added to the `IGNORE_PATTERNS` list in `check-linter-ignores.py`
- Documentation is updated to reflect new patterns
- The spirit of encouraging proper fixes over suppressions is maintained

## License

Part of the claude-code-plugins personal plugin collection.

## See Also

- [format-and-lint plugin](../format-and-lint/) - Automatic formatting and linting
- [Claude Code Plugins Guide](https://docs.claude.com/en/docs/claude-code/plugins.md)
- [Claude Code Hooks Documentation](https://docs.claude.com/en/docs/claude-code/hooks.md)
