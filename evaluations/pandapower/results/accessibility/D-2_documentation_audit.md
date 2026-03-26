---
test_id: D-2
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 41406d30
status: informational
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
timestamp: "2026-03-24T00:00:00Z"
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Finding

3 of 10 Suite A tests are fully implementable from official documentation alone.
The remaining 7 require source code inspection, primarily because pandapower lacks
explicit scope boundaries — users cannot distinguish "not yet documented" from
"not implemented" without reading source code.

## Evidence

### Method

For each Suite A test, assessed whether it could be implemented solely from pandapower's
official documentation at pandapower.readthedocs.io (v3.4.0), without needing source code
inspection, GitHub issues, or guesswork. Access date: 2026-03-24.

### Per-Test Ratings

| Test | Description | Rating | Notes |
|------|-------------|--------|-------|
| A-1 | DCPF | Doable from docs | `rundcpp()` documented with parameters. `res_bus`, `res_line` result DataFrames documented. |
| A-2 | ACPF | Doable from docs | `runpp()` thoroughly documented including algorithm selection, tolerance, init mode, distributed slack, and enforce_q_lims. |
| A-3 | DCOPF | Doable from docs | `rundcopp()` documented. Cost function creation via `create_poly_cost()` and `create_pwl_cost()` documented. |
| A-4 | AC Feasibility | Needed source code | Combination of `rundcopp()` + `runpp()` each individually documented, but the workflow connecting them is not. Borderline. |
| A-5 | SCUC | Needed source code | No SCUC capability exists. Documentation never explicitly states this is out of scope. |
| A-6 | SCED | Needed source code | No multi-period economic dispatch capability. Same gap as A-5. |
| A-9 | SCOPF | Needed source code | `run_contingency()` documented for post-hoc N-1 analysis, but no SCOPF (optimization with contingency constraints) documented. Distinction between N-1 checking and N-1-constrained optimization not made clear. |
| A-10 | Lossy DCOPF + LMP Decomposition | Needed source code | No documentation for lossy DC OPF or LMP decomposition. `res_bus.lam_p` produced by OPF but not documented as an LMP. Required source code inspection of PYPOWER result structures. |
| A-11 | Distributed Slack OPF | Needed source code | `distributed_slack` parameter documented for `runpp()` but NOT for `rundcopp()`/`runopp()`. Parameter silently accepted via `**kwargs` but has no effect on OPF. See [observation](../observations/api-friction-expressiveness-A-11_distributed_slack_opf.md). |
| A-12 | Multi-period DCOPF + Storage | Needed source code | `create_storage()` and `run_timeseries()` documented, but documentation does not explain that `run_timeseries()` runs independent single-period solves with no inter-temporal coupling. |

### Documentation Strengths

1. **Element creation API is comprehensive.** Every network element (`create_bus`, `create_line`,
   `create_gen`, etc.) has full parameter documentation with units.
2. **Standard type library is well-documented.** Line and transformer standard types with
   real-world parameters accessible via `available_std_types()`.
3. **Power flow options are thoroughly documented.** `runpp()` documents algorithm choice,
   convergence parameters, initialization, distributed slack, Q-limit enforcement, and
   temperature-dependent modeling.
4. **Result DataFrame structure is clear.** `res_bus`, `res_line`, `res_gen` column definitions
   are documented per analysis type.
5. **Built-in network library.** `pandapower.networks` provides IEEE/MATPOWER test cases
   accessible via documented functions.

### Documentation Gaps

1. **No explicit scope statement.** The documentation never states what pandapower *cannot* do
   (no SCUC, no SCOPF, no multi-period OPF). Users must infer limitations from the absence
   of features.
2. **PYPOWER userfcn mechanism undocumented.** The callback system for injecting custom OPF
   constraints exists (used internally for dclines) but is not in pandapower's documentation.
   See [observation](../observations/doc-gaps-extensibility-B-1_custom_constraints.md).
3. **0-indexed bus mapping not documented.** The `from_mpc` converter remaps MATPOWER 1-indexed
   bus numbers to 0-indexed pandas indices without documentation.
   See [observation](../observations/api-friction-expressiveness-A-3_dcopf.md).
4. **`**kwargs` silently absorbs invalid parameters.** `rundcopp()` and `runopp()` accept
   arbitrary keyword arguments without validation. `distributed_slack=True` accepted without
   error but has no effect.
5. **LMP / shadow price interpretation absent.** `res_bus.lam_p` produced by OPF but not
   documented as a locational marginal price or explained in economic terms.

### Summary Statistics

| Category | Count |
|----------|-------|
| Doable from docs | 3 of 10 (A-1, A-2, A-3) |
| Needed source code | 7 of 10 |
| Needed GitHub issues | 0 |
| Guessing required | 0 |

## Implications

Documentation is strong for core power flow and basic OPF operations but has significant gaps
for advanced optimization features. The biggest documentation issue is the absence of explicit
scope boundaries — users cannot distinguish "not yet documented" from "not implemented" without
reading source code. This is a recurring pattern in academic-origin tools where documentation
grows organically around implemented features.
