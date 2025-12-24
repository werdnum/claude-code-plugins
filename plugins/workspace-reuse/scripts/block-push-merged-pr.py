#!/usr/bin/env python3
"""
PreToolUse hook to block git push to branches that have merged PRs.

Checks if a git push command is targeting a branch with a merged PR,
and blocks it with instructions to create a new branch.
"""

import json
import re
import subprocess
import sys


def get_current_branch() -> str | None:
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def check_branch_has_merged_pr(branch: str) -> bool:
    """Check if the branch has a corresponding merged PR using gh cli."""
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "merged",
            "--json",
            "number",
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False

    try:
        prs = json.loads(result.stdout)
        return len(prs) > 0
    except json.JSONDecodeError:
        return False


def extract_push_branch(command: str) -> str | None:
    """Extract the branch being pushed to from a git push command."""
    # Pattern: git push [-u] [origin] [branch]
    # Also handles: git push origin branch:branch

    # Check if it's a git push command
    if not re.search(r"\bgit\s+push\b", command):
        return None

    # Try to extract explicit branch from command
    # Pattern: git push origin branch-name
    match = re.search(r"\bgit\s+push\s+(?:-[^\s]+\s+)*(?:origin\s+)?([^\s:]+)", command)
    if match:
        branch = match.group(1)
        # Filter out flags
        if not branch.startswith("-"):
            return branch

    # If no explicit branch, it pushes current branch
    return get_current_branch()


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

    # Only check Bash tool calls with git push commands
    if tool_name != "Bash" or not command:
        sys.exit(0)

    # Check if this is a git push command
    if not re.search(r"\bgit\s+push\b", command):
        sys.exit(0)

    # Extract the branch being pushed
    branch = extract_push_branch(command)
    if not branch:
        sys.exit(0)

    # Check if this branch has a merged PR
    if check_branch_has_merged_pr(branch):
        print(f"BLOCKED: Cannot push to branch '{branch}' - it has a merged PR.", file=sys.stderr)
        print("", file=sys.stderr)
        print("The PR for this branch has already been merged.", file=sys.stderr)
        print("Please create a new branch for your changes:", file=sys.stderr)
        print("", file=sys.stderr)
        print("  git checkout main && git pull", file=sys.stderr)
        print("  git checkout -b new-feature-branch", file=sys.stderr)
        print("  # ... make your changes ...", file=sys.stderr)
        print("  git push -u origin new-feature-branch", file=sys.stderr)
        print("  gh pr create", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
