---
test_id: F-8
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "5314ea15"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# F-8: Solver Dependency Assessment

## Result: INFORMATIONAL

## Summary

All target use cases except lossy DCOPF (A-10) work on open-source solvers. Four
open-source solvers are available in the evaluation stack: HiGHS (LP/MILP/QP),
GLPK (LP/MILP), SCIP (MILP), and Ipopt (NLP). No commercial solver is required
for the core evaluation use cases. The single gap (DCPLLPowerModel requiring SOCP)
could be addressed by adding an open-source SOCP solver (SCS or Clarabel.jl).

**v11 JLL binary artifact license audit:** All four solver JLL packages have been
audited for wrapper vs. binary license discrepancies. The binary artifact license
(not the Julia wrapper license) governs deployment authorization. SCIP binary
version 10.0.2 confirmed via `SCIP.SCIPversion()` -- Apache 2.0 applies (well above
the 8.0.3 ZIB Academic threshold).

## Solver Inventory with JLL Binary License Audit

### Wrapper vs. Binary License (v11 requirement)

| Solver | JLL Package | JLL Version | Julia Wrapper License | Binary Artifact License | Discrepancy? |
|--------|-------------|-------------|----------------------|------------------------|--------------|
| HiGHS | HiGHS_jll | v1.13.1+0 | MIT | **MIT** | No |
| Ipopt | Ipopt_jll | v300.1400.1900+0 | MIT | **EPL-2.0** | **Yes** |
| GLPK | GLPK_jll | v5.0.1+1 | MIT | **GPL-3.0** | **Yes** |
| SCIP | SCIP_jll | v1000.0.2+0 | MIT | **Apache-2.0** | **Yes** |

### SCIP Version Verification (v11 critical check)

```
julia> SCIP.SCIPversion()
10.0
```

SCIP_jll v1000.0.2+0 maps to SCIP version 10.0.2. The ZIB Academic License applied
to SCIP versions < 8.0.3 (non-commercial use only). Starting with SCIP 8.0.3, the
license changed to Apache 2.0. Since 10.0.2 >> 8.0.3, the bundled binary is
**Apache 2.0 -- no ZIB Academic restriction applies.**

### Binary License Implications

| Solver | Binary License | Impact on Deployment |
|--------|---------------|---------------------|
| HiGHS | MIT | No restrictions. Fully permissive. |
| Ipopt | EPL-2.0 | Weak copyleft (file-level). Modifications to Ipopt source must be shared. Using Ipopt as a solver backend does not create a derivative work. No impact for standard use. |
| GLPK | GPL-3.0 | **Strong copyleft.** Whether dynamic linking via `ccall` constitutes "linking" under GPL is a legal question. For risk-averse deployments, GLPK can be excluded -- HiGHS covers all LP/MILP use cases. |
| SCIP | Apache-2.0 | No restrictions beyond attribution. Fully permissive for version >= 8.0.3. |

### Solver Transitive Binary Dependencies

| Component | JLL Package | Binary License | Used By |
|-----------|-------------|---------------|---------|
| MUMPS (seq) | MUMPS_seq_jll v500.800.100+0 | CeCILL-C (LGPL-compatible) | Ipopt |
| SPRAL | SPRAL_jll v2025.5.20+0 | BSD-3-Clause | Ipopt |
| ASL | ASL_jll | BSD-3-Clause | Ipopt |
| METIS | METIS_jll | Apache-2.0 | SCIP |
| bliss | bliss_jll | LGPL-3.0 | SCIP |
| GMP | GMP_jll | LGPL-3.0+ | SCIP |
| boost | boost_jll | BSL-1.0 | SCIP |
| SCIP_PaPILO | SCIP_PaPILO_jll v1000.0.2+0 | Apache-2.0 | SCIP |

All solver transitive binary dependencies are permissive or weak copyleft (dynamic linking OK).

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

## Open-Source SOCP Solver Options

The A-10 gap could be closed by adding an open-source SOCP-capable solver:

| Solver | License | Julia Package | SOCP Support | Notes |
|--------|---------|---------------|--------------|-------|
| SCS | MIT | SCS.jl | Yes | First-order splitting conic solver |
| Clarabel | Apache-2.0 | Clarabel.jl | Yes | Native Julia, interior-point |
| ECOS | GPL-3.0 | ECOS.jl | Yes | Embedded conic solver |
| COSMO | Apache-2.0 | COSMO.jl | Yes | Operator splitting, native Julia |

Adding `Clarabel.jl` or `SCS.jl` would likely resolve the A-10 failure without
requiring a commercial solver.

## Commercial Solver Assessment

**No commercial solver is required for any core use case.** The evaluation
demonstrates that:

1. **DCOPF/SCUC/SCED** -- fully solved by HiGHS (MIT binary)
2. **ACOPF/AC feasibility** -- fully solved by Ipopt (EPL-2.0 binary)
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

## License Summary for Recommended Solver Configuration

For a license-clean deployment:

| Solver | Use For | Binary License | Risk |
|--------|---------|---------------|------|
| HiGHS | LP/MILP/QP | MIT | None |
| Ipopt | NLP/ACOPF | EPL-2.0 | Weak copyleft, no impact for standard use |
| SCIP | Alternative MILP | Apache-2.0 | None (v10.0.2, confirmed above 8.0.3 threshold) |

Excluding GLPK (GPL-3.0) from the solver set eliminates all strong copyleft exposure
with no loss of problem-class coverage (HiGHS covers all LP/MILP use cases).

## Data Source

- JLL package versions from `Pkg.dependencies()` in devcontainer (accessed 2026-03-24)
- SCIP version from `SCIP.SCIPversion()` in devcontainer = 10.0 (accessed 2026-03-24)
- Binary artifact licenses from JuliaBinaryWrappers GitHub repos and upstream project licenses (accessed 2026-03-24)
- SCIP upstream license from `gh api repos/scipopt/scip --jq '.license.spdx_id'` = Apache-2.0 (accessed 2026-03-24)
- Solver test results from evaluation Suites A and C (accessed 2026-03-24)

## Implications

1. **All core use cases work on open-source solvers.** No commercial solver dependency exists for DCOPF, SCUC, SCED, ACOPF, or SCOPF.
2. **SCIP binary is Apache 2.0 (v11 confirmed).** The bundled SCIP v10.0.2 is well above the 8.0.3 ZIB Academic threshold. No non-commercial restriction applies.
3. **GLPK is the only GPL-licensed solver binary and is fully replaceable.** HiGHS covers all problem classes that GLPK handles, with better performance.
4. **Ipopt binary is EPL-2.0 (weak copyleft).** Standard use as a solver backend does not trigger copyleft obligations.
5. **The SOCP gap (A-10) is addressable without commercial solvers.** Adding Clarabel.jl (Apache-2.0) or SCS.jl (MIT) would close this gap.
6. **Solver swap is trivial.** JuMP's solver abstraction layer makes switching solvers a single-parameter change with no model reformulation.
