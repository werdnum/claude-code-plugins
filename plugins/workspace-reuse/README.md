# Workspace Reuse Plugin

Manage workspace state for seamless reuse between tasks. This plugin automatically handles branch management to help you quickly move between completed and new work.

## Features

### Session Start Behavior

When starting a new Claude Code session:

1. **On a branch with merged PR**: Automatically switches to main/master and pulls latest changes, notifying both user and agent
2. **On a feature branch (no merged PR)**: Runs `git fetch` and shows `git status` to the agent
3. **On main/master**: Automatically runs `git pull` to get latest changes

### Post-Prompt Check

After each prompt submission, checks if you're on a branch with a merged PR and automatically switches to main if so.

### Push Protection

Blocks `git push` commands to branches that have merged PRs, with instructions to create a new branch and PR.

### PR Edit Protection

Blocks `gh pr edit` commands for PRs that are already merged.

## Hook Events

| Event | Behavior |
|-------|----------|
| `SessionStart` | Branch detection, auto-switch from merged PRs, fetch/pull |
| `UserPromptSubmit` | Check for merged PR branch and switch if needed |
| `PreToolUse` (Bash) | Block push to merged PR branches |
| `PreToolUse` (Bash) | Block editing merged PRs |

## Requirements

- Git repository
- GitHub CLI (`gh`) installed and authenticated

## Installation

```
/plugin install workspace-reuse@claude-code-plugins
```
