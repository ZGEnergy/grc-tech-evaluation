---
test_id: C-10
tool: powermodels
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 128.93
peak_memory_mb: 18.96
timestamp: 2026-03-05
---

# C-10: Distributed Slack DC OPF at MEDIUM (10000 buses)

## Result: PASS

## Timing

| Variant | Wall-clock | Status | Objective |

|---------|-----------|--------|-----------|

| Single slack (standard) | 49.7s | LOCALLY_SOLVED | 2,446,806.45 |

| Distributed slack (custom) | 27.5s | LOCALLY_SOLVED | 2,446,806.45 |

- Peak memory: 19.0 MB
- Solver: Ipopt (HiGHS has QP errors at 10k scale)
- CPU cores: 1 (single-threaded)

## Output
- Network: 10,000 buses, 12,706 branches, 2,485 generators
- Buses with load: 4,170
- Total load: 1,509.17 p.u.
- Objectives match: Yes (difference = 0.0)
- Max LMP difference: 0.0

## Method
Custom build function replacing `constraint_theta_ref` with load-proportional angle reference:

```julia
# sum(w_i * va_i) = 0 where w_i = load_i / total_load

```

This is the same approach as the A-11 expressiveness test, now validated at 10k-bus scale.

## Analysis
The distributed slack formulation scales well to 10k buses:
1. Same objective and LMPs as single-slack (expected for lossless DC OPF)
2. The distributed slack solve (27.5s) was actually faster than single-slack (49.7s), likely due to better numerical conditioning of the angle reference constraint
3. Custom build function approach works identically at any network size
4. Requires Ipopt (HiGHS fails with QP errors on 10k networks)

Note: PowerModels has NO native distributed slack. The custom build function (~40 LOC) is required.
