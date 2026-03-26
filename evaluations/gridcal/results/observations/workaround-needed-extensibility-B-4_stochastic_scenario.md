---
tag: workaround-needed
source_dimension: extensibility
source_test: B-4
tool: gridcal
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Sequential snapshot OPF workaround for time-series bug

## Finding

GridCal's native time-series OPF fails on VeraGridEngine 5.6.28 due to a TapPhaseControl enum bug. The workaround uses sequential snapshot solves (documented public API), which is classified as stable but loses inter-temporal coupling.

## Context

During B-4 (stochastic scenario DCOPF), the native multi-period OPF crashed with `ValueError: 0 is not a valid TapPhaseControl`. The sequential snapshot workaround solved all 20 scenarios x 12 hours (240 total solves) successfully in 11.33 seconds. All scenarios converged and produced meaningful variation in objectives (std = 153.32) and LMPs.

## Implications

The stable workaround supports `qualified_pass` status. The loss of inter-temporal coupling is the main limitation -- ramp constraints, storage SoC tracking, and other temporal dependencies are not enforced between hours. Tests requiring true multi-period coupling (A-12) are more severely affected.
