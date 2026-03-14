---
tag: solver-issues
source_dimension: expressiveness
source_test: A-10
tool: gridcal
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Lossy DCOPF loss approximation produces negligible losses

## Finding

GridCal's `add_losses_approximation` option in linear OPF uses a linearized loss factor
`R * rate / V^2` that produces losses of 0.055 MW (0.0009% of load) on case39, compared
to 43.6 MW (0.7%) from ACPF. The loss factor uses the static branch thermal rating rather
than actual power flow magnitude, resulting in extreme underestimation.

## Context

During A-10 (lossy DCOPF with LMP decomposition), the loss approximation was enabled via
`OptimalPowerFlowOptions(add_losses_approximation=True)`. While the feature runs without
errors and produces non-zero loss terms, the magnitude is insufficient for meaningful
loss-inclusive LMP analysis. The LMP differences between lossy and lossless runs are <0.004
$/MWh.

## Implications

This finding affects scalability assessments: the loss approximation may produce slightly
better results on larger networks with higher R values, but the fundamental issue (using
ratings instead of actual flows) limits the accuracy regardless of network size. The
Accessibility audit (D-4) should note that the `add_losses_approximation` parameter is
underdocumented -- its behavior and limitations are not described in any public documentation.
