---
tag: doc-gaps
source_dimension: extensibility
source_test: B-9
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: PTDF bus ordering (buses_o) is undocumented

## Finding

PyPSA's `sub_network.PTDF` matrix uses `sn.buses_o` column ordering (slack bus first, then pvpq buses), not `n.buses` alphabetical ordering. This is not documented in user-facing API documentation or examples.

## Context

B-9 requires predicting DCPF branch flows using `PTDF @ P_inj`. The naive approach — assembling `P_inj` in `n.buses` alphabetical order — produces flow predictions with errors of up to 14 pu. The correct approach requires using `buses_o` ordering (discoverable only by reading PyPSA source code: `pf.py`, line 1064 `B[1:, 1:]` shows the slack-removed convention).

Once the `buses_o` ordering is used, predictions match DCPF flows to machine precision (< 2e-14 pu). The PTDF matrix itself is correct; the ordering convention is simply undiscoverable from documentation.

## Implications

Any user attempting to use the PTDF for flow prediction or sensitivity analysis will produce incorrect results unless they know about `buses_o`. The Accessibility audit (D-tests) should verify that the PTDF user guide, if any, specifies the column ordering convention. The Maturity audit should note that this API subtlety has no corresponding example or warning in the PyPSA documentation.
