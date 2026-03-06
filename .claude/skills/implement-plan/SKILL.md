---
name: implement-plan
description: Use when the user wants to "implement a plan", "turn PRDs into code", "implement PRDs", "code up a plan", or "run the implementation workflow". Takes a plans directory and orchestrates parallel subagents that each implement one PRD in an isolated git worktree, respecting dependency ordering via topological tiers.
---

# Plan Implementation Orchestrator

Turn PRDs produced by `decompose-plan` into working code. Each PRD is implemented by a subagent in an isolated git worktree. PRDs are grouped into dependency tiers; within a tier, implementations run in parallel. Supports both single-repo and multi-repo plans.

## Invocation

Parse `$ARGUMENTS` for:
1. **Plans directory** (required) — path to the directory containing `executive-plan.md` and `phases/`
2. **Options** (optional):
   - `--phase NN` — implement only the specified phase (e.g., `--phase 02`)
   - `--prd NN/MM,NN/MM` — implement specific PRDs by phase/prd number (e.g., `--prd 02/01,02/04`)
   - `--parallel N` — max concurrent subagents (default: 4)

Examples:

```
/implement-plan plans/                                # full plan
/implement-plan plans/ --phase 02                     # one phase
/implement-plan plans/ --prd 02/01,02/04              # specific PRDs
/implement-plan plans/ --parallel 6                   # override max parallelism
```

If `$ARGUMENTS` is empty, ask the user for the plans directory path.

## State Machine

```
INIT → PARSE_PLAN → CONFIGURE → COMPUTE_TIERS → SETUP_TIER ⟷ IMPLEMENT_TIER → MERGE_TIER → DONE
                                                      ↑                                │
                                                      └──── (more tiers) ─────────────┘
```

Track the current state explicitly and report transitions to the user.

---

### State 1: INIT

1. Parse arguments: extract plans directory, `--phase`, `--prd`, `--parallel` options.
2. Verify the plans directory exists and contains `executive-plan.md` (or `ROOT_PLAN.md`). For Tier 2/3 plans, verify `phases/` subdirectory exists. For Tier 1 plans, verify `task-cards.md` exists instead.
3. Read the executive plan to get the project name for branch naming. Extract `complexity_tier` from the `## Complexity` section if present; default to **3** if missing (backward compatible).
3a. Set `detail_level` based on `complexity_tier`: 1 → `task_card`, 2 → `lean_prd`, 3 → `full_prd`.
4. **Check for session handoff first, then progress file** (see "Dual-Resume Coordination" and "Resume from Handoff" sections below for the complete procedure):
   - **Handoff check (Priority 1):** Check for `<plans-dir>/.session-handoff.md`. If found, validate the envelope, confirm with the user, and execute the handoff-mediated resume procedure (Scenarios A or C). If the handoff resume is taken, it subsumes the progress file check — do not execute step 4b independently.
   - **Progress file check (Priority 2):** If no handoff is found, or if the handoff is invalid/declined/mismatched, check for `<plans-dir>/implementation-progress.md`. If it exists, this is a progress-file-only resume (Scenario B). Read it, extract current state, current tier, per-repo TIER_BASE_REFs, and PRD statuses. For IN_PROGRESS PRDs, check if their worktree has a commit (via `git -C <worktree> log --oneline -1`): if committed, mark IMPLEMENTED; otherwise, re-launch. Skip to the appropriate state (SETUP_TIER for the current tier).
   - **Fresh start (Priority 3):** If neither file exists, proceed to steps 5-6 (Scenario D).
5. Report to user: plans directory validated, scope (full/phase/prd).
6. Transition to **PARSE_PLAN**.

### State 2: PARSE_PLAN

Parse PRDs (or task cards) into a compact registry without loading full content into the orchestrator's context.

#### Tier 1: Parse Task Cards

1. Read `<plans-dir>/task-cards.md`.
2. **Launch one PRD Parser subagent** using the Task tool:
   - Read the prompt template from `prd-parser-prompt.md` in this skill's directory.
   - Replace `{{detail_level}}` with `task_card`.
   - Replace `{{phase_number}}` with `01` (Tier 1 has no phases; use `01` as a synthetic phase).
   - Replace `{{phase_name}}` with the plan name slug.
   - Replace `{{prd_file_list}}` with the path to `task-cards.md`.
   - Use `subagent_type: "general-purpose"`.
3. Collect the JSON array returned. Build PRD_REGISTRY with entries containing: `prd_id`, `phase` (always `"01"`), `title`, `slug`, `source_file`, `test_file`, `repo`, `internal_deps`, `external_deps`, `test_count`.
4. Report to user: total task cards found.
5. Transition to **CONFIGURE**.

#### Tier 2 and Tier 3: Parse PRDs

1. List all phase directories: `Glob("phases/phase-*/")` in the plans directory.
2. If `--phase` was specified, filter to just that phase. If `--prd` was specified, note which PRDs to include.
3. For each phase, collect the list of PRD files: `Glob("phases/phase-<NN>-*/prds/prd-*.md")`.
4. **Launch one PRD Parser subagent per phase in parallel** using the Task tool:
   - Read the prompt template from `prd-parser-prompt.md` in this skill's directory.
   - Replace `{{detail_level}}` with `lean_prd` (Tier 2) or `full_prd` (Tier 3).
   - Replace `{{phase_number}}` with the phase number (e.g., `01`).
   - Replace `{{phase_name}}` with the phase directory slug (e.g., `data-ingestion`).
   - Replace `{{prd_file_list}}` with the newline-separated list of PRD file paths for that phase.
   - Use `subagent_type: "general-purpose"`.
5. Collect the JSON arrays returned by each subagent. Merge into a single PRD_REGISTRY — an array of objects, each with: `prd_id`, `phase`, `title`, `slug`, `source_file`, `test_file`, `repo`, `internal_deps`, `external_deps`, `test_count`.
6. If `--prd` was specified, filter the registry to only the requested PRDs (but keep their dependency PRDs in the registry for reference, marked as `"scope": "dependency_only"`).
7. Report to user: total PRDs found, PRDs in scope, per-phase breakdown.
8. Transition to **CONFIGURE**.

### State 2.5: CONFIGURE

Build the REPO_REGISTRY and set up per-repo state. This runs after PARSE_PLAN because repo detection depends on the parsed PRD registry.

1. **Determine repo mode**:
   - Collect all unique non-null `repo` values from PRD_REGISTRY.
   - If all `repo` values are `null` OR only one unique `repo` value exists → **single-repo mode** (`MULTI_REPO = false`).
   - If multiple unique `repo` values exist → **multi-repo mode** (`MULTI_REPO = true`).

2. **Build REPO_REGISTRY**:
   - **Single-repo mode (MULTI_REPO = false)**: Detect the repo using the existing method — read the first PRD's `## File Location`, walk up from the source path to find the directory containing `pyproject.toml`. Build a single-entry REPO_REGISTRY:

     ```
     REPO_REGISTRY = {
       "<repo_name>": {
         "root": "<absolute path to repo root>",
         "package_name": "<package from source path>",
         "conventions": "<extracted from CLAUDE.md>",
         "feature_branch": "implement/<plan-slug>",
         "tier_base_ref": "<HEAD sha>",
         "pkg_manager": "uv" | "pip",
         "test_command": "uv run pytest" | "pytest",
         "lint_command": "uv run ruff check" | "ruff check",
         "line_length": 100
       }
     }
     ```

   - **Multi-repo mode (MULTI_REPO = true)**: For each unique repo name from the PRD registry:
     a. Resolve root path: `<workspace>/<repo_name>/` (where `<workspace>` is the workspace root directory).
     b. Verify the directory exists and contains `pyproject.toml`.
     c. Read `<repo_root>/CLAUDE.md` and extract conventions (package manager, test/lint commands, line length, patterns).
     d. Extract the package name from the first PRD targeting this repo.
     e. Build a REPO_REGISTRY entry as above.

3. **Detect cross-repo dependencies** (only when `MULTI_REPO = true`):
   - For each repo in REPO_REGISTRY, read its `pyproject.toml` and extract the `[project.dependencies]` and `[project.optional-dependencies]` lists.
   - Build a REPO_DEPS map: `{ "market-ercot": ["market-framework"], ... }` — which repos depend on which other repos in the registry.
   - This is used later in SETUP_TIER for cross-repo dependency sync.

4. **Create feature branches**:
   - Derive a slug from the project name (e.g., `ercot-power-flow-scenario-gen`).
   - For each repo in REPO_REGISTRY:
     a. `cd <repo_root> && git branch implement/<plan-slug>` (create branch ref without checking it out — all work happens in worktrees).
     b. Store HEAD as `tier_base_ref` in that repo's REPO_REGISTRY entry.

5. **Write initial progress file** with metadata section (plans directory, repos, feature branch, scope, max parallelism, current state: CONFIGURE, Repo State table, timestamps).
6. Report to user: repos detected (`MULTI_REPO` mode or single), feature branches created, conventions extracted.
7. Transition to **COMPUTE_TIERS**.

### State 3: COMPUTE_TIERS

Topological sort on the dependency graph to group PRDs into implementation tiers.

1. Build a dependency graph from PRD_REGISTRY: nodes are `"phase/prd_id"` strings, edges are from `internal_deps`.
2. Validate: check for cycles (report and abort if found), check for missing dependencies (warn if a dep references a PRD not in the registry).
3. **Cross-repo dependency validation** (only when `MULTI_REPO = true`): If two PRDs in the same computed tier have a cross-repo dependency between them (PRD A in repo X depends on PRD B in repo Y, or vice versa via REPO_DEPS), bump the dependent PRD to the next tier. This ensures cross-repo sync can happen between tiers.
4. Compute tiers via Kahn's algorithm:
   - Tier 0: PRDs with no unmet internal dependencies (or whose dependencies are all `"scope": "dependency_only"` and already exist in the codebase).
   - Tier N: PRDs whose dependencies are all in Tiers 0..N-1.
5. If `--prd` was specified, exclude `"scope": "dependency_only"` PRDs from actual implementation — they are reference-only.
6. Annotate each tier with `repos_touched` — the set of repo names that have PRDs in that tier.
7. Cross-check tier ordering against phase plan `## Deliverable Dependencies` sections for sanity. Warn if the computed tiers differ from the documented implementation tiers (but use the computed tiers — they reflect actual dependency analysis).
8. Write the PRD Status table to the progress file with all PRDs, their computed tiers, and status PENDING.
9. Report to user: number of tiers, PRDs per tier, repos per tier, any warnings.
10. Set CURRENT_TIER = 0. Transition to **SETUP_TIER**.

### State 4: SETUP_TIER

Prepare worktrees for each PRD in the current tier.

0. **Cross-repo dependency sync** (only when `MULTI_REPO = true` and CURRENT_TIER > 0):
   - For each repo R in this tier's `repos_touched`:
     - Check if R depends on any repo modified in prior tiers (using REPO_DEPS and prior tiers' `repos_touched`).
     - If so, for each modified upstream repo A:
       1. Build a dev release: `cd <repo_a_root> && uv build` (or `python -m build` for pip-managed repos).
       2. Publish to private index: `uv publish --index zge` (or `twine upload --repository zge`).
       3. Bump the version pin in repo R's `pyproject.toml` for the dependency on A.
       4. Sync: `cd <repo_r_root> && uv sync` (or `pip install -e ".[dev]"` for pip-managed repos).
   - **Report to user before executing** — this is a heavyweight step that publishes packages. Summarize what will be published and where.

1. Filter PRD_REGISTRY to PRDs in CURRENT_TIER with status PENDING (skip already-completed on resume).
2. For each PRD in the tier:
   a. Derive branch name: `implement-prd-<phase><prd_id>-<slug>` (e.g., `implement-prd-0101-schema`).
   b. Derive worktree path: `<workspace>/worktrees/<repo_name>/implement-prd-<phase><prd_id>-<slug>` (where `<workspace>` is the workspace root directory and `<repo_name>` is from the PRD's `repo` field or the single repo name).
   c. Create worktree: `git worktree add <worktree_path> -b <branch_name> <REPO_REGISTRY[prd.repo]["tier_base_ref"]>` (run from the PRD's repo root: `REPO_REGISTRY[prd.repo]["root"]`).
   d. Share the venv: `ln -s <REPO_REGISTRY[prd.repo]["root"]>/.venv <worktree_path>/.venv`.
   e. Verify the environment using the repo-specific command: `cd <worktree_path> && <REPO_REGISTRY[prd.repo]["test_command"]> python -c "import <package>"`. If this fails, report and skip the PRD.
   f. Update PRD status to SETUP_COMPLETE in the progress file.
3. Report to user: worktrees created, any setup failures.
4. Transition to **IMPLEMENT_TIER**.

### State 5: IMPLEMENT_TIER

Launch parallel subagents to implement each PRD in the current tier.

1. Collect PRDs in CURRENT_TIER with status SETUP_COMPLETE.
2. Determine batch size: `min(tier_size, max_parallelism)`. If tier is larger than max_parallelism, process in batches.
3. For each batch, launch PRD Implementer subagents in parallel using the Task tool:
   - Read the prompt template from `prd-implementer-prompt.md` in this skill's directory.
   - Replace template variables (look up per-repo values from `REPO_REGISTRY[prd.repo]`):
     - `{{detail_level}}`: `task_card`, `lean_prd`, or `full_prd` (from orchestrator's `detail_level` variable).
     - `{{prd_content}}`: Read the full PRD file (or task card section) and pass its content.
     - `{{prd_id}}`: The two-digit PRD number (e.g., `01`).
     - `{{prd_title}}`: The PRD title from the registry.
     - `{{repo_name}}`: The repo directory name from the PRD's `repo` field (or the single repo name).
     - `{{repo_conventions}}`: `REPO_REGISTRY[prd.repo]["conventions"]` (package manager, test command, lint rules, line length, patterns).
     - `{{worktree_path}}`: The absolute worktree path for this PRD.
     - `{{source_file_path}}`: The source file path from the PRD registry (relative to repo root, used within worktree).
     - `{{test_file_path}}`: The test file path from the PRD registry.
     - `{{dependency_file_list}}`: For each internal dependency, the source file path. The subagent reads these to understand interfaces. Use paths relative to the worktree (which has the merged code from prior tiers).
     - `{{phase_plan_summary}}`: Read and pass the parent phase plan content (~200 word summary). For Tier 1, pass empty string (no phase plans exist).
     - `{{line_length}}`: `REPO_REGISTRY[prd.repo]["line_length"]`.
   - Use `subagent_type: "general-purpose"`.
   - Update PRD status to IN_PROGRESS before launching.
4. Collect results from each subagent. Each returns a compact RESULT block with: `status` (SUCCESS/FAILED), `prd_id`, `phase`, `commit_hash`, `tests_passed`, `tests_total`, `lint_clean` (bool), `mypy_clean` (bool). Detailed information (files created, issues, deviations) is in the worktree's `.implement-report.md` file.
5. For each result:
   - SUCCESS: Update PRD status to IMPLEMENTED. Record test counts.
   - FAILED: **Retry once** — re-launch the subagent with the error context appended to the prompt. If still failing, mark as FAILED and mark all downstream dependents as SKIPPED_BLOCKED.
6. Update the progress file with results.
7. Report to user: successes, failures, retries, any blocked PRDs.
8. Transition to **MERGE_TIER**.

### State 6: MERGE_TIER

Delegate the merge+validate cycle to subagents. In multi-repo mode, launch one merge subagent per repo (in parallel); in single-repo mode, launch one.

1. **Group branches by repo**: Partition the PRDs in CURRENT_TIER with status IMPLEMENTED by their `repo` field.
2. For each repo with branches to merge, build `branches_json` — a JSON array of objects:

   ```json
   [
     {"branch": "implement-prd-0101-schema", "prd_id": "01/01", "title": "Schema", "source_file": "src/.../schema.py", "worktree_path": "/abs/path/to/worktree"}
   ]
   ```

3. **Launch one Tier Merge & Validate subagent per repo** (parallel if multiple repos in the same tier):
   - Read the prompt template from `tier-merge-validate-prompt.md` in this skill's directory.
   - Replace template variables from `REPO_REGISTRY[repo]`:
     - `{{repo_root}}` → `REPO_REGISTRY[repo]["root"]`
     - `{{feature_branch}}` → `REPO_REGISTRY[repo]["feature_branch"]`
     - `{{package_name}}` → `REPO_REGISTRY[repo]["package_name"]`
     - `{{tier_number}}` → CURRENT_TIER
     - `{{branches_json}}` → the JSON array for this repo
     - `{{test_command}}` → `REPO_REGISTRY[repo]["test_command"]`
     - `{{lint_command}}` → `REPO_REGISTRY[repo]["lint_command"]`
     - `{{line_length}}` → `REPO_REGISTRY[repo]["line_length"]`
   - Use `subagent_type: "general-purpose"`.
4. Parse each `TIER_MERGE_VALIDATE_RESULT` block. Extract: `status`, `head_sha`, `tests_passed`, `tests_total`, `branches_merged`, `branches_failed`, `issues`.
5. Process results per repo:
   - For each branch in `branches_merged`: update the corresponding PRD status to VALIDATED.
   - For each branch in `branches_failed`: update the PRD status to FAILED and mark downstream dependents as SKIPPED_BLOCKED.
   - If any repo's `status` is FAILED: report to the user and ask how to proceed.
6. **Update per-repo tier_base_ref**: Set `REPO_REGISTRY[repo]["tier_base_ref"]` to the returned `head_sha` for each repo.
7. Update the progress file: Tier Merge Log entry with merge results per repo, test counts, and any issues.
8. If more tiers remain: increment CURRENT_TIER, transition to **SETUP_TIER**.
9. If no more tiers: transition to **DONE**.

### State 7: DONE

Final validation and summary report.

1. Run the complete test suite per repo (parallel if `MULTI_REPO = true`) — no `-x` flag, run all tests.
2. Run lint and type checks per repo.
3. Generate the final summary and report to the user:

```
## Implementation Complete

**Feature branch:** implement/<plan-slug>

### Repos
| Repo | Root | Feature Branch | Tests |
|------|------|----------------|-------|
| <repo_name> | <path> | implement/<slug> | <pass>/<total> |

### Results
| Status | Count |
|--------|-------|
| VALIDATED | <N> |
| FAILED | <N> |
| SKIPPED_BLOCKED | <N> |

### Test Summary
- Total tests: <N>
- Passing: <N>
- Failing: <N>

### PRD Details
| Phase | PRD | Title | Repo | Status | Tests | Files |
|-------|-----|-------|------|--------|-------|-------|
| 01 | 01 | Schema | ercot-power-flow-poc | VALIDATED | 13/13 | schema.py, test_schema.py |

### Issues
<list any open issues>

### Files Created
<list all new files, grouped by repo>

### Next Steps
- Review the feature branch(es): `git log --oneline implement/<plan-slug>`
- Run full test suite: `uv run pytest -v`
- Merge when ready: `git merge implement/<plan-slug>`
```

1. Update progress file with final state DONE and timestamp.
2. Output: `<promise>IMPLEMENTATION COMPLETE</promise>`

## Resumability

The progress file (`<plans-dir>/implementation-progress.md`) enables resume across sessions:

- **On INIT**: If progress file exists, read it and restore state:
  - CURRENT_TIER, per-repo TIER_BASE_REFs (from Repo State table), PRD statuses, feature branch names, MULTI_REPO flag
  - Rebuild REPO_REGISTRY from the Repo State table
  - For IN_PROGRESS PRDs: check worktree for commit → if committed, mark IMPLEMENTED; else re-launch
  - For SETUP_COMPLETE PRDs: verify worktree still exists → if yes, proceed to IMPLEMENT_TIER; else re-setup
  - Skip VALIDATED tiers entirely
  - Resume from the earliest incomplete state

- **Progress file update frequency**: Update after every state transition and after each PRD status change. Always write timestamps.

## Subagent Dispatch

To launch a subagent:

1. Read the appropriate prompt template file from this skill's directory using the Read tool.
2. Replace all `{{variable}}` placeholders with actual values.
3. Launch via the Task tool with `subagent_type: "general-purpose"`.
4. When launching multiple independent subagents (e.g., parallel PRD implementations within a tier), use a single message with multiple Task tool calls.

## Context Management

To avoid blowing the orchestrator's context window:

- **PRD registry**: ~6 lines per PRD (compact JSON, includes `repo` field). For 100 PRDs, this is ~600 lines — manageable.
- **REPO_REGISTRY**: ~10 lines per repo. Typically 1-5 repos — negligible.
- **PRD content**: Never loaded into the orchestrator. Each PRD's full content is read only by its dedicated subagent.
- **Phase plans**: Summarized to ~200 words when passed as context to implementer subagents.
- **Dependency source files**: Passed as file paths to subagents — they read the files themselves.
- **Test output**: Only failure summaries are kept in the orchestrator; full output stays in subagent context.
- **Merge+validate delegation**: The entire merge, `__init__.py` fixup, lint, test, and cleanup cycle is delegated to a single subagent per repo per tier. The orchestrator only sees the compact `TIER_MERGE_VALIDATE_RESULT` block (~10 lines), not the verbose output from each git merge, ruff run, and pytest execution.
- **Implementer results**: Each PRD implementer returns only a compact ~8-line `RESULT` block. Detailed information (files created, issues, deviations) is written to `.implement-report.md` in the worktree, readable on demand but not loaded into the orchestrator's context.

## Guardrails

- **Max parallelism**: Configurable via `--parallel` (default 4). Never launch more subagents than this limit.
- **Feature branch only**: Never merge to main/master. All work happens on `implement/<plan-slug>`.
- **Failed PRDs don't block independent PRDs**: Only downstream dependents are blocked.
- **All file writes reported**: After each state transition, report what changed to the user.
- **Subagent scope**: Each implementer subagent only touches its assigned source file, test file, and `__init__.py` for new directories. Never modify dependency files.
- **No force operations**: Never `git push --force`, `git reset --hard`, or `git clean -f`.
- **Worktree cleanup**: Successful worktrees are cleaned up after merge. Failed worktrees are preserved for debugging.
- **Retry budget**: Each PRD gets at most one retry. After that, it's marked FAILED.
- **Cross-repo sync confirmation**: When `MULTI_REPO = true`, always report to the user before publishing dev releases or bumping cross-repo dependencies.

## Context Monitoring Integration

See `.claude/skills/shared/context-monitoring-reference.md` for shared procedures (warning recognition, envelope format, write/resume protocols, handoff lifecycle, subagent continuation protocol).

The orchestrator receives context utilization warnings from the Phase 1 PostToolUse hook. Track three in-memory variables: `DEGRADATION_SEVERITY` (null|CAUTION|WARNING|CRITICAL), `DEGRADED_MAX_PARALLEL` (effective parallelism cap), and `ORIGINAL_MAX_PARALLEL` (initial value for reporting).

### Atomic Operations

After each atomic operation completes, check for degradation signals before starting the next. Atomic boundaries per state: INIT and COMPUTE_TIERS run as single units. PARSE_PLAN and IMPLEMENT_TIER: one subagent batch (all launched subagents must return). CONFIGURE: one numbered step. SETUP_TIER: one PRD's worktree setup (steps a-f). MERGE_TIER: one repo's merge subagent. DONE: entire state.

### CAUTION Behavior

1. **Reduce parallelism:** Set `DEGRADED_MAX_PARALLEL = min(current, 2)`. This is sticky — never increased back.
2. **Omit phase plan summaries:** Replace `{{phase_plan_summary}}` with empty string in implementer prompts.
3. **Annotate progress file** with a DEG-001 issue entry noting the timestamp and parallelism reduction.
4. **Continue execution** with reduced concurrency.

### WARNING Behavior

1. **Finish the current atomic operation.** Do not interrupt mid-operation.
2. **Do not start new work.** No new batches in IMPLEMENT_TIER, no new repo merges in MERGE_TIER, no new worktree setups in SETUP_TIER, no state advancement from CONFIGURE or COMPUTE_TIERS.
3. **Escalate DEG-001** to WARNING in the progress file.
4. **Begin mentally assembling handoff context** (preparation for potential CRITICAL). No file written yet.
5. **Report to user:** current state, tier, completed/in-progress counts, and that no new work will start.
6. **Wait** for CRITICAL or session end. If session ends without CRITICAL, the progress file captures state for normal resume.

### CRITICAL Behavior

1. **Stop all new work.** No new subagents, worktrees, batches, or state transitions.
2. **Execute the Handoff Write Protocol** (see below).
3. **Escalate DEG-001** to CRITICAL. Mark unreturned IN_PROGRESS PRDs as `IN_PROGRESS (interrupted)`.
4. **Report to user** with handoff path, progress file path, and resume command: `/implement-plan <plans-dir>`.
5. **End the response.** No further tool calls. Do NOT output completion signals or promise tags — the task is unfinished; only this session's context is exhausted. If running inside an iterative wrapper (e.g., Ralph Loop), let the wrapper re-invoke with fresh context. If user asks anything after stopping, respond with the context-limit message from the shared reference.

### Subagent CONTEXT_EXHAUSTED Handling

Continuation protocol per shared reference. Skill-specific handling:

**IMPLEMENT_TIER — PRD Implementer:** Read `.fragment-handoff.md` from the PRD's worktree. Build a continuation prompt referencing committed files and remaining steps only. Re-launch in the same worktree. On budget exhaustion, mark based on partial progress: tests pass → IMPLEMENTED; otherwise FAILED with note "context exhausted."

**PARSE_PLAN — PRD Parser:** If the parser returns a partial JSON array (last entry has `"partial": true`), re-launch with only the unparsed PRD files. Merge the two arrays into the full PRD_REGISTRY.

**MERGE_TIER — Tier Merge & Validate:** If the merge subagent returns `CONTEXT_EXHAUSTED` with a list of merged vs remaining branches, re-launch with only the remaining branches.

**Budget tracking:** `continuation_count` is per PRD (implementer), per phase (parser), or per repo-tier (merge) — independent of `retry_count`.

### Handoff Write Protocol

Triggered at CRITICAL. Only permitted actions: wait for in-flight subagents, update progress file, write handoff, report, stop.

**Grace period (30s):** Wait for in-flight subagents. Process returns, mark timed-out PRDs as `IN_PROGRESS (interrupted)`.

**Update progress file:** Record results, escalate DEG-001 to CRITICAL, update header with stop position.

**Assemble handoff:** Envelope from shared reference with optional `**Current Phase:**` and `**Current Tier:**`. Snapshot uses the 5 shared subsections plus: `### Tier Assignment Map` (PRD ID | Tier | Status per PRD — validates re-computed tiers on resume), `### Repo State` (Repo | Feature Branch | Tier Base Ref | Status per repo), `### Scope and Degradation` (invocation, scope, all three degradation variables).

**Write and stop:** Follow shared reference write procedure. Report completed/in-progress/pending counts, degradation state, and resume command.

### Resume from Handoff

Detection, envelope validation, staleness, and user confirmation follow the shared reference. Check `<plans-dir>/.session-handoff.md` during INIT before the progress file check.

**Reconciliation principles:** Progress file PRD statuses are authoritative over handoff. Handoff is authoritative for orchestrator context not in the progress file (scope, batch position, degradation, key decisions). Re-derive registries from disk: re-run PARSE_PLAN for PRD_REGISTRY, verify (don't recreate) feature branches for REPO_REGISTRY, re-run COMPUTE_TIERS and compare against handoff's Tier Assignment Map (warn on mismatch, use fresh tiers). Validate non-terminal worktrees by checking for commits and `.implement-report.md`. A fresh `--parallel` flag resets degradation state.

**Fast-forward:** Lowest tier with non-terminal PRDs → CURRENT_TIER. Resume state: SETUP_TIER (all PENDING), IMPLEMENT_TIER (SETUP_COMPLETE/IN_PROGRESS), or MERGE_TIER (IMPLEMENTED).

**Finalize:** Write RES-001 to progress file, delete handoff (warn on failure), report reconciliation summary, transition.

### Dual-Resume Coordination

| Scenario | Handoff? | Progress File? | Path |
|----------|----------|----------------|------|
| A | Valid + confirmed | Yes | Handoff-mediated: handoff context + progress file PRD statuses. Subsumes progress-file-only logic. |
| B | No / invalid / declined | Yes | Progress-file-only resume (INIT step 4b). |
| C | Valid + confirmed | No | Handoff-only: near-fresh start guided by handoff scope. |
| D | No | No | Fresh start. |

Handoff deleted after successful resume; progress file never deleted by handoff mechanism.

## Supporting Files

Read these files from this skill's directory (`.claude/skills/implement-plan/` relative to the workspace root) as needed:

- `prd-parser-prompt.md` — Template for PRD Parser subagents (extracts structured metadata)
- `prd-implementer-prompt.md` — Template for PRD Implementer subagents (writes source + tests)
- `tier-merge-validate-prompt.md` — Template for Tier Merge & Validate subagents (merge branches, update `__init__.py`, lint, test, cleanup)

External references:
- `.claude/skills/decompose-plan/consistency-checker-prompt.md` — Can be reused if plan issues are discovered during implementation
- `.claude/agents/worktree-pr-agent.md` — Worktree conventions reference

## Progress File Format

The progress file is written to `<plans-dir>/implementation-progress.md`:

```markdown
# Implementation Progress

## Metadata
- **Plans directory:** <path>
- **Complexity tier:** <1 | 2 | 3>
- **Multi-repo:** true | false
- **Scope:** full | phase-02 | prd-02/01,02/04
- **Max parallelism:** 4
- **Current state:** <STATE_NAME>
- **Current tier:** <N>
- **Started:** <ISO timestamp>
- **Last updated:** <ISO timestamp>

## Repo State
| Repo | Root | Feature Branch | Tier Base Ref | Pkg Manager |
|------|------|----------------|---------------|-------------|
| market-framework | /home/user/code/zge/market-framework | implement/<slug> | <sha> | uv |
| market-ercot | /home/user/code/zge/market-ercot | implement/<slug> | <sha> | pip |

## PRD Registry
| Phase | PRD | Title | Slug | Repo | Source File | Test File | Tier | Status |
|-------|-----|-------|------|------|-------------|-----------|------|--------|

## Issues
### ISS-001: [OPEN] <title>
- **PRD:** <phase>-<prd>
- **Detail:** <description>

## Tier Merge Log
### Tier 0 (completed <timestamp>)
- **market-framework**: Merged implement-prd-0101-schema: no conflicts. Validation: 13/13 tests pass.
- **market-ercot**: Merged implement-prd-0102-adapters: no conflicts. Validation: 8/8 tests pass.
```

Status values: `PENDING` → `SETUP_COMPLETE` → `IN_PROGRESS` → `IMPLEMENTED` → `MERGED` → `VALIDATED` | `FAILED` | `BLOCKED` | `SKIPPED_BLOCKED`

## Git Workflow

### Single-repo (MULTI_REPO = false)

```
main (untouched)
  └── implement/<plan-slug>  (feature branch, created at CONFIGURE)
        ├── implement-prd-0101-schema         (Tier 0, worktree branch)
        ├── implement-prd-0102-adapters       (Tier 0, worktree branch)
        │ ← merge Tier 0 branches, cleanup worktrees
        ├── implement-prd-0201-ingestion      (Tier 1, from TIER_BASE_REF)
        │ ← merge Tier 1, cleanup
        └── ...
```

### Multi-repo (MULTI_REPO = true)

```
market-framework/main (untouched)
  └── implement/<plan-slug>  (feature branch)
        ├── implement-prd-0101-schema         (Tier 0)
        │ ← merge Tier 0, update tier_base_ref for market-framework
        │ ← publish dev release of market-framework
        └── ...

market-ercot/main (untouched)
  └── implement/<plan-slug>  (feature branch)
        │ ← bump market-framework dep, uv sync
        ├── implement-prd-0201-ercot-adapter  (Tier 1, from tier_base_ref)
        │ ← merge Tier 1, update tier_base_ref for market-ercot
        └── ...
```

Each repo maintains its own `tier_base_ref`, feature branch, and worktree set.

Worktree path: `<workspace>/worktrees/<repo_name>/implement-prd-<phase><prd>-<slug>`
Venv sharing: symlink `.venv` from repo root to each worktree.
