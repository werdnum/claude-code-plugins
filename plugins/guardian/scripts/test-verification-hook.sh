#!/bin/bash

# Test Verification Hook for Claude Code
# Ensures tests have been run successfully since the last file modification
# Exit codes: 0 = success/pass, 2 = blocking error (tests not run)

set -euo pipefail

# Source the core test verification logic
source "${CLAUDE_PLUGIN_ROOT}/scripts/test-verification-core.sh"

# Load merged configuration
CONFIG=$(load_guardian_config)
TEST_VERIFICATION_CONFIG=$(echo "$CONFIG" | jq -r '.testVerification // {}')
ENABLED=$(echo "$TEST_VERIFICATION_CONFIG" | jq -r '.enabled // false')

# Exit early if test verification is disabled
if [ "$ENABLED" != "true" ]; then
    exit 0
fi

# Ensure CLAUDE_PLUGIN_ROOT is set for portability
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export CLAUDE_PLUGIN_ROOT
fi

# Skip verification when running in remote Claude Code session if configured
SKIP_REMOTE=$(echo "$TEST_VERIFICATION_CONFIG" | jq -r '.skipInRemote // true')
ENV_SELECTOR=$(echo "$TEST_VERIFICATION_CONFIG" | jq -r '.environmentSelector // "CLAUDE_CODE_REMOTE"')
case "$ENV_SELECTOR" in
    CLAUDE_CODE_REMOTE)
        IS_REMOTE_ENV="${CLAUDE_CODE_REMOTE:-false}"
        ;;
    *)
        # Unknown or unsupported environment variable name; default to false
        IS_REMOTE_ENV="false"
        ;;
esac

if [ "$SKIP_REMOTE" = "true" ] && [ "$IS_REMOTE_ENV" = "true" ]; then
    exit 0
fi

# Read JSON input from stdin
INPUT=$(cat)

# Check if this is a command we want to verify tests for
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check for specific tool names (Bash for Claude, run_shell_command for Gemini)
if [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "run_shell_command" ]; then
    exit 0
fi

# Check if this is one of our trigger commands
TRIGGER_COMMANDS=$(echo "$TEST_VERIFICATION_CONFIG" | jq -r '.triggerCommands[]' | paste -sd '|')
if [ -z "$TRIGGER_COMMANDS" ]; then
    exit 0
fi
if ! echo "$COMMAND" | grep -qE "($TRIGGER_COMMANDS)"; then
    exit 0
fi

# Check if stop_hook_active is true to avoid loops
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    exit 0
fi

# Extract transcript path and call core function
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')

if ! check_test_status "$TRANSCRIPT_PATH" "$TEST_VERIFICATION_CONFIG"; then
    exit 2  # Block the action
fi

exit 0
