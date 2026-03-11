# PRD-01: Config Generation Smoke Test

## Overview

Run the evaluate-tool skill's config-generator agent against the v8 protocol and v6
rubric for a single tool (pypsa). Validate that config generation completes without error
and produces a structurally valid `eval-config.yaml`. This is a verification deliverable
-- it produces a smoke test report documenting pass/fail status for each structural check,
not new code or document edits.

The config-generator agent (`config-generator-prompt.md`) reads the protocol and rubric,
extracts dimensions, test IDs, network tiers, observation tags, test dependencies, and
an execution DAG, then writes a single `eval-config.yaml`. The smoke test confirms that
the v8 protocol structure is machine-readable by this pipeline: the generated config is
syntactically valid YAML, contains every test ID from the v8 protocol, declares a
well-formed DAG, routes observation tags consistently, maps network tiers correctly, and
reflects v8-specific additions (the `formulation_difference` tag, the 5a/5b criterion
split, and a `protocol_version` field set to `v8`).

The generated config is written to a scratch location
(`plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/scratch/`) to avoid
polluting pypsa's evaluation state. The smoke test report is a standalone markdown file
with a per-check results table and the generated config included as an appendix.

## Goals

1. **Confirm v8 protocol is machine-parseable.** The config-generator agent completes
   without error when given the v8 protocol and v6 rubric as inputs. Completion means
   the agent writes a YAML file to the output path and reports success.

2. **Validate structural completeness.** Every test ID defined in the v8 protocol
   (Suites G, A, B, C, D, E, F, G-FNM) appears in the generated config under the
   correct dimension. No test IDs are invented, omitted, or misattributed.

3. **Validate DAG well-formedness.** The execution DAG is a valid topological sort:
   every step references test IDs that exist in the config, no test ID appears in
   multiple steps, gate tests precede all other steps, observation consumers run after
   their producers, and no step exceeds the 5-test-ID batch limit.

4. **Validate observation tag consistency.** Every observation tag declared in the
   config's `observation_tags` section has at least one emitter and at least one
   consumer. Every tag referenced in a dimension's `emits` or `consumes` list exists
   in the `observation_tags` section. The `formulation_difference` tag -- a v8
   addition -- is present in the tag vocabulary.

5. **Validate network tier mapping.** The config's `networks` section matches the
   protocol's Reference Networks table: TINY = IEEE 39-bus (39 buses), SMALL = ACTIVSg
   2k, MEDIUM = ACTIVSg 10k, LARGE = FNM Annual S01 (FNM_PATH-gated). File paths
   point to files that exist in `data/networks/` (or are documented as FNM_PATH-gated
   for LARGE).

6. **Validate v8-specific fields.** The config contains `protocol_version: v8` (or
   `"v8"`). If the config encodes rubric criteria, the 5a/5b split is reflected (e.g.,
   two sub-dimensions under criterion 5, or a `sub_criteria` field with `5a` and `5b`
   entries).

7. **Produce a structured smoke test report.** The report records each check as
   pass/fail with evidence (the specific config section or value that satisfied or
   violated the check). Failures include the check name, the expected condition, and
   the actual finding.

## Non-Goals

1. **No execution of the generated config.** The smoke test does not run gate tests,
   evaluator agents, or any part of the EVALUATE/VALIDATE/SYNTHESIZE states. It only
   confirms that config generation succeeds and the output is structurally valid.

2. **No tool re-evaluation.** The generated config is written to a scratch directory
   and is not used for an actual pypsa evaluation.

3. **No modification of the config-generator prompt.** If the config-generator produces
   incorrect output, this PRD documents the failure. Fixes belong in Phase 2 (the
   config-generator prompt) or Phase 1 (the protocol/rubric), not here.

4. **No modification of the protocol or rubric.** Phase 3 is read-only with respect
   to Phases 1 and 2 artifacts.

5. **No automated test suite.** The checks are documented as verification functions
   (specification) and executed manually by the auditor. There is no pytest file.

## Data Structures

### Smoke test report schema

The smoke test report is written to:

```
plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/config-generation-smoke-test.md
```

The report follows this structure:

```markdown
# Config Generation Smoke Test Report

**Tool:** pypsa
**Protocol:** evaluation_guides/Phase1_Test_Protocol.md (v8)
**Rubric:** evaluation_guides/Phase1_Evaluation_Rubric.md (v6)
**Config output:** plans/.../scratch/pypsa-eval-config.yaml
**Date:** <ISO 8601>
**Status:** PASS | FAIL (N of M checks passed)

---

## Summary

<1-3 sentence summary of overall result>

## Check Results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | YAML syntax valid | PASS/FAIL | <evidence> |
| 2 | ... | ... | ... |

## Failures

### <Check name>

**Expected:** <condition>
**Actual:** <finding>
**Config section:** <YAML path or excerpt>

---

## Appendix: Generated Config

```yaml
<full contents of the generated eval-config.yaml>
```
```

### Report field specifications

| Field | Type | Description |
|-------|------|-------------|
| `Tool` | string | Always `pypsa` for this smoke test. |
| `Protocol` | string | Relative path to the v8 protocol file. |
| `Rubric` | string | Relative path to the v6 rubric file. |
| `Config output` | string | Relative path to the generated config in the scratch directory. |
| `Date` | string | ISO 8601 timestamp of report generation. |
| `Status` | enum | `PASS` if all checks pass, `FAIL` otherwise. Includes count. |

### Check result row specification

| Column | Type | Description |
|--------|------|-------------|
| `#` | integer | Sequential check number (1-based). |
| `Check` | string | Short name matching a success criterion (e.g., "YAML syntax valid"). |
| `Status` | enum | `PASS` or `FAIL`. |
| `Evidence` | string | Brief evidence: the specific config value, count, or section that proves the check. For failures, a description of what was found instead. |

### Scratch directory layout

```
plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/
  scratch/
    pypsa-eval-config.yaml       # Generated config (input to validation)
  config-generation-smoke-test.md  # Smoke test report (output)
```

### v8 protocol test ID inventory

The following test ID sets must all appear in the generated config. This inventory is
derived from the v8 protocol's test tables and is the source of truth for the
completeness check.

| Suite | Dimension | Test IDs | Count |
|-------|-----------|----------|-------|
| Gate | gate | G-1, G-2, G-3 | 3 |
| A | expressiveness | A-1 through A-11 | 11 |
| B | extensibility | B-1 through B-9 | 9 |
| C | scalability | C-1 through C-10 | 10 |
| D | accessibility | D-1 through D-5 | 5 |
| E | maturity | E-1 through E-7 | 7 |
| F | supply_chain | F-1 through F-9 | 9 |
| G-FNM | fnm_ingestion | G-FNM-1 through G-FNM-5 | 5 |
| **Total** | | | **59** |

Note: The v8 protocol may introduce additional test IDs (e.g., P2 readiness findings)
or renumber existing ones. The auditor must extract the actual test ID inventory from
the v8 protocol at audit time and compare against the config. The table above reflects
the v7 baseline; the check validates against whatever v8 defines.

## API

These are verification functions that describe the checks performed on the generated
config. They operate on the parsed YAML content of the generated `eval-config.yaml`.

### Generation verification

#### `verify_generation_success(scratch_dir: str) -> tuple[bool, str]`

Check that the config-generator agent completed and produced output. Checks:

- A file named `pypsa-eval-config.yaml` exists in the scratch directory.
- The file is non-empty (more than 10 lines).
- The file is valid YAML (parseable without syntax errors).

Returns `(success, error_message_or_empty)`.

### Structural completeness

#### `verify_test_id_completeness(config: dict, protocol_text: str) -> tuple[bool, list[str], list[str]]`

Cross-reference every test ID in the v8 protocol against the config. Checks:

- Extract all test IDs from the protocol's test tables (regex: lines matching
  `| <ID> |` where ID follows the pattern `[A-G]-\d+` or `G-FNM-\d+`).
- Extract all test IDs from the config's `dimensions[].tests[].id` fields.
- Compute the symmetric difference: IDs in protocol but not in config (missing),
  and IDs in config but not in protocol (invented).

Returns `(complete, missing_ids, invented_ids)`.

#### `verify_dimension_attribution(config: dict) -> tuple[bool, list[str]]`

Check that every test ID is under the correct dimension. Checks:

- Gate test IDs (`G-*` but not `G-FNM-*`) are under the `gate` dimension.
- `A-*` IDs are under `expressiveness`.
- `B-*` IDs are under `extensibility`.
- `C-*` IDs are under `scalability`.
- `D-*` IDs are under `accessibility`.
- `E-*` IDs are under `maturity`.
- `F-*` IDs are under `supply_chain`.
- `G-FNM-*` IDs are under `fnm_ingestion`.

Returns `(correct, misattributed_ids_with_details)`.

### DAG well-formedness

#### `verify_dag_structure(config: dict) -> tuple[bool, list[str]]`

Check the execution DAG's structural integrity. Checks:

- The `execution_dag` key exists and contains a list of steps.
- Each step has `step` (integer), `label` (string), and `dimensions` (list).
- Step numbers are sequential starting from 1.
- Every step's `dimensions` entries have `name`, `tier`, and `test_ids` fields.
- Every `test_ids` list is non-empty.

Returns `(well_formed, structural_errors)`.

#### `verify_dag_completeness(config: dict) -> tuple[bool, list[str], list[str]]`

Check that the DAG covers all test IDs. Checks:

- Collect all test IDs from all DAG steps.
- Compare against the full test ID set from `dimensions[].tests[].id`.
- No test ID appears in zero DAG steps (missing from DAG).
- No test ID appears in more than one DAG step (duplicate in DAG).

Returns `(complete, missing_from_dag, duplicated_in_dag)`.

#### `verify_dag_ordering(config: dict) -> tuple[bool, list[str]]`

Check topological ordering constraints. Checks:

- Gate tests (dimension `gate`) appear only in step 1.
- No non-gate test appears in step 1.
- For every test with `depends_on` entries, the dependency test IDs appear in an
  earlier step than the dependent test.
- For every dimension that consumes observation tags, the producing dimensions
  complete in an earlier step.
- The `fnm_ingestion` dimension's DAG step (if present) is marked
  `fnm_path_gated: true`.

Returns `(valid_order, ordering_violations)`.

#### `verify_dag_batch_limit(config: dict) -> tuple[bool, list[str]]`

Check the 5-test-ID batch limit. Checks:

- For every DAG step dimension entry, `len(test_ids) <= 5`.

Returns `(within_limit, oversized_batches_with_counts)`.

### Observation tag consistency

#### `verify_observation_tags(config: dict) -> tuple[bool, list[str]]`

Check observation tag declarations and references. Checks:

- An `observation_tags` section exists in the config.
- Every tag in `observation_tags` has `emitted_by` and `consumed_by` lists.
- Every tag has at least one emitter and at least one consumer.
- Every tag name referenced in any dimension's `emits` list exists in
  `observation_tags`.
- Every tag name referenced in any dimension's `consumes` list exists in
  `observation_tags`.
- Emitter/consumer lists in `observation_tags` are consistent with dimension-level
  `emits`/`consumes` declarations (bidirectional consistency).

Returns `(consistent, inconsistencies)`.

#### `verify_formulation_difference_tag(config: dict) -> tuple[bool, str]`

Check for the v8-specific `formulation_difference` tag. Checks:

- A tag named `formulation_difference` (or `formulation-difference`) exists in the
  `observation_tags` section.
- The tag has a non-empty description.
- The tag has at least one emitter and at least one consumer.

Returns `(present, error_message_or_empty)`.

### Network tier validation

#### `verify_network_tiers(config: dict) -> tuple[bool, list[str]]`

Check network tier definitions. Checks:

- The `networks` section contains exactly four tiers: TINY, SMALL, MEDIUM, LARGE.
- TINY references IEEE 39-bus with `buses: 39` (or `~39`).
- TINY's `file` path contains `case39.m` and points to `data/networks/`.
- SMALL references ACTIVSg 2k with bus count approximately 2000.
- MEDIUM references ACTIVSg 10k with bus count approximately 10000.
- LARGE is marked `fnm_path_gated: true`.
- LARGE references the FNM (~30000 buses).

Returns `(correct, tier_errors)`.

### v8-specific fields

#### `verify_protocol_version(config: dict) -> tuple[bool, str]`

Check for protocol version field. Checks:

- A top-level `protocol_version` key exists (or a key containing `protocol` and
  `version` in its name).
- Its value is `"v8"` or `"8"` or `8`.

Returns `(present_and_correct, error_message_or_empty)`.

#### `verify_criterion_5_split(config: dict) -> tuple[bool, str]`

Check that the 5a/5b criterion split is reflected. Checks:

- The config encodes rubric criteria in some form (dimension `criterion_number`
  fields, a `criteria` section, or similar).
- Criterion 5 is split into 5a and 5b (two sub-dimensions, two criterion entries,
  or an explicit `sub_criteria` field with `5a`/`5b` keys).
- If the config does not encode rubric criteria at all (config-generator may not
  produce this), this check is recorded as N/A with an explanatory note.

Returns `(reflected_or_na, error_message_or_na_note)`.

## Success Criteria

Each criterion is a verifiable check performed on the generated config and documented
in the smoke test report.

### Config generation (2 checks)

1. **SC-01: Config generation completes.** The config-generator agent, when given the
   v8 protocol, v6 rubric, tool name `pypsa`, and a scratch output path, completes
   without error and writes a file to the output path.

2. **SC-02: Generated config is valid YAML.** The output file parses as valid YAML
   without syntax errors. The top-level structure contains at minimum: `tool`,
   `networks`, `dimensions`, `execution_dag`, and `observation_tags` keys.

### Test ID completeness (2 checks)

3. **SC-03: All v8 protocol test IDs present.** Every test ID defined in the v8
   protocol's test tables appears in the config under a `dimensions[].tests[].id`
   field. Zero test IDs are missing. The auditor extracts the authoritative test ID
   list from the v8 protocol at audit time (not from a hardcoded list in this PRD).

4. **SC-04: No invented test IDs.** No test ID appears in the config that does not
   exist in the v8 protocol. The config-generator must not fabricate tests.

### Dimension attribution (1 check)

5. **SC-05: Test IDs under correct dimensions.** Every test ID is attributed to the
   correct dimension based on its suite prefix: `G-*` (non-FNM) to `gate`, `A-*` to
   `expressiveness`, `B-*` to `extensibility`, `C-*` to `scalability`, `D-*` to
   `accessibility`, `E-*` to `maturity`, `F-*` to `supply_chain`, `G-FNM-*` to
   `fnm_ingestion`. If the v8 protocol introduces a `p2_readiness` dimension with
   its own test IDs, those must also be correctly attributed.

### DAG well-formedness (4 checks)

6. **SC-06: DAG steps are structurally valid.** Each DAG step has a sequential integer
   `step` field, a `label` string, and a `dimensions` list. Each dimension entry in a
   step has `name`, `tier`, and `test_ids` fields.

7. **SC-07: DAG covers all test IDs exactly once.** Every test ID from the config's
   dimensions appears in exactly one DAG step. No test ID is missing from the DAG.
   No test ID appears in multiple steps.

8. **SC-08: DAG respects topological constraints.** Gate tests are in step 1. No
   non-gate tests are in step 1. Every test dependency (`depends_on`) is satisfied by
   an earlier step. Every observation tag consumer dimension runs after all of that
   tag's producer dimensions complete.

9. **SC-09: DAG respects batch limit.** No single dimension entry within a DAG step
   contains more than 5 test IDs.

### Observation tags (2 checks)

10. **SC-10: Observation tags are internally consistent.** Every tag in
    `observation_tags` has at least one emitter and at least one consumer. Every tag
    referenced in a dimension's `emits` or `consumes` list exists in
    `observation_tags`. The emitter/consumer declarations are bidirectionally consistent
    (if dimension X declares `emits: [foo]`, then `observation_tags.foo.emitted_by`
    includes X).

11. **SC-11: `formulation_difference` tag present.** The v8-specific
    `formulation_difference` (or `formulation-difference`) tag exists in the config's
    tag vocabulary with a non-empty description and at least one emitter and consumer.

### Network tiers (1 check)

12. **SC-12: Network tiers match protocol.** The config's `networks` section defines
    TINY (IEEE 39-bus, 39 buses, file in `data/networks/`), SMALL (ACTIVSg 2k, ~2000
    buses), MEDIUM (ACTIVSg 10k, ~10000 buses), and LARGE (FNM, ~30000 buses,
    `fnm_path_gated: true`). File paths for TINY/SMALL/MEDIUM reference files in
    `data/networks/`. LARGE is correctly marked as FNM_PATH-gated.

### v8-specific fields (2 checks)

13. **SC-13: Protocol version is v8.** The config contains a `protocol_version` field
    (top-level or within metadata) with value `v8`.

14. **SC-14: 5a/5b criterion split reflected.** If the config encodes rubric criteria
    (via `criterion_number` fields or a criteria section), criterion 5 is split into
    5a (Demonstrated Maturity) and 5b (Sustainability Risk). If the config does not
    encode rubric criteria at all, this check is recorded as N/A with a note explaining
    that the config-generator does not currently produce criterion-level metadata -- the
    split is verified via the rubric directly in Deliverable 3 (traceability audit).

### FNM ingestion dimension (2 checks)

15. **SC-15: FNM ingestion dimension present and gated.** The config contains a
    dimension with `name: fnm_ingestion` (or equivalent). The dimension is marked
    `fnm_path_gated: true`. Its tests include G-FNM-1 through G-FNM-5.

16. **SC-16: G-FNM-1 gate semantics encoded.** The config encodes that G-FNM-1 is the
    Suite G gate test: either via a `gate_test` field on the fnm_ingestion dimension,
    a dependency chain where G-FNM-2 through G-FNM-5 depend on G-FNM-1, or equivalent
    structural encoding that the orchestrator can use to skip G-FNM-2 through G-FNM-5
    if G-FNM-1 fails.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/config-generation-smoke-test.md` | Create | Smoke test report with per-check results and generated config appendix |
| `plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/scratch/pypsa-eval-config.yaml` | Create | Generated config (scratch, not production) |

No existing files are modified.

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

### External Dependencies

- **Phase 1 complete.** The v8 protocol (`evaluation_guides/Phase1_Test_Protocol.md`)
  and v6 rubric (`evaluation_guides/Phase1_Evaluation_Rubric.md`) must be finalized.
  The smoke test reads these files as inputs to the config-generator.

- **Phase 2 complete.** The config-generator prompt
  (`.claude/skills/evaluate-tool/prompts/config-generator-prompt.md`) must reflect any
  v8-specific changes (e.g., the `formulation_difference` tag, `protocol_version`
  field, 5a/5b encoding). If Phase 2 did not update the config-generator prompt, the
  smoke test will reveal this as SC failures.

### Internal Dependencies

None. This is Phase 3, Deliverable 1. It has no intra-phase dependencies.

### Downstream Consumers

- **Project maintainer.** Uses the smoke test report to confirm the evaluation pipeline
  can consume the v8 protocol before merging the overhaul to main.

- **Deliverable 3 (traceability audit).** May reference the generated config as
  evidence of config-generator coverage, but does not depend on this deliverable's
  completion.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Single tool (pypsa) for the smoke test: confirmed. Pypsa exercises all suites
  including G-FNM when FNM_PATH is available.
- Scratch location (not the tool's results directory): confirmed. Prevents pollution
  of evaluation state.
- No config execution (structural validation only): confirmed.
- Failures route back to Phases 1/2 for fixes: confirmed. Phase 3 does not edit
  upstream artifacts.
