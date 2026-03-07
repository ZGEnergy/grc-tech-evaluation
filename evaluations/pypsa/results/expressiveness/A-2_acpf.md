---
test_id: A-2
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.156
peak_memory_mb: null
loc: 141
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-2: Solve AC power flow (Newton-Raphson)

## Result: PASS

## Approach

Loaded the IEEE 39-bus network via the standard MATPOWER import pipeline. Solved AC
power flow using `n.pf()`, which uses Newton-Raphson iteration.

Following the convergence protocol:
1. **Flat start** (V=1.0 pu, theta=0): Attempted first.
2. Result: Converged in **4 iterations** with final mismatch of **3.32e-9**.
3. DC warm start fallback was **not needed**.

Extracted structured results from PyPSA's pandas DataFrame attributes:
- Bus voltage magnitudes: `n.buses_t.v_mag_pu`
- Bus voltage angles: `n.buses_t.v_ang`
- Line P flows: `n.lines_t.p0`, `n.lines_t.p1`
- Line Q flows: `n.lines_t.q0`, `n.lines_t.q1`
- Losses: computed as `p0 + p1` (sending + receiving end flows)
- Transformer flows: `n.transformers_t.p0`

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| NR iterations | 4 |
| Final mismatch | 3.32e-9 |
| DC warm start needed | No |
| Output format | pandas DataFrame |

**Voltage magnitudes (pu):**

| Statistic | Value |
|-----------|-------|
| Min | 0.982 |
| Max | 1.064 |
| Mean | 1.026 |
| Num buses | 39 |

**Voltage angles (radians):**

| Statistic | Value |
|-----------|-------|
| Min | -0.2537 |
| Max | 0.0780 |
| Mean | -0.1299 |

**Line P flows (MW):**

| Statistic | Value |
|-----------|-------|
| p0 min | -604.42 |
| p0 max | 453.82 |

**Line Q flows (MVAr):**

| Statistic | Value |
|-----------|-------|
| q0 min | -156.66 |
| q0 max | 113.06 |

**Losses:**

| Statistic | Value |
|-----------|-------|
| Total P losses | 31.06 MW |
| Total Q losses | -692.65 MVAr |
| Num lines | 35 |

**Transformer flows:**

| Statistic | Value |
|-----------|-------|
| Num transformers | 11 |
| p0 min | -824.77 MW |
| p0 max | 174.73 MW |

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.156 s
- **Peak memory:** not measured
- **Solver iterations:** 4 (Newton-Raphson)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a2_acpf.py`

The API is clean: `n.pf()` returns a dict with convergence info (`n_iter`, `error`,
`converged`). All bus and branch results are available as structured DataFrames.
Losses must be computed manually from sending/receiving end flows (`p0 + p1`), but
the data is readily accessible.
