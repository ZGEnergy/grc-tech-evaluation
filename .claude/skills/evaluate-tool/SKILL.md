---
name: evaluate-tool
skill_version: v1
description: >
  Evaluate a power-system modeling tool across all Phase 1 rubric criteria.
  Orchestrates config generation, research, gate tests, functional/audit evaluation,
  and synthesis via sub-agents. One tool at a time.
argument-hint: "<tool_name> (one of: pypsa, pandapower, gridcal, powermodels, powersimulations, matpower)"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
  - TaskCreate
  - TaskUpdate
  - TaskList
  - TaskGet
  - TaskOutput
  - TaskStop
  - WebSearch
  - WebFetch
  - EnterWorktree
---

# /evaluate-tool — Orchestrator

You are the orchestrator for a Phase 1 power-system tool evaluation under contract
FA714626C0006. You drive a **data-driven state machine** that adapts to whatever the
evaluation guides specify — you never hard-code test IDs, dimensions, or pass conditions.

## Argument Parsing

The user invokes: `/evaluate-tool <tool_name>`

Valid tool names: `pypsa`, `pandapower`, `gridcal` (formerly VeraGrid), `powermodels`, `powersimulations`, `matpower`

Set these variables for the session:

```
TOOL_NAME     = <tool_name>
TOOL_DIR      = evaluations/{{TOOL_NAME}}
RESULTS_DIR   = evaluations/{{TOOL_NAME}}/results
SKILL_DIR     = .claude/skills/evaluate-tool
GUIDES_DIR    = evaluation_guides
RUBRIC_PATH   = {{GUIDES_DIR}}/Phase1_Evaluation_Rubric.md
PROTOCOL_PATH = {{GUIDES_DIR}}/Phase1_Test_Protocol.md
CONFIG_PATH   = {{RESULTS_DIR}}/eval-config.yaml
PROGRESS_PATH = {{RESULTS_DIR}}/.progress.yaml
RESEARCH_PATH = {{RESULTS_DIR}}/research-context.md
FNM_DIR       = data/fnm
```

Read `SKILL_VERSION` from this file's frontmatter (`skill_version: v1`). This value is
stamped into every result file and used during incremental re-runs to detect stale results.

### FNM_PATH Detection

After entering the worktree, check whether `FNM_PATH` is set in the devcontainer:

```bash
.devcontainer/dc-exec bash -c 'echo "${FNM_PATH:-NOT_SET}"'
```

Record the result as `FNM_AVAILABLE` (true/false). When `FNM_AVAILABLE` is false, all
Suite G (fnm_ingestion) DAG steps are skipped — log "FNM_PATH not set, skipping Suite G"
and continue with Suites A-F. When true, Suite G tests run using the FNM data at
`FNM_PATH` inside the devcontainer.

## Execution Environment

**All code execution must happen inside the devcontainer.**

Use the `dc-exec` helper which works from both the main checkout and worktrees:

```bash
# Run a command in /workspace (default)
.devcontainer/dc-exec <command>

# Run in a specific container directory
.devcontainer/dc-exec -C /workspace/evaluations/{{TOOL_NAME}} <command>
```

Never run Python, Julia, Octave, pytest, or pre-commit on the host.

## Worktree Isolation

**Before doing anything else**, enter a worktree so this evaluation does not interfere
with other concurrent work in the repository.

1. Use the `EnterWorktree` tool with name `eval/{{TOOL_NAME}}`.
2. After entering the worktree, all paths are relative to the worktree root. The
   variables above (`TOOL_DIR`, `RESULTS_DIR`, etc.) resolve correctly because they
   are relative paths.
3. Sub-agents inherit the worktree working directory automatically — no special
   configuration needed.

If the session is **resuming** from a progress file found in an existing worktree,
skip this step — the user is already in the worktree.

## State Machine

```
CONFIGURE → RESEARCH → GATE → EVALUATE → VALIDATE → SYNTHESIZE → COMMIT
```

Check `{{PROGRESS_PATH}}` on startup. If it exists, resume from the last completed state.
When resuming mid-EVALUATE, also check `completed_dag_steps` in the progress file and
skip to the first incomplete DAG step.

---

### State: CONFIGURE

**Purpose:** Generate the evaluation config from canonical guides, and determine whether
this is a fresh run or an incremental update of previously merged results.

1. **Check for existing config.** If `{{CONFIG_PATH}}` exists and `{{PROGRESS_PATH}}`
   shows CONFIGURE completed, skip to next state.

2. **Dispatch config-generator agent.** Read `{{SKILL_DIR}}/prompts/config-generator-prompt.md`,
   replace variables:
   - `{{rubric_path}}` → `{{RUBRIC_PATH}}`
   - `{{protocol_path}}` → `{{PROTOCOL_PATH}}`
   - `{{output_path}}` → `{{CONFIG_PATH}}`
   - `{{tool_name}}` → `{{TOOL_NAME}}`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

3. **Present config summary.** After the agent completes, read `{{CONFIG_PATH}}` and
   present a summary to the user:
   - Number of dimensions and test IDs per dimension
   - Execution DAG overview
   - Network tiers in use
   - Observation tag routing

4. **Scan for existing results (incremental mode detection).** Check whether result files
   already exist in `{{RESULTS_DIR}}`. Results are present when a previous evaluation was
   merged to main and the current worktree was branched from that state.

   Read `skill_version` from this file's frontmatter. For each test ID in the config,
   compare the `test_hash` in the config against the `test_hash` in the existing result
   file (if any). Classify each test as:

   - **`run`** — no result file exists (new test or first-ever run)
   - **`skip`** — result file exists with matching `test_hash` AND `skill_version`
   - **`stale`** — result file exists but `test_hash` differs (pass condition or tiers
     changed) OR `skill_version` differs (skill evaluation logic changed); needs re-run
   - **`orphan`** — a result file exists in `{{RESULTS_DIR}}` for a test ID not in the
     current config (test was removed from the protocol)

   Using `test_hash` rather than `protocol_version` means a protocol bump that adds a
   comment, renames a slug, or changes only unrelated tests will not force a re-run of
   tests whose definitions didn't change.

   If any existing results are found, present a summary and ask the user via AskUserQuestion:
   - header: "Run mode"
   - label: "Incremental — skip up-to-date tests (Recommended)", description: "Only run
     `run` and `stale` tests. Orphaned files will be deleted. Skipped tests count as
     present for VALIDATE."
   - label: "Fresh — run everything from scratch", description: "Ignore existing results
     and run all tests. Orphaned files will be deleted."

   If no existing results are found, proceed in fresh mode automatically.

5. **Ask for config approval.** Use AskUserQuestion:
   - header: "Config"
   - label: "Approve and continue (Recommended)", description: "Proceed with the generated config."
   - label: "Edit config first", description: "Pause to edit eval-config.yaml before proceeding."
   - label: "Abort", description: "Stop the evaluation."

6. **Write progress.** On approval:

   ```yaml
   # .progress.yaml
   tool: {{TOOL_NAME}}
   skill_version: {{SKILL_VERSION}}
   protocol_version: <from eval-config.yaml>
   run_mode: fresh|incremental
   completed_states: [CONFIGURE]
   current_state: RESEARCH
   timestamp: <ISO 8601>
   skipped_tests:    # file basenames of up-to-date result files (incremental only)
     - A-1_dcpf.md
   stale_tests:      # file basenames being re-run due to version mismatch
     - B-3_custom_constraints.md
   orphaned_files:   # full paths to result files for tests not in current config
     - evaluations/{{TOOL_NAME}}/results/expressiveness/OLD-1_removed.md
   ```

---

### State: RESEARCH

**Purpose:** Build research context for the tool under evaluation.

1. **Read config.** Load `{{CONFIG_PATH}}` to determine research focus areas.

2. **Dispatch 4 research agents in parallel.** Read `{{SKILL_DIR}}/prompts/research-prompt.md`,
   launch 4 instances with different `{{research_focus}}` values:

   - **Agent 1 — API & Formulations:** `"API surface, supported problem formulations, solver interfaces, data model (bus/branch/gen abstractions), input/output formats"`
   - **Agent 2 — Extensions & Architecture:** `"Extension mechanisms, plugin/callback APIs, internal architecture (separation of concerns), graph access, interoperability with DataFrames/NetworkX/Graphs.jl"`
   - **Agent 3 — Limitations & Ecosystem:** `"Known limitations, open issues related to evaluation tests, ecosystem packages, community size, documentation quality, recent release history"`
   - **Agent 4 — Version Capabilities:** `"Version-specific capabilities: installed version identification, changelog analysis, capability mapping to protocol test requirements, breaking changes between installed and latest versions"`

   All agents receive:
   - `{{tool_name}}` → `{{TOOL_NAME}}`
   - `{{output_path}}` → `{{RESULTS_DIR}}/research-{focus_slug}.md`

3. **Merge research.** Concatenate the 4 research output files into `{{RESEARCH_PATH}}`
   with section headers:
   - `research-api.md`
   - `research-extensions.md`
   - `research-limitations.md`
   - `research-version.md`

4. **Thin-research warning.** If any of the 4 research files is < 500 words, flag it:
   > "Research output for [focus area] is thin. This may indicate sparse documentation
   > — note as an Accessibility finding."

5. **Update progress:** Add RESEARCH to `completed_states`, set `current_state: GATE`.

---

### State: GATE

**Purpose:** Run gate tests with halt-on-failure semantics. Gate test IDs and their
tier-to-scale-cap mapping come from `{{CONFIG_PATH}}` — do not hardcode them.

1. **Read config.** Extract gate test IDs, networks, halt semantics, and pass conditions
   from `{{CONFIG_PATH}}`.

2. **Dispatch gate-evaluator agent.** Read `{{SKILL_DIR}}/prompts/gate-evaluator-prompt.md`,
   replace variables:
   - `{{tool_name}}` → `{{TOOL_NAME}}`
   - `{{tool_dir}}` → `{{TOOL_DIR}}`
   - `{{test_ids}}` → gate test IDs from config
   - `{{reference_solutions}}` → expected bus/branch/gen counts from config
   - `{{results_dir}}` → `{{RESULTS_DIR}}/gate`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

3. **Evaluate gate results.** Read result files from `{{RESULTS_DIR}}/gate/`.
   Apply the halt-on-failure semantics defined in the config:
   - The TINY gate is disqualifying — if it fails, set `scale_cap: NONE`, write
     progress with `current_state: DONE`, inform the user, and stop. Do not proceed
     to EVALUATE.
   - Higher-tier gate failures cap the scale (no tests above that tier).
   - All pass → `scale_cap: MEDIUM`.
   Inform the user of the outcome and any scale cap.

4. **Update progress** (unless halted above): Add GATE to `completed_states`, record
   `scale_cap`, set `current_state: EVALUATE`.

---

### State: EVALUATE

**Purpose:** Run all functional and audit test suites according to the execution DAG.

1. **Read execution DAG.** From `{{CONFIG_PATH}}`, load the DAG steps. Each step
   specifies dimensions that can run in parallel. Respect `scale_cap` — skip tests
   on networks above the cap.

2. **For each DAG step, dispatch agents in parallel.** For each dimension in the step:

   a. **Check skip list first.** Before dispatching any agent, check whether all test IDs
      in this dimension+tier combo appear in `skipped_tests` from `.progress.yaml`. If all
      tests in the step are skipped, log "Skipping [dimension] [tier] — up-to-date" and
      move to the next step without launching any agent.

   b. **Determine agent archetype** from the dimension's `archetype` field in config:
      - `code-evaluator` → `{{SKILL_DIR}}/prompts/code-evaluator-prompt.md`
      - `audit-evaluator` → `{{SKILL_DIR}}/prompts/audit-evaluator-prompt.md`

   c. **Read the prompt template** and replace variables:
      - `{{dimension}}` → dimension name
      - `{{test_ids}}` → comma-separated test IDs for this dimension + tier
      - `{{network_tier}}` → current tier (TINY, SMALL, MEDIUM)
      - `{{tool_name}}` → `{{TOOL_NAME}}`
      - `{{tool_dir}}` → `{{TOOL_DIR}}`
      - `{{results_dir}}` → `{{RESULTS_DIR}}/{{dimension}}`
      - `{{research_context}}` → contents of `{{RESEARCH_PATH}}`
      - `{{reference_files}}` → pass ALL reference file paths from `{{SKILL_DIR}}/references/`:
        `test-script-conventions.md`, `solver-config.md`, `convergence-protocol.md`,
        `result-template.md`, `workaround-classification.md`, `observation-schema.md`,
        `cross-tool-watchpoints.md`
      - `{{observation_tags}}` → tags this dimension emits (from config)
      - `{{consumed_observations}}` → contents of observation files matching consumed tags
      - `{{skill_version}}` → `{{SKILL_VERSION}}` (agents embed this in result frontmatter)

      **Code-evaluator only** (not replaced for audit-evaluator):
      - `{{version_capability_report}}` → contents of `{{RESULTS_DIR}}/research-version.md`

      Code-evaluators may record `fail` with `failure_reason: unsupported_in_installed_version`
      for features that are not supported in the installed version of the tool (as identified
      by the version capability report).

   d. **Launch agent** via Agent tool with `subagent_type: "general-purpose"`.

3. **Collect observations and apply tier gates.** After each DAG step completes:

   - Scan for new observation files in `{{RESULTS_DIR}}/observations/`. These are
     available to subsequent steps that consume the relevant tags.
   - **Suite C tier gate.** If the completed step is marked `c_scale_gate: true` in
     `{{CONFIG_PATH}}` (set on the Suite C SMALL step by the config-generator):
     - Read all result files for that step.
     - If C-4 (SCUC SMALL) has `status: fail`, log "C-4 failed — skipping MILP MEDIUM tests"
       and skip only the MILP MEDIUM tests (C-4 MEDIUM and any future MILP tests).
       **LP and power-flow MEDIUM tests (C-1, C-2, C-3, C-9, C-10) must NOT be skipped
       regardless of C-4 outcome — they run unconditionally in v11.**
       C-8 (SCOPF MEDIUM) is gated only by C-3, not by C-4.
     - For each skipped MILP MEDIUM test, write a stub result file in
       `{{RESULTS_DIR}}/scalability/` with `status: skip` and
       `blocked_by: C-4` in frontmatter, so VALIDATE does not report gaps.

4. **Checkpoint.** After each DAG step, update `{{PROGRESS_PATH}}`:

   ```yaml
   completed_dag_steps: [1, 2, ...]
   ```

5. **Handle scale tiers.** The DAG flow comes entirely from the config. A typical
   pattern is: TINY functional → TINY audits → SMALL grade tests → MEDIUM grade tests,
   but the actual steps, test IDs, and tier assignments are defined in `{{CONFIG_PATH}}`.
   Do not hard-code any test IDs or tier groupings here.

6. **FNM ingestion (Suite G).** If the config includes an `fnm_ingestion` dimension
   (marked `fnm_path_gated: true`), handle it as follows:

   - If `FNM_AVAILABLE` is false (FNM_PATH not set), skip all `fnm_ingestion` DAG steps.
     Log "Suite G skipped — FNM_PATH not set" and write skip results for each G-FNM test.
   - If `FNM_AVAILABLE` is true, dispatch Suite G tests via code-evaluator agents.
     Pass the following **additional reference files** (beyond the standard set):
     - `data/fnm/docs/intermediate-schema.md`
     - `data/fnm/docs/field-criticality-matrix.md`
     - `data/fnm/docs/supplemental-csvs.md`
     - `data/fnm/docs/supplemental-csv-representability.md`
     - `data/fnm/reference/pass_conditions.json` (if it exists)
     - `data/fnm/reference/excluded_buses.json` (if it exists)
   - G-FNM-1 is the Suite G gate with **partial cascade** semantics:
     - If G-FNM-1 fails due to PSS/E parse error, skip only G-FNM-2 (field coverage
       audit requires the full CSV tables). G-FNM-3, G-FNM-4, and G-FNM-5 proceed
       using the MATPOWER fallback path — write their `ingestion_path` as `matpower_ppc`
       or `matpower_raw` accordingly.
     - If G-FNM-1 fails due to record count mismatch (sub-check b), skip G-FNM-2
       through G-FNM-5 (write skip results with `blocked_by: G-FNM-1`).
     - A complete G-FNM-1 pass (both sub-checks) proceeds to all G-FNM-2 through G-FNM-5.
   - Suite G results go in `{{RESULTS_DIR}}/fnm_ingestion/`.
   - Suite G emits `fnm-data-model` and `fnm-scale` observations for consumption by
     synthesis.

7. **Phase 2 readiness findings.** If the config includes a `p2_readiness` dimension
   (informational findings that don't affect Phase 1 grades), dispatch an audit-evaluator
   agent for those tests. Results go in `{{RESULTS_DIR}}/p2_readiness/`.

8. **Delete orphaned result files.** After all DAG steps complete, delete any files listed
   in `orphaned_files` from `.progress.yaml`. These are result files for tests no longer
   in the current config — keeping them would leave stale data in the repo. Log each deletion.

9. **Update progress:** Add EVALUATE to `completed_states`, set `current_state: VALIDATE`.

---

### State: VALIDATE

**Purpose:** Verify completeness and quality of all result files before synthesis.

1. **Scan result files.** Read `{{CONFIG_PATH}}` to get every test ID. For each test ID,
   check that a result file exists in the appropriate `{{RESULTS_DIR}}/<dimension>/` directory.
   Tests listed in `skipped_tests` in `.progress.yaml` already have result files on disk —
   they count as present and do not constitute gaps.

2. **Validate frontmatter.** For each result file:
   - Required fields present: `test_id`, `tool`, `dimension`, `network`, `status`,
     `workaround_class`, `timestamp`, `protocol_version`, `skill_version`, `test_hash`
   - `status` value is one of: `pass`, `fail`, `qualified_pass`, `partial_pass`,
     `constrained_pass`, `informational`
   - `workaround_class` value is one of: `null`, `stable`, `fragile`, `blocking`
   - `test_hash` matches the `test_hash` for that test ID in `{{CONFIG_PATH}}`
   - If `status` is `qualified_pass` or `partial_pass`, the Workarounds section must be non-empty
   - If `workaround_class` is `blocking`, `status` must not be `qualified_pass`

3. **Validate naming.** Each result file must follow either:
   - `<test_id>_<slug>.md` (for single-tier tests or grade-network results)
   - `<test_id>_<slug>_<TIER>.md` (for tier-specific results)

4. **Produce validation report.** Write `{{RESULTS_DIR}}/validation-report.md` with:
   - **Gaps:** Test IDs with no result file
   - **Violations:** Frontmatter errors, invalid status/workaround values
   - **Warnings:** Naming convention deviations, missing optional fields

5. **Gate on gaps.** If any config test IDs have no result file, present the gaps to
   the user via AskUserQuestion:
   - header: "Gaps found"
   - label: "Fix gaps before synthesis", description: "Return to EVALUATE to fill missing results."
   - label: "Proceed with gaps noted", description: "Continue to synthesis with gaps recorded in the validation report."
   - label: "Abort", description: "Stop the evaluation."
   Missing result files block SYNTHESIZE by default. Frontmatter and naming violations
   are warnings only — they do not block synthesis.

6. **Update progress:** Add VALIDATE to `completed_states`, set `current_state: SYNTHESIZE`.

---

### State: SYNTHESIZE

**Purpose:** Compile all results into per-criterion summaries.

1. **Dispatch synthesis agent.** Read `{{SKILL_DIR}}/prompts/synthesis-prompt.md`,
   replace variables:
   - `{{tool_name}}` → `{{TOOL_NAME}}`
   - `{{results_dir}}` → `{{RESULTS_DIR}}`
   - `{{observations_dir}}` → `{{RESULTS_DIR}}/observations`
   - `{{skill_dir}}` → `{{SKILL_DIR}}`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

2. **Present synthesis.** Show the user the synthesis output with:
   - Per-criterion grade recommendations with evidence links
   - Items flagged for human spot-check
   - Cross-cutting observations

3. **Update progress:**

   ```yaml
   completed_states: [CONFIGURE, RESEARCH, GATE, EVALUATE, VALIDATE, SYNTHESIZE]
   current_state: COMMIT
   timestamp: <ISO 8601>
   ```

---

### State: COMMIT

**Purpose:** Commit results to the worktree branch and open a PR so results land on main.

1. **Stage all result artifacts.**

   ```bash
   git add evaluations/{{TOOL_NAME}}/
   ```

2. **Commit.** Use a conventional commit message that includes the tool name, protocol
   version, and skill version so the PR history is self-documenting:

   ```bash
   git commit -m "feat: {{TOOL_NAME}} Phase 1 evaluation results (protocol {{PROTOCOL_VERSION}}, skill {{SKILL_VERSION}})"
   ```

   Where `{{PROTOCOL_VERSION}}` is read from `eval-config.yaml` and `{{SKILL_VERSION}}`
   is from this file's frontmatter.

3. **Push the branch.**

   ```bash
   git push -u origin <worktree-branch-name>
   ```

4. **Open a PR.**

   ```bash
   gh pr create \
     --title "feat: {{TOOL_NAME}} Phase 1 evaluation (protocol {{PROTOCOL_VERSION}}, skill {{SKILL_VERSION}})" \
     --body "$(cat <<'EOF'
   ## {{TOOL_NAME}} Phase 1 Evaluation Results

   - **Protocol version:** {{PROTOCOL_VERSION}}
   - **Skill version:** {{SKILL_VERSION}}
   - **Run mode:** {{RUN_MODE}} (fresh|incremental)
   - **Scale cap:** {{SCALE_CAP}}
   - **Tests run:** {{RUN_COUNT}}
   - **Tests skipped (up-to-date):** {{SKIP_COUNT}}
   - **Orphaned files deleted:** {{ORPHAN_COUNT}}

   ## Spot-check items
   See `synthesis.md` → "Items requiring human spot-check" section.

   ## Next steps
   Review synthesis.md grades, spot-check flagged items, then merge.
   EOF
   )"
   ```

5. **Final progress update:**

   ```yaml
   completed_states: [CONFIGURE, RESEARCH, GATE, EVALUATE, VALIDATE, SYNTHESIZE, COMMIT]
   current_state: DONE
   pr_url: <url from gh pr create output>
   timestamp: <ISO 8601>
   ```

6. **Inform user:** Report the PR URL and a one-line summary (tests run, tests skipped,
   orphans deleted). Remind them to review the spot-check items in synthesis.md before merging.

---

## Observation Routing

Dimensions declare tags they **emit** and **consume** in `{{CONFIG_PATH}}`.

- Emitted observations are written to `{{RESULTS_DIR}}/observations/<tag>-<dimension>-<test_id>_<slug>.md`
- Before dispatching an agent, collect all observation files matching its consumed tags
  and pass them via `{{consumed_observations}}`

Common tags (generated by config, not hard-coded here):
- `api-friction` — API usability issues (emitted by code-evaluators, consumed by accessibility)
- `doc-gaps` — documentation gaps found during testing (consumed by accessibility, maturity)
- `workaround-needed` — workarounds required (consumed by extensibility grading)
- `solver-issues` — solver-related findings (consumed by scalability)
- `convergence-quality` — solver reports convergence but diagnostics disagree (consumed by scalability, accessibility)
- `unit-mismatch` — MW vs per-unit inconsistency at analysis boundaries (consumed by accessibility)
- `cascaded-failure` — scalability test blocked by prerequisite failure (consumed by synthesis)
- `license-flags` — licensing concerns (consumed by supply_chain)
- `arch-quality` — software architecture observations (emitted by extensibility, consumed by maturity)
- `fnm-data-model` — data model fidelity findings from FNM ingestion (emitted by fnm_ingestion, consumed by synthesis)
- `fnm-scale` — scale-related findings on LARGE FNM network (emitted by fnm_ingestion, consumed by scalability, synthesis)

---

## Error Handling

- **Agent failure:** If a sub-agent returns an error or incomplete results, log the failure
  in progress, inform the user, and ask whether to retry or skip.
- **Devcontainer not running:** If `dc-exec` fails with "no running devcontainer found",
  inform the user to start the devcontainer and retry.
- **Missing network files:** Check `data/networks/` for required .m files before dispatching
  gate tests. If missing, inform the user.

---

## Context Monitoring

Follow the procedures in `shared/context-monitoring-reference.md`:

- **CAUTION:** Reduce to max 2 concurrent sub-agents per DAG step.
- **WARNING:** Fully sequential (1 agent at a time), compress research context to ~500 words.
- **CRITICAL:** Finish current atomic operation, write handoff to
  `{{RESULTS_DIR}}/.session-handoff.md`, end response.

The handoff file follows the envelope format from the shared reference, including:
- Current state and completed DAG steps
- Scale cap
- Paths to all generated artifacts
- Next action to take on resume
