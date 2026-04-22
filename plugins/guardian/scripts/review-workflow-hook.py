#!/usr/bin/env python3
"""
Pre-commit hook for code review using the review-changes.sh script.
Handles formatting/linting, running the review, and processing the results.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class ReviewHook:
    """Handles the review hook workflow."""

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
                    "runCodeReview": {"enabled": False}
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

    # ast-grep-ignore: no-dict-any - Review data returned by script is genuinely arbitrary
    def _run_review(self, command: str) -> tuple[int, dict[str, Any], str]:
        """Run the review script and get JSON output.

        Args:
            command: The git command being executed (for context)

        Returns:
            Tuple of (exit_code, review_data, cache_key)
        """
        # Check if code review is enabled in config
        review_config = self.config.get("preCommitReview", {}).get("workflow", {}).get("runCodeReview", {})
        if not review_config.get("enabled", False):
            return 0, {}, ""  # Skip if disabled

        # Use plugin's bundled review script
        plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))
        review_script = plugin_root / "scripts" / "review-changes.py"

        if not review_script.exists():
            print("Review script not found in plugin, skipping code review", file=sys.stderr)
            return 0, {}, ""

        print("\nAnalyzing staged changes for issues...", file=sys.stderr)
        cmd = ["uv", "run", str(review_script), "--json"]
        if command:
            cmd.extend(["--command", command])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        # The human-readable output goes to stderr, JSON to stdout
        print(result.stderr, file=sys.stderr)

        try:
            review_data = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            review_data = {}

        # Extract cache_key from review data
        cache_key = review_data.get("cache_key", "")

        return result.returncode, review_data, cache_key

    # ast-grep-ignore: no-dict-any - Issues contain arbitrary JSON data from review script
    def _format_issues(self, issues: list[dict[str, Any]]) -> str:
        """Format issues from JSON for display."""
        if not issues:
            return "No specific issues available"

        formatted = []
        for issue in issues[:20]:  # Limit to 20 issues
            severity = issue.get("severity", "UNKNOWN")
            file = issue.get("file", "unknown")
            line = issue.get("line", "")
            desc = issue.get("description", "")

            if line:
                formatted.append(f"[{severity}] {file}:{line}: {desc}")
            else:
                formatted.append(f"[{severity}] {file}: {desc}")

        return "\n".join(formatted)

    def _check_for_sentinel(
        self, command: str, cache_key: str
    ) -> tuple[bool, bool, str, str]:
        """Check for review acknowledgment or bypass in the command.

        Args:
            command: The git command being executed
            cache_key: The review cache key for this diff

        Returns: (has_reviewed, has_bypass, bypass_reason, cache_key_prefix)
        """
        # Use first 12 characters of cache key for readability
        cache_key_prefix = cache_key[:12] if cache_key else "no-cache"
        sentinel = f"Reviewed: cache-{cache_key_prefix}"

        has_reviewed = sentinel in command

        # Check for bypass
        bypass_match = re.search(r"Bypass-Review:\s*([^\"'\n]+)", command)
        has_bypass = False
        bypass_reason = ""

        if bypass_match:
            bypass_reason = bypass_match.group(1).strip()
            if bypass_reason and bypass_reason not in {"<reason>", "reason"}:
                has_bypass = True

        return has_reviewed, has_bypass, bypass_reason, cache_key_prefix

    def _output_json_response(self, permission: str, reason: str) -> None:
        """Output the JSON response for the hook."""
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": permission,
                "permissionDecisionReason": reason,
            }
        }
        print(json.dumps(response))

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

            print(
                "🔍 Running improved pre-commit review workflow...\n", file=sys.stderr
            )

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

            # Step 5: Run code review
            exit_code, review_data, cache_key = self._run_review(command)

            # Check for sentinel phrases
            has_reviewed, has_bypass, bypass_reason, cache_key_prefix = (
                self._check_for_sentinel(command, cache_key)
            )

            # Process based on exit code and sentinels
            if exit_code == 0:
                if has_bypass or has_reviewed:
                    # Review passed - no need for bypass/reviewed sentinels
                    print(
                        "Code review passed with no issues. "
                        "Remove the bypass/acknowledgment sentinel from your commit message - "
                        "it is not needed when there are no issues to bypass.",
                        file=sys.stderr,
                    )
                    sys.exit(2)
                sys.exit(0)
            elif exit_code == 1:
                # Minor issues
                if has_reviewed:
                    sys.exit(0)
                elif has_bypass:
                    self._output_json_response(
                        "ask",
                        f"Minor issues found. Bypass requested: {bypass_reason}\n\nDo you want to proceed?",
                    )
                else:
                    issues = review_data.get("issues", [])
                    formatted_issues = self._format_issues(issues)
                    print(
                        f"Code review found minor issues:\n\n{formatted_issues}\n\n"
                        f"Fix these issues, then commit again normally (without any sentinel phrase).\n"
                        f"The review will re-run automatically on the updated code.\n\n"
                        f"Only if you have a specific reason NOT to fix them, you may acknowledge by adding:\n"
                        f"• Reviewed: cache-{cache_key_prefix}\n\n"
                        f"Do NOT use Bypass-Review or Reviewed if you have already fixed the issues.",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            elif has_bypass:
                # Major issues (exit code 2) with bypass request - escalate to user
                self._output_json_response(
                    "ask",
                    f"BLOCKING issues found. Escalation requested: {bypass_reason}\n\n"
                    "These are serious issues (potential build breaks, runtime errors, security risks, or logic errors) "
                    "that should typically be fixed.\n\n"
                    "You may proceed if the review is incorrect or contradicts the user's explicit instructions. "
                    "Do you want to proceed?",
                )
            elif has_reviewed:
                # Blocking issues with has_reviewed - can't bypass with Reviewed
                issues = review_data.get("issues", [])
                formatted_issues = self._format_issues(issues)
                print(
                    f"BLOCKING issues found that cannot be bypassed with 'Reviewed' acknowledgment:\n\n"
                    f"{formatted_issues}\n\n"
                    "Fix these issues, then commit again normally (without any sentinel phrase).\n"
                    "The review will re-run automatically on the updated code.\n"
                    "'Reviewed' acknowledgment is only for minor issues.\n\n"
                    "Only if you believe the review is incorrect or contradicts the user's explicit instructions, "
                    "escalate for manual decision: Bypass-Review: <why the review is incorrect>\n"
                    "Do NOT use Bypass-Review if you have already fixed the issues.",
                    file=sys.stderr,
                )
                sys.exit(2)
            else:
                # Blocking issues without bypass - exit with error message
                issues = review_data.get("issues", [])
                formatted_issues = self._format_issues(issues)
                print(
                    f"Code review found BLOCKING issues:\n\n{formatted_issues}\n\n"
                    "Fix these issues, then commit again normally (without any sentinel phrase).\n"
                    "The review will re-run automatically on the updated code.\n\n"
                    "Only if you believe the review is incorrect or contradicts the user's explicit instructions, "
                    "you may escalate for manual decision: Bypass-Review: <why the review is incorrect>\n"
                    "Do NOT use Bypass-Review if you have already fixed the issues.",
                    file=sys.stderr,
                )
                sys.exit(2)

        finally:
            # Always restore stash on exit
            self._restore_stash()


if __name__ == "__main__":
    hook = ReviewHook()
    hook.run()
