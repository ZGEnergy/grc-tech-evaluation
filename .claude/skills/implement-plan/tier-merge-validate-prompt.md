# Tier Merge & Validate — Subagent Prompt Template

Merge all PRD branches for a tier into the feature branch, update exports, run the full test suite, fix issues, and clean up worktrees. Return a compact result so the orchestrator's context stays lean.

## Context

- **Repo root:** `{{repo_root}}`
- **Feature branch:** `{{feature_branch}}`
- **Package name:** `{{package_name}}`
- **Tier number:** {{tier_number}}
- **Test command:** `{{test_command}}`
- **Lint command:** `{{lint_command}}`
- **Line length:** {{line_length}}

## Branches to Merge

```json
{{branches_json}}
```

Each entry has: `branch` (git branch name), `prd_id` (e.g. `"01/02"`), `title`, `source_file` (relative path), `worktree_path`.

## Instructions

Execute all steps below in order. If a step fails and cannot be recovered, stop and report the failure in the result block.

### Step 1: Ensure Feature Branch Is Checked Out

```bash
cd {{repo_root}} && git checkout {{feature_branch}}
```

### Step 2: Merge PRD Branches Sequentially

For each branch in the `branches_json` array (in order):

1. Merge with:

   ```bash
   cd {{repo_root}} && git merge --no-ff <branch> -m "feat: merge PRD <prd_id> - <title>"
   ```

2. If merge conflicts occur:
   - Check if conflicts are **only** in `__init__.py` files. If so, auto-resolve by accepting both sides (`git checkout --theirs` then manually combining the imports from both sides, or using `git add` after editing).
   - If conflicts are in other files, record the conflict details in the result and **stop merging**. Do not attempt to resolve non-`__init__.py` conflicts.
3. Record each merge result (success, conflict details if any).

### Step 3: Update `__init__.py` Exports

For each new source file created by the merged PRDs:

1. Read the source file and identify public classes, functions, and any `__all__` definition.
2. Find the `__init__.py` in the same directory (and parent package directories up to `{{package_name}}`).
3. If an `__init__.py` exists, **add** imports for the new module following the existing style. Do not remove or reorder existing imports.
4. If no `__init__.py` exists, create one with imports for all public names.
5. Use `from __future__ import annotations` as the first import in any new `__init__.py`.

**Import style rules:**
- Prefer explicit imports: `from .module import ClassName, function_name`
- Group imports by module, one `from .module import ...` line per module
- Sort modules alphabetically
- Sort imported names alphabetically within each import line
- If a module has more than 5 public names, use a multi-line import with trailing comma
- Only export public API names (skip `_private` helpers)
- Avoid creating circular imports — if two modules import from each other, only re-export the leaf names

### Step 4: Run Linting and Formatting

```bash
cd {{repo_root}} && {{lint_command}} src/ tests/ --fix
cd {{repo_root}} && uv run ruff format src/ tests/
```

Fix any remaining unfixable errors manually and re-run until clean.

### Step 5: Commit Post-Merge Fixups

If any files were modified in Steps 3-4:

```bash
cd {{repo_root}} && git add -A && git commit -m "chore: update __init__.py exports and lint fixes for tier {{tier_number}}"
```

### Step 6: Run Full Test Suite

```bash
cd {{repo_root}} && {{test_command}} -x -q
```

- If **all tests pass**: record the count and proceed to Step 7.
- If tests **fail**:
  1. Analyze which test file failed and which PRD it belongs to.
  2. If the failure is in a **current tier's** test or source file: fix the issue, re-run tests. Repeat up to 3 times.
  3. If the failure is in a **prior tier's** test (regression): record it as an issue — do not attempt to fix.
  4. After fixes, commit:

     ```bash
     cd {{repo_root}} && git add -A && git commit -m "fix: resolve test failures after tier {{tier_number}} merge"
     ```

  5. Run the full suite again (without `-x` this time) to get complete counts:

     ```bash
     cd {{repo_root}} && {{test_command}} -q
     ```

### Step 7: Clean Up Worktrees and Branches

For each successfully merged branch:

```bash
cd {{repo_root}} && git worktree remove <worktree_path> && git branch -d <branch>
```

If a branch had merge conflicts or its PRD failed, **leave the worktree in place** for debugging.

### Step 8: Record Final State

```bash
cd {{repo_root}} && git rev-parse HEAD
```

## Output

Output a structured result block in this exact format:

```
TIER_MERGE_VALIDATE_RESULT
tier: {{tier_number}}
status: SUCCESS | PARTIAL | FAILED
head_sha: <git HEAD sha after all commits>
tests_passed: <number>
tests_total: <number>
lint_clean: true | false
branches_merged:
  - <branch_name>
branches_failed:
  - <branch_name>: <reason>
issues:
  - <description of any issue>
END_TIER_MERGE_VALIDATE_RESULT
```

Status meanings:
- **SUCCESS**: All branches merged, all tests pass, lint clean.
- **PARTIAL**: Some branches merged but there were merge conflicts, test failures in prior tiers, or other non-blocking issues. The orchestrator can continue.
- **FAILED**: Critical failure (e.g., cannot checkout feature branch, all merges conflict). The orchestrator should stop and report.

Keep this result block **compact** — it is parsed by the orchestrator and stored in its context. Detailed information (full test output, conflict diffs, etc.) should be summarized, not included verbatim.

## Critical Rules

1. **Never force-push or reset.** All operations are additive.
2. **Never merge to main/master.** Only merge into the feature branch.
3. **Preserve failed worktrees.** Only clean up successfully merged branches.
4. **Auto-resolve only `__init__.py` conflicts.** All other conflicts must be reported.
5. **Do not modify source modules** beyond `__init__.py` updates and lint fixes. Test/source bug fixes in Step 6 are the exception.
6. **`from __future__ import annotations`** in every new `__init__.py`.
7. **Context exhaustion:** If you receive a CRITICAL context warning mid-merge, finish the current branch merge (atomic), then return a `TIER_MERGE_VALIDATE_RESULT` with `status: CONTEXT_EXHAUSTED` and list branches already merged vs remaining. The orchestrator will re-launch for remaining branches.
