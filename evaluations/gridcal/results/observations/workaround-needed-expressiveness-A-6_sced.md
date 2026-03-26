---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-6
tool: gridcal
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Ramp enforcement partially fails with tightened limits in Normal dispatch mode

## Finding

GridCal's `consider_ramps=True` in `OpfDispatchMode.Normal` enforces ramp constraints in the
baseline case (no violations detected across 208 inter-hour checks), but partially violates
ramp limits when they are tightened to 10% of baseline (capped at 50 MW/hr). One generator
showed a 219 MW delta against a 50 MW/hr ramp limit (4.38x violation).

## Context

During A-6 v11 ramp binding evidence testing, a tightened ramp run was performed to verify
that ramp constraints are demonstrably binding. The tightened ED converged and produced a
significantly different dispatch (865 MW max diff from baseline), confirming ramps affect the
optimization. However, the ramp constraint on Gen 5 was violated, suggesting the formulation
may not enforce ramps uniformly across all generators in Normal mode. Ramp constraint dual
values are not extractable from the LP solution.

## Implications

For Extensibility assessment: the inability to extract ramp dual values limits formulation
transparency. For Scalability: ramp enforcement reliability at tighter settings may affect
confidence in production-grade SCED workflows.
