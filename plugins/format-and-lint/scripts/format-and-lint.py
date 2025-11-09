#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
PostToolUse hook for formatting and linting files after edits.
Supports Python, TypeScript, JavaScript, Angular, HTML, and CSS files.
"""

import asyncio
import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Any

# Import linter modules
sys.path.insert(0, str(Path(__file__).parent))
from linters import python, typescript, angular


def load_config() -> dict[str, Any]:
    """Load configuration with layered override support."""
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))

    # Load default configuration
    default_config_path = plugin_root / "config" / "format-lint-config.json"
    try:
        with open(default_config_path, encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading default config: {e}", file=sys.stderr)
        return {}

    # Load global overrides
    global_config_path = Path.home() / ".config" / "claude-code" / "format-lint.json"
    if global_config_path.exists():
        try:
            with open(global_config_path, encoding="utf-8") as f:
                global_config = json.load(f)
                config = merge_config(config, global_config)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # Load project overrides
    project_config_path = Path.cwd() / ".claude" / "format-lint.json"
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


def should_exclude(file_path: str, exclude_patterns: list[str]) -> bool:
    """Check if file should be excluded from processing."""
    return any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns)


async def run_formatters(file_path: str, config: dict[str, Any]) -> None:
    """Run configured formatters on the file."""
    formatting_config = config.get("formatting", {})

    if not formatting_config.get("enabled", True):
        return

    exclude_patterns = formatting_config.get("exclude", [])
    if should_exclude(file_path, exclude_patterns):
        return

    formatters = formatting_config.get("formatters", {})

    for formatter_name, formatter_config in formatters.items():
        if not formatter_config.get("enabled", True):
            continue

        patterns = formatter_config.get("patterns", [])
        file_name = os.path.basename(file_path)

        if any(fnmatch.fnmatch(file_name, pattern) for pattern in patterns):
            command = formatter_config.get("command", "")
            if command and os.path.exists(file_path):
                # Replace {} placeholder with file path
                cmd = command.replace("{}", file_path)

                # Execute formatter
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()


async def run_linters(file_path: str, tool_name: str, tool_input: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    """Run appropriate linters based on file type."""
    linting_config = config.get("linting", {})

    if not linting_config.get("enabled", True):
        return None

    file_ext = Path(file_path).suffix.lower()

    # Determine which linter to use
    if file_ext == ".py":
        python_config = linting_config.get("python", {})
        if python_config.get("enabled", True):
            return await python.lint_file(file_path, tool_name, tool_input, python_config)

    elif file_ext in {".js", ".jsx", ".ts", ".tsx"}:
        # Check if this is TypeScript or Angular
        typescript_config = linting_config.get("typescript", {})
        angular_config = linting_config.get("angular", {})

        # Try Angular first if enabled and file is in app directory
        if angular_config.get("enabled", False):
            project_dir = angular_config.get("projectDir", "app")
            if str(Path(file_path)).startswith(str(Path.cwd() / project_dir)):
                return await angular.lint_file(file_path, tool_name, tool_input, angular_config)

        # Fall back to TypeScript
        if typescript_config.get("enabled", True):
            return await typescript.lint_file(file_path, tool_name, tool_input, typescript_config)

    elif file_ext in {".html", ".css", ".scss"}:
        # HTML/CSS can be Angular or standalone
        angular_config = linting_config.get("angular", {})
        if angular_config.get("enabled", False):
            project_dir = angular_config.get("projectDir", "app")
            if str(Path(file_path)).startswith(str(Path.cwd() / project_dir)):
                return await angular.lint_file(file_path, tool_name, tool_input, angular_config)

    return None


async def main() -> None:
    """Main entry point."""
    try:
        # Read tool data from stdin
        tool_data = json.loads(sys.stdin.read())

        tool_name = tool_data.get("tool_name", "")
        tool_input = tool_data.get("tool_input", {})

        # Only process file editing tools
        if tool_name not in {"Edit", "Write", "NotebookEdit"}:
            return

        # Extract file path
        file_path = tool_input.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return

        # Load configuration
        config = load_config()
        if not config:
            return

        # Run formatters first
        await run_formatters(file_path, config)

        # Run linters
        lint_result = await run_linters(file_path, tool_name, tool_input, config)

        # Output lint results if any
        if lint_result:
            print(json.dumps(lint_result))

    except Exception as e:
        # Log error but don't block the tool
        error_output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"Format/lint hook error: {str(e)}",
            }
        }
        print(json.dumps(error_output))


if __name__ == "__main__":
    asyncio.run(main())
