---
tag: solver-issues
source_dimension: extensibility
source_test: B-4
tool: gridcal
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: TapPhaseControl enum profile bug prevents time-series OPF

## Finding

VeraGridEngine 5.6.28 crashes with `ValueError: 0 is not a valid TapPhaseControl` when using time-series OPF (`run_linear_opf_ts` with non-None `time_indices`). The bug is in the sparse profile system where enum-typed device attributes default to 0, which is not a valid enum member.

## Context

During B-4 (stochastic scenario DCOPF), the native multi-period OPF (`time_indices=[0,1,...,11]`) failed on every scenario. The error occurs in `compile_numerical_circuit_at` when it reads `TapPhaseControl` from a profile at a specific time index. The sparse profile initializes with `default_value=0`, then tries `TapPhaseControl(0)` which raises ValueError. The same crash occurs with `TapModuleControl`.

The workaround was to solve each hour as an independent snapshot, losing inter-temporal coupling (ramp constraints, storage SoC tracking). This affects any test requiring true multi-period OPF on networks with transformers.

## Implications

This bug is tool-specific [tool-specific: enum profile initialization bug] -- not a solver limitation. It affects scalability tests (C-3, C-5) that use time-series OPF on larger networks, and A-12 (multi-period DCOPF with storage) where the sequential-snapshot workaround loses the storage SoC coupling central to that test. The Scalability evaluation should verify whether this bug persists in newer versions.
