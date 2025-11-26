#!/bin/bash

# Stop Validation Hook for Claude Code
# Provides feedback on session state before stopping.
# Exit codes: 0 = allow stop, 2 = block stop and show feedback

set -euo pipefail

# Source the core test verification logic
source "${CLAUDE_PLUGIN_ROOT}/scripts/test-verification-core.sh"

# --- Early exit checks ---
# Read JSON from stdin once and store it
JSON_INPUT=$(cat)

# Prevent feedback loop on API errors
TRANSCRIPT_PATH=$(echo "$JSON_INPUT" | jq -r '.transcript_path // empty')
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    if tail -n 1 "$TRANSCRIPT_PATH" | jq -e '.isApiErrorMessage // false' > /dev/null; then
        echo "API error message detected. Exiting gracefully to prevent loop." >&2
        exit 0
    fi
fi

# If stop hook is already active (e.g., from a 'block' response), allow exit.
STOP_HOOK_ACTIVE=$(echo "$JSON_INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    exit 0
fi

# --- Load configuration ---
CONFIG=$(load_guardian_config)
STOP_VALIDATION_CONFIG=$(echo "$CONFIG" | jq -r '.stopValidation // {}')
ENABLED=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.enabled // false')
ONESHOT_CONFIG=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.oneshotMode // {}')
ONESHOT_MODE_ENABLED=$(echo "$ONESHOT_CONFIG" | jq -r '.enabled // false')

# Exit early if stop validation is disabled in all modes
if [ "$ENABLED" != "true" ] && { [ -z "$ONESHOT_MODE" ] || [ "$ONESHOT_MODE_ENABLED" != "true" ]; }; then
    exit 0
fi

# --- One-Shot Mode Validation ---
if [ "$ONESHOT_MODE_ENABLED" = "true" ] && [ -n "$ONESHOT_MODE" ]; then
    echo "🎯 ONE SHOT MODE - Checking completion status..." >&2
    
    FAILURE_FILE=$(echo "$ONESHOT_CONFIG" | jq -r '.allowFailureFile // ".claude/FAILURE_REASON"')
    if [ -f "$FAILURE_FILE" ]; then
        echo "❌ TASK MARKED AS FAILED" >&2
        echo "   Reason: $(cat "$FAILURE_FILE")" >&2
        exit 0
    fi
    
    ISSUES=()
    STRICT_REQS=$(echo "$ONESHOT_CONFIG" | jq -r '.strictRequirements // {}')

    # 1. Git Repo Check
    if [ "$(echo "$STRICT_REQS" | jq -r '.gitRepo // true')" = "true" ] && ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        ISSUES+=("❌ Not inside a git repository - You MUST initialize git and commit all work.")
    else
        # 2. Feature Branch Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.featureBranch // true')" = "true" ]; then
            current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
            if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
                ISSUES+=("❌ You're on the $current_branch branch - Create a feature branch.")
            fi
        fi
        
        # 3. Clean Working Dir Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.cleanWorkingDir // true')" = "true" ] && [ -n "$(git status --porcelain)" ]; then
            ISSUES+=("❌ Uncommitted changes found - You MUST commit all changes.")
        fi
        
        # 4. All Commits Pushed Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.allCommitsPushed // true')" = "true" ]; then
            upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)
            if [ -n "$upstream" ]; then
                if [ -n "$(git log --oneline "$upstream"..HEAD)" ]; then
                    ISSUES+=("❌ Unpushed commits found - You MUST push all commits.")
                fi
            elif [ -n "$(git log --oneline | head -1)" ]; then
                ISSUES+=("❌ No upstream branch set - You MUST push to a remote branch.")
            fi
        fi
    fi

    # 5. Tests Pass Check
    if [ "$(echo "$STRICT_REQS" | jq -r '.testsPass // true')" = "true" ]; then
        TEST_VERIFICATION_CONFIG=$(echo "$CONFIG" | jq -r '.testVerification // {}')
        if ! check_test_status "$TRANSCRIPT_PATH" "$TEST_VERIFICATION_CONFIG"; then
            ISSUES+=("❌ Tests have not passed - You MUST run tests and fix any failures.")
        fi
    fi

    if [ ${#ISSUES[@]} -gt 0 ]; then
        echo "🎯 ONE SHOT MODE - Issues to resolve:" >&2
        for issue in "${ISSUES[@]}"; do echo "   $issue" >&2; done
        echo "   💡 Fix ALL issues, or write a failure reason to $FAILURE_FILE" >&2
        exit 2
    fi

    echo "✅ All requirements met for one-shot mode. Task complete." >&2
    exit 0
fi

# --- Standard Mode Validation ---
if [ "$ENABLED" != "true" ]; then
    exit 0
fi

VALIDATION_MESSAGES=()
BLOCKING_ERROR_FOUND=false

add_message() {
    local type="$1"
    local message="$2"
    VALIDATION_MESSAGES+=("$message")
    if [ "$type" = "error" ]; then BLOCKING_ERROR_FOUND=true; fi
}

# 1. Format and Lint
FORMAT_LINT_CONFIG=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.formatAndLint // {}')
if [ "$(echo "$FORMAT_LINT_CONFIG" | jq -r '.enabled // false')" = "true" ]; then
    echo "$FORMAT_LINT_CONFIG" | jq -r '.commands[]' | while IFS= read -r cmd; do
        if ! eval "$cmd"; then
            add_message "error" "❌ Command '$cmd' failed."
            break
        fi
    done
fi

# 2. Uncommitted Changes
UNCOMMITTED_LEVEL=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.uncommittedChanges // "warn"')
if [ "$UNCOMMITTED_LEVEL" != "ignore" ]; then
    if uncommitted_changes=$(git status --porcelain 2>/dev/null); [ -n "$uncommitted_changes" ]; then
        msg="Uncommitted changes detected:\n$uncommitted_changes"
        add_message "$UNCOMMITTED_LEVEL" "Uncommitted changes detected."
    fi
fi

# 3. Unpushed Commits
UNPUSHED_LEVEL=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.unpushedCommits // "warn"')
if [ "$UNPUSHED_LEVEL" != "ignore" ]; then
    upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)
    if [ -n "$upstream" ]; then
        if unpushed_commits=$(git log --oneline "$upstream"..HEAD 2>/dev/null); [ -n "$unpushed_commits" ]; then
            add_message "$UNPUSHED_LEVEL" "Unpushed commits detected."
        fi
    fi
fi

# 4. Test Status
TEST_VERIFICATION_CONFIG=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.testVerification // {}')
if [ "$(echo "$TEST_VERIFICATION_CONFIG" | jq -r '.enabled // false')" = "true" ]; then
    TEST_VERIFICATION_CORE_CONFIG=$(echo "$CONFIG" | jq -r '.testVerification // {}')
    if ! check_test_status "$TRANSCRIPT_PATH" "$TEST_VERIFICATION_CORE_CONFIG"; then
        level=$(echo "$TEST_VERIFICATION_CONFIG" | jq -r '.level // "warn"')
        add_message "$level" "Tests are not in a passing state."
    fi
fi

# --- Output and Exit ---
if [ ${#VALIDATION_MESSAGES[@]} -gt 0 ]; then
    echo "✋ Before stopping, please review the following:" >&2
    for msg in "${VALIDATION_MESSAGES[@]}"; do echo "   - $msg" >&2; done

    if [ "$BLOCKING_ERROR_FOUND" = "true" ]; then
        echo "🚫 Blocking issues must be resolved before stopping." >&2
        exit "$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.returnCode // 2')"
    else
        echo "You may proceed, but please consider addressing warnings." >&2
        exit 2
    fi
fi

exit 0
