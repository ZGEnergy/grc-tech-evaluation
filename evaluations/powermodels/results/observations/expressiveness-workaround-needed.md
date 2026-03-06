---
dimension: expressiveness
tag: workaround-needed
tool: powermodels
timestamp: 2026-03-05T19:00:00Z
---

# Workaround-Needed Observations -- Expressiveness

## Critical Missing Functionality

### 1. No built-in SCUC (A-5)
- **Severity:** Critical
- **Workaround effort:** ~100 lines of custom JuMP code
- **What's missing:** Binary commitment variables, startup/shutdown logic, min up/down time constraints, ramp rate constraints linked to commitment
- **Workaround approach:** `instantiate_model()` to get JuMP model, then manually add binary variables and constraints. Requires switching from HiGHS to SCIP for MIQP support.
- **Durability:** Fragile -- depends on internal PowerModels variable naming conventions that may change between versions

### 2. No native stochastic programming (A-8)
- **Severity:** High
- **Workaround effort:** ~30 lines for scenario indexing; ~50+ lines for non-anticipativity
- **What's missing:** Probability weights, scenario trees, non-anticipativity constraints, two-stage stochastic formulation
- **Workaround approach:** `replicate()` with flat scenario x period indexing. Works for dispatch-only (scenarios decouple) but would require extensive manual JuMP work for stochastic SCUC.
- **Durability:** Moderate -- `replicate()` and `solve_mn_opf()` are stable public API

### 3. SCOPF requires separate package (A-9)
- **Severity:** High
- **Workaround effort:** ~80 lines of custom code
- **What's missing:** `PowerModelsSecurityConstrained.jl` not installed; no built-in contingency-constrained OPF in base PowerModels
- **Workaround approach:** Multi-network with manual branch removal per contingency, custom objective replacement for base-case-only cost. Preventive SCOPF infeasible on case39; corrective approach used.
- **Durability:** Moderate -- multi-network infrastructure is stable, but objective replacement depends on JuMP internals

### 4. No LMP decomposition (A-10)
- **Severity:** Moderate
- **Workaround effort:** ~20 lines of manual decomposition code
- **What's missing:** Automatic decomposition of LMPs into energy, congestion, and loss components
- **Workaround approach:** Two-solve method (lossless + lossy) with residual attribution. Approximate -- exact decomposition would require loss sensitivity factors.
- **Durability:** Good -- uses only stable public API (`solve_dc_opf`, `solve_opf` with duals)

## Minor Workarounds

### 5. No built-in contingency sweep (A-7)
- **Severity:** Low
- **Workaround effort:** ~50 lines (graph traversal, combinatorics, PF loop)
- **What's missing:** Contingency enumeration, graph-distance pruning, batch PF solve
- **Workaround approach:** Manual BFS, custom combinations iterator, loop over `compute_dc_pf()`
- **Durability:** Good -- `compute_dc_pf()` and dict-based data are stable

### 6. Nodal injection extraction (A-1)
- **Severity:** Low
- **Workaround effort:** ~10 lines
- **What's missing:** Direct API to get net bus injections from power flow solution
- **Workaround approach:** Manual summation of gen output minus load at each bus
