---
test_id: A-1
tool: powermodels
dimension: expressiveness
network: MEDIUM
status: pass
wall_clock_seconds: 18.06
timestamp: 2026-03-05
---

# A-1: DC Power Flow [MEDIUM]

## Result: PASS

## Approach
Same as TINY: `compute_dc_pf()` (native, non-JuMP solver) followed by `calc_branch_flow_dc()`. No changes needed for scale.

## Data Preprocessing
- 1349 generators missing cost data: added default $20/MWh linear cost
- 2462 branches with rate_a=0: set to 9999 (unconstrained)
- Note: preprocessing not strictly needed for DCPF (no optimization), but applied for consistency

## Output
- 10000 buses, 12706 branches, 2485 generators
- Non-zero voltage angles: all non-reference buses have non-trivial angles
- Branch flows computed for all 12706 branches

## Timing
- Wall-clock: 18.06s (includes file parsing ~12s, solve <1s, flow calculation ~5s)
- The native `compute_dc_pf` solver uses direct matrix factorization, no JuMP overhead
