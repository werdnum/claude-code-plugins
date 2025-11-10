---
description: Comprehensive commit workflow with pre-commit checks and PR creation
---

# Commit and Create Pull Request

You are performing a comprehensive commit workflow. Follow these steps carefully and thoroughly:

## Step 1: Review All Changes

First, check ALL changes in the current working directory using:

!`git diff --stat HEAD`

And get the full diff to understand what has changed:

!`git diff HEAD`

Also check for any untracked files:

!`git status`

## Step 2: Pre-commit Checks

Before committing, perform all required pre-commit checks. Look for any of the following in the project:

- Check if there's a `.pre-commit-config.yaml` or similar pre-commit configuration
- Check if there are linting commands in `package.json`, `pyproject.toml`, `Makefile`, or similar
- Check if there are test commands that should be run
- Look for any commit hooks or CI configuration that indicates required checks

Run all applicable checks. Common checks include:

- Linting (e.g., `eslint`, `pylint`, `ruff`, etc.)
- Type checking (e.g., `mypy`, `tsc --noEmit`, etc.)
- Tests (e.g., `pytest`, `npm test`, `poe test`, etc.)
- Formatting (e.g., `prettier`, `black`, `rustfmt`, etc.)

**CRITICAL**: Ensure that ALL checks pass. Do not ignore any failures or write them off as pre-existing unless given EXPLICIT permission by the user. In most cases, failures are caused by your changes, albeit perhaps indirectly.

If any checks fail:
1. Investigate the failure thoroughly
2. Fix the issues
3. Re-run the checks
4. Only proceed when all checks pass

## Step 3: Review Your Changes

Carefully review all changes you've made:

1. Ensure all temporary code, debug statements, or experimental code is cleaned up
2. Verify that appropriate tests have been added for new functionality
3. Check that documentation has been updated if necessary
4. Confirm that no sensitive information (API keys, passwords, etc.) is being committed
5. Verify that the changes are complete and ready for review

## Step 4: Compose Detailed Commit Message

Create a comprehensive commit message following this format:

```
[One-line description in the imperative mood. Conventional commit prefixes are only to be added where they are useful or add important clarification]

[Details of all changes made if unclear from one-line description]

[Purpose of the change, explanation of any changes that are unclear or required considerable investigation or decisionmaking]
```

The commit message should:
- Explain **what** was done in detail
- Most importantly, explain **why** the changes were made
- Provide context about the problem being solved or feature being added
- Be clear enough that someone reading the history can understand the reasoning
- Include relevant details about implementation decisions when applicable

Example format:
```
Associate delegation flows with sub-conversation IDs in message history table

Added a new field `sub_conversation_id` to the `message_history` table, and populated it for messages that belong with delegation sub-conversations.

Filter out sub-conversations when populating message history in `processing.py`.

This ensures that sub-conversations ('subagents') do not 'leak' up into the main conversation, which fulfills one of the core goals of the processing profile.
```

## Step 5: Commit and Push to Feature Branch

1. If you're not already on a feature branch, create one with a descriptive name
2. Stage all relevant changes (be careful not to stage unintended files)
3. Create the commit with your detailed message
4. Push the branch to the remote repository

## Step 6: Create Pull Request

Unless otherwise requested by the user, create a Pull Request with:

- A title that summarizes the change (similar to the commit message first line)
- A description that includes:
  - Summary of changes
  - Why these changes were made
  - Any relevant context or background
  - Testing performed
  - Screenshots or examples if applicable

Use a similar format to the commit message but formatted appropriately for a PR description.

## Important Notes

- Do NOT skip any steps in this workflow
- Do NOT proceed with the commit if pre-commit checks fail
- Do NOT make assumptions about what checks are required - investigate the project configuration
- Ask the user for clarification if you're unsure about any aspect of the changes or requirements
- If you discover issues during the review process, fix them before proceeding
