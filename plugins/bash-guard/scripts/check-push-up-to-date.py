#!/usr/bin/env python3
"""
PreToolUse hook to block git push if the branch is not up to date with main.

Ensures feature branches are rebased onto the latest main before pushing,
preventing stale branches from being pushed.
"""

import json
import os
import re
import subprocess
import sys


def get_main_branch() -> str:
    """Determine the main branch name (main or master)."""
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        # refs/remotes/origin/main -> main
        ref = result.stdout.strip()
        return ref.split("/")[-1]

    # Fallback: check if main or master exists
    for branch in ["main", "master"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return branch

    return "main"  # Default to main


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


def extract_push_branch(command: str) -> str | None:
    """
    Extract the branch being pushed to from a git push command.

    Handles common patterns:
    - git push
    - git push origin
    - git push -u origin branch-name
    - git push origin branch-name
    - git push branch-name (shorthand)
    - git push origin branch:remote-branch
    """
    # Check if it's a git push command
    if not re.search(r"\bgit\s+push\b", command):
        return None

    # Skip if pushing to a specific remote ref that's not a branch name
    # e.g., git push origin HEAD:refs/for/main (gerrit)
    if re.search(r"HEAD:refs/", command):
        return None

    # Extract explicit branch from command patterns
    # Pattern 1: git push origin local-branch:remote-branch -> use local-branch
    match = re.search(
        r"\bgit\s+push\s+(?:[-\w]+\s+)*(?:origin\s+)?(\S+):(\S+)",
        command,
    )
    if match:
        local_branch = match.group(1)
        if not local_branch.startswith("-") and local_branch != "HEAD":
            return local_branch

    # Pattern 2: git push [-u] [--set-upstream] [origin] branch-name
    # Remove flags first to simplify parsing
    simplified = re.sub(r"\s+-[a-zA-Z]+(?:\s+\S+)?", " ", command)
    simplified = re.sub(r"\s+--[a-z-]+=\S+", " ", simplified)
    simplified = re.sub(r"\s+--[a-z-]+", " ", simplified)

    # Now parse: git push [remote] [branch]
    match = re.search(r"\bgit\s+push\s*(\S*)\s*(\S*)", simplified)
    if match:
        arg1 = match.group(1).strip()
        arg2 = match.group(2).strip()

        # If arg1 is "origin" or empty, arg2 is the branch
        if arg1 in ("origin", "") and arg2 and not arg2.startswith("-"):
            return arg2

        # If arg1 looks like a branch (not a remote), use it
        if arg1 and not arg2 and arg1 != "origin" and not arg1.startswith("-"):
            # Check if it's actually a known remote
            result = subprocess.run(
                ["git", "remote"],
                capture_output=True,
                text=True,
                check=False,
            )
            remotes = result.stdout.strip().split("\n") if result.returncode == 0 else []
            if arg1 not in remotes:
                return arg1

    # If no explicit branch, it pushes current branch
    return get_current_branch()


def fetch_remote(remote: str = "origin") -> bool:
    """Fetch the latest from remote. Returns True on success."""
    result = subprocess.run(
        ["git", "fetch", remote],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def is_branch_up_to_date_with_main(branch: str, main_branch: str) -> tuple[bool, str]:
    """
    Check if branch contains the latest main branch commit.

    Returns:
        tuple of (is_up_to_date, message)
    """
    # Get the merge base between the branch and main
    result = subprocess.run(
        ["git", "merge-base", branch, f"origin/{main_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Can't determine merge base, allow the push
        return True, ""

    merge_base = result.stdout.strip()

    # Get the latest commit on origin/main
    result = subprocess.run(
        ["git", "rev-parse", f"origin/{main_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return True, ""

    main_head = result.stdout.strip()

    # If merge base equals main head, branch is up to date
    if merge_base == main_head:
        return True, ""

    # Count commits behind
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{merge_base}..origin/{main_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    commits_behind = result.stdout.strip() if result.returncode == 0 else "some"

    return False, f"Branch is {commits_behind} commit(s) behind origin/{main_branch}"


def load_config() -> dict:
    """Load configuration from bash-guard config files."""
    plugin_root = os.environ.get(
        "CLAUDE_PLUGIN_ROOT",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    config_locations = [
        os.path.join(plugin_root, "config", "bash-guard-config.json"),
        os.path.expanduser("~/.config/claude-code/bash-guard.json"),
        os.path.join(os.getcwd(), ".claude", "bash-guard.json"),
    ]

    config = {}
    for config_path in config_locations:
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    layer_config = json.load(f)
                    # Simple merge for our purposes
                    config.update(layer_config)
            except (FileNotFoundError, json.JSONDecodeError):
                continue

    return config


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

    # Load config to check if this check is enabled
    config = load_config()
    push_config = config.get("push_up_to_date_check", {})
    if not push_config.get("enabled", True):
        sys.exit(0)

    # Extract the branch being pushed
    branch = extract_push_branch(command)
    if not branch:
        sys.exit(0)

    # Get the main branch name
    main_branch = get_main_branch()

    # Don't check if pushing main itself
    if branch in (main_branch, f"origin/{main_branch}"):
        sys.exit(0)

    # Fetch to get latest state
    print(f"Fetching latest from origin to check if '{branch}' is up to date with '{main_branch}'...", file=sys.stderr)
    if not fetch_remote():
        # If fetch fails, allow the push (network issues shouldn't block work)
        print("Warning: Could not fetch from origin, skipping up-to-date check", file=sys.stderr)
        sys.exit(0)

    # Check if branch is up to date with main
    is_up_to_date, message = is_branch_up_to_date_with_main(branch, main_branch)

    if not is_up_to_date:
        print(f"BLOCKED: {message}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Your branch '{branch}' is not up to date with '{main_branch}'.", file=sys.stderr)
        print("Please rebase or merge before pushing:", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  git fetch origin", file=sys.stderr)
        print(f"  git rebase origin/{main_branch}", file=sys.stderr)
        print("  # or: git merge origin/{main_branch}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Then try pushing again.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
