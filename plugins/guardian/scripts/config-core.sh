#!/bin/bash

# Shared configuration helpers for the guardian hooks.

# Loads and merges guardian configuration from default, user, and project locations.
# Merging order: project > user > default.
load_guardian_config() {
    local base_config_path="${CLAUDE_PLUGIN_ROOT}/config/guardian-config.json"
    local user_config_path="$HOME/.config/claude-code/guardian.json"
    local project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    local project_config_path="${project_dir}/.claude/guardian.json"

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

# Reads a boolean config value, falling back to a default when the key is absent.
#
# jq's alternative operator yields the right-hand side when the left is `false`
# *or* null, so the common `.someFlag // true` idiom silently turns a
# configured `false` back into `true` -- making every such flag impossible to
# disable. This distinguishes "absent" from "explicitly false".
#
# Arguments:
#   $1: JSON string to read from
#   $2: jq filter selecting the flag, e.g. '.prCreated' (no `//` default)
#   $3: default, "true" or "false", used when the key is absent or unreadable
config_bool() {
    local json="$1"
    local filter="$2"
    local default="$3"
    local value

    value=$(echo "$json" | jq -r "$filter" 2>/dev/null) || value="null"
    case "$value" in
        true) echo "true" ;;
        false) echo "false" ;;
        *) echo "$default" ;;
    esac
}
