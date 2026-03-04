# PRD Implementer — Subagent Prompt Template

Implement the code and tests for a single PRD in an isolated git worktree.

**Detail level:** `{{detail_level}}`

## PRD Content

{{prd_content}}

## Repository Conventions

{{repo_conventions}}

## Working Environment

- **Repository:** `{{repo_name}}`
- **Worktree path:** `{{worktree_path}}`
- **Source file:** `{{worktree_path}}/{{source_file_path}}`
- **Test file:** `{{worktree_path}}/{{test_file_path}}`
- **Line length:** {{line_length}}

## Dependency Source Files

These are the source files from PRDs that this PRD depends on. Read them to understand the interfaces you will consume. They are already present in the worktree (merged from prior tiers or concurrent in this tier).

{{dependency_file_list}}

## Phase Plan Summary

{{phase_plan_summary}}

## Instructions

Implement the PRD above in the worktree. Follow this workflow exactly:

{% if detail_level == "task_card" %}

### Step 1: Read Dependencies (if any)

If the task card lists dependencies (`TC-NN`), read the corresponding source files from the worktree to understand the interfaces you will consume.

### Step 2: Write the Source Module

Write the source file to `{{worktree_path}}/{{source_file_path}}` using the Write tool.

Requirements:
- `from __future__ import annotations` as the first import in every file
- Design the data structures and API yourself based on the task card description and acceptance criteria — you have full design freedom
- Full type annotations on all function signatures
- Google-style docstrings on all public functions and classes
- Line length: {{line_length}} characters max
- Import dependencies from their actual module paths (check the dependency source files)
- If the source file directory doesn't exist yet, create any necessary `__init__.py` files

### Step 3: Write the Test Module

Write the test file to `{{worktree_path}}/{{test_file_path}}` using the Write tool.

Requirements:
- `from __future__ import annotations` as the first import
- One test function per acceptance criterion from the task card (2-4 tests)
- Use `pytest` fixtures for shared test data
- Self-contained test data — no external files, no network calls, no database connections
- Import the source module using its full package path
- If the test file directory doesn't exist yet, create any necessary `__init__.py` and `conftest.py` files

{% elif detail_level == "lean_prd" %}

### Step 1: Understand Dependencies

Read each dependency source file listed above. Note:
- Data structures (classes, dataclasses, enums) you will import
- Function signatures you will call
- Any conventions in the existing code (naming, patterns, imports)

### Step 2: Write the Source Module

Write the source file to `{{worktree_path}}/{{source_file_path}}` using the Write tool.

Requirements:
- `from __future__ import annotations` as the first import in every file
- Design the data structures and API yourself based on the PRD's Goals and Key Decisions — you have design freedom for anything not explicitly specified
- Full type annotations on all function signatures
- Google-style docstrings on all public functions and classes
- Line length: {{line_length}} characters max
- Import dependencies from their actual module paths (check the dependency source files)
- If the source file directory doesn't exist yet, create any necessary `__init__.py` files

### Step 3: Write the Test Module

Write the test file to `{{worktree_path}}/{{test_file_path}}` using the Write tool.

Requirements:
- `from __future__ import annotations` as the first import
- One test function per Acceptance Criteria item from the PRD (3-6 tests)
- Use `pytest` fixtures for shared test data
- Self-contained test data — no external files, no network calls, no database connections
- Use Protocol-based mocks for any SQL client or external service interfaces
- Test both happy paths and error cases as described in the PRD
- Import the source module using its full package path
- If the test file directory doesn't exist yet, create any necessary `__init__.py` and `conftest.py` files

{% else %}

### Step 1: Understand Dependencies

Read each dependency source file listed above. Note:
- Data structures (classes, dataclasses, enums) you will import
- Function signatures you will call
- Any conventions in the existing code (naming, patterns, imports)

If a PRD interface description conflicts with what actually exists in the dependency source file, **match the actual code** and note the deviation in your result.

### Step 2: Write the Source Module

Write the source file to `{{worktree_path}}/{{source_file_path}}` using the Write tool.

Requirements:
- `from __future__ import annotations` as the first import in every file
- All data structures from the PRD's `## Data Structures` section
- All functions from the PRD's `## API` section
- Full type annotations on all function signatures
- Google-style docstrings on all public functions and classes
- Line length: {{line_length}} characters max
- Import dependencies from their actual module paths (check the dependency source files)
- If the source file directory doesn't exist yet, create any necessary `__init__.py` files

### Step 3: Write the Test Module

Write the test file to `{{worktree_path}}/{{test_file_path}}` using the Write tool.

Requirements:
- `from __future__ import annotations` as the first import
- One test function per Success Criteria item from the PRD
- Use `pytest` fixtures for shared test data
- Self-contained test data — no external files, no network calls, no database connections
- Use Protocol-based mocks for any SQL client or external service interfaces
- Test both happy paths and error cases as described in the PRD
- Import the source module using its full package path
- If the test file directory doesn't exist yet, create any necessary `__init__.py` and `conftest.py` files

{% endif %}

### Step 4: Create `__init__.py` Files

For any new directories created (source or test), create `__init__.py` files. For source directories, add appropriate imports/exports. For test directories, the `__init__.py` can be empty.

### Step 5: Run Tests

Run the tests from the worktree root. Use the command prefix from `{{repo_conventions}}` — for `uv`-managed repos use `uv run`, for `pip`-managed repos run commands directly (with the venv activated).

```bash
cd {{worktree_path}} && uv run pytest {{test_file_path}} -v
```

(Adjust the `uv run` prefix based on the repo conventions above.)

If tests fail:
1. Read the error output carefully
2. Fix the source code or test code as needed
3. Re-run tests
4. Repeat up to 3 times. If still failing after 3 attempts, stop and report the failures.

### Step 6: Run Linting

Adjust `uv run` prefix based on repo conventions above.

```bash
cd {{worktree_path}} && uv run ruff check {{source_file_path}} {{test_file_path}} --fix
```

If ruff reports unfixable errors, manually fix them and re-run.

Then format:

```bash
cd {{worktree_path}} && uv run ruff format {{source_file_path}} {{test_file_path}}
```

### Step 7: Run Type Checking (if available)

Adjust `uv run` prefix based on repo conventions above.

```bash
cd {{worktree_path}} && uv run mypy {{source_file_path}} --ignore-missing-imports
```

Fix any type errors and re-run. If mypy is not installed, skip this step and note it.

### Step 8: Commit

Stage and commit all changes:

```bash
cd {{worktree_path}} && git add -A && git commit -m "feat: implement PRD {{prd_id}} - {{prd_title}}"
```

Use a HEREDOC for the commit message if it contains special characters.

{% if detail_level != "task_card" %}
### Step 9: Write Implementation Report

Write a detailed implementation report to `{{worktree_path}}/.implement-report.md` covering:

- **Files created:** full list of all files written or modified (relative paths from worktree root)
- **Test breakdown:** individual test names and pass/fail status
- **Design decisions:** any non-obvious choices made during implementation
- **Deviations from PRD:** any cases where actual dependency interfaces differed from PRD descriptions, with rationale
- **Issues encountered:** any problems hit during implementation, even if resolved

This report file stays in the worktree for reference as an untracked file. It is NOT committed and NOT included in the result block returned to the orchestrator.
{% endif %}

## Output

After completing all steps, output a structured result block in this exact format:

```
RESULT
status: SUCCESS | FAILED
prd_id: <two-digit PRD number>
phase: <two-digit phase number>
commit_hash: <short git commit hash>
tests_passed: <number>
tests_total: <number>
lint_clean: true | false
mypy_clean: true | false | skipped
END_RESULT
```

Keep this result block **compact** — it is parsed by the orchestrator and stored in its context window. Detailed information (files created, issues, deviations, design decisions) is in the `.implement-report.md` file written in Step 9.

## Context Exhaustion

On CRITICAL context warning (`CONTEXT MONITOR [CRITICAL]:`), finish the current step, then:

1. **Commit** work so far: `feat(wip): partial implement PRD {{prd_id}} - {{prd_title}}`
2. **Write** `{{worktree_path}}/.fragment-handoff.md` with header fields (`Subagent Type: prd-implementer`, `Unit: {{prd_id}}`, `Timestamp`, `Progress: steps N of 9`) and three sections: `## Completed` (steps done with key details), `## Remaining` (steps left), `## Artifacts on Disk` (files with complete/partial status).
3. **Return** RESULT block with `status: CONTEXT_EXHAUSTED` (same fields as the normal Output block, plus `commit_hash` of WIP commit; use `"not yet run"` for uncompleted checks).

## Critical Rules

1. **Never modify dependency files.** Only write to your assigned source file, test file, and `__init__.py` files for new directories.
2. **Match actual dependency interfaces**, not PRD descriptions, if they conflict. Note deviations.
3. **Self-contained tests.** No fixtures from conftest.py in other test directories. No external data files. No network calls.
4. **All tests must pass** before committing. If you cannot get tests to pass after 3 fix attempts, commit what you have and report FAILED status.
5. **No stubs or placeholders.** Every function and class must be fully implemented, not `pass` or `raise NotImplementedError`.
6. **`from __future__ import annotations`** in every `.py` file you create.
7. **Do not install packages.** The venv is shared from the repo root. If an import fails, check that you're using the right module path.
