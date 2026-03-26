---
test_id: A-1
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 05bc255c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.94
timing_source: measured
peak_memory_mb: 0.49
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 143
solver: null
timestamp: 2026-03-24T12:00:00Z
---

# A-1: Solve DCPF on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via the shared MATPOWER loader (`load_pypsa` from
`evaluations/shared/matpower_loader.py`), which applies three correctness patches:
branch status mapping, transformer susceptance correction (b = 1/x for DCPF),
and generator marginal cost extraction from gencost data. Ran `n.lpf()` (PyPSA's
linear power flow) which performs a direct linear solve of the DC power flow
equations -- no iterative solver or external optimizer needed.

## Output

| Metric | Value |
|--------|-------|
| Buses | 39 |
| Lines | 35 |
| Transformers | 11 |
| Generators | 10 |
| Non-zero angles (non-slack) | 38/38 |
| Non-zero line flows | 35/35 |
| Max voltage angle | 13.46 deg |
| Max line flow | 608.78 MW |
| Total generation | 7367.0 MW |
| Slack bus | 31 |

**Voltage angles (degrees) -- first 5 buses:**

| Bus | Angle (deg) |
|-----|------------|
| 1 | -12.304 |
| 2 | -8.104 |
| 3 | -10.989 |
| 4 | -11.650 |
| 5 | -10.346 |

**Line flows (MW) -- first 5 lines:**

| Line | P0 (MW) |
|------|---------|
| L0 | -178.35 |
| L1 | 80.75 |
| L2 | 333.43 |
| L3 | -261.78 |
| L4 | 54.12 |

All three output categories (voltage angles, nodal injections, line flows) are
returned as `pandas.DataFrame` objects, satisfying the structured output requirement.
Transformer flows are also accessible via `n.transformers_t.p0`.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.94 s (including network loading)
- **Solve only:** 0.25 s
- **Timing source:** measured
- **Peak memory:** 0.49 MB (tracemalloc, solve phase only)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a1_dcpf.py`
