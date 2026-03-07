---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: PPC importer drops gencost data, requiring manual cost assignment

## Finding

PyPSA's `import_from_pypower_ppc()` silently drops the `gencost` table from PPC dicts,
leaving all generators with zero marginal cost. Users must manually parse and assign
cost data for any OPF workflow that starts from MATPOWER data.

## Context

During test A-3 (DC OPF), the network was imported via `matpowercaseframes` -> PPC dict
-> `n.import_from_pypower_ppc(ppc)`. PyPSA emits a warning ("some PYPOWER features not
supported: areas, gencosts, component status") but the optimizer will happily run with
zero costs, producing a meaningless dispatch. The workaround requires ~5 lines of code
to parse `gencost` and set `n.generators["marginal_cost"]`.

## Implications

This is relevant to the Accessibility audit (D-series). A new user following the
documented PPC import path may not realize their OPF results are wrong due to missing
costs. The warning is easy to overlook in verbose solver output. This should also be
noted in the Maturity assessment as a known long-standing limitation of the importer.
