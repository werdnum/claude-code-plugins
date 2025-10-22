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

Plugins will be added to the `plugins/` directory. Browse available plugins using:

```bash
/plugin
```

Then select "Browse Plugins" and choose this marketplace.

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
