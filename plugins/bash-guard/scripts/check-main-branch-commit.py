#!/usr/bin/env python3
"""
PreToolHook script to prevent commits on protected branches (main/master).
Reads input from stdin and returns 0 to allow, 2 to block with message.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_config() -> dict[str, Any]:
    """Load configuration with layered override support."""
    # Get plugin root from environment
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))

    # Load default configuration
    default_config_path = plugin_root / "config" / "bash-guard-config.json"
    try:
        with open(default_config_path, encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading default config from {default_config_path}: {e}", file=sys.stderr)
        return {}

    # Load global overrides if they exist
    global_config_path = Path.home() / ".config" / "claude-code" / "bash-guard.json"
    if global_config_path.exists():
        try:
            with open(global_config_path, encoding="utf-8") as f:
                global_config = json.load(f)
                config = merge_config(config, global_config)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # Load project overrides if they exist
    project_config_path = Path.cwd() / ".claude" / "bash-guard.json"
    if project_config_path.exists():
        try:
            with open(project_config_path, encoding="utf-8") as f:
                project_config = json.load(f)
                config = merge_config(config, project_config)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return config


def merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two configuration dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result


def main() -> None:
    """Main entry point."""
    # Read the hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check Bash tool calls with git commit commands
    if tool_name != "Bash" or not command:
        sys.exit(0)

    # Check if this is a git commit command (but not with --no-verify)
    if not re.search(r"\bgit\s+commit\b", command) or "--no-verify" in command:
        sys.exit(0)

    # Load configuration
    config = load_config()
    protection_config = config.get("mainBranchProtection", {})

    # Check if protection is enabled
    if not protection_config.get("enabled", True):
        sys.exit(0)

    # Get protected branches list
    protected_branches = protection_config.get("protectedBranches", ["main", "master"])

    # Get the current branch
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        check=False,
    )

    # Check if the command succeeded
    if result.returncode != 0:
        # If we can't determine the branch, allow the commit
        print(
            f"Warning: Could not determine current branch: {result.stderr}", file=sys.stderr
        )
        sys.exit(0)

    current_branch = result.stdout.strip()

    # Check if we're on a protected branch
    if current_branch in protected_branches:
        print(
            f"• You're currently on the '{current_branch}' branch. Direct commits to protected branches are not allowed.",
            file=sys.stderr,
        )
        print(
            "• Please create a feature branch first: git checkout -b feature-name",
            file=sys.stderr,
        )
        print(
            "• Then you can commit your changes and create a pull request.", file=sys.stderr
        )
        sys.exit(2)

    # Allow commits on non-protected branches
    sys.exit(0)


if __name__ == "__main__":
    main()
