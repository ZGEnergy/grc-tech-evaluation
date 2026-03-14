---
test_id: D-2
tool: pandapower
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "41406d30"
---

# D-2: Documentation Audit

## Method

For each Suite A test, assessed whether it could be implemented solely from pandapower's
official documentation at pandapower.readthedocs.io (v3.4.0), without needing source code
inspection, GitHub issues, or guesswork.

## Per-Test Ratings

| Test | Description | Rating | Notes |
|------|-------------|--------|-------|
| A-1 | DCPF | Doable from docs | `rundcpp()` is documented with parameters. `res_bus`, `res_line` result DataFrames are documented. |
| A-2 | ACPF | Doable from docs | `runpp()` is thoroughly documented including algorithm selection, tolerance, init mode, distributed slack, and enforce_q_lims. |
| A-3 | DCOPF | Doable from docs | `rundcopp()` documented. Cost function creation via `create_poly_cost()` and `create_pwl_cost()` documented. Constraint specification via element DataFrame columns documented. |
| A-4 | AC Feasibility Check | Doable from docs | Combination of `rundcopp()` for dispatch + `runpp()` with `enforce_q_lims` for feasibility. Both individually documented. |
| A-5 | SCUC | Needed source code | No SCUC documentation exists because pandapower has no SCUC capability. The absence itself is not documented — users must infer it from the lack of any multi-period or unit commitment API. |
| A-6 | SCED | Needed source code | Same as A-5. No multi-period economic dispatch capability. Documentation gap is the same: no explicit statement that this is out of scope. |
| A-9 | SCOPF | Needed source code | `run_contingency()` is documented for post-hoc N-1 analysis, but no SCOPF (optimization with contingency constraints) is documented. The distinction between N-1 checking and N-1-constrained optimization is not made clear. Users must read source code to confirm SCOPF is impossible. |
| A-10 | Lossy DCOPF + LMP Decomposition | Needed source code | No documentation for lossy DC OPF or LMP decomposition. `res_bus.lam_p` exists but is not documented as an LMP. No documentation mentions energy/congestion/loss components. Required source code inspection of PYPOWER result structures. |
| A-11 | Distributed Slack OPF | Needed source code | `distributed_slack` parameter is documented for `runpp()` but NOT for `rundcopp()`/`runopp()`. The parameter is silently accepted via `**kwargs` but has no effect on OPF. Users would assume it works based on the power flow docs. |
| A-12 | Multi-period DCOPF + Storage | Needed source code | `create_storage()` is documented. `run_timeseries()` is documented. But the documentation does not explain that `run_timeseries()` runs independent single-period solves with no inter-temporal coupling. Users must read source code to discover the lack of SoC linkage. |

## Documentation Strengths

1. **Element creation API is comprehensive.** Every network element (`create_bus`,
   `create_line`, `create_gen`, etc.) has full parameter documentation with units.

2. **Standard type library is well-documented.** Line and transformer standard types with
   real-world parameters are accessible via `available_std_types()`.

3. **Power flow options are thoroughly documented.** `runpp()` documents algorithm choice,
   convergence parameters, initialization, distributed slack, Q-limit enforcement, and
   temperature-dependent modeling.

4. **Result DataFrame structure is clear.** `res_bus`, `res_line`, `res_gen` column
   definitions are documented per analysis type.

5. **Built-in network library.** `pandapower.networks` provides IEEE/MATPOWER test cases
   accessible via documented functions (`case9()`, `case39()`, etc.).

## Documentation Gaps

1. **No explicit scope statement.** The documentation never states what pandapower
   *cannot* do (no SCUC, no SCOPF, no multi-period OPF). Users must infer limitations
   from the absence of features.

2. **PYPOWER userfcn mechanism is undocumented.** The callback system for injecting
   custom OPF constraints exists (used internally for dclines) but is not mentioned
   in pandapower's documentation. Users must read PYPOWER source code.
   (See observation: doc-gaps-extensibility-B-1)

3. **0-indexed bus mapping not documented.** The `from_mpc` converter remaps MATPOWER
   1-indexed bus numbers to 0-indexed pandas indices without documentation.
   (See observation: api-friction-expressiveness-A-3)

4. **`**kwargs` silently absorbs invalid parameters.** `rundcopp()` and `runopp()` accept
   arbitrary keyword arguments via `**kwargs` without validation. `distributed_slack=True`
   is accepted without error but has no effect.
   (See observation: api-friction-expressiveness-A-11)

5. **OPF convergence properties poorly documented.** The docs note that PYPOWER OPF
   "does not have the best convergence properties" but provide no guidance on
   troubleshooting or parameter tuning.

6. **LMP / shadow price interpretation absent.** `res_bus.lam_p` is produced by OPF
   but not documented as a locational marginal price or explained in economic terms.

## Summary

| Category | Count |
|----------|-------|
| Doable from docs | 3 of 10 (A-1, A-2, A-3) |
| Needed source code | 7 of 10 (A-4 borderline, A-5, A-6, A-9, A-10, A-11, A-12) |
| Needed GitHub issues | 0 |
| Guessing required | 0 |

The documentation is strong for basic power flow (AC/DC) and simple OPF, but has
significant gaps for advanced optimization features. The biggest documentation issue
is the absence of explicit scope boundaries — users cannot distinguish "not yet
documented" from "not implemented" without reading source code.
