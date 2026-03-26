---
test_id: D-2
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: d1e20188
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T18:00:00Z
---

# D-2: Documentation Audit

## Result: QUALIFIED PASS

## Finding

Of the 12 Suite A tests, only 1 (A-3 DCOPF+LMPs) is fully completable from official
PowerModels documentation alone. 6 tests are partially documented (API exists but usage
patterns require inference or source code reading for details). 2 require source code reading
(A-9 SCOPF, A-10 lossy DCOPF). 3 represent undocumented gaps where the capability does not
exist in the tool (A-5 SCUC, A-8 stochastic OPF, A-11 distributed slack).

## Evidence

Documentation source: `https://lanl-ansi.github.io/PowerModels.jl/stable/`

### Per-Test Assessment

**Rating scale:**
- **Fully documented** -- example code covers the exact API; no inference required
- **Partially documented** -- API documented but usage pattern requires inference
- **Source code required** -- result structure or behavior discoverable only via source
- **Undocumented gap** -- functionality absent or unmentioned

### A-1: DC Power Flow (DCPF)
**Partially documented.** `compute_dc_pf` documented with bus angle output. Branch flows are
NOT in result dict (not mentioned in docs). Workaround: manual `(va_from - va_to - shift) /
(br_x * tap)` or `calc_branch_flow_dc` requires source code reading. `termination_status`
returned as Bool (not JuMP TerminationStatusCode) is undocumented.

### A-2: AC Power Flow (ACPF)
**Partially documented.** `compute_ac_pf` documented. Branch flows require `calc_branch_flow_ac`
post-processing -- function mentioned in docs but two-step workflow not shown in end-to-end
example. NR iteration count and convergence residual not exposed (convergence-quality
observation confirms binary_convergence_api tier only).

### A-3: DC OPF with LMPs
**Fully documented.** `solve_dc_opf` in quickstart. `setting=Dict("output" => Dict("duals" =>
true))` for LMPs documented. `lam_kcl_r` key for LMP extraction listed in bus solution dict.
Minor friction: some older examples show deprecated 3-argument form.

### A-4: AC Feasibility Check
**Partially documented.** Both `solve_ac_opf` and `compute_ac_pf` documented. Warm-start
pattern (setting vm/va from DC solution) described in PF docs but exact dict key structure
not shown with worked example. `update_data!` documented but not shown in this workflow.

### A-5: SCUC (Unit Commitment)
**Undocumented gap.** SCUC is not a built-in problem type. UC binary variables, min up/down
times, startup costs not in PowerModels data model. Requires fully custom JuMP model (~250 LOC).

### A-6: SCED (Economic Dispatch)
**Partially documented.** `solve_mn_opf` and `replicate` documented. Workflow for fixing
commitment from prior SCUC and constructing time-varying load profiles requires source code
or test examples. Ramp rate constraints not in standard formulation.

### A-7: N-1 Contingency Sweep
**Partially documented.** `deepcopy` + `br_status=0` + `compute_dc_pf` loop pattern not
described in docs. Individual components documented. Users must derive the loop pattern.

### A-8: Stochastic Timeseries OPF
**Undocumented gap.** No stochastic OPF formulation. `replicate` creates temporal coupling,
not scenario branching. No scenario tree, non-anticipativity, or probability-weighted objectives.

### A-9: SCOPF
**Source code required.** SCOPF not in core PowerModels (`PowerModelsSecurityConstrained.jl`
is separate). Implementing via LODF requires: undocumented LODF formula, branch flow variable
access via `var(pm, :p)[(br_idx, f_bus, t_bus)]` tuple keys (source code only),
`make_basic_network` prerequisite (not in docstrings). See [doc-gap observation](../observations/doc-gap-expressiveness-A9_scopf_lodf_not_documented.md).

### A-10: Lossy DC OPF with LMP Decomposition
**Source code required.** `DCPLLPowerModel` listed in formulations reference but solver
requirement (Ipopt, not HiGHS -- QCQP constraints) undocumented. LMP decomposition into
energy/congestion/loss requires KKT understanding. No decomposition formula or worked example.

### A-11: Distributed Slack OPF
**Undocumented gap.** No distributed slack formulation. `calc_basic_ptdf_matrix` documented
but building distributed-slack PTDF-OPF in JuMP is entirely user-derived (~150 LOC).

### A-12: Multi-Period DCOPF with Storage
**Partially documented.** `solve_mn_opf_strg` documented by name. Storage data model partially
described. Cyclic SoC requires manual JuMP constraint injection. Solver requirement (SCIP for
MIQP complementarity) undocumented.

### Summary Table

| Test | Coverage | Source Code Needed? | GitHub/SO Needed? |
|------|----------|--------------------|--------------------|
| A-1 DCPF | Partial | Yes (branch flows) | No |
| A-2 ACPF | Partial | No (inferrable) | No |
| A-3 DCOPF+LMPs | Full | No | No |
| A-4 AC Feasibility | Partial | No (inferrable) | No |
| A-5 SCUC | Undocumented gap | N/A (not built-in) | No |
| A-6 SCED | Partial | Helpful | No |
| A-7 N-1 Contingency | Partial | No (inferrable) | No |
| A-8 Stochastic OPF | Undocumented gap | N/A (not built-in) | No |
| A-9 SCOPF | Source required | Yes | No |
| A-10 Lossy DCOPF | Source required | Yes | No |
| A-11 Distributed Slack | Undocumented gap | N/A (not built-in) | No |
| A-12 Multi-Period+Storage | Partial | Yes (solver, cyclic SoC) | No |

### Cross-Reference to Consumed Observations

- **api-friction** (10 observations): Branch flow gaps (A-1, A-2, A-4), solver incompatibilities
  (A-10 HiGHS/QCQP, A-12 HiGHS/MIQP), quadratic cost QP (A-3), baseMVA type (A-6), no graph
  library (A-7/B-2), no distributed slack (B-8)
- **doc-gaps** (2 observations): SCOPF LODF undocumented (A-9), formulation methods lack
  docstrings (B-6)
- **convergence-quality** (1 observation): compute_ac_pf no NR diagnostics (A-2)

## Implications

Core OPF and power flow (A-1 through A-4) are largely implementable from docs, with the
branch-flow post-processing gap being the most consistent friction. Advanced capabilities
(SCUC, stochastic, distributed slack) are absent from the tool. SCOPF and lossy OPF exist
but require source code reading. Documentation strengths: well-structured formulation concepts,
two-level API. Weaknesses: no worked examples for data manipulation patterns, no solver
compatibility matrix, inconsistent result dict documentation between `compute_*` and `solve_*`.

No test required GitHub issues or Stack Overflow. Where docs were insufficient, Julia source
code (readable, type-annotated) filled the gap.
