---
tag: api-friction
source_dimension: expressiveness
source_test: A-9
tool: pypsa
severity: medium
timestamp: 2026-03-14T00:30:00Z
---

# Observation: SCOPF API excludes transformer contingencies

## Finding

`n.optimize.optimize_security_constrained()` only accepts Line names in
the `branch_outages` parameter. Passing Transformer names raises an error:
"The following passive branches are not in the network: {('Line', 'T0'), ...}".
This excludes 11 of 46 branches (24%) on the IEEE 39-bus network from N-1
contingency analysis.

## Context

During A-9 (SCOPF on TINY), the test attempted to use all 46 branches
(35 lines + 11 transformers) as contingencies per the test specification.
The API rejected transformer names with a clear but non-obvious error
message. The workaround was to use only line contingencies (35 of 46).

The underlying BODF-based formulation could in principle handle transformer
outages, but the API surface restricts the `branch_outages` parameter to
Line component names only.

## Implications

This limitation affects the Extensibility assessment -- transformer
contingencies would need to be implemented via custom constraints (B-1's
`extra_functionality` callback) rather than the built-in SCOPF API. For
networks where transformer outages are critical (e.g., radial transformer
feeds), this is a meaningful gap. The Accessibility audit (D-4) should
note that the API error message does not suggest the limitation or a
workaround.
