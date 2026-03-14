---
test_id: G-FNM-4
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "4aa892c7"
status: informational
input_path: matpower
workaround_class: null
blocked_by: null
wall_clock_seconds: 65.0
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: 100
loc: 175
solver: "MATPOWER NR (built-in)"
timestamp: "2026-03-14T00:00:00Z"
---

# G-FNM-4: ACPF convergence test with DCPF warm-start and progressive relaxation

## Result: INFORMATIONAL

## Approach

Loaded the pre-cleaned FNM main island case from the MATPOWER fallback path
(`data/fnm/reference/cleaned/fnm_main_island.mat`).

**Step 1 -- DCPF warm-start:** Solved DCPF using `rundcpf()` to obtain bus
voltage angles for warm-starting the ACPF solver. DCPF converged in 0.167s.

**Step 2 -- ACPF at 0% relaxation:** Initialized `VM = 1.0` (flat voltage
magnitude) and `VA = DCPF angles` (warm-start). Used MATPOWER's built-in
Newton-Raphson solver (`pf.alg = 'NR'`, `pf.nr.max_it = 100`,
`pf.tol = 1e-8`). RATE_A at nominal values.

**Step 3 -- ACPF at 10% relaxation:** Same initialization, `RATE_A * 1.10`.

**Step 4 -- ACPF at 20% relaxation:** Same initialization, `RATE_A * 1.20`.

## Output

### DCPF Warm-Start

| Metric | Value |
|--------|-------|
| DCPF success | yes |
| DCPF wall clock | 0.167 s |
| dcpf_init_mean_deg | 209.5004 |
| dcpf_init_max_abs_deg | 536.9252 |

### ACPF Progressive Relaxation

| Step | Relaxation | Converged | Wall Clock | Failure Mode |
|------|------------|-----------|------------|--------------|
| 2 | 0% | No | 21.750 s | Singular Jacobian (rcond ~ 1.86e-17) |
| 3 | 10% | No | 21.671 s | Singular Jacobian (rcond ~ 1.89e-17) |
| 4 | 20% | No | 21.608 s | Singular Jacobian (rcond ~ 1.98e-17) |

**relaxation_level_achieved: infeasible**

### Failure Analysis

The Newton-Raphson solver encounters a singular Jacobian matrix at every
iteration across all three relaxation levels. The `rcond` values (~1.9e-17)
indicate near-machine-epsilon conditioning, meaning the linearized power
flow equations have no unique solution at the current operating point.

This is expected behavior for the FNM network for several reasons:

1. **Network topology:** The 27,862-bus FNM main island has complex topology
   with many low-voltage radial feeders and transformer-connected sub-networks
   that create ill-conditioned Jacobian blocks.

2. **DCPF warm-start angles are extreme:** The DCPF solution produces angles
   up to 536.9 degrees (mean absolute 209.5 degrees), which places the ACPF
   initial point far from any physically realizable AC solution. These large
   angles arise from the DC approximation on a network with many transformer
   taps and phase shifters.

3. **Thermal limit relaxation is irrelevant:** RATE_A relaxation affects OPF
   constraint limits, not power flow convergence. The `runpf()` function does
   not enforce thermal limits -- it solves the power balance equations only.
   Therefore 10% and 20% relaxation have no effect on NR convergence, which
   is confirmed by the identical failure mode across all three steps.

4. **Q-limit sensitivity:** The FNM has generators with reactive power limits
   that may cause PV-to-PQ bus transitions during NR iteration, creating
   discontinuities that destabilize convergence.

The ACPF reference data (`buses_acpf.csv`) shows VM values ranging from
0.09 to 379,646 pu, confirming that the reference ACPF solution also
exhibits non-physical voltage magnitudes on many buses, consistent with
convergence difficulties across solvers.

## Workarounds

None attempted. The protocol specifies that G-FNM-4 outcomes are
informational with no pass/fail gate. Progressive relaxation was applied
as specified but did not resolve the singular Jacobian.

## Timing

- **Wall-clock:** ~65 seconds total (0.167s DCPF + 3 x ~21.7s ACPF attempts)
- **Timing source:** measured
- **Peak memory:** 1.8 MB (peak RSS)
- **NR iterations:** 100 per attempt (hit max_it limit)

## Test Script

**Path:** `evaluations/matpower/tests/fnm_ingestion/test_g_fnm_4_fnm_acpf_convergence.m`
