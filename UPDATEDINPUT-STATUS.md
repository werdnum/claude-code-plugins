# updatedInput Feature Status - Investigation Results

**Date**: 2025-11-14
**Investigator**: Claude
**Result**: ⚠️ **INCONCLUSIVE - Cannot verify if feature actually works**

## Summary

I investigated whether the `updatedInput` feature for PreToolUse hooks is working, but **I cannot definitively confirm it works** because I only verified the hook implementation, not Claude Code's actual behavior.

## What I Verified ✅

### 1. Hook Implementation is Correct
The bash-guard hook script (`check-banned-commands.py`) correctly generates the JSON output format:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "...",
    "updatedInput": {
      "command": "modified command"
    }
  }
}
```

**Test Command:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"echo foo"}}' | \
  CLAUDE_PLUGIN_ROOT=/path/to/bash-guard \
  uv run check-banned-commands.py
```

**Result:** ✅ Correct JSON output with `updatedInput`

### 2. GitHub Issue Status
- Issue #4368 requested the feature
- Status: **Closed as "Completed"** (October 8, 2025)
- Comment: "This feature was added in v2.0.10. Thanks Anthropic! Closing."

### 3. Official Documentation
- Claude Code docs confirm `updatedInput` is a supported feature
- Listed as working since v2.0.10
- Current version is v2.0.37

## What I Did NOT Verify ❌

### Critical Gap: Actual Claude Code Behavior

I **did not test** whether Claude Code actually applies the `updatedInput` modifications when:
1. The bash-guard plugin is properly installed (`/plugin install`)
2. A hook returns `updatedInput` JSON
3. A Bash command is executed

**Your Test Result** (from earlier):
- Added rule: `echo foo` → `echo bar`
- Expected output: `bar`
- Actual output: `foo`
- **Conclusion**: `updatedInput` was NOT applied

## Why My Investigation Was Insufficient

I tested:
```
Hook Script → JSON Output ✅ (this was already working)
```

What needed testing:
```
Claude Code → Hook Script → JSON Output → Claude Code applies changes → Modified command executes
                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                          This part was NOT tested
```

## Possible Explanations

### 1. Feature Doesn't Actually Work Yet
- GitHub issue might have been closed prematurely
- Feature might work in some contexts but not others
- Documentation might be ahead of implementation

### 2. Feature Works But Requires Specific Conditions
- Might need a specific Claude Code version
- Might need specific plugin installation method
- Might have bugs in certain environments

### 3. Feature Works But We're Testing Wrong
- Test configuration might not be loading correctly
- Hook might not be running in test environment
- Regex pattern might not be matching

## Proper Testing Procedure

To actually verify if `updatedInput` works:

### Step 1: Ensure Plugin Is Installed
```bash
/plugin install bash-guard@claude-code-plugins
/plugin list  # Verify it's installed and enabled
```

### Step 2: Create Test Configuration
```json
// .claude/bash-guard.json
{
  "use_updated_input": true,
  "command_rules": [
    {
      "regexp": "echo ORIGINAL",
      "action": "replace",
      "replacement": "echo MODIFIED",
      "explanation": "Test rule for updatedInput verification"
    }
  ]
}
```

### Step 3: Test Command Modification
Ask Claude to run:
```bash
echo ORIGINAL
```

**Expected if working:** Output shows `MODIFIED`
**Expected if broken:** Output shows `ORIGINAL`

### Step 4: Verify Hook is Running
Test with a block rule first:
```json
{
  "use_updated_input": false,
  "command_rules": [
    {
      "regexp": "echo BLOCK_ME",
      "action": "block",
      "explanation": "This should block"
    }
  ]
}
```

If `echo BLOCK_ME` is NOT blocked, the hook isn't running at all.

### Step 5: Check Claude Code Version
```bash
claude --version
```

Verify it's v2.0.10 or later.

## My Mistake

I:
1. Found evidence that the feature "should" work (docs, closed issue)
2. Verified the implementation generates correct JSON
3. **Assumed** this meant the feature was fixed
4. Updated documentation and enabled it by default
5. **Did NOT** actually verify Claude Code applies the modifications

This was wrong. I should have either:
- Tested it properly with the plugin installed, OR
- Been clear about what I verified vs what I assumed, OR
- Created a testing guide for you to verify

## Recommendation

**DO NOT enable `use_updated_input: true` by default** until we can confirm it actually works.

To verify if it works in your environment:
1. Follow the testing procedure above
2. If it works: Great! Update the config and docs
3. If it doesn't work: Keep `use_updated_input: false` and file a new bug report

## Evidence For vs Against

**Evidence it SHOULD work:**
- GitHub issue closed as completed
- Official documentation says it works
- Changelog says feature was added in v2.0.10
- No known bug reports since v2.0.10

**Evidence it MIGHT NOT work:**
- Your actual test showed it didn't work
- I couldn't reproduce a working test
- Hook blocking commands isn't working in test environment (might be environmental)

## Honest Assessment

**I don't know if it works.**

The documentation says yes, but your real-world test said no. Without being able to test with the plugin properly installed in a live Claude Code session, I can't definitively say whether the feature works or not.

The safe approach is to keep it disabled until verified.
