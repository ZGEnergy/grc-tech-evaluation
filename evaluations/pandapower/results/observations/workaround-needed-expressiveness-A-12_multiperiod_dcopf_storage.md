---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-12
tool: pandapower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: No native multi-period DCOPF with inter-temporal storage

## Finding

pandapower cannot natively formulate multi-period DCOPF with inter-temporal storage constraints. The time series module runs sequential independent solves without coupling. The PandaModels.jl bridge has `runpm_storage_opf()` with multi-period parameters, but requires a Julia runtime dependency.

## Context

While testing A-12 (multi-period DCOPF with storage), `rundcopp()` was confirmed to be single-period only. The `run_timeseries()` module loops over timesteps but each solve is independent -- there is no SoC linkage between hours. Storage elements exist (`create_storage()`) and participate in single-period OPF, but without inter-temporal constraints the optimizer cannot perform arbitrage. The `runpm_storage_opf()` function in the PandaModels.jl bridge has the correct interface signature for multi-period storage OPF but requires Julia + PandaModels.jl packages.

## Implications

This finding is relevant to both Expressiveness (blocking for A-12) and Extensibility. The existence of `runpm_storage_opf()` shows the pandapower developers have identified the need, but the implementation depends on an external Julia ecosystem. For users who need multi-period DCOPF in a pure Python environment, pandapower does not provide a solution.
