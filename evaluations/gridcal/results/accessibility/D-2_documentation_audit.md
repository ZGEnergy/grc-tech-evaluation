---
test_id: D-2
tool: gridcal
dimension: accessibility
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "779bdb76"
timestamp: "2026-03-13T18:00:00Z"
---

# D-2: Documentation Audit

## Documentation Sources Reviewed

1. **veragrid.readthedocs.io** — Official documentation (covers up to v5.0.2, installed
   version is v5.6.28). Contains theory sections, analysis descriptions, and changelog
   through v5.0.2. API reference pages return 404 for VeraGridEngine-specific docs.
2. **GitHub README** (github.com/SanPen/VeraGrid) — Installation instructions, feature
   list, file format support. Uses `VeraGridEngine` naming. No API usage examples.
3. **GridCalTutorials repo** (github.com/SanPen/GridCalTutorials) — 5 files including
   1 Jupyter notebook and 4 Python scripts. All use the old `GridCal.Engine` import
   namespace, not `VeraGridEngine`.
4. **Source code docstrings** — Constructor signatures are typed but most methods lack
   docstrings explaining behavior, parameter semantics, or return value structure.

## Suite A Test Completability from Documentation

| Test | Completable from Docs? | Documentation Source Used | Gap Description |
|------|----------------------|--------------------------|-----------------|
| A-1 (DCPF) | Yes | README + readthedocs theory | `SolverType.Linear` for DC is documented in theory section. `open_file()` is documented. |
| A-2 (ACPF) | Yes | readthedocs theory + README | `SolverType.NR` is well-known. `PowerFlowOptions` constructor is discoverable. |
| A-3 (DCOPF) | No | Source code required | `OptimalPowerFlowOptions` uses `solver=` not `solver_type=` — naming inconsistency requires runtime introspection. `overloads` result attribute semantics undocumented. |
| A-4 (AC feasibility) | Partial | Docs + source | Chaining DCOPF dispatch to ACPF is undocumented. Generator dispatch injection pattern discovered via API exploration. |
| A-5 (SCUC) | No | Source code required | `OpfDispatchMode.UnitCommitment` exists but the time profile API (`set_time_profile` accepting unix timestamps) is undocumented. Profile system (`Pmax_prof`, `Cost_prof`) requires source reading. |
| A-6 (SCED) | No | Source code required | No SCED abstraction. Two-stage UC-ED workflow via Pmax/Pmin profile manipulation is entirely undocumented. |
| A-9 (SCOPF) | No | Source code required | `ContingencyAnalysisDriver` is mentioned in readthedocs but API for combining contingency analysis with OPF (`consider_contingencies` option) is undocumented. |
| A-10 (Lossy DCOPF) | No | Source code required | `add_losses_approximation` parameter is not documented anywhere. Its behavior (linearized loss factor using branch rating) was discovered only through source code reading and result inspection. |
| A-11 (Distributed slack) | No | Source code required | `distributed_slack` option exists on `PowerFlowOptions` but is silently ignored by the OPF formulation (hardcoded False in `linear_opf_ts.py`). No documentation warns of this. |
| A-12 (Multi-period storage) | No | Source code required | Battery device API is discoverable but the multi-period OPF workflow (time series driver, profile setup, Battery configuration) is undocumented. The energy balance sign bug was found only through result validation. |

## Summary

- **Completable from docs alone:** 2 of 10 (A-1, A-2)
- **Partially from docs:** 1 of 10 (A-4)
- **Required source code / introspection:** 7 of 10

## Key Documentation Gaps

1. **Version lag:** ReadTheDocs covers v5.0.2; installed version is v5.6.28. Six major
   version increments of API changes are undocumented.
2. **API reference missing:** No auto-generated API docs for class constructors, method
   signatures, or return types. Users must use `help()`, `inspect.signature()`, or read
   source code.
3. **Naming inconsistencies:** `PowerFlowOptions.solver_type=` vs
   `OptimalPowerFlowOptions.solver=`. Not documented; causes TypeErrors on first attempt.
4. **OPF options undocumented:** `add_losses_approximation`, `consider_contingencies`,
   `OpfDispatchMode` variants, `distributed_slack` behavior in OPF context — none
   documented.
5. **Time profile API:** `set_time_profile()` accepts numpy int64 unix timestamps, not
   datetime objects. Undocumented; other tools accept datetime directly.
6. **Tutorials use deprecated imports:** All GridCalTutorials examples use `GridCal.Engine`
   imports which no longer work with the `VeraGridEngine` package.
7. **Silent option ignoring:** The `distributed_slack` flag is accepted by OPF options but
   silently ignored. No warning, error, or documentation indicates this limitation.

## Consumed Observations

- `doc-gaps-expressiveness-A-3_dcopf`: OPF parameter naming inconsistency, overloads semantics
- `doc-gaps-expressiveness-A-6_sced`: No SCED workflow documentation
- `doc-gaps-extensibility-B-2_graph_access`: `build_graph()` node type undocumented
- `api-friction-expressiveness-A-5_scuc`: Time profile API requires unix timestamps
- `api-friction-expressiveness-A-11_distributed_slack_opf`: Distributed slack silently ignored by OPF
- `unit-mismatch-expressiveness-A-3_dcopf`: Generator names empty in MATPOWER import
