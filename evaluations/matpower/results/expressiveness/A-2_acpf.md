---
test_id: A-2
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "fca7353e"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.0879
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: 3.319e-11
convergence_iterations: 4
loc: 32
solver: "Newton-Raphson (built-in)"
timestamp: 2026-03-13T00:00:00Z
---

# A-2: Solve AC power flow (Newton-Raphson) on TINY

## Result: PASS

## Approach

Loaded the IEEE 39-bus case, set flat start (VM=1.0 pu, VA=0 for all buses), configured Newton-Raphson solver via `mpoption('pf.alg', 'NR', 'verbose', 2, 'pf.tol', 1e-8)`, then called `runpf(mpc, mpopt)`.

MATPOWER uses its own built-in Newton-Raphson solver for AC power flow, not an external solver like Ipopt. Ipopt is only used for OPF. The `verbose` level 2 output shows per-iteration convergence progress.

## Output

| Metric | Value |
|--------|-------|
| NR iterations | 4 |
| Final residual | 3.319e-11 |
| PF tolerance | 1e-8 |
| Flat start converged | Yes (no DC warm start needed) |
| VM differs from 1.0 pu | 100.0% of buses |
| VM range | [0.9820, 1.0636] pu |
| VM mean | 1.0263 pu |
| VA range | [-14.54, 4.47] deg |
| Total generation | 6297.87 MW + 1274.94 MVAr |
| Total load | 6254.23 MW + 1387.10 MVAr |
| Total P losses | 43.64 MW (0.69%) |
| Total Q losses | -112.16 MVAr |

NR convergence trace:

| Iter | Max Residual | Max dx |
|------|-------------|--------|
| 0    | 8.129e+00   | -      |
| 1    | 1.137e+00   | 2.367e-01 |
| 2    | 2.273e-02   | 4.733e-02 |
| 3    | 2.347e-05   | 1.928e-03 |
| 4    | 3.319e-11   | 2.106e-06 |

Sample bus results:

| Bus | VM (pu) | VA (deg) |
|-----|---------|----------|
| 1   | 1.0394  | -13.5366 |
| 2   | 1.0485  | -9.7853  |
| 3   | 1.0307  | -12.2764 |
| 4   | 1.0045  | -12.6267 |
| 5   | 1.0060  | -11.1923 |

**Diagnostic quality:** MATPOWER stores the NR iteration count in `results.iterations` (accessible programmatically). The convergence residual is visible in verbose output (per-iteration max residual) but the final residual value is not stored in the results struct -- it must be parsed from verbose output or inferred from the configured tolerance. The verbose output format is well-structured and parseable.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.0879 s
- **Timing source:** measured
- **Peak memory:** 1.9 MB
- **Solver iterations:** 4 (Newton-Raphson)
- **Convergence residual:** 3.319e-11 (from verbose output)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a2_acpf.m`
