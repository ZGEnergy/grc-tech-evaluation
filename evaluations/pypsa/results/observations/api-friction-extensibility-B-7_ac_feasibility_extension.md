---
tag: api-friction
source_dimension: extensibility
source_test: B-7
tool: pypsa
severity: low
timestamp: 2026-03-11T00:00:00Z
---

# Observation: pf() return structure inflates convergence extraction code — extensibility impact

## Finding

The undocumented `pf()` return structure (already noted in A-4) causes a disproportionate LOC cost when the AC feasibility workflow is extended programmatically: ~25 LOC to extract convergence status, versus ~5 LOC expected if a documented helper or simple attribute existed.

## Context

Assessed during B-7 extensibility audit of the A-4 AC feasibility test script (332 LOC). The convergence extraction block is the most verbose section relative to its functional role. The `n.pf()` return `Dict` with per-key DataFrames (`pf_result["converged"].values.flatten()[0]`) is not described in primary documentation, requiring developers to inspect source or existing examples to use correctly. The expressiveness observation (`api-friction-expressiveness-A-4_ac_feasibility.md`) already records the discovery; this observation records the extensibility consequence.

## Implications

The accessibility audit (D-4) should note that the `pf()` return structure creates a recurring learning cost for new developers implementing AC feasibility workflows. Any tool integrating PyPSA's AC PF result programmatically will encounter this friction. The maturity audit (D-series) should note that this documentation gap has persisted through at least PyPSA 1.1.2.
