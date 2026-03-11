# PRD: Updated Prompt — audit-evaluator-prompt.md (Reviewer Concentration in E-3)

## Overview

This deliverable updates `.claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md` to expand the E-3 methodology with reviewer/approval concentration analysis. The current E-3 section ("Contributor concentration") covers only commit-based metrics: top 3 contributors by commits and bus factor assessment. This misses a critical sustainability signal — a project can have many committers but funnel all merge authority through a single gatekeeper. The rubric v6 split of Criterion 5 into 5a (Demonstrated Maturity) and 5b (Sustainability Risk) makes this gap actionable: commit activity contributes to 5a evidence while contributor and reviewer concentration contribute to 5b risk scoring.

The update adds a concrete methodology for sampling the last 50 merged PRs via `gh` CLI, computing reviewer concentration percentages, and flagging single-gatekeeper risk. The finding is reported as a sibling subsection to commit concentration within the same E-3 result file, not as a separate test ID. This keeps the test ID count stable while broadening the evidence gathered per audit.

The deliverable also adds a note clarifying that E-3 now contributes evidence to both sub-criteria (5a and 5b), consistent with the rubric v6 structure established in Phase 1 Deliverable 3.

## Goals

1. Add reviewer/approval concentration methodology to the E-3 section of the audit-evaluator prompt, specifying: sample the last 50 merged PRs via GitHub API or `gh` CLI, record percentage approved by the top reviewer, record percentage approved by the top 3 reviewers, flag if the top reviewer approved >60% of PRs as a concentration risk.
2. Define the expected evidence schema for the "Reviewer Concentration" subsection within E-3 result files — structured data that the synthesis agent can consume for cross-tool comparison.
3. Add a dual-contribution note to E-3 explaining that commit activity evidence feeds 5a (Demonstrated Maturity) while concentration metrics (both commit and reviewer) feed 5b (Sustainability Risk).
4. Preserve the existing E-3 commit concentration methodology unchanged — the reviewer concentration is additive, not a replacement.

## Non-Goals

- **Adding a new test ID.** Reviewer concentration is a sub-metric within E-3, not a new E-N test. The test ID count for Suite E is unchanged.
- **Modifying any section other than E-3.** E-1, E-2, E-4 through E-7, and all non-maturity suite sections are untouched.
- **Modifying the rubric.** The rubric v6 changes (5a/5b split, reviewer concentration sub-metric definition) are handled by Phase 1 Deliverable 3. This deliverable implements the corresponding audit methodology.
- **Modifying the eval-config or config-generator.** The E-3 test ID already exists in the config. The expanded methodology is prompt-level guidance, not config-level.
- **Defining how `gh` CLI authenticates.** The devcontainer environment is already configured for `gh` access. The prompt specifies the tool, not the auth mechanism.
- **Handling repositories without PRs.** Some tools (e.g., those using mailing-list workflows) may not have GitHub PRs. The existing prompt already handles "apply the most appropriate audit method" for edge cases; no special-case logic is added here.

## Data Structures

These types define the reviewer concentration evidence schema that E-3 result files must include in the "Reviewer Concentration" subsection. They are validation types for verifying prompt correctness, not runtime code.

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReviewerConcentrationEvidence:
    """Schema for the reviewer concentration subsection in E-3 result files.

    The audit-evaluator must populate these fields when writing the E-3 result.
    """

    sample_size: int                          # Target: 50 merged PRs
    actual_sample_size: int                   # May be < 50 if repo has fewer merged PRs
    total_merged_prs_available: int           # Total merged PRs in repo (for context)
    top_reviewer_login: str                   # GitHub login of the top reviewer
    top_reviewer_approvals: int               # Number of PRs approved by top reviewer
    top_reviewer_pct: float                   # Percentage approved by top reviewer
    top_3_reviewers: list[ReviewerEntry]      # Top 3 reviewers by approval count
    top_3_pct: float                          # Combined percentage approved by top 3
    concentration_flag: bool                  # True if top_reviewer_pct > 60%
    flag_threshold: float = 60.0             # The threshold used for flagging (%)
    methodology_note: str = ""                # Any caveats (e.g., "bot approvals excluded")


@dataclass(frozen=True)
class ReviewerEntry:
    """A single reviewer's contribution to the sample."""

    login: str           # GitHub login
    approvals: int       # Number of PRs approved in sample
    pct: float           # Percentage of sample approved by this reviewer


@dataclass(frozen=True)
class E3ResultStructure:
    """Expected structure of the full E-3 result file after this update.

    The E-3 result file now has two sibling evidence subsections:
    1. Commit Concentration (existing) — top 3 committers, bus factor
    2. Reviewer Concentration (new) — top reviewers by PR approvals

    Both subsections appear under the Evidence heading.
    """

    # Existing fields (unchanged)
    test_id: str = "E-3"
    dimension: str = "maturity"
    status: str = ""  # pass|fail|qualified_pass|informational

    # Commit concentration (existing, unchanged)
    top_contributor_pct: float = 0.0
    top_3_contributors_pct: float = 0.0
    bus_factor: int = 0

    # Reviewer concentration (new)
    reviewer_concentration: ReviewerConcentrationEvidence | None = None

    # Dual-contribution mapping (new)
    contributes_to_5a: bool = True   # Commit activity → Demonstrated Maturity
    contributes_to_5b: bool = True   # Concentration metrics → Sustainability Risk


@dataclass(frozen=True)
class E3MethodologySection:
    """Describes the expected structure of the E-3 entry in the prompt.

    Used for verifying the prompt edit is structurally complete.
    """

    has_commit_concentration_method: bool     # Original: top 3 by commits, bus factor
    has_reviewer_concentration_method: bool   # New: sample 50 PRs, top reviewer %
    has_dual_contribution_note: bool          # New: E-3 feeds both 5a and 5b
    has_concentration_flag_threshold: bool    # New: >60% = concentration risk
    has_gh_cli_instruction: bool              # New: uses gh pr list or gh api
    sample_size: int = 50                     # Number of merged PRs to sample
    flag_threshold: float = 60.0              # Top reviewer % threshold for flagging
```

## API

Verification functions for confirming the prompt edit is correct. These operate on the prompt markdown text.

```python
from __future__ import annotations

from pathlib import Path


PROMPT_PATH = Path(
    ".claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md"
)


def load_prompt() -> str:
    """Read the audit-evaluator prompt and return its full text."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_e3_section(prompt_text: str) -> str:
    """Extract the E-3 methodology block from the prompt.

    Returns everything from the E-3 heading through the next E-N heading
    or section boundary.
    """
    ...


def verify_commit_concentration_preserved(e3_text: str) -> tuple[bool, str]:
    """Verify the original commit concentration methodology is unchanged.

    Checks for:
    - 'Top 3 contributors by commits' or equivalent phrasing
    - 'bus factor' reference
    - Percentage from top contributor

    Returns (preserved, error_message_if_missing).
    """
    ...


def verify_reviewer_concentration_methodology(
    e3_text: str,
) -> tuple[bool, list[str]]:
    """Verify the reviewer concentration methodology is present and complete.

    Checks for all required elements:
    1. Sample size: 'last 50 merged PRs' or equivalent
    2. Data source: 'gh' CLI or GitHub API reference
    3. Top reviewer metric: percentage approved by top reviewer
    4. Top 3 reviewers metric: percentage approved by top 3 reviewers
    5. Concentration flag: >60% threshold with 'concentration risk' language

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_reviewer_subsection_in_result_template(
    e3_text: str,
) -> tuple[bool, str]:
    """Verify the E-3 result file template includes a Reviewer Concentration subsection.

    The prompt should indicate that the E-3 result file's Evidence section
    contains both 'Commit Concentration' and 'Reviewer Concentration' as
    sibling subsections.

    Returns (present, error_message_if_missing).
    """
    ...


def verify_dual_contribution_note(e3_text: str) -> tuple[bool, str]:
    """Verify the E-3 section notes that it contributes to both 5a and 5b.

    Checks for:
    - Reference to '5a' or 'Demonstrated Maturity'
    - Reference to '5b' or 'Sustainability Risk'
    - Language indicating E-3 contributes evidence to both sub-criteria

    Returns (present, error_message_if_missing).
    """
    ...


def verify_flag_threshold_explicit(e3_text: str) -> tuple[bool, str]:
    """Verify the >60% flag threshold is stated as a concrete number.

    The threshold must be explicit (not vague language like 'high concentration')
    so that different evaluator agents produce consistent flags.

    Returns (explicit, error_message_if_vague).
    """
    ...


def verify_no_new_test_id(prompt_text: str) -> tuple[bool, str]:
    """Verify no new E-N test ID has been added to the maturity section.

    The existing test IDs are E-1 through E-7. The reviewer concentration
    is a sub-metric of E-3, not a new E-8.

    Returns (unchanged, error_message_if_new_id_found).
    """
    ...


def verify_other_sections_unchanged(
    original_text: str,
    updated_text: str,
) -> tuple[bool, list[str]]:
    """Verify no sections other than E-3 were modified.

    Compares the original and updated prompt text and confirms that:
    - All Suite D (Accessibility) entries are identical
    - E-1, E-2, E-4, E-5, E-6, E-7 entries are identical
    - All Suite F (Supply Chain) entries are identical
    - All Suite P2 entries are identical
    - The preamble, inputs, task, and reference sections are identical

    Returns (unchanged, list_of_unexpected_changes).
    """
    ...


def verify_gh_cli_usage(e3_text: str) -> tuple[bool, str]:
    """Verify the methodology specifies gh CLI as the data collection tool.

    The devcontainer has gh pre-configured. The prompt should reference
    gh pr list, gh api, or equivalent gh commands for PR sampling.

    Returns (specified, error_message_if_missing).
    """
    ...
```

## Success Criteria

Each criterion maps to a verification function above. All must pass on the updated `audit-evaluator-prompt.md`.

1. **SC-01: Commit concentration methodology preserved.** `verify_commit_concentration_preserved` confirms the original E-3 methodology (top 3 contributors by commits, percentage from top contributor, bus factor assessment) remains present and unmodified in the E-3 section.

2. **SC-02: Reviewer sample size specified.** `verify_reviewer_concentration_methodology` confirms the E-3 section specifies sampling the "last 50 merged PRs" (or semantic equivalent with explicit count of 50).

3. **SC-03: Data collection tool specified.** `verify_gh_cli_usage` confirms the E-3 section references `gh` CLI or GitHub API as the mechanism for retrieving merged PR data. The evaluator agent must know which tool to use inside the devcontainer.

4. **SC-04: Top reviewer percentage metric.** `verify_reviewer_concentration_methodology` confirms the E-3 section instructs the auditor to record the percentage of sampled PRs approved by the top reviewer.

5. **SC-05: Top 3 reviewers percentage metric.** `verify_reviewer_concentration_methodology` confirms the E-3 section instructs the auditor to record the percentage of sampled PRs approved by the top 3 reviewers.

6. **SC-06: Concentration risk flag with explicit threshold.** `verify_flag_threshold_explicit` confirms the E-3 section specifies that a top reviewer approving >60% of PRs is flagged as a "concentration risk." The threshold must be a concrete number (60%), not vague language.

7. **SC-07: Reviewer Concentration as sibling subsection in result file.** `verify_reviewer_subsection_in_result_template` confirms the E-3 methodology indicates that the result file's Evidence section contains both a "Commit Concentration" and a "Reviewer Concentration" subsection (or equivalent sibling structure), not a replacement of one by the other.

8. **SC-08: Dual-contribution note present.** `verify_dual_contribution_note` confirms the E-3 section contains a note stating that E-3 contributes evidence to both 5a (Demonstrated Maturity) and 5b (Sustainability Risk), consistent with the rubric v6 5a/5b split.

9. **SC-09: No new test ID introduced.** `verify_no_new_test_id` confirms that the maturity section still contains exactly test IDs E-1 through E-7. No E-8 or other new ID has been added. Reviewer concentration remains a sub-metric within E-3.

10. **SC-10: Other sections unchanged.** `verify_other_sections_unchanged` confirms that all sections outside of E-3 — including Suite D (Accessibility), E-1, E-2, E-4 through E-7, Suite F (Supply Chain), Suite P2, and all framing sections (preamble, inputs, task, reference files, consumed observations, cross-referencing, supply chain gate semantics) — are identical between the original and updated prompt.

11. **SC-11: E-3 heading text updated.** The E-3 heading or description in the maturity section reflects the expanded scope (e.g., "Contributor & reviewer concentration" rather than just "Contributor concentration") so the auditor knows at a glance that reviewer analysis is expected.

12. **SC-12: Bot exclusion guidance.** The reviewer concentration methodology includes a note to exclude or annotate bot accounts (e.g., dependabot, renovate) when computing reviewer percentages, since bot approvals do not represent human gate-keeping.

## File Location

The single file modified by this deliverable:

```
.claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md
```

No new files are created. No files are deleted.

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

- **No dependencies on other Phase 2 deliverables.** The audit-evaluator prompt changes are self-contained. They do not reference the version capability report (Deliverable 3), the code-evaluator changes (Deliverable 4), or the SKILL.md orchestrator changes (Deliverable 6).
- **Depends on:** The rubric v6 5a/5b split (Phase 1 Deliverable 3) as the authoritative definition of what E-3 evidence feeds into. The prompt implements methodology for evidence gathering; the rubric defines how that evidence is graded.
- **Enables:** Phase 3 validation, which checks that the audit-evaluator prompt's E-3 methodology is consistent with the rubric v6 definition of Criterion 5b's reviewer concentration sub-metric.

## Open Questions

None. All design decisions were resolved in the phase plan:

- The sample size (50 merged PRs) is specified.
- The flag threshold (>60% by top reviewer) is specified.
- The reporting structure (sibling subsection within E-3 result file) is specified.
- The dual-contribution mapping (E-3 feeds both 5a and 5b) is specified.
- The data collection tool (`gh` CLI) is specified by the devcontainer environment.
