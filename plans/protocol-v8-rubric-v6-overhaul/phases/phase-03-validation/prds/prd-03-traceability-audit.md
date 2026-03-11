# PRD-03: Protocol-to-Skill Traceability Audit

## Overview

This deliverable produces `traceability-audit.md`, a structured verification document
that confirms bidirectional consistency between the v8 protocol and the skill machinery
files updated in Phases 1 and 2. The audit has four sub-checks: forward traceability
(protocol test IDs to skill files), reverse traceability (skill file references to
protocol), PHASE2 marker cleanup verification, and cross-reference integrity between
skill prompts and reference files.

The protocol defines test IDs that skill prompts implement. The skill prompts reference
watchpoint sections and methodology note sections by name. The SKILL.md orchestrator
declares variables that evaluator prompts consume. Any inconsistency between these layers
causes silent evaluation failures — a code-evaluator dispatched for a test ID that does
not exist in the protocol produces invalid results, a prompt referencing a watchpoint
section that was renamed produces a dangling reference, and a variable referenced in a
prompt but missing from the orchestrator's replacement list produces unresolved template
markers in the dispatched agent's instructions.

This is a pure verification deliverable. It produces a markdown audit report with
structured findings tables. It does not modify any protocol, rubric, or skill files. If
any sub-check fails, the finding is documented with a category ("gap", "dangling", or
"stale"), the responsible artifact is identified, and the fix is routed back to the
relevant phase.

This PRD treats "Data Structures" as the finding types and audit report schema. "API"
defines the 4 sub-check verification functions. "Success Criteria" lists the checks
that confirm each sub-check was executed correctly and produced a valid result.

## Goals

1. **Forward traceability: protocol to skill files.** Extract every test ID from the v8
   protocol (Suites A through G, including G-FNM-1 through G-FNM-5) and verify that each
   ID appears in at least one skill prompt (`code-evaluator-prompt.md`,
   `audit-evaluator-prompt.md`, `gate-evaluator-prompt.md`) or reference file
   (`test-methodology-notes.md`, `cross-tool-watchpoints.md`), either by literal mention
   or by config-driven dispatch that covers the ID's suite.

2. **Reverse traceability: skill files to protocol.** Extract every test ID referenced in
   skill prompts and reference files and verify each exists in the v8 protocol. Flag any
   IDs that reference deleted, renumbered, or nonexistent tests.

3. **PHASE2 marker cleanup verification.** Scan the v8 protocol for any remaining
   `<!-- PHASE2 -->` HTML comments and verify none remain. For each forward reference in
   the protocol that points to `test-methodology-notes.md`, verify the referenced section
   exists in that file.

4. **Cross-reference integrity between skill files.** Verify that skill prompts
   referencing watchpoint sections by name point to sections that actually exist in
   `cross-tool-watchpoints.md`. Verify that the SKILL.md orchestrator's variable
   replacement list includes all variables referenced in evaluator prompts.

5. **Categorize failures.** Every finding is categorized as one of: "gap" (missing
   coverage — a test ID or section exists in one artifact but not the corresponding one),
   "dangling" (reference to a nonexistent target — a prompt references a section or test
   ID that does not exist), or "stale" (reference to moved or renamed content — the
   target existed in a prior version but has been relocated).

6. **Produce a structured audit report.** The output is a single markdown file with one
   section per sub-check, each containing a summary verdict (pass/fail), an evidence
   table, and a findings list with categorized failures.

## Non-Goals

1. **No modification of any protocol, rubric, or skill file.** This deliverable identifies
   inconsistencies; it does not fix them. Fixes are routed back to Phase 1 or Phase 2.

2. **No execution of tests or agents.** This is a static text analysis of markdown files.
   No code is run, no agents are dispatched, no devcontainer is needed.

3. **No validation of eval-config.yaml.** Config generation and structural validation
   are covered by PRD-01 (Config Generation Smoke Test). This PRD audits the source
   artifacts that the config generator reads, not the generated output.

4. **No validation of issue-to-fix mappings.** That is PRD-02 (Cross-Reference Checklist).
   This PRD focuses on test ID and section-level traceability, not GitHub issue coverage.

5. **No content correctness verification.** This audit checks that references resolve and
   that test IDs are consistent. It does not verify that the content behind a reference is
   semantically correct or complete.

6. **No validation of result file schemas.** Result file frontmatter validation is handled
   by the VALIDATE state of the skill orchestrator. This audit covers the prompt and
   reference layer only.

## Data Structures

### Finding Categories

Every audit finding is classified into one of three categories:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FindingCategory(StrEnum):
    """Classification for traceability audit findings."""

    GAP = "gap"
    """Missing coverage. A test ID or section exists in one artifact but has no
    corresponding entry in the other artifact. Example: protocol defines G-FNM-3
    but no skill file mentions it."""

    DANGLING = "dangling"
    """Reference to a nonexistent target. A skill prompt references a test ID,
    section anchor, or variable that does not exist in the target file. Example:
    code-evaluator-prompt.md references 'cross-tool-watchpoints.md#formulation-
    sophistication-catalog' but no such section exists."""

    STALE = "stale"
    """Reference to moved or renamed content. The target existed in a prior version
    but has been relocated, renamed, or removed. Example: a prompt references a
    watchpoint section that was renamed from 'Formulation Catalog' to 'Formulation
    Sophistication Catalog' but the prompt still uses the old name."""
```

### Audit Finding Schema

```python
@dataclass(frozen=True)
class AuditFinding:
    """A single traceability audit finding."""

    sub_check: str
    """Which sub-check produced this finding: 'forward', 'reverse', 'phase2', or
    'cross_reference'."""

    category: FindingCategory
    """gap, dangling, or stale."""

    source_file: str
    """The file containing the reference or expectation. Relative to repo root."""

    source_location: str
    """Line number, section heading, or test ID where the issue was found."""

    target_file: str
    """The file that should contain the referenced entity. Relative to repo root."""

    target_entity: str
    """The test ID, section anchor, variable name, or marker that is missing or
    mismatched."""

    description: str
    """1-2 sentence explanation of the finding."""

    responsible_phase: str
    """'Phase 1' or 'Phase 2' — identifies which phase should fix the issue."""
```

### Sub-Check Result Schema

```python
@dataclass(frozen=True)
class SubCheckResult:
    """Result of one of the 4 sub-checks."""

    name: str
    """Sub-check identifier: 'A_forward_traceability', 'B_reverse_traceability',
    'C_phase2_marker_cleanup', 'D_cross_reference_integrity'."""

    verdict: str
    """'pass' if zero findings, 'fail' if one or more findings."""

    total_items_checked: int
    """Number of test IDs, references, markers, or variables checked."""

    findings: list[AuditFinding] = field(default_factory=list)
    """List of findings. Empty if verdict is 'pass'."""

    evidence_summary: str = ""
    """Brief summary of what was checked and the outcome, suitable for inclusion
    in the audit report's summary section."""
```

### Audit Report Schema

```python
@dataclass(frozen=True)
class TraceabilityAuditReport:
    """Complete traceability audit report structure.

    Serialized as a markdown file at:
    plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/traceability-audit.md
    """

    audit_date: str
    """ISO 8601 date of the audit."""

    protocol_version: str
    """Protocol version audited (expected: 'v8')."""

    sub_checks: list[SubCheckResult]
    """Results of the 4 sub-checks, in order A through D."""

    overall_verdict: str
    """'pass' if all sub-checks pass, 'fail' if any sub-check fails."""

    total_findings: int
    """Sum of findings across all sub-checks."""

    findings_by_category: dict[str, int]
    """Count of findings per category: {'gap': N, 'dangling': N, 'stale': N}."""

    files_audited: list[str]
    """List of all files examined during the audit (relative to repo root)."""

    recommended_actions: list[str]
    """If overall_verdict is 'fail', a list of recommended actions to resolve
    each finding, identifying the responsible phase and file."""
```

### Files Under Audit

The audit examines the following files:

| File | Role in audit |
|------|---------------|
| `evaluation_guides/Phase1_Test_Protocol.md` | Source of truth for test IDs (Suites A-G), forward references to `test-methodology-notes.md`, and absence of `<!-- PHASE2 -->` markers |
| `.claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md` | Contains test ID references, watchpoint section references, variable placeholders |
| `.claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md` | Contains test ID references for audit dimensions (D, E, F, P2) |
| `.claude/skills/evaluate-tool/prompts/gate-evaluator-prompt.md` | Contains test ID references for gate tests |
| `.claude/skills/evaluate-tool/references/test-methodology-notes.md` | Target of forward references from protocol; contains test ID annotations in note headers |
| `.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md` | Target of section references from code-evaluator prompt |
| `.claude/skills/evaluate-tool/SKILL.md` | Declares variable replacement lists for evaluator prompts |
| `.claude/skills/evaluate-tool/prompts/research-prompt.md` | Contains variable placeholders consumed by SKILL.md dispatch |
| `.claude/skills/evaluate-tool/prompts/config-generator-prompt.md` | References protocol structure; may contain test ID patterns |

## API

### Sub-Check A: Forward Traceability

```python
from __future__ import annotations

from pathlib import Path


PROTOCOL_PATH = Path("evaluation_guides/Phase1_Test_Protocol.md")
SKILL_DIR = Path(".claude/skills/evaluate-tool")

SKILL_FILES = [
    SKILL_DIR / "prompts/code-evaluator-prompt.md",
    SKILL_DIR / "prompts/audit-evaluator-prompt.md",
    SKILL_DIR / "prompts/gate-evaluator-prompt.md",
    SKILL_DIR / "references/test-methodology-notes.md",
    SKILL_DIR / "references/cross-tool-watchpoints.md",
    SKILL_DIR / "SKILL.md",
]


def extract_protocol_test_ids(protocol_text: str) -> list[str]:
    """Extract all test IDs from the v8 protocol test tables.

    Scans for IDs matching the patterns:
    - Suite A: A-1 through A-11
    - Suite B: B-1 through B-9
    - Suite C: C-1 through C-10
    - Suite D: D-1 through D-5
    - Suite E: E-1 through E-7
    - Suite F: F-1 through F-9
    - Suite G: G-FNM-1 through G-FNM-5
    - Gate: G-1, G-2, G-3 (or equivalent gate test IDs)
    - P2: P2-1 through P2-N (if present)

    Returns deduplicated, sorted list of test IDs found in protocol table rows.
    Does not include test IDs mentioned only in prose (those are captured by
    reverse traceability).
    """
    ...


def check_forward_traceability(
    protocol_test_ids: list[str],
    skill_file_contents: dict[str, str],
) -> SubCheckResult:
    """Verify every protocol test ID appears in at least one skill file.

    For each test ID from extract_protocol_test_ids:
    1. Search all skill file contents for a literal match of the test ID.
    2. If no literal match, check whether the test ID's suite is covered by
       config-driven dispatch (e.g., the code-evaluator prompt handles all
       test IDs in a dimension via {{test_ids}} variable replacement, so
       individual IDs need not be hardcoded — but the prompt must reference
       the suite or dimension by name).
    3. If neither literal match nor suite-level coverage is found, record a
       GAP finding.

    Returns SubCheckResult with verdict, item count, and findings.
    """
    ...


def identify_suite_level_coverage(
    prompt_text: str,
    suite_name: str,
) -> bool:
    """Check whether a prompt covers a suite via config-driven dispatch.

    A prompt provides suite-level coverage if:
    - It references the suite by name (e.g., 'Suite G', 'FNM Ingestion',
      'fnm_ingestion') in a methodology section, OR
    - It uses {{test_ids}} variable replacement and the suite's dimension
      is listed in the prompt's scope, OR
    - The SKILL.md orchestrator dispatches the prompt for the suite's dimension.

    Returns True if suite-level coverage exists.
    """
    ...
```

### Sub-Check B: Reverse Traceability

```python
def extract_skill_file_test_ids(skill_file_contents: dict[str, str]) -> dict[str, list[str]]:
    """Extract all test IDs referenced in skill files.

    Scans each skill file for strings matching test ID patterns (A-N, B-N, C-N,
    D-N, E-N, F-N, G-FNM-N, GATE-*, P2-N). Returns a dict mapping file path
    to list of test IDs found in that file.

    Excludes test IDs inside code blocks that are clearly example/template text
    (e.g., '{{test_ids}}' placeholder descriptions).
    """
    ...


def check_reverse_traceability(
    protocol_test_ids: list[str],
    skill_file_test_ids: dict[str, list[str]],
) -> SubCheckResult:
    """Verify every test ID in skill files exists in the protocol.

    For each test ID found in any skill file:
    1. Check whether it exists in the protocol_test_ids set.
    2. If not found, determine whether the ID was renamed (STALE) or never
       existed (DANGLING) by checking common renumbering patterns (e.g.,
       an old ID that was split or merged in v8).
    3. Record the finding with the source file and the nonexistent ID.

    Returns SubCheckResult with verdict, item count, and findings.
    """
    ...
```

### Sub-Check C: PHASE2 Marker Cleanup

```python
def check_phase2_marker_cleanup(
    protocol_text: str,
    methodology_notes_text: str,
) -> SubCheckResult:
    """Verify PHASE2 markers are cleaned up and forward references resolve.

    Two verification passes:

    Pass 1 — Marker absence:
    Scan protocol_text for any HTML comments containing 'PHASE2' (case-insensitive).
    This includes:
    - '<!-- PHASE2: move to test-methodology-notes.md -->'
    - '<!-- PHASE2 -->'
    - Any other variant containing 'PHASE2'
    If any are found, record a STALE finding for each (the marker should have been
    consumed by Phase 2 Deliverable 1 and removed).

    Pass 2 — Forward reference resolution:
    Scan protocol_text for forward references to test-methodology-notes.md. These
    have the form:
    - '*See test-methodology-notes.md for implementation guidance.*'
    - References with section anchors: 'test-methodology-notes.md#suite-a-expressiveness'
    For each forward reference:
    - Verify that test-methodology-notes.md exists (it should, per Phase 2 PRD-01).
    - If the reference includes a section anchor (e.g., #suite-g-fnm-ingestion),
      verify that the anchor exists as a heading in the methodology notes file.
    - If the file or anchor does not exist, record a DANGLING finding.

    Returns SubCheckResult with counts and findings.
    """
    ...


def extract_forward_references(protocol_text: str) -> list[dict[str, str]]:
    """Extract all forward references to test-methodology-notes.md from the protocol.

    Returns a list of dicts, each with:
    - 'line_number': approximate line in the protocol
    - 'reference_text': the full reference string
    - 'target_file': 'test-methodology-notes.md'
    - 'target_anchor': section anchor if present (e.g., '#suite-a-expressiveness'),
      or empty string if the reference is to the file as a whole
    """
    ...


def extract_methodology_note_anchors(notes_text: str) -> list[str]:
    """Extract all section anchors from test-methodology-notes.md.

    Returns a list of markdown heading anchors (e.g., '#suite-a-expressiveness',
    '#a-7-contingency-sweep-algorithm'). These are the valid targets for forward
    references.
    """
    ...
```

### Sub-Check D: Cross-Reference Integrity

```python
def check_cross_reference_integrity(
    skill_file_contents: dict[str, str],
) -> SubCheckResult:
    """Verify cross-references between skill files are valid.

    Two verification passes:

    Pass 1 — Watchpoint section references:
    Scan code-evaluator-prompt.md (and audit-evaluator-prompt.md if applicable)
    for references to cross-tool-watchpoints.md section anchors. These appear as:
    - 'cross-tool-watchpoints.md#<section-anchor>'
    - 'See the <Section Name> section in cross-tool-watchpoints.md'
    - 'Formulation Sophistication Catalog' (section name used without file prefix)
    For each reference, verify the target section exists in cross-tool-watchpoints.md
    by checking H2 headings and their corresponding anchors.
    If a referenced section does not exist, record a DANGLING finding.

    Pass 2 — SKILL.md variable completeness:
    Extract the set of template variables ({{variable_name}}) referenced in:
    - code-evaluator-prompt.md
    - audit-evaluator-prompt.md
    - gate-evaluator-prompt.md
    - research-prompt.md
    - config-generator-prompt.md
    For each variable, verify it appears in the SKILL.md variable replacement list
    for the appropriate state and agent archetype. Specifically:
    - Code-evaluator variables must appear in EVALUATE state step 2b
    - Audit-evaluator variables must appear in EVALUATE state step 2b
    - Gate-evaluator variables must appear in GATE state step 2
    - Research prompt variables must appear in RESEARCH state step 2
    - Config-generator variables must appear in CONFIGURE state step 2
    If a variable is referenced in a prompt but not declared in SKILL.md's
    replacement list for that archetype, record a GAP finding.

    Returns SubCheckResult with counts and findings.
    """
    ...


def extract_watchpoint_section_references(
    prompt_text: str,
) -> list[dict[str, str]]:
    """Extract references to cross-tool-watchpoints.md sections from a prompt.

    Returns a list of dicts, each with:
    - 'reference_text': the reference as it appears in the prompt
    - 'target_anchor': the section anchor being referenced (e.g.,
      '#formulation-sophistication-catalog')
    - 'target_section_name': the human-readable section name if available
    """
    ...


def extract_watchpoint_sections(watchpoints_text: str) -> list[dict[str, str]]:
    """Extract H2 sections from cross-tool-watchpoints.md.

    Returns a list of dicts, each with:
    - 'heading': the H2 heading text
    - 'anchor': the markdown anchor (e.g., '#formulation-sophistication-catalog')
    """
    ...


def extract_prompt_variables(prompt_text: str) -> list[str]:
    """Extract all {{variable_name}} template variables from a prompt.

    Returns deduplicated list of variable names (without the {{ }} delimiters).
    Excludes variables that appear inside code blocks showing example output
    (e.g., YAML frontmatter examples with {{tool_name}} as placeholder illustration).
    """
    ...


def extract_skill_md_variables(
    skill_text: str,
    state: str,
    archetype: str,
) -> list[str]:
    """Extract variables declared in SKILL.md for a given state and archetype.

    Scans the SKILL.md section for the specified state (CONFIGURE, RESEARCH, GATE,
    EVALUATE, SYNTHESIZE) and agent archetype (code-evaluator, audit-evaluator,
    gate-evaluator, research, config-generator). Returns the list of variable names
    that appear in the variable replacement step for that state/archetype combination.

    For the EVALUATE state, code-evaluator and audit-evaluator have separate
    variable lists — the archetype parameter selects which list to return.
    """
    ...
```

## Success Criteria

Each criterion is a verifiable check on the audit report and the process that produced
it. They are grouped by sub-check.

### Sub-Check A: Forward Traceability (4 checks)

1. **SC-01: All Suite A-F test IDs checked.** The forward traceability section's evidence
   table lists every test ID from Suites A through F (A-1 through A-11, B-1 through B-9,
   C-1 through C-10, D-1 through D-5, E-1 through E-7, F-1 through F-9) with a pass/fail
   status for each. No test ID is omitted from the check.

2. **SC-02: All Suite G test IDs checked.** The forward traceability section's evidence
   table lists G-FNM-1 through G-FNM-5 with a pass/fail status for each. The check
   accounts for the fact that Suite G test IDs may be covered by config-driven dispatch
   in the code-evaluator prompt's Suite G methodology section rather than literal ID
   mentions.

3. **SC-03: Gate test IDs checked.** The forward traceability section's evidence table
   includes gate test IDs (G-1, G-2, G-3 or equivalent) with
   coverage traced to the gate-evaluator prompt.

4. **SC-04: Forward traceability verdict is justified.** If the verdict is "pass", the
   evidence table shows coverage for every protocol test ID. If the verdict is "fail",
   each finding identifies the specific test ID lacking coverage, the category is "gap",
   and the responsible phase is identified.

### Sub-Check B: Reverse Traceability (4 checks)

5. **SC-05: All skill files scanned.** The reverse traceability section lists every skill
   file examined (at minimum: `code-evaluator-prompt.md`, `audit-evaluator-prompt.md`,
   `gate-evaluator-prompt.md`, `test-methodology-notes.md`, `cross-tool-watchpoints.md`)
   and the test IDs extracted from each.

6. **SC-06: Test IDs from methodology notes checked.** Every test ID appearing in note
   header annotations in `test-methodology-notes.md` (e.g., `[A-7]`, `[G-FNM-1]`) is
   verified against the protocol's test ID inventory. This catches test IDs that may have
   been mistyped during the Phase 2 extraction.

7. **SC-07: Dangling test IDs flagged.** Any test ID found in a skill file that does not
   exist in the v8 protocol is recorded as a "dangling" finding with the source file and
   line/section where it appears.

8. **SC-08: Stale test IDs distinguished from dangling.** If a test ID in a skill file
   matches a known v7 test ID that was renumbered or removed in v8, the finding is
   categorized as "stale" (not "dangling"), with a note identifying the old-to-new
   mapping if determinable.

### Sub-Check C: PHASE2 Marker Cleanup (3 checks)

9. **SC-09: Protocol scanned for PHASE2 markers.** The audit report explicitly states
   whether any `<!-- PHASE2 -->` HTML comments remain in the v8 protocol. The scan
   covers all variants: `<!-- PHASE2: move to test-methodology-notes.md -->`,
   `<!-- PHASE2 -->`, and any other comment containing the string "PHASE2".

10. **SC-10: Forward references to test-methodology-notes.md resolved.** For each
    forward reference in the protocol (of the form `*See test-methodology-notes.md ...*`),
    the audit report confirms that the target file exists and, if a section anchor is
    specified, that the anchor resolves to an existing heading in the file. Any
    unresolvable reference is recorded as a "dangling" finding.

11. **SC-11: Forward reference count reported.** The audit report states the total number
    of forward references to `test-methodology-notes.md` found in the protocol, enabling
    cross-validation against the expected count from Phase 1 PRD-02 (at least 4 forward
    references for the 4 confirmed purely agent-facing note removals, up to 6 if
    additional reclassifications occurred).

### Sub-Check D: Cross-Reference Integrity (5 checks)

12. **SC-12: Watchpoint section references validated.** Every reference to a
    `cross-tool-watchpoints.md` section in evaluator prompts is checked against the
    actual H2 headings in that file. The audit report lists each reference and its
    resolution status. The check must cover at minimum the "Formulation Sophistication
    Catalog" reference from the code-evaluator prompt's formulation_difference procedure.

13. **SC-13: New watchpoint sections verified.** The 5 new watchpoint sections added by
    Phase 2 PRD-02 ("Suite G Format Context", "Formulation Sophistication Catalog",
    "Post-Ingestion Fidelity Checks", "baseMVA and Q-Limit Pitfalls", "PowerModels
    solve_dc_pf Pitfall") are confirmed to exist as H2 headings in
    `cross-tool-watchpoints.md`. Any prompt reference to these sections resolves
    successfully.

14. **SC-14: SKILL.md variable completeness for code-evaluator.** Every `{{variable}}`
    referenced in `code-evaluator-prompt.md` is verified to appear in SKILL.md's EVALUATE
    state variable replacement list for the code-evaluator archetype. This must include
    the new `{{version_capability_report}}` variable added by Phase 2 PRD-06. Any missing
    variable is recorded as a "gap" finding.

15. **SC-15: SKILL.md variable completeness for other archetypes.** Every `{{variable}}`
    referenced in `audit-evaluator-prompt.md`, `gate-evaluator-prompt.md`,
    `research-prompt.md`, and `config-generator-prompt.md` is verified against the
    corresponding SKILL.md state and archetype. Variables specific to code-evaluator
    (e.g., `{{version_capability_report}}`) must NOT appear in the audit-evaluator
    variable list.

16. **SC-16: Reference file list in SKILL.md complete.** The `{{reference_files}}` list
    in SKILL.md's EVALUATE state step 2b includes `test-methodology-notes.md` alongside
    the existing reference files (`solver-config.md`, `convergence-protocol.md`,
    `cross-tool-watchpoints.md`, etc.). If the new reference file is missing from the
    dispatch list, it is recorded as a "gap" finding.

### Report Structure (2 checks)

17. **SC-17: Audit report follows schema.** The output file `traceability-audit.md`
    contains: an audit metadata header (date, protocol version), an overall verdict, a
    findings summary table (counts by category), one section per sub-check (A through D)
    each with verdict and evidence, and a recommended actions section if any findings
    exist.

18. **SC-18: All findings have required fields.** Every finding in the report includes:
    sub-check identifier, finding category (gap/dangling/stale), source file, source
    location, target file, target entity, description, and responsible phase. No finding
    is missing any of these fields.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/traceability-audit.md` | Create | Structured audit report with findings from all 4 sub-checks |

No existing files are modified. The audit reads the following files but does not edit them:

| File | Read purpose |
|------|-------------|
| `evaluation_guides/Phase1_Test_Protocol.md` | Extract test IDs, scan for PHASE2 markers and forward references |
| `.claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md` | Extract test ID references, watchpoint section references, template variables |
| `.claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md` | Extract test ID references, template variables |
| `.claude/skills/evaluate-tool/prompts/gate-evaluator-prompt.md` | Extract test ID references, template variables |
| `.claude/skills/evaluate-tool/prompts/research-prompt.md` | Extract template variables |
| `.claude/skills/evaluate-tool/prompts/config-generator-prompt.md` | Extract template variables |
| `.claude/skills/evaluate-tool/references/test-methodology-notes.md` | Validate forward reference targets, extract test ID annotations |
| `.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md` | Validate watchpoint section reference targets |
| `.claude/skills/evaluate-tool/SKILL.md` | Extract variable replacement lists per state/archetype |

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

### Internal Dependencies

- **Phase 1 Deliverable 1 (protocol v8 G-FNM formulation).** The protocol must have the
  v8 Suite G test definitions (G-FNM-1 through G-FNM-5 with updated descriptions) and
  the formulation_difference annotations. This PRD extracts test IDs from the final v8
  protocol.

- **Phase 1 Deliverable 2 (protocol v8 thinning).** The protocol must have completed
  note thinning: purely agent-facing notes removed with forward references inserted,
  hybrid notes trimmed with `<!-- PHASE2 -->` markers consumed (not remaining). This PRD
  checks that the thinning was cleanly completed.

- **Phase 2 Deliverable 1 (test-methodology-notes.md).** The methodology notes file must
  exist and contain the extracted agent-facing notes organized by suite with test ID
  annotations. This PRD validates that forward references in the protocol resolve to
  existing sections in this file.

- **Phase 2 Deliverable 2 (cross-tool-watchpoints.md).** The watchpoints file must
  contain the 5 new sections. This PRD validates that prompt references to watchpoint
  sections resolve correctly.

- **Phase 2 Deliverable 4 (code-evaluator-prompt.md).** The code-evaluator prompt must
  contain the 4 updates (CSV input path, ingestion count gate, formulation_difference
  procedure, version capability input). This PRD checks variable declarations and
  watchpoint references in the updated prompt.

- **Phase 2 Deliverable 5 (audit-evaluator-prompt.md).** The audit-evaluator prompt must
  contain the E-3 reviewer concentration update. This PRD checks test ID references.

- **Phase 2 Deliverable 6 (SKILL.md).** The orchestrator must contain Agent 4 dispatch
  and `{{version_capability_report}}` variable wiring. This PRD validates that all
  prompt variables are covered in the orchestrator's replacement lists.

### External Dependencies

None. This deliverable reads only files within the repository.

### Downstream Consumers

- **Project maintainer.** Uses the audit report to confirm the overhaul is internally
  consistent before merging to main. If findings exist, they are routed back to the
  responsible phase for remediation.

- **No automated consumers.** This is a terminal verification artifact with no downstream
  automation dependencies.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Bidirectional traceability (forward + reverse): confirmed.
- Three finding categories (gap, dangling, stale): confirmed.
- PHASE2 marker cleanup as part of this audit (not a separate deliverable): confirmed.
- Cross-reference integrity covers both watchpoint sections and SKILL.md variables: confirmed.
- Static text analysis only (no code execution, no agent dispatch): confirmed.
- Output location in phase-03-validation directory: confirmed.
