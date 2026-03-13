---
test_id: A-2
tool: pypsa
dimension: expressiveness
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 97f53d76
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 46.63
timing_source: measured
peak_memory_mb: 2099.0
convergence_residual: null
convergence_iterations: 72
loc: 249
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-2: AC Power Flow (acpf) — MEDIUM

## Result: FAIL

## Approach

Same pipeline as TINY: loaded ACTIVSg10k via CaseFrames → ppc → `import_from_pypower_ppc`. Attempted flat-start Newton-Raphson ACPF via `n.pf()`. Following the convergence protocol, applied DC warm start fallback when flat start failed. Both attempts failed to converge.

Convergence data extracted from `pf_result["n_iter"]`, `pf_result["error"]`, `pf_result["converged"]`.

## Output

**Flat start attempt:**
- Converged: False
- NR iterations: 72 (hit iteration limit)
- Final residual: NaN (diverged — sparse matrix became exactly singular)
- Solve time: 29.6 s
- Peak memory: 2,099 MB

**DC warm start fallback:**
- Converged: False
- NR iterations: 72
- Final residual: NaN (same singular matrix condition)
- Additional solve time: 9.7 s (DCPF first, then NR attempt)

**Solver warning:** `MatrixRankWarning: Matrix is exactly singular` from `scipy.sparse.linalg.spsolve` inside PyPSA's Newton-Raphson solver. This indicates the Jacobian becomes singular during the iteration, preventing further progress.

**Partial voltage profile (from non-converged state):**
- V_mag range: [0.9616, 1.0814] pu (on buses that did converge locally)
- Non-flat buses: 1,705 of 10,000 (17.1% — far below 95% threshold for convergence quality)
- Most bus voltages are NaN (diverged)

## Convergence Finding

AC power flow does not converge on ACTIVSg10k with PyPSA's Newton-Raphson solver from either flat start or DC warm start. This is a notable finding — per the convergence protocol, non-convergence on MEDIUM is documented as a finding rather than automatic failure for grading purposes, but it is **counted as a fail** per protocol.

Root cause: ACTIVSg10k is a synthetic 10k-bus network designed to have realistic congestion patterns. The network has unusual properties (large voltage angles from DCPF up to 104°, many zero-impedance or near-zero-impedance branches) that may cause the NR Jacobian to become ill-conditioned or singular.

The `MatrixRankWarning` from `spsolve` suggests the issue is structural: the admittance matrix or its Jacobian variant contains a dependent row, possibly from the zero-resistance transformer T18 (flagged by PyPSA consistency checker) or from parallel/near-parallel branches.

**Per convergence protocol (Table: MEDIUM / Both Fail):** "Record, may cap grade."

## Workarounds

None required (the test ran without workaround; it simply did not converge).

## Timing

- **Wall-clock:** 46.63 s (flat start 29.6 s + DC warm start 9.7 s + overhead)
- **Timing source:** measured
- **Peak memory:** 2,099 MB
- **Flat start iterations:** 72 (iteration limit)
- **DC warm start iterations:** 72 (iteration limit)
- **Convergence residual:** NaN (diverged)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a2_acpf_medium.py`
