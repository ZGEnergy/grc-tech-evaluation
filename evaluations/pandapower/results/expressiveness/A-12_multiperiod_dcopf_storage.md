---
test_id: A-12
tool: pandapower
dimension: expressiveness
network: TINY
status: fail
workaround_class: blocking
blocked_by: null
protocol_version: "v10"
skill_version: "v1"
test_hash: "6fc27521"
wall_clock_seconds: 0.80
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 290
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-13T00:00:00Z"
---

# A-12: Multi-Period DCOPF with Storage and Congestion

## Result: FAIL

## Approach

1. Inspected `rundcopp()` signature for any multi-period or temporal parameters -- found none.
2. Inspected `pandapower.timeseries.run_timeseries()` -- confirmed it runs sequential independent PF/OPF solves per timestep, with no inter-temporal coupling.
3. Confirmed `pp.create_storage()` exists and accepts the required BESS parameters (bus, power, energy, SoC, efficiency bounds).
4. Discovered `pp.runpm_storage_opf()` in the PandaModels.jl bridge -- this function **does** accept multi-period parameters (`from_time_step`, `to_time_step`, `n_timesteps`, `charge_efficiency`, `discharge_efficiency`). However, it requires Julia with PandaModels.jl installed, which is a separate runtime dependency.
5. Loaded the case39 network, applied differentiated costs, 70% branch derating, and created a storage element at bus 5.
6. Ran a single-snapshot DC OPF to demonstrate that storage participates in single-period OPF (it dispatched at -150 MW, full charge, because a single-period solve without SoC constraints has no reason to manage energy across time).

## Output

**Capability assessment:**

| Feature | Available | Notes |
|---|---|---|
| Single-period DCOPF | Yes | `rundcopp()` |
| Multi-period DCOPF | No | No native formulation |
| Storage element | Yes | `pp.create_storage()` with p_mw, max_e_mwh, soc_percent, etc. |
| Storage in single-period OPF | Yes | Dispatches as controllable gen/load |
| Inter-temporal SoC constraint | No | Not in native OPF |
| Cyclic SoC constraint | No | Not in native OPF |
| Time series module | Yes | Sequential independent solves only |
| PandaModels storage OPF | Available (function exists) | Requires Julia + PandaModels.jl runtime |

**`rundcopp()` parameters:** `net, verbose, check_connectivity, suppress_warnings, switch_rx_ratio, delta, trafo3w_losses, kwargs` -- no temporal parameters.

**`run_timeseries()` parameters:** `net, time_steps, continue_on_divergence, verbose, check_controllers, kwargs` -- runs independent solves per step without inter-temporal optimization.

**`runpm_storage_opf()` parameters (PandaModels.jl bridge):**
- `from_time_step`, `to_time_step`, `n_timesteps`, `time_elapsed` -- multi-period parameters
- `charge_efficiency`, `discharge_efficiency`, `standby_loss`, `p_loss`, `q_loss` -- storage parameters
- `pm_solver`, `pm_mip_solver`, `pm_nl_solver`, `pm_model` -- solver selection

This function signature shows pandapower has designed a multi-period storage OPF interface through the PandaModels.jl bridge. However, this path requires a Julia installation with PandaModels.jl and PowerModels.jl packages, and uses Julia's JuMP optimization framework rather than pandapower's native PYPOWER solver.

**Single-snapshot OPF baseline:**

| Metric | Value |
|---|---|
| Converged | Yes |
| Storage dispatch | -150.0 MW (full charge) |
| BESS bus | 4 (0-indexed, MATPOWER bus 5) |

The storage element charges at maximum rate in a single-period solve because there is no future horizon for the optimizer to consider. This demonstrates the fundamental limitation: without inter-temporal coupling, storage dispatch is myopic.

## Workarounds

- **What:** No native workaround available. Multi-period DCOPF with inter-temporal storage would require either (a) building a custom Pyomo model from pandapower's network data, or (b) using the `runpm_storage_opf()` bridge which requires Julia + PandaModels.jl.
- **Why:** pandapower's DC OPF is architecturally single-period. The `timeseries` module provides sequential execution but not co-optimization. The PYPOWER solver has no mechanism for inter-temporal constraints.
- **Durability:** blocking -- the formulation cannot be expressed in pandapower's native OPF. The PandaModels.jl bridge could potentially provide this capability, but it requires a separate language runtime and its availability is not guaranteed in deployment environments.
- **Grade impact:** All three behavioral pass conditions (congestion reporting across hours, BESS arbitrage timing, SoC trajectory) require co-optimization across 24 hours, which is impossible in pandapower's native OPF.

## Timing

- **Wall-clock:** 0.80 s (includes capability inspection and single-snapshot baseline OPF)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a12_multiperiod_dcopf_storage.py`
