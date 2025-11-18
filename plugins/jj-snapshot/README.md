# jj-snapshot Plugin

Automatically snapshot repository state with Jujutsu (jj) after each file edit in Claude Code.

## Overview

This plugin runs `jj status` silently after every file edit operation (Edit, Write, or NotebookEdit). Since Jujutsu automatically creates snapshots when the working copy changes, running `jj status` ensures that the current repository state is captured and tracked in jj's operation log.

## Features

- **Automatic Snapshots**: Runs `jj status` after each file edit to snapshot the repo state
- **Silent Operation**: Runs completely in the background without interrupting Claude Code workflow
- **Safe Fallback**: Gracefully handles cases where jj is not installed or the directory is not a jj repository
- **Zero Configuration**: Works out of the box with no setup required

## How It Works

The plugin uses a PostToolUse hook that triggers after Edit, Write, or NotebookEdit operations. When triggered, it:

1. Checks if jj is installed on the system
2. Verifies the current directory is inside a jj repository
3. Runs `jj status` silently to create a snapshot
4. Exits without producing any output

## Installation

Install this plugin from the claude-code-plugins marketplace:

```bash
/plugin install jj-snapshot@claude-code-plugins
```

## Requirements

- [Jujutsu (jj)](https://github.com/martinvonz/jj) version control system installed
- Working within a jj repository

If jj is not installed or you're not in a jj repository, the plugin will silently do nothing.

## Benefits

- **Version History**: Every file edit is automatically captured in jj's operation log
- **Easy Rollback**: Use `jj op log` to see all changes and `jj op undo` to roll back if needed
- **Complete Audit Trail**: Track exactly what changes Claude Code made and when
- **No Manual Snapshots**: Never forget to snapshot your work again

## Technical Details

- **Hook Type**: PostToolUse
- **Trigger Tools**: Edit, Write, NotebookEdit
- **Timeout**: 5 seconds
- **Script**: `/scripts/snapshot.sh`

## Example Workflow

1. Claude Code edits a file using the Edit tool
2. The jj-snapshot hook triggers automatically
3. `jj status` runs silently in the background
4. jj creates a snapshot of the current state
5. You continue working without interruption

Later, you can view the complete history:

```bash
jj op log
```

And undo changes if needed:

```bash
jj op undo
```

## Compatibility

Works with all jj repositories and is compatible with other Claude Code plugins.

## Author

Andrew Garrett (andrewgarrett@google.com)
