---
test_id: A-1
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "05bc255c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.0739
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: null
convergence_iterations: null
loc: 28
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# A-1: Solve DC power flow on TINY

## Result: PASS

## Approach

Loaded the IEEE 39-bus case via `loadcase()`, configured `mpoption('verbose', 0, 'out.all', 0)` to suppress default output, then called `rundcpf(mpc, mpopt)`. Used `define_constants` to access named column indices (BUS_I, VA, PF, PD, GEN_BUS, PG, etc.) for structured output extraction.

MATPOWER's DCPF solves a linear system directly (no iterative solver), so convergence is guaranteed for connected networks.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 39 |
| Branch count | 46 |
| Generator count | 10 |
| Total generation | 6254.23 MW |
| Total load | 6254.23 MW |
| Angle spread | 20.87 deg |
| Max branch flow | 830.00 MW |
| Nonzero angles | 38 / 39 |

Sample bus results:

| Bus | Angle (deg) | Net Injection (MW) |
|-----|-------------|---------------------|
| 1   | -12.3044    | -97.60              |
| 2   | -8.1044     | 0.00                |
| 3   | -10.9891    | -322.00             |
| 4   | -11.6495    | -500.00             |
| 5   | -10.3464    | 0.00                |

Sample branch results:

| From | To | Pf (MW) | Pt (MW) |
|------|----|---------|---------|
| 1    | 2  | -178.35 | 178.35  |
| 1    | 39 | 80.75   | -80.75  |
| 2    | 3  | 333.43  | -333.43 |
| 2    | 25 | -261.78 | 261.78  |
| 2    | 30 | -250.00 | 250.00  |

**Structured output:** Results are accessible as a MATPOWER struct with named matrices (`results.bus`, `results.gen`, `results.branch`). Column indices are provided by `define_constants` (e.g., `BUS_I`, `VA`, `PF`, `PG`). This qualifies as structured output per the pass condition.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.0739 s
- **Timing source:** measured
- **Peak memory:** 1.9 MB
- **Solver iterations:** N/A (direct linear solve)
- **Convergence residual:** N/A (direct solve)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a1_dcpf.m`
