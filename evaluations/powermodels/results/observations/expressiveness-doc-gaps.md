---
dimension: expressiveness
tag: doc-gaps
tool: powermodels
timestamp: 2026-03-05T19:00:00Z
---

# Documentation Gaps Observations -- Expressiveness

## 1. Multi-network variable access underdocumented

- `PowerModels.var(pm, nw_id, :pg, gen_id)` is the key pattern for accessing optimization variables in multi-network models
- This is not documented in the main PowerModels documentation or tutorials
- Discovered via source code inspection of `src/core/variable.jl`
- Critical for A-5 (SCUC), A-9 (SCOPF), and any custom formulation built on multi-network models

## 2. Dual extraction setting not prominently documented

- The `setting = Dict("output" => Dict("duals" => true))` parameter is required for LMP extraction
- Not mentioned in function docstrings for `solve_dc_opf` or `solve_opf`
- Found via example code in test files, not main documentation

## 3. Native solver API differences not called out

- `compute_dc_pf(data)` returns a result dict (non-mutating)
- `compute_ac_pf!(data)` mutates data in-place
- The documentation does not explicitly highlight this difference or the implications for workflow
- The naming convention (`!` suffix) follows Julia convention but the behavioral difference is significant

## 4. Formulation-solver compatibility matrix missing

- No documentation on which formulations (DCPPowerModel, ACPPowerModel, DCPLLPowerModel, etc.) work with which solvers (HiGHS, GLPK, Ipopt, SCIP)
- Users discover incompatibilities at solve time via opaque MOI errors
- A simple matrix table would prevent significant debugging time

## 5. `replicate()` semantics for stochastic/multi-period use cases

- `replicate(data, N)` creates N independent copies with no coupling
- Documentation does not clarify that this is purely structural -- no temporal or stochastic semantics
- Users may expect multi-period OPF to include ramp constraints or inter-period coupling (it does not)

## 6. Cost model conventions

- `gen["model"] == 2` means polynomial costs; `gen["ncost"]` gives the order
- `gen["cost"]` array ordering (highest-degree coefficient first) is MATPOWER convention but not explicitly documented in PowerModels
- Relevant when manually constructing objectives (A-5 startup costs, A-9 base-case objective)
