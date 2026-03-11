# PRD: Rubric v6 — Criterion 5 Split (5a/5b) and Grade Matrix

## Overview

This deliverable restructures Criterion 5 ("Maturity & Sustainability") in `evaluation_guides/Phase1_Evaluation_Rubric.md` from a single undifferentiated section into two internal sub-criteria: **5a (Demonstrated Maturity)** and **5b (Sustainability Risk)**. The split separates backward-looking evidence of engineering health from forward-looking risk indicators, enabling the evaluator to independently assess each dimension and combine them via a defined composite grade matrix. The criterion count remains at 6 — the 5a/5b split is internal to Criterion 5 and does not alter the rubric's top-level structure or weighting.

The current rubric (v5) treats all seven sub-questions (E-1 through E-7) as a flat list under a single set of grading standards. This conflates two distinct concerns: whether a project *has been* well-engineered (release discipline, CI, test coverage, issue responsiveness, operational adoption) versus whether a project *will continue to be* maintained (contributor concentration, funding stability, governance model). A project can score well on maturity evidence while carrying significant sustainability risk (e.g., excellent CI and operational adoption but bus factor of one), or vice versa. The flat structure forces evaluators to perform an implicit mental weighting that is neither documented nor reproducible.

The deliverable also adds a new sub-metric under 5b: **reviewer/approval concentration**, which measures whether merge authority is concentrated in a single person by sampling the last 50 merged PRs. This addresses a blind spot where a project may appear to have multiple contributors but all merge decisions flow through a single gatekeeper.

## Goals

1. Split the Criterion 5 section into two labeled sub-sections (5a: Demonstrated Maturity, 5b: Sustainability Risk) while keeping the outer Criterion 5 heading and numbering intact.
2. Reassign sub-questions E-1 through E-7 to the appropriate sub-criterion based on temporal orientation (backward-looking evidence vs. forward-looking risk).
3. Add reviewer/approval concentration as a new sub-metric under 5b E-1 (contributor concentration), with explicit measurement protocol: sample last 50 merged PRs, record percentage approved by the top reviewer.
4. Define separate grading standards (A/B/C bands) for 5a and 5b independently.
5. Add the 3x3 composite grade matrix that maps {5a grade band, 5b grade band} to a Criterion 5 composite grade, with two-grade ranges per cell and boundary-proximity selection guidance.
6. Update the Quick Reference table to reflect the 5a/5b internal split without adding a new row (Criterion 5 stays as one row).
7. Update the Overview weighted criteria list item for Criterion 5 to reference the internal split.
8. Add a v6 entry to the Revision History table.

## Non-Goals

- **Changing the criterion count.** The rubric stays at 6 criteria. The 5a/5b split is internal — it does not create a new top-level criterion or change the priority ordering.
- **Changing the grading scale.** The 9-point scale (A through C-) is unchanged.
- **Modifying any other criterion.** Criteria 1-4 and 6 are untouched by this deliverable.
- **Modifying the evaluation protocol.** This deliverable edits the rubric only. Protocol v8 changes are handled by PRDs 01 and 02.
- **Defining how to run the evaluation.** The rubric defines *what* to evaluate and *how to grade*; the protocol defines *how to run* the evaluation.
- **Automating the Criterion 5 evaluation.** This is a document edit, not a software feature.
- **Changing grade weights or tie-breaking rules.** The priority ordering (Criterion 5 is priority 5) is unchanged.

## Data Structures

Since this deliverable edits a markdown document, the data structures below define validation types for verifying the rubric edits are structurally correct and complete.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SubCriterion(StrEnum):
    """The two internal sub-criteria within Criterion 5."""

    DEMONSTRATED_MATURITY = "5a"
    SUSTAINABILITY_RISK = "5b"


class GradeBand(StrEnum):
    """Grade bands used in the composite matrix axes."""

    A_RANGE = "A"   # A, A-
    B_RANGE = "B"   # B+, B, B-
    C_RANGE = "C"   # C+, C, C-


VALID_GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-"]


@dataclass(frozen=True)
class SubQuestionAssignment:
    """Maps an original sub-question number to its new sub-criterion."""

    original_number: int           # 1-7 (original E-N numbering)
    sub_criterion: SubCriterion
    new_label: str                 # e.g. "5a E-1", "5b E-2"
    title: str                     # sub-question title
    has_measurement_protocol: bool # True if specific sampling/counting protocol defined


# Canonical sub-question assignments per the phase plan
SUBQUESTION_ASSIGNMENTS: list[SubQuestionAssignment] = [
    SubQuestionAssignment(1, SubCriterion.DEMONSTRATED_MATURITY, "5a E-1",
                          "Release engineering discipline", False),
    SubQuestionAssignment(2, SubCriterion.DEMONSTRATED_MATURITY, "5a E-2",
                          "Test coverage and CI health", False),
    SubQuestionAssignment(3, SubCriterion.DEMONSTRATED_MATURITY, "5a E-3",
                          "Issue responsiveness", True),   # sample last 20+10
    SubQuestionAssignment(6, SubCriterion.DEMONSTRATED_MATURITY, "5a E-4",
                          "Operational adoption", False),
    SubQuestionAssignment(4, SubCriterion.SUSTAINABILITY_RISK, "5b E-1",
                          "Contributor concentration and bus factor", True),  # commit %
    SubQuestionAssignment(5, SubCriterion.SUSTAINABILITY_RISK, "5b E-2",
                          "Funding stability", False),
    SubQuestionAssignment(7, SubCriterion.SUSTAINABILITY_RISK, "5b E-3",
                          "Governance model", False),
]


@dataclass(frozen=True)
class ReviewerConcentrationMetric:
    """New sub-metric added under 5b E-1 (or as 5b E-4)."""

    sample_size: int = 50          # last N merged PRs to sample
    metric: str = "pct_approved_by_top_reviewer"
    description: str = (
        "Sample last 50 merged PRs, record percentage approved by the "
        "top reviewer. High concentration (>80%) indicates single-gatekeeper risk."
    )


@dataclass(frozen=True)
class CompositeGradeCell:
    """One cell of the 3x3 composite grade matrix."""

    row_band: GradeBand     # 5a grade band
    col_band: GradeBand     # 5b grade band
    grade_range: tuple[str, str]  # two-grade range, evaluator picks based on proximity


# Canonical composite grade matrix from the phase plan
COMPOSITE_MATRIX: list[CompositeGradeCell] = [
    CompositeGradeCell(GradeBand.A_RANGE, GradeBand.A_RANGE, ("A",  "A-")),
    CompositeGradeCell(GradeBand.A_RANGE, GradeBand.B_RANGE, ("B+", "B")),
    CompositeGradeCell(GradeBand.A_RANGE, GradeBand.C_RANGE, ("B",  "B-")),
    CompositeGradeCell(GradeBand.B_RANGE, GradeBand.A_RANGE, ("B+", "B")),
    CompositeGradeCell(GradeBand.B_RANGE, GradeBand.B_RANGE, ("B",  "B-")),
    CompositeGradeCell(GradeBand.B_RANGE, GradeBand.C_RANGE, ("C+", "C")),
    CompositeGradeCell(GradeBand.C_RANGE, GradeBand.A_RANGE, ("B-", "C+")),
    CompositeGradeCell(GradeBand.C_RANGE, GradeBand.B_RANGE, ("C+", "C")),
    CompositeGradeCell(GradeBand.C_RANGE, GradeBand.C_RANGE, ("C",  "C-")),
]


@dataclass(frozen=True)
class GradingStandard:
    """A single row in a sub-criterion's grading standards table."""

    grade_band: GradeBand
    description: str


@dataclass(frozen=True)
class SubCriterionSection:
    """Expected structure of a sub-criterion section in the rubric."""

    label: SubCriterion
    title: str
    orientation: str   # "backward-looking" or "forward-looking"
    sub_questions: list[SubQuestionAssignment]
    grading_standards: list[GradingStandard]  # exactly 3: A, B, C bands
```

## API

Validation functions for verifying the rubric edits. These are structural checks on the markdown content, not runtime APIs.

```python
from __future__ import annotations

import re
from pathlib import Path


RUBRIC_PATH = Path("evaluation_guides/Phase1_Evaluation_Rubric.md")


def load_rubric() -> str:
    """Read the rubric markdown file and return its full text."""
    return RUBRIC_PATH.read_text(encoding="utf-8")


def extract_criterion5_section(rubric_text: str) -> str:
    """Extract the full Criterion 5 section from the rubric.

    Returns everything between '## Criterion 5' and the next '## Criterion 6'
    heading.
    """
    pattern = r"(## Criterion 5.*?)(?=## Criterion 6)"
    match = re.search(pattern, rubric_text, re.DOTALL)
    if not match:
        raise ValueError("Criterion 5 section not found in rubric")
    return match.group(1)


def verify_sub_criterion_headings(criterion5_text: str) -> tuple[bool, list[str]]:
    """Verify that 5a and 5b sub-section headings exist within Criterion 5.

    Returns (all_present, list_of_missing_headings).
    Expected headings at ### level:
      - '### 5a — Demonstrated Maturity'
      - '### 5b — Sustainability Risk'
    """
    ...


def verify_subquestion_assignments(criterion5_text: str) -> tuple[bool, list[str]]:
    """Verify each sub-question appears under the correct sub-criterion.

    Checks that:
    - 5a contains: release engineering discipline, test coverage/CI health,
      issue responsiveness, operational adoption
    - 5b contains: contributor concentration/bus factor, funding stability,
      governance model
    - No sub-question appears under the wrong sub-criterion
    - No original sub-question is missing

    Returns (all_correct, list_of_errors).
    """
    ...


def verify_reviewer_concentration_metric(criterion5_text: str) -> tuple[bool, str]:
    """Verify the reviewer/approval concentration sub-metric exists under 5b.

    Checks for:
    - Reference to sampling last 50 merged PRs
    - Reference to percentage approved by top reviewer
    - Placement under 5b (not 5a)

    Returns (present, error_message_if_missing).
    """
    ...


def verify_separate_grading_standards(
    criterion5_text: str,
) -> tuple[bool, list[str]]:
    """Verify that 5a and 5b each have their own grading standards table.

    Checks:
    - Two separate grading standards tables exist (not one combined table)
    - Each table has exactly 3 rows: A, B, C grade bands
    - The old single grading standards table has been removed

    Returns (valid, list_of_errors).
    """
    ...


def verify_composite_grade_matrix(criterion5_text: str) -> tuple[bool, list[str]]:
    """Verify the 3x3 composite grade matrix is present and correct.

    Checks:
    - A markdown table with 4 columns (row header + 3 5b bands) exists
    - 3 data rows (one per 5a band)
    - All 9 cells contain the expected two-grade ranges:
      (A,A)->A/A-, (A,B)->B+/B, (A,C)->B/B-, (B,A)->B+/B, (B,B)->B/B-,
      (B,C)->C+/C, (C,A)->B-/C+, (C,B)->C+/C, (C,C)->C/C-
    - Boundary-proximity selection guidance is present

    Returns (valid, list_of_errors).
    """
    ...


def verify_composite_matrix_monotonicity(
    matrix: list[CompositeGradeCell],
) -> tuple[bool, list[str]]:
    """Verify the composite matrix has monotonic grade degradation.

    Moving from A->B->C on either axis should never produce a higher
    composite grade. Checks that:
    - For fixed 5a band, moving 5b from A->B->C yields non-increasing grades
    - For fixed 5b band, moving 5a from A->B->C yields non-increasing grades

    Returns (valid, list_of_violations).
    """
    ...


def verify_quick_reference_table(rubric_text: str) -> tuple[bool, str]:
    """Verify the Quick Reference table mentions the 5a/5b internal split.

    Checks:
    - Criterion 5 row still exists (not split into two rows)
    - Row references the internal 5a/5b structure or sub-criteria
    - Criterion count in table is still 6

    Returns (valid, error_message_if_wrong).
    """
    ...


def verify_overview_weighted_list(rubric_text: str) -> tuple[bool, str]:
    """Verify the Overview weighted criteria list references the 5a/5b split.

    Checks:
    - Item 5 in the weighted criteria list still exists
    - It references the internal split (5a/5b, Demonstrated Maturity,
      Sustainability Risk, or similar language)
    - The list still has exactly 5 items (no new top-level criterion added)

    Returns (valid, error_message_if_wrong).
    """
    ...


def verify_revision_history(rubric_text: str) -> tuple[bool, str]:
    """Verify a v6 entry exists in the Revision History table.

    Checks:
    - A row with version 'v6' exists
    - The change description references Criterion 5 split, 5a/5b,
      composite grade matrix, or similar language
    - The date field is populated

    Returns (valid, error_message_if_missing).
    """
    ...


def verify_no_orphaned_grading_standards(criterion5_text: str) -> tuple[bool, str]:
    """Verify the old single grading standards table has been removed.

    The original Criterion 5 had one '### Grading Standards' section with
    a single A/B/C table. After the split, that table must not remain —
    it should be replaced by the two sub-criterion grading tables.

    Returns (valid, error_message_if_orphan_found).
    """
    ...


def verify_all_grades_valid(criterion5_text: str) -> tuple[bool, list[str]]:
    """Verify all grade references in the section use valid 9-point scale grades.

    Scans for grade-like tokens (A, A-, B+, B, B-, C+, C, C-) and flags
    any that fall outside the valid set.

    Returns (valid, list_of_invalid_references).
    """
    ...
```

## Success Criteria

Each criterion maps to a verification function above. All must pass on the updated `Phase1_Evaluation_Rubric.md`.

1. **SC-01: Sub-criterion headings exist.** `verify_sub_criterion_headings` finds both `### 5a — Demonstrated Maturity` and `### 5b — Sustainability Risk` headings within the Criterion 5 section.

2. **SC-02: Sub-question assignment correctness.** `verify_subquestion_assignments` confirms that 5a contains release engineering discipline (E-1), test coverage/CI health (E-2), issue responsiveness (E-3), and operational adoption (E-4); and 5b contains contributor concentration/bus factor (E-1), funding stability (E-2), and governance model (E-3). No sub-question is missing or misassigned.

3. **SC-03: Reviewer concentration metric present.** `verify_reviewer_concentration_metric` finds the reviewer/approval concentration sub-metric under 5b with explicit protocol: "sample last 50 merged PRs, record percentage approved by top reviewer."

4. **SC-04: Separate grading standards for 5a and 5b.** `verify_separate_grading_standards` finds two distinct grading standards tables, each with A/B/C band rows. The 5a standards describe backward-looking evidence (release discipline, CI, test coverage, issue responsiveness, operational adoption). The 5b standards describe forward-looking risk (contributor concentration, funding, governance, reviewer concentration).

5. **SC-05: Old grading standards removed.** `verify_no_orphaned_grading_standards` confirms the original single Criterion 5 grading standards table no longer exists. There is no "### Grading Standards" heading directly under "## Criterion 5" — only under the 5a and 5b sub-sections.

6. **SC-06: Composite grade matrix present and correct.** `verify_composite_grade_matrix` finds the 3x3 markdown table with all 9 cells matching the specified grade ranges: (A,A)=A/A-, (A,B)=B+/B, (A,C)=B/B-, (B,A)=B+/B, (B,B)=B/B-, (B,C)=C+/C, (C,A)=B-/C+, (C,B)=C+/C, (C,C)=C/C-.

7. **SC-07: Composite matrix monotonicity.** `verify_composite_matrix_monotonicity` confirms that moving from A to C on either axis never produces a higher composite grade. The matrix degrades monotonically along both dimensions.

8. **SC-08: Boundary-proximity guidance present.** The composite grade matrix section contains explicit text instructing the evaluator to select from the two-grade range based on boundary proximity (i.e., how close the sub-criterion score is to the adjacent grade band).

9. **SC-09: Quick Reference table updated.** `verify_quick_reference_table` confirms Criterion 5 remains a single row in the Quick Reference table (not split into two rows) and the row text references the 5a/5b internal structure. The table still has exactly 6 criterion rows.

10. **SC-10: Overview weighted list updated.** `verify_overview_weighted_list` confirms item 5 in the weighted criteria list references the internal split. The list still has exactly 5 items.

11. **SC-11: Revision History v6 entry.** `verify_revision_history` finds a v6 row in the Revision History table with a change description referencing the Criterion 5 split and composite grade matrix.

12. **SC-12: All grades valid.** `verify_all_grades_valid` confirms every grade reference in the Criterion 5 section uses a valid grade from the 9-point scale.

13. **SC-13: Criterion count unchanged.** The rubric contains exactly 6 `## Criterion N` headings (numbered 1 through 6). No new top-level criterion heading has been added.

14. **SC-14: Core question preserved.** The Criterion 5 core question ("Is this tool going to be here in three years...") and its explanatory paragraph remain present at the top of the Criterion 5 section, before the 5a/5b sub-sections.

## File Location

The single file modified by this deliverable:

```
evaluation_guides/Phase1_Evaluation_Rubric.md
```

No new files are created. No files are deleted.

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

- **No dependencies on other Phase 1 deliverables.** PRDs 01 and 02 edit the evaluation protocol; this PRD edits the rubric. The files do not overlap and the changes are structurally independent.
- **Depends on:** The current rubric v5 (`evaluation_guides/Phase1_Evaluation_Rubric.md`) as the base document to modify.
- **Enables:** Phase 2 deliverables that implement Criterion 5 evaluation using the 5a/5b structure and composite grade matrix.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Sub-question assignments (which go to 5a vs. 5b) are specified.
- The composite grade matrix values are fully defined.
- The reviewer concentration measurement protocol (50 PRs, % by top reviewer) is specified.
- Boundary-proximity selection within two-grade cells is the documented tiebreaker.
