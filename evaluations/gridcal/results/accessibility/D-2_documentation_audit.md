---
test_id: D-2
tool: gridcal
dimension: accessibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "779bdb76"
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
timestamp: "2026-03-24T12:00:00Z"
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Finding

Only 2 of 10 Suite A tests were completable from official documentation alone. The
remaining 8 required source code reading, runtime introspection, or API guessing.
Documentation has improved since the rebrand (ReadTheDocs now covers v5.6.31 with
auto-generated API reference), but OPF workflows, time-series profiles, and advanced
features remain underdocumented.

## Evidence

### Documentation Sources Reviewed

1. **veragrid.readthedocs.io** (accessed 2026-03-24) — Official documentation now
   covers v5.6.31 (up from v5.0.2 in earlier audit). Contains theory sections, analysis
   descriptions, auto-generated API index with thousands of entries. Includes sections
   on power flow, OPF, contingency analysis, state estimation, and more. Some tutorial
   content exists (e.g., "Power Flow on the 5-Node Example Grid").

2. **GitHub VeraGrid repo** (github.com/SanPen/VeraGrid, accessed 2026-03-24) — Contains
   49 Python example scripts in `examples/` directory using current `VeraGridEngine.api`
   imports. Covers power flow, DC linear OPF, time-series OPF, contingency analysis,
   short circuit, state estimation, and more.

3. **GridCalTutorials repo** (github.com/SanPen/GridCalTutorials, accessed 2026-03-24) —
   5 files, 6 commits total, last updated October 2021. All use deprecated
   `GridCal.Engine` imports. Effectively unmaintained and non-functional with current
   package.

4. **Source code docstrings** — Constructor signatures are typed but most methods lack
   docstrings explaining behavior, parameter semantics, or return value structure.

### Suite A Test Completability from Documentation

| Test | From Docs? | Source Used | Gap Description |
|------|-----------|-------------|-----------------|
| A-1 (DCPF) | Yes | README + readthedocs + examples | `SolverType.Linear` documented; `open_file()` has examples |
| A-2 (ACPF) | Yes | readthedocs + examples | `SolverType.NR` well-known; `PowerFlowOptions` discoverable |
| A-3 (DCOPF) | No | Source code | `OptimalPowerFlowOptions` uses `solver=` not `solver_type=` -- naming inconsistency causes TypeError. Soft constraint behavior undocumented |
| A-4 (AC feasibility) | Partial | Docs + source | DCOPF-to-ACPF chaining undocumented. Generator dispatch injection via API exploration |
| A-5 (SCUC) | No | Source code | `OpfDispatchMode.UnitCommitment` exists but time profile API (`set_time_profile` accepting unix timestamps) undocumented. Profile system requires source reading |
| A-6 (SCED) | No | Source code | No SCED abstraction. UC-ED two-stage workflow via Pmax/Pmin profiles entirely undocumented |
| A-9 (SCOPF) | No | Source code | `consider_contingencies` option and contingency-constrained OPF workflow undocumented |
| A-10 (Lossy DCOPF) | No | Source code | `add_losses_approximation` parameter not documented. Formula and limitations unknown without source reading |
| A-11 (Distributed slack) | No | Source code | `distributed_slack` option exists on `PowerFlowOptions` but silently ignored by OPF formulation (hardcoded `False` in `linear_opf_ts.py` line 3022). No warning |
| A-12 (Multi-period storage) | No | Source code | Battery device API discoverable but multi-period OPF workflow undocumented. Energy balance sign behavior found only through result validation |

### Summary Counts

- **Completable from docs alone:** 2 of 10 (A-1, A-2)
- **Partially from docs:** 1 of 10 (A-4)
- **Required source code / introspection:** 7 of 10

### Key Documentation Gaps

1. **Improved but still lagging:** ReadTheDocs now covers v5.6.31 with auto-generated
   API index, a significant improvement over v5.0.2. However, the auto-generated
   reference lacks usage examples and semantic documentation for most methods.

2. **VeraGrid examples repo (49 scripts):** The main VeraGrid GitHub repo contains
   49 example scripts using current `VeraGridEngine.api` imports. These cover basic
   power flow and OPF but not the advanced workflows tested in Suite A (SCUC, SCED,
   SCOPF, lossy DCOPF, distributed slack, multi-period storage).

3. **Naming inconsistencies:** `PowerFlowOptions.solver_type=` vs
   `OptimalPowerFlowOptions.solver=`. Not documented; causes TypeErrors.

4. **OPF options undocumented:** `add_losses_approximation`, `consider_contingencies`,
   `OpfDispatchMode` variants, `distributed_slack` behavior in OPF -- none documented
   with usage examples. [tool-specific]

5. **Time profile API:** `set_time_profile()` accepts numpy int64 unix timestamps, not
   datetime objects. Undocumented; other tools accept datetime directly. [tool-specific]

6. **Stale tutorials repo:** GridCalTutorials uses `GridCal.Engine` imports (broken).
   The main repo examples are current but not prominently linked from documentation.

7. **Silent option ignoring:** The `distributed_slack` flag is accepted by OPF options
   but silently ignored. No warning, error, or documentation indicates this limitation.
   [tool-specific]

## Consumed Observations

- `doc-gaps-expressiveness-A-3_dcopf`: OPF parameter naming inconsistency, soft constraint semantics undocumented
- `doc-gaps-expressiveness-A-6_sced`: No SCED workflow documentation
- `doc-gaps-extensibility-B-2_graph_access`: `build_graph()` return type undocumented
- `api-friction-expressiveness-A-5_scuc`: Time profile API requires unix timestamps
- `api-friction-expressiveness-A-11_distributed_slack_opf`: Distributed slack silently ignored by OPF
- `api-friction-extensibility-B-1_custom_constraints`: No public API for custom OPF constraints
- `unit-mismatch-expressiveness-A-3_dcopf`: Generator names empty in MATPOWER import
- `unit-mismatch-expressiveness-A-10_lossy_dcopf_lmp`: Loss formula uses rating instead of flow

## Implications

GridCal's documentation has improved significantly with the auto-generated API index
and the 49 example scripts in the main repo. However, for the power-system domain
workflows tested in Suite A, only the simplest analyses (DCPF, ACPF) are completable
from documentation. All OPF-related workflows require source code reading, which is
a significant accessibility barrier. The silent ignoring of configuration flags
(distributed_slack in OPF) is particularly concerning because it produces incorrect
results without any diagnostic signal.
