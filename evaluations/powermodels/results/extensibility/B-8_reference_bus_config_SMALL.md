---
test_id: B-8
tool: powermodels
dimension: extensibility
network: SMALL
status: pass
wall_clock_seconds: 3.248
timestamp: 2026-03-05
---

# B-8: Reference Bus Configuration (Three Slack Configs) [SMALL]

## Result: PASS

## Approach
Same as TINY: three DC OPF configurations tested.
1. Default reference bus (bus_type=3 from data)
2. Alternative single slack (swap bus_type between two generator buses)
3. Distributed slack (custom build function: sum(va)==0)

## Data Preprocessing
- Standard preprocessing (costs, rate_a)

## Output
- All three configurations solved successfully with Ipopt
- Config 1 and 2 objectives match (reference bus choice doesn't affect dispatch in lossless DC OPF)
- Config 3 (distributed slack) objective matches configs 1 and 2
- Reference bus configurable via `bus_type` field manipulation
- Distributed slack requires custom build function (~20 LOC)

## Timing
- Wall-clock: 3.25s (all three solves combined)
- Very fast at 2000-bus scale

## Workarounds
- Distributed slack requires custom build function; not built-in
