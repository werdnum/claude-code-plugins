#!/usr/bin/env python3
"""
PreToolHook script to check Bash commands against banned patterns and enforce minimum timeouts.
Reads input from stdin and returns 0 to allow, 2 to block with message.
"""

import json
import os
import re
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
                # Deep merge global config into default config
                config = merge_config(config, global_config)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # Load project overrides if they exist
    project_config_path = Path.cwd() / ".claude" / "bash-guard.json"
    if project_config_path.exists():
        try:
            with open(project_config_path, encoding="utf-8") as f:
                project_config = json.load(f)
                # Deep merge project config into merged config
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


def check_banned_commands(command: str, config: dict[str, Any]) -> tuple[bool, str]:
    """Check if command matches any banned patterns."""
    banned_config = config.get("bannedCommands", {})

    if not banned_config.get("enabled", True):
        return False, ""

    # Check built-in patterns
    patterns = banned_config.get("patterns", [])
    for pattern_config in patterns:
        pattern = pattern_config.get("regexp", "")
        explanation = pattern_config.get("explanation", "This command is not allowed.")

        try:
            if re.search(pattern, command):
                return True, explanation
        except re.error:
            # Skip invalid patterns
            continue

    # Check custom patterns
    custom_patterns = banned_config.get("customPatterns", [])
    for pattern_config in custom_patterns:
        pattern = pattern_config.get("regexp", "")
        explanation = pattern_config.get("explanation", "This command is not allowed.")

        try:
            if re.search(pattern, command):
                return True, explanation
        except re.error:
            continue

    return False, ""


def check_background_restrictions(command: str, run_in_background: bool, config: dict[str, Any]) -> tuple[bool, str]:
    """Check if command is allowed to run in background."""
    if not run_in_background:
        return False, ""

    banned_in_bg = config.get("bannedInBackground", [])
    for pattern in banned_in_bg:
        try:
            if re.search(pattern, command):
                return True, f"'{pattern}' must NOT be run in the background. Always run it in the foreground."
        except re.error:
            continue

    return False, ""


def check_timeout_requirements(command: str, timeout: int | None, config: dict[str, Any]) -> tuple[bool, str]:
    """Check if command meets minimum timeout requirements."""
    timeouts_config = config.get("timeouts", {})
    minimums = timeouts_config.get("minimums", {})
    default_timeout = timeouts_config.get("defaults", {}).get("bash", 120000)

    # Get default timeout from environment variable or config
    timeout_str = os.environ.get("BASH_DEFAULT_TIMEOUT_MS", str(default_timeout))
    try:
        default_timeout_ms = int(timeout_str)
    except ValueError:
        default_timeout_ms = default_timeout

    for pattern, min_timeout_ms in minimums.items():
        try:
            if re.search(pattern, command):
                current_timeout_ms = timeout if timeout is not None else default_timeout_ms

                if current_timeout_ms < min_timeout_ms:
                    min_timeout_minutes = min_timeout_ms / 60000
                    current_timeout_minutes = current_timeout_ms / 60000 if current_timeout_ms > 0 else 0

                    cleaned_pattern = pattern.replace("\\b", "")
                    message = f"Command '{cleaned_pattern}' requires a minimum timeout of {min_timeout_minutes:.0f} minutes. "

                    if timeout is None:
                        message += f"No timeout was specified, using default timeout of {(current_timeout_ms / 60000):.1f} minutes. Please add 'timeout: {min_timeout_ms}' to your Bash tool call."
                    else:
                        message += f"Current timeout is {current_timeout_minutes:.1f} minutes. Please increase it to at least {min_timeout_ms}."

                    return True, message
        except re.error:
            continue

    return False, ""


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
    timeout = tool_input.get("timeout")
    run_in_background = tool_input.get("run_in_background", False)

    # Only check Bash tool calls with commands
    if tool_name != "Bash" or not command:
        sys.exit(0)

    # Load configuration
    config = load_config()
    if not config:
        # Allow command if we can't load configuration
        sys.exit(0)

    # Check banned commands
    is_banned, explanation = check_banned_commands(command, config)
    if is_banned:
        print(f"• {explanation}", file=sys.stderr)
        sys.exit(2)

    # Check background restrictions
    is_restricted, message = check_background_restrictions(command, run_in_background, config)
    if is_restricted:
        print(f"• {message}", file=sys.stderr)
        sys.exit(2)

    # Check timeout requirements
    needs_timeout, message = check_timeout_requirements(command, timeout, config)
    if needs_timeout:
        print(f"• {message}", file=sys.stderr)
        sys.exit(2)

    # Command is allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
