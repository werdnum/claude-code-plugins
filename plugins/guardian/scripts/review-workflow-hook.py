#!/usr/bin/env python3
"""
Pre-commit workflow hook.

Runs deterministic gates before a commit or PR creation: executes any `git add`
commands from the command line, isolates the staged changes, runs formatters and
linters, and runs the pre-commit framework hooks.

This hook does NOT run an LLM code review. The automatic review used to shell out to
`review-changes.py` (defaulting to Gemini) on every commit; when no API key was
configured it failed open with an empty issue list, so commits were reported as
"reviewed" without anything having been reviewed. `review-changes.py` is still
available to run by hand -- see scripts/review-changes.py in the marketplace repo.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class ReviewHook:
    """Handles the pre-commit workflow."""

    def __init__(self) -> None:
        self.repo_root = self._get_repo_root()
        self.config = self._load_config()
        # ast-grep-ignore: no-dict-any - Hook configuration uses generic dict for flexibility
        self.stash_ref: str | None = None
        self.has_stashed = False

    def _get_repo_root(self) -> Path:
        """Get the repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            # Not in a git repo, allow the command
            sys.exit(0)
        return Path(result.stdout.strip())

    def _load_config(self) -> dict[str, Any]:
        """Load configuration with layered override support."""
        plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))

        # Load default configuration
        default_config_path = plugin_root / "config" / "guardian-config.json"
        try:
            with open(default_config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading default config from {default_config_path}: {e}", file=sys.stderr)
            return self._get_fallback_config()

        # Load global overrides if they exist
        global_config_path = Path.home() / ".config" / "claude-code" / "guardian.json"
        if global_config_path.exists():
            try:
                with open(global_config_path, encoding="utf-8") as f:
                    global_config = json.load(f)
                    config = self._merge_config(config, global_config)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        # Load project overrides if they exist
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", self.repo_root))
        project_config_path = project_dir / ".claude" / "guardian.json"
        if project_config_path.exists():
            try:
                with open(project_config_path, encoding="utf-8") as f:
                    project_config = json.load(f)
                    config = self._merge_config(config, project_config)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        return config

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def _get_fallback_config(self) -> dict[str, Any]:
        """Return minimal fallback config if default config can't be loaded."""
        return {
            "preCommitReview": {
                "enabled": True,
                "skipInRemote": True,
                "workflow": {
                    "executeGitAdds": True,
                    "stashUnstaged": True,
                    "runFormatLint": {"enabled": False},
                    "runPreCommitHooks": {"enabled": True, "maxIterations": 5},
                }
            }
        }

    # ast-grep-ignore: no-dict-any - JSON parsing requires generic dict
    def _parse_input(self) -> dict[str, Any]:
        """Parse the JSON input from stdin."""
        try:
            return json.loads(sys.stdin.read())
        except json.JSONDecodeError:
            # Invalid input, allow the command
            sys.exit(0)

    # ast-grep-ignore: no-dict-any - JSON input is genuinely arbitrary hook data
    def _extract_command(self, json_input: dict[str, Any]) -> str:
        """Extract the bash command from the JSON input."""
        return json_input.get("tool_input", {}).get("command", "")

    def _is_commit_or_pr(self, command: str) -> bool:
        """Check if the command is a git commit or PR creation."""
        patterns = [r"git\s+(commit|ci)(\s|$)", r"gh\s+pr\s+create"]
        return any(re.search(pattern, command) for pattern in patterns)

    def _execute_git_adds(self, command: str) -> bool:
        """Parse and execute any git add commands in the command."""
        add_pattern = r"git\s+add\s+[^;&|]*"
        add_commands = re.findall(add_pattern, command)

        for add_cmd in add_commands:
            result = subprocess.run(
                add_cmd,
                shell=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                print(f"❌ {add_cmd} failed", file=sys.stderr)
                return False

        if add_commands:
            print("✅ Git add commands completed", file=sys.stderr)
        return True

    def _stash_unstaged_changes(self) -> bool:
        """Stash unstaged changes to isolate staged changes."""
        # Check if there are unstaged changes
        result = subprocess.run(
            ["git", "diff", "--quiet"], capture_output=True, check=False
        )
        if result.returncode == 0:
            # No unstaged changes
            return False

        # Create a stash
        result = subprocess.run(
            ["git", "stash", "create", "review-hook: unstaged changes"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.stdout.strip():
            self.stash_ref = result.stdout.strip()
            # Store the stash
            subprocess.run(
                [
                    "git",
                    "stash",
                    "store",
                    "-m",
                    "review-hook: unstaged changes",
                    self.stash_ref,
                ],
                check=False,
            )
            # Reset to match index
            subprocess.run(["git", "checkout-index", "-a", "-f"], check=False)
            self.has_stashed = True
            print(
                f"✅ Unstaged changes stashed (ref: {self.stash_ref[:8]})",
                file=sys.stderr,
            )
            return True
        return False

    def _restore_stash(self) -> None:
        """Restore stashed changes."""
        if not self.has_stashed or not self.stash_ref:
            return

        print("\nRestoring stashed changes...", file=sys.stderr)
        result = subprocess.run(
            ["git", "stash", "apply", "--quiet", self.stash_ref],
            capture_output=True,
            check=False,
        )

        if result.returncode == 0:
            subprocess.run(
                ["git", "stash", "drop", "--quiet", self.stash_ref], check=False
            )
            print("✅ Stashed changes restored successfully", file=sys.stderr)
        else:
            print("⚠️ Failed to restore stashed changes cleanly", file=sys.stderr)
            # If stash apply fails it can leave conflict markers behind. Clean up the
            # working tree by restoring the index contents so the user keeps their
            # staged/ formatted changes without conflict artifacts.
            cleanup = subprocess.run(
                ["git", "checkout-index", "-a", "-f"],
                capture_output=True,
                text=True,
                check=False,
            )
            if cleanup.returncode != 0 and cleanup.stderr:
                print(cleanup.stderr, file=sys.stderr)
            print(
                f"Your changes are preserved in stash: {self.stash_ref[:8]}",
                file=sys.stderr,
            )

    def _run_formatters_and_linters(self) -> bool:
        """Run formatting/linting via plugin or repo script."""
        format_config = self.config.get("preCommitReview", {}).get("workflow", {}).get("runFormatLint", {})

        if not format_config.get("enabled", False):
            return True  # Skip if disabled in config

        # Get staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        staged_files = [f for f in result.stdout.splitlines() if f]

        if not staged_files:
            return True

        # Try format-and-lint plugin if enabled
        if format_config.get("usePlugin", True):
            plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))
            # Check if format-and-lint plugin is available (assumes it's a sibling plugin)
            format_plugin_script = plugin_root.parent / "format-and-lint" / "scripts" / "format-and-lint.py"

            if format_plugin_script.exists():
                print("Running format-and-lint plugin...", file=sys.stderr)
                # Format-and-lint plugin works via PostToolUse hooks, not directly callable
                # For now, just note that it exists and will run automatically
                print("ℹ️ format-and-lint plugin will run automatically via hooks", file=sys.stderr)
                return True

        # Fall back to repo script
        repo_script_path = format_config.get("repoScriptPath", "scripts/format-and-lint.sh")
        script_path = self.repo_root / repo_script_path

        if not script_path.exists():
            print(f"⚠️ {repo_script_path} not found, skipping formatting", file=sys.stderr)
            return True

        print(f"Running {repo_script_path}...", file=sys.stderr)
        result = subprocess.run(
            [str(script_path)] + staged_files,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print("❌ Formatting/linting failed", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            return False

        # Stage any changes made by formatters
        subprocess.run(["git", "add"] + staged_files, check=False)
        print("✅ Formatting and linting completed", file=sys.stderr)
        return True

    def _run_precommit_hooks(self) -> tuple[bool, str]:
        """Run pre-commit hooks on staged files."""
        if (
            subprocess.run(
                ["which", "pre-commit"], capture_output=True, check=False
            ).returncode
            != 0
        ):
            return True, ""

        config_path = self.repo_root / ".pre-commit-config.yaml"
        if not config_path.exists():
            return True, ""

        print("Running pre-commit hooks...", file=sys.stderr)

        for iteration in range(5):
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=False,
            )
            staged_files = [f for f in result.stdout.splitlines() if f]

            if not staged_files:
                break

            result = subprocess.run(
                ["pre-commit", "run", "--files"] + staged_files,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                # Check if any changes were made
                if (
                    subprocess.run(["git", "diff", "--quiet"], check=False).returncode
                    == 0
                ):
                    print("✅ Pre-commit hooks completed", file=sys.stderr)
                    break
                else:
                    print(
                        f"Pre-commit hooks made changes (iteration {iteration + 1})...",
                        file=sys.stderr,
                    )
                    subprocess.run(["git", "add", "-u"], check=False)
            else:
                print("❌ Pre-commit hooks failed", file=sys.stderr)
                error_msg = ""
                if result.stdout:
                    print("STDOUT:", file=sys.stderr)
                    print(result.stdout, file=sys.stderr)
                    error_msg += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    print("STDERR:", file=sys.stderr)
                    print(result.stderr, file=sys.stderr)
                    error_msg += f"STDERR:\n{result.stderr}\n"
                return False, error_msg

        return True, ""

    def run(self) -> None:
        """Main workflow execution."""
        # Check if pre-commit review is enabled
        pre_commit_config = self.config.get("preCommitReview", {})
        if not pre_commit_config.get("enabled", True):
            sys.exit(0)

        # Skip review when running in remote Claude Code session if configured
        if pre_commit_config.get("skipInRemote", True):
            if os.getenv("CLAUDE_CODE_REMOTE", "false").lower() == "true":
                sys.exit(0)

        try:
            # Parse input
            json_input = self._parse_input()
            command = self._extract_command(json_input)

            # Check if this is a commit/PR command
            if not self._is_commit_or_pr(command):
                sys.exit(0)

            print("🔍 Running pre-commit workflow...\n", file=sys.stderr)

            # Step 1: Execute git add commands
            if not self._execute_git_adds(command):
                sys.exit(0)

            # Step 2: Stash unstaged changes
            self._stash_unstaged_changes()

            # Step 3: Run formatters and linters
            if not self._run_formatters_and_linters():
                print(
                    "Formatting/linting failed. Please fix the issues before committing.",
                    file=sys.stderr,
                )
                sys.exit(2)

            # Step 4: Run pre-commit hooks
            success, error_msg = self._run_precommit_hooks()
            if not success:
                print(
                    "Pre-commit hooks failed. Please fix the issues before committing.",
                    file=sys.stderr,
                )
                sys.exit(2)

            # All gates passed - allow the commit.
            sys.exit(0)

        finally:
            # Always restore stash on exit
            self._restore_stash()


if __name__ == "__main__":
    hook = ReviewHook()
    hook.run()
