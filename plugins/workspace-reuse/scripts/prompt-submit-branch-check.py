#!/usr/bin/env python3
"""
UserPromptSubmit hook to check if on a branch with a merged PR.

If on a merged PR branch, switch to main and notify user/agent.
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
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip().split("/")[-1]

    for branch in ["main", "master"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return branch

    return "main"


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
    # Read the hook input from stdin
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    current_branch = get_current_branch()

    if not current_branch:
        sys.exit(0)

    default_branch = get_default_branch()

    # Skip if already on default branch
    if current_branch == default_branch:
        sys.exit(0)

    # Check if on a branch with a merged PR
    if check_branch_has_merged_pr(current_branch):
        success, switch_output = switch_to_default_branch(default_branch)

        if success:
            pull_output = run_git_pull()

            print(f"[workspace-reuse] Branch '{current_branch}' has a merged PR.", file=sys.stderr)
            print(f"[workspace-reuse] Switched to {default_branch} and pulled latest changes.", file=sys.stderr)

            response = {
                "continue": True,
                "message": (
                    f"NOTE: The branch '{current_branch}' has a merged PR. "
                    f"Automatically switched to {default_branch} and pulled latest changes.\n"
                    f"```\n{pull_output}\n```\n"
                    f"Please create a new branch for any new work."
                ),
            }
            print(json.dumps(response))
        else:
            print(f"[workspace-reuse] Warning: Could not switch to {default_branch}: {switch_output}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
