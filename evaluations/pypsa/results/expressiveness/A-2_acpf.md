---
test_id: A-2
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: eb349d9c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.11
timing_source: measured
peak_memory_mb: 0.60
convergence_residual: 3.316811e-09
convergence_iterations: 4
convergence_evidence_quality: residual_reported
loc: 245
solver: null
timestamp: 2026-03-24T12:01:00Z
---

# A-2: Solve ACPF (Newton-Raphson) on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via `matpowercaseframes` to pypower PPC dict, then
imported with `import_from_pypower_ppc`. Notably, this test does NOT use the
shared `load_pypsa` loader's transformer susceptance patch (b = 1/x), because
that patch corrects the DCPF B-matrix but breaks ACPF convergence. In PyPSA's
AC model, the transformer `b` field represents shunt susceptance (pi-model),
not series susceptance.

Ran `n.pf(x_tol=1e-6)` which executes PyPSA's internal Newton-Raphson solver.
Flat start (all voltages 1.0 pu, all angles 0.0 rad) converged on the first
attempt -- no DC warm start was needed.

## Output

### Convergence

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| NR iterations | 4 |
| Final residual | 3.317e-09 p.u. |
| Evidence quality | residual_reported (Tier 1) |
| DC warm start needed | No |

PyPSA's `n.pf()` returns a `Dict` with keys `converged`, `n_iter`, and `error`,
providing Tier 1 convergence evidence: the residual value (3.317e-09) is far below
the 1e-4 p.u. threshold, and the iteration count (4) confirms the solver actually
executed NR iterations.

### Voltage Profile

| Metric | Value |
|--------|-------|
| V_mag range | 0.982 - 1.064 pu |
| V_mag mean | 1.026 pu |
| Buses with non-flat voltage | 38/39 (97.4%) |

**Voltage magnitudes (pu) -- first 5 buses:**

| Bus | V_mag (pu) | V_ang (deg) |
|-----|-----------|-------------|
| 1 | 1.0394 | -13.537 |
| 2 | 1.0485 | -9.785 |
| 3 | 1.0307 | -12.276 |
| 4 | 1.0045 | -12.627 |
| 5 | 1.0060 | -11.192 |

### Line Flows and Losses

| Metric | Value |
|--------|-------|
| Total load | 6254.23 MW |
| Total losses | 31.06 MW |
| Loss percentage | 0.50% |

**Line P flows (MW) -- first 5 lines:**

| Line | P0 (MW) | Q0 (MVAr) |
|------|---------|-----------|
| L0 | -173.70 | -40.31 |
| L1 | 76.10 | -3.89 |
| L2 | 319.91 | 88.59 |
| L3 | -244.59 | 82.97 |
| L4 | 37.34 | 113.06 |

Bus voltage magnitudes, angles, line P/Q flows, and losses are all accessible as
`pandas.DataFrame` structured outputs.

## Workarounds

None required.

## Timing

- **Wall-clock:** 2.11 s (including network loading)
- **Solve only:** 0.41 s
- **Timing source:** measured
- **Peak memory:** 0.60 MB (tracemalloc, solve phase only)
- **Solver iterations:** 4 (Newton-Raphson)
- **Convergence residual:** 3.317e-09 p.u.

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a2_acpf.py`

Key implementation note: The test uses a custom `load_network_for_acpf` function
that skips the shared loader's transformer susceptance patch. This is necessary
because PyPSA's transformer `b` field has different semantics in the AC model
(shunt susceptance) versus the DC model (series susceptance for B-matrix).
