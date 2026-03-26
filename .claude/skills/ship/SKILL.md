---
name: ship
description: "Approve and squash-merge GitHub PRs after verifying CI is green. Use when the user says 'ship it', 'merge PRs', 'ship PRs', 'land these PRs', wants to merge pull requests, or says /ship. Handles single PRs, multiple PRs by number, --all for every open PR by the user, or auto-detects the most recent PR from conversation context."
argument-hint: "[PR #s | --all | <empty for auto-detect>] [--hierarchical] [--dry-run]"
---

# Ship PRs

Approve and squash-merge GitHub PRs that have passing CI. Fix trivial merge conflicts along the way.

## Invocation

Parse `$ARGUMENTS` for:

1. **PR identifiers** — one of:
   - One or more PR numbers: `42 43 44` or `#42 #43`
   - `--all` — all open PRs authored by the current user in the current repo (explicit version of the default)
   - Empty — auto-detect from conversation context, then fall back to all user PRs in the repo (see below)
2. **`--hierarchical`** (optional) — merge PRs in dependency order, updating base branches as earlier PRs land
3. **`--dry-run`** (optional) — check CI and mergeability but don't actually merge

### Auto-detect logic (no PR numbers given and no `--all`)

Try these in order, stop at first match:

1. **Conversation context** — scan the current conversation for PR URLs or `#<number>` references tied to work you just did (e.g., a PR you created with `/fix-issue` or the worktree agent). Use the most recent one(s).
2. **All user PRs in the repo** — run `gh pr list --author @me --state open` in the current repo (or the repo mentioned in conversation). If PRs are found, use all of them.

If nothing is found, print usage and stop:
```
Usage: /ship [PR #s | --all] [--hierarchical] [--dry-run]
Examples:
  /ship 42
  /ship 42 43 44
  /ship --all
  /ship                  (auto-detects from context)
```

## Resolve repo context

Determine `OWNER/REPO` from:
1. If the current directory is inside a git repo, use its remote origin
2. If PR URLs were found in conversation context, extract from those

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
```

For `--all` or when multiple repos are involved, group PRs by repo and process each group.

## Workflow — for each PR

Process PRs sequentially (or in dependency order with `--hierarchical`).

### Step 1 — Fetch PR details

```bash
gh pr view $PR_NUMBER --json number,title,state,headRefName,baseRefName,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,author,isDraft
```

**Stop conditions** (skip this PR with a warning):
- PR is not in `OPEN` state
- PR is a draft
- Author is not `@me` and `--all` was used (safety: only auto-merge your own PRs)

### Step 2 — Check CI status

Extract the CI status from `statusCheckRollup`. Every check must be in a terminal state and passing.

| Check state | Action |
|---|---|
| All checks `SUCCESS` or `NEUTRAL` | Proceed |
| Any check `PENDING` or `IN_PROGRESS` | Report which checks are still running, skip this PR. Tell the user they can retry after CI finishes. |
| Any check `FAILURE` or `ERROR` | Report which checks failed with their names and URLs. Skip this PR. |

If there are no status checks at all, warn but proceed — some repos don't have required checks.

### Step 3 — Check mergeability and fix conflicts

Check the `mergeable` and `mergeStateStatus` fields:

| Status | Action |
|---|---|
| `MERGEABLE` / `CLEAN` | Proceed to merge |
| `CONFLICTING` | Attempt to fix (see below) |
| `BEHIND` | Attempt rebase (see below) |
| `BLOCKED` | Report why (missing reviews, branch protection). Skip unless the only blocker is approval (handled in Step 4). |
| `UNKNOWN` | Re-fetch after a few seconds. GitHub sometimes needs time to compute. |

#### Fixing merge conflicts

Only attempt fixes for **trivial** conflicts. The goal is to save you a click, not to make judgment calls about code.

1. **Clone/checkout the branch locally:**
   ```bash
   cd <repo-dir>
   git fetch origin
   git checkout $HEAD_BRANCH
   git rebase origin/$BASE_BRANCH
   ```

2. **For each conflicted file, assess triviality:**
   - **Trivial** (fix automatically):
     - Lockfiles (`uv.lock`, `poetry.lock`, `package-lock.json`) — regenerate using the repo's package manager
     - Whitespace-only or formatting conflicts
     - Non-overlapping import additions (both sides added different imports)
     - `__init__.py` `__all__` list ordering
     - CHANGELOG/version bumps where both sides added entries (keep both)
   - **Non-trivial** (abort and skip this PR):
     - Logic changes in the same function
     - Overlapping edits to the same lines
     - Structural changes (moved/renamed files where both sides edited)

3. **If all conflicts are trivial**, resolve them, continue the rebase, and force-push:
   ```bash
   git rebase --continue
   git push --force-with-lease origin $HEAD_BRANCH
   ```
   Wait a moment for GitHub to recompute mergeability, then re-check CI (force-push may re-trigger checks — if so, report that CI is re-running and skip to the next PR, or wait if there's only one PR).

4. **If any conflict is non-trivial**, abort the rebase and skip this PR:
   ```bash
   git rebase --abort
   ```
   Report which files had non-trivial conflicts.

### Step 4 — Approve

If the PR doesn't already have an approving review from the current user:

```bash
gh pr review $PR_NUMBER --approve --body "Approved via /ship — CI green, mergeability confirmed."
```

If approval fails (e.g., can't self-approve due to branch protection), note it and proceed to merge anyway — the merge will fail if approval is actually required, which is fine.

### Step 5 — Squash and merge

```bash
gh pr merge $PR_NUMBER --squash --delete-branch --auto
```

Use `--auto` so that if there's a brief delay in status propagation, GitHub will merge as soon as requirements are met rather than failing.

If `--dry-run` was specified, skip this step and instead print:
```
[dry-run] Would merge PR #<number>: <title>
```

### Step 6 — Handle `--hierarchical` chain

When `--hierarchical` is set, after merging a PR whose branch was the base for another PR in the list:

1. The downstream PR's base branch has been deleted (or merged into main)
2. Update the downstream PR's base to the next appropriate branch:
   ```bash
   gh pr edit $DOWNSTREAM_PR --base $NEW_BASE
   ```
3. Wait for CI to re-run on the rebased PR before proceeding

## Summary

After processing all PRs, print a table:

```
## Ship Results

| PR | Title | Status |
|----|-------|--------|
| #42 | feat: add widget | Merged |
| #43 | fix: cache bug | Merged |
| #44 | refactor: cleanup | Skipped — CI failing (lint) |
```

If any PRs were skipped, include a brief note on what to do:
- CI failing → "Fix the failing checks and run `/ship 44` again"
- Non-trivial conflicts → "Resolve conflicts manually, push, and run `/ship 44` again"
- Still running → "CI still in progress, try again in a few minutes"

## Edge Cases

| Scenario | Handling |
|---|---|
| No PRs found | Print usage |
| PR already merged | Skip with note |
| PR is a draft | Skip with note |
| CI re-triggered by force-push | Wait up to 2 minutes for checks to start, then report status |
| Rate limiting | Respect `gh` rate limit errors, wait and retry once |
| No git repo in cwd | Ask user which repo to target |
| `--all` finds 10+ PRs | List them and ask for confirmation before proceeding |
| Merge fails despite passing checks | Report the error from `gh pr merge` verbatim |
