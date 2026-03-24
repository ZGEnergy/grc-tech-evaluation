---
tag: unit-mismatch
source_dimension: expressiveness
source_test: A-3
tool: gridcal
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Generator dispatch names empty in OPF results

## Finding

When extracting generator dispatch from `opf_results.generator_power`, the generator names
returned by `grid.get_generators()` all had empty string names (`""`). The dispatch values
are correct (total matches expected system load), but mapping dispatch back to specific
generators requires using index position rather than name lookup.

## Context

The MATPOWER `.m` importer does not populate generator names -- the `name` attribute defaults
to an empty string. Bus names are populated from bus numbers (e.g., "1", "2", ..., "39"),
but generator names are not derived from bus assignment.

This means OPF result arrays are index-aligned with `grid.get_generators()` but cannot be
labeled by generator name without additional user code.

## Implications

For accessibility assessment: The lack of generator names in imported MATPOWER cases makes
result interpretation less intuitive. Users must manually track generator-to-bus mapping.
This is a data import limitation, not a solver issue.
