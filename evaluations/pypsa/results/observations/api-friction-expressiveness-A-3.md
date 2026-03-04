---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: medium
timestamp: 2026-03-04T19:12:50Z
---

# Observation: gencost data silently dropped on MATPOWER import

## Finding

PyPSA's `import_from_pypower_ppc` silently drops generator cost data (`gencost`) from
MATPOWER files, defaulting all `marginal_cost` values to 0.0. This forces any OPF workflow
starting from standard test cases to manually reconstruct cost data.

## Context

During test A-3 (DC OPF), generator costs had to be manually assigned by reading the
`gencost` matrix from `matpowercaseframes` and setting `net.generators.at[name, "marginal_cost"]`
for each generator. The import emits a warning ("some PYPOWER features not supported:
areas, gencosts, component status") but the warning is easily overlooked in log output.

The workaround is straightforward (setting a public DataFrame column) but adds ~15 lines
of boilerplate to any OPF test starting from MATPOWER data.

## Implications

- **Accessibility:** Users attempting their first OPF on a standard test case will get a
  zero-cost solution (all generators at minimum output or arbitrary dispatch) with no error.
  The failure mode is silent incorrect results, not an error message.
- **Maturity:** The gencost format is well-defined in MATPOWER and widely used. Not
  supporting it in the pypower importer is a completeness gap.
