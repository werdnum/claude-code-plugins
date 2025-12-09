#!/usr/bin/env python3
"""
PostToolUse hook to discourage linter ignore comments without proper justification.
Detects common linter ignore patterns and provides educational feedback.
"""

import json
import re
import sys
from pathlib import Path


# Common linter ignore patterns across different languages and tools
IGNORE_PATTERNS = [
    # Python
    (r"#\s*type:\s*ignore", "type: ignore", "Python type checker (mypy/pyright)"),
    (r"#\s*noqa", "noqa", "Python linters (flake8/ruff)"),
    (r"#\s*pylint:\s*disable", "pylint: disable", "Pylint"),
    (r"#\s*pyright:\s*ignore", "pyright: ignore", "Pyright type checker"),
    (r"#\s*mypy:\s*ignore", "mypy: ignore", "Mypy type checker"),

    # JavaScript/TypeScript
    (r"//\s*@ts-ignore", "@ts-ignore", "TypeScript compiler"),
    (r"//\s*@ts-expect-error", "@ts-expect-error", "TypeScript compiler"),
    (r"//\s*@ts-nocheck", "@ts-nocheck", "TypeScript compiler"),
    (r"//\s*eslint-disable", "eslint-disable", "ESLint"),
    (r"/\*\s*eslint-disable", "eslint-disable", "ESLint"),

    # Code analysis tools
    (r"//\s*ast-grep-ignore", "ast-grep-ignore", "ast-grep"),
    (r"#\s*ast-grep-ignore", "ast-grep-ignore", "ast-grep"),

    # Formatters
    (r"//\s*prettier-ignore", "prettier-ignore", "Prettier"),
    (r"#\s*fmt:\s*off", "fmt: off", "Python formatters (black/yapf)"),
    (r"#\s*fmt:\s*skip", "fmt: skip", "Python formatters (black/yapf)"),

    # Rust
    (r"#\[allow\(", "#[allow(", "Rust compiler/clippy"),
    (r"//\s*rustfmt::skip", "rustfmt::skip", "rustfmt"),

    # Go
    (r"//\s*nolint", "nolint", "Go linters (golangci-lint)"),

    # Ruby
    (r"#\s*rubocop:disable", "rubocop:disable", "RuboCop"),

    # Java
    (r"@SuppressWarnings", "@SuppressWarnings", "Java compiler"),
]


def detect_ignore_comments(content: str) -> list[dict[str, str]]:
    """
    Detect linter ignore comments in the content.

    Returns a list of dictionaries with 'pattern', 'tool', and 'line' information.
    """
    detections = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for pattern, name, tool in IGNORE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                detections.append({
                    'pattern': name,
                    'tool': tool,
                    'line': line_num,
                    'content': line.strip()
                })

    return detections


def has_justification(line: str) -> bool:
    """
    Check if an ignore comment has a justification.
    Simple heuristic: line has additional text beyond the ignore directive.
    """
    # Remove common ignore patterns and check if there's meaningful text left
    cleaned = re.sub(r'#\s*(type:\s*ignore|noqa|pylint:\s*disable|pyright:\s*ignore|mypy:\s*ignore)', '', line, flags=re.IGNORECASE)
    cleaned = re.sub(r'//\s*(@ts-ignore|@ts-expect-error|eslint-disable|prettier-ignore|ast-grep-ignore|nolint)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'/\*\s*eslint-disable.*?\*/', '', cleaned, flags=re.IGNORECASE)

    # If there's substantial text remaining (not just code), consider it justified
    # This is a simple heuristic and may need refinement
    remaining_text = cleaned.strip()

    # Check for common justification patterns
    justification_indicators = [
        'because',
        'reason:',
        'justification:',
        'todo:',
        'fixme:',
        'note:',
        'see:',
        'ref:',
        'issue:',
        'bug:',
        'workaround',
        'temporary',
        'legacy',
        'third-party',
        'external',
    ]

    lower_line = line.lower()
    return any(indicator in lower_line for indicator in justification_indicators)


def create_warning_message(detections: list[dict[str, str]], file_path: str) -> dict:
    """Create a hook output message warning about linter ignore comments."""

    # Count justified vs unjustified
    unjustified = []
    justified = []

    for detection in detections:
        if has_justification(detection['content']):
            justified.append(detection)
        else:
            unjustified.append(detection)

    # Build the warning message
    if not unjustified:
        # All ignores have justifications - still show a gentle reminder
        if justified:
            message_parts = [
                "⚠️  Linter ignore comments detected",
                "",
                f"Found {len(justified)} linter ignore comment(s) in {Path(file_path).name}:",
                ""
            ]

            for det in justified[:5]:  # Limit to first 5
                message_parts.append(f"  Line {det['line']}: {det['pattern']} ({det['tool']})")

            if len(justified) > 5:
                message_parts.append(f"  ... and {len(justified) - 5} more")

            message_parts.extend([
                "",
                "✓ These appear to have justifications, which is good practice.",
                "",
                "💡 Reminder: Always prefer fixing the underlying issue over suppressing warnings.",
            ])

            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n".join(message_parts)
                }
            }
    else:
        # Found unjustified ignores - show stronger warning
        message_parts = [
            "⚠️  LINTER IGNORE COMMENTS WITHOUT JUSTIFICATION DETECTED",
            "",
            f"Found {len(unjustified)} unjustified linter ignore comment(s) in {Path(file_path).name}:",
            ""
        ]

        for det in unjustified[:5]:  # Limit to first 5
            message_parts.append(f"  Line {det['line']}: {det['pattern']} ({det['tool']})")

        if len(unjustified) > 5:
            message_parts.append(f"  ... and {len(unjustified) - 5} more")

        message_parts.extend([
            "",
            "🚫 Silencing linter warnings is strongly discouraged!",
            "",
            "Instead, you should:",
            "  1. FIX THE UNDERLYING ISSUE - This is always the preferred approach",
            "  2. If fixing is genuinely not possible, add a clear justification explaining:",
            "     • Why the warning cannot be fixed",
            "     • Why suppressing it is the only option",
            "     • Any relevant context (e.g., third-party code, known limitation)",
            "",
            "Example of justified ignore:",
            "  # type: ignore  # Third-party library has incomplete type stubs, see issue #123",
            "  # noqa: E501  # URL cannot be split across lines",
            "",
            "Remember: Linter warnings exist to catch bugs and improve code quality.",
            "Suppressing them without understanding why defeats their purpose.",
            "",
            "Note: This is a reminder only. Disregard if an appropriate justification",
            "has already been provided.",
        ])

        if justified:
            message_parts.extend([
                "",
                f"Note: Found {len(justified)} other ignore(s) with justifications - good work on those!",
            ])

        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(message_parts)
            }
        }

    return None


def main() -> None:
    """Main entry point."""
    try:
        # Read tool data from stdin
        tool_data = json.loads(sys.stdin.read())

        tool_name = tool_data.get("tool_name", "")
        tool_input = tool_data.get("tool_input", {})

        # Only process Edit and Write tools
        if tool_name not in {"Edit", "Write"}:
            return

        file_path = tool_input.get("file_path")
        if not file_path:
            return

        # Get the content that was written/edited
        content = ""
        if tool_name == "Edit":
            new_string = tool_input.get("new_string", "")
            content = new_string
        elif tool_name == "Write":
            content = tool_input.get("content", "")

        if not content:
            return

        # Detect ignore comments
        detections = detect_ignore_comments(content)

        if detections:
            # Create and output warning message
            warning = create_warning_message(detections, file_path)
            if warning:
                print(json.dumps(warning))

    except Exception as e:
        # Log error but don't block the tool
        error_output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"Linter-ignore-guard error: {str(e)}",
            }
        }
        print(json.dumps(error_output), file=sys.stderr)


if __name__ == "__main__":
    main()
