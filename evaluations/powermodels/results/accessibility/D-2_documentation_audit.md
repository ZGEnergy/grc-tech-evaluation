---
test_id: D-2
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# D-2: Documentation audit for Suite A tests

## Result: QUALIFIED PASS

## Finding

Of 11 Suite A tests, 4 are completable from official documentation alone (A-1, A-2, A-3, A-8). Three more are partially supported by docs (A-4, A-7, A-10). Four tests required extensive source code reading, GitHub issues, or independent JuMP knowledge with no documentation guidance (A-5, A-6, A-9, A-11). The core PF/OPF workflow is well-documented but anything beyond built-in problem types has significant documentation gaps.

## Evidence

### Per-Test Documentation Assessment

| Test | Task | Docs Alone? | Notes |
|------|------|-------------|-------|
| A-1 (DCPF) | DC power flow | YES | `solve_dc_pf` documented in Quick Guide and Power Flow page. `compute_dc_pf` also documented. Return dict structure explained. |
| A-2 (ACPF) | AC power flow | YES | `solve_ac_pf` documented. Flow calculation via `calc_branch_flow_ac` mentioned in Power Flow docs. |
| A-3 (DCOPF) | DC optimal power flow | YES | `solve_dc_opf` is the primary documented example in Quick Guide. Fully covered. |
| A-4 (AC feasibility) | AC feasibility check | PARTIAL | Not a documented problem type. Requires understanding that AC PF non-convergence implies infeasibility. No explicit guidance on feasibility checking as a workflow. |
| A-5 (SCUC) | Unit commitment | NO | PowerModels has no built-in SCUC. Not mentioned in docs. Required building ~140 lines of JuMP from scratch using only PowerModels for data parsing. No documentation on how to extend for commitment problems. |
| A-6 (SCED) | Economic dispatch | NO | No built-in SCED. Required ~400 lines of custom JuMP code for two-stage decomposition. Zero documentation coverage. |
| A-7 (Contingency sweep) | N-1 contingency analysis | PARTIAL | No built-in contingency sweep function, but the tutorial notebook demonstrates toggling `gen_status` for N-1 analysis. Branch contingencies require manual `deepcopy` + status toggling, which is inferable but not documented. |
| A-8 (Stochastic time-series) | Multi-period OPF | PARTIAL (barely) | Multi-network docs exist but are explicitly marked "for advanced users" and direct readers to source code (`src/prob/test.jl`). `replicate()` function is documented. Sufficient for basic usage but sparse. |
| A-9 (SCOPF) | Security-constrained OPF | NO | Not in core PowerModels. PowerModelsSecurityConstrained.jl exists but is a separate package. Core docs do not mention SCOPF. Required ~330 lines of manual JuMP assembly. |
| A-10 (Lossy DCOPF/LMP) | Lossy DC OPF with LMPs | PARTIAL | `DCPLLPowerModel` formulation exists in the type hierarchy docs but with no usage guidance. LMP extraction via duals not documented. Required Ipopt fallback discovery when HiGHS failed on QCQP (undocumented). ~370 lines. |
| A-11 (Distributed slack) | Distributed slack OPF | NO | No documentation on distributed slack. No built-in support. Required ~400 lines of manual PTDF-based formulation. Not referenced anywhere in docs. |

### Documentation Structure Assessment

**Well-documented areas:**
- Installation and Quick Guide (clear, accurate, minimal)
- Network data format (comprehensive field listings for all component types)
- Result data format (keys documented, `print_summary` utility mentioned)
- Power flow functions (`solve_dc_pf`, `solve_ac_pf`, `compute_dc_pf` differences explained)
- Built-in problem types (PF, OPF, OTS, TNEP)

**Significant gaps:**
- Multi-network framework marked as "for advanced users" with pointer to source code only (GitHub issue #169 open since 2017)
- No SCUC, SCED, SCOPF documentation (not built-in)
- Stochastic OPF not documented; only discoverable via GitHub issue #112
- No guidance on extending PowerModels for custom problem formulations beyond what `build_opf` supports
- Formulation selection guidance absent (when to use ACPPowerModel vs SOCWRPowerModel etc.)
- LMP/dual extraction not documented
- `compute_dc_pf` vs `solve_dc_pf` return type inconsistency not documented (Bool vs MOI enum)
- Native PF solution dict omitting gen outputs not documented

### Sources Required Beyond Docs

- **Source code reading**: A-5, A-6, A-9, A-10, A-11 all required reading PowerModels source to understand internal data structures
- **GitHub issues**: Stochastic OPF limitations (#112), multi-network sparseness (#169)
- **JuMP documentation**: A-5, A-6, A-9, A-11 required independent JuMP/MathOptInterface knowledge
- **Trial and error**: A-10 solver compatibility (HiGHS vs Ipopt for QCQP), A-4 feasibility workflow

## Implications

PowerModels documentation is adequate for its core use case (steady-state PF and OPF) but has substantial gaps for anything beyond built-in problem types. 4/11 tests (36%) are fully documented, 3/11 (27%) partially documented, and 4/11 (36%) have no documentation support. The heavy reliance on JuMP expertise for advanced problems means the effective documentation surface is split across two projects, neither of which documents the integration patterns needed for power-system-specific extensions.
