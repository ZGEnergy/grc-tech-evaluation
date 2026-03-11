# PRD-02: Cross-Reference Checklist

## Overview

Produce a structured verification document (`cross-reference-checklist.md`) that maps each of the 8 GitHub issues addressed by this overhaul to its concrete fix location(s) across the three artifact layers: protocol (`evaluation_guides/Phase1_Test_Protocol.md`), rubric (`evaluation_guides/Phase1_Evaluation_Rubric.md`), and skill files (`.claude/skills/evaluate-tool/`). The checklist is the authoritative traceability record proving that every issue has been addressed and that no fix was partially applied (e.g., updated in the protocol but not propagated to the skill prompt that implements it).

This is a verification/audit deliverable, not a code change. The "Data Structures" section defines the schema for each checklist row. The "API" section defines verification functions that an auditor uses to populate and validate the checklist. The output artifact is a markdown file with a structured table and per-issue evidence blocks. If any row fails verification, the failure is documented in the checklist with a pointer to the responsible phase/PRD — Phase 3 does not fix the artifact, it identifies what needs fixing.

## Goals

1. **Complete issue coverage.** Every one of the 8 issues (#43, #48, #49, #54, #55, #56, #57, #59) has a row in the checklist with at least one confirmed fix location.

2. **Three-layer traceability.** For each issue, the checklist records whether the fix required changes in the protocol, rubric, and/or skill files, with explicit section/file citations. Layers that do not require changes for a given issue have an `N/A` entry with a one-sentence justification.

3. **Content-verified citations.** Each cited fix location is verified by reading the actual file content at that location and confirming the fix text is present — not merely by checking that the file was modified in git.

4. **Pass/fail assessment per issue.** Each row carries a pass/fail verdict indicating whether all required fix locations have been confirmed. A row fails if any cited location is missing the expected fix content, or if a required layer has no citation and no N/A justification.

5. **Actionable failure routing.** Any failed row includes a pointer to the specific Phase (1 or 2) and PRD responsible for the missing or incomplete fix, enabling targeted remediation without re-auditing the entire artifact set.

## Non-Goals

- **Modifying any artifact.** This deliverable reads artifacts; it does not edit the protocol, rubric, or skill files. Fixes go through Phases 1 or 2. (Phase plan design decision: "No code changes in this phase.")
- **Re-evaluating any tool.** The checklist verifies framework fixes, not evaluation results.
- **Verifying test ID traceability.** Bidirectional test ID mapping is PRD-03 (Traceability Audit). This PRD is issue-centric, not test-ID-centric.
- **Verifying config generation.** Config generation validation is PRD-01 (Smoke Test).
- **Verifying PHASE2 marker cleanup.** Marker verification is part of PRD-03.

## Data Structures

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ArtifactLayer(StrEnum):
    """The three artifact layers that may contain fix locations."""

    PROTOCOL = "protocol"
    RUBRIC = "rubric"
    SKILL = "skill"


class VerificationStatus(StrEnum):
    """Outcome of verifying a single fix location."""

    PASS = "pass"          # Fix content confirmed present at cited location
    FAIL = "fail"          # Fix content missing or incomplete at cited location
    NOT_APPLICABLE = "n/a" # This layer does not require changes for this issue


@dataclass(frozen=True)
class FixLocation:
    """A single fix location within one artifact layer.

    Each location identifies a specific file and section where fix content
    should be present, plus the verification evidence.
    """

    layer: ArtifactLayer
    file_path: str                   # Relative path from repo root
    section_or_line: str             # Section heading, line range, or key identifier
    expected_content_summary: str    # What the fix should contain (1-2 sentences)
    status: VerificationStatus
    evidence: str                    # Quoted text or N/A justification (1-3 sentences)
    responsible_prd: str | None      # e.g. "Phase 1 PRD-01" — populated on FAIL


@dataclass(frozen=True)
class IssueChecklistRow:
    """One row of the cross-reference checklist, mapping a single GitHub issue
    to its fix locations across all three artifact layers.

    A row passes only when every FixLocation has status PASS or NOT_APPLICABLE.
    """

    issue_number: int                # GitHub issue number (e.g. 43)
    issue_title: str                 # Short title from the issue
    problem_description: str         # 1-2 sentence summary of what the issue reported
    fix_locations: list[FixLocation] # One or more entries per layer; at least one per layer
    overall_status: VerificationStatus  # PASS if all locations pass; FAIL if any fails


@dataclass
class CrossReferenceChecklist:
    """The complete checklist document, containing one row per issue.

    The checklist is complete when it has exactly 8 rows (one per issue)
    and every row has been verified.
    """

    rows: list[IssueChecklistRow] = field(default_factory=list)
    auditor_notes: str = ""          # Free-text notes from the auditor
    audit_date: str = ""             # ISO date of the audit

    @property
    def all_passed(self) -> bool:
        """True if every row has overall_status == PASS."""
        return all(r.overall_status == VerificationStatus.PASS for r in self.rows)

    @property
    def issue_count(self) -> int:
        return len(self.rows)

    @property
    def failed_issues(self) -> list[int]:
        return [r.issue_number for r in self.rows
                if r.overall_status == VerificationStatus.FAIL]
```

### Issue-to-Layer Mapping (Expected)

The following table defines which artifact layers are expected to require changes for each issue. This is the auditor's reference for populating N/A entries.

| Issue | Protocol | Rubric | Skill Files | Primary PRD(s) |
|-------|----------|--------|-------------|-----------------|
| #43 — MATPOWER format bias in Suite G | Yes (G-FNM-3/4 input path, Reference Networks table) | N/A | Yes (code-evaluator-prompt CSV path, cross-tool-watchpoints format context) | P1-D1, P2-D2, P2-D4 |
| #48 — formulation_difference tag needed | Yes (tag definition, decision procedure, pass_conditions.json) | N/A | Yes (code-evaluator-prompt tag procedure, cross-tool-watchpoints formulation catalog) | P1-D1, P2-D2, P2-D4 |
| #49 — protocol thinning / agent-facing note duplication | Yes (note removals, trims, forward references) | N/A | Yes (test-methodology-notes.md created with extracted content) | P1-D2, P2-D1 |
| #54 — Criterion 5 conflates maturity and sustainability | N/A | Yes (5a/5b split, separate grading standards, composite matrix) | Yes (audit-evaluator-prompt 5a/5b structure) | P1-D3, P2-D5 |
| #55 — version-awareness gap | Yes (Version Compatibility section) | N/A | Yes (research-prompt version agent, code-evaluator version report consumption, SKILL.md orchestrator) | P1-D2, P2-D3, P2-D4, P2-D6 |
| #56 — reviewer/approval concentration missing | N/A | Yes (reviewer concentration sub-metric under 5b) | Yes (audit-evaluator-prompt E-3 expansion) | P1-D3, P2-D5 |
| #57 — intermediate CSV input path | Yes (G-FNM-3/4 intermediate CSV as primary input) | N/A | Yes (code-evaluator-prompt CSV input instructions) | P1-D1, P2-D4 |
| #59 — formulation_difference decision procedure | Yes (6-step decision procedure in Suite G notes) | N/A | Yes (code-evaluator-prompt tag application procedure) | P1-D1, P2-D4 |

## API

### Verification functions

These functions are the auditor's toolkit for populating and validating the checklist. Each function reads file content and returns structured verification results.

```python
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(".")
PROTOCOL_PATH = REPO_ROOT / "evaluation_guides" / "Phase1_Test_Protocol.md"
RUBRIC_PATH = REPO_ROOT / "evaluation_guides" / "Phase1_Evaluation_Rubric.md"
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "evaluate-tool"


def load_artifact(path: Path) -> str:
    """Read an artifact file and return its full text.

    Raises FileNotFoundError if the file does not exist.
    """
    return path.read_text(encoding="utf-8")


def verify_issue_43(
    protocol: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #43: MATPOWER format bias in Suite G.

    Checks:
    - Protocol G-FNM-3 description lists intermediate CSVs as primary input.
    - Protocol G-FNM-4 description lists intermediate CSVs as primary input.
    - Protocol Reference Networks table LARGE row mentions intermediate CSV.
    - code-evaluator-prompt.md contains CSV input path instructions for G-FNM-3/4.
    - cross-tool-watchpoints.md contains Suite G format context section.

    Args:
        protocol: Full text of Phase1_Test_Protocol.md.
        skill_files: Dict mapping relative file paths to their content
            for skill files under .claude/skills/evaluate-tool/.

    Returns:
        Populated IssueChecklistRow with fix locations and verification status.
    """
    ...


def verify_issue_48(
    protocol: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #48: formulation_difference tag needed.

    Checks:
    - Protocol contains formulation_difference tag definition in Suite G notes.
    - Protocol contains the 6-step decision procedure.
    - pass_conditions.json contains formulation_difference_max_abs keys.
    - code-evaluator-prompt.md references formulation_difference tag application.
    - cross-tool-watchpoints.md contains formulation sophistication catalog.

    Args:
        protocol: Full text of Phase1_Test_Protocol.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def verify_issue_49(
    protocol: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #49: protocol thinning / agent-facing note duplication.

    Checks:
    - Protocol no longer contains bodies of purely agent-facing notes.
    - Protocol contains forward references to test-methodology-notes.md.
    - Protocol hybrid notes are trimmed to evaluator-facing content only.
    - test-methodology-notes.md exists and contains extracted agent-facing content.
    - test-methodology-notes.md contains at least 6 factored notes.

    Args:
        protocol: Full text of Phase1_Test_Protocol.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def verify_issue_54(
    rubric: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #54: Criterion 5 conflates maturity and sustainability.

    Checks:
    - Rubric contains ### 5a and ### 5b sub-headings within Criterion 5.
    - Rubric contains separate grading standards for 5a and 5b.
    - Rubric contains 3x3 composite grade matrix with correct cell values.
    - audit-evaluator-prompt.md references 5a/5b structure.

    Args:
        rubric: Full text of Phase1_Evaluation_Rubric.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def verify_issue_55(
    protocol: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #55: version-awareness gap.

    Checks:
    - Protocol contains a Version Compatibility section.
    - research-prompt.md contains a version-awareness research agent definition.
    - code-evaluator-prompt.md contains version capability report consumption logic.
    - SKILL.md contains 4th research agent dispatch and version report variable.

    Args:
        protocol: Full text of Phase1_Test_Protocol.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def verify_issue_56(
    rubric: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #56: reviewer/approval concentration missing.

    Checks:
    - Rubric contains reviewer/approval concentration sub-metric under 5b.
    - Rubric specifies sampling last 50 merged PRs.
    - audit-evaluator-prompt.md contains reviewer concentration evaluation
      instructions in E-3.

    Args:
        rubric: Full text of Phase1_Evaluation_Rubric.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def verify_issue_57(
    protocol: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #57: intermediate CSV input path.

    Checks:
    - Protocol G-FNM-3 specifies intermediate CSV as primary input.
    - Protocol G-FNM-4 specifies intermediate CSV as primary input.
    - code-evaluator-prompt.md instructs loading from intermediate CSV path.

    Note: This issue overlaps with #43. The distinction is that #43 addresses
    the format bias (MATPOWER-centric), while #57 addresses the missing CSV
    input path specifically. Both must be independently verified.

    Args:
        protocol: Full text of Phase1_Test_Protocol.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def verify_issue_59(
    protocol: str, skill_files: dict[str, str],
) -> IssueChecklistRow:
    """Verify #59: formulation_difference decision procedure.

    Checks:
    - Protocol contains a numbered decision procedure with exactly 6 steps.
    - Step 3 specifies correlation gate with 0.80 threshold.
    - Step 4 references formulation_difference_max_abs from pass_conditions.json.
    - Step 6 states hard-fail conditions are NOT relaxed.
    - code-evaluator-prompt.md references the decision procedure for tag application.

    Note: This issue overlaps with #48. The distinction is that #48 established
    the need for the tag, while #59 demanded a concrete decision procedure.
    Both must be independently verified.

    Args:
        protocol: Full text of Phase1_Test_Protocol.md.
        skill_files: Dict mapping relative file paths to their content.

    Returns:
        Populated IssueChecklistRow.
    """
    ...


def build_checklist(repo_root: Path = REPO_ROOT) -> CrossReferenceChecklist:
    """Build the complete cross-reference checklist by running all 8 issue verifiers.

    Loads protocol, rubric, and skill files once, then passes them to each
    per-issue verification function. Returns a fully populated checklist.

    Args:
        repo_root: Path to the repository root directory.

    Returns:
        CrossReferenceChecklist with 8 rows, one per issue.
    """
    ...


def render_checklist_markdown(checklist: CrossReferenceChecklist) -> str:
    """Render the checklist as a markdown document suitable for the output artifact.

    Output structure:
    1. Header with audit date and overall pass/fail.
    2. Summary table (one row per issue: number, title, protocol, rubric, skill, status).
    3. Per-issue detail blocks with:
       - Problem description
       - Fix locations with evidence quotes
       - Pass/fail verdict
       - Failure routing (if applicable)

    Args:
        checklist: The populated checklist to render.

    Returns:
        Markdown string for writing to cross-reference-checklist.md.
    """
    ...


def validate_checklist_completeness(
    checklist: CrossReferenceChecklist,
) -> list[str]:
    """Validate that the checklist itself is structurally complete.

    Checks:
    - Exactly 8 rows present.
    - All 8 expected issue numbers are represented (43, 48, 49, 54, 55, 56, 57, 59).
    - Every row has at least one FixLocation with status != NOT_APPLICABLE.
    - Every row with a FAIL status has at least one FixLocation with responsible_prd set.
    - No duplicate issue numbers.
    - Every N/A entry has a non-empty evidence field (the justification).

    Args:
        checklist: The checklist to validate.

    Returns:
        List of validation errors (empty list = structurally complete).
    """
    ...
```

## Success Criteria

Each criterion is a verifiable check on the output checklist artifact. The checks are grouped by the verification dimension they address.

### Completeness — all issues represented (3 checks)

1. **SC-01: Checklist contains exactly 8 rows.**
   - The output markdown contains exactly 8 issue detail blocks, one for each of: #43, #48, #49, #54, #55, #56, #57, #59. No issue is missing and no extra issues are present.

2. **SC-02: Every row has at least one confirmed fix location.**
   - No row consists entirely of N/A entries. Every issue has at least one FixLocation with status `pass` (or `fail` if the fix is missing — the point is that the expected fix location is identified, not that it is N/A across all layers).

3. **SC-03: All three artifact layers are assessed per row.**
   - Every row has at least one FixLocation entry (pass, fail, or N/A) for each of the three layers: protocol, rubric, and skill. No layer is silently omitted from any row.

### N/A justifications (2 checks)

4. **SC-04: N/A entries have justifications.**
   - Every FixLocation with status `n/a` has a non-empty `evidence` field containing a one-sentence justification explaining why this layer does not require changes for this issue.

5. **SC-05: N/A entries match the expected mapping.**
   - The N/A pattern for each issue matches the Issue-to-Layer Mapping table in Data Structures. Specifically: #43, #48, #49, #55, #57, #59 have rubric = N/A; #54 and #56 have protocol = N/A. No issue has skill = N/A (all 8 issues require at least one skill file change).

### Content verification — protocol layer (3 checks)

6. **SC-06: Protocol fix for #43/#57 verified by content.**
   - The checklist row for #43 and #57 cites the G-FNM-3 and G-FNM-4 test descriptions in the protocol and quotes text confirming "intermediate CSV" (or equivalent) appears as the primary input.

7. **SC-07: Protocol fix for #48/#59 verified by content.**
   - The checklist row for #48 cites the `formulation_difference` tag definition section and quotes the tag name. The row for #59 cites the decision procedure section and confirms 6 numbered steps are present, including the 0.80 correlation gate and the `formulation_difference_max_abs` reference.

8. **SC-08: Protocol fix for #49 verified by content.**
   - The checklist row for #49 cites at least one forward reference to `test-methodology-notes.md` in the protocol and confirms that at least one purely agent-facing note body has been removed (by quoting the forward reference line that replaced it).

### Content verification — rubric layer (2 checks)

9. **SC-09: Rubric fix for #54 verified by content.**
   - The checklist row for #54 cites the Criterion 5 section in the rubric and quotes text confirming both `5a` and `5b` sub-headings exist, separate grading standards are present, and the composite grade matrix is present.

10. **SC-10: Rubric fix for #56 verified by content.**
    - The checklist row for #56 cites the 5b sub-section in the rubric and quotes text confirming reviewer/approval concentration is mentioned with the 50-PR sampling protocol.

### Content verification — skill layer (3 checks)

11. **SC-11: Skill fix for #49 verified by content.**
    - The checklist row for #49 cites `references/test-methodology-notes.md` and confirms it exists and contains at least 6 extracted agent-facing notes (by quoting a note heading or count).

12. **SC-12: Skill fix for #55 verified by content.**
    - The checklist row for #55 cites `prompts/research-prompt.md` and confirms it contains a version-awareness agent definition (by quoting the agent name or a distinctive instruction). Additionally cites `SKILL.md` and confirms it contains the version report variable or 4th agent dispatch.

13. **SC-13: Skill fix for #56 verified by content.**
    - The checklist row for #56 cites `prompts/audit-evaluator-prompt.md` and confirms it contains reviewer/approval concentration instructions in the E-3 section (by quoting distinctive text).

### Failure routing (2 checks)

14. **SC-14: Failed rows have responsible PRD identified.**
    - If any row has `overall_status == fail`, at least one of its FixLocation entries has a non-empty `responsible_prd` field identifying the Phase and PRD number responsible for the missing fix (e.g., "Phase 1 PRD-01", "Phase 2 PRD-04").

15. **SC-15: Responsible PRD citations are valid.**
    - Every `responsible_prd` value references a PRD that actually exists in the plan: Phase 1 PRDs 01-03, Phase 2 PRDs 01-06. No references to nonexistent PRDs.

### Structural integrity (1 check)

16. **SC-16: Output artifact is well-formed markdown.**
    - The output `cross-reference-checklist.md` contains: (a) a header with audit date, (b) a summary table with columns for issue number, title, protocol status, rubric status, skill status, and overall status, (c) per-issue detail blocks with problem description, fix locations, evidence, and verdict. The markdown renders without broken table formatting.

17. **SC-17: Protocol thinning line-count verification.**
    - Compare the v8 protocol line count against the v7 baseline. The net reduction should be approximately 50 lines (executive plan Objective 5 targets ~11% reduction). Record the exact delta. A reduction of 30–70 lines passes; outside this range, flag for review with an explanation of what caused the deviation.

## File Location

### Input files (read-only)

| File | Layer | Description |
|------|-------|-------------|
| `evaluation_guides/Phase1_Test_Protocol.md` | Protocol | v8 protocol with all Phase 1 edits applied |
| `evaluation_guides/Phase1_Evaluation_Rubric.md` | Rubric | v6 rubric with Criterion 5 split applied |
| `data/fnm/reference/pass_conditions.json` | Protocol | Pass conditions with formulation_difference_max_abs keys |
| `.claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md` | Skill | Updated code evaluator with CSV path and formulation_difference |
| `.claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md` | Skill | Updated audit evaluator with reviewer concentration |
| `.claude/skills/evaluate-tool/prompts/research-prompt.md` | Skill | Updated research prompt with version-awareness agent |
| `.claude/skills/evaluate-tool/references/test-methodology-notes.md` | Skill | New file with extracted agent-facing notes |
| `.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md` | Skill | Updated watchpoints with Suite G sections |
| `.claude/skills/evaluate-tool/SKILL.md` | Skill | Updated orchestrator with 4th research agent |

### Output file

| File | Description |
|------|-------------|
| `plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/cross-reference-checklist.md` | The verification artifact produced by this deliverable |

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

### Internal Dependencies

- **Phase 1 PRD-01** (Protocol v8 — G-FNM Input Path and Formulation Annotations) — provides protocol fixes for #43, #48, #57, #59.
- **Phase 1 PRD-02** (Protocol v8 — Thinning and Version Compatibility) — provides protocol fixes for #49, #55.
- **Phase 1 PRD-03** (Rubric v6 — Criterion 5 Split and Grade Matrix) — provides rubric fixes for #54, #56.
- **Phase 2 PRD-01** (test-methodology-notes.md) — provides skill fix for #49.
- **Phase 2 PRD-02** (cross-tool-watchpoints.md) — provides skill fixes for #43, #48.
- **Phase 2 PRD-03** (research-prompt.md) — provides skill fix for #55.
- **Phase 2 PRD-04** (code-evaluator-prompt.md) — provides skill fixes for #43, #48, #55, #57, #59.
- **Phase 2 PRD-05** (audit-evaluator-prompt.md) — provides skill fixes for #54, #56.
- **Phase 2 PRD-06** (SKILL.md) — provides skill fix for #55.

All Phase 1 and Phase 2 deliverables must be complete before this checklist can be populated. The checklist reads final artifact state, not intermediate drafts.

### External Dependencies

None. This deliverable uses only files within the repository.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Issue-centric (not file-centric) organization: confirmed.
- Three-layer coverage per row with explicit N/A justifications: confirmed.
- Content-level verification (not git-diff-level): confirmed.
- Phase 3 documents failures but does not fix them: confirmed.
