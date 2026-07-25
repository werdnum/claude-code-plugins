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

# If there are background tasks or scheduled (cron) tasks still in flight, allow
# exit. Claude Code now runs work in the background (background shells, agents,
# Monitor subscriptions) and re-awakens the session when those finish, so a stop
# here is expected rather than premature task abandonment. Blocking would force a
# busy-wait. These fields were added to the Stop hook payload in Claude Code
# v2.1.181; `length` works for both arrays and objects and yields 0 when absent.
BACKGROUND_TASK_COUNT=$(echo "$JSON_INPUT" | jq -r '(.background_tasks // []) | length' 2>/dev/null || echo 0)
SESSION_CRON_COUNT=$(echo "$JSON_INPUT" | jq -r '(.session_crons // []) | length' 2>/dev/null || echo 0)
if [ "${BACKGROUND_TASK_COUNT:-0}" -gt 0 ] || [ "${SESSION_CRON_COUNT:-0}" -gt 0 ]; then
    echo "Background tasks or scheduled tasks still in flight; allowing stop." >&2
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

# Honour the documented `skipInRemote` flag. It was present in the config schema
# but never read here, so remote sessions ran the full validation regardless.
SKIP_IN_REMOTE=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.skipInRemote // false')
if [ "$SKIP_IN_REMOTE" = "true" ] && [ "${CLAUDE_CODE_REMOTE:-false}" = "true" ]; then
    echo "Remote session and stopValidation.skipInRemote is set; allowing stop." >&2
    exit 0
fi

# --- Git / PR state helpers ---
# These are shared by both validation modes so the two code paths can't drift
# apart again. Every helper is written to be *quiet when it cannot be sure*:
# a check that cannot determine the answer must not manufacture a complaint.

# Current branch name, or empty for detached HEAD / not a git repo. Note that
# `rev-parse --abbrev-ref HEAD` prints the literal string "HEAD" when detached,
# which is not a branch and must never be fed to `gh pr list --head`.
git_current_branch() {
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
    [ "$branch" = "HEAD" ] && branch=""
    echo "$branch"
}

# Configured upstream (e.g. origin/feature-x), or empty when the branch has
# never been pushed.
git_upstream() {
    git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true
}

# Resolve the ref that this branch would be merged into. Prefers the remote's
# default branch, falling back to conventional names. Empty when nothing
# resolves, which callers treat as "unknown" rather than "no base".
git_base_ref() {
    local candidate
    candidate=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
    if [ -n "$candidate" ] && git rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
        echo "$candidate"
        return
    fi
    for candidate in origin/main origin/master main master; do
        if git rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
            echo "$candidate"
            return
        fi
    done
    echo ""
}

# Is this branch the trunk (or the remote's default branch)? Trunk branches
# never need a PR of their own.
is_base_branch() {
    local branch="$1"
    local base_ref
    [ -z "$branch" ] && return 0
    case "$branch" in
        main|master) return 0 ;;
    esac
    base_ref=$(git_base_ref)
    [ -n "$base_ref" ] && [ "${base_ref#origin/}" = "$branch" ]
}

# Number of commits on HEAD that are not on the base ref. Prints "unknown" when
# the base ref can't be resolved so callers can stay quiet instead of guessing.
git_commits_ahead_of_base() {
    local base_ref count
    base_ref=$(git_base_ref)
    if [ -z "$base_ref" ]; then
        echo "unknown"
        return
    fi
    count=$(git rev-list --count "${base_ref}..HEAD" 2>/dev/null || true)
    [ -z "$count" ] && count="unknown"
    echo "$count"
}

# Does the branch's *current* work already have a pull request?
# Prints "yes", "no", or "unknown". "unknown" covers every case where we cannot
# get a trustworthy answer: gh missing, not authenticated, no GitHub remote,
# network/API failure, unparseable output. Previously all of these collapsed
# into "0 PRs" via `|| echo "0"`, which turned any lookup *failure* into a
# confident "you never created a PR" complaint.
#
# A closed or merged PR only counts when its head commit is still the branch's
# head. Branches get reused after their PR lands -- reset onto the new trunk,
# then developed again -- and a bare "--state all" lookup would find that dead
# PR and report the new, entirely un-reviewed commits as already covered.
pr_exists_for_branch() {
    local branch="$1"
    local output head_sha result
    [ -z "$branch" ] && { echo "unknown"; return; }
    command -v gh >/dev/null 2>&1 || { echo "unknown"; return; }
    gh auth status >/dev/null 2>&1 || { echo "unknown"; return; }
    head_sha=$(git rev-parse HEAD 2>/dev/null || true)
    output=$(gh pr list --head "$branch" --state all --json state,headRefOid --limit 20 2>/dev/null) || { echo "unknown"; return; }
    result=$(printf '%s' "$output" | jq -r --arg head "$head_sha" '
        if type != "array" then "unknown"
        elif any(.[]; .state == "OPEN") then "yes"
        elif ($head != "" and any(.[]; .headRefOid == $head)) then "yes"
        else "no" end
    ' 2>/dev/null) || { echo "unknown"; return; }
    case "$result" in
        yes|no|unknown) echo "$result" ;;
        *) echo "unknown" ;;
    esac
}

# Does this branch carry work of its own? Prefers "commits ahead of the base
# branch", falling back to "has any commits at all" when the base ref cannot be
# resolved (single-branch checkouts, repos with no remote). The fallback keeps
# strict mode enforcing on layouts where the base is unknowable.
branch_has_own_work() {
    local commits_ahead="$1"
    if [ "$commits_ahead" = "unknown" ]; then
        [ -n "$(git log --oneline -1 2>/dev/null || true)" ]
        return
    fi
    [ "$commits_ahead" -gt 0 ]
}

# Should the "no PR" check run at all for this branch? This gate is the main
# fix for the check firing on sessions that had nothing to open a PR for.
# Returns 0 (run the check) only when a PR is genuinely the missing next step.
#
# $3 selects how much benefit of the doubt to give:
#   advisory (default) -- regular mode. Stay quiet on anything uncertain; a
#                         nagging warning is worse than a missed one.
#   strict             -- oneshot mode. The user configured `prCreated` as a
#                         hard requirement, so uncertainty must not be allowed
#                         to silently satisfy it.
should_check_pr() {
    local branch="$1"
    local commits_ahead="$2"
    local mode="${3:-advisory}"

    # Detached HEAD, or not on a branch at all.
    [ -z "$branch" ] && return 1

    # Trunk branches don't get PRs.
    is_base_branch "$branch" && return 1

    # No work of its own means nothing to open a PR for -- this is the case that
    # fired on read-only and question-answering sessions that merely happened to
    # be checked out on a feature branch. In strict mode an unresolvable base
    # falls back to "has any commits" instead of skipping the check.
    if [ "$mode" = "strict" ]; then
        branch_has_own_work "$commits_ahead" || return 1
        # Deliberately no upstream requirement here: `allCommitsPushed` reports
        # the missing push separately, and a strict checklist should surface
        # every outstanding requirement rather than hiding one behind another.
        return 0
    fi

    # We couldn't work out what this branch would merge into, so we can't know
    # whether it holds unmerged work. Stay quiet rather than guess.
    [ "$commits_ahead" = "unknown" ] && return 1
    [ "$commits_ahead" -gt 0 ] || return 1

    # The branch has never been pushed. Pushing comes first, and the unpushed
    # commits check already covers that; telling Claude to run `gh pr create`
    # here produces a second complaint about the same one missing step.
    [ -n "$(git_upstream)" ] || return 1

    return 0
}

# --- One-Shot Mode Validation ---
# ONESHOT_MODE may be unset; `set -u` made the bare `$ONESHOT_MODE` reference
# abort the hook outright whenever oneshotMode was enabled in config.
if [ "$ONESHOT_MODE_ENABLED" = "true" ] && [ -n "${ONESHOT_MODE:-}" ]; then
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
        current_branch=$(git_current_branch)
        commits_ahead=$(git_commits_ahead_of_base)

        # 2. Feature Branch Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.featureBranch // true')" = "true" ]; then
            if [ -n "$current_branch" ] && is_base_branch "$current_branch"; then
                ISSUES+=("❌ You're on the $current_branch branch - Create a feature branch.")
            fi
        fi

        # 3. Clean Working Dir Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.cleanWorkingDir // true')" = "true" ] && [ -n "$(git status --porcelain)" ]; then
            ISSUES+=("❌ Uncommitted changes found - You MUST commit all changes.")
        fi

        # 4. All Commits Pushed Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.allCommitsPushed // true')" = "true" ]; then
            upstream=$(git_upstream)
            if [ -n "$upstream" ]; then
                if [ -n "$(git log --oneline "$upstream"..HEAD 2>/dev/null || true)" ]; then
                    ISSUES+=("❌ Unpushed commits found - You MUST push all commits.")
                fi
            elif [ -n "$current_branch" ] && branch_has_own_work "$commits_ahead"; then
                # Only demand a push when we're on a real branch that actually
                # carries work of its own. A branch sitting level with the base
                # has nothing to push, and complaining about it just blocks the
                # stop. When the base ref can't be resolved, branch_has_own_work
                # falls back to "has any commits" so an unresolvable base can't
                # let unpushed work through this strict check.
                ISSUES+=("❌ No upstream branch set - You MUST push to a remote branch.")
            fi
        fi

        # 5. PR Created Check
        if [ "$(echo "$STRICT_REQS" | jq -r '.prCreated // true')" = "true" ]; then
            if should_check_pr "$current_branch" "$commits_ahead" strict && [ "$(pr_exists_for_branch "$current_branch")" = "no" ]; then
                ISSUES+=("❌ No PR created for branch '$current_branch' - You MUST create a PR with 'gh pr create'.")
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

BLOCKING_MESSAGES=()
WARNING_MESSAGES=()

# Anything not explicitly configured as "error" is advisory. Only "error"
# blocks the stop; see the exit handling at the bottom of this file.
add_message() {
    local type="$1"
    local message="$2"
    if [ "$type" = "error" ]; then
        BLOCKING_MESSAGES+=("$message")
    else
        WARNING_MESSAGES+=("$message")
    fi
}

# 1. Format and Lint
FORMAT_LINT_CONFIG=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.formatAndLint // {}')
if [ "$(echo "$FORMAT_LINT_CONFIG" | jq -r '.enabled // false')" = "true" ]; then
    mapfile -t commands < <(echo "$FORMAT_LINT_CONFIG" | jq -r '.commands[]')
    for cmd in "${commands[@]}"; do
        # Use bash -c instead of eval to reduce risk of code injection.
        # Redirect the command's stdout to stderr: this hook may emit a JSON
        # response on stdout, and formatters/linters routinely print there.
        # Mixing the two would leave stdout unparseable and silently drop the
        # systemMessage. stderr keeps the output visible for debugging.
        if ! bash -c "$cmd" >&2; then
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
    upstream=$(git_upstream)
    unpushed_ahead=$(git_commits_ahead_of_base)
    if [ -n "$upstream" ]; then
        if unpushed_commits=$(git log --oneline "$upstream"..HEAD 2>/dev/null); [ -n "$unpushed_commits" ]; then
            add_message "$UNPUSHED_LEVEL" "Unpushed commits detected."
        fi
    elif [ -n "$(git_current_branch)" ] && [ "$unpushed_ahead" != "unknown" ] && [ "$unpushed_ahead" -gt 0 ]; then
        # Branch carries commits but has no upstream at all. The PR check defers
        # to this message rather than telling Claude to open a PR for a branch
        # that was never pushed.
        add_message "$UNPUSHED_LEVEL" "Branch has commits but no upstream set; push with 'git push -u origin HEAD'."
    fi
fi

# 4. PR Created Check
NO_PR_LEVEL=$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.validation.noPr // "warn"')
if [ "$NO_PR_LEVEL" != "ignore" ]; then
    current_branch=$(git_current_branch)
    commits_ahead=$(git_commits_ahead_of_base)
    if should_check_pr "$current_branch" "$commits_ahead" && [ "$(pr_exists_for_branch "$current_branch")" = "no" ]; then
        add_message "$NO_PR_LEVEL" "No PR created for branch '$current_branch'. Consider running 'gh pr create'."
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
# Blocking issues (level "error") stop the session and are reported on stderr,
# which Claude Code feeds back to Claude.
if [ ${#BLOCKING_MESSAGES[@]} -gt 0 ]; then
    echo "✋ Before stopping, please review the following:" >&2
    for msg in "${BLOCKING_MESSAGES[@]}"; do printf '   - %b\n' "$msg" >&2; done
    for msg in "${WARNING_MESSAGES[@]}"; do printf '   - (warning) %b\n' "$msg" >&2; done
    echo "🚫 Blocking issues must be resolved before stopping." >&2
    exit "$(echo "$STOP_VALIDATION_CONFIG" | jq -r '.returnCode // 2')"
fi

# Warnings are advisory and must NOT block. Exiting 2 here made "warn" and
# "error" behave identically: every warn-level check -- and uncommittedChanges,
# unpushedCommits and noPr all default to "warn" -- forced Claude back into the
# loop for one more round on essentially every stop. Surface them as a
# systemMessage instead, which shows the text to the user without blocking.
if [ ${#WARNING_MESSAGES[@]} -gt 0 ]; then
    warning_text=$(printf '   - %b\n' "${WARNING_MESSAGES[@]}")
    jq -n --arg msg "✋ Guardian stop validation warnings:"$'\n'"$warning_text" \
        '{continue: true, suppressOutput: true, systemMessage: $msg}'
    exit 0
fi

exit 0
