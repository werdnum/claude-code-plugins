#!/usr/bin/env python3
"""
PreToolUse hook script to rate limit BashOutput calls.
Prevents reading BashOutput too frequently to avoid excessive polling.

Rate limits:
- Maximum 2 calls per minute (60 seconds)
- Maximum 3 calls per 5 minutes (300 seconds)

Exit codes:
- 0: Allow (within rate limits)
- 2: Block (rate limit exceeded)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone


def load_config() -> dict:
    """Load and parse the bash-guard-config.json configuration file."""
    # Try layered config loading: plugin defaults → global → project
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(__file__))

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
                    # Deep merge (simple version - replace entire keys)
                    config.update(layer_config)
            except (FileNotFoundError, json.JSONDecodeError):
                continue

    if not config:
        print("Error: No configuration file found", file=sys.stderr)
        sys.exit(1)

    return config


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO 8601 timestamp string to datetime object."""
    # Handle timestamps with 'Z' suffix
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
    return datetime.fromisoformat(timestamp_str)


def get_bashoutput_calls_from_transcript(transcript_path: str) -> list[datetime]:
    """
    Extract all BashOutput tool use timestamps from the transcript.

    Returns:
        List of datetime objects representing when BashOutput was called
    """
    if not os.path.exists(transcript_path):
        print(f"Warning: Transcript file not found: {transcript_path}", file=sys.stderr)
        return []

    try:
        with open(transcript_path, encoding="utf-8") as f:
            transcript = [json.loads(line) for line in f if line.strip()]
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Warning: Could not read transcript: {e}", file=sys.stderr)
        return []

    timestamps = []

    for entry in transcript:
        # Look for assistant messages with tool use
        if entry.get("type") != "assistant":
            continue

        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        timestamp_str = entry.get("timestamp")
        if not timestamp_str:
            continue

        # Check if any tool use is BashOutput
        for item in content:
            if (item.get("type") == "tool_use" and
                item.get("name") == "BashOutput"):
                try:
                    timestamp = parse_iso_timestamp(timestamp_str)
                    timestamps.append(timestamp)
                except (ValueError, AttributeError) as e:
                    print(f"Warning: Could not parse timestamp '{timestamp_str}': {e}", file=sys.stderr)
                    continue

    return sorted(timestamps)


def check_rate_limit(
    timestamps: list[datetime],
    current_time: datetime,
    max_calls_per_minute: int,
    max_calls_per_5_minutes: int
) -> tuple[bool, str]:
    """
    Check if rate limits are exceeded.

    Returns:
        tuple of (allowed, explanation)
        - allowed: True if within rate limits, False otherwise
        - explanation: Human-readable explanation if blocked
    """
    # Count calls in the last minute
    one_minute_ago = current_time - timedelta(seconds=60)
    calls_last_minute = sum(1 for ts in timestamps if ts > one_minute_ago)

    # Count calls in the last 5 minutes
    five_minutes_ago = current_time - timedelta(seconds=300)
    calls_last_5_minutes = sum(1 for ts in timestamps if ts > five_minutes_ago)

    # Check rate limits
    if calls_last_minute >= max_calls_per_minute:
        return False, (
            f"BashOutput rate limit exceeded: {calls_last_minute} calls in the last minute "
            f"(maximum: {max_calls_per_minute}).\n"
            "Please wait before checking output again. "
            "Excessive polling can slow down Claude Code and consume unnecessary resources."
        )

    if calls_last_5_minutes >= max_calls_per_5_minutes:
        return False, (
            f"BashOutput rate limit exceeded: {calls_last_5_minutes} calls in the last 5 minutes "
            f"(maximum: {max_calls_per_5_minutes}).\n"
            "Please wait before checking output again. "
            "Consider using longer intervals between checks or waiting for the background process to complete."
        )

    return True, ""


def main() -> None:
    """Main entry point for the hook."""
    # Read the hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Only check BashOutput tool calls
    tool_name = input_data.get("tool_name", "")

    if tool_name != "BashOutput":
        # Not a BashOutput call, allow
        sys.exit(0)

    # Load configuration
    config = load_config()

    # Check if rate limiting is enabled
    rate_limit_config = config.get("bashoutput_rate_limit", {})
    if not rate_limit_config.get("enabled", True):
        # Rate limiting disabled
        sys.exit(0)

    # Get rate limit thresholds
    max_calls_per_minute = rate_limit_config.get("max_calls_per_minute", 2)
    max_calls_per_5_minutes = rate_limit_config.get("max_calls_per_5_minutes", 3)

    # Get transcript path
    transcript_path = input_data.get("transcript_path", "")

    if not transcript_path:
        # No transcript available, allow (fail open)
        sys.exit(0)

    # Get all BashOutput calls from transcript
    bashoutput_timestamps = get_bashoutput_calls_from_transcript(transcript_path)

    # Check rate limit
    current_time = datetime.now(timezone.utc)
    allowed, explanation = check_rate_limit(
        bashoutput_timestamps,
        current_time,
        max_calls_per_minute,
        max_calls_per_5_minutes
    )

    if not allowed:
        print(f"• {explanation}", file=sys.stderr)
        sys.exit(2)

    # Within rate limits, allow
    sys.exit(0)


if __name__ == "__main__":
    main()
