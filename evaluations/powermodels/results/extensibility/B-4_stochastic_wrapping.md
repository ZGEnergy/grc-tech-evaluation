# B-4: Stochastic Wrapping (TINY — case39)

## Tool
PowerModels.jl v0.21.5

## Status: PASS

## Summary
50 scenarios with correlated load perturbations over a 24-hour multi-period DC OPF. Uses `replicate()` for multi-period expansion and `solve_mn_opf` with HiGHS for optimization. 10 of 50 scenarios solve to optimality; 40 are infeasible due to generator limits under load perturbation. Total wall clock: 8.3s.

## Approach
1. Parse network with `PowerModels.parse_file()`
2. Create 24-period network: `mn_data = PowerModels.replicate(data, 24)`
3. For each scenario:
   - `deepcopy(mn_data)` to clone multi-period structure
   - Generate correlated load perturbations (common factor 60% + idiosyncratic 40%)
   - Modify `nw["$t"]["load"][id]["pd"]` for each period and load
   - Solve with `PowerModels.solve_mn_opf(sc_data, DCPPowerModel, HiGHS.Optimizer)`
4. Collect costs and solve times

## Results

| Metric | Value |

|--------|-------|

| Scenarios | 50 |

| Hours per scenario | 24 |

| Loads perturbed | 21 |

| Scenarios solved | 10 |

| Scenarios infeasible | 40 |

| Mean cost (solved) | 981,954.73 |

| Std cost | 22,246.91 |

| Min / Max cost | 934,236.79 / 1,008,364.23 |

| Mean solve time | 0.14s per scenario |

| Total solve time | 7.0s |

| Total wall clock | 8.3s |

### Correlation model
- Common factor weight: 0.6, std: 10%
- Idiosyncratic std: 5%
- Seed: 42

## Observations
- **`replicate()` is the correct API** for multi-period expansion. It deep-copies per-period data and creates the `nw` multi-network dict structure.
- **No timeseries input API**: PowerModels has no native way to specify load profiles as timeseries. The user must manually modify load values in each `nw["$t"]` sub-dict. This is workable but verbose.
- **High infeasibility rate** (80%) is due to generator limits in case39 being tight. A production stochastic study would need to either relax bounds or add load-shedding variables. This is a modeling issue, not a tool limitation.
- **Per-scenario overhead is low**: 0.14s average solve time for 24-period QP with 3168 rows and 2280 cols.

## Workarounds
- No timeseries input method; must manually loop over periods and modify load dicts.

## Script
`tests/extensibility/test_b4_stochastic_wrapping.jl`
