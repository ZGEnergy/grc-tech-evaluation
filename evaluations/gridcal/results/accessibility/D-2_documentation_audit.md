---
test_id: D-2
tool: gridcal
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Methodology

For each Suite A test, assessed whether the test could be completed from official documentation alone (<https://veragrid.readthedocs.io>) without reading source code, searching GitHub issues, or trial-and-error.

## Consumed Observations

- **api-friction-expressiveness-A-1**: DC PF named "Linear" not "DC" -- not documented clearly
- **api-friction-expressiveness-A-3**: CBC unsupported despite enum, GLPK not available
- **solver-issues-expressiveness-A-8**: Time-series OPF crashes with TapPhaseControl
- **workaround-needed-expressiveness-A-7**: N-M contingency requires manual loop
- **blocking-gap-extensibility-B-1**: No custom constraint API for OPF

## Per-Test Assessment

| Test | Status | From Docs Only? | Source Reading Required? | Notes |
|------|--------|-----------------|------------------------|-------|
| A-1 DCPF | pass | Partial | Yes | Power flow page shows API usage with VeraGridEngine. But "SolverType.Linear" for DCPF is not intuitive and not prominently documented. User must scan enum listing. |
| A-2 ACPF | pass | Yes | No | Power flow page has a complete example with `PowerFlowDriver`. Newton-Raphson is the default. |
| A-3 DC OPF | pass | Yes | Minimal | OPF page documents `linear_opf()` and `OptimalPowerFlowOptions`. MIP solver enum documented. |
| A-4 AC Feasibility | pass | Partial | Yes | OPF page shows "OPF verification" pattern (pass OPF results to PF driver). But the exact API to inject dispatch from OPF into PF is not obvious from docs alone. |
| A-5 SCUC | fail | Partial | Yes | UC dispatch mode is documented on OPF page. But the time-series OPF crash and lack of inter-temporal constraint enforcement are not documented. User discovers failure only at runtime. |
| A-6 SCED | fail | No | Yes | No documentation on separating UC from ED. No API to fix commitment and solve ED only. |
| A-7 Contingency | qual_pass | No | Yes | `ContingencyAnalysisDriver` is mentioned but its N-1-only limitation is not documented. N-M sweep with graph distance requires reading source to discover `build_graph()`. |
| A-8 Stochastic | fail | Partial | Yes | Time-series OPF is documented. But the TapPhaseControl crash and the lack of native stochastic formulation require source reading to diagnose. |
| A-9 SCOPF | fail | No | Yes | `consider_contingencies` option exists but documentation does not explain how it works or how to define contingencies for SCOPF. |
| A-10 Lossy DCOPF | qual_pass | Partial | Yes | `add_losses_approximation` option is in the API but not explained in docs. Loss-inclusive LMP decomposition is not documented. |
| A-11 Dist. Slack | fail | No | Yes | No documentation on distributed slack for OPF. |

## Summary Metrics

| Metric | Count |
|--------|-------|
| Tests completable from docs alone | 2 (A-2, A-3) |
| Tests partially completable from docs | 5 (A-1, A-4, A-5, A-8, A-10) |
| Tests requiring source code reading | 9 of 11 |
| Tests requiring external search (GitHub issues) | 2 (A-5, A-8) |

## Documentation Structure Assessment

- **Strengths:** API reference is auto-generated from docstrings. Power flow and OPF pages have working code examples. Import paths now consistently use `VeraGridEngine` (not old `GridCalEngine`).
- **Weaknesses:** Advanced features (SCOPF, distributed slack, loss approximation, stochastic OPF) are exposed as options but not documented. The relationship between `OpfDispatchMode`, `consider_contingencies`, `consider_ramps`, and `consider_time_up_down` options is not explained. No troubleshooting guide for common errors.
- **Gap:** No migration guide from GridCalEngine to VeraGridEngine. Documentation URLs still reference "gridcal" in some stable-branch paths.
