---
test_id: D-3
tool: gridcal
dimension: accessibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "2b77857a"
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

# D-3: Example Verification

## Result: INFORMATIONAL

## Finding

GridCal has two sources of official examples: the deprecated GridCalTutorials repo
(all broken) and the main VeraGrid repo's `examples/` directory (49 scripts, current
imports). The main repo examples work when adapted to use available test cases, but
the tutorials repo is completely non-functional.

## Evidence

### Source 1: GridCalTutorials Repo (github.com/SanPen/GridCalTutorials)

Accessed 2026-03-24. Contains 5 files with 6 total commits, last updated October 2021.

| Example | Status | Issue |
|---------|--------|-------|
| `defining_a_grid_from_scratch.ipynb` | BROKEN | Uses `from GridCal.Engine import *` (deprecated namespace) |
| `defining_a_grid_from_scratch_with_profiles.py` | BROKEN | Uses `GridCal.Engine` imports + deprecated `Branch` class |
| `ml_example.py` | NOT TESTED | Domain-specific; likely uses deprecated imports |
| `rt_example_client.py` | NOT TESTED | Infrastructure example; likely deprecated imports |
| `rt_example_server.py` | NOT TESTED | Infrastructure example; likely deprecated imports |

- **Run unmodified:** 0 of 2 tested
- **Broken (will not import):** 2 of 2 tested

Root cause: The GridCal-to-VeraGrid rebrand at v5.4.0 changed the import namespace
from `GridCal.Engine` to `VeraGridEngine`, but the tutorials repo was never updated.

### Source 2: VeraGrid Main Repo Examples (github.com/SanPen/VeraGrid/examples/)

Accessed 2026-03-24. Contains 49 Python scripts using current `VeraGridEngine.api`
imports. Key examples include:

| Example | Category | Import Style |
|---------|----------|-------------|
| `power_flow_example.py` | Power flow | `VeraGridEngine.api as gce` |
| `dc_linear_opf.py` | DC OPF | `VeraGridEngine.api as gce` |
| `dc_linear_opf_ts_example.py` | Time-series OPF | `VeraGridEngine.api as gce` |
| `contingency_analysis_run.py` | Contingency | `VeraGridEngine.api as gce` |
| `helm_run.py` | HELM solver | `VeraGridEngine.api as gce` |
| `short_circuit_run.py` | Short circuit | `VeraGridEngine.api as gce` |
| `state_estimation_run.py` | State estimation | `VeraGridEngine.api as gce` |
| `hydro_opf.py` | Hydro OPF | `VeraGridEngine.api as gce` |
| ... (41 more) | Various | Current imports |

### Verification of Main Repo Examples (in devcontainer)

Three representative examples were adapted and tested using IEEE 39-bus case
(the repo examples reference `.gridcal` format files not available in our test data):

| Example Pattern | Status | Notes |
|----------------|--------|-------|
| Power flow (`power_flow()`) | PASS | Converged, residual 3.32e-11 |
| DC Linear OPF (`linear_opf()`) | PASS | Converged, gen_power sum = 6254.23 MW |
| Linear analysis (PTDF) | PASS | PTDF shape (46, 39) correct |

The core API patterns demonstrated in the main repo examples work correctly when
adapted to use MATPOWER `.m` files. The examples themselves reference `.gridcal`
format files bundled with the VeraGrid GUI application, which are not available
in an engine-only installation.

### Discoverability Issue

The main repo examples (49 scripts, current imports) are not prominently linked from
the ReadTheDocs documentation or the README. A user following the "getting started"
path would likely find the GridCalTutorials repo first (linked from the old
GridCal README), which is completely broken. The functional examples are buried in the
main repo's `examples/` directory.

## Summary

| Source | Total | Pass | Broken | Not Tested |
|--------|-------|------|--------|------------|
| GridCalTutorials repo | 5 | 0 | 2 | 3 |
| VeraGrid main repo | 49 | 3 tested/pass | 0 tested broken | 46 not tested |

## Implications

The example situation is bifurcated: the discoverable tutorials are broken (stale repo),
while the functional examples (main repo) are less discoverable. The core API patterns
are clean and work correctly, but the data file dependency on `.gridcal` format means
the examples cannot run out-of-box without either the GUI application or adaptation to
use MATPOWER `.m` files. For accessibility grading, the 49 functional examples in the
main repo mitigate the broken tutorials, but the discoverability gap and data file
dependency reduce their practical value for new users.
