# PRD-04: Updated Prompt — code-evaluator-prompt.md

## Overview

This deliverable makes four updates to `.claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md`,
the prompt that governs code-evaluator agents during the EVALUATE state of an evaluation run.
The current prompt (protocol v7 era) directs Suite G tests to load FNM data from `$FNM_PATH/`
with no distinction between intermediate CSVs and the cleaned MATPOWER `.m` case, provides
no structured ingestion count verification gate in G-FNM-1, lacks a decision procedure for
tagging DCPF deviations as formulation differences vs. bugs, and has no mechanism to consume
version capability data from a research agent.

The four updates are:

1. **G-FNM intermediate CSV input path.** The Suite G methodology section is updated to
   specify intermediate CSVs at `$FNM_PATH/intermediate/` as the primary input for all G-FNM
   tests (G-FNM-1 through G-FNM-5), with the cleaned MATPOWER `.m` as a documented fallback
   when a tool cannot consume CSVs. G-FNM-3/4 guidance is updated to record `input_path` in
   result frontmatter so downstream consumers know which input was used.

2. **Ingestion count verification gate.** G-FNM-1 gains an explicit post-ingestion step that
   checks each table's record count against the manifest and produces structured error output
   on mismatch, failing the gate with actionable diagnostics rather than a generic failure.

3. **Formulation_difference tag procedure.** A new subsection under Methodology Guardrails
   provides a step-by-step decision procedure for classifying DCPF deviation clusters in
   G-FNM-3 as `formulation_difference` (systematic, correlated with transformer-adjacent
   buses at >= 0.80 threshold) vs. `data_ingestion_error` (scattered across all bus types).
   The procedure references the Formulation Sophistication Catalog in
   `cross-tool-watchpoints.md` for background.

4. **Version capability report consumption.** A new `{{version_capability_report}}` input
   variable is added, and a guardrail instructs the code-evaluator to check installed version
   capabilities before attempting tests that depend on version-specific features, recording
   unsupported tests as `fail` with `failure_reason: unsupported_in_installed_version`.

These changes bring the code-evaluator prompt into alignment with the v8 protocol's Suite G
methodology, the formulation-awareness requirements from the rubric v6, and the version
capability pipeline established by the 4th research agent.

## Goals

1. **Update Suite G data source specification** to distinguish the intermediate CSV path
   (`$FNM_PATH/intermediate/`) from the cleaned MATPOWER case path
   (`data/fnm/reference/cleaned/fnm_main_island.mat`). CSVs are the primary input for
   all G-FNM tests (G-FNM-1 through G-FNM-5); the cleaned `.m` is a documented fallback
   when a tool cannot consume CSVs.

2. **Add structured count verification to G-FNM-1** that loads `manifest.json`, iterates
   each table, compares the tool's ingested record count against the manifest's expected
   count, and produces a per-table pass/fail report with expected vs. actual counts. Any
   mismatch fails the G-FNM-1 gate and blocks G-FNM-2 through G-FNM-5.

3. **Add a formulation_difference tag decision procedure** under Methodology Guardrails
   that the code-evaluator follows when G-FNM-3 DCPF deviations exceed pass condition
   thresholds. The procedure distinguishes formulation sophistication differences (tag as
   `formulation_difference`, record as `qualified_pass`) from data ingestion bugs (tag as
   `data_ingestion_error`, record as `fail`).

4. **Add `{{version_capability_report}}` as a consumed input** and a guardrail that
   instructs the code-evaluator to consult this report before running tests that exercise
   version-specific features, preventing misleading error traces from attempts to use
   unsupported APIs.

5. **Add `input_path` to result frontmatter** for G-FNM-3 and G-FNM-4 so that downstream
   consumers (synthesis agent, auditor) can verify which input file was used for power flow
   verification.

## Non-Goals

- **Modifying the cleaned MATPOWER case or the CSV export pipeline.** Those are Phase 0
  artifacts. This PRD only updates the prompt that directs agents to consume them.

- **Defining the formulation sophistication catalog content.** The background context
  (which tools use simplified vs. full B-matrix, expected deviation magnitudes) is defined
  in PRD-02 (`cross-tool-watchpoints.md`). This PRD provides the decision *procedure* that
  references that background.

- **Defining the version capability report schema.** The report schema (YAML frontmatter,
  capability table columns, breaking changes format) is defined in PRD-03
  (`research-prompt.md`). This PRD defines how the code-evaluator *consumes* that schema.

- **Modifying SKILL.md.** The orchestrator updates (dispatching Agent 4, wiring
  `{{version_capability_report}}` into the code-evaluator's variable replacement) are
  PRD-06 scope. This PRD adds the input variable and consumption guardrail to the prompt;
  PRD-06 populates the variable at runtime.

- **Modifying Suite A-C or Suite E methodology.** Only Suite G methodology and the shared
  Methodology Guardrails section are changed. Existing guardrails for convergence
  verification, measured timing, PTDF phase-shifter handling, unit consistency, binding
  constraint verification, generator cycling, and cascaded failure distinction are unchanged.

- **Changing the result frontmatter schema for non-G tests.** The `input_path` enum field
  is added only to G-FNM-3/4 result guidance. The existing frontmatter schema for Suites A-C
  is unchanged.

## Data Structures

### Ingestion Count Verification Output

The structured error output that G-FNM-1 produces when verifying record counts against
the manifest. This schema defines what the test script must log and what appears in the
G-FNM-1 result file's Output section.

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableCountVerification:
    """Per-table result of record count verification against manifest."""

    table_name: str
    """Table name as it appears in the manifest (e.g., 'bus', 'branch', 'generator')."""

    expected_count: int
    """Expected record count from manifest.json."""

    actual_count: int
    """Actual record count after tool ingestion."""

    status: str
    """'match' if expected == actual, 'mismatch' if different,
    'merged' if table was merged with another (e.g., branch + transformer)."""

    merged_from: list[str] = field(default_factory=list)
    """If status is 'merged', lists the constituent manifest tables whose expected
    counts were summed for comparison (e.g., ['branch', 'transformer'])."""

    delta: int = 0
    """actual_count - expected_count. Zero for matches, nonzero for mismatches."""


@dataclass(frozen=True)
class IngestionCountReport:
    """Complete count verification report for G-FNM-1.

    Appears in the G-FNM-1 result file's Output section as a structured table.
    """

    tables: list[TableCountVerification]
    """One entry per manifest table (or merged group)."""

    all_match: bool
    """True if every table's status is 'match' or 'merged' with correct summed count."""

    total_expected: int
    """Sum of all expected counts across all manifest tables."""

    total_actual: int
    """Sum of all actual counts across all ingested tables."""

    manifest_path: str
    """Path to the manifest.json file used for verification."""

    gate_status: str
    """'pass' if all_match is True, 'fail' otherwise. Controls G-FNM-2..5 gating."""

    failure_summary: str = ""
    """If gate_status is 'fail', a human-readable summary of which tables mismatched
    and by how much. Empty string if gate passed."""
```

### Formulation Difference Tag Output

The structured output that the formulation_difference decision procedure produces when
classifying a DCPF deviation cluster in G-FNM-3.

```python
@dataclass(frozen=True)
class DeviationClusterAnalysis:
    """Analysis of a DCPF deviation cluster for formulation_difference tagging.

    Produced by the formulation_difference decision procedure in Methodology Guardrails.
    Appears in the G-FNM-3 result file's Output section.
    """

    total_buses_exceeding_threshold: int
    """Number of buses whose DCPF voltage angle deviation exceeds the pass condition
    threshold."""

    transformer_adjacent_buses_exceeding: int
    """Number of those buses that are adjacent to at least one transformer (branch with
    tap ratio != 1.0 or phase-shift angle != 0)."""

    non_transformer_adjacent_buses_exceeding: int
    """Number of those buses that are NOT adjacent to any transformer."""

    transformer_adjacent_fraction: float
    """transformer_adjacent_buses_exceeding / total_buses_exceeding_threshold.
    High values (>=0.80) indicate formulation difference; low values indicate bug."""

    max_deviation_mw: float
    """Maximum absolute deviation in MW across all exceeding buses."""

    median_deviation_mw: float
    """Median absolute deviation in MW across all exceeding buses."""

    correlation_with_transformer_adjacency: str
    """'strong' if deviations are concentrated on buses adjacent to transformers
    (correlation >= 0.80), 'weak' if deviations are scattered across all bus types,
    'none' if no pattern is discernible."""

    classification: str
    """'formulation_difference' or 'data_ingestion_error' based on the decision procedure."""

    rationale: str
    """1-2 sentence explanation of why this classification was chosen, referencing
    the specific evidence (transformer_fraction, correlation pattern)."""

    recommended_status: str
    """'qualified_pass' for formulation_difference, 'fail' for data_ingestion_error."""

    watchpoints_reference: str = "cross-tool-watchpoints.md#formulation-sophistication-catalog"
    """Anchor to the background context in watchpoints that informed this classification."""
```

### Version Capability Consumption

The code-evaluator does not produce a new schema for version capability consumption;
it consumes the capability report produced by Agent 4 (schema defined in PRD-03). The
relevant interaction is:

```python
@dataclass(frozen=True)
class VersionGatedTestDecision:
    """Decision record when a test is skipped or failed due to version capability.

    Appears in the result file's frontmatter and Approach section when the
    code-evaluator determines a test cannot be attempted because the installed
    version does not support a required feature.
    """

    test_id: str
    """The test being evaluated."""

    required_feature: str
    """The canonical feature name from the capability report (e.g., 'CSV Data Import',
    'Security-Constrained Unit Commitment (SCUC)')."""

    installed_version: str
    """The installed version of the tool, from the capability report frontmatter."""

    feature_supported: str
    """'yes', 'no', or 'partial' — from the capability report's capability table."""

    since_version: str
    """The version in which the feature was introduced, from the capability report.
    'unknown' if not determinable."""

    decision: str
    """'attempt' if supported is 'yes' or 'partial', 'skip' if supported is 'no'."""

    failure_reason: str = ""
    """If decision is 'skip': 'unsupported_in_installed_version'.
    Empty if decision is 'attempt'."""
```

### Extended G-FNM-3/4 Result Frontmatter

The `input_path` field added to G-FNM-3 and G-FNM-4 result frontmatter:

```yaml
---
test_id: G-FNM-3
tool: "{{tool_name}}"
dimension: fnm_ingestion
network: fnm
protocol_version: "v8"
status: pass|fail|qualified_pass
input_path: "csv"  # NEW FIELD — enum: "csv" | "matpower"
workaround_class: null|stable|fragile|blocking
# ... remaining fields unchanged
---
```

The `input_path` field records which input format was used for the test. The value is an
enum: `"csv"` (intermediate CSVs, the primary input) or `"matpower"` (cleaned `.m` fallback).
The field enables downstream consumers to verify the input provenance without re-reading
the Approach section.

## API

No executable API. This deliverable modifies a markdown prompt template. The following
verification functions describe checks against the prompt text.

### Prompt structure verification

```python
from __future__ import annotations

from pathlib import Path


PROMPT_PATH = Path(
    ".claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md"
)


def load_prompt() -> str:
    """Read the code-evaluator prompt and return its full text."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_suite_g_section(prompt_text: str) -> str:
    """Extract the FNM Ingestion (Suite G) Methodology section.

    Returns everything from '## FNM Ingestion (Suite G) Methodology' through
    the next H2 heading or end of file.
    """
    ...


def extract_methodology_guardrails(prompt_text: str) -> str:
    """Extract the Methodology Guardrails section.

    Returns everything from '## Methodology Guardrails' through the next H2
    heading.
    """
    ...


def verify_csv_input_path(suite_g_text: str) -> tuple[bool, str]:
    """Verify that Suite G specifies intermediate CSVs as the primary input.

    Checks for:
    - '$FNM_PATH/intermediate/' or equivalent path reference as primary for all G-FNM
    - Cleaned .m documented as fallback (not primary) for any G-FNM test
    - Rationale for CSV preference (format neutrality, explicit type separation)

    Returns (present, error_message_if_missing).
    """
    ...


def verify_ingestion_count_gate(suite_g_text: str) -> tuple[bool, list[str]]:
    """Verify the ingestion count verification gate in G-FNM-1.

    Checks for:
    - Manifest loading instruction (manifest.json)
    - Per-table count comparison
    - Structured error output on mismatch
    - Gate failure semantics (blocks G-FNM-2..5)
    - Merged table handling (sum of constituent counts)

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_formulation_difference_procedure(
    guardrails_text: str,
) -> tuple[bool, list[str]]:
    """Verify the formulation_difference tag decision procedure.

    Checks for:
    - Step-by-step procedure (at least 3 decision steps)
    - Reference to cross-tool-watchpoints.md#formulation-sophistication-catalog
    - Distinction between formulation_difference and data_ingestion_error
    - Transformer-adjacent bus correlation check (>= 0.80 threshold)
    - Recommended result status mapping (qualified_pass vs fail)

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_version_capability_input(prompt_text: str) -> tuple[bool, list[str]]:
    """Verify the version capability report consumption.

    Checks for:
    - '{{version_capability_report}}' in the Inputs section
    - A guardrail referencing the capability report
    - 'unsupported_in_installed_version' failure reason
    - Instruction to check before attempting version-specific tests

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_input_path_frontmatter(suite_g_text: str) -> tuple[bool, str]:
    """Verify that G-FNM-3/4 guidance includes input_path in result frontmatter.

    Checks for:
    - 'input_path' field mentioned in the G-FNM-3 section
    - 'input_path' field mentioned in the G-FNM-4 section
    - The field records the path to the primary input file used

    Returns (present, error_message_if_missing).
    """
    ...


def verify_existing_content_preserved(
    original_text: str,
    updated_text: str,
) -> tuple[bool, list[str]]:
    """Verify that content outside the four update areas is unchanged.

    Checks that:
    - Generic Guardrails section is unchanged
    - All existing Methodology Guardrails (convergence, timing, PTDF, unit
      consistency, binding constraint, generator cycling, cascaded failure)
      are unchanged
    - Execution Environment, Reference Files, Task sections are unchanged
    - Emit Observations and Consumed Observations sections are unchanged

    Returns (unchanged, list_of_unexpected_changes).
    """
    ...
```

## Success Criteria

Each criterion is a verifiable check on the updated `prompts/code-evaluator-prompt.md` file.

### Update 1: G-FNM Intermediate CSV Input Path (4 checks)

1. **SC-01: CSV input path specified for G-FNM-1.** The Suite G methodology section
   specifies that G-FNM-1 loads intermediate format tables from `$FNM_PATH/intermediate/`
   (or an equivalent path that distinguishes the intermediate CSV directory from the root
   `$FNM_PATH`). The previous generic reference to loading from `$FNM_PATH` for all tables
   is replaced with the specific intermediate subdirectory.

2. **SC-02: CSVs primary for G-FNM-3/4 with .m as fallback.** The G-FNM-3 and G-FNM-4
   sections specify intermediate CSVs as the primary input for power flow verification,
   with the cleaned MATPOWER `.m` at `data/fnm/reference/cleaned/fnm_main_island.mat`
   documented as a fallback when a tool cannot consume CSVs.

3. **SC-03: input_path enum in G-FNM-3/4 result frontmatter.** The G-FNM-3 and G-FNM-4
   per-test guidance sections instruct the code-evaluator to include an `input_path` field
   in the result file's YAML frontmatter, using the enum value `"csv"` or `"matpower"` to
   record which input format was used for that test.

4. **SC-04: Data Source section updated.** The "Data Source" subsection within Suite G
   methodology specifies intermediate CSVs as the primary input for all G-FNM tests, with
   the cleaned `.m` case file as a documented fallback, replacing the current undifferentiated
   description of FNM data at `$FNM_PATH/`.

### Update 2: Ingestion Count Verification Gate (4 checks)

5. **SC-05: Manifest loading instruction.** The G-FNM-1 per-test guidance instructs the
   code-evaluator to load `manifest.json` (at `data/fnm/manifest.json` on the host or
   `/workspace/data/fnm/manifest.json` in the devcontainer) and extract per-table expected
   record counts.

6. **SC-06: Per-table count comparison.** The G-FNM-1 guidance instructs the code-evaluator
   to compare the tool's ingested record count for each table against the manifest's expected
   count. The comparison must be explicit (not implicit via "load every table and check" —
   the specific check-against-manifest step must be stated).

7. **SC-07: Structured mismatch reporting.** The G-FNM-1 guidance specifies that on count
   mismatch, the result file's Output section must include a per-table report showing
   table name, expected count, actual count, and delta for each table. This is structured
   output (table or list), not a prose narrative.

8. **SC-08: Merged table handling preserved.** The existing guidance for merged record types
   (e.g., branches + transformers) is preserved: the merged count must equal the sum of
   constituent manifest counts. This is consistent with the structured verification — merged
   tables report `merged_from` constituent names and a summed expected count.

### Update 3: Formulation_difference Tag Procedure (4 checks)

9. **SC-09: Decision procedure subsection exists.** The Methodology Guardrails section
   contains a new subsection (H3 or bullet block) for the `formulation_difference` tag
   decision procedure. The subsection is visually distinct from the existing guardrails
   and applies specifically to G-FNM-3 DCPF deviation analysis.

10. **SC-10: Step-by-step classification steps.** The decision procedure includes at least
    3 explicit steps: (a) identify buses exceeding the DCPF deviation threshold,
    (b) compute the fraction of exceeding buses that are adjacent to transformers (tap != 1.0
    or shift != 0), (c) classify as `formulation_difference` if the transformer-adjacent
    fraction is high (>= 0.80) and deviations correlate with transformer adjacency, or as
    `data_ingestion_error` if deviations are scattered across all bus types.

11. **SC-11: Watchpoints catalog reference.** The decision procedure references
    `cross-tool-watchpoints.md#formulation-sophistication-catalog` (or the section by name)
    as the background context for understanding why formulation differences arise between
    tools.

12. **SC-12: Result status mapping.** The decision procedure maps classifications to result
    statuses: `formulation_difference` maps to `qualified_pass` (the tool's DCPF is correct
    for its formulation level), `data_ingestion_error` maps to `fail`.

### Update 4: Version Capability Report Consumption (3 checks)

13. **SC-13: Input variable declared.** The Inputs section at the top of the prompt includes
    `{{version_capability_report}}` as a listed input variable with a brief description of
    its purpose (version capability data from the research phase).

14. **SC-14: Version-gated test guardrail.** The prompt contains a guardrail (in Methodology
    Guardrails or Generic Guardrails) instructing the code-evaluator to consult the version
    capability report before attempting any test that exercises a feature listed in the
    capability table. If the feature's `supported` field is `no`, the test should be recorded
    as `fail` with `failure_reason: unsupported_in_installed_version` without attempting
    execution.

15. **SC-15: Partial support handling.** The version-gated guardrail specifies that `partial`
    support means the test should be attempted, with a note in the result file documenting
    which subset of the feature is supported per the capability report.

### Preservation checks (2 checks)

16. **SC-16: Existing Methodology Guardrails unchanged.** The 7 existing Methodology
    Guardrails (convergence verification, measured timing, PTDF phase-shifter handling,
    unit consistency, binding constraint verification, generator cycling verification,
    cascaded failure distinction) are present and unmodified in the updated prompt.

17. **SC-17: Existing Generic Guardrails unchanged.** The Generic Guardrails section
    (protocol authority, workaround taxonomy, performance loops, result frontmatter) is
    present and unmodified in the updated prompt.

## File Location

The single file modified by this deliverable:

```
.claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md
```

No new files are created. No files are deleted.

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

### Internal Dependencies

- **PRD-02 (`cross-tool-watchpoints.md`)** — The formulation_difference tag procedure
  (Update 3) references `cross-tool-watchpoints.md#formulation-sophistication-catalog`
  for background context on B-matrix formulation differences. PRD-02 must define this
  section before the code-evaluator can reference it.

- **PRD-03 (`research-prompt.md`)** — The version capability report consumption (Update 4)
  assumes the capability report schema defined in PRD-03 (YAML frontmatter with
  `installed_version`, capability table with `feature`/`supported`/`since_version`/`notes`
  columns). The code-evaluator consumes the report using this schema; it does not redefine
  it.

- **Existing `manifest.json` format** — The ingestion count verification gate (Update 2)
  relies on the manifest containing per-table record counts. The manifest format is defined
  by Phase 0 deliverables and documented in `data/fnm/docs/intermediate-schema.md`.

- **Existing cleaned MATPOWER case** — The CSV input path update (Update 1) documents the
  cleaned case at `data/fnm/reference/cleaned/fnm_main_island.mat` as a fallback input for
  tools that cannot consume intermediate CSVs.

### External Dependencies

None. This deliverable modifies only a markdown prompt template with no code execution.

### Downstream Consumers

- **PRD-06 (SKILL.md)** — The SKILL.md orchestrator update wires `{{version_capability_report}}`
  into the code-evaluator's variable replacement. PRD-06 depends on this PRD having declared
  the variable in the Inputs section.

- **Phase 3 (Validation)** — Verifies that the code-evaluator prompt's Suite G methodology is
  consistent with the v8 protocol's G-FNM test definitions and that no dangling references
  exist to moved or deleted content.

## Open Questions

None. All design decisions were resolved in the phase plan:

- CSV path as primary for all G-FNM tests (G-FNM-1 through G-FNM-5), cleaned `.m` as
  documented fallback: confirmed.
- Formulation_difference procedure in code-evaluator prompt, background in watchpoints:
  confirmed (design decision documented in phase plan).
- `{{version_capability_report}}` as a new input variable (not embedded in research
  context): confirmed. Separate variable enables programmatic consumption.
- `input_path` in result frontmatter for G-FNM-3/4 only (not all tests): confirmed.
  Only Suite G power flow tests have ambiguous input sources requiring provenance tracking.
- Structured mismatch reporting in G-FNM-1 (not prose): confirmed. Structured output
  enables automated cross-tool comparison of ingestion fidelity.
