# PRD-07: Updated Prompt — config-generator-prompt.md

## Overview

This deliverable updates `.claude/skills/evaluate-tool/prompts/config-generator-prompt.md`,
the prompt that instructs the config-generator agent to parse the evaluation rubric and test
protocol into a structured `eval-config.yaml`. The current prompt (protocol v7 era) is
missing four elements that the v8 protocol and rubric v6 introduce:

1. **`formulation_difference` observation tag.** The v8 protocol introduces a formulation
   difference classification procedure for DCPF deviations in G-FNM-3. The code-evaluator
   prompt (PRD-04) emits a `formulation_difference` tag, but the config-generator's
   Observation Tags section does not include it. Without this tag in the generated config,
   the orchestrator cannot route formulation difference findings to their consumers.

2. **`protocol_version` field.** The generated config should declare `protocol_version: "v8"`
   so that downstream consumers (orchestrator, synthesis agent, Phase 3 validation) can
   verify which protocol version the config was generated from. The current template has no
   protocol version field.

3. **5a/5b criterion split encoding.** The rubric v6 splits Criterion 5 into 5a (Demonstrated
   Maturity) and 5b (Sustainability Risk). The config-generator's dimension extraction for
   the maturity dimension should encode the `sub_criteria` structure so the synthesis agent
   knows which sub-questions feed 5a vs. 5b and can apply the composite grade matrix.

4. **Suite G intermediate CSV path and manifest reference.** The v8 protocol specifies
   intermediate CSVs at `$FNM_PATH/intermediate/` as the primary Suite G input, with a
   `manifest.json` for count verification. The LARGE network tier entry in the config
   template should reference the intermediate CSV path and manifest, not just the generic
   `data/fnm/` source.

These are small, targeted changes to an existing prompt — no structural reorganization of the
config-generator's task, output format, or extraction logic is required.

## Goals

1. **Add `formulation_difference` to the observation tags vocabulary.** Add a new entry to
   the `observation_tags` section of the output template, with `emitted_by: [fnm_ingestion]`
   and `consumed_by: [expressiveness, scalability, synthesis]`. Update the fnm_ingestion
   dimension's `emits` list to include `formulation_difference`. Update the expressiveness
   and scalability dimensions' `consumes` lists to include `formulation_difference`.

2. **Add `protocol_version` field to the output template header.** Add `protocol_version: "v8"`
   immediately after `tool: {{tool_name}}` in the output YAML template. The config-generator
   should extract the protocol version from the protocol document's revision history or
   header and populate this field.

3. **Encode the 5a/5b sub-criteria structure in the maturity dimension.** Add a
   `sub_criteria` mapping to the maturity dimension entry that lists which E-N test IDs
   feed 5a (Demonstrated Maturity) vs. 5b (Sustainability Risk), along with the composite
   grade matrix reference. This enables the synthesis agent to apply the correct grade
   composition logic.

4. **Update the LARGE network tier to reference intermediate CSVs and manifest.** Change the
   LARGE network tier's `source` field to specify `$FNM_PATH/intermediate/` as the primary
   CSV path. Add a `manifest` field pointing to `$FNM_PATH/intermediate/manifest.json`. Add
   `fallback` field pointing to the cleaned MATPOWER case for tools that cannot consume CSVs.

## Non-Goals

- **Restructuring the config-generator prompt.** The task flow (read documents, extract
  dimensions, extract tests, build DAG, write YAML) is unchanged. These updates add fields
  to the extraction and output template without changing the prompt's overall structure.

- **Changing the extraction logic for Suites A-F.** Only the maturity dimension gains
  sub-criteria encoding and only Suite G gains input path updates. Expressiveness,
  extensibility, scalability, accessibility, and supply_chain dimension extraction is
  unchanged except for consuming the new `formulation_difference` tag.

- **Adding new test IDs.** The config-generator extracts test IDs from the protocol. No new
  test IDs are invented by this prompt change.

- **Modifying the execution DAG structure.** The DAG topology, batch splitting rules, and
  step ordering are unchanged.

- **Implementing the formulation_difference decision procedure.** The decision procedure
  lives in the code-evaluator prompt (PRD-04). This PRD only ensures the tag is present in
  the config's observation routing table so the orchestrator can route findings.

- **Implementing the 5a/5b grading logic.** Grading is handled by the synthesis agent and
  the rubric. This PRD encodes the structural mapping so downstream consumers know which
  test feeds which sub-criterion.

- **Modifying SKILL.md or other prompts.** The config-generator prompt is consumed by the
  orchestrator's CONFIGURE state. No other prompts or the orchestrator itself are changed
  by this PRD.

## Data Structures

### Protocol Version Field

The new `protocol_version` field in the generated config header:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigHeader:
    """Header section of the generated eval-config.yaml.

    Documents the expected fields after this update.
    """

    tool: str
    """Tool name, from {{tool_name}}."""

    protocol_version: str
    """NEW — Protocol version extracted from the protocol document.
    Expected value for current protocol: 'v8'."""

    rubric_path: str
    """Path to the rubric document used for generation."""

    protocol_path: str
    """Path to the protocol document used for generation."""

    generated: str
    """ISO 8601 timestamp of config generation."""
```

### Formulation Difference Observation Tag

The new tag entry in the `observation_tags` section:

```python
@dataclass(frozen=True)
class ObservationTagEntry:
    """A single entry in the observation_tags mapping."""

    name: str
    description: str
    emitted_by: list[str]
    consumed_by: list[str]


FORMULATION_DIFFERENCE_TAG = ObservationTagEntry(
    name="formulation-difference",
    description=(
        "DCPF deviations classified as formulation sophistication differences "
        "(correlated with transformer/phase-shifter branches) rather than data "
        "ingestion errors. Emitted by G-FNM-3 formulation_difference decision "
        "procedure."
    ),
    emitted_by=["fnm_ingestion"],
    consumed_by=["expressiveness", "scalability", "synthesis"],
)
```

### 5a/5b Sub-Criteria Encoding

The sub-criteria structure added to the maturity dimension:

```python
@dataclass(frozen=True)
class SubCriteriaMapping:
    """Encodes the 5a/5b split within the maturity dimension config entry.

    This structure tells the synthesis agent which E-N test IDs contribute
    to which sub-criterion, enabling correct composite grade computation.
    """

    sub_criterion_5a: SubCriterionConfig
    """5a: Demonstrated Maturity — backward-looking evidence."""

    sub_criterion_5b: SubCriterionConfig
    """5b: Sustainability Risk — forward-looking risk indicators."""

    composite_grade_matrix: str
    """Reference to the rubric section containing the 3x3 matrix.
    Value: 'rubric:criterion-5:composite-grade-matrix'."""


@dataclass(frozen=True)
class SubCriterionConfig:
    """Configuration for one sub-criterion within Criterion 5."""

    label: str
    """'5a' or '5b'."""

    title: str
    """'Demonstrated Maturity' or 'Sustainability Risk'."""

    test_ids: list[str]
    """E-N test IDs that contribute evidence to this sub-criterion.
    5a: E-1, E-2, E-3, E-6 (renumbered as 5a E-1..E-4 in rubric v6).
    5b: E-4, E-5, E-7 (renumbered as 5b E-1..E-3 in rubric v6)."""
```

### Updated LARGE Network Tier

The LARGE network tier entry with intermediate CSV references:

```python
@dataclass(frozen=True)
class LargeNetworkTier:
    """Updated LARGE network tier config entry.

    Adds intermediate CSV path, manifest, and fallback fields.
    """

    name: str = "FNM Annual S01"
    buses: str = "~30000"
    source: str = "$FNM_PATH/intermediate/"
    manifest: str = "$FNM_PATH/intermediate/manifest.json"
    fallback: str = "data/fnm/reference/cleaned/fnm_main_island.mat"
    fnm_path_gated: bool = True
```

## API

No executable API. This deliverable modifies a markdown prompt template. The following
verification functions describe checks against the prompt text.

### Prompt structure verification

```python
from __future__ import annotations

from pathlib import Path


PROMPT_PATH = Path(
    ".claude/skills/evaluate-tool/prompts/config-generator-prompt.md"
)


def load_prompt() -> str:
    """Read the config-generator prompt and return its full text."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_output_template(prompt_text: str) -> str:
    """Extract the YAML output template from the prompt.

    Returns everything between the ```yaml code fence in the Output Format
    section and the closing ```.
    """
    ...


def extract_observation_tags_section(prompt_text: str) -> str:
    """Extract the Observation Tags section from the prompt.

    Returns everything from '### Observation Tags' through the next H3
    heading or section boundary.
    """
    ...


def verify_protocol_version_field(template_text: str) -> tuple[bool, str]:
    """Verify the output template contains a protocol_version field.

    Checks for:
    - 'protocol_version:' key present in the YAML template header
    - Value is 'v8' or a template variable indicating extraction from protocol
    - Field appears near the 'tool:' field (in the header, not buried in a
      dimension or test entry)

    Returns (present, error_message_if_missing).
    """
    ...


def verify_formulation_difference_tag(prompt_text: str) -> tuple[bool, list[str]]:
    """Verify the formulation_difference tag in observation tags.

    Checks for:
    - 'formulation-difference' or 'formulation_difference' key in the
      observation_tags section of the output template
    - description referencing DCPF deviations or formulation sophistication
    - emitted_by includes fnm_ingestion
    - consumed_by includes expressiveness, scalability, and synthesis

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_fnm_ingestion_emits_tag(prompt_text: str) -> tuple[bool, str]:
    """Verify fnm_ingestion dimension emits formulation-difference.

    Checks the fnm_ingestion dimension entry's emits list includes
    'formulation-difference' or 'formulation_difference' alongside the
    existing tags (fnm-data-model, fnm-scale, workaround-needed).

    Returns (present, error_message_if_missing).
    """
    ...


def verify_consumers_updated(prompt_text: str) -> tuple[bool, list[str]]:
    """Verify expressiveness and scalability consume formulation-difference.

    Checks:
    - The expressiveness dimension's consumes list includes formulation-difference
    - The scalability dimension's consumes list includes formulation-difference

    Also checks that the observation_tags routing table's consumed_by lists
    for formulation-difference include these dimensions.

    Returns (complete, list_of_missing_consumer_entries).
    """
    ...


def verify_sub_criteria_in_maturity(prompt_text: str) -> tuple[bool, list[str]]:
    """Verify the maturity dimension encodes 5a/5b sub-criteria structure.

    Checks for:
    - A 'sub_criteria' mapping or equivalent structure in the maturity dimension
    - 5a label with 'Demonstrated Maturity' title
    - 5b label with 'Sustainability Risk' title
    - Test ID assignments matching rubric v6 (5a: E-1,E-2,E-3,E-6;
      5b: E-4,E-5,E-7 — or the renumbered equivalents)
    - Composite grade matrix reference

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_large_network_csv_path(template_text: str) -> tuple[bool, list[str]]:
    """Verify the LARGE network tier references intermediate CSVs.

    Checks for:
    - source field references '$FNM_PATH/intermediate/' or equivalent
    - manifest field references 'manifest.json'
    - fallback field references the cleaned MATPOWER case
    - fnm_path_gated remains true

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_protocol_version_extraction_instruction(
    prompt_text: str,
) -> tuple[bool, str]:
    """Verify the extraction task instructs reading protocol version.

    Checks that the Task section includes an instruction to extract the
    protocol version from the protocol document (e.g., from the revision
    history table or version header) and populate the protocol_version field.

    Returns (present, error_message_if_missing).
    """
    ...


def verify_existing_tags_preserved(prompt_text: str) -> tuple[bool, list[str]]:
    """Verify all existing observation tags are unchanged.

    Checks that the following tags still exist with their original routing:
    - api-friction, doc-gaps, workaround-needed, solver-issues
    - convergence-quality, unit-mismatch, cascaded-failure
    - license-flags, arch-quality, fnm-data-model, fnm-scale

    Returns (all_present, list_of_missing_or_changed_tags).
    """
    ...


def verify_existing_structure_preserved(
    original_text: str,
    updated_text: str,
) -> tuple[bool, list[str]]:
    """Verify non-targeted sections of the prompt are unchanged.

    Checks that the following sections are identical:
    - Preamble (agent role description)
    - Inputs section
    - Dimensions extraction rules (except maturity sub_criteria addition)
    - Test IDs extraction rules
    - Reference Counts section
    - Test Dependencies section
    - Execution DAG section (structure, not tag routing)
    - Critical Rules section
    - Network tiers for TINY, SMALL, MEDIUM (only LARGE changes)

    Returns (unchanged, list_of_unexpected_changes).
    """
    ...
```

## Success Criteria

Each criterion is a verifiable check on the updated
`.claude/skills/evaluate-tool/prompts/config-generator-prompt.md`.

### Update 1: `formulation_difference` observation tag (4 checks)

1. **SC-01: Tag entry in observation_tags template.** The output template's
   `observation_tags` section includes a `formulation-difference` entry with a description
   referencing DCPF deviation classification or formulation sophistication.

2. **SC-02: Tag emitted by fnm_ingestion.** The `formulation-difference` tag's `emitted_by`
   list includes `fnm_ingestion`. Additionally, the fnm_ingestion dimension's `emits` list
   in the dimension template includes `formulation-difference`.

3. **SC-03: Tag consumed by expressiveness, scalability, synthesis.** The
   `formulation-difference` tag's `consumed_by` list includes `expressiveness`, `scalability`,
   and `synthesis`. The expressiveness and scalability dimension entries include
   `formulation-difference` in their `consumes` lists (synthesis is an implicit consumer via
   the observation routing table).

4. **SC-04: Existing tags unchanged.** All 11 pre-existing observation tags (`api-friction`,
   `doc-gaps`, `workaround-needed`, `solver-issues`, `convergence-quality`, `unit-mismatch`,
   `cascaded-failure`, `license-flags`, `arch-quality`, `fnm-data-model`, `fnm-scale`) remain
   present with their original `emitted_by` and `consumed_by` routing. No tag has been
   removed or had its routing changed.

### Update 2: `protocol_version` field (2 checks)

5. **SC-05: Field in output template header.** The YAML output template contains a
   `protocol_version:` field in the header section (near the `tool:` field), with value
   `"v8"` or a placeholder indicating the value is extracted from the protocol document.

6. **SC-06: Extraction instruction present.** The Task section (step 2 or equivalent) includes
   an instruction to extract the protocol version from the protocol document's revision
   history or header and populate the `protocol_version` field.

### Update 3: 5a/5b sub-criteria encoding (3 checks)

7. **SC-07: Sub-criteria structure in maturity dimension.** The maturity dimension entry in
   the output template includes a `sub_criteria` mapping (or equivalent structured encoding)
   with entries for `5a` and `5b`.

8. **SC-08: Correct test ID assignments.** The 5a entry lists test IDs corresponding to
   release engineering discipline, test coverage/CI health, issue responsiveness, and
   operational adoption (the backward-looking evidence tests). The 5b entry lists test IDs
   corresponding to contributor concentration/bus factor, funding stability, and governance
   model (the forward-looking risk tests). The assignments match the rubric v6 definitions
   from Phase 1 Deliverable 3.

9. **SC-09: Composite grade matrix reference.** The sub-criteria structure includes a
   reference to the rubric's composite grade matrix so the synthesis agent knows where to
   find the 3x3 grade composition table.

### Update 4: LARGE network tier CSV path (3 checks)

10. **SC-10: Primary source is intermediate CSVs.** The LARGE network tier's `source` field
    references `$FNM_PATH/intermediate/` (or equivalent path to the intermediate CSV
    directory), not just the generic `data/fnm/` path.

11. **SC-11: Manifest reference present.** The LARGE network tier includes a `manifest` field
    (or equivalent) referencing `manifest.json` within the intermediate CSV directory. This
    is the manifest that G-FNM-1 uses for count verification.

12. **SC-12: Fallback path present.** The LARGE network tier includes a `fallback` field (or
    equivalent) referencing the cleaned MATPOWER `.m` case for tools that cannot consume CSVs.
    The fallback path points to `data/fnm/reference/cleaned/fnm_main_island.mat` or the
    equivalent location.

### Preservation checks (2 checks)

13. **SC-13: Existing prompt structure preserved.** The preamble, Inputs section, Dimensions
    extraction rules (other than maturity sub_criteria), Test IDs extraction rules, Reference
    Counts section, Test Dependencies section, Execution DAG structure, and Critical Rules
    section are unchanged. No structural reorganization of the prompt has occurred.

14. **SC-14: TINY/SMALL/MEDIUM network tiers unchanged.** The TINY, SMALL, and MEDIUM
    network tier entries in the output template are identical to their pre-update values. Bus
    counts, file paths, and reference count guidance are preserved.

## File Location

The single file modified by this deliverable:

```
.claude/skills/evaluate-tool/prompts/config-generator-prompt.md
```

No new files are created. No files are deleted.

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

### Internal Dependencies

- **Phase 1 Deliverable 1 (`Phase1_Test_Protocol.md` v8)** — The config-generator parses the
  v8 protocol. The protocol must contain the intermediate CSV input path references, the
  formulation sophistication annotations, and the version compatibility section so the
  config-generator can extract them. The `protocol_version` field extraction depends on the
  v8 revision history entry existing in the protocol.

- **Phase 1 Deliverable 3 (`Phase1_Evaluation_Rubric.md` v6)** — The config-generator parses
  the v6 rubric. The 5a/5b sub-criteria structure and test ID assignments must exist in the
  rubric so the config-generator can extract the sub-criteria mapping for the maturity
  dimension.

- **Phase 2 PRD-04 (`code-evaluator-prompt.md`)** — Defines the formulation_difference tag
  emission from the code-evaluator. This PRD ensures the config routes that tag correctly.
  The config-generator's observation routing must match what the code-evaluator emits and
  what the synthesis agent consumes.

### External Dependencies

None. This deliverable modifies only a markdown prompt template with no code execution.

### Downstream Consumers

- **Phase 3 Deliverable 1 (Config generation smoke test).** Phase 3 validates that the
  config-generator can parse the v8 protocol and v6 rubric and produce a well-formed
  `eval-config.yaml`. This PRD's changes directly affect that smoke test — the generated
  config must include `protocol_version`, `formulation-difference` tag routing, sub-criteria
  encoding, and the updated LARGE network tier.

- **All subsequent evaluation runs.** The generated `eval-config.yaml` drives the entire
  evaluation orchestrator. Missing tags or incorrect routing would cause silent observation
  loss.

## Open Questions

None. All design decisions are resolved:

- The `formulation-difference` tag name uses hyphens (matching existing tag naming convention:
  `api-friction`, `doc-gaps`, `fnm-data-model`).
- The `protocol_version` field is placed in the YAML header alongside `tool:`, not in a nested
  metadata section.
- The 5a/5b encoding is a `sub_criteria` mapping within the maturity dimension entry, not a
  top-level restructuring of the dimensions list (Criterion 5 remains one dimension in the
  config).
- The LARGE network tier gains `manifest` and `fallback` fields alongside the updated `source`
  field; the `fnm_path_gated: true` flag is preserved.
