# PRD: Updated Reference — cross-tool-watchpoints.md

## Overview

This deliverable adds 5 new sections to the existing
`.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md` file. The new
sections encode domain knowledge discovered during prior evaluation rounds and Phase 0
CSV materialization work that evaluator agents need to avoid false failures, misdiagnose
formulation differences as bugs, or miss silent solver pitfalls.

The existing watchpoints file has 11 sections covering solver compatibility, timing
methodology, per-tool pitfalls, resource classification, PTDF phase-shifter corrections,
ACTIVSg10k congestion, SCUC cycling, convergence verification, measured vs estimated
timing, and unit consistency. The 5 new sections extend coverage to Suite G (FNM
ingestion) context, formulation-level differences between tools, post-ingestion
verification, baseMVA/Q-limit failure modes, and a PowerModels-specific silent failure.

Unlike the code-evaluator prompt (which contains actionable step-by-step procedures),
watchpoints provide factual background context. The formulation sophistication catalog,
for example, explains *why* DCPF deviations arise between tools, while the decision
procedure for tagging those deviations as `formulation_difference` lives in the
code-evaluator prompt (Phase 2 Deliverable 4). This PRD produces the background; PRD-04
produces the procedure that references it.

## Goals

1. **Add a Suite G Format Context section** that explains the intermediate CSV format
   structure — the 17-table layout, the `manifest.json` sidecar carrying baseMVA, the
   explicit separation of `branch.csv` (lines) from `transformer.csv` (transformers),
   and why the CSV path is preferred over the MATPOWER `.m` fallback for G-FNM tests.

2. **Add a Formulation Sophistication Catalog section** that documents which tools use
   simplified vs. full B-matrix construction for DCPF, how transformer tap ratios and
   phase-shifter angles produce systematic deviations, and expected deviation magnitudes
   so evaluators can distinguish formulation differences from bugs.

3. **Add a Post-Ingestion Fidelity Checks section** that lists the concrete verification
   steps an evaluator should perform after any tool ingests the intermediate CSVs —
   bus count, branch count, transformer count, baseMVA, slack bus identification, and
   tap ratio preservation.

4. **Add a baseMVA and Q-Limit Pitfalls section** that documents the baseMVA unit
   convention in the intermediate CSVs (always 100 MVA), how tools that assume a
   different base or misinterpret per-unit vs. physical units produce 100x errors, and
   how Q-limit representation in the generator table can cause false ACPF convergence
   failures.

5. **Add a PowerModels solve_dc_pf Pitfall section** that documents the risk of
   `solve_dc_pf` silently returning a trivial (all-zero) solution when the problem
   is infeasible or the solver exits early, and the validation checks that detect this.

## Non-Goals

- **Writing the `formulation_difference` decision procedure** — that is a step-by-step
  evaluator workflow and belongs in the code-evaluator prompt (PRD-04). This deliverable
  provides the background catalog that the procedure references.
- **Modifying existing watchpoints sections** — the 11 existing sections are unchanged.
  If an existing section needs updating (e.g., adding a tool to the Known Pitfalls list),
  that is a separate concern.
- **Defining JSON Schema for intermediate CSVs** — already defined in
  `data/fnm/intermediate/schemas/`. The Suite G Format Context section describes the
  format but does not redefine it.
- **Modifying the export pipeline or materialized CSVs** — those are Phase 0 artifacts.
- **Adding test-methodology notes** — those go in `test-methodology-notes.md` (PRD-01).

## Data Structures

The new sections are markdown content appended to an existing reference file. There are
no code artifacts, but each section follows a defined schema to ensure consistent
structure and completeness.

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WatchpointSection:
    """Schema for a single watchpoints section."""

    heading: str
    """The H2 heading text (e.g., 'Suite G Format Context')."""

    preamble: str
    """1-3 sentence introductory paragraph explaining the section's purpose."""

    body_elements: list[str]
    """Types of body content present. Valid values:
    'prose' — explanatory paragraphs
    'bullet_list' — bulleted list of items
    'table' — markdown table
    'code_block' — inline code or code block
    'when_evaluating' — a 'When evaluating ...:' guidance block (consistent
        with existing watchpoints style)
    """

    references_test_ids: list[str]
    """Protocol test IDs this section is relevant to (e.g., ['G-FNM-1', 'G-FNM-3'])."""


@dataclass(frozen=True)
class SuiteGFormatContextSection(WatchpointSection):
    """Schema for the Suite G Format Context section."""

    heading: str = "Suite G Format Context"

    describes_csv_table_count: bool = True
    """Must state that the intermediate format has 17 CSV tables."""

    describes_manifest_sidecar: bool = True
    """Must explain that manifest.json carries baseMVA and record counts."""

    describes_branch_transformer_split: bool = True
    """Must explain the branch.csv vs transformer.csv distinction."""

    describes_csv_preference_rationale: bool = True
    """Must explain why CSVs are preferred over MATPOWER .m for G-FNM tests."""

    references_test_ids: list[str] = field(
        default_factory=lambda: ["G-FNM-1", "G-FNM-2", "G-FNM-3", "G-FNM-4", "G-FNM-5"]
    )


@dataclass(frozen=True)
class FormulationSophisticationSection(WatchpointSection):
    """Schema for the Formulation Sophistication Catalog section."""

    heading: str = "Formulation Sophistication Catalog"

    documents_simplified_b_matrix: bool = True
    """Must describe simplified B-matrix construction (ignoring taps/shifts)."""

    documents_full_b_matrix: bool = True
    """Must describe full B-matrix construction (incorporating taps/shifts)."""

    lists_tools_by_formulation: bool = True
    """Must indicate which evaluated tools use which formulation approach."""

    states_expected_deviation_magnitudes: bool = True
    """Must provide expected deviation magnitudes (e.g., 'up to X MW on branches
    with tap ratios != 1.0')."""

    explains_systematic_vs_scattered: bool = True
    """Must explain the distinction between systematic deviations (correlated with
    transformer branches) and scattered deviations (indicative of bugs)."""

    references_test_ids: list[str] = field(
        default_factory=lambda: ["G-FNM-3", "G-FNM-4"]
    )


@dataclass(frozen=True)
class PostIngestionFidelitySection(WatchpointSection):
    """Schema for the Post-Ingestion Fidelity Checks section."""

    heading: str = "Post-Ingestion Fidelity Checks"

    check_bus_count: bool = True
    """Must list bus count verification against manifest."""

    check_branch_count: bool = True
    """Must list branch (line) count verification."""

    check_transformer_count: bool = True
    """Must list transformer count verification."""

    check_basemva: bool = True
    """Must list baseMVA value verification."""

    check_slack_bus: bool = True
    """Must list slack bus identification verification."""

    check_tap_ratio_preservation: bool = True
    """Must list tap ratio preservation verification (tap=0 converted to 1.0)."""

    references_test_ids: list[str] = field(
        default_factory=lambda: ["G-FNM-1"]
    )


@dataclass(frozen=True)
class BaseMVAQLimitPitfallsSection(WatchpointSection):
    """Schema for the baseMVA and Q-Limit Pitfalls section."""

    heading: str = "baseMVA and Q-Limit Pitfalls"

    documents_basemva_convention: bool = True
    """Must state that intermediate CSVs use baseMVA = 100 MVA."""

    documents_unit_mismatch_symptom: bool = True
    """Must describe the 100x error symptom from MW vs per-unit confusion."""

    documents_q_limit_representation: bool = True
    """Must explain Q-limit encoding in the generator table."""

    documents_false_acpf_failure: bool = True
    """Must explain how Q-limit misinterpretation causes false ACPF failures."""

    references_test_ids: list[str] = field(
        default_factory=lambda: ["G-FNM-1", "G-FNM-4"]
    )


@dataclass(frozen=True)
class PowerModelsSolveDcPfPitfallSection(WatchpointSection):
    """Schema for the PowerModels solve_dc_pf Pitfall section."""

    heading: str = "PowerModels solve_dc_pf Pitfall"

    documents_trivial_solution_risk: bool = True
    """Must explain that solve_dc_pf can return all-zero angles/flows."""

    documents_conditions_triggering: bool = True
    """Must describe conditions under which the trivial solution occurs."""

    documents_validation_checks: bool = True
    """Must list the checks that detect a trivial solution (e.g., check that
    at least some bus voltage angles are nonzero, check that branch flows
    are nonzero for loaded branches)."""

    references_test_ids: list[str] = field(
        default_factory=lambda: ["G-FNM-3"]
    )
```

## API

No code API — this deliverable produces only markdown content. The "interface" is the
section heading anchors that other files reference:

```
cross-tool-watchpoints.md#suite-g-format-context
cross-tool-watchpoints.md#formulation-sophistication-catalog
cross-tool-watchpoints.md#post-ingestion-fidelity-checks
cross-tool-watchpoints.md#basemva-and-q-limit-pitfalls
cross-tool-watchpoints.md#powermodels-solve_dc_pf-pitfall
```

These anchors are consumed by:
- `code-evaluator-prompt.md` (PRD-04) — references the formulation sophistication
  catalog when describing the `formulation_difference` tag procedure
- `test-methodology-notes.md` (PRD-01) — may cross-reference watchpoints for
  background context on G-FNM methodology notes

## Success Criteria

### Structure and Placement Tests

1. **`test_file_unchanged_above_new_sections`** — The 11 existing sections of
   `cross-tool-watchpoints.md` (from "Solver Compatibility Matrix" through
   "Unit Consistency (MW vs Per-Unit)") are byte-identical to their pre-edit state.
   No existing content is modified, reordered, or deleted.

2. **`test_five_new_h2_sections_present`** — The file contains exactly 5 new H2
   (`##`) headings after the existing content: "Suite G Format Context",
   "Formulation Sophistication Catalog", "Post-Ingestion Fidelity Checks",
   "baseMVA and Q-Limit Pitfalls", and "PowerModels solve_dc_pf Pitfall".

3. **`test_section_order`** — The 5 new sections appear in the order listed above,
   after all 11 existing sections. The ordering groups Suite G context first, then
   formulation background, then verification guidance, then pitfall documentation.

4. **`test_no_duplicate_headings`** — No H2 heading in the file appears more than
   once. The file's total H2 count is exactly 16 (11 existing + 5 new).

### Suite G Format Context Tests

5. **`test_suite_g_mentions_17_csv_tables`** — The "Suite G Format Context" section
   states that the intermediate format consists of 17 CSV tables.

6. **`test_suite_g_describes_manifest_sidecar`** — The section explains that
   `manifest.json` is a sidecar file carrying `baseMVA` (or `sbase`) and per-table
   record counts.

7. **`test_suite_g_describes_branch_transformer_split`** — The section explains that
   transmission lines and transformers are stored in separate files (`branch.csv` and
   `transformer.csv`) rather than a single combined table.

8. **`test_suite_g_states_csv_preference`** — The section states that the CSV path
   is preferred over the MATPOWER `.m` fallback for G-FNM tests, with a rationale
   (format neutrality, explicit transformer separation, or similar).

### Formulation Sophistication Catalog Tests

9. **`test_formulation_describes_simplified_vs_full`** — The "Formulation
   Sophistication Catalog" section describes both simplified B-matrix construction
   (ignoring or approximating tap ratios and phase-shifter angles) and full B-matrix
   construction (incorporating them), with enough detail for an evaluator to understand
   why DCPF results differ between tools.

10. **`test_formulation_lists_tools`** — The section identifies which of the 6
    evaluated tools (PyPSA, pandapower, GridCal, PowerModels, PowerSimulations,
    MATPOWER) are known to use simplified vs. full B-matrix approaches, or explicitly
    states where the formulation is version-dependent or configurable.

11. **`test_formulation_states_deviation_magnitudes`** — The section provides
    expected deviation magnitudes, either as absolute MW ranges or as a qualitative
    scale (e.g., "deviations concentrated on branches with tap != 1.0, typically
    <X MW on the FNM network").

12. **`test_formulation_distinguishes_systematic_vs_scattered`** — The section
    explains that systematic deviations (correlated with transformer/phase-shifter
    branches) indicate formulation differences, while scattered deviations across
    all branch types indicate bugs or data ingestion errors.

### Post-Ingestion Fidelity Checks Tests

13. **`test_fidelity_lists_six_checks`** — The "Post-Ingestion Fidelity Checks"
    section lists at least the following 6 verification items: bus count, branch
    (line) count, transformer count, baseMVA value, slack bus identification, and
    tap ratio preservation (tap=0 pre-converted to 1.0).

14. **`test_fidelity_references_manifest`** — The section states that expected counts
    should be compared against the values in `manifest.json` (the sidecar file
    produced by the export pipeline).

### baseMVA and Q-Limit Pitfalls Tests

15. **`test_basemva_states_convention`** — The "baseMVA and Q-Limit Pitfalls" section
    states that the intermediate CSVs use a baseMVA of 100 MVA.

16. **`test_basemva_describes_unit_mismatch`** — The section describes the symptom
    of MW vs. per-unit confusion (errors on the order of 100x) and identifies this
    as a common source of apparent solver failures that are actually unit-labeling
    errors.

17. **`test_q_limit_documents_false_acpf_failure`** — The section explains how
    Q-limit values in the generator table can cause false ACPF convergence failures
    if misinterpreted (e.g., zero Q-limits treated as "no reactive capability"
    vs. "unlimited"), and identifies this as a source of false negatives in G-FNM-4.

### PowerModels solve_dc_pf Pitfall Tests

18. **`test_powermodels_documents_trivial_solution`** — The "PowerModels solve_dc_pf
    Pitfall" section documents that `solve_dc_pf` can silently return a trivial
    solution (all-zero or near-zero bus voltage angles and branch flows) and lists
    at least one concrete validation check to detect this (e.g., verify that bus
    voltage angles are not uniformly zero, or verify that branch flows are nonzero
    for branches connecting loaded buses).

## File Location

Modified file:

```
.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md
```

No new files are created. The 5 new sections are appended after the existing
"Unit Consistency (MW vs Per-Unit)" section.

## Repository

`grc-tech-evaluation`

## Dependencies

### Internal Dependencies

- **Existing `cross-tool-watchpoints.md`** — The file being extended. The 11 existing
  sections must not be modified.
- **`data/fnm/intermediate/schemas/*.schema.json`** — Define the intermediate CSV
  column schemas. The Suite G Format Context section describes the format these schemas
  define but does not reproduce them.
- **`data/fnm/docs/intermediate-schema.md`** — Documents the intermediate format design
  decisions. The new sections are consistent with this document but do not duplicate it;
  watchpoints focus on evaluator-facing guidance, not format specification.
- **Phase 0 deliverables (materialized CSVs, manifest.json)** — The new sections
  reference the existence and structure of these artifacts. The sections are factually
  correct regardless of whether Phase 0 has executed, because they describe the format
  design rather than specific file contents.

### External Dependencies

None. This deliverable is pure documentation with no code execution.

### Downstream Consumers

- **PRD-04 (`code-evaluator-prompt.md`)** — References
  `cross-tool-watchpoints.md#formulation-sophistication-catalog` in the
  `formulation_difference` tag decision procedure. PRD-04 depends on this deliverable.

## Open Questions

None. The 5 section topics, their scope boundaries (background context vs. actionable
procedure), and their placement within the file are all resolved in the phase plan's
design decisions.
