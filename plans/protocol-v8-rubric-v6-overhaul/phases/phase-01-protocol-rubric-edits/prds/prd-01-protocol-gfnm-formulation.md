# PRD-01: Protocol v8 — G-FNM Input Path and Formulation Annotations

## Overview

Update the Suite G section of `evaluation_guides/Phase1_Test_Protocol.md` to make
intermediate CSVs the primary input path for G-FNM-3 and G-FNM-4 (with the cleaned
MATPOWER `.m` as fallback), add the `formulation_difference` tag definition and
decision procedure to the Suite G notes, add the `formulation_difference` maximum
absolute threshold key to `pass_conditions.json`, and update the LARGE row in the
Reference Networks table.

This PRD edits a markdown document (the protocol) and a JSON file (pass conditions),
not executable code. "Data Structures" defines structured data schemas referenced by
the protocol. "API" defines any validation helpers needed to verify the updated
document content.

## Goals

1. **Primary CSV input path.** G-FNM-3 and G-FNM-4 test descriptions specify
   intermediate CSVs as the primary input and the cleaned MATPOWER `.m` as fallback,
   so tools that can ingest CSVs directly do not need a MATPOWER parser for power
   flow verification.

2. **`input_path` frontmatter key.** Result files for G-FNM-3 and G-FNM-4 must
   include an `input_path` key in their YAML frontmatter indicating which input path
   was used (`csv` or `matpower`).

3. **`formulation_difference` tag.** Define a new result tag that may be applied to
   G-FNM-3 and G-FNM-4 deviations when a tool's power flow formulation differs from
   the MATPOWER reference in a systematic, bounded, and explainable way. The tag
   definition includes a numbered decision procedure that produces a deterministic
   tag/no-tag outcome.

4. **`formulation_difference_max_abs` threshold.** Add a new key to
   `data/fnm/reference/pass_conditions.json` under both `dcpf` and `acpf` sections
   specifying the maximum absolute deviation permitted under the
   `formulation_difference` classification. The actual numeric value is set in the
   JSON, not hardcoded in the protocol.

5. **LARGE reference network row.** Update the Reference Networks table to reflect
   that LARGE input is now available in both intermediate CSV and cleaned MATPOWER
   formats.

6. **Protocol version bump.** All changes are authored under protocol version `v8`.
   The revision history table gets a new v8 row summarizing these changes.

## Non-Goals

1. **No changes to G-FNM-1, G-FNM-2, or G-FNM-5.** These tests continue to use the
   raw intermediate format as defined in v7. This PRD only modifies G-FNM-3 and
   G-FNM-4.

2. **No changes to Suites A-F.** This PRD is scoped to Suite G and the Reference
   Networks table only.

3. **No changes to the rubric.** Rubric edits are PRD-03.

4. **No changes to agent-facing notes or version compatibility.** Those are PRD-02.

5. **No implementation of CSV ingestion code.** This PRD defines the protocol text
   that describes the input path; Phase 0 already materialized the CSVs.

6. **No numeric threshold selection.** The `formulation_difference_max_abs` key is
   added to `pass_conditions.json` with a placeholder value. The actual threshold is
   determined during evaluation calibration, not in this PRD.

7. **No removal of cleaned MATPOWER references.** The `.m` file remains as an
   explicit fallback path. Both paths are first-class.

## Data Structures

### `input_path` frontmatter field

A new required YAML frontmatter field for G-FNM-3 and G-FNM-4 result files.

```yaml
# In G-FNM-3.md or G-FNM-4.md frontmatter:
input_path: "csv"       # or "matpower"
```

| Value | Meaning |
|-------|---------|
| `csv` | Tool ingested intermediate CSV tables directly (primary path). |
| `matpower` | Tool loaded the cleaned MATPOWER `.m` case (fallback path). |

The field is mandatory. Results missing `input_path` are non-conformant with v8.

### `formulation_difference` tag schema

A tag that may appear in the `tags` list of G-FNM-3 or G-FNM-4 result frontmatter
when deviations are attributable to a formulation difference rather than an ingestion
or solver error.

```yaml
# In G-FNM-3.md or G-FNM-4.md frontmatter:
tags:
  - formulation_difference
formulation_difference_detail:
  correlated_branch_type: "transformer"   # or "phase_shifter"
  max_abs_deviation_pu: 0.003             # measured max |tool - ref|
  affected_bus_count: 47
  affected_bus_fraction: 0.0017
  explanation: >
    Tool uses a different transformer tap model (ideal vs. non-ideal)
    producing systematic VM deviations on regulated buses.
```

**Fields in `formulation_difference_detail`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `correlated_branch_type` | string | yes | The branch type whose presence correlates with the deviation pattern. Must be one of: `transformer`, `phase_shifter`. |
| `max_abs_deviation_pu` | number | yes | Observed maximum absolute deviation (VM in p.u. for ACPF, VA in degrees for DCPF) across affected buses. |
| `affected_bus_count` | integer | yes | Number of buses where the deviation exceeds the normal aggregate tolerance AND correlates with the identified branch type. |
| `affected_bus_fraction` | number | yes | `affected_bus_count / count(non_excluded_buses)`. |
| `explanation` | string | yes | Human-readable description of the formulation difference and why it produces the observed deviation pattern. |

### `formulation_difference` decision procedure

The following numbered checklist produces a deterministic tag/no-tag outcome. It is
applied per-test (G-FNM-3 or G-FNM-4) after the standard pass/fail evaluation.

> **Formulation Difference Decision Procedure**
>
> Apply this procedure to buses that fail the aggregate tolerance but are not
> already classified by the outlier classification rules in `pass_conditions.json`.
>
> 1. **Compute the set of unclassified failing buses.** Start with all buses
>    exceeding the aggregate tolerance. Remove any bus already classified by the
>    priority-ordered outlier rules (switched_shunt, q_limit, slack_distribution,
>    tap_position, island_boundary). The remainder is the unclassified set.
>
> 2. **Test correlation with transformer/phase-shifter branches.** For each bus
>    in the unclassified set, determine whether it is directly connected to (a) an
>    in-service transformer branch, or (b) an in-service branch with a nonzero
>    phase shift angle (SHIFT != 0). Compute the fraction of unclassified failing
>    buses that are connected to such branches. Call this `correlation_fraction`.
>
> 3. **Correlation gate.** If `correlation_fraction < 0.80`, STOP. The
>    `formulation_difference` tag does NOT apply. The deviations are not
>    systematically correlated with transformer/phase-shifter branches.
>
> 4. **Boundedness gate.** Compute the maximum absolute deviation across all
>    unclassified failing buses. Compare against the
>    `formulation_difference_max_abs` threshold from `pass_conditions.json`
>    (under the relevant `dcpf` or `acpf` section). If the maximum absolute
>    deviation exceeds the threshold, STOP. The `formulation_difference` tag
>    does NOT apply. The deviations are too large to attribute to formulation
>    differences.
>
> 5. **Apply tag.** Both gates passed. Apply the `formulation_difference` tag.
>    Populate `formulation_difference_detail` in the result frontmatter. Buses
>    in the unclassified set that are correlated with transformer/phase-shifter
>    branches are reclassified as `formulation_difference` outliers. The
>    remaining unclassified buses (those not correlated) retain their
>    unclassified status.
>
> 6. **Recalculate pass/fail.** Re-evaluate the aggregate pass condition with
>    `formulation_difference`-classified buses treated the same as other
>    classified outlier causes (i.e., they count as classified outliers in the
>    warning thresholds, not as unqualified failures). The hard-fail conditions
>    are NOT relaxed by this tag -- a bus exceeding the extreme deviation
>    threshold remains a hard fail regardless of classification.

### `formulation_difference_max_abs` in pass_conditions.json

New keys added to the `dcpf` and `acpf` sections of
`data/fnm/reference/pass_conditions.json`:

```json
{
  "dcpf": {
    "formulation_difference_max_abs": {
      "description": "Maximum absolute VA deviation (degrees) permitted under formulation_difference classification. Deviations exceeding this are too large to attribute to formulation differences.",
      "threshold_deg": null,
      "unit": "degrees"
    }
  },
  "acpf": {
    "formulation_difference_max_abs": {
      "description": "Maximum absolute VM deviation (p.u.) permitted under formulation_difference classification. Deviations exceeding this are too large to attribute to formulation differences.",
      "threshold_pu": null,
      "unit": "pu"
    }
  }
}
```

The `null` values are placeholders. Actual thresholds are set during evaluation
calibration based on observed cross-tool deviations on transformer-adjacent buses.

### Updated LARGE row in Reference Networks table

The LARGE row in the Reference Networks table is updated from:

```
| LARGE | FNM Annual S01 | ~30,000 | PSS/E v31 via intermediate format; pre-cleaned MATPOWER case for power flow | Data model fidelity — Suite G FNM ingestion tests (FNM_PATH-gated). |
```

to:

```
| LARGE | FNM Annual S01 | ~30,000 | Intermediate CSV tables (primary); pre-cleaned MATPOWER .m case (fallback) | Data model fidelity — Suite G FNM ingestion tests (FNM_PATH-gated). |
```

## API

### Protocol document validation functions

These are verification functions that check the updated protocol document content.
They operate on the markdown text and JSON files, not on runtime network data.

#### `validate_gfnm3_description(protocol_text: str) -> list[str]`

Parse the G-FNM-3 row from the Suite G table in the protocol. Return a list of
validation errors (empty list = pass). Checks:

- The "Inputs" column references intermediate CSV tables as the primary input.
- The "Inputs" column references cleaned MATPOWER `.m` case as fallback.
- The "Procedure" column describes loading from CSVs first, with fallback to `.m`.
- The "Pass Condition" column is unchanged from v7 (aggregate thresholds from
  `pass_conditions.json`).
- The "Procedure" column or a note requires `input_path` in result frontmatter.

#### `validate_gfnm4_description(protocol_text: str) -> list[str]`

Same as above for G-FNM-4.

#### `validate_formulation_difference_section(protocol_text: str) -> list[str]`

Parse the Suite G notes section. Return validation errors. Checks:

- A `formulation_difference` tag definition exists.
- The decision procedure contains exactly 6 numbered steps.
- Step 3 specifies a correlation gate with threshold 0.80.
- Step 4 references `formulation_difference_max_abs` from `pass_conditions.json`.
- Step 6 states that hard-fail conditions are NOT relaxed.

#### `validate_pass_conditions_json(json_path: str) -> list[str]`

Load `pass_conditions.json` and check:

- `dcpf.formulation_difference_max_abs` key exists with `threshold_deg` field.
- `acpf.formulation_difference_max_abs` key exists with `threshold_pu` field.
- Both have `description` and `unit` fields.

#### `validate_large_row(protocol_text: str) -> list[str]`

Parse the Reference Networks table. Check:

- LARGE row Format column mentions "Intermediate CSV" (or equivalent).
- LARGE row Format column mentions "MATPOWER" as fallback.
- LARGE row no longer references "PSS/E v31 via intermediate format" (the old
  wording that implied PSS/E was the source format).

#### `validate_revision_history(protocol_text: str) -> list[str]`

Check the Revision History table:

- A v8 row exists.
- The v8 row references G-FNM input path changes.
- The v8 row references `formulation_difference` tag.

## Success Criteria

Each criterion is a verifiable check on the updated protocol document or pass
conditions JSON. They are grouped by the document section they verify.

### Reference Networks table (1 check)

1. **SC-01: LARGE row updated.** The LARGE row in the Reference Networks table
   specifies "Intermediate CSV tables" as primary format and "MATPOWER .m" as
   fallback. The old "PSS/E v31 via intermediate format" wording is removed.

### G-FNM-3 test description (3 checks)

2. **SC-02: G-FNM-3 primary input is CSV.** The G-FNM-3 "Inputs" column lists
   intermediate CSV tables (at `FNM_PATH`) as the primary input source.

3. **SC-03: G-FNM-3 fallback is MATPOWER.** The G-FNM-3 "Inputs" column lists
   the cleaned MATPOWER `.m` case (`data/fnm/reference/cleaned/fnm_main_island.mat`)
   as a fallback input when the tool cannot ingest CSVs directly.

4. **SC-04: G-FNM-3 requires `input_path` frontmatter.** The G-FNM-3 description
   or an associated note requires result files to include `input_path: "csv"` or
   `input_path: "matpower"` in YAML frontmatter.

### G-FNM-4 test description (3 checks)

5. **SC-05: G-FNM-4 primary input is CSV.** Same as SC-02 but for G-FNM-4.

6. **SC-06: G-FNM-4 fallback is MATPOWER.** Same as SC-03 but for G-FNM-4.

7. **SC-07: G-FNM-4 requires `input_path` frontmatter.** Same as SC-04 but for
   G-FNM-4.

### `formulation_difference` tag (5 checks)

8. **SC-08: Tag definition exists.** The Suite G notes section contains a
   `formulation_difference` tag definition with a clear scope statement (applies
   to G-FNM-3 and G-FNM-4 only).

9. **SC-09: Decision procedure has 6 numbered steps.** The decision procedure is
   a numbered list with exactly 6 steps, starting with computing the unclassified
   set and ending with pass/fail recalculation.

10. **SC-10: Correlation gate threshold is 0.80.** Step 3 of the decision procedure
    specifies `correlation_fraction >= 0.80` as the gate for applying the tag.

11. **SC-11: Boundedness gate references pass_conditions.json.** Step 4 references
    `formulation_difference_max_abs` from `pass_conditions.json` (not a hardcoded
    threshold in the protocol text).

12. **SC-12: Hard-fail conditions are not relaxed.** Step 6 explicitly states that
    hard-fail conditions (extreme VM/VA deviations) are not relaxed by the
    `formulation_difference` classification.

### pass_conditions.json (2 checks)

13. **SC-13: DCPF threshold key exists.** `pass_conditions.json` contains
    `dcpf.formulation_difference_max_abs` with fields `description`,
    `threshold_deg`, and `unit`.

14. **SC-14: ACPF threshold key exists.** `pass_conditions.json` contains
    `acpf.formulation_difference_max_abs` with fields `description`,
    `threshold_pu`, and `unit`.

### Recording and version (2 checks)

15. **SC-15: Recording note updated.** The "Recording for each G-test" paragraph
    specifies `protocol_version: "v8"` and includes `input_path` as a required
    frontmatter field for G-FNM-3 and G-FNM-4.

16. **SC-16: Revision history v8 row.** The Revision History table contains a v8
    row that summarizes: intermediate CSV as primary G-FNM-3/4 input,
    `formulation_difference` tag and decision procedure, and
    `formulation_difference_max_abs` key in pass_conditions.json.

### Backward compatibility (1 check)

17. **SC-17: v7 results remain valid for G-FNM-1, G-FNM-2, G-FNM-5.** The
    protocol text or revision history note confirms that existing v7 results for
    G-FNM-1, G-FNM-2, and G-FNM-5 do not require re-evaluation under v8. Only
    G-FNM-3 and G-FNM-4 results should be re-evaluated if they were produced
    under v7 without the `input_path` field.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `evaluation_guides/Phase1_Test_Protocol.md` | Edit | Update Reference Networks table, G-FNM-3/4 descriptions, add formulation_difference notes, update recording paragraph, add v8 revision history row |
| `data/fnm/reference/pass_conditions.json` | Edit | Add `formulation_difference_max_abs` keys to `dcpf` and `acpf` sections |

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

- **Phase 0 (completed):** Intermediate CSVs must already exist at `FNM_PATH`.
  This PRD references them in the protocol text but does not create them.
- **pass_conditions.json (exists):** The file already exists at
  `data/fnm/reference/pass_conditions.json` with `dcpf` and `acpf` sections.
  This PRD adds new keys to those sections.
- **PRD-02 (downstream):** PRD-02 bumps `protocol_version` references throughout
  the protocol to v8 and adds the Version Compatibility section. This PRD writes
  the v8 revision history row and updates the recording note, but PRD-02 handles
  the global version string update.

## Open Questions

None. All design decisions were resolved in the phase plan:

- CSV as primary with `.m` fallback: confirmed.
- `formulation_difference` correlation threshold 0.80: confirmed.
- Decision procedure as 6-step numbered checklist: confirmed.
- Threshold values as `null` placeholders in JSON: confirmed (calibration is a
  separate activity).
