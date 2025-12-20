#!/bin/bash
# Silently run jj status to snapshot the current repository state
# This hook runs after Edit, Write, or NotebookEdit operations

# Exit silently if jj is not available
if ! command -v jj &> /dev/null; then
    exit 0
fi

# Exit silently if not in a jj repository
if ! jj root &> /dev/null; then
    exit 0
fi

# Ensure CLAUDE_PLUGIN_ROOT is set for portability
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export CLAUDE_PLUGIN_ROOT
fi

# Run jj status silently to create a snapshot
jj status &> /dev/null

exit 0
