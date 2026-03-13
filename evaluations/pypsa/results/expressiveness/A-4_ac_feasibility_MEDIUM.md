---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 1734eea4
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 547.71
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 71
loc: 278
solver: scipy (Newton-Raphson)
timestamp: 2026-03-11T00:00:00Z
---

# A-4: AC Feasibility Check (ac_feasibility) — MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded ACTIVSg10k (`overwrite_zero_s_nom=9999.0` for OPF feasibility). Assigned differentiated marginal costs to all 2,485 generators ($10–$100/MWh). Ran DC OPF via `n.optimize()` to obtain the optimal dispatch. Fixed generator active power to DC OPF values via `n.generators_t.p_set` assignment — all within the same `n` object (no file export or reimport). Ran `n.pf()` (flat-start Newton-Raphson AC PF) on the fixed dispatch.

The "same model context" requirement is fully satisfied: the DC OPF dispatch is applied to the identical network object, and `n.pf()` is called immediately without any serialization.

## Output

**DC OPF:** Solved optimally (HiGHS LP, optimal) in 521.4 s
- Total dispatch: 150,917 MW
- Active generators: 1,722 of 2,485

**AC PF:** Did not converge
- Iterations: 71 (hit limit)
- Residual: NaN (Jacobian became singular — `MatrixRankWarning: Matrix is exactly singular`)
- Solve time: 24.1 s

**Same model context:** True (verified — no export/reimport between steps)

**Voltage profile (from non-converged state):**
- V_mag range: [0.9616, 1.0814] pu
- Non-trivial buses: 9,998 of 10,000 (99.98% — the NR ran but diverged)
- Since AC PF didn't converge, no meaningful voltage or thermal violations can be reported
  - Reported violations: 0 (not meaningful — based on non-converged NaN voltages)

## Convergence Finding

AC PF does not converge on ACTIVSg10k starting from the DC OPF dispatch. This is the same root cause as A-2 MEDIUM: the NR Jacobian becomes exactly singular on this 10k-bus synthetic network. The DC OPF dispatch starting point does not improve convergence vs flat start.

**Key finding:** The "same model context" expressiveness test is **passed** — PyPSA can apply DC OPF dispatch and attempt AC PF in-memory without any I/O. The convergence failure is a network-specific numerical issue, not an API limitation.

Per convergence protocol for A-4 on MEDIUM: non-convergence from DC dispatch starting point is an expected and documented outcome that does not constitute a tool failure for the expressiveness test.

## Workarounds

None required for the same-model-context pattern. The DC OPF → fix dispatch → run ACPF workflow is natively supported via `generators_t.p_set` assignment.

## Timing

- **Wall-clock:** 547.7 s total
- **Load time:** 2.2 s
- **DC OPF (n.optimize):** 521.4 s
- **AC PF (n.pf):** 24.1 s
- **Timing source:** measured
- **Peak memory:** not measured separately (DC OPF peak similar to A-3: ~4.4 GB)
- **Solver iterations:** 71 NR iterations (did not converge)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility_medium.py`
