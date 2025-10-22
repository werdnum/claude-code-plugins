# Claude Code Plugins Repository

This repository contains miscellaneous Claude Code plugins for personal development use.

## About This Repository

This is a personal plugin marketplace for Claude Code extensions. Plugins extend Claude Code with custom functionality including commands, agents, hooks, and MCP servers.

## Repository Structure

```
claude-code-plugins/
├── .claude-plugin/
│   └── marketplace.json      # Marketplace configuration
├── plugins/                  # Individual plugin directories
│   └── [plugin-name]/
│       ├── .claude-plugin/
│       │   └── plugin.json  # Plugin metadata
│       ├── commands/        # Slash commands (optional)
│       ├── agents/          # Agent definitions (optional)
│       ├── skills/          # Agent Skills (optional)
│       └── hooks/           # Event handlers (optional)
└── CLAUDE.md               # This file

```

## Plugin Development

Each plugin follows a standard structure with a manifest file (`.claude-plugin/plugin.json`) and optional component directories for commands, agents, skills, and hooks.

### Creating a New Plugin

1. Create a new directory under `plugins/`
2. Add `.claude-plugin/plugin.json` with metadata
3. Add functionality in appropriate directories (commands/, agents/, skills/, hooks/)
4. Update `.claude-plugin/marketplace.json` to include the new plugin
5. Test locally before committing

### Testing Plugins

Install this local marketplace in Claude Code:
```
/plugin marketplace add /data/ssd/sync/workspace/src/claude-code-plugins
```

Then install plugins from this marketplace:
```
/plugin install plugin-name@claude-code-plugins
```

## Documentation

- **Plugins Guide**: https://docs.claude.com/en/docs/claude-code/plugins.md
- **Plugin Marketplaces**: https://docs.claude.com/en/docs/claude-code/plugin-marketplaces.md

## Key Concepts

- **Plugins**: Extend Claude Code with custom functionality (commands, agents, hooks, MCP servers)
- **Marketplace**: A catalog of available plugins with centralized discovery and version management
- **Commands**: Custom slash commands defined in markdown files
- **Agents**: Autonomous model-invoked tools for specialized tasks
- **Skills**: Model-invoked tools that Claude uses contextually
- **Hooks**: Event handlers that respond to specific Claude Code events

## Plugin Management Commands

- Browse and install: `/plugin`
- Install specific plugin: `/plugin install plugin-name@marketplace-name`
- List installed: `/plugin list`
- Enable/disable: `/plugin enable plugin-name` or `/plugin disable plugin-name`
- Uninstall: `/plugin uninstall plugin-name@marketplace-name`
- Validate plugin: `claude plugin validate path/to/plugin`

## Marketplace Management

- List marketplaces: `/plugin marketplace list`
- Update marketplace: `/plugin marketplace update marketplace-name`
- Remove marketplace: `/plugin marketplace remove marketplace-name`

## Development Practices

### Commit Messages

Write descriptive, detailed, and comprehensive commit messages. Conventional commit prefixes (feat:, fix:, etc.) should only be used if they add clarity to the message.

A good commit message should:
- Explain **what** was done in detail
- Most importantly, explain **why** the changes were made
- Provide context about the problem being solved or feature being added
- Be clear enough that someone reading the history can understand the reasoning
- Include relevant details about implementation decisions when applicable

Example of a good commit message:
```
Add marketplace configuration and initial repository structure

Initialize the repository with the essential files needed for a Claude Code
plugin marketplace. This includes the marketplace.json manifest that defines
available plugins, a comprehensive CLAUDE.md with development guidelines and
documentation links, and a README for general repository information.

The marketplace.json starts empty but provides the foundation for adding
plugins. The documentation includes links to official Claude Code plugin
guides to ensure consistent development practices.
```
