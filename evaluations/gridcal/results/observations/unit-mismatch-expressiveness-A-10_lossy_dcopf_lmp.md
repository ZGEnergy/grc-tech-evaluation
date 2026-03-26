---
tag: unit-mismatch
source_dimension: expressiveness
source_test: A-10
tool: gridcal
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Loss formula uses thermal rating instead of actual flow, producing scale mismatch

## Finding

GridCal's lossy DCOPF loss factor formula uses `R * rate / V^2` where `rate` is the static
branch thermal rating (MVA) rather than the actual power flow (MW). This produces loss estimates
that are orders of magnitude smaller than expected because the thermal rating appears in a
position where actual flow magnitude should be used. The result is a 500x underestimate of
total losses (5.46e-02 MW vs ~43 MW expected).

## Context

During A-10 (lossy DCOPF with LMP decomposition), the loss approximation was enabled and
produced technically non-zero losses, but the magnitude (8.74e-04% of load) falls far below
the expected 0.5--3% range. The loss factor is computed during model setup and applied as a
fixed coefficient rather than being updated iteratively with the flow solution.

## Implications

For Accessibility (D-dimension): users relying on the loss approximation may not realize the
extreme underestimation. The feature name (`add_losses_approximation`) implies a useful
approximation, but the actual output is negligible. No documentation describes the formula
or its limitations.
