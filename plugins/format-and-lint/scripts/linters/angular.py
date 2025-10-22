"""Angular linting support with prettier and eslint for TS/HTML/CSS files."""

import asyncio
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


async def run_command(cmd: list[str], timeout: float = 5.0, cwd: str | None = None) -> tuple[int, str, str, float]:
    """Run a command asynchronously with timeout."""
    start_time = time.time()
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
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


async def run_prettier(file_path: str, config: dict[str, Any]) -> LintResult:
    """Run prettier formatter on Angular files."""
    prettier_config = config.get("tools", {}).get("prettier", {})

    if not prettier_config.get("enabled", True):
        return LintResult("prettier", True, 0.0)

    project_dir = config.get("projectDir", "app")
    file_path_obj = Path(file_path)
    app_dir = Path.cwd() / project_dir

    # Check if file is in the app directory
    try:
        file_path_obj.relative_to(app_dir)
    except ValueError:
        return LintResult("prettier", True, 0.0)

    relative_path = str(file_path_obj.relative_to(app_dir))
    npm_script = prettier_config.get("npmScript", "format")
    timeout_ms = prettier_config.get("timeout", 5000)

    cmd = ["npm", "run", npm_script, "--prefix", project_dir, "--", relative_path]
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0:
        return LintResult(
            "prettier",
            success=False,
            duration=duration,
            output=stderr or stdout or "Prettier formatting needed",
            auto_fixable=True
        )

    return LintResult("prettier", True, duration)


async def run_eslint(file_path: str, config: dict[str, Any]) -> LintResult:
    """Run ESLint on Angular TypeScript files."""
    eslint_config = config.get("tools", {}).get("eslint", {})

    if not eslint_config.get("enabled", True):
        return LintResult("eslint", True, 0.0)

    # Only run eslint on TypeScript files
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in {".ts", ".js"}:
        return LintResult("eslint", True, 0.0)

    project_dir = config.get("projectDir", "app")
    file_path_obj = Path(file_path)
    app_dir = Path.cwd() / project_dir

    # Check if file is in the app directory
    try:
        file_path_obj.relative_to(app_dir)
    except ValueError:
        return LintResult("eslint", True, 0.0)

    relative_path = str(file_path_obj.relative_to(app_dir))
    npm_script = eslint_config.get("npmScript", "lint:fix")
    timeout_ms = eslint_config.get("timeout", 8000)

    cmd = ["npm", "run", npm_script, "--prefix", project_dir, "--", relative_path]
    returncode, stdout, stderr, duration = await run_command(cmd, timeout=timeout_ms / 1000.0)

    if returncode != 0:
        return LintResult(
            "eslint",
            success=False,
            duration=duration,
            output=stderr or stdout,
            auto_fixable=True
        )

    return LintResult("eslint", True, duration)


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
        output_lines.append("💡 Some issues can be auto-fixed with npm run format or npm run lint:fix")

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
    """Run Angular linters on a file."""
    file_ext = Path(file_path).suffix.lower()

    # Run appropriate linters based on file type
    if file_ext in {".ts", ".js"}:
        # TypeScript/JavaScript: both prettier and eslint
        tasks = [
            run_prettier(file_path, config),
            run_eslint(file_path, config),
        ]
    elif file_ext in {".html", ".css", ".scss"}:
        # HTML/CSS: only prettier
        tasks = [run_prettier(file_path, config)]
    else:
        return None

    results = await asyncio.gather(*tasks)
    return format_results(file_path, list(results))
