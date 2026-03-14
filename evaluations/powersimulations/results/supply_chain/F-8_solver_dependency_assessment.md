---
test_id: F-8
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "10863706"
status: informational
workaround_class: null
timestamp: "2026-03-14T00:00:00Z"
---

# F-8: Solver Dependency Assessment

## Result: INFORMATIONAL

## Summary

All target use cases except lossy DCOPF (A-10) work on open-source solvers. Four
open-source solvers are available in the evaluation stack: HiGHS (LP/MILP/QP),
GLPK (LP/MILP), SCIP (MILP), and Ipopt (NLP). No commercial solver is required
for the core evaluation use cases. The single gap (DCPLLPowerModel requiring SOCP)
could be addressed by adding an open-source SOCP solver (SCS or Clarabel.jl).

## Solver Inventory

| Solver | Type | License | JLL Version | Problem Classes |
|--------|------|---------|-------------|-----------------|
| HiGHS | LP/MILP/QP | MIT | 1.13.1 | DCOPF, SCUC, SCED, storage dispatch |
| GLPK | LP/MILP | GPL-3.0 | 5.0.1 | DCOPF (linear costs only) |
| SCIP | MILP | Apache-2.0 | 10.0.0 | SCUC, MILP problems |
| Ipopt | NLP (interior point) | EPL-2.0 | 3.14.19 | ACOPF, AC feasibility |

All four are open-source with publicly available source code.

## Use Case Coverage

### Fully Working on Open-Source Solvers

| Test | Use Case | Solver Used | Status |
|------|----------|-------------|--------|
| A-1 | DC Power Flow | N/A (matrix solve) | Pass |
| A-2 | AC Power Flow | N/A (Newton-Raphson) | Pass |
| A-3 | DC OPF | HiGHS | Pass |
| A-4 | AC Feasibility Check | Ipopt | Pass |
| A-5 | SCUC | HiGHS | Pass |
| A-6 | SCED | HiGHS | Pass |
| A-9 | SCOPF (via custom constraints) | HiGHS | Pass |
| A-11 | Distributed Slack OPF | HiGHS | Pass |
| A-12 | Multi-period DCOPF + Storage | HiGHS | Pass |
| C-7 | Solver Swap | All 4 solvers | Pass |

### Failed Due to Solver Limitation

| Test | Use Case | Issue | Required Solver Class |
|------|----------|-------|----------------------|
| A-10 | Lossy DCOPF (DCPLLPowerModel) | Quadratic constraints unsupported by HiGHS | SOCP or QCP solver |

**Details:** The `DCPLLPowerModel` formulation from PowerModels.jl uses
`ScalarQuadraticFunction-in-GreaterThan` constraints for linearized Ohm's law.
HiGHS supports quadratic *objectives* (QP) but not quadratic *constraints* (QCP/SOCP).
GLPK and SCIP also lack SOCP support. Ipopt could solve this as a general NLP but
was not tested for this specific formulation.

### Solver Limitation vs Tool Limitation

| Failure | Category | Explanation |
|---------|----------|-------------|
| A-10 DCPLLPowerModel | **Solver limitation** | The formulation exists in PowerModels.jl but requires a solver class (SOCP) not available in the current open-source stack |
| GLPK + quadratic costs | **Solver limitation** | GLPK cannot handle QP objectives; workaround is linear cost override |
| Hydro dispatch | **Tool limitation** | PowerSimulations lacks HydroDispatch formulation (not solver-related) |

## Open-Source SOCP Solver Options

The A-10 gap could be closed by adding an open-source SOCP-capable solver:

| Solver | License | Julia Package | SOCP Support | Notes |
|--------|---------|---------------|--------------|-------|
| SCS | MIT | SCS.jl | Yes | First-order splitting conic solver |
| Clarabel | Apache-2.0 | Clarabel.jl | Yes | Native Julia, interior-point |
| ECOS | GPL-3.0 | ECOS.jl | Yes | Embedded conic solver |
| COSMO | Apache-2.0 | COSMO.jl | Yes | Operator splitting, native Julia |

These are available in the Julia ecosystem but were not included in the evaluation
Project.toml. Adding `Clarabel.jl` or `SCS.jl` would likely resolve the A-10 failure
without requiring a commercial solver.

## Commercial Solver Assessment

**No commercial solver is required for any core use case.** The evaluation
demonstrates that:

1. **DCOPF/SCUC/SCED** -- fully solved by HiGHS (MIT, free)
2. **ACOPF/AC feasibility** -- fully solved by Ipopt (EPL-2.0, free)
3. **Solver swap** -- all four open-source solvers produce consistent results
4. **Large-scale (10K bus)** -- HiGHS solves DCOPF in 11.5s, Ipopt in 9.7s

Commercial solvers (Gurobi, CPLEX, Mosek) would provide:
- Faster solve times on very large problems
- SOCP/QCP support (Gurobi, Mosek) for DCPLLPowerModel
- Better MILP performance for large SCUC problems
- But they are **not necessary** for the evaluated use cases

## Solver Swap Effort

Solver swap is a **single-parameter change** in PowerSimulations.jl:

```julia
model = DecisionModel(template, sys; optimizer=HiGHS.Optimizer)
# becomes:
model = DecisionModel(template, sys; optimizer=Gurobi.Optimizer)
```

No reformulation or template changes are needed. Solver-specific parameter names
differ (e.g., time limit: `time_limit` vs `tm_lim` vs `limits/time`), but the
JuMP/MathOptInterface abstraction layer handles the model translation.

## License Considerations

| Solver | License | Copyleft Risk |
|--------|---------|---------------|
| HiGHS | MIT | None |
| Ipopt | EPL-2.0 | Weak copyleft (file-level, not linking) |
| SCIP | Apache-2.0 | None |
| GLPK | GPL-3.0 | **Yes** -- GPL copyleft if dynamically linked |
| JuMP | MPL-2.0 | Weak copyleft (file-level) |

**GLPK's GPL-3.0 license** is the primary copyleft concern. Julia loads GLPK via
`ccall` (FFI) to the GLPK shared library. Whether this constitutes "linking" under
GPL is a legal question. For risk-averse deployments, GLPK can be excluded entirely
-- HiGHS covers all LP/MILP use cases that GLPK handles, with better performance.

## Assessment

The open-source solver stack is **sufficient for all core evaluation use cases**
except lossy DCOPF (A-10), which requires an SOCP solver. This gap is addressable
by adding Clarabel.jl or SCS.jl (both open-source, non-GPL). No commercial solver
dependency exists. Solver swap is a trivial configuration change via JuMP's solver
abstraction.
