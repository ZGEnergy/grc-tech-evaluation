---
test_id: G-FNM-4
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: cea622c5
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 163.8
timing_source: measured
peak_memory_mb: 16289.3
convergence_residual: null
convergence_iterations: 70
loc: 276
solver: Newton-Raphson (PyPSA built-in)
input_path: matpower
timestamp: 2026-03-13T00:00:00Z
---

# G-FNM-4: ACPF convergence -- DCPF warm-start + progressive relaxation on LARGE

## Result: INFORMATIONAL

PyPSA's Newton-Raphson ACPF solver did not converge at any relaxation level
(0%, 10%, 20%) on the 27,862-bus FNM main island. This is consistent with
MATPOWER 8.1's failure on the same network. The FNM is a planning model with no
solved voltage profile.

## Approach

1. **DCPF warm start:** Solved DCPF via `n.lpf()` to obtain voltage angles (14.3s).
   Used DC angles as initial guess for ACPF. Voltage magnitudes initialized at 1.0 p.u.
   (flat start for VM, DC warm start for VA).

2. **Progressive relaxation:** Attempted ACPF via `n.pf()` at three relaxation levels:
   - **0% relaxation:** Nominal thermal limits. Failed after 70 iterations (48.9s).
     Singular Jacobian matrix encountered.
   - **10% relaxation:** Thermal limits multiplied by 1.1. Failed after 70 iterations
     (52.5s). Singular Jacobian matrix.
   - **20% relaxation:** Thermal limits multiplied by 1.2. Failed after 54 iterations
     (46.5s). Singular Jacobian matrix.

   Note: PyPSA's `n.pf()` uses Newton-Raphson with a fixed iteration limit (default 70).
   The solver does not use Ipopt (as specified in the test definition) because PyPSA's
   AC power flow is implemented as a built-in Newton-Raphson solver, not as an
   optimization problem sent to an external NLP solver.

## Output

### Convergence Results

| Relaxation Level | Converged | Iterations | Final Residual | Solve Time |
|-----------------|-----------|------------|----------------|------------|
| 0% (nominal) | No | 70 | NaN (singular) | 48.9s |
| 10% | No | 70 | NaN (singular) | 52.5s |
| 20% | No | 54 | NaN (singular) | 46.5s |

**Relaxation level achieved:** infeasible

### Singular Jacobian Analysis

All three attempts encountered a singular Jacobian matrix (`MatrixRankWarning:
Matrix is exactly singular`). This indicates structural issues in the network model
rather than numerical convergence difficulties:

- The network has a 9,981 MW (6.0%) generation-load imbalance
- Zero-impedance branches or degenerate transformer configurations may create
  singularity in the admittance matrix
- The `overwrite_zero_s_nom=100000.0` parameter prevents zero-rating issues but
  does not address impedance-related singularity

### MATPOWER Comparison

| Method | MATPOWER 8.1 | PyPSA 1.1.2 |
|--------|-------------|-------------|
| Newton-Raphson (flat start) | Failed (all variants) | Failed (singular) |
| Fast-Decoupled (FDXB/FDBX) | Failed (1000 iter) | N/A (not available) |
| Continuation PF | Reached ~30% load | N/A (not available) |
| DC warm start + NR | N/A | Failed (singular) |
| Progressive relaxation | N/A | Failed at all levels |

Neither tool converges on this network. The FNM planning model lacks a feasible
AC operating point at full load.

### Network Characteristics

| Metric | Value |
|--------|-------|
| Buses | 27,862 |
| Lines | 23,125 |
| Transformers | 9,481 |
| Generators | 5,741 |
| Loads | 8,624 |
| baseMVA | 100.0 |
| Generation | 155,511 MW |
| Load | 165,492 MW |
| Imbalance | -9,981 MW (6.0%) |

## Workarounds

- **What:** MATPOWER fallback path (same as G-FNM-3)
- **Why:** G-FNM-1 failed -- PyPSA cannot parse PSS/E intermediate CSV format

## Timing

- **Wall-clock:** 163.8s (total across all attempts)
- **DCPF warm-start:** 14.3s
- **ACPF attempts:** 48.9s + 52.5s + 46.5s = 147.9s
- **Timing source:** measured
- **Peak memory:** 16,289 MB per attempt
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_4_acpf_convergence.py`
