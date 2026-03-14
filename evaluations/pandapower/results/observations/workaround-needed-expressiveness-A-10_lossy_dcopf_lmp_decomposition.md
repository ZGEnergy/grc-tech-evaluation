---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-10
tool: pandapower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: No lossy DC OPF or LMP decomposition capability

## Finding

pandapower has no lossy DC OPF formulation and provides no mechanism to decompose LMPs into energy, congestion, and loss components. This is a blocking limitation with no available workaround within the tool's API.

## Context

While testing A-10 (lossy DC OPF with LMP decomposition), the PYPOWER backend's DC OPF solver (`qps_pypower`) was confirmed to use a standard lossless B-theta formulation. The `res_bus.lam_p` column provides total bus shadow prices but no decomposition. The PYPOWER bus result matrix has exactly 18 columns with no additional fields. The PandaModels.jl bridge offers `runpm_ploss()` for loss minimization but this is a fundamentally different formulation.

## Implications

This finding affects both Expressiveness (blocking for A-10) and Extensibility assessments. Users who need lossy DC OPF or LMP decomposition would need to build a custom optimization model outside pandapower (e.g., via Pyomo), extracting only the network data from pandapower's DataFrames. This is a significant expressiveness gap for market-simulation and LMP analysis use cases.
