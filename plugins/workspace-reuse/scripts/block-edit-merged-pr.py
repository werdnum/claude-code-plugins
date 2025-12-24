#!/usr/bin/env python3
"""
PreToolUse hook to block editing PRs that are already merged.

Intercepts gh pr edit commands and checks if the PR is merged before allowing.
"""

import json
import re
import subprocess
import sys


def get_pr_state(pr_identifier: str) -> str | None:
    """Get the state of a PR (open, closed, merged)."""
    result = subprocess.run(
        ["gh", "pr", "view", pr_identifier, "--json", "state"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
        return data.get("state", "").upper()
    except json.JSONDecodeError:
        return None


def extract_pr_identifier(command: str) -> str | None:
    """Extract PR number or branch from a gh pr edit command."""
    # Pattern: gh pr edit [number|branch|url]
    # Also handles: gh pr edit (current branch)

    if not re.search(r"\bgh\s+pr\s+edit\b", command):
        return None

    # Try to extract PR number
    match = re.search(r"\bgh\s+pr\s+edit\s+(\d+)", command)
    if match:
        return match.group(1)

    # Try to extract branch name or URL
    match = re.search(r"\bgh\s+pr\s+edit\s+([^\s]+)", command)
    if match:
        identifier = match.group(1)
        if not identifier.startswith("-"):
            return identifier

    # No explicit identifier means current branch
    return None  # Will use current branch context


def main() -> None:
    """Main entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check Bash tool calls with gh pr edit commands
    if tool_name != "Bash" or not command:
        sys.exit(0)

    # Check if this is a gh pr edit command
    if not re.search(r"\bgh\s+pr\s+edit\b", command):
        sys.exit(0)

    # Extract PR identifier (or use current branch context)
    pr_identifier = extract_pr_identifier(command)

    # Check PR state - if no identifier, gh will use current branch
    if pr_identifier:
        state = get_pr_state(pr_identifier)
    else:
        # Use current branch context for gh pr view
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "state"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            # No PR associated with current branch
            sys.exit(0)
        try:
            data = json.loads(result.stdout)
            state = data.get("state", "").upper()
        except json.JSONDecodeError:
            sys.exit(0)

    if state == "MERGED":
        print("BLOCKED: Cannot edit a merged PR.", file=sys.stderr)
        print("", file=sys.stderr)
        print("This PR has already been merged and cannot be modified.", file=sys.stderr)
        print("If you need to make additional changes, please:", file=sys.stderr)
        print("", file=sys.stderr)
        print("  1. Create a new branch from main", file=sys.stderr)
        print("  2. Make your changes", file=sys.stderr)
        print("  3. Create a new PR", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
