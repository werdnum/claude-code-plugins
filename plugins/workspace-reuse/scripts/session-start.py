#!/usr/bin/env python3
"""
SessionStart hook to manage workspace state for reuse between tasks.

Behaviors:
- If on a branch with a merged PR, switch to main and notify user/agent
- If on a branch (not merged), run git fetch and show git status to agent
- If on main, run git pull to get latest changes
"""

import json
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


def get_default_branch() -> str:
    """Get the default branch name (main or master)."""
    # Try to get the default branch from remote
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        # Output is like "refs/remotes/origin/main"
        return result.stdout.strip().split("/")[-1]

    # Fall back to checking if main or master exists
    for branch in ["main", "master"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return branch

    return "main"  # Default fallback


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


def run_git_fetch() -> str:
    """Run git fetch and return the output."""
    result = subprocess.run(
        ["git", "fetch", "--all"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    return output.strip() if output.strip() else "No new changes from remote."


def run_git_status() -> str:
    """Run git status and return the output."""
    result = subprocess.run(
        ["git", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def run_git_pull() -> str:
    """Run git pull and return the output."""
    result = subprocess.run(
        ["git", "pull"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    return output.strip()


def switch_to_default_branch(default_branch: str) -> tuple[bool, str]:
    """Switch to the default branch. Returns (success, output)."""
    result = subprocess.run(
        ["git", "checkout", default_branch],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output.strip()


def main() -> None:
    """Main entry point."""
    # Read the hook input from stdin (SessionStart provides session info)
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass  # SessionStart may not have JSON input

    current_branch = get_current_branch()

    if not current_branch:
        # Not in a git repository or can't determine branch
        sys.exit(0)

    default_branch = get_default_branch()

    # Case 1: On the default branch - run git pull
    if current_branch == default_branch:
        pull_output = run_git_pull()
        # Provide feedback to both user and agent
        print(f"[workspace-reuse] On {default_branch} branch, pulled latest changes:", file=sys.stderr)
        print(pull_output, file=sys.stderr)

        # Also provide to agent via stdout (continue with message)
        response = {
            "continue": True,
            "message": f"Automatically pulled latest changes on {default_branch}:\n```\n{pull_output}\n```",
        }
        print(json.dumps(response))
        sys.exit(0)

    # Case 2: On a feature branch - check if it has a merged PR
    if check_branch_has_merged_pr(current_branch):
        # Switch to default branch
        success, switch_output = switch_to_default_branch(default_branch)

        if success:
            # Also pull latest
            pull_output = run_git_pull()

            print(f"[workspace-reuse] Branch '{current_branch}' has a merged PR.", file=sys.stderr)
            print(f"[workspace-reuse] Switched to {default_branch} and pulled latest changes.", file=sys.stderr)

            response = {
                "continue": True,
                "message": (
                    f"The previous branch '{current_branch}' had a merged PR. "
                    f"Automatically switched to {default_branch} and pulled latest changes:\n"
                    f"```\n{pull_output}\n```\n"
                    f"Ready for new work - please create a new branch for any changes."
                ),
            }
            print(json.dumps(response))
        else:
            print(f"[workspace-reuse] Warning: Could not switch to {default_branch}: {switch_output}", file=sys.stderr)

        sys.exit(0)

    # Case 3: On a feature branch without merged PR - fetch and show status
    fetch_output = run_git_fetch()
    status_output = run_git_status()

    print(f"[workspace-reuse] On branch '{current_branch}', fetched updates:", file=sys.stderr)
    print(fetch_output, file=sys.stderr)

    response = {
        "continue": True,
        "message": (
            f"Currently on branch '{current_branch}'.\n\n"
            f"Git fetch output:\n```\n{fetch_output}\n```\n\n"
            f"Git status:\n```\n{status_output}\n```"
        ),
    }
    print(json.dumps(response))
    sys.exit(0)


if __name__ == "__main__":
    main()
