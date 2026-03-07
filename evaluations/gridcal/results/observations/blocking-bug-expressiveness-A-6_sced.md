---
tag: blocking-bug
source_dimension: expressiveness
source_test: A-6
tool: gridcal
severity: high
timestamp: 2026-03-06T02:00:00Z
---

# Observation: UC/ED not separable; time-series OPF blocks both A-5 and A-6

## Finding

GridCal has no API to fix a commitment schedule and solve economic dispatch only. The `OpfDispatchMode` enum switches between Normal and UnitCommitment modes, but there is no way to pass a binary commitment vector to the solver. Combined with the TapPhaseControl crash that blocks time-series OPF on case39.m, this means neither SCUC (A-5) nor SCED (A-6) can be properly tested.

## Context

A-6 depends on A-5 for a commitment schedule. A-5 failed. Even if A-5 had succeeded, the lack of UC/ED separation means the user cannot hold commitment fixed and re-optimize dispatch -- a fundamental operation in market clearing.

## Implications

The TapPhaseControl bug (affecting time-series OPF) cascades across multiple expressiveness tests: A-5, A-6, A-8, B-4. This single bug is responsible for at least 3 test failures/downgrades. It should be weighted heavily in the maturity assessment.
