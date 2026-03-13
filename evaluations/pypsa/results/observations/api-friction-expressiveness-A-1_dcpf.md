---
tag: api-friction
source_dimension: expressiveness
source_test: A-1
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Two-step MATPOWER ingestion pipeline with non-obvious ppc dict format

## Finding

PyPSA has no native MATPOWER .m reader. Loading case39.m requires: (1) parse with `matpowercaseframes.CaseFrames`, (2) manually construct a PYPOWER ppc dict using `.values` numpy arrays (DataFrames fail), (3) call `n.import_from_pypower_ppc()`. The `.values` requirement is not documented in PyPSA's API docs.

## Context

Test A-1 (DCPF) needed to load `data/networks/case39.m`. PyPSA's `import_from_pypower_ppc` expects numpy arrays for `bus`, `gen`, `branch` keys — passing `cf.to_dict()` (which returns pandas DataFrames) raises `TypeError: list indices must be integers or slices, not tuple`.

## Implications

Affects all tools dimensions that need to load MATPOWER case files. Accessibility evaluators should note this is a common source of user friction when first working with PyPSA and MATPOWER data. Maturity evaluators should check if this limitation is documented prominently. The `matpowercaseframes` companion package is not listed in PyPSA's core dependencies but is available on PyPI.
