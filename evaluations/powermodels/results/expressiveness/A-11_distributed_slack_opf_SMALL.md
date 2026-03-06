---
test_id: A-11
tool: powermodels
dimension: expressiveness
network: SMALL
status: pass
wall_clock_seconds: 1.49
timestamp: 2026-03-05
---

# A-11: Distributed Slack DC OPF [SMALL]

## Result: PASS

## Approach
Same as TINY: custom build function replacing `constraint_theta_ref` with load-proportional weighted angle-sum constraint. Single-slack vs distributed-slack LMP comparison.

## Data Preprocessing
- Standard preprocessing (costs, rate_a)

## Output
- Single-slack DC OPF: solved (Ipopt)
- Distributed-slack DC OPF: solved via custom build function
- LMP differences between configs: near-zero (as expected for lossless DC OPF)
- Objectives match within tolerance

## Timing
- Wall-clock: 1.49s (both solves combined)
- Very fast at 2000-bus scale with Ipopt

## Workarounds
- No native distributed slack; custom build function with weighted angle-sum constraint (~40 LOC)
