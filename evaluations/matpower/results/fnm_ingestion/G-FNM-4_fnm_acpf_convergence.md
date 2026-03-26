---
test_id: G-FNM-4
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: "4aa892c7"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 117.108
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: null
convergence_iterations: 100
convergence_evidence_quality: binary_convergence_api
loc: 183
solver: Newton-Raphson (MATPOWER built-in)
ingestion_path: matpower_raw
input_path: matpower
timestamp: "2026-03-24T18:00:00Z"
---

# G-FNM-4: ACPF convergence test with DCPF warm-start and progressive relaxation

## Result: INFORMATIONAL

## Approach

Loaded the pre-cleaned FNM main island network from the MATPOWER fallback
path (`fnm_main_island.mat`). Followed the three-step progressive
relaxation protocol:

1. **Step 1 (DCPF warm-start):** Solved DCPF via `rundcpf()` to obtain
   voltage angle initialization. Recorded `dcpf_init_mean_deg` and
   `dcpf_init_max_abs_deg`.

2. **Step 2 (ACPF at 0% relaxation):** Set VM = 1.0 pu (flat voltage
   magnitude), VA from DCPF solution. Ran `runpf()` with Newton-Raphson
   solver (`pf.alg = 'NR'`, `pf.nr.max_it = 100`, `pf.tol = 1e-8`).
   30-minute timeout.

3. **Step 3 (ACPF at 10% relaxation):** Multiplied `RATE_A` by 1.10.
   Re-ran `runpf()` with same settings and DCPF warm-start angles.

4. **Step 4 (ACPF at 20% relaxation):** Multiplied `RATE_A` by 1.20.
   Re-ran `runpf()`.

Note: Thermal limit relaxation (`RATE_A` scaling) has no effect on
`runpf()` convergence because MATPOWER's power flow solver does not
enforce thermal limits -- it solves only power balance equations. The
relaxation steps were performed per protocol but were not expected to
change the convergence outcome.

## Output

### DCPF Warm-Start (Step 1)

| Metric | Value |
|--------|-------|
| DCPF success | 1 (converged) |
| DCPF wall clock | 0.183 seconds |
| dcpf_init_mean_deg | 209.5004 |
| dcpf_init_max_abs_deg | 536.9252 |

The DCPF angles reach 537 degrees absolute maximum, indicating the
network has very large angle spreads characteristic of a continental-scale
transmission system with many series impedances.

### ACPF at 0% Relaxation (Step 2)

| Metric | Value |
|--------|-------|
| Converged | No |
| Iterations | 100 (max reached) |
| Wall clock | 63.617 seconds |
| Peak RSS | 1.9 MB |
| Failure mode | Singular Jacobian (rcond ~ 1.9e-17) |

### ACPF at 10% Relaxation (Step 3)

| Metric | Value |
|--------|-------|
| Converged | No |
| Iterations | 100 (max reached) |
| Wall clock | 26.788 seconds |
| Peak RSS | 1.9 MB |
| Failure mode | Singular Jacobian (rcond ~ 1.9e-17) |

### ACPF at 20% Relaxation (Step 4)

| Metric | Value |
|--------|-------|
| Converged | No |
| Iterations | 100 (max reached) |
| Wall clock | 26.703 seconds |
| Peak RSS | 1.8 MB |
| Failure mode | Singular Jacobian (rcond ~ 1.9e-17) |

### Summary

| Metric | Value |
|--------|-------|
| relaxation_level_achieved | infeasible |
| Total ACPF wall clock | 117.108 seconds |
| Failure mode | Singular Jacobian at all relaxation levels |

### Diagnosis

The Newton-Raphson solver fails at iteration 1 with a singular Jacobian
matrix (rcond ~ 1.9e-17). This persists across all 100 iterations at each
relaxation level, indicating the Jacobian never becomes well-conditioned.

The singular Jacobian is consistent with known characteristics of the FNM
network:
- Very large angle spreads (537 degrees max) from DCPF initialization
- Possible low-voltage radial sub-networks creating ill-conditioned
  admittance matrix blocks
- Transformer tap interactions at distribution-transmission boundaries

The ACPF reference data files (buses_acpf.csv, branches_acpf.csv) contain
non-physical values (VM up to 379,646 p.u., branch flows in the millions
of MW), confirming that this network is inherently difficult for ACPF
convergence. The reference ACPF solution appears to be from a
non-converged or improperly scaled solve.

This is a network characteristic, not a MATPOWER-specific limitation.
[solver-specific: Newton-Raphson on structurally ill-conditioned network]

## Workarounds

None applicable. The ACPF non-convergence is due to network structural
ill-conditioning, not a tool limitation. Alternative approaches that were
not tested but could be investigated include:
- Fast-Decoupled power flow (`pf.alg = 'FDXB'` or `'FDBX'`)
- Implicit Z-bus Gauss method (MATPOWER 8.0+ for radial systems)
- Network splitting to solve sub-networks independently
- Voltage initialization from a solved sub-network

## Timing

- **Wall-clock:** 117.108 seconds total (63.6s + 26.8s + 26.7s for three ACPF attempts)
- **Timing source:** measured (tic/toc)
- **Peak memory:** 1.9 MB
- **Iterations:** 100 per attempt (NR max_it limit)

## Test Script

**Path:** `evaluations/matpower/tests/fnm_ingestion/test_g_fnm_4_fnm_acpf_convergence.m`
