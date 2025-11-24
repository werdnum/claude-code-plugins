"""Python linting support with ruff, basedpyright, and ast-grep."""

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LintResult:
    """Result from running a linter."""
    name: str
    success: bool
    duration: float
    output: str = ""
    error: str = ""
    auto_fixable: bool = False


def expand_shell_var(template: str) -> str:
    """
    Expand shell-style variable syntax like ${VAR:-default}.

    Supports:
    - ${VAR:-default}: Use VAR if set and non-empty, otherwise use default
    - ${VAR}: Use VAR if set, otherwise empty string
    - $VAR: Use VAR if set, otherwise empty string
    """
    # Handle ${VAR:-default} syntax
    def replace_with_default(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        value = os.environ.get(var_name, "").strip()
        return value if value else default

    result = re.sub(r'\$\{([^:}]+):-([^}]*)\}', replace_with_default, template)

    # Handle ${VAR} syntax
    def replace_simple(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    result = re.sub(r'\$\{([^}]+)\}', replace_simple, result)

    # Handle $VAR syntax
    result = re.sub(r'\$([A-Z_][A-Z0-9_]*)', lambda m: os.environ.get(m.group(1), ""), result)

    return result


async def run_command(cmd: list[str], timeout: float = 5.0) -> tuple[int, str, str, float]:
    """Run a command asynchronously with timeout."""
    start_time = time.time()
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            duration = time.time() - start_time
            return process.returncode or 0, stdout, stderr, duration
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            duration = time.time() - start_time
            return -1, "", f"Timeout after {timeout}s", duration
    except Exception as e:
        duration = time.time() - start_time
        return -1, "", str(e), duration


async def run_hints(file_path: str, tool_name: str, tool_input: dict[str, Any], config: dict[str, Any]) -> LintResult:
    """Run hints checker and filter to only new/changed code."""
    hints_config = config.get("tools", {}).get("ast-grep-hints", {})

    if not hints_config.get("enabled", True):
        return LintResult("hints", True, 0.0)

    script_path = hints_config.get("scriptPath", ".ast-grep/check-hints.py")
    if not Path(script_path).exists():
        return LintResult("hints", True, 0.0)

    timeout_ms = hints_config.get("timeout", 2000)
    cmd = [script_path, "--json", file_path]
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0 or not stdout:
        return LintResult("hints", True, duration)

    try:
        hints = json.loads(stdout) if stdout else []
        if not hints:
            return LintResult("hints", True, duration)

        # Filter hints based on tool type and filter mode
        filter_mode = hints_config.get("filterMode", "new-code-only")
        filtered_hints = []

        if filter_mode == "all":
            filtered_hints = hints
        elif filter_mode == "new-code-only" and tool_name == "Edit":
            # For Edit: only show hints where matched code appears in new_string
            new_string = tool_input.get("new_string", "")
            for hint in hints:
                matched_text = hint.get("text", "")
                if matched_text and matched_text in new_string:
                    filtered_hints.append(hint)
        elif filter_mode == "new-files-only" and tool_name == "Write":
            # For Write: only show hints if file is not tracked by git
            check_cmd = ["git", "ls-files", "--error-unmatch", file_path]
            ret, _, _, _ = await run_command(check_cmd, timeout=1.0)
            if ret != 0:
                filtered_hints = hints

        if filtered_hints:
            output = f"Code hints for {file_path}:\n"
            for hint in filtered_hints:
                line = hint.get("range", {}).get("start", {}).get("line", "?")
                rule_id = hint.get("ruleId", "unknown")
                message = hint.get("message", "")
                output += f"  Line {line}: 💡 [{rule_id}] {message}\n"

            return LintResult("hints", success=True, duration=duration, output=output.strip())

        return LintResult("hints", True, duration)

    except json.JSONDecodeError:
        return LintResult("hints", True, duration)


async def run_conformance(file_path: str, config: dict[str, Any]) -> LintResult:
    """Run code conformance check (ast-grep)."""
    conformance_config = config.get("tools", {}).get("ast-grep-conformance", {})

    if not conformance_config.get("enabled", True):
        return LintResult("code-conformance", True, 0.0)

    script_path = conformance_config.get("scriptPath", ".ast-grep/check-conformance.py")
    if not Path(script_path).exists():
        return LintResult("code-conformance", True, 0.0)

    timeout_ms = conformance_config.get("timeout", 2000)
    cmd = [script_path, "--json", file_path]
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0 and stdout:
        try:
            violations = json.loads(stdout) if stdout else []
            if violations:
                output = f"Code conformance violations in {file_path}:\n"
                for v in violations:
                    line = v.get("range", {}).get("start", {}).get("line", "?")
                    rule_id = v.get("ruleId", "unknown")
                    message = v.get("message", "")
                    output += f"  Line {line}: [{rule_id}] {message}\n"

                return LintResult("code-conformance", success=False, duration=duration, output=output.strip(), auto_fixable=False)
        except json.JSONDecodeError:
            pass

    return LintResult("code-conformance", True, duration)


async def run_ruff_format(file_path: str, config: dict[str, Any]) -> LintResult:
    """Run ruff format."""
    ruff_format_config = config.get("tools", {}).get("ruff-format", {})

    if not ruff_format_config.get("enabled", True):
        return LintResult("ruff format", True, 0.0)

    venv = expand_shell_var(config.get("venvPath", "${VIRTUAL_ENV:-.venv}"))

    command_template = ruff_format_config.get("command", "{venv}/bin/ruff format {file}")
    command = command_template.replace("{venv}", venv).replace("{file}", file_path)

    timeout_ms = ruff_format_config.get("timeout", 5000)
    cmd = command.split()
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0:
        output = stderr or stdout or "ruff format failed"
        return LintResult("ruff format", success=False, duration=duration, output=output)

    return LintResult("ruff format", True, duration)


async def run_ruff_check(file_path: str, config: dict[str, Any]) -> LintResult:
    """Run ruff check."""
    ruff_check_config = config.get("tools", {}).get("ruff-check", {})

    if not ruff_check_config.get("enabled", True):
        return LintResult("ruff check", True, 0.0)

    venv = expand_shell_var(config.get("venvPath", "${VIRTUAL_ENV:-.venv}"))

    command_template = ruff_check_config.get("command", "{venv}/bin/ruff check --preview --ignore=E501 {file}")
    command = command_template.replace("{venv}", venv).replace("{file}", file_path)

    timeout_ms = ruff_check_config.get("timeout", 2000)
    cmd = command.split()
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0:
        output = stderr or stdout

        # Show diff if enabled
        if ruff_check_config.get("showDiff", True):
            diff_cmd = f"{venv}/bin/ruff check --diff --unsafe-fixes --preview --ignore=E501 {file_path}".split()
            _, diff_stdout, diff_stderr, _ = await run_command(diff_cmd, timeout=timeout_ms / 1000.0)
            diff_output = diff_stdout or diff_stderr
            if diff_output:
                output += f"\n💡 Suggested fixes:\n{diff_output}"

        return LintResult("ruff check", success=False, duration=duration, output=output, auto_fixable=bool(diff_output))

    return LintResult("ruff check", True, duration)


async def run_basedpyright(file_path: str, config: dict[str, Any]) -> LintResult:
    """Run basedpyright type checker."""
    pyright_config = config.get("tools", {}).get("basedpyright", {})

    if not pyright_config.get("enabled", True):
        return LintResult("basedpyright", True, 0.0)

    venv = expand_shell_var(config.get("venvPath", "${VIRTUAL_ENV:-.venv}"))

    command_template = pyright_config.get("command", "{venv}/bin/basedpyright {file}")
    command = command_template.replace("{venv}", venv).replace("{file}", file_path)

    timeout_ms = pyright_config.get("timeout", 8000)
    cmd = command.split()
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0:
        output = stdout or stderr
        # Extract error messages
        lines = output.split("\n")
        errors = [line for line in lines if "error:" in line.lower()]

        max_errors = pyright_config.get("maxErrorsShown", 5)
        if errors:
            output = "\n".join(errors[:max_errors])
            if len(errors) > max_errors:
                output += f"\n... and {len(errors) - max_errors} more errors"

        return LintResult("basedpyright", success=False, duration=duration, output=output)

    return LintResult("basedpyright", True, duration)


def format_results(file_path: str, results: list[LintResult]) -> dict[str, Any] | None:
    """Format lint results for output."""
    total_duration = sum(r.duration for r in results)
    has_errors = any(not r.success for r in results)

    if not has_errors:
        return None

    output_lines = [
        f"🔍 Lint issues in {file_path} ({total_duration:.2f}s)",
        ""
    ]

    for result in results:
        if not result.success:
            output_lines.append(f"❌ {result.name} ({result.duration:.2f}s)")
            if result.output:
                for line in result.output.split("\n"):
                    if line.strip():
                        output_lines.append(f"   {line}")
            output_lines.append("")

    has_auto_fixable = any(r.auto_fixable for r in results)
    if has_auto_fixable:
        output_lines.append("💡 Some issues can be auto-fixed")

    output_lines.extend([
        "",
        "ℹ️  Note: It's okay to temporarily ignore these if you're",
        "   actively working on related changes that will fix them."
    ])

    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(output_lines),
        }
    }


async def lint_file(file_path: str, tool_name: str, tool_input: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    """Run all Python linters on a file."""
    # Run format first
    format_result = await run_ruff_format(file_path, config)

    # Run other linters in parallel
    other_tasks = [
        run_ruff_check(file_path, config),
        run_basedpyright(file_path, config),
        run_conformance(file_path, config),
        run_hints(file_path, tool_name, tool_input, config),
    ]

    other_results = await asyncio.gather(*other_tasks)
    all_results = [format_result, *other_results]

    return format_results(file_path, all_results)
