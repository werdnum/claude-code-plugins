#!/bin/bash

# Core test verification logic for Claude Code hooks

# Loads and merges guardian configuration from default, user, and project locations.
# Merging order: project > user > default.
load_guardian_config() {
    local base_config_path="${CLAUDE_PLUGIN_ROOT}/config/guardian-config.json"
    local user_config_path="$HOME/.config/claude-code/guardian.json"
    local project_config_path
    project_config_path=$(pwd)/.claude/guardian.json

    local merged_config="{}"

    if [ -f "$base_config_path" ]; then
        merged_config=$(jq -s '.[0]' "$base_config_path")
    fi

    if [ -f "$user_config_path" ]; then
        merged_config=$(jq -s '.[0] * .[1]' <(echo "$merged_config") "$user_config_path")
    fi

    if [ -f "$project_config_path" ]; then
        merged_config=$(jq -s '.[0] * .[1]' <(echo "$merged_config") "$project_config_path")
    fi

    echo "$merged_config"
}

# Checks if tests have been run and are passing based on the provided configuration.
# Arguments:
#   $1: path to the transcript file
#   $2: JSON string of the test verification configuration section
# Returns: 0 if tests are passing, 1 otherwise.
check_test_status() {
    local TRANSCRIPT_PATH="$1"
    local CONFIG_JSON="$2"

    if [ -z "$TRANSCRIPT_PATH" ]; then
        echo "Error: No transcript_path provided to check_test_status" >&2
        return 1
    fi

    if [ ! -f "$TRANSCRIPT_PATH" ]; then
        echo "Error: Transcript file not found: $TRANSCRIPT_PATH" >&2
        return 1
    fi

    # --- Get configuration with defaults ---
    local ENV_SELECTOR=$(echo "$CONFIG_JSON" | jq -r '.environmentSelector // "CLAUDE_CODE_REMOTE"')
    local IS_REMOTE_ENV="false"
    # Only allow known, safe environment variable names
    case "$ENV_SELECTOR" in
        CLAUDE_CODE_REMOTE)
            IS_REMOTE_ENV="${CLAUDE_CODE_REMOTE:-false}"
            ;;
        *)
            # Unknown selector, default to false
            IS_REMOTE_ENV="false"
            ;;
    esac

    local TEST_COMMANDS_KEY="local"
    if [ "$IS_REMOTE_ENV" = "true" ]; then
        TEST_COMMANDS_KEY="remote"
    fi

    local TEST_COMMAND_PATTERNS=$(echo "$CONFIG_JSON" | jq -r --arg key "$TEST_COMMANDS_KEY" '
        .testCommands[$key][] | .pattern // empty
    ' | grep . | paste -sd '|')

    if [ -z "$TEST_COMMAND_PATTERNS" ]; then
        echo "Warning: No test command patterns configured for the '$TEST_COMMANDS_KEY' environment." >&2
        # Default to "poe test" if not configured to maintain backward compatibility
        TEST_COMMAND_PATTERNS="poe\s+test"
    fi

    local ALLOWED_COMMANDS_LIST=$(echo "$CONFIG_JSON" | jq -r --arg key "$TEST_COMMANDS_KEY" '
        (.testCommands[$key] // []) | map(.name // .pattern) | join(", ")
    ')

    if [ -z "$ALLOWED_COMMANDS_LIST" ]; then
        ALLOWED_COMMANDS_LIST="poe test"
    fi

    local EXCLUDE_FROM_TEST_REQ=$(echo "$CONFIG_JSON" | jq -r '
        .excludeFromTestRequirement | join("|") // ""
    ' 2>/dev/null)

    local FALLBACK_ENABLED=$(echo "$CONFIG_JSON" | jq -r '.testReportFallback.enabled // true')
    local REPORT_FILE=$(echo "$CONFIG_JSON" | jq -r '.testReportFallback.reportFile // ".report.json"')
    local STALE_THRESHOLD=$(echo "$CONFIG_JSON" | jq -r '.testReportFallback.transcriptStaleThreshold // 300')

    # --- Relaxed test file verification config ---
    local RELAXED_ENABLED=$(echo "$CONFIG_JSON" | jq -r '.relaxedTestFileVerification.enabled // true')
    local TEST_FILE_PATTERNS=$(echo "$CONFIG_JSON" | jq -r '
        .relaxedTestFileVerification.testFilePatterns // ["^tests?/", "_test\\.py$", "test_[^/]*\\.py$", "\\.test\\.(js|ts|jsx|tsx)$", "\\.spec\\.(js|ts|jsx|tsx)$"] | join("|")
    ' 2>/dev/null)
    local SINGLE_TEST_CMD=$(echo "$CONFIG_JSON" | jq -r --arg key "$TEST_COMMANDS_KEY" '
        .relaxedTestFileVerification.singleTestCommand[$key] // null
    ' 2>/dev/null)

    # --- Check transcript age ---
    local TRANSCRIPT_AGE=$(( $(date +%s) - $(stat -c %Y "$TRANSCRIPT_PATH" 2>/dev/null || stat -f %m "$TRANSCRIPT_PATH" 2>/dev/null) ))

    if [ "$FALLBACK_ENABLED" = "true" ] && [ "$TRANSCRIPT_AGE" -gt "$STALE_THRESHOLD" ]; then
        echo "DEBUG: Transcript is stale ($TRANSCRIPT_AGE seconds old), using fallback strategy" >&2

        if [ ! -f "$REPORT_FILE" ]; then
            echo "❌ No test report found ($REPORT_FILE missing)" >&2
            echo "You MUST run one of the following configured test commands EXACTLY as shown (no additions, modifications, or substitutes accepted):" >&2
            echo "  $ALLOWED_COMMANDS_LIST" >&2
            return 1
        fi

        local REPORT_TIME=$(stat -c %Y "$REPORT_FILE" 2>/dev/null || stat -f %m "$REPORT_FILE" 2>/dev/null)

        local MOST_RECENT_MODIFIED=$(git status --porcelain -z | tr '\0' '\n' | grep -E '^\s*[MADR]' | while IFS= read -r line; do
            local file="${line:3}"
            file="${file#\"}"
            file="${file%\"}"

            if [ -n "$EXCLUDE_FROM_TEST_REQ" ] && echo "$file" | grep -qE "($EXCLUDE_FROM_TEST_REQ)"; then
                continue
            fi

            if [ -f "$file" ]; then
                local FILE_TIME=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null)
                echo "$FILE_TIME $file"
            else
                echo "$(date +%s) $file (deleted)"
            fi
        done | sort -rn | head -1)

        if [ -z "$MOST_RECENT_MODIFIED" ]; then
            return 0
        fi

        local MOST_RECENT_TIME=$(echo "$MOST_RECENT_MODIFIED" | awk '{print $1}')
        local MOST_RECENT_FILE=$(echo "$MOST_RECENT_MODIFIED" | awk '{print $2}')

        if [ "$MOST_RECENT_TIME" -gt "$REPORT_TIME" ]; then
            local FILE_DATE=$(date -d @"$MOST_RECENT_TIME" 2>/dev/null || date -r "$MOST_RECENT_TIME" 2>/dev/null)
            local REPORT_DATE=$(date -d @"$REPORT_TIME" 2>/dev/null || date -r "$REPORT_TIME" 2>/dev/null)
            echo "❌ Tests have not been run since modifying $MOST_RECENT_FILE at $FILE_DATE" >&2
            echo "Test report ($REPORT_FILE) is from: $REPORT_DATE" >&2
            echo "You MUST run one of the following configured test commands EXACTLY as shown (no additions, modifications, or substitutes accepted):" >&2
            echo "  $ALLOWED_COMMANDS_LIST" >&2
            return 1
        fi

        local FAILED_COUNT=$(jq '.summary.failed // 0' "$REPORT_FILE" 2>/dev/null)
        if [ "$FAILED_COUNT" -gt 0 ]; then
            echo "❌ Test report shows $FAILED_COUNT failed test(s)" >&2
            echo "You MUST fix all failing tests before committing" >&2
            return 1
        fi

        return 0
    fi

    echo "DEBUG: Using transcript path: $TRANSCRIPT_PATH" >&2

    # --- Helper: Check if a test command succeeded ---
    check_test_success() {
        local test_id="$1"
        local TEST_TIME=$(cat "$TRANSCRIPT_PATH" | jq -r --arg id "$test_id" '
            select(.type == "assistant" and .message.content) |
            select(.message.content[] | select(.type == "tool_use" and .id == $id)) |
            .timestamp
        ' | head -1)

        local TEST_RESULT=$(cat "$TRANSCRIPT_PATH" | jq -r --arg id "$test_id" --arg test_time "$TEST_TIME" '
            select(.type == "user" and .message.content and (.message.content | type == "array") and .timestamp > $test_time) |
            .message.content[] |
            select(.type == "tool_result" and .tool_use_id == $id) |
            .is_error // false
        ' 2>/dev/null | head -1)

        if [ -z "$TEST_RESULT" ] || [ "$TEST_RESULT" = "false" ]; then
            echo "true"
        else
            echo "false"
        fi
    }

    # --- Get all file modifications (excluding excluded patterns) ---
    local ALL_MODIFICATIONS=$(cat "$TRANSCRIPT_PATH" | jq -c --arg exclude_pattern "$EXCLUDE_FROM_TEST_REQ" '
        select(.type == "assistant" and .message.content and (.message.content | type == "array")) |
        .message.content[] |
        select(.type == "tool_use" and (.name == "Edit" or .name == "Write" or .name == "MultiEdit")) |
        select(
            .input.file_path and
            (if $exclude_pattern != "" then .input.file_path | test($exclude_pattern; "ix") | not else true end)
        ) |
        {id: .id, name: .name, file: .input.file_path}
    ' 2>/dev/null)

    if [ -z "$ALL_MODIFICATIONS" ]; then
        return 0
    fi

    # --- Get the last modification ---
    local LAST_MODIFICATION=$(echo "$ALL_MODIFICATIONS" | tail -1)
    local LAST_MOD_ID=$(echo "$LAST_MODIFICATION" | jq -r '.id')
    local LAST_MOD_FILE=$(echo "$LAST_MODIFICATION" | jq -r '.file // "unknown file"')
    local LAST_MOD_TIME=$(cat "$TRANSCRIPT_PATH" | jq -r --arg id "$LAST_MOD_ID" '
        select(.type == "assistant" and .message.content) |
        select(.message.content[] | select(.type == "tool_use" and .id == $id)) |
        .timestamp
    ' | head -1)

    if [ -z "$LAST_MOD_TIME" ]; then
        echo "Warning: Could not determine timestamp of last modification" >&2
        return 0
    fi

    # --- Check for user approval to skip tests ---
    local SKIP_APPROVED=$(cat "$TRANSCRIPT_PATH" | jq -r --arg mod_time "$LAST_MOD_TIME" '
        select(.type == "user" and .message.content and .timestamp > $mod_time) |
        if (.message.content | type) == "string" then
            .message.content
        elif (.message.content | type) == "array" then
            .message.content[] | select(type == "string" or .type == "text") |
            if type == "string" then . else .text end
        else
            empty
        end
    ' 2>/dev/null | grep "SKIPPING TESTS APPROVED" | head -1)

    if [ -n "$SKIP_APPROVED" ]; then
        echo "DEBUG: User approved skipping tests" >&2
        return 0
    fi

    # --- Find all test commands (full suite runs) after the last modification ---
    local TEST_COMMANDS=$(cat "$TRANSCRIPT_PATH" | jq -c --arg mod_time "$LAST_MOD_TIME" --arg test_patterns "$TEST_COMMAND_PATTERNS" '
        select(.type == "assistant" and .message.content and (.message.content | type == "array") and .timestamp > $mod_time) |
        .message.content[] |
        select(.type == "tool_use" and .name == "Bash") |
        select(.input.command | test($test_patterns; "i")) |
        {id: .id, command: .input.command}
    ' 2>/dev/null)

    # --- Check if any full test suite run succeeded after the last modification ---
    if [ -n "$TEST_COMMANDS" ]; then
        while IFS= read -r test_cmd; do
            if [ -z "$test_cmd" ]; then continue; fi
            local TEST_ID=$(echo "$test_cmd" | jq -r '.id')
            if [ "$(check_test_success "$TEST_ID")" = "true" ]; then
                return 0  # Full test run passed after last modification
            fi
        done <<< "$TEST_COMMANDS"
    fi

    # --- No full test run after last modification - try relaxed verification if enabled ---
    if [ "$RELAXED_ENABLED" = "true" ]; then
        echo "DEBUG: No full test run since last modification, trying relaxed verification" >&2

        # Find the last successful full test run (this is our baseline)
        local LAST_FULL_TEST=$(cat "$TRANSCRIPT_PATH" | jq -c --arg test_patterns "$TEST_COMMAND_PATTERNS" '
            select(.type == "assistant" and .message.content and (.message.content | type == "array")) |
            .message.content[] |
            select(.type == "tool_use" and .name == "Bash") |
            select(.input.command | test($test_patterns; "i")) |
            {id: .id, command: .input.command}
        ' 2>/dev/null | while IFS= read -r test_cmd; do
            if [ -z "$test_cmd" ]; then continue; fi
            local tid=$(echo "$test_cmd" | jq -r '.id')
            if [ "$(check_test_success "$tid")" = "true" ]; then
                echo "$test_cmd"
            fi
        done | tail -1)

        if [ -z "$LAST_FULL_TEST" ]; then
            # No full passing test run exists in transcript - cannot use relaxed mode
            echo "❌ Tests have not been run since modifying $LAST_MOD_FILE at $LAST_MOD_TIME" >&2
            echo "You MUST run one of the following configured test commands EXACTLY as shown (no additions, modifications, or substitutes accepted):" >&2
            echo "  $ALLOWED_COMMANDS_LIST" >&2
            echo "" >&2
            echo "Note: Relaxed test verification requires at least one full passing test run as a baseline." >&2
            return 1
        fi

        # Get timestamp of last full passing test
        local FULL_TEST_ID=$(echo "$LAST_FULL_TEST" | jq -r '.id')
        local FULL_TEST_TIME=$(cat "$TRANSCRIPT_PATH" | jq -r --arg id "$FULL_TEST_ID" '
            select(.type == "assistant" and .message.content) |
            select(.message.content[] | select(.type == "tool_use" and .id == $id)) |
            .timestamp
        ' | head -1)

        echo "DEBUG: Found last full passing test at $FULL_TEST_TIME" >&2

        # Get all modifications SINCE the last full passing test run
        local MODS_SINCE_FULL_TEST=$(cat "$TRANSCRIPT_PATH" | jq -c --arg full_test_time "$FULL_TEST_TIME" --arg exclude_pattern "$EXCLUDE_FROM_TEST_REQ" '
            select(.type == "assistant" and .message.content and (.message.content | type == "array") and .timestamp > $full_test_time) |
            .message.content[] |
            select(.type == "tool_use" and (.name == "Edit" or .name == "Write" or .name == "MultiEdit")) |
            select(
                .input.file_path and
                (if $exclude_pattern != "" then .input.file_path | test($exclude_pattern; "ix") | not else true end)
            ) |
            {id: .id, name: .name, file: .input.file_path}
        ' 2>/dev/null)

        if [ -z "$MODS_SINCE_FULL_TEST" ]; then
            # No modifications since full test run - should have passed above, but allow
            return 0
        fi

        # Check if ALL modifications since full test are to test files
        local NON_TEST_MODS=""
        local TEST_FILE_MODS=""
        while IFS= read -r mod; do
            if [ -z "$mod" ]; then continue; fi
            local mod_file=$(echo "$mod" | jq -r '.file')
            if echo "$mod_file" | grep -qE "($TEST_FILE_PATTERNS)"; then
                TEST_FILE_MODS="${TEST_FILE_MODS}${mod}"$'\n'
            else
                NON_TEST_MODS="${NON_TEST_MODS}${mod_file}"$'\n'
            fi
        done <<< "$MODS_SINCE_FULL_TEST"

        if [ -n "$NON_TEST_MODS" ]; then
            # Non-test files were modified - require full test run
            local first_non_test=$(echo "$NON_TEST_MODS" | head -1)
            echo "❌ Tests have not been run since modifying $LAST_MOD_FILE at $LAST_MOD_TIME" >&2
            echo "You MUST run one of the following configured test commands EXACTLY as shown (no additions, modifications, or substitutes accepted):" >&2
            echo "  $ALLOWED_COMMANDS_LIST" >&2
            echo "" >&2
            echo "Note: Non-test files have been modified since the last full test run (e.g., $first_non_test)," >&2
            echo "so a full test suite run is required." >&2
            return 1
        fi

        # Only test files modified - check if each has been individually verified
        echo "DEBUG: Only test files modified since last full test run" >&2

        # Get unique test files modified since the full test run
        local UNIQUE_TEST_FILES=$(echo "$MODS_SINCE_FULL_TEST" | jq -r '.file' | sort -u)

        local UNVERIFIED_FILES=""
        while IFS= read -r test_file; do
            if [ -z "$test_file" ]; then continue; fi

            # Find the last modification to this specific file
            local FILE_LAST_MOD_TIME=$(cat "$TRANSCRIPT_PATH" | jq -r --arg file "$test_file" '
                select(.type == "assistant" and .message.content and (.message.content | type == "array")) |
                select(.message.content[] | select(.type == "tool_use" and (.name == "Edit" or .name == "Write" or .name == "MultiEdit") and .input.file_path == $file)) |
                .timestamp
            ' | tail -1)

            # Check if there's a test command AFTER this modification that includes this file
            local FILE_TESTED=$(cat "$TRANSCRIPT_PATH" | jq -c --arg mod_time "$FILE_LAST_MOD_TIME" --arg file "$test_file" --arg test_patterns "$TEST_COMMAND_PATTERNS" '
                select(.type == "assistant" and .message.content and (.message.content | type == "array") and .timestamp > $mod_time) |
                .message.content[] |
                select(.type == "tool_use" and .name == "Bash") |
                select(.input.command | (test($test_patterns; "i") and test($file; "i"))) |
                {id: .id, command: .input.command}
            ' 2>/dev/null)

            local FILE_VERIFIED="false"
            if [ -n "$FILE_TESTED" ]; then
                while IFS= read -r test_cmd; do
                    if [ -z "$test_cmd" ]; then continue; fi
                    local tid=$(echo "$test_cmd" | jq -r '.id')
                    if [ "$(check_test_success "$tid")" = "true" ]; then
                        FILE_VERIFIED="true"
                        echo "DEBUG: Test file $test_file has been individually verified" >&2
                        break
                    fi
                done <<< "$FILE_TESTED"
            fi

            if [ "$FILE_VERIFIED" = "false" ]; then
                UNVERIFIED_FILES="${UNVERIFIED_FILES}${test_file}"$'\n'
            fi
        done <<< "$UNIQUE_TEST_FILES"

        if [ -z "$UNVERIFIED_FILES" ]; then
            echo "DEBUG: All modified test files have been individually verified" >&2
            return 0
        fi

        # Some test files not verified - generate helpful error message
        local first_unverified=$(echo "$UNVERIFIED_FILES" | head -1)
        local unverified_count=$(echo "$UNVERIFIED_FILES" | grep -c .)

        echo "❌ Tests have not been run since modifying test file(s)" >&2

        if [ "$unverified_count" -eq 1 ]; then
            echo "   Modified test file: $first_unverified" >&2
        else
            echo "   Modified test files ($unverified_count total):" >&2
            echo "$UNVERIFIED_FILES" | while read -r f; do
                [ -n "$f" ] && echo "     - $f" >&2
            done
        fi

        echo "" >&2

        # Provide specific command suggestions
        if [ "$SINGLE_TEST_CMD" != "null" ] && [ -n "$SINGLE_TEST_CMD" ]; then
            echo "Please verify that the modified test(s) pass. Run:" >&2
            echo "$UNVERIFIED_FILES" | while read -r f; do
                if [ -n "$f" ]; then
                    local cmd="${SINGLE_TEST_CMD//\{file\}/$f}"
                    echo "  $cmd" >&2
                fi
            done
        else
            echo "Please verify that the modified test(s) pass by running them individually." >&2
            echo "Example commands that would be accepted:" >&2
            echo "$UNVERIFIED_FILES" | while read -r f; do
                if [ -n "$f" ]; then
                    # Generate example command based on file type
                    if echo "$f" | grep -qE '\.py$'; then
                        echo "  pytest $f" >&2
                    elif echo "$f" | grep -qE '\.(js|ts|jsx|tsx)$'; then
                        echo "  npm test -- $f" >&2
                    else
                        echo "  <test-runner> $f" >&2
                    fi
                fi
            done
            echo "" >&2
            echo "Tip: Configure 'relaxedTestFileVerification.singleTestCommand' in .claude/guardian.json" >&2
            echo "to customize the suggested command (e.g., 'pytest {file}' or 'npm test -- {file}')." >&2
        fi

        echo "" >&2
        echo "Alternatively, run a full test suite EXACTLY as configured (no modifications): $ALLOWED_COMMANDS_LIST" >&2
        return 1
    fi

    # Relaxed mode disabled - use standard error message
    echo "❌ Tests have not been run since modifying $LAST_MOD_FILE at $LAST_MOD_TIME" >&2
    echo "You MUST run one of the following configured test commands EXACTLY as shown (no additions, modifications, or substitutes accepted):" >&2
    echo "  $ALLOWED_COMMANDS_LIST" >&2
    return 1
}
