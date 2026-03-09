---
name: evaluate-tool
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
```

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
4. At the end of the evaluation (after SYNTHESIZE), remind the user that results
   live on the worktree branch and need to be merged or PR'd to `main`.

If the session is **resuming** from a progress file found in an existing worktree,
skip this step — the user is already in the worktree.

## State Machine

```
CONFIGURE → RESEARCH → GATE → EVALUATE → VALIDATE → SYNTHESIZE
```

Check `{{PROGRESS_PATH}}` on startup. If it exists, resume from the last completed state.
When resuming mid-EVALUATE, also check `completed_dag_steps` in the progress file and
skip to the first incomplete DAG step.

---

### State: CONFIGURE

**Purpose:** Generate the evaluation config from canonical guides.

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

4. **Ask for approval.** Use AskUserQuestion:
   - "Review the generated eval-config.yaml. Proceed with evaluation?"
   - Options: "Approve and continue", "Edit config first", "Abort"

5. **Write progress.** On approval:

   ```yaml
   # .progress.yaml
   tool: {{TOOL_NAME}}
   completed_states: [CONFIGURE]
   current_state: RESEARCH
   timestamp: <ISO 8601>
   ```

---

### State: RESEARCH

**Purpose:** Build research context for the tool under evaluation.

1. **Read config.** Load `{{CONFIG_PATH}}` to determine research focus areas.

2. **Dispatch 3 research agents in parallel.** Read `{{SKILL_DIR}}/prompts/research-prompt.md`,
   launch 3 instances with different `{{research_focus}}` values:

   - **Agent 1 — API & Formulations:** `"API surface, supported problem formulations, solver interfaces, data model (bus/branch/gen abstractions), input/output formats"`
   - **Agent 2 — Extensions & Architecture:** `"Extension mechanisms, plugin/callback APIs, internal architecture (separation of concerns), graph access, interoperability with DataFrames/NetworkX/Graphs.jl"`
   - **Agent 3 — Limitations & Ecosystem:** `"Known limitations, open issues related to evaluation tests, ecosystem packages, community size, documentation quality, recent release history"`

   All agents receive:
   - `{{tool_name}}` → `{{TOOL_NAME}}`
   - `{{output_path}}` → `{{RESULTS_DIR}}/research-{focus_slug}.md`

3. **Merge research.** Concatenate the 3 research output files into `{{RESEARCH_PATH}}`
   with section headers.

4. **Thin-research warning.** If any research file is < 500 words, flag it:
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

   a. **Determine agent archetype** from the dimension's `archetype` field in config:
      - `code-evaluator` → `{{SKILL_DIR}}/prompts/code-evaluator-prompt.md`
      - `audit-evaluator` → `{{SKILL_DIR}}/prompts/audit-evaluator-prompt.md`

   b. **Read the prompt template** and replace variables:
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

   c. **Launch agent** via Agent tool with `subagent_type: "general-purpose"`.

3. **Collect observations.** After each DAG step completes, scan for new observation
   files in `{{RESULTS_DIR}}/observations/`. These are available to subsequent steps
   that consume the relevant tags.

4. **Checkpoint.** After each DAG step, update `{{PROGRESS_PATH}}`:

   ```yaml
   completed_dag_steps: [1, 2, ...]
   ```

5. **Handle scale tiers.** The DAG flow comes entirely from the config. A typical
   pattern is: TINY functional → TINY audits → SMALL grade tests → MEDIUM grade tests,
   but the actual steps, test IDs, and tier assignments are defined in `{{CONFIG_PATH}}`.
   Do not hard-code any test IDs or tier groupings here.

6. **Phase 2 readiness findings.** If the config includes a `p2_readiness` dimension
   (informational findings that don't affect Phase 1 grades), dispatch an audit-evaluator
   agent for those tests. Results go in `{{RESULTS_DIR}}/p2_readiness/`.

7. **Update progress:** Add EVALUATE to `completed_states`, set `current_state: VALIDATE`.

---

### State: VALIDATE

**Purpose:** Verify completeness and quality of all result files before synthesis.

1. **Scan result files.** Read `{{CONFIG_PATH}}` to get every test ID. For each test ID,
   check that a result file exists in the appropriate `{{RESULTS_DIR}}/<dimension>/` directory.

2. **Validate frontmatter.** For each result file:
   - Required fields present: `test_id`, `tool`, `dimension`, `network`, `status`,
     `workaround_class`, `timestamp`, `protocol_version`
   - `status` value is one of: `pass`, `fail`, `qualified_pass`, `informational`
   - `workaround_class` value is one of: `null`, `stable`, `fragile`, `blocking`
   - `protocol_version` is present and non-empty
   - If `status` is `qualified_pass`, the Workarounds section must be non-empty

3. **Validate naming.** Each result file must follow either:
   - `<test_id>_<slug>.md` (for single-tier tests or grade-network results)
   - `<test_id>_<slug>_<TIER>.md` (for tier-specific results)

4. **Produce validation report.** Write `{{RESULTS_DIR}}/validation-report.md` with:
   - **Gaps:** Test IDs with no result file
   - **Violations:** Frontmatter errors, invalid status/workaround values
   - **Warnings:** Naming convention deviations, missing optional fields

5. **Gate on gaps.** If any config test IDs have no result file, present the gaps to
   the user via AskUserQuestion:
   - "The following test IDs have no result file: [list]. Choose an option:"
   - Options: "Fix gaps before synthesis", "Proceed with gaps noted", "Abort"
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

3. **Final progress update:**

   ```yaml
   completed_states: [CONFIGURE, RESEARCH, GATE, EVALUATE, VALIDATE, SYNTHESIZE]
   current_state: DONE
   timestamp: <ISO 8601>
   ```

4. **Inform user:** Evaluation complete. Results in `{{RESULTS_DIR}}/`.

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
