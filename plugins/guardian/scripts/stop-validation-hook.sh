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
    if [ "$(tail -n 1 "$TRANSCRIPT_PATH" | jq -r '.isApiErrorMessage // false')" = "true" ]; then
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

if [ "$ENABLED" != "true" ] && [ "$ONESHOT_MODE_ENABLED" != "true" ]; then
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
        # Get current branch once for all subsequent checks
        current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)

        # 2. Feature Branch Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.featureBranch // true')" = "true" ]; then
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

        # 5. PR Created Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.prCreated // true')" = "true" ]; then
            if [ -n "$current_branch" ] && command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
                pr_count=$(gh pr list --head "$current_branch" --state open --json number --limit 1 2>/dev/null | jq 'length' 2>/dev/null || echo "0")
                if [ "$pr_count" = "0" ]; then
                    ISSUES+=("❌ No PR created for branch '$current_branch' - You MUST create a PR with 'gh pr create'.")
                fi
            fi
        fi
    fi

    # 6. Tests Pass Check
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
    mapfile -t commands < <(echo "$FORMAT_LINT_CONFIG" | jq -r '.commands[]')
    for cmd in "${commands[@]}"; do
        # Use bash -c instead of eval to reduce risk of code injection
        if ! bash -c "$cmd"; then
            add_message "error" "❌ Command '$cmd' failed."
            break
        fi
    done
fi

# 2. Uncommitted Changes
UNCOMMITTED_LEVEL=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.uncommittedChanges // "warn"')
if [ "$UNCOMMITTED_LEVEL" != "ignore" ]; then
    if uncommitted_changes=$(git status --porcelain 2>/dev/null); [ -n "$uncommitted_changes" ]; then
        add_message "$UNCOMMITTED_LEVEL" "Uncommitted changes detected:\n$uncommitted_changes"
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

# 4. PR Created Check
NO_PR_LEVEL=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.noPr // "warn"')
if [ "$NO_PR_LEVEL" != "ignore" ]; then
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
    if [ -n "$current_branch" ] && [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
            pr_count=$(gh pr list --head "$current_branch" --state open --json number --limit 1 2>/dev/null | jq 'length' 2>/dev/null || echo "0")
            if [ "$pr_count" = "0" ]; then
                add_message "$NO_PR_LEVEL" "No PR created for branch '$current_branch'. Consider running 'gh pr create'."
            fi
        fi
    fi
fi

# 5. Test Status
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
        exit 0
    fi
fi

exit 0
