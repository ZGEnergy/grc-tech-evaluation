---
name: decompose-plan
description: This skill should be used when the user asks to "decompose a plan", "break down a plan into phases and PRDs", "create a hierarchical plan", "generate PRDs from a plan", or "run the planning decomposition workflow". It implements a top-down planning methodology that decomposes executive plans into phase plans and PRDs through iterative refinement with consistency checking.
---

# Hierarchical Plan Decomposition

Decompose an executive plan into phase plans and PRDs using a structured state machine with targeted subagents. The process follows the methodology documented in `hierarchical-planning-spec.md`.

## Invocation

Accept `$ARGUMENTS` as either:
1. A file path to an existing executive plan (markdown file)
2. A short description of what to plan (used to draft an executive plan first)
3. Empty — prompt the user to provide a plan or description

If `$ARGUMENTS` is a file path, read it. If it is a description, draft an `executive-plan.md` using the template from `artifact-templates.md` (in this skill's directory) and present it to the user for approval before proceeding.

## Artifact Tree Convention

All artifacts live in a single project directory. The user specifies the output directory, or default to `plans/` relative to the current working directory.

**Tier 2 and Tier 3 layout:**

```
<output-dir>/
├── executive-plan.md
└── phases/
    ├── phase-01-<slug>/
    │   ├── phase-plan.md
    │   └── prds/
    │       ├── README.md
    │       ├── prd-01-<slug>.md
    │       └── prd-02-<slug>.md
    └── phase-02-<slug>/
        ├── phase-plan.md
        └── prds/
            ├── README.md
            └── prd-01-<slug>.md
```

**Tier 1 layout** (flat — no phases/ subdirectory):

```
<output-dir>/
├── executive-plan.md
└── task-cards.md
```

Naming rules:
- Phase directories: `phase-<NN>-<slug>/` where NN is zero-padded two digits, slug is lowercase-hyphenated
- PRD files: `prd-<NN>-<slug>.md` where NN is zero-padded two digits within the phase
- Slugs derived from the deliverable/phase name (lowercase, spaces to hyphens, strip special chars)
- Numbering reflects intended execution order, not creation order

## Backward Compatibility

Executive plans without a `## Complexity` section default to **Tier 3** (full PRDs). This ensures existing plans decomposed before this feature was added continue to produce the same output.

## Open Question Format

Open questions use scope-prefixed IDs and checkbox format:

- Executive level: `OQ-E<NN>` (e.g., `OQ-E01`)
- Phase level: `OQ-P<N>-<NN>` (e.g., `OQ-P1-03`)
- PRD level: `OQ-D<phase>.<prd>-<NN>` (e.g., `OQ-D1.02-01`)

Unresolved format:

```markdown
- [ ] OQ-E01: Should we support multi-tenancy? — *options: A (yes from start) / B (single-tenant first) / C (defer decision)*
```

Resolved format:

```markdown
- [x] OQ-E01: Should we support multi-tenancy? — *resolved: B (single-tenant first, multi-tenant in Phase 3)*
```

## State Machine

The orchestrator progresses through these states. Track the current state explicitly and report transitions to the user.

### State 1: INIT

1. Read the executive plan (from file or draft one from description).
2. Create the output directory structure: `<output-dir>/` (defer `phases/` until after ASSESS determines tier).
3. If the input was a rough description, use the Task tool (general-purpose subagent) to draft `executive-plan.md` following the template in `artifact-templates.md`. Present it to the user for approval. Revise if requested.
4. Write (or copy) the executive plan to `<output-dir>/executive-plan.md`.
5. Parse the executive plan to identify phases, their names, rough scope, inter-phase dependencies, and target repositories (from each phase's `Target repository` field if present). Store the per-phase target repository for use in later states.
6. If the executive plan does not already contain a `## Phase Dependencies` section with a dependency table and implementation tiers, generate one by analyzing the per-phase `Dependencies` fields. Add it to the executive plan after the `## Phases` section. The table must list every phase with its Depends On and Enables columns, and tiers must group phases that can run in parallel.
7. Report to the user: number of phases identified, proposed folder structure, and the phase dependency tiers.
8. Transition to **ASSESS**.

### State 2: ASSESS

Determine the complexity tier for this plan. This controls the artifact format, consistency checking depth, and subagent specification level throughout the rest of the workflow.

#### Tier Definitions

| Tier | Label | Artifact Format | Tests/unit | Consistency Checks |
|------|-------|----------------|------------|-------------------|
| 1 | Task Cards | Flat `task-cards.md` | 2-4 acceptance criteria | None |
| 2 | Lean PRDs | Lean PRDs (no Data Structures/API/Non-Goals) | 3-6 acceptance criteria | Cross-phase + type checker only |
| 3 | Full PRDs | Current full PRD format | 8-18 unit tests | All checkers |

#### Assessment Procedure

1. Count the number of phases in the executive plan.
2. Estimate the total number of files from scope indicators: count explicit file references, key deliverables, and estimated scope fields across all phases.
3. Count the number of unique target repositories.
4. Apply thresholds:
   - **Tier 1** if: ≤1 phase AND ≤5 estimated files AND single repository
   - **Tier 3** if: ≥3 phases OR ≥15 estimated files OR (multi-repo with critical cross-repo interfaces)
   - **Tier 2** otherwise
5. If the executive plan already contains a `## Complexity` section, read the tier from it and skip to step 7.
6. Present the assessment to the user:

   ```
   Complexity Assessment:
   - Phases: <N>
   - Estimated files: <N>
   - Repositories: <N>
   - Selected tier: <N> (<label>)
   - Rationale: <1-2 sentences>

   Override? [Use Tier <N> / Override to Tier 1 / Override to Tier 2 / Override to Tier 3]
   ```

   Use AskUserQuestion with the selected tier as the recommended option.
7. Write the `## Complexity` section to the executive plan (after `## Phase Dependencies`, or after `## Phases` if no dependencies section):

   ```markdown
   ## Complexity

   - **Tier:** <N> (<label>)
   - **Rationale:** <1-2 sentences>
   ```

8. Store `complexity_tier` (1, 2, or 3) and `detail_level` (`task_card`, `lean_prd`, or `full_prd`) in orchestrator memory.
9. If Tier 1: create output directory only (no `phases/` subdirectory). If Tier 2 or 3: create `<output-dir>/phases/`.
10. Transition to **DECOMPOSE_PHASES**.

### State 3: DECOMPOSE_PHASES

**Tier 1:** Skip this state entirely — Tier 1 has no phase plans. Transition directly to **DECOMPOSE_PRDS**.

**Tier 2 and Tier 3:**

1. Determine which phases can be written in parallel (no inter-phase dependencies).
2. For each batch of independent phases, launch Phase Plan Writer subagents in parallel via the Task tool. Each subagent receives:
   - `{{executive_summary}}`: a ~500 word summary of the executive plan (see Context Summarization), plus the full `### Phase N` section for the specific phase being written
   - The phase number and name
   - Summaries of any already-completed phase plans (~200 words each)
   - Any resolved open questions relevant to this phase
   - The output path for the phase plan
   - The output path for the `prds/README.md`
   - `{{detail_level}}`: `lean_prd` (Tier 2) or `full_prd` (Tier 3)
3. Read the prompt template from `phase-plan-writer-prompt.md` in this skill directory. Replace `{{variables}}` with actual values before passing to the Task tool.
4. Collect returned content. Write each phase plan to `phases/phase-<NN>-<slug>/phase-plan.md`.
5. Write each `prds/README.md` index file.
6. Phases that depend on earlier phases: write sequentially after dependencies complete, including summaries of completed dependency phases.
7. Report progress to the user after each batch completes.
8. Transition to **DECOMPOSE_PRDS**.

### State 4: DECOMPOSE_PRDS

#### Tier 1: Write Task Cards

1. Read the executive plan to identify deliverables from the single phase (or top-level deliverables if no phases).
2. Launch PRD Writer subagents for each task card. Pass `{{detail_level}}` = `task_card`. Each subagent receives:
   - `{{prd_number}}`, `{{prd_title}}`
   - `{{executive_summary}}`: full executive plan (small enough for Tier 1)
   - `{{target_repo}}`: the target repository
   - `{{output_path}}`: ignored — subagent returns content, orchestrator assembles the flat file
3. Read the prompt template from `prd-writer-prompt.md`. Replace `{{variables}}` with actual values.
4. Collect returned task card content from all subagents.
5. Assemble `<output-dir>/task-cards.md` using the Task Card Container Template from `artifact-templates.md`. Write the overview, all task cards in order, and the execution order table.
6. Report to user: number of task cards produced.
7. Transition to **COLLECT**.

#### Tier 2: Write Lean PRDs

Same as Tier 3 below, but pass `{{detail_level}}` = `lean_prd` to the PRD writer subagent.

#### Tier 3: Write Full PRDs

1. Process phases in dependency order.
2. Within each phase, read the phase plan to identify deliverables and their intra-phase dependencies.
3. For each batch of independent PRDs (no intra-phase dependencies), launch PRD Writer subagents in parallel.
4. Read the prompt template from `prd-writer-prompt.md`. Replace `{{variables}}`:
   - `{{prd_number}}`, `{{phase_number}}`, `{{prd_title}}`
   - `{{detail_level}}`: `full_prd` (Tier 3) or `lean_prd` (Tier 2)
   - `{{phase_plan_summary}}`: full text of parent phase plan
   - `{{executive_summary}}`: summarized executive plan (~500 words)
   - `{{adjacent_prd_summaries}}`: summaries of sibling PRDs already written (~200 words each)
   - `{{resolved_oqs}}`: any resolved open questions relevant to this PRD
   - `{{target_repo}}`: the target repository directory name for this PRD's phase (from the executive plan's per-phase `Target repository` field; if not specified, use the workspace's single repo name or prompt the user)
   - `{{output_path}}`: the file path for the PRD
5. Collect returned content. Write PRDs to `phases/phase-<NN>-<slug>/prds/prd-<NN>-<slug>.md`.
6. Update the phase's `prds/README.md` with the new PRD entry.
7. Collect any **discoveries** from PRD writers (things that conflict with or require changes to higher-level documents). Add these to a reconciliation backlog.
8. PRDs with intra-phase dependencies: write sequentially, providing completed dependency PRDs as context.
9. Report progress after each phase's PRDs complete.
10. After all PRDs for all phases are written, transition to **COLLECT**.

### State 5: COLLECT

1. Scan all artifacts for unresolved open questions by searching for `- [ ] OQ-` patterns across all markdown files in the output directory.
2. Also include any unresolved discoveries from the reconciliation backlog.
3. Group questions by scope: executive first, then phase (in order), then PRD (in order).
4. Deduplicate: if the same question appears in multiple places, keep the highest-scope version.
5. If no unresolved questions and no pending discoveries exist, transition to **RECONCILE** (skip ASK_USER).
6. Otherwise, transition to **ASK_USER**.

### State 6: ASK_USER

1. Present the batch of open questions to the user, organized by scope level.
2. For each question, show:
   - The question ID and text
   - The suggested options from the subagent
   - Which artifact it appears in
3. Use AskUserQuestion for batches of 1-4 questions at a time. If more than 4, present them in sequential batches, prioritizing executive-level questions first.
4. Record the user's answers.
5. Transition to **APPLY**.

### State 7: APPLY

1. For each resolved question, update the artifact where it lives:
   - Change `- [ ]` to `- [x]`
   - Append the resolution text: `— *resolved: <answer>*`
2. Determine the blast radius of each resolution:
   - Executive-level resolutions may affect all phase plans and PRDs
   - Phase-level resolutions may affect PRDs within that phase and possibly the executive plan
   - PRD-level resolutions may affect the parent phase plan
3. For documents significantly affected by resolutions, launch subagents (reusing the appropriate writer prompt) to rewrite affected sections. Pass the original content plus resolution context.
4. Write updated content to the affected files.
5. Record the set of modified files and their containing phase numbers in the reconciliation state. This enables incremental mode in RECONCILE.
6. Transition to **RECONCILE**.

### State 8: RECONCILE

**Tier 1:** Skip this state entirely. Transition directly to **CHECK**.

**Tier 2:** Run only the deterministic type checker (Step 1b) and the cross-phase checker (Step 3, cross-phase only — no intra-phase, no edge checkers). This provides basic structural validation without the heavyweight multi-agent consistency sweep.

**Tier 3:** Full consistency checking as described below.

Consistency checking uses three scoped agent types to stay within context limits. Each agent reads only the artifacts it needs.

#### Step 1: Determine scope (full vs incremental)

On first entry (from DECOMPOSE_PRDS or COLLECT with no prior APPLY), run **full mode** — all phases and edges.

On re-entry after APPLY, run **incremental mode**:
- Read the set of modified files recorded by APPLY.
- Identify which phases contain modified files (`modified_phases`).
- Intra-phase checkers: run only for phases in `modified_phases`.
- Edge checkers: run only for edges where at least one endpoint is in `modified_phases`.
- Cross-phase checker: run if any phase plan or the executive plan was modified; skip otherwise.

#### Step 1b: Run deterministic type checker

1. Run the plan-type-checker via the Bash tool:

   ```
   uv run plan-type-check <output-dir> --json
   ```

2. Parse the JSON output. It contains a `findings` array with `rule`, `severity`,
   `summary`, `detail`, `suggested_fix`, and `locations` fields.
3. If findings exist:
   - **With suggested_fix**: Apply the fix directly by editing the referenced PRD file.
     These are deterministic structural errors (column mismatches, missing fields,
     file path conflicts) — no LLM judgment needed.
   - **Without suggested_fix**: Convert to open questions using `OQ-` prefix and
     insert into the relevant PRD's Open Questions section.
   - Record all modified files in the reconciliation state for incremental scope.
4. Report type-checker results to the user: findings by severity, fixes applied,
   new open questions created.
5. If new open questions were created, transition to **COLLECT** — skip the LLM
   checkers for this iteration since the plan changed.
6. Otherwise, proceed to Step 2 (LLM checkers) with updated scope.

#### Step 2: Launch intra-phase checkers (parallel)

1. Read the prompt template from `consistency-checker-intra-phase-prompt.md`.
2. For each phase in scope, prepare the prompt:
   - `{{phase_number}}`: the phase number
   - `{{phase_name}}`: the phase name
   - `{{executive_plan_content}}`: the full text of executive-plan.md (inlined in the prompt, not as a file to Read)
   - `{{artifact_file_list}}`: the phase's `phase-plan.md`, `prds/README.md`, and all `prd-*.md` files
3. Launch all intra-phase checkers in parallel via a single message with multiple Task tool calls. Use `subagent_type: "general-purpose"`.

#### Step 3: Launch edge checkers and cross-phase checker (parallel)

After intra-phase checkers complete:

1. **Parse the Phase Dependencies table** from the executive plan to identify all dependency edges (directed pairs of phases).
2. Read the prompt template from `consistency-checker-edge-prompt.md`.
3. For each edge in scope, prepare the prompt:
   - `{{upstream_phase_number}}`, `{{upstream_phase_name}}`: the upstream (depended-on) phase
   - `{{downstream_phase_number}}`, `{{downstream_phase_name}}`: the downstream (dependent) phase
   - `{{artifact_file_list}}`: both phases' `phase-plan.md` files and all PRD files from both phases
4. Read the prompt template from `consistency-checker-cross-phase-prompt.md`.
5. Prepare the cross-phase prompt:
   - `{{artifact_file_list}}`: `executive-plan.md`, all `phase-plan.md` files, and all `prds/README.md` files (no individual PRDs)
6. Launch all edge checkers and the cross-phase checker in parallel via a single message with multiple Task tool calls.

#### Step 4: Merge and deduplicate results

1. Collect findings from all checker agents.
2. Exclude findings already fixed by the deterministic type checker in Step 1b.
3. Deduplicate: two findings are duplicates if they share the same type, reference the same files, and have descriptions matching in the first 50 characters. Keep the version with more detail.
4. Sort by severity: HIGH first, then MEDIUM, then LOW.

#### Step 5: Act on findings

1. If the merged report contains **no inconsistencies**, transition to **CHECK**.
2. If inconsistencies are found:
   - **Mechanical fixes** (e.g., deliverable list doesn't match actual PRDs, naming inconsistency): apply directly by editing the affected file.
   - **Judgment calls** (e.g., scope conflict, interface mismatch requiring a design decision): convert to new open questions using the appropriate `OQ-` prefix and insert into the relevant document.
   - Increment the reconciliation iteration counter.
   - If iteration counter exceeds 5 for this cycle, flag remaining issues to the user and ask how to proceed rather than looping. Transition to **ASK_USER** with the flagged issues.
   - Otherwise, transition to **COLLECT**.

### State 9: CHECK

1. Scan all artifacts for any remaining `- [ ] OQ-` patterns.
2. Verify the consistency checker returned no issues on the last run.
3. If both conditions are satisfied, transition to **DONE**.
4. Otherwise, transition to **COLLECT**.

### State 10: DONE

Present a summary to the user:

**Tier 1:**
- Complexity tier and rationale
- Total task cards produced
- Execution order table
- Final folder structure (tree view)

**Tier 2 and 3:**
- Complexity tier and rationale
- Total phases and PRDs produced
- Phase dependency tiers (which phases can run in parallel)
- Key decisions made (list resolved open questions with their resolutions)
- Final folder structure (tree view)
- Any deferred items or known limitations noted during the process

After presenting the summary, output: `<promise>DECOMPOSE COMPLETE</promise>`

## Subagent Dispatch

To launch a subagent:

1. Read the appropriate prompt template file from this skill's directory using the Read tool.
2. Replace all `{{variable}}` placeholders with actual values.
3. Launch via the Task tool with `subagent_type: "general-purpose"`.
4. The prompt should instruct the subagent to write content using the Write tool to the specified output path.

When launching multiple independent subagents (e.g., parallel phase plans or parallel PRDs), use a single message with multiple Task tool calls.

## Context Summarization

To keep subagent prompts within context limits, summarize documents before passing them:

**Executive plan summary (~500 words):**
Include: vision statement, all phase names with one-sentence descriptions, key constraints, cross-phase dependencies, phase dependency tiers, resolved open questions. Exclude: detailed prose, background context, rationale paragraphs.

**Phase plan summary (~200 words):**
Include: phase objective (1 sentence), deliverable list with titles, deliverable dependency tiers, key design decisions (bullet points), resolved open questions. Exclude: full prose descriptions, detailed rationale.

**PRD summary (~200 words):**
Include: overview (1 sentence), goals list, key data structures (names only, not full code), success criteria count, dependencies, open questions. Exclude: full code blocks, detailed API signatures, non-goal explanations.

Always pass the **parent** phase plan in full (not summarized) to PRD writer subagents. Only summarize **sibling** artifacts.

## Guardrails

- **Iteration cap**: The COLLECT -> ASK_USER -> APPLY -> RECONCILE loop runs at most 5 times. After 5 iterations, present remaining issues to the user and ask for direction.
- **Never write artifact content directly**: Always delegate writing to subagents via the Task tool. The orchestrator only performs mechanical edits (checking OQ boxes, fixing names).
- **User decisions override consistency checker**: If the user's resolution conflicts with what the consistency checker suggests, the user's decision wins. Record the rationale as a comment in the affected document.
- **No silent changes**: Report every file modification to the user with a brief explanation of what changed and why.
- **Subagent scope**: Each subagent writes to exactly one file. Cross-file updates are coordinated by the orchestrator.

## Context Monitoring Integration

Degradation modifies only orchestrator coordination (batch sizes, dispatch order, checker selection, summary verbosity) -- never subagent prompt templates, artifact content quality, or state machine logic. A phase plan written at WARNING is identical in quality to one under normal conditions.

See `.claude/skills/shared/context-monitoring-reference.md` for shared procedures (warning recognition, envelope format, write/resume protocols, handoff lifecycle, subagent continuation protocol).

Track the highest severity ever observed and the state where it was first seen. Report context status at each state transition when severity is non-null.

### Degradation Actions

**CAUTION:** Max 2 concurrent subagents per batch in DECOMPOSE_PHASES, DECOMPOSE_PRDS, RECONCILE. Single-line progress reports (e.g., "Phases 01-02 plans written. Context: CAUTION (58%)."). Omit resolved OQ lists from user-facing reports.

**WARNING (includes CAUTION rules, then overrides):** Fully sequential -- 1 subagent at a time. Skip edge checkers in RECONCILE (run type checker + intra-phase + cross-phase only; iterations still count toward the cap). Reduce context summaries: executive ~300w, phase/PRD ~100w (parent phase plan still passed in full). Begin tracking handoff context mentally (current state, artifact counts, iteration counter, un-persisted user decisions).

**CRITICAL (includes WARNING rules, then):** Finish the current atomic operation: one complete subagent batch, one complete checker step, one complete scan, or one complete edit batch. A partial reconciliation iteration interrupted by CRITICAL does not count toward the 5-iteration cap. Write handoff, report, end the response. Do NOT output completion signals or promise tags — the task is unfinished; only this session's context is exhausted. See shared reference step 5.

Lightweight states (INIT, COLLECT, ASK_USER, APPLY, CHECK) are unaffected by CAUTION/WARNING -- they do not dispatch parallel subagent batches.

### Subagent CONTEXT_EXHAUSTED Handling

Continuation protocol per shared reference. Skill-specific handling:

**Writer continuation (phase-plan-writer, prd-writer):** Read `.fragment-handoff.md` from the artifact's directory and the partial artifact on disk. Build a continuation prompt listing only remaining sections/files. Track `continuation_count` per phase or per PRD.

**Checker continuation (intra-phase, cross-phase, edge):** Parse partial findings from before the `CONTEXT_EXHAUSTED:` line. Build a continuation prompt scoped to unchecked categories. Merge partial + continuation findings before deduplication in Step 4.

**Budget exhaustion:** Mark the artifact as partial (writers) or proceed with partial findings (checkers) and report to the user. Partial artifacts do not block downstream work but are flagged in the progress report.

### Session Handoff

Handoff file: `<plan_directory>/.session-handoff.md`. Uses the common envelope with optional `**Current Phase:**`, `**Notes:**`, and `**Complexity Tier:**` (1, 2, or 3).

**Snapshot rules:** The 5 shared subsections plus: reconciliation-loop states (COLLECT through RECONCILE) include `### Reconciliation State` with iteration counter, backlog, and OQ state. Non-obvious requirements:
- DECOMPOSE_PRDS Key Decisions MUST include the reconciliation backlog (discoveries from PRD writers — exists only in orchestrator memory; list each with source phase/PRD, or state "0 discoveries" explicitly)
- ASK_USER must split Open Questions into Answered (with answers — carry to APPLY without re-asking) and Unanswered; no user answers may be discarded
- DONE is terminal — never write a handoff; resume session reports "plan already complete" and exits

### Resume from Handoff

Check for `<plan_directory>/.session-handoff.md` before any INIT work. Follow shared reference for envelope validation, skill match, staleness, and user confirmation.

**Artifact inventory scan:** Glob for executive plan, phase plans, PRDs, and READMEs. Grep for resolved/unresolved OQs. Extract reconciliation backlog from snapshot (no on-disk representation). Cross-reference snapshot claims against disk — on-disk state wins. Items claimed complete but missing go back to work queue. If >50% of claims unverifiable, warn user.

**State override rules:**

| Snapshot Target | Artifact Condition | Effective State |
|----------------|-------------------|----------------|
| Any after INIT | Executive plan missing | INIT |
| DECOMPOSE_PRDS or later | Not all phase plans exist | DECOMPOSE_PHASES |
| COLLECT or later | Not all PRDs exist | DECOMPOSE_PRDS |
| ASK_USER / APPLY | Snapshot missing OQs or answers | COLLECT |
| Any reconciliation state | Missing Reconciliation State | COLLECT (iteration 1) |

Report overrides to the user.

**Context reconstruction:** Rebuild in-memory state from disk artifacts + snapshot Key Decisions. Reconciliation states also restore iteration counter, backlog, and OQ splits from Reconciliation State subsection. RECONCILE always re-enters from Step 1. DONE handoff → report "plan already complete" and exit.

**Handoff deletion:** After all restoration succeeds, before state transition. On failure or unrecognized target state, preserve handoff and fall to fresh start.

## Supporting Files

Read these files from this skill's directory (`.claude/skills/decompose-plan/` relative to the workspace root) as needed:

- `phase-plan-writer-prompt.md` — Template prompt for Phase Plan Writer subagents
- `prd-writer-prompt.md` — Template prompt for PRD Writer subagents
- `consistency-checker-intra-phase-prompt.md` — Template prompt for intra-phase consistency checkers (one per phase)
- `consistency-checker-cross-phase-prompt.md` — Template prompt for cross-phase structural checker (reads executive plan + phase plans + READMEs only)
- `consistency-checker-edge-prompt.md` — Template prompt for cross-phase edge checkers (one per dependency edge, reads PRDs from both phases)
- `artifact-templates.md` — Document skeletons for all artifact types

## Reference

The full methodology is documented in the hierarchical planning specification. The ercot-power-flow-poc project (`ercot-power-flow-poc/plans/`) provides a worked example of the artifact tree this skill produces.
