---
name: synthesize-selection
description: >
  Synthesize all completed tool evaluations into a ranked selection recommendation.
  Reads synthesis.md files across evaluation worktrees, applies lexicographic forced
  ranking per the rubric's priority ordering, and produces a ~3-page customer-deliverable
  markdown document. Use when all (or most) tool evaluations are complete and you want
  to produce the final selection report. Also trigger when the user mentions "selection
  report", "tool ranking", "final recommendation", "compare all tools", or "which tool
  should we pick".
argument-hint: "[protocol_version] (default: v4)"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
---

# /synthesize-selection -- Orchestrator

You produce the Phase 1 tool selection report for contract FA714626C0006. This is a
customer-deliverable document — GRC is staking its professional recommendation on this
output. Accuracy and traceability matter more than speed.

## Argument Parsing

The user invokes: `/synthesize-selection [protocol_version]`

Default protocol version: `v4`

Set these variables for the session:

```
PROTOCOL_VERSION = <protocol_version>
SKILL_DIR        = .claude/skills/synthesize-selection
GUIDES_DIR       = evaluation_guides
RUBRIC_PATH      = {{GUIDES_DIR}}/Phase1_Evaluation_Rubric.md
OUTPUT_DIR       = report
TOOLS            = [pypsa, pandapower, gridcal, powermodels, powersimulations, matpower]
```

## State Machine

```
DISCOVER -> EXTRACT -> CONFIRM -> RANK -> SENSITIVITY -> DRAFT -> REVIEW
```

---

### State: DISCOVER

**Purpose:** Find all synthesis.md files across worktree branches and open PRs.

Evaluation results live on worktree branches (e.g., `worktree-eval/pypsa-v4`), typically
with open PRs against `main`. The synthesis files may not be in the worktree working
directory if the worktree wasn't updated after the evaluation completed — always read
from the **branch HEAD** rather than the filesystem.

1. **List open evaluation PRs.** Run `gh pr list --state open` via Bash. Evaluation PRs
   use branches named `worktree-eval/<tool>-{{PROTOCOL_VERSION}}`.

2. **List worktree branches.** Run `git branch --list 'worktree-eval/*'` to find all
   evaluation branches (including any without open PRs).

3. **Probe each branch for synthesis.** For each tool in `TOOLS`, try to read the
   synthesis file from the branch HEAD:

   ```bash
   git show worktree-eval/<tool>-{{PROTOCOL_VERSION}}:evaluations/<tool>/results/synthesis.md
   ```

   This works regardless of whether a worktree is mounted or whether the worktree
   working directory is up to date.

4. **Map tool -> branch + synthesis contents.** Build a lookup:
   - tool name
   - branch name
   - PR number (if an open PR exists for this branch)
   - whether synthesis.md was found on the branch HEAD
   - protocol version from the synthesis file

5. **Check protocol version.** For each found synthesis file, verify the protocol
   version matches `{{PROTOCOL_VERSION}}`. Flag any mismatches.

6. **Report to user.** Present:
   - Tools with synthesis files found (with branch and PR#)
   - Tools missing synthesis files
   - Any protocol version mismatches

7. **Ask user.** Use AskUserQuestion:
   > "Found synthesis files for N of 6 tools. Proceed with available tools, or wait for
   > remaining evaluations?"
   >
   > Options: "Proceed with available", "Wait"

   If fewer than 2 tools are available, warn that sensitivity analysis won't be meaningful
   but still allow proceeding (for dry-run / single-tool testing).

---

### State: EXTRACT

**Purpose:** Use LLM comprehension to extract a normalized grade table from all synthesis files.

1. **Read the rubric.** Load `{{RUBRIC_PATH}}` for canonical criterion names and grade
   definitions.

2. **Build extraction input.** For each available tool, read its synthesis.md from the
   branch HEAD via `git show` (the same method used in DISCOVER). Concatenate all
   synthesis files with clear headers:

   ```
   === TOOL: <tool_name> ===
   === SOURCE: worktree-eval/<tool>-{{PROTOCOL_VERSION}}:evaluations/<tool>/results/synthesis.md ===
   <contents>
   === END: <tool_name> ===
   ```

3. **Dispatch extractor subagent.** Read `{{SKILL_DIR}}/prompts/extractor-prompt.md` and
   replace variables:
   - `{{synthesis_contents}}` -> the concatenated synthesis files
   - `{{rubric_path}}` -> `{{RUBRIC_PATH}}`
   - `{{tool_names}}` -> comma-separated list of available tools

   Launch via Agent tool with `subagent_type: "general-purpose"`.

4. **Parse extraction output.** The subagent returns structured markdown tables. Read and
   preserve the extraction for the next state.

---

### State: CONFIRM

**Purpose:** Human verification of extracted grades before any ranking occurs.

This is the "trust but verify" step — the extraction uses LLM comprehension which is
robust to format variation but not infallible. Getting the grades wrong would invalidate
the entire report.

1. **Display grade table.** Show a clean markdown table:

   ```
   | Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
   |------|---------------|---------------|-------------|---------------|----------|--------------|
   | ...  | ...           | ...           | ...         | ...           | ...      | ...          |
   ```

2. **Display P2 readiness summary.** Show pass/fail for P2-1, P2-2, P2-3 per tool.

3. **Display strengths/weaknesses.** Show top 2 strengths and top 2 weaknesses per tool
   (1-line each with test IDs).

4. **Ask user.** Use AskUserQuestion:
   > "Are these extracted grades correct?"
   >
   > Options: "Approve", "Edit (specify corrections)", "Re-extract from scratch"

   On "Edit": apply the user's corrections to the grade table and re-confirm.
   On "Re-extract": return to EXTRACT state.

---

### State: RANK

**Purpose:** Mechanical lexicographic ranking — no judgment calls, purely algorithmic.

1. **Gate checks.** Apply two gates in order:

   a. **Rubric exclusions.** The rubric may designate certain tools as "reference
      benchmark only" (e.g., MATPOWER — MATLAB/Octave runtime disqualifies for
      classified deployment). These tools are **excluded from primary ranking** but
      retained in the grade table with a footnote for comparison. Read the rubric's
      tool list and the "Addendum — Tools Considered but Ruled Out" section to
      identify any such designations.

   b. **Supply Chain gate.** Any remaining tool with Supply Chain grade <= C+ is
      **disqualified**. The grade ordering for the gate threshold:
      - B- and above: passes gate
      - C+ and below: disqualified

   Excluded and disqualified tools are marked with footnotes in the output table but
   removed from the ranking competition. If ALL tools are excluded or disqualified,
   inform the user and stop.

2. **Lexicographic comparison.** Compare surviving tools in strict priority order:
   1. Expressiveness
   2. Extensibility
   3. Scalability
   4. Accessibility (Workforce Accessibility)
   5. Maturity (Maturity & Sustainability)

   Grade ordering (best to worst): A > A- > B+ > B > B- > C+ > C > C- > F

   Compare tools on criterion 1 first. If tied, move to criterion 2, and so on.

3. **Tiebreaker 1: count of top grades.** If two tools are tied across all 5 criteria
   (same grade in every position), break the tie by counting A and A- grades across
   ALL criteria (including Supply Chain).

4. **Tiebreaker 2: user escalation.** If still tied after count-of-top-grades, use
   AskUserQuestion to break the tie:
   > "Tools X and Y are tied across all criteria with identical grade profiles.
   > Which should be ranked higher, and why?"

5. **Output strict ordering.** Rank 1 through N (where N = number of non-disqualified
   tools). Report the ranking to the user with a brief explanation of which criteria
   drove the ordering.

---

### State: SENSITIVITY

**Purpose:** Test whether the recommendation is robust to alternative weighting assumptions.

If only 1 tool survived the gate, skip this state entirely (no comparison possible).

1. **Identify tightest margins.** Look at the criteria where #1 and #2 differ by the
   smallest gap (or are tied). These are the leverage points where a different weighting
   scheme could change the outcome.

2. **Propose 1-3 scenarios.** Based on the tightest margins, propose alternative
   scenarios. Examples:
   - "What if Scalability were the top priority instead of Expressiveness?"
   - "What if we dropped Maturity from the ranking?"
   - "What if Supply Chain were a weighted criterion instead of a gate?"
   - "What if Accessibility and Extensibility swapped priority?"

   Each scenario should target a realistic concern a stakeholder might raise.

3. **Ask user.** Use AskUserQuestion:
   > "I've identified N sensitivity scenarios based on the tightest margins between
   > #1 and #2. Here they are:
   >
   > 1. [scenario description]
   > 2. [scenario description]
   > 3. [scenario description]
   >
   > Confirm, modify, or skip these scenarios?"

4. **Recompute rankings.** For each confirmed scenario, recompute the ranking using
   the alternative weighting/priority order. Record:
   - Does #1 change? If so, to what?
   - How does the full ordering change?

5. **Record results.** Store scenarios and results for inclusion in the report. This
   provides reproducibility — anyone can verify the sensitivity analysis.

---

### State: DRAFT

**Purpose:** Produce the customer-deliverable selection report.

1. **Prepare inputs.** Gather all data the report writer needs:
   - Confirmed grade table (from CONFIRM)
   - Ranking results (from RANK)
   - Sensitivity analysis results (from SENSITIVITY)
   - P2 readiness findings per tool
   - Per-tool strengths, weaknesses, caveats
   - Rubric contents (for Phase 2 gap enumeration)
   - Report template

2. **Dispatch report-writer subagent.** Read `{{SKILL_DIR}}/prompts/report-writer-prompt.md`
   and replace variables:
   - `{{protocol_version}}` -> `{{PROTOCOL_VERSION}}`
   - `{{grade_table}}` -> confirmed grade table (markdown)
   - `{{ranking_results}}` -> ranking with explanations
   - `{{sensitivity_results}}` -> sensitivity scenarios and outcomes
   - `{{p2_readiness}}` -> P2 readiness findings per tool
   - `{{tool_details}}` -> per-tool strengths/weaknesses/caveats/workarounds
   - `{{rubric_path}}` -> `{{RUBRIC_PATH}}`
   - `{{template_path}}` -> `{{SKILL_DIR}}/report-template.md`
   - `{{output_path}}` -> `{{OUTPUT_DIR}}/selection-report.md`
   - `{{date}}` -> today's date (YYYY-MM-DD)

   Launch via Agent tool with `subagent_type: "general-purpose"`.

3. **Ensure output directory exists.** Create `{{OUTPUT_DIR}}/` if needed.

---

### State: REVIEW

**Purpose:** Present the report for user approval and add provenance.

1. **Display the report.** Read `{{OUTPUT_DIR}}/selection-report.md` and display
   the full contents to the user.

2. **Ask user.** Use AskUserQuestion:
   > "Review the selection report above."
   >
   > Options: "Approve", "Edit (specify changes)", "Regenerate"

   On "Edit": apply the user's changes via the Edit tool, then re-display and re-ask.
   On "Regenerate": return to DRAFT state.

3. **Add provenance footer.** On approval, append a provenance section to the report:
   - Protocol version
   - Synthesis file paths with git SHAs (run `git log -1 --format=%h -- <path>` for each)
   - Timestamp (ISO 8601)
   - Ranking algorithm description

4. **Report completion.** Tell the user:
   > "Selection report written to `{{OUTPUT_DIR}}/selection-report.md`."

---

## Context Monitoring

Follow the procedures in `shared/context-monitoring-reference.md`:

- **CAUTION:** Proceed normally — this skill is lightweight compared to evaluate-tool.
- **WARNING:** If mid-DRAFT, let the subagent finish. Do not start new subagent dispatches.
- **CRITICAL:** Finish current atomic operation, write handoff to
  `{{OUTPUT_DIR}}/.session-handoff.md`, end response.

The handoff file follows the shared envelope format, including:
- Current state
- Grade table (confirmed or extracted)
- Ranking results (if computed)
- Sensitivity results (if computed)
- Paths to all generated artifacts
- Next action to take on resume

## Error Handling

- **No synthesis files found:** Inform user that evaluations must be run first
  (`/evaluate-tool <tool>`). List which tools are missing. Stop.
- **Malformed synthesis file:** The extractor flags incomplete/malformed files. Present
  the flags to the user and ask whether to proceed without that tool or fix the file first.
- **Subagent failure:** Log the failure, inform the user, offer retry.
