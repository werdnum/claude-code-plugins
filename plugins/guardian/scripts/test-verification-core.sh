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

    # --- Check transcript age ---
    local TRANSCRIPT_AGE=$(( $(date +%s) - $(stat -c %Y "$TRANSCRIPT_PATH" 2>/dev/null || stat -f %m "$TRANSCRIPT_PATH" 2>/dev/null) ))

    if [ "$FALLBACK_ENABLED" = "true" ] && [ "$TRANSCRIPT_AGE" -gt "$STALE_THRESHOLD" ]; then
        echo "DEBUG: Transcript is stale ($TRANSCRIPT_AGE seconds old), using fallback strategy" >&2

        if [ ! -f "$REPORT_FILE" ]; then
            echo "❌ No test report found ($REPORT_FILE missing)" >&2
            echo "You MUST run one of the following configured test commands before committing:" >&2
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
            echo "You MUST run one of the following configured test commands before committing:" >&2
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

    local LAST_MODIFICATION=$(cat "$TRANSCRIPT_PATH" | jq -c --arg exclude_pattern "$EXCLUDE_FROM_TEST_REQ" '
        select(.type == "assistant" and .message.content and (.message.content | type == "array")) |
        .message.content[] |
        select(.type == "tool_use" and (.name == "Edit" or .name == "Write" or .name == "MultiEdit")) |
        select(
            .input.file_path and
            (if $exclude_pattern != "" then .input.file_path | test($exclude_pattern; "ix") | not else true end)
        ) |
        {id: .id, name: .name, file: .input.file_path}
    ' 2>/dev/null | tail -1)

    if [ -z "$LAST_MODIFICATION" ]; then
        return 0
    fi

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

    local TEST_COMMANDS=$(cat "$TRANSCRIPT_PATH" | jq -c --arg mod_time "$LAST_MOD_TIME" --arg test_patterns "$TEST_COMMAND_PATTERNS" '
        select(.type == "assistant" and .message.content and (.message.content | type == "array") and .timestamp > $mod_time) |
        .message.content[] |
        select(.type == "tool_use" and .name == "Bash") |
        select(.input.command | test($test_patterns; "i")) |
        {id: .id, command: .input.command}
    ' 2>/dev/null)

    if [ -z "$TEST_COMMANDS" ]; then
        echo "❌ Tests have not been run since modifying $LAST_MOD_FILE at $LAST_MOD_TIME" >&2
        echo "You MUST run one of the following configured test commands before finishing:" >&2
        echo "  $ALLOWED_COMMANDS_LIST" >&2
        return 1
    fi

    local SUCCESSFUL_TEST=""
    while IFS= read -r test_cmd; do
        if [ -z "$test_cmd" ]; then continue; fi
        local TEST_ID=$(echo "$test_cmd" | jq -r '.id')
        local TEST_TIME=$(cat "$TRANSCRIPT_PATH" | jq -r --arg id "$TEST_ID" '
            select(.type == "assistant" and .message.content) |
            select(.message.content[] | select(.type == "tool_use" and .id == $id)) |
            .timestamp
        ' | head -1)

        local TEST_RESULT=$(cat "$TRANSCRIPT_PATH" | jq -r --arg id "$TEST_ID" --arg test_time "$TEST_TIME" '
            select(.type == "user" and .message.content and (.message.content | type == "array") and .timestamp > $test_time) |
            .message.content[] |
            select(.type == "tool_result" and .tool_use_id == $id) |
            .is_error // false
        ' 2>/dev/null | head -1)
        
        if [ -z "$TEST_RESULT" ] || [ "$TEST_RESULT" = "false" ]; then
            SUCCESSFUL_TEST="true"
            break
        fi
    done <<< "$TEST_COMMANDS"

    if [ -n "$SUCCESSFUL_TEST" ]; then
        return 0
    else
        echo "❌ Last test run failed after modifying $LAST_MOD_FILE at $LAST_MOD_TIME" >&2
        echo "You MUST fix failing tests before finishing" >&2
        return 1
    fi
}
