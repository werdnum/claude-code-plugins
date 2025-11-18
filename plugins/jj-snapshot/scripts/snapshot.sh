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

# Run jj status silently to create a snapshot
jj status &> /dev/null

exit 0
