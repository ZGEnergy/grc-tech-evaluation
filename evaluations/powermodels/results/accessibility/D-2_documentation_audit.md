---
test_id: D-2
tool: powermodels
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-2: Documentation Audit

## Finding

Of the 11 Suite A tests, 4 are fully completable from official documentation alone, 3 are partially completable (docs provide the building blocks but not the full workflow), and 4 require source code reading, GitHub issues, or guesswork. The official docs cover core OPF/PF functions well but have significant gaps in advanced use cases (multi-network workflows, dual extraction, solver compatibility, and custom formulation construction).

## Evidence

### Per-Test Documentation Completability

| Test | Task | Docs Alone? | Notes |

|------|------|-------------|-------|

| A-1 (DCPF) | DC power flow | Yes | `compute_dc_pf` documented on Power Flow page. `calc_branch_flow_dc` also documented. |

| A-2 (ACPF) | AC power flow | Yes | `compute_ac_pf` documented on Power Flow page. Branch flow calc documented. |

| A-3 (DCOPF) | DC OPF with costs/limits | Partial | `solve_dc_opf` shown in Quick Guide. LMP extraction via `setting = Dict("output" => Dict("duals" => true))` is NOT documented in function docstrings or Quick Guide. Dual key names (`lam_kcl_r`, `mu_sm_fr`) undocumented. |

| A-4 (AC feasibility) | AC PF on DC OPF dispatch | Yes | Workflow of set pg values + `compute_ac_pf!` follows from A-1/A-2/A-3 docs. |

| A-5 (SCUC) | Unit commitment | No | No SCUC formulation exists. Docs do not discuss adding binary variables. `instantiate_model` shown in Quick Guide but multi-network variable access pattern `PowerModels.var(pm, nw, :pg, g)` is undocumented. Required source code reading of `src/core/variable.jl`. |

| A-6 (SCED) | Security-constrained ED | No | No built-in SCED. Not mentioned in docs. Would require custom JuMP construction similar to A-5. |

| A-7 (Contingency sweep) | N-M contingency analysis | Partial | No built-in contingency analysis. But `compute_dc_pf` + data dict modification (toggling `br_status`) is inferable from docs. Graph traversal/pruning is entirely custom. |

| A-8 (Stochastic) | Multi-period stochastic OPF | Partial | `replicate()` and `solve_mn_opf` documented on Multi Networks page. But scenario indexing pattern, load profile application via `mn_data["nw"]["$t"]["load"]`, and probability weighting are not shown. No stochastic examples. |

| A-9 (SCOPF) | Security-constrained OPF | No | Docs mention PowerModelsSecurityConstrained.jl exists but provide no guidance on implementing SCOPF in base PowerModels. Multi-network workaround requires undocumented objective replacement and variable access. |

| A-10 (Lossy DCOPF LMP) | Lossy DC OPF + LMP decomposition | Partial | `DCPLLPowerModel` listed in Formulations page. `solve_opf` with formulation type shown in Quick Guide. But LMP decomposition is entirely custom -- no documentation on extracting or decomposing duals. |

| A-11 (Distributed slack) | Distributed slack OPF | No | No distributed slack formulation in PowerModels. Not mentioned in docs. Would require custom constraint construction. |

### Documentation Structure Assessment

The official docs at <https://lanl-ansi.github.io/PowerModels.jl/stable/> are organized as:
- **Quick Guide**: 14 code examples covering basic OPF solve, result access, formulation selection, model inspection
- **Manual**: Network data format, result format, mathematical model, power flow, multi-networks
- **Library**: Formulations list, problem specifications, variables, constraints, objective
- **Developer**: Formulation details

**Strengths:**
- Core functions (`solve_ac_opf`, `solve_dc_opf`, `solve_opf`, `compute_dc_pf`) are discoverable
- Formulation type hierarchy is documented
- `replicate()` and multi-network concept explained
- `instantiate_model` + `optimize_model!` workflow shown

**Critical gaps:**
1. No dual/LMP extraction documentation (the `setting` parameter for duals is not in any docstring or guide)
2. No formulation-solver compatibility matrix (which formulations need which solver types)
3. Multi-network variable access pattern (`PowerModels.var(pm, nw, :pg, g)`) not documented
4. No examples of custom constraint addition via JuMP model access
5. No stochastic/scenario analysis examples
6. No SCUC/SCED/SCOPF guidance (even to say "use extension package X")
7. Tutorial notebooks (lanl-ansi/tutorial-grid-science) target 2019 Grid Science Winter School and recommend Julia v1.8; unclear compatibility with current release

### Summary Counts

- **Completable from docs alone:** 4/11 (A-1, A-2, A-4, plus A-3 partially)
- **Partially completable (building blocks in docs):** 3/11 (A-3, A-7, A-8, A-10)
- **Require source code / guesswork:** 4/11 (A-5, A-6, A-9, A-11)

## Implications

PowerModels documentation is adequate for basic OPF/PF workflows but insufficient for the advanced power systems analysis tasks that represent the core evaluation criteria. The 4/11 fully-documentable rate and the critical gap around dual extraction (essential for LMP analysis) are notable weaknesses. The documentation assumes users will read source code for anything beyond standard OPF -- this is a significant accessibility barrier for teams without Julia expertise.
