---
test_id: A-1
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.098
peak_memory_mb: null
loc: 79
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-1: Solve DC power flow

## Result: PASS

## Approach

Loaded the IEEE 39-bus (New England) network from `data/networks/case39.m` using the
`matpowercaseframes` -> PYPOWER PPC dict -> `n.import_from_pypower_ppc(ppc)` pipeline.
Solved DC power flow using `n.lpf()`, which performs a direct linear solve (no
iterative solver needed).

Extracted results from PyPSA's pandas DataFrame attributes:
- Voltage angles: `n.buses_t.v_ang`
- Line flows: `n.lines_t.p0`
- Nodal power injections: `n.buses_t.p`

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Output format | pandas DataFrame |

**Voltage angles (radians):**

| Statistic | Value |
|-----------|-------|
| Min | -0.2349 |
| Max | 0.1292 |
| Mean | -0.1035 |
| Num buses | 39 |

**Line flows (MW):**

| Statistic | Value |
|-----------|-------|
| Min | -608.78 |
| Max | 448.48 |
| Mean | -31.44 |
| Num lines | 35 |

**Nodal injections (MW):**

| Statistic | Value |
|-----------|-------|
| Min | -680.0 |
| Max | 830.0 |
| Sum | 0.0 |
| Num buses | 39 |

The sum of nodal injections equals zero, confirming power balance. All outputs are
structured pandas DataFrames indexed by bus/line name, not raw solver vectors.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.098 s
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct linear solve)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a1_dcpf.py`

The API is straightforward: one call to `n.lpf()` and results are immediately available
on the network object as named DataFrames. No solver configuration needed.
