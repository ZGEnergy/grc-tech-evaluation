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

Valid tool names: `pypsa`, `pandapower`, `gridcal`, `powermodels`, `powersimulations`, `matpower`

Set these variables for the session:

```
TOOL_NAME     = <tool_name>
TOOL_DIR      = evaluations/{{TOOL_NAME}}
RESULTS_DIR   = evaluations/{{TOOL_NAME}}/results
SKILL_DIR     = .claude/skills/evaluate-tool
GUIDES_DIR    = evaluation_guides
RUBRIC_PATH   = {{GUIDES_DIR}}/Phase1_Evaluation_Rubric_v1.md
PROTOCOL_PATH = {{GUIDES_DIR}}/Phase1_Test_Protocol_v2.md
CONFIG_PATH   = {{RESULTS_DIR}}/eval-config.yaml
PROGRESS_PATH = {{RESULTS_DIR}}/.progress.yaml
RESEARCH_PATH = {{RESULTS_DIR}}/research-context.md
```

## Execution Environment

**All code execution must happen inside the devcontainer.**

```bash
devcontainer exec --workspace-folder . <command>
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
CONFIGURE → RESEARCH → GATE → EVALUATE → SYNTHESIZE
```

Check `{{PROGRESS_PATH}}` on startup. If it exists, resume from the last completed state.

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

**Purpose:** Run gate tests (G-1, G-2, G-3) with halt-on-failure semantics.

1. **Read config.** Extract gate test IDs, networks, and pass conditions from `{{CONFIG_PATH}}`.

2. **Dispatch gate-evaluator agent.** Read `{{SKILL_DIR}}/prompts/gate-evaluator-prompt.md`,
   replace variables:
   - `{{tool_name}}` → `{{TOOL_NAME}}`
   - `{{tool_dir}}` → `{{TOOL_DIR}}`
   - `{{test_ids}}` → gate test IDs from config (e.g., `G-1, G-2, G-3`)
   - `{{reference_solutions}}` → expected bus/branch/gen counts from config
   - `{{results_dir}}` → `{{RESULTS_DIR}}/gate`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

3. **Evaluate gate results.** Read result files from `{{RESULTS_DIR}}/gate/`.

   - **G-1 FAIL:** Halt the entire evaluation. Inform the user:
     > "{{TOOL_NAME}} failed G-1 (TINY network ingestion). Evaluation cannot proceed."
     Write final progress and exit.

   - **G-2 or G-3 FAIL:** Record findings, set a `scale_cap` variable:
     - G-2 fail → `scale_cap: TINY` (no SMALL/MEDIUM tests)
     - G-3 fail → `scale_cap: SMALL` (no MEDIUM tests)
     Inform the user of the cap and continue.

   - **All pass:** Set `scale_cap: MEDIUM` and continue.

4. **Update progress:** Add GATE to `completed_states`, record `scale_cap`, set
   `current_state: EVALUATE`.

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
      - `{{reference_files}}` → list of relevant reference file paths from `{{SKILL_DIR}}/references/`
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

5. **Handle scale tiers.** The DAG typically flows:
   - Step 1: TINY functional tests (all code-evaluator dimensions)
   - Step 2: TINY audit dimensions (accessibility, maturity, supply_chain)
   - Step 3: SMALL grade tests (A-5, A-6, A-8, B-4, C-4, C-6)
   - Step 4: MEDIUM grade tests (remaining A, B, C tests)

   But the actual flow comes from the config — do not hard-code it.

6. **Update progress:** Add EVALUATE to `completed_states`, set `current_state: SYNTHESIZE`.

---

### State: SYNTHESIZE

**Purpose:** Compile all results into per-criterion summaries.

1. **Dispatch synthesis agent.** Read `{{SKILL_DIR}}/prompts/synthesis-prompt.md`,
   replace variables:
   - `{{tool_name}}` → `{{TOOL_NAME}}`
   - `{{results_dir}}` → `{{RESULTS_DIR}}`
   - `{{observations_dir}}` → `{{RESULTS_DIR}}/observations`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

2. **Present synthesis.** Show the user the synthesis output with:
   - Per-criterion grade recommendations with evidence links
   - Items flagged for human spot-check
   - Cross-cutting observations

3. **Final progress update:**

   ```yaml
   completed_states: [CONFIGURE, RESEARCH, GATE, EVALUATE, SYNTHESIZE]
   current_state: DONE
   timestamp: <ISO 8601>
   ```

4. **Inform user:** Evaluation complete. Results in `{{RESULTS_DIR}}/`.

---

## Observation Routing

Dimensions declare tags they **emit** and **consume** in `{{CONFIG_PATH}}`.

- Emitted observations are written to `{{RESULTS_DIR}}/observations/<tag>-<dimension>.md`
- Before dispatching an agent, collect all observation files matching its consumed tags
  and pass them via `{{consumed_observations}}`

Common tags (generated by config, not hard-coded here):
- `api-friction` — API usability issues (emitted by code-evaluators, consumed by accessibility)
- `doc-gaps` — documentation gaps found during testing (consumed by accessibility, maturity)
- `workaround-needed` — workarounds required (consumed by extensibility grading)
- `solver-issues` — solver-related findings (consumed by scalability)
- `license-flags` — licensing concerns (consumed by supply_chain)

---

## Error Handling

- **Agent failure:** If a sub-agent returns an error or incomplete results, log the failure
  in progress, inform the user, and ask whether to retry or skip.
- **Devcontainer not running:** If `devcontainer exec` fails, inform the user to start
  the devcontainer and retry.
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
