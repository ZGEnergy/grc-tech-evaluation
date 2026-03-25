---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Clean 5-layer architecture with package-per-concern design

## Finding

The Sienna ecosystem uses a clean 5-layer architecture for DCPF (7 layers for OPF) with
well-defined package boundaries: PowerSystems.jl (data), PowerNetworkMatrices.jl (matrices),
PowerFlows.jl (power flow), PowerSimulations.jl (optimization), DataFrames.jl (results).
No circular dependencies -- the package DAG is clean.

## Context

B-6 traced the DCPF solve path from `solve_powerflow(DCPowerFlow(), sys)` through all
abstraction layers. Julia's multiple dispatch provides the formulation selection mechanism.
Internal interfaces use Julia's type system for compile-time safety. Each package can be
used independently (e.g., PowerNetworkMatrices.jl alone for PTDF computation).

## Implications

This is a strongly positive architectural finding for the Maturity audit. The
package-per-concern design enables independent testing, versioning, and evolution of
each component. The main gap is that internal interfaces (KLULinSolveCache, PowerFlowData
construction) are not documented in the public API -- users extending the framework
need to read source code.
