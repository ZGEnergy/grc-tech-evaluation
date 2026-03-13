---
test_id: G-FNM-4
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v9
skill_version: v1
test_hash: 04ad55d9
status: informational
workaround_class: stable
blocked_by: null
wall_clock_seconds: 55.801
timing_source: measured
peak_memory_mb: 16289.4
convergence_residual: null
convergence_iterations: 70
loc: 288
solver: Newton-Raphson (PyPSA built-in)
timestamp: 2026-03-11T00:00:00Z
---

# G-FNM-4: ACPF Convergence

## Result: INFORMATIONAL

## Finding

PyPSA's Newton-Raphson AC power flow did not converge on the ERCOT FNM main island
(27,862 buses, 32,532 active branches). This is consistent with MATPOWER 8.1, which
also fails on this network (voltage collapse at ~30% load). The failure mode is a
singular Jacobian matrix, causing NaN propagation during Newton-Raphson iterations.
Non-convergence is the expected outcome; convergence would have been a positive finding.

## Approach

1. Parsed the pre-cleaned MATPOWER `.m` case file (`fnm_main_island.m`) using a
   regex-based parser (same approach as G-FNM-3; `.mat` is Octave text format,
   not scipy-compatible).
2. Imported into PyPSA via `import_from_pypower_ppc()`.
3. Ran `n.pf()` (Newton-Raphson AC power flow) with default settings and flat start
   initialization (all VM=1.0, VA=0.0 from the planning model).
4. Recorded convergence status, iteration count, residual, timing, and memory.

No custom continuation methods, homotopy, or warm-start fallbacks were attempted.
The test used PyPSA's built-in solver with default parameters only.

## Output

| Metric | Value |
|--------|-------|
| Converged | No |
| Solver | Newton-Raphson (PyPSA built-in) |
| Iterations | 70 (hit max limit) |
| Final residual | NaN (singular Jacobian) |
| Failure mode | `MatrixRankWarning: Matrix is exactly singular` |
| Wall-clock (solve) | 55.299 s |
| Wall-clock (total) | 55.801 s |
| Peak memory | 16,289.4 MB (~16.3 GB) |

### Network imported

| Component | Count |
|-----------|-------|
| Buses | 27,862 |
| Lines | 23,125 |
| Transformers | 9,481 |
| Generators | 5,741 |
| Loads | 8,624 |

### Failure Analysis

The ERCOT FNM is a planning model with flat-start initialization (all VM=1.0, VA=0.0,
Vg=1.0). It has no solved voltage profile. Additional complicating factors:

- **86 electrical islands** in the full network (main island extracted for this test)
- **541 series capacitors** (negative reactance branches, coerced to |X| in cleaning)
- **~9,500 transformers** with varying tap ratios
- **No voltage solution** exists as starting point

The singular Jacobian indicates the network topology/parameters create a degenerate
system that standard Newton-Raphson cannot initialize from flat start. MATPOWER's
more advanced solvers (continuation power flow, FDXB/FDBX with 1000 iterations) also
failed, reaching only ~30% of full load before voltage collapse.

### Comparison with MATPOWER

| Aspect | MATPOWER 8.1 | PyPSA 1.1.2 |
|--------|-------------|-------------|
| Converged | No | No |
| Methods tried | NR, FDXB/FDBX, CPF | NR (default only) |
| Max load reached | ~30% (via CPF) | N/A (full load attempt) |
| Failure mode | Voltage collapse | Singular Jacobian / NaN |
| Root cause | Same: flat-start planning model with no solved voltage profile |

## Workarounds

- **What:** Parsed MATPOWER `.m` file with regex-based parser
- **Why:** The `.mat` file is Octave text format (not scipy-compatible) and PyPSA has
  no native MATPOWER reader
- **Durability:** stable
- **Grade impact:** None (ingestion-related, not convergence-related)
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 55.801 s
- **Timing source:** measured
- **Peak memory:** 16,289.4 MB (~16.3 GB)
- **Solver iterations:** 70 (max limit hit)
- **Convergence residual:** NaN (singular Jacobian)
- **CPU cores used:** 1 (single-threaded NR)

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_4_acpf_convergence.py`
