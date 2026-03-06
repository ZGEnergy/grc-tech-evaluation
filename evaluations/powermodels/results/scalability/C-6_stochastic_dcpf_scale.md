---
test_id: C-6
tool: powermodels
dimension: scalability
network: SMALL
status: fail
wall_clock_seconds: -1
peak_memory_mb: 1812
timestamp: 2026-03-05
---

# C-6: 50-Scenario Stochastic DCPF at SMALL (2000 buses)

## Result: FAIL (timeout)

The first scenario of 50 did not converge within the observation window (>45 minutes). The multi-period DC OPF (2000 buses x 24 hours) creates a very large QP that HiGHS cannot solve efficiently.

## Timing
- Wall-clock: >2700s on scenario 1 of 50 (still running)
- HiGHS iterations at 2703s: 28,347 (objective: 29,841,276)
- Peak memory: ~1,812 MB
- Problem size: 188,976 rows, 135,312 columns, 523,128 matrix nonzeros, 135,312 Hessian nonzeros
- CPU cores: 1 (single-threaded)

## HiGHS Iteration Progress

| Time (s) | Iterations | Objective |

|----------|-----------|-----------|

| 145 | 0 | 29,872,085 |

| 903 | 1 | 29,871,918 |

| 943 | 725 | 29,869,400 |

| 1,423 | 4,743 | 29,848,880 |

| 2,063 | 12,735 | 29,841,619 |

| 2,703 | 28,347 | 29,841,276 |

## Method

```julia
mn_data = PowerModels.replicate(data, 24)  # 24-hour multi-period
# Per scenario: deepcopy, perturb loads, solve_mn_opf
result = PowerModels.solve_mn_opf(sc_data, DCPPowerModel, HiGHS.Optimizer)

```

## Analysis
The 2000-bus x 24-hour multi-period DC OPF creates a massive QP (189k rows, 135k cols) that HiGHS struggles with:

1. **First iteration took 903s** -- the initial basis factorization alone is very expensive
2. **Convergence is extremely slow** -- after 28k iterations, objective has only decreased by 0.1%
3. **50 scenarios at this rate would take >56 hours** (infeasible in any practical workflow)

Root cause: HiGHS's QP solver has poor performance on large multi-period power system problems. This is consistent with the C-3/C-7 findings where HiGHS had numerical issues on 10k-bus QPs.

**Mitigation:** Using Ipopt instead of HiGHS would likely solve each scenario in ~60s (based on C-3 data), making the full 50-scenario sweep ~50 minutes. However, this was not tested in this run due to the HiGHS timeout consuming the available time budget.
