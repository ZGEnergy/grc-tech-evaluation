---
test_id: G-FNM-4
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: cea622c5
status: informational
workaround_class: null
blocked_by: null
ingestion_path: matpower
relaxation_level_achieved: "infeasible"
dcpf_init_mean_deg: 65.597048
dcpf_init_max_abs_deg: 536.925222
acpf_timeout_minutes: 30
wall_clock_seconds: 137.583
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 276
solver: Newton-Raphson (PyPSA built-in)
timestamp: 2026-03-24T00:00:00Z
---

# G-FNM-4: ACPF Convergence -- DCPF Warm-Start + Progressive Relaxation

## Result: INFORMATIONAL

PyPSA's Newton-Raphson ACPF solver did not converge at any relaxation level
(0%, 10%, 20%) on the ~28,000-bus FNM main island. This is consistent with
MATPOWER 8.1's failure on the same network. The FNM is a planning model with no
solved voltage profile.

## Approach

1. **Loaded via shared matpower_loader:** Used `matpower_loader.load_pypsa()` which
   applies branch status, transformer susceptance, and gencost patches. The branch
   status patch correctly deactivates 74 inactive branches (MATPOWER fallback path
   due to G-FNM-1 failure).

2. **Step 1 -- DCPF warm start:** Solved DCPF via `n.lpf()` to obtain voltage angles
   (15.1s). Extracted bus voltage angles from the DCPF solution. Voltage magnitudes
   initialized at 1.0 p.u. (flat start for VM, DC warm start for VA).

   - DCPF init mean angle: 65.60 degrees
   - DCPF init max absolute angle: 536.93 degrees
   - DCPF angle range: [-536.93, 385.47] degrees

3. **Steps 2-4 -- Progressive relaxation:** Attempted ACPF via `n.pf()` at three
   relaxation levels:
   - **0% relaxation (Step 2):** Nominal thermal limits. Failed -- SuperLU
     factorization error (38.9s).
   - **10% relaxation (Step 3):** `s_nom * 1.10`. Failed -- SuperLU factorization
     error (40.1s).
   - **20% relaxation (Step 4):** `s_nom * 1.20`. Failed -- SuperLU factorization
     error (39.8s).

   PyPSA's `n.pf()` uses its own Newton-Raphson implementation with SuperLU for
   sparse matrix factorization. It does not use Ipopt. The solver has a fixed
   iteration limit (default 70 NR iterations).

## Output

### DCPF Warm-Start Statistics

| Metric | Value |
|--------|-------|
| DCPF solve time | 15.1s |
| Mean angle (degrees) | 65.60 |
| Max absolute angle (degrees) | 536.93 |
| Angle range (degrees) | [-536.93, 385.47] |
| VM initialization | 1.0 p.u. (flat) |

### Convergence Results

| Relaxation Level | Converged | Error Type | Solve Time |
|-----------------|-----------|------------|------------|
| 0% (nominal) | No | SuperLU factorization failure | 38.9s |
| 10% | No | SuperLU factorization failure | 40.1s |
| 20% | No | SuperLU factorization failure | 39.8s |

**Relaxation level achieved:** infeasible

### Error Analysis

All three attempts encountered a SuperLU sparse matrix factorization failure
(`RuntimeError: failed to factorize matrix`). This indicates structural issues in
the network model rather than numerical convergence difficulties:

- The network has a 9,981 MW (6.0%) generation-load imbalance
- Zero-impedance branches or degenerate transformer configurations may create
  singularity in the admittance matrix
- The `overwrite_zero_s_nom=100000.0` parameter prevents zero-rating issues but
  does not address impedance-related singularity
- The large DCPF angle spread (max abs 536.9 degrees) suggests electrically distant
  buses or very long radial paths, further complicating the NR initialization

### MATPOWER Comparison

| Method | MATPOWER 8.1 | PyPSA 1.1.2 |
|--------|-------------|-------------|
| Newton-Raphson (flat start) | Failed (all variants) | Failed (SuperLU) |
| Fast-Decoupled (FDXB/FDBX) | Failed (1000 iter) | N/A (not available) |
| Continuation PF | Reached ~30% load | N/A (not available) |
| DC warm start + NR | N/A | Failed (SuperLU) |
| Progressive relaxation | N/A | Failed at all levels |

Neither tool converges on this network. The FNM planning model lacks a feasible
AC operating point at full load. [solver-specific: SuperLU factorization failure
on ill-conditioned admittance matrix]

### Network Characteristics

| Metric | Value |
|--------|-------|
| Buses | ~28,000 |
| Lines | 23,125 (69 inactive) |
| Transformers | 9,481 (5 inactive) |
| Generators | ~5,700 |
| Loads | 8,624 |
| baseMVA | 100.0 |

## Workarounds

- **What:** MATPOWER fallback path via shared `matpower_loader.load_pypsa()`
- **Why:** G-FNM-1 failed -- PyPSA cannot parse PSS/E intermediate CSV format
- **Durability:** stable -- uses documented public API (matpowercaseframes +
  import_from_pypower_ppc)
- **Grade impact:** None for this informational test

## Timing

- **Wall-clock:** 137.6s (total across all attempts)
- **DCPF warm-start:** 15.1s
- **ACPF attempts:** 38.9s + 40.1s + 39.8s = 118.8s
- **Timing source:** measured
- **Peak memory:** not measured (tracemalloc interrupted by SuperLU exception)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_4_acpf_convergence.py`
