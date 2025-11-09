#!/bin/bash

# Test Verification Hook for Claude Code
# Ensures tests have been run successfully since the last file modification
# Exit codes: 0 = success/pass, 2 = blocking error (tests not run)

set -euo pipefail

# Load configuration to check if test verification is enabled
CONFIG_PATHS=(
    "${CLAUDE_PLUGIN_ROOT}/config/guardian-config.json"
    "$HOME/.config/claude-code/guardian.json"
    "$(pwd)/.claude/guardian.json"
)

ENABLED=false
for config_path in "${CONFIG_PATHS[@]}"; do
    if [ -f "$config_path" ]; then
        ENABLED=$(jq -r '.testVerification.enabled // false' "$config_path")
        if [ "$ENABLED" = "true" ]; then
            break
        fi
    fi
done

# Exit early if test verification is disabled
if [ "$ENABLED" != "true" ]; then
    exit 0
fi

# Skip verification when running in remote Claude Code session (can't run full test suite due to resource constraints)
if [ "${CLAUDE_CODE_REMOTE:-false}" = "true" ]; then
    exit 0
fi

# Read JSON input from stdin
INPUT=$(cat)

# Check if this is a command we want to verify tests for
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check for specific commands that indicate completion
if [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
fi

# Check if this is one of our trigger commands
if ! echo "$COMMAND" | grep -qE "(git commit|echo done)"; then
    exit 0
fi

# Check if stop_hook_active is true to avoid loops
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    # Skip verification if we're already in a stop hook to avoid loops
    exit 0
fi

# Source the core test verification logic
source "${CLAUDE_PLUGIN_ROOT}/scripts/test-verification-core.sh"

# Extract transcript path and call core function
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')

if ! check_test_status "$TRANSCRIPT_PATH"; then
    exit 2  # Block the action
fi

exit 0

