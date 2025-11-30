---
description: Fetch and display all GitHub PR comments including inline review comments
allowed-tools: Bash(git branch:*), Bash(gh:*)
---

# Fetch All PR Comments

You are fetching all comments from a GitHub Pull Request, including inline review comments that are not shown by `gh pr view --comments`.

## Step 1: Determine PR Number and Repository

First, determine the current repository and PR number. Check if the user provided a PR number as an argument: $ARGUMENTS

If no PR number was provided, try to detect it from the current branch:

!`git branch --show-current`

Then check if there's an open PR for this branch:

!`gh pr view --json number,url,title 2>/dev/null || echo "No PR found for current branch"`

If no PR is found and no number was provided, ask the user to specify a PR number.

## Step 2: Get Repository Information

!`gh repo view --json nameWithOwner --jq '.nameWithOwner'`

## Step 3: Fetch Regular PR Comments

Fetch the standard issue-style comments on the PR:

```bash
gh pr view <PR_NUMBER> --comments --json comments --jq '.comments[] | "---\n**\(.author.login)** commented at \(.createdAt):\n\(.body)\n"'
```

## Step 4: Fetch Inline Review Comments

This is the key step - inline review comments are stored separately and require the API:

```bash
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments --jq '.[] | "---\n**\(.user.login)** commented on `\(.path)` (line \(.line // .original_line // "N/A")):\n\(.body)\n"'
```

## Step 5: Fetch Review Summaries

Also fetch the review summaries (approved, changes requested, etc.):

```bash
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/reviews --jq '.[] | select(.body != "") | "---\n**\(.user.login)** \(.state) at \(.submitted_at):\n\(.body)\n"'
```

## Step 6: Present Results

Organize and present all comments in a clear format:

### Output Format

Present the comments organized by type:

1. **Review Summaries** - Overall review decisions (approved, changes requested, commented)
2. **Inline Comments** - Comments on specific lines of code, grouped by file
3. **General Comments** - Discussion comments on the PR itself

For inline comments, include:
- File path
- Line number (if available)
- Author
- Comment body
- Whether it's part of a resolved conversation (if detectable)

### Handling Empty Results

If there are no comments of a particular type, note that explicitly rather than showing nothing.

## Example Commands

Here are the full commands to run (replace OWNER, REPO, and PR_NUMBER):

```bash
# Get PR details
gh pr view PR_NUMBER --json number,title,author,url,state

# Get regular comments
gh pr view PR_NUMBER --json comments

# Get inline review comments (the key missing feature)
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments

# Get review summaries
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/reviews
```

## Notes

- The `gh api` command is required for inline comments because `gh pr view --comments` only shows issue-style comments, not code review comments
- This is a known limitation of the GitHub CLI (see https://github.com/cli/cli/issues/5788)
- Inline comments may reference outdated code if the PR has been updated since the comment was made
