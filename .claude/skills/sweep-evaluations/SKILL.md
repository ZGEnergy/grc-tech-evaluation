---
name: sweep-evaluations
description: >
  Cross-tool meta-evaluation sweep. Reads all completed evaluations for a given protocol
  version, identifies cross-cutting themes (low-signal tests, misleading results,
  extraordinary claims), runs spot-check probes to verify suspicious findings, and produces
  three outputs: a versioned findings report, updated protocol/rubric documents, and updated
  evaluate-tool skill files. Use when the user wants to sweep, compare, or audit evaluation
  results across all tools, or when upgrading the protocol/rubric version.
argument-hint: "<source_version> (e.g., v4)"
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

# /sweep-evaluations — Orchestrator

You are the orchestrator for a cross-tool evaluation sweep (contract FA714626C0006). You
read completed evaluation results from all tool worktree branches, identify cross-cutting
issues, verify extraordinary claims via spot-check probes, and produce updated protocol
artifacts.

## Argument Parsing

The user invokes: `/sweep-evaluations <source_version>`

Example: `/sweep-evaluations v4`

Set these variables for the session:

```
SOURCE_VERSION    = <source_version>          # e.g., "v4"
TARGET_VERSION    = v<N+1>                    # e.g., "v5" (auto-derived)
SKILL_DIR         = .claude/skills/sweep-evaluations
GUIDES_DIR        = evaluation_guides
RUBRIC_PATH       = {{GUIDES_DIR}}/Phase1_Evaluation_Rubric.md
PROTOCOL_PATH     = {{GUIDES_DIR}}/Phase1_Test_Protocol.md
SWEEP_DATA_DIR    = sweep-data/{{SOURCE_VERSION}}-to-{{TARGET_VERSION}}
FINDINGS_REPORT   = sweep-reports/{{SOURCE_VERSION}}-to-{{TARGET_VERSION}}.md
PROGRESS_PATH     = {{SWEEP_DATA_DIR}}/.progress.yaml
ISSUES_PATH       = {{SWEEP_DATA_DIR}}/github-issues.yaml
```

**Tool list** (canonical, do not hardcode elsewhere):

```
TOOLS = [pypsa, pandapower, gridcal, powermodels, powersimulations, matpower]
```

## Execution Environment

**All code execution must happen inside the devcontainer.**

Use the `dc-exec` helper which works from both the main checkout and worktrees:

```bash
.devcontainer/dc-exec <command>
.devcontainer/dc-exec -C /workspace/evaluations/<tool> <command>
```

Never run Python, Julia, Octave, pytest, or pre-commit on the host.

## Worktree Isolation

**Before doing anything else**, enter a worktree so the sweep does not interfere with
other concurrent work.

1. Use the `EnterWorktree` tool with name `sweep/{{SOURCE_VERSION}}-to-{{TARGET_VERSION}}`.
2. After entering the worktree, all paths are relative to the worktree root.
3. Sub-agents inherit the worktree working directory automatically.
4. At the end of the sweep (after VALIDATE), remind the user that outputs live on the
   worktree branch and need to be merged or PR'd to `main`.

If the session is **resuming** from a progress file found in an existing worktree,
skip this step — the user is already in the worktree.

## State Machine

```
INIT → SWEEP → PROBE → AGGREGATE → GENERATE → VALIDATE
```

Check `{{PROGRESS_PATH}}` on startup. If it exists, resume from the last completed state.

---

### State: INIT

**Purpose:** Resolve data sources and validate prerequisites.

1. **Create output directories.**

   ```
   sweep-data/{{SOURCE_VERSION}}-to-{{TARGET_VERSION}}/
     per-tool/        # Per-tool sweep agent outputs
     probes/          # Spot-check probe results
     aggregation/     # Cross-tool aggregation output
   sweep-reports/     # Findings reports (versioned)
   ```

2. **Resolve tool worktree paths.** For each tool in `TOOLS`, locate its evaluation
   results. The worktrees follow the naming convention:

   ```
   .claude/worktrees/eval/<tool>-<SOURCE_VERSION>/evaluations/<tool>/results/
   ```

   Use `git worktree list` to find actual filesystem paths. If a worktree doesn't exist
   for a tool, check if results exist on a branch (e.g., `worktree-eval/<tool>-<SOURCE_VERSION>`)
   and note the tool as unavailable with a warning.

   Store resolved paths in `{{SWEEP_DATA_DIR}}/tool-paths.yaml`:

   ```yaml
   tools:
     pypsa:
       worktree: /path/to/.claude/worktrees/eval/pypsa-v4
       results_dir: /path/to/.../evaluations/pypsa/results
       synthesis: /path/to/.../evaluations/pypsa/results/synthesis.md
       status: available
     pandapower:
       # ...
   ```

3. **Validate prerequisites.** For each available tool:
   - Confirm `results/synthesis.md` exists (evaluation is complete)
   - Confirm `results/eval-config.yaml` exists (config is available)
   - Read `protocol_version` from a sample result file frontmatter
   - Flag any tools with mixed or unexpected protocol versions

4. **Read protocol and rubric.** Load `{{PROTOCOL_PATH}}` and `{{RUBRIC_PATH}}` to
   establish the baseline test structure for the source version.

5. **Query open GitHub issues.** Run `gh issue list --state open --label protocol --json number,title,body,labels`
   to find issues proposing rubric or protocol changes. For each issue, triage its relevance:
   - `rubric` — proposes a rubric scoring or weighting change
   - `protocol` — proposes a test design, addition, or removal
   - `skill` — proposes a skill file update
   - `out_of_scope` — not relevant to this sweep

   Save results to `{{ISSUES_PATH}}`:

   ```yaml
   issues:
     - number: 43
       title: "Add reviewer concentration metric for bus factor"
       relevance: rubric
       summary: <1-2 sentence distillation of the proposal>
     - number: 45
       title: "..."
       relevance: out_of_scope
       summary: "..."
   ```

   If `gh` is not available or the query fails, log a warning and continue without
   issues — the sweep can still run from evaluation results alone.

6. **Present summary to user.** Show:
   - Tools available (with paths) vs unavailable
   - Protocol version confirmation
   - Total result files per tool
   - Open GitHub issues triaged (count by relevance, list in-scope issues)
   Ask for approval via AskUserQuestion before proceeding.

7. **Write progress:**

   ```yaml
   # .progress.yaml
   source_version: {{SOURCE_VERSION}}
   target_version: {{TARGET_VERSION}}
   tools_available: [list]
   issues_in_scope: <count of issues with relevance != out_of_scope>
   completed_states: [INIT]
   current_state: SWEEP
   timestamp: <ISO 8601>
   ```

---

### State: SWEEP

**Purpose:** Analyze each tool's evaluation results independently in parallel.

1. **Dispatch per-tool sweep agents in parallel.** For each available tool, read
   `{{SKILL_DIR}}/prompts/per-tool-sweep-prompt.md` and replace variables:
   - `{{tool_name}}` → tool name
   - `{{results_dir}}` → resolved results directory (from tool-paths.yaml)
   - `{{synthesis_path}}` → path to tool's synthesis.md
   - `{{config_path}}` → path to tool's eval-config.yaml
   - `{{protocol_path}}` → `{{PROTOCOL_PATH}}`
   - `{{rubric_path}}` → `{{RUBRIC_PATH}}`
   - `{{output_dir}}` → `{{SWEEP_DATA_DIR}}/per-tool/{{tool_name}}`
   - `{{findings_schema}}` → `{{SKILL_DIR}}/references/intermediate-findings-schema.md`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

   Parallelize up to 6 agents (one per tool). These are read-only operations on
   separate worktrees, so there is no contention.

2. **Collect per-tool findings.** After all agents complete, verify each produced:
   - `{{SWEEP_DATA_DIR}}/per-tool/<tool>/findings.yaml` — structured findings
   - `{{SWEEP_DATA_DIR}}/per-tool/<tool>/findings.md` — narrative findings

3. **Extract probe candidates.** Scan all `findings.yaml` files for entries with
   `probe_recommended: true`. Compile a probe manifest:

   ```yaml
   # {{SWEEP_DATA_DIR}}/probe-manifest.yaml
   probes:
     - id: probe-001
       tool: powersimulations
       claim: "C-4 SCUC qualified_pass based on estimated timing"
       source_test: C-4
       source_file: <path to result file>
       probe_type: timing_verification
       priority: high
     # ...
   ```

4. **Present probe manifest to user.** Show the list of recommended probes with
   priorities. Ask via AskUserQuestion:
   - "I've identified N spot-check probes. Review the list and choose:"
   - Options: "Run all probes", "Select probes to run", "Skip probes"

5. **Update progress:** Add SWEEP to `completed_states`, set `current_state: PROBE`.

---

### State: PROBE

**Purpose:** Run spot-check probes to verify extraordinary claims.

If the user chose "Skip probes" in SWEEP, skip directly to AGGREGATE.

1. **Read probe manifest** from `{{SWEEP_DATA_DIR}}/probe-manifest.yaml`.

2. **Read probe conventions** from `{{SKILL_DIR}}/references/probe-conventions.md`.

3. **Group probes by tool.** Probes for the same tool run sequentially (shared
   devcontainer — no concurrent probes for the same tool). Probes for different tools
   can run in parallel.

4. **For each probe, dispatch a probe agent.** Read
   `{{SKILL_DIR}}/prompts/probe-agent-prompt.md` and replace variables:
   - `{{probe_id}}` → probe ID
   - `{{tool_name}}` → tool name
   - `{{tool_dir}}` → `evaluations/{{tool_name}}`
   - `{{claim}}` → the claim being verified
   - `{{source_test}}` → original test ID
   - `{{source_file}}` → path to original result file
   - `{{probe_type}}` → type of probe
   - `{{output_dir}}` → `{{SWEEP_DATA_DIR}}/probes/{{tool_name}}`
   - `{{probe_conventions}}` → `{{SKILL_DIR}}/references/probe-conventions.md`
   - `{{timeout_seconds}}` → 300 (default, configurable per probe)

   Launch via Agent tool with `subagent_type: "general-purpose"`.

   **Sequential within tool, parallel across tools.** For each tool with probes,
   dispatch one probe at a time. Different tools' probes can run in parallel.

5. **Collect probe results.** Each probe produces a result file:
   `{{SWEEP_DATA_DIR}}/probes/<tool>/<probe_id>.md`

   Classify each result:
   - `probe_bug` — probe script itself had a bug (inconclusive, needs fixing)
   - `claim_debunked` — probe found evidence contradicting the original claim
   - `claim_supported` — probe found evidence supporting the original claim
   - `inconclusive` — probe ran but couldn't definitively confirm or deny

6. **Present probe results to user.** Summary table showing each probe and its
   classification. Flag any `claim_debunked` results prominently.

7. **Update progress:** Add PROBE to `completed_states`, set `current_state: AGGREGATE`.

---

### State: AGGREGATE

**Purpose:** Synthesize per-tool findings and probe results into cross-tool themes.

1. **Dispatch cross-tool aggregation agent.** Read
   `{{SKILL_DIR}}/prompts/cross-tool-aggregation-prompt.md` and replace variables:
   - `{{per_tool_dir}}` → `{{SWEEP_DATA_DIR}}/per-tool`
   - `{{probes_dir}}` → `{{SWEEP_DATA_DIR}}/probes`
   - `{{protocol_path}}` → `{{PROTOCOL_PATH}}`
   - `{{rubric_path}}` → `{{RUBRIC_PATH}}`
   - `{{output_dir}}` → `{{SWEEP_DATA_DIR}}/aggregation`
   - `{{tools}}` → comma-separated list of available tools
   - `{{github_issues_path}}` → `{{ISSUES_PATH}}`

   Launch via Agent tool with `subagent_type: "general-purpose"`.

2. **Verify aggregation output.** The agent should produce:
   - `aggregation/themes.yaml` — structured cross-tool themes
   - `aggregation/themes.md` — narrative analysis
   - `aggregation/low-signal-tests.yaml` — tests producing low differentiation
   - `aggregation/comparison-matrices.md` — cross-tool comparison tables
   - `aggregation/proposed-changes.yaml` — evidence-backed protocol/rubric changes

3. **Present aggregation summary to user.** Show:
   - Number of themes identified
   - Low-signal tests flagged
   - Number of proposed changes (grouped by type: test redesign, new test, remove test,
     scoring change, rubric change, skill change)
   Ask for approval via AskUserQuestion before generating outputs.

4. **Update progress:** Add AGGREGATE to `completed_states`, set `current_state: GENERATE`.

---

### State: GENERATE

**Purpose:** Produce the three output artifacts.

1. **Dispatch 3 output agents in parallel:**

   a. **Findings report writer.** Read
      `{{SKILL_DIR}}/prompts/findings-report-prompt.md`, replace variables:
      - `{{source_version}}` → `{{SOURCE_VERSION}}`
      - `{{target_version}}` → `{{TARGET_VERSION}}`
      - `{{aggregation_dir}}` → `{{SWEEP_DATA_DIR}}/aggregation`
      - `{{per_tool_dir}}` → `{{SWEEP_DATA_DIR}}/per-tool`
      - `{{probes_dir}}` → `{{SWEEP_DATA_DIR}}/probes`
      - `{{output_path}}` → `{{FINDINGS_REPORT}}`
      - `{{report_template}}` → `{{SKILL_DIR}}/references/findings-report-template.md`
      - `{{mapping_schema}}` → `{{SKILL_DIR}}/references/test-id-mapping-schema.md`
      - `{{github_issues_path}}` → `{{ISSUES_PATH}}`

   b. **Protocol/rubric updater.** Read
      `{{SKILL_DIR}}/prompts/protocol-update-prompt.md`, replace variables:
      - `{{source_version}}` → `{{SOURCE_VERSION}}`
      - `{{target_version}}` → `{{TARGET_VERSION}}`
      - `{{current_protocol}}` → `{{PROTOCOL_PATH}}`
      - `{{current_rubric}}` → `{{RUBRIC_PATH}}`
      - `{{aggregation_dir}}` → `{{SWEEP_DATA_DIR}}/aggregation`
      - `{{output_protocol}}` → `{{GUIDES_DIR}}/Phase1_Test_Protocol.md`
      - `{{output_rubric}}` → `{{GUIDES_DIR}}/Phase1_Evaluation_Rubric.md`
      - `{{github_issues_path}}` → `{{ISSUES_PATH}}`

   c. **Skill updater.** Read
      `{{SKILL_DIR}}/prompts/skill-update-prompt.md`, replace variables:
      - `{{source_version}}` → `{{SOURCE_VERSION}}`
      - `{{target_version}}` → `{{TARGET_VERSION}}`
      - `{{aggregation_dir}}` → `{{SWEEP_DATA_DIR}}/aggregation`
      - `{{evaluate_tool_dir}}` → `.claude/skills/evaluate-tool`
      - `{{new_protocol}}` → `{{GUIDES_DIR}}/Phase1_Test_Protocol.md`
      - `{{new_rubric}}` → `{{GUIDES_DIR}}/Phase1_Evaluation_Rubric.md`

   Launch all 3 via Agent tool with `subagent_type: "general-purpose"`.

2. **Update progress:** Add GENERATE to `completed_states`, set `current_state: VALIDATE`.

---

### State: VALIDATE

**Purpose:** Verify completeness and internal consistency of all outputs.

1. **Check findings report.** Verify `{{FINDINGS_REPORT}}` exists and contains:
   - Executive summary
   - Cross-tool comparison matrices
   - Low-signal test identification with evidence
   - Spot-check probe results (if probes were run)
   - Test-ID mapping table (vN → vN+1)
   - Change rationale for every proposed protocol/rubric change

2. **Check protocol/rubric.** Verify updated files exist and:
   - Protocol contains the target version number
   - All test IDs from the mapping table are present in the new protocol
   - No orphan test IDs (in mapping but not in new protocol, or vice versa)
   - Rubric scoring criteria are consistent with protocol changes

3. **Check skill updates.** Verify evaluate-tool skill files were updated:
   - Config generator can handle new test IDs
   - Cross-tool watchpoints updated if applicable
   - Reference files consistent with new protocol

4. **Cross-reference consistency.** Verify:
   - Every change in protocol/rubric has a rationale in the findings report
   - Every proposed change in `aggregation/proposed-changes.yaml` is reflected
     in either the protocol, rubric, or findings report (with an explanation
     if a proposed change was not adopted)
   - Test-ID mapping table is complete (every vN test accounted for)
   - Every in-scope GitHub issue from `{{ISSUES_PATH}}` is either reflected in a
     proposed change or listed as deferred with rationale in the findings report

5. **Produce validation report.** Write `{{SWEEP_DATA_DIR}}/validation-report.md` with:
   - Checks passed / failed
   - Missing items
   - Consistency issues

6. **Present results to user.** Show validation report summary. If any checks failed,
   ask via AskUserQuestion:
   - "Validation found N issues. Choose an option:"
   - Options: "Fix issues", "Accept with issues noted", "Abort"

7. **Final progress update:**

   ```yaml
   completed_states: [INIT, SWEEP, PROBE, AGGREGATE, GENERATE, VALIDATE]
   current_state: DONE
   timestamp: <ISO 8601>
   ```

8. **Inform user:** Sweep complete. Outputs:
   - Findings report: `{{FINDINGS_REPORT}}`
   - Updated protocol: `{{PROTOCOL_PATH}}`
   - Updated rubric: `{{RUBRIC_PATH}}`
   - Updated skill: `.claude/skills/evaluate-tool/`
   - All on worktree branch — needs PR to `main`.

   **Issue linking.** If any in-scope GitHub issues were incorporated into the
   protocol update, include them in the PR body so they auto-close on merge.
   Use `Closes #<number>` for each resolved issue. List deferred issues as
   `Related to #<number>` so they remain open but linked.

---

## Data Flow Summary

```
Per-tool worktrees (read-only)     GitHub issues (gh issue list)
  │                                       │
  ├─ INIT: resolve paths, query issues → github-issues.yaml
  │                                       │
  ├─ SWEEP: 6 parallel agents → per-tool/*/findings.{yaml,md}
  │                                    │
  │                            probe-manifest.yaml
  │                                    │
  ├─ PROBE: sequential/tool  → probes/*/<probe_id>.md
  │         parallel/cross
  │                                    │
  ├─ AGGREGATE: 1 agent      → aggregation/{themes,low-signal-tests,
  │    (+ github issues)        comparison-matrices,proposed-changes}
  │                                    │
  ├─ GENERATE: 3 parallel    → findings report + protocol/rubric + skill updates
  │                                    │
  └─ VALIDATE: consistency   → validation-report.md (+ issue coverage check)
```

---

## Existing Evaluation Results — Read-Only Contract

The sweep **never modifies** files in tool evaluation worktrees. All reads from
`evaluations/<tool>/results/` are read-only. All sweep outputs go into `sweep-data/`
and `sweep-reports/` in the sweep's own worktree.

---

## Error Handling

- **Missing tool worktree:** Log warning, exclude tool from sweep, note in findings report.
  The sweep proceeds with available tools (minimum 3 required for meaningful cross-tool
  analysis).
- **Agent failure:** Log failure, inform user, offer retry or skip.
- **Devcontainer not running:** Required only for PROBE state. If `dc-exec` fails, inform
  user to start devcontainer. SWEEP and AGGREGATE can run without devcontainer.
- **Probe timeout:** Classify as `inconclusive` with reason "timeout after N seconds".

---

## Context Monitoring

Follow the procedures in `shared/context-monitoring-reference.md`:

- **CAUTION:** Reduce to max 3 concurrent sub-agents.
- **WARNING:** Fully sequential (1 agent at a time), compress intermediate data summaries.
- **CRITICAL:** Finish current atomic operation, write handoff to
  `{{SWEEP_DATA_DIR}}/.session-handoff.md`, end response.

The handoff file follows the shared envelope format, including:
- Current state and completed states
- Tools swept so far
- Probes completed/pending
- Paths to all generated artifacts
- Next action to take on resume
