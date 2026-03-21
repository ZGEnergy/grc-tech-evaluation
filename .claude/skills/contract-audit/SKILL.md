---
name: contract-audit
description: >
  Audit the report site deliverables against SOW contract requirements. Reads the
  SOW (data/whitepaper_proposal.md), cross-references every requirement against the
  Docusaurus report site pages and JSON data files, identifies gaps and factual errors,
  creates or updates a contract traceability page, and runs three adversarial reviewer
  subagents to catch issues a contract officer could flag. Use when the user mentions
  "contract audit", "SOW compliance", "deliverable traceability", "contract officer
  review", "check deliverables against the contract", "audit the report", or wants to
  verify that the report meets contract requirements before submission.
argument-hint: "[--fix] [--reviewers-only] [--traceability-only]"
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

# /contract-audit -- Orchestrator

You audit the Phase 1 Technology Evaluation Report (Docusaurus site at `report/`)
against the Statement of Work (Contract FA714626C0006) to ensure every contracted
requirement is demonstrably addressed in the deliverables. This matters because the
project manager will be evaluated on whether the contracted deliverables were met, and
a contract officer could flag any gap as non-delivery.

## Argument Parsing

The user invokes: `/contract-audit [flags]`

Flags:
- `--fix` — Automatically fix factual errors and data inconsistencies found (default:
  report only)
- `--reviewers-only` — Skip traceability page creation, only run the three reviewers
- `--traceability-only` — Only create/update the traceability page, skip reviewers

Default (no flags): full audit — traceability + reviewers + fix report.

## Key Paths

```
SOW_PATH         = data/whitepaper_proposal.md
REPORT_DOCS      = report/docs/
REPORT_DATA      = report/data/
SELECTION_REPORT = report/selection-report-v10.md
TRACEABILITY     = report/docs/contract-traceability.mdx
SIDEBARS         = report/sidebars.js
GRADES_JSON      = report/data/grades.json
RISK_JSON        = report/data/risk-register.json
SENSITIVITY_JSON = report/data/sensitivity.json
```

## Phase 1: Gather Context

Read these files in parallel — you need all of them before proceeding:

1. **SOW document** (`data/whitepaper_proposal.md`) — extract every requirement,
   deliverable, and scope statement. Pay attention to Task 1.1, 1.2, 1.3 and the
   Deliverables table in Section 5.0.
2. **All MDX pages** in `report/docs/` (including subdirectories) — these are the
   deliverable content.
3. **All JSON data files** in `report/data/` — these are the source of truth for
   grades, risks, sensitivity scenarios, head-to-head comparisons, etc.
4. **Selection report** (`report/selection-report-v10.md`) — the narrative backbone.
5. **Existing traceability page** if it exists (`report/docs/contract-traceability.mdx`).

## Phase 2: Cross-Reference Requirements

For each SOW requirement, determine:
- **Addressed?** Which report page(s) and section(s) cover it?
- **Gap?** Is there a requirement with no corresponding report content?
- **Factual error?** Does any page claim something that contradicts the JSON data?

### Known SOW Requirements to Check

These are the requirements that have historically been flagged. Check all of them:

| SOW Ref | Requirement | What to look for |
|---------|-------------|------------------|
| Task 1.1 | "open-source AND proprietary technologies" | Explain why proprietary tools weren't independently evaluated (Supply Chain gate) |
| Task 1.1 | "support for long-term forecasting" | Map to multi-period optimization (UC-4/A-5) and stochastic wrapping (B-4) |
| Task 1.1 | "vulnerability identification" | Map to contingency analysis (A-7, A-9), SCOPF, N-M sweep |
| Task 1.2 | "Down-select to an initial tech stack" | Verify recommendation + runner-up are clearly stated |
| Task 1.3 | "Produce White Paper" | Verify report-to-whitepaper relationship is explained |
| §5 | "Technology Evaluation Report" | Verify the report site is identified as Deliverable 1 |
| §1.0 | California grid scope | Phase 1 is tool selection; California data is Phase 2 |

### Data Consistency Checks

These are the specific cross-page consistency checks that catch real errors:

1. **Grade consistency**: Compare every grade claim in MDX narrative text against
   `grades.json`. Common errors: grades carried from older protocol versions.
2. **Risk register**: Compare risk count, severity levels, and descriptions between
   `index.mdx` and `risk-register.json`.
3. **Sensitivity scenarios**: Compare scenario names, rankings, and "PyPSA holds #1
   in N of M scenarios" claims against `sensitivity.json`.
4. **Phase 2 scope tables**: Compare `index.mdx` scope tables against
   `selection-report-v10.md` lines 109-137.
5. **Head-to-head ratings**: Compare capability ratings in `head-to-head.mdx` against
   `head-to-head.json`.

## Phase 3: Run Reviewer Subagents

Launch three reviewer subagents **in parallel** using the Agent tool. Each reviewer
reads all deliverable content and produces a findings report. The reviewers are
adversarial — they look for problems, not confirmation.

### Reviewer 1: Contract Officer Adversary

Read the prompt from `prompts/contract-officer-adversary.md` and launch as an Explore
subagent. This reviewer:
- Reads every MDX page + selection report + SOW
- Finds every SOW requirement not demonstrably addressed
- Flags ambiguity a program auditor could exploit to claim non-delivery
- Classifies each gap as HIGH/MEDIUM/LOW severity

### Reviewer 2: Data Consistency Auditor

Read the prompt from `prompts/data-consistency-auditor.md` and launch as an Explore
subagent. This reviewer:
- Reads all MDX pages + all JSON data files
- Finds claims that contradict data
- Finds grades that disagree across pages
- Finds risks described differently in two locations
- Finds inconsistent scenario descriptions

### Reviewer 3: Validation Gatekeeper

Read the prompt from `prompts/validation-gatekeeper.md` and launch as an Explore
subagent. This reviewer:
- Checks forbidden grid operator names (run the checker script)
- Checks frontmatter correctness on all MDX pages
- Checks sidebar inclusion for all pages
- Checks internal link validity
- Checks content validation script expectations

## Phase 4: Triage Findings

After all three reviewers complete, triage their findings:

1. **Blocking issues** — factual errors, data contradictions, missing traceability.
   These must be fixed before submission.
2. **Non-blocking issues** — pre-existing problems outside the current scope, cosmetic
   issues, style concerns. Note these but don't fix them.
3. **False positives** — things that look like gaps but are actually addressed
   elsewhere or intentionally omitted (e.g., California location names forbidden by
   pre-commit hooks).

Present the triaged findings to the user and ask which non-blocking issues (if any)
they want fixed.

## Phase 5: Fix and Validate (if --fix or default)

### Fix Factual Errors

For each blocking issue:
1. Identify the authoritative data source (JSON file or selection report)
2. Edit the MDX page to match the source of truth
3. Verify the fix doesn't introduce new inconsistencies

### Create/Update Traceability Page

If `contract-traceability.mdx` doesn't exist or needs updating:

1. Create/update the page with:
   - SOW requirement → report mapping table
   - Scope rationale sections for each gap (proprietary tools, forecasting,
     vulnerability identification)
   - Contract context (Deliverable 1, Task 1, white paper relationship)
2. Set `sidebar_position: 5` (after tools-evaluated, before Evaluation Results)
3. Add `'contract-traceability'` to `sidebars.js` if not already present
4. Add a Contract Context callout to `index.mdx` if not already present
5. Add a SOW context paragraph to `use-cases-criteria.mdx` if not already present

### Build and Validate

All commands must run in the devcontainer via `.devcontainer/dc-exec`:

```bash
# Build the site
.devcontainer/dc-exec -C /workspace/report make build

# Run validation (permissive mode for placeholders)
.devcontainer/dc-exec -C /workspace/report make validate-dev

# Run pre-commit
.devcontainer/dc-exec -C /workspace pre-commit run --all-files
```

**Expected validation results:**
- `make build` must succeed (0 exit code)
- `make validate-dev` must pass all content checks. A "Missing Last updated"
  failure on a new page is expected if the page hasn't been committed yet —
  this resolves after the first commit.
- `pre-commit` may show failures in `.claude/skills/` files (pre-existing
  forbidden grid name references in skill prompts). These are not blocking.
  Your new/modified report files must pass clean.

## Phase 6: Report

Present the final audit report to the user:

```
## Contract Audit Results

### Findings by Reviewer
- **Contract Officer Adversary:** N gaps found, M addressed, K remaining
- **Data Consistency Auditor:** N inconsistencies found, M fixed, K pre-existing
- **Validation Gatekeeper:** Build ✓/✗, Validation N/M checks, Pre-commit ✓/✗

### Blocking Issues Fixed
- [list of fixes applied]

### Non-Blocking Issues (pre-existing)
- [list of issues noted but not fixed, with file paths]

### Validation Status
- Build: PASS/FAIL
- Content checks: N/M passed
- Broken links: N found
- Forbidden names: PASS/FAIL (in report files)
```

## Constraints

- **Never modify JSON data files** — they are the source of truth. If narrative
  text contradicts JSON, fix the narrative.
- **Never modify `selection-report-v10.md`** — it is the authoritative selection
  report. If other pages contradict it, fix the other pages.
- **Forbidden grid names** — the pre-commit hook blocks references to real grid
  operators and specific military installations (see `scripts/check_no_real_grid_names.py`
  for the full list). The SOW references these locations, but the report intentionally
  omits them. This is not a gap to fix — it's a security constraint. The traceability
  page should explain Phase 1 scope boundaries without naming specific locations.
- **Devcontainer only** — all builds, tests, and pre-commit must run inside the
  devcontainer via `.devcontainer/dc-exec`.
