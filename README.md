# Claude Code Plugins

Personal collection of miscellaneous Claude Code plugins for development workflows.

## About

This repository serves as a local plugin marketplace for Claude Code, containing custom plugins that extend functionality with commands, agents, hooks, and MCP server integrations.

## Installation

Add this marketplace to your Claude Code instance:

```bash
/plugin marketplace add /data/ssd/sync/workspace/src/claude-code-plugins
```

Or if using a git remote:

```bash
/plugin marketplace add https://github.com/your-username/claude-code-plugins
```

## Available Plugins

### bash-guard

Safety checks for Bash commands - prevents dangerous operations, enforces timeouts, and blocks commits to main branch.

```bash
/plugin install bash-guard@claude-code-plugins
```

**Features**: Banned command patterns, main branch protection, timeout enforcement, background restrictions

### format-and-lint

Auto-format and lint files after edits with support for Python, TypeScript, and Angular.

```bash
/plugin install format-and-lint@claude-code-plugins
```

**Features**: File formatting, Python linting (ruff, basedpyright, ast-grep), TypeScript/Angular linting (prettier, eslint)

### guardian

Test verification, pre-commit review workflow, and stop validation to ensure code quality.

```bash
/plugin install guardian@claude-code-plugins
```

**Features**: Test verification hooks, pre-commit review workflow, stop validation with oneshot mode support

### development-agents

Collection of specialized development agents and commands for common workflows.

```bash
/plugin install development-agents@claude-code-plugins
```

**Includes**: systematic-debugger, focused-coder, mechanical-coder, codebase-researcher, external-research-specialist, playwright-qa-tester, parallel-coder agents, plus /test command

## Browse Plugins

Use the Claude Code plugin browser:

```bash
/plugin
```

Then select "Browse Plugins" and choose the "claude-code-plugins" marketplace.

## Development

### Creating a New Plugin

1. Create a new directory in `plugins/`:
   ```bash
   mkdir -p plugins/my-plugin/.claude-plugin
   ```

2. Create the plugin manifest `plugins/my-plugin/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "my-plugin",
     "description": "Description of what this plugin does",
     "version": "1.0.0",
     "author": "Your Name"
   }
   ```

3. Add functionality (commands, agents, skills, or hooks)

4. Update `.claude-plugin/marketplace.json` to include your plugin

5. Test locally by reinstalling the marketplace

### Plugin Structure

Each plugin should follow this structure:

```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json        # Required: plugin metadata
├── commands/              # Optional: slash commands (.md files)
├── agents/                # Optional: agent definitions
├── skills/                # Optional: agent skills
└── hooks/                 # Optional: event handlers
```

## Documentation

- [Claude Code Plugins Guide](https://docs.claude.com/en/docs/claude-code/plugins.md)
- [Plugin Marketplaces Guide](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces.md)

## License

MIT
