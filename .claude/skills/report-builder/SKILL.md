---
name: report-builder
description: >
  Build the full Docusaurus report site from evaluation data. Consumes calibrated
  grades from sweep-evaluations plus per-tool test results from evaluate-tool, performs
  lexicographic ranking and sensitivity analysis, writes all MDX pages and JSON data
  files, generates charts, verifies factual consistency, and runs the Docusaurus build.
  Use when the user mentions "build the report", "generate report site", "write report
  pages", "rebuild the report", "update the report site", "report-builder", or wants
  to produce the customer-deliverable report from evaluation results. Also trigger when
  the user says "selection report", "tool ranking", "final recommendation", or "compare
  all tools" -- this skill replaces the retired synthesize-selection skill.
argument-hint: "[protocol_version] (default: v10)"
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

# /report-builder -- Orchestrator

You produce the Phase 1 Tool Selection Report site for contract FA714626C0006. This is
a customer-deliverable Docusaurus site -- GRC is staking its professional recommendation
on this output. Every claim must trace to evaluation evidence, and the report must be
free of internal process artifacts.

## Argument Parsing

The user invokes: `/report-builder [protocol_version]`

Default protocol version: `v10`

Set these variables for the session:

```
PROTOCOL_VERSION = <protocol_version>
SKILL_DIR        = .claude/skills/report-builder
GUIDES_DIR       = evaluation_guides
RUBRIC_PATH      = {{GUIDES_DIR}}/Phase1_Evaluation_Rubric.md
PROTOCOL_PATH    = {{GUIDES_DIR}}/Phase1_Test_Protocol.md
REPORT_DIR       = report
DOCS_DIR         = {{REPORT_DIR}}/docs
DATA_DIR         = {{REPORT_DIR}}/data
SCRIPTS_DIR      = {{REPORT_DIR}}/scripts
SOW_PATH         = data/whitepaper_proposal.md
TOOLS            = [pypsa, pandapower, gridcal, powermodels, powersimulations, matpower]
NETWORK_DIR      = data/networks
```

## Execution Environment

All commands run inside the devcontainer. Use `.devcontainer/dc-exec <command>` for
every shell operation. Never run locally.

## State Machine

```
DISCOVER -> EXTRACT -> CONFIRM -> RANK -> SENSITIVITY -> GENERATE -> VERIFY -> BUILD -> REVIEW -> COMMIT
```

---

### State: DISCOVER

**Purpose:** Find all per-tool synthesis files and the sweep-evaluations grade table.

Evaluation results live on worktree branches (e.g., `worktree-eval/pypsa-v10`). Sweep
results may be on a sweep branch or merged to main. Always read from **branch HEAD**
via `git show` rather than assuming the filesystem is up to date.

1. **Locate sweep grade table.** The sweep-evaluations skill produces a calibrated grade
   table. Check for it in:
   - `sweep-data/` or `sweep-reports/` directories on main or sweep branches
   - Look for a YAML or markdown file containing the cross-tool grade table
   - If not found, inform user that sweep-evaluations must be run first.

2. **Locate per-tool synthesis files.** For each tool in `TOOLS`, probe the branch HEAD:

   ```bash
   git show worktree-eval/<tool>-{{PROTOCOL_VERSION}}:evaluations/<tool>/results/synthesis.md
   ```

   Also check for per-tool result files in the same path.

3. **Locate per-tool test result files.** For each tool, find all result files:

   ```bash
   git show worktree-eval/<tool>-{{PROTOCOL_VERSION}}:evaluations/<tool>/results/
   ```

4. **Read network case files for bus counts.** Read the actual MATPOWER .m files to
   determine correct bus counts for each network tier. Do not hardcode bus counts --
   derive them from the data:

   ```bash
   # Count buses in each case file
   grep -c "^[[:space:]]*[0-9]" {{NETWORK_DIR}}/case*.m
   ```

   Store these counts for factual verification in VERIFY state.

5. **Report to user.** Present:
   - Whether sweep grade table was found (with location)
   - Tools with synthesis files found (with branch and PR#)
   - Tools missing synthesis files
   - Bus counts derived from network files

6. **Ask user.** Use AskUserQuestion:
   > "Found synthesis files for N of 6 tools and [found/did not find] the sweep grade
   > table. Proceed with available data?"
   >
   > Options: "Proceed", "Wait for missing data"

---

### State: EXTRACT

**Purpose:** Extract structured evaluation data from synthesis files and sweep output.

Grades come from sweep-evaluations (the grading authority), not from per-tool synthesis
files. Synthesis files provide everything else: P2 readiness, strengths/weaknesses,
workarounds, test evidence, and caveats.

1. **Read the rubric.** Load `{{RUBRIC_PATH}}` for canonical criterion names.

2. **Read the sweep grade table.** Parse the calibrated grades produced by
   sweep-evaluations. This is the authoritative source for all tier assignments.

3. **Build extraction input.** For each available tool, read its synthesis.md from the
   branch HEAD. Concatenate with clear delimiters:

   ```
   === TOOL: <tool_name> ===
   === SOURCE: worktree-eval/<tool>-{{PROTOCOL_VERSION}}:evaluations/<tool>/results/synthesis.md ===
   <contents>
   === END: <tool_name> ===
   ```

4. **Dispatch extractor subagent.** Read `{{SKILL_DIR}}/prompts/extractor-prompt.md` and
   replace variables:
   - `{{synthesis_contents}}` -> concatenated synthesis files
   - `{{rubric_path}}` -> `{{RUBRIC_PATH}}`
   - `{{tool_names}}` -> comma-separated list of available tools
   - `{{sweep_grades}}` -> the sweep grade table

   Launch via Agent tool with `subagent_type: "general-purpose"`.

5. **Parse extraction output.** The subagent returns structured markdown tables for
   grades, P2 readiness, strengths/weaknesses, workarounds, and caveats.

---

### State: CONFIRM

**Purpose:** Human verification of grades and extracted data before ranking.

The grade table comes from sweep-evaluations, but the user must confirm it before it
feeds into the mechanical ranking. Getting grades wrong invalidates the entire report.

1. **Display grade table.** Show a clean markdown table:

   ```
   | Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
   |------|---------------|---------------|-------------|---------------|----------|--------------|
   | ...  | ...           | ...           | ...         | ...           | ...      | ...          |
   ```

2. **Display P2 readiness summary.** Show pass/fail for P2-1, P2-2, P2-3 per tool.

3. **Display strengths/weaknesses.** Top 2 strengths and 2 weaknesses per tool.

4. **Ask user.** Use AskUserQuestion:
   > "Are these grades and extracted data correct?"
   >
   > Options: "Approve", "Edit (specify corrections)", "Re-extract from scratch"

   On "Edit": apply corrections and re-confirm.
   On "Re-extract": return to EXTRACT state.

---

### State: RANK

**Purpose:** Mechanical lexicographic ranking -- purely algorithmic, no judgment.

This state is identical to the retired synthesize-selection RANK state.

1. **Gate checks.** Apply two gates in order:

   a. **Rubric exclusions.** Read the rubric for "reference benchmark only" designations.
      These tools are excluded from primary ranking but kept in the grade table with a
      footnote. The exclusion rationale for MATPOWER: the customer specifically asked in
      the kickoff call for source code they can inspect, which precludes a compiled
      binary like the MATLAB/Octave runtime.

   b. **Supply Chain gate.** Any remaining tool with Supply Chain tier of Weak or
      Failing is **disqualified**:
      - Strong or Adequate: passes gate
      - Weak or Failing: disqualified

   If ALL tools are excluded or disqualified, inform user and stop.

2. **Lexicographic comparison.** Compare surviving tools in strict priority order:
   1. Expressiveness
   2. Extensibility
   3. Scalability
   4. Accessibility (Workforce Accessibility)
   5. Maturity (Maturity & Sustainability)

   Tier ordering (best to worst): Strong > Adequate > Weak > Failing

   Compare on criterion 1 first. If tied, move to criterion 2, and so on.

3. **Tiebreaker 1: count of top tiers.** If tied across all 5, count Strong tiers
   across ALL criteria (including Supply Chain).

4. **Tiebreaker 2: user escalation.** If still tied, use AskUserQuestion:
   > "Tools X and Y are tied across all criteria. Which should rank higher, and why?"

5. **Output strict ordering.** Rank 1 through N with brief explanation of which criteria
   drove the ordering.

---

### State: SENSITIVITY

**Purpose:** Test whether the recommendation is robust to alternative weightings.

If only 1 tool survived the gate, skip this state entirely.

1. **Identify tightest margins.** Find criteria where #1 and #2 differ by the smallest
   gap (or are tied). These are leverage points.

2. **Propose 1-3 scenarios.** Examples:
   - "What if Scalability were the top priority instead of Expressiveness?"
   - "What if we dropped Maturity from the ranking?"
   - "What if Supply Chain were weighted instead of gated?"
   - "What if Accessibility and Extensibility swapped priority?"

   Each scenario should target a realistic concern a stakeholder might raise.

3. **Ask user.** Use AskUserQuestion:
   > "I've identified N sensitivity scenarios. [list them]. Confirm, modify, or skip?"

4. **Recompute rankings.** For each confirmed scenario, recompute and record:
   - Does #1 change? If so, to what?
   - How does the full ordering change?
   - **Narrative emphasis:** Note which tools hold stable positions across all scenarios
     vs tools that only top a single scenario. A tool that tops one scenario but cannot
     meet Phase 2 requirements is not meaningful -- flag this explicitly.

5. **Record results** for inclusion in the report.

---

### State: GENERATE

**Purpose:** Write all Docusaurus report site content from evaluation data.

This is the heaviest state. It produces JSON data files, MDX pages, the selection
report, and charts. Everything is rebuilt from the latest evaluation data -- never
carry forward stale content from earlier runs.

Read `{{SKILL_DIR}}/references/content-rules.md` before dispatching any writer agent.
These rules are non-negotiable for all generated content.

Read `{{SKILL_DIR}}/references/site-structure.md` for the complete page inventory and
what each page must contain.

#### Step 1: Generate JSON data files

Write the following to `{{DATA_DIR}}/`:

- **grades.json** — Grade table with numeric scale, provenance
- **sensitivity.json** — Scenarios, rankings per scenario
- **risk-register.json** — 3-5 risks with severity and mitigation
- **head-to-head.json** — Critical Phase 2 capabilities per tool
- **tool-profiles.json** — Per-tool strengths, weaknesses, workarounds

Remove internal-only data files that should not be in the customer report:
- **sweep-themes.json** — Internal sweep artifact. Delete if present.
- **probe-results.json** — Internal probe artifact. Delete if present.

#### Step 2: Dispatch page writers (parallel where independent)

Dispatch subagents to write MDX pages. Read `{{SKILL_DIR}}/prompts/site-writer-prompt.md`
for the detailed instructions given to each subagent.

The pages fall into three groups:

**Group A — Data-driven pages (rebuild every time):**
- `docs/index.mdx` — Selection report homepage (recommendation, why-X, runner-up, risk register, Phase 2 scope)
- `docs/results/index.mdx` — Results overview (grade table, sensitivity analysis)
- `docs/results/expressiveness.mdx` — Per-criterion detail
- `docs/results/extensibility.mdx`
- `docs/results/scalability.mdx`
- `docs/results/accessibility.mdx`
- `docs/results/maturity.mdx`
- `docs/results/supply-chain.mdx`
- `docs/results/head-to-head.mdx` — Phase 2 capability comparison
- `docs/tools-evaluated.mdx` — Per-tool profiles

**Group B — Reference pages (update only if data changes):**
- `docs/contract-traceability.mdx` — SOW requirement mapping
- `docs/use-cases-criteria.mdx` — Criteria descriptions
- `docs/grid-primer.mdx` — Background context

**Group C — Pages to REMOVE:**
- `docs/results/sweep-findings.mdx` — Internal artifact. Delete.
- `docs/results/probe-results.mdx` — Internal artifact. Delete.

Update `sidebars.js` to remove sweep-findings and probe-results entries.

#### Step 3: Write selection report markdown

Dispatch the selection report writer. Read
`{{SKILL_DIR}}/prompts/selection-report-prompt.md` for the subagent instructions.
Output: `{{REPORT_DIR}}/selection-report-{{PROTOCOL_VERSION}}.md`

#### Step 4: Generate charts

Run the chart generation pipeline inside the devcontainer:

```bash
.devcontainer/dc-exec -C /workspace/report python scripts/generate_charts.py
```

This reads from `{{DATA_DIR}}/` and writes SVGs to `{{REPORT_DIR}}/static/img/`.

---

### State: VERIFY

**Purpose:** Cross-validate all generated content for factual consistency.

This is the quality gate before the build. Read
`{{SKILL_DIR}}/prompts/verifier-prompt.md` for the full verification protocol.

Dispatch a verifier subagent that checks:

1. **Grade consistency.** Every grade mentioned in MDX prose matches `grades.json`.
   No page should say "B+" for a tool/criterion that's actually "B" in the data.

2. **Bus count accuracy.** Verify all network bus counts in the report match the
   actual counts derived from MATPOWER .m files in DISCOVER state.

3. **Test ID validity.** Every test ID referenced in the report (e.g., "A-3", "B-9")
   exists in the protocol and has a corresponding result file.

4. **Cross-page consistency.** Claims made on one page don't contradict claims on
   another page. The index.mdx recommendation must align with results/index.mdx
   ranking.

5. **No internal artifacts.** Scan all generated content for:
   - Protocol version mentions (e.g., "v10", "protocol v10")
   - Sweep findings references
   - Probe results references
   - Internal process notes
   - Em-dashes (U+2014) -- replace with standard punctuation

6. **No real grid names.** Run the pre-commit grid-name checker or scan for real
   ISO/RTO/utility names. Use generic terms instead.

7. **MATPOWER exclusion rationale.** Verify the report says the customer asked for
   inspectable source code, not that MATLAB "cannot receive authorization."

8. **Tier-to-finding consistency.** For each tool/criterion, verify the tier's
   severity matches the findings. Blocking architectural limitations should produce
   a Failing tier, not Weak or above.

9. **JSON-to-MDX consistency.** Every JSON data file value that appears in MDX prose
   must match exactly.

The verifier produces a structured report of all issues found. If blocking issues
exist, present them to the user and ask whether to fix and re-verify or proceed.

---

### State: BUILD

**Purpose:** Run the Docusaurus build to catch broken links and rendering errors.

```bash
.devcontainer/dc-exec -C /workspace/report npm run build
```

Docusaurus is configured with `onBrokenLinks: 'throw'`, so broken internal links
will fail the build.

If the build fails:
1. Read the error output
2. Fix the issue (usually a broken link from removing sweep-findings/probe-results)
3. Re-run the build
4. If you cannot fix it, present the error to the user

Also run validation scripts:

```bash
.devcontainer/dc-exec -C /workspace/report python scripts/validate_content.py
.devcontainer/dc-exec -C /workspace/report python scripts/validate_charts.py
```

---

### State: REVIEW

**Purpose:** Present the generated report for user approval.

1. **Summary.** Tell the user what was generated:
   - Number of MDX pages written/updated
   - Number of JSON data files written
   - Number of charts generated
   - VERIFY results (issues found and fixed, if any)
   - BUILD result (pass/fail)

2. **Key content for review.** Display:
   - The index.mdx recommendation section
   - The grade table
   - The sensitivity analysis summary
   - The risk register

3. **Ask user.** Use AskUserQuestion:
   > "Review the report site content above. The full site can be served locally with
   > `make serve` inside the devcontainer."
   >
   > Options: "Approve", "Edit (specify changes)", "Regenerate (return to GENERATE)"

   On "Edit": apply changes, re-run VERIFY and BUILD, then re-display.
   On "Regenerate": return to GENERATE state.

4. **Add provenance.** On approval, update the selection report with:
   - Synthesis file paths with git SHAs
   - Timestamp (ISO 8601)
   - Ranking algorithm description

---

### State: COMMIT

**Purpose:** Commit all report changes and push.

1. Stage all modified files in `{{REPORT_DIR}}/`.
2. Create a conventional commit:
   ```
   feat: rebuild report site from {{PROTOCOL_VERSION}} evaluation data
   ```
3. Push the branch.
4. If this is a feature branch, offer to open a PR.

---

## Content Rules (Summary)

These are enforced during GENERATE and checked during VERIFY. Full details in
`{{SKILL_DIR}}/references/content-rules.md`.

1. **No em-dashes.** Replace with commas, semicolons, hyphens, or parentheses.
2. **No internal artifacts.** No protocol versions, sweep findings, probe results, or
   internal process notes in customer-facing content.
3. **No real grid names.** Use "target ISO", "customer's network", etc.
4. **Inspectable-source rationale.** MATPOWER excluded because customer asked for
   inspectable source code, not because MATLAB "cannot receive authorization."
5. **Bus counts from data.** Derive from actual .m files, never hardcode.
6. **Sensitivity narrative.** Emphasize ranking stability across scenarios, not
   individual scenario wins by tools that can't meet Phase 2 requirements.
7. **Grade-finding alignment.** Blocking architectural limitations = Failing tier.
8. **Traceability.** Every claim references a test ID or synthesis finding.
9. **No stale data.** Always rebuild from latest evaluation results.

## Context Monitoring

Follow procedures in `shared/context-monitoring-reference.md`:

- **CAUTION:** Finish current subagent dispatch, then assess.
- **WARNING:** Let running subagents finish. Do not start new dispatches.
- **CRITICAL:** Finish current atomic operation, write handoff to
  `{{REPORT_DIR}}/.session-handoff.md`, end response.

The handoff file includes: current state, grade table, ranking results, sensitivity
results, paths to all generated artifacts, next action on resume.

## Error Handling

- **No sweep grade table:** Inform user that `/sweep-evaluations` must be run first.
- **Missing synthesis files:** List missing tools; ask whether to proceed without them.
- **Malformed synthesis file:** Flag to user; offer to proceed without that tool.
- **Build failure:** Read error, attempt fix, re-build. If unfixable, present to user.
- **Verification failures:** Present issue list; ask user whether to fix or proceed.
- **Subagent failure:** Log, inform user, offer retry.
