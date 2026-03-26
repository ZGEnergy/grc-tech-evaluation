---
test_id: B-8
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "dad5cf97"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.05
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 399
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-13T00:00:00Z"
---

# B-8: Solve DC OPF with three slack configurations and compare LMPs

## Result: QUALIFIED PASS

## Approach

In pandapower, the slack (reference) bus is defined by `ext_grid` elements. The tool has no single API call to change the reference bus. Reconfiguring the slack requires:

1. Remove the existing `ext_grid` element and its cost function
2. Create a `gen` element at the old slack bus (to preserve the generator)
3. Remove any existing `gen` at the new slack bus
4. Create a new `ext_grid` at the new slack bus
5. Transfer cost functions between element types

Three configurations were tested:

| Config | Slack Bus (pp) | Slack Bus (MATPOWER) | Generator Type |
|--------|---------------|---------------------|----------------|
| 1 (default) | 30 | 31 | Nuclear |
| 2 | 29 | 30 | Hydro |
| 3 | 33 | 34 | Coal |

## Output

### Convergence and Objectives

| Config | Converged | Objective ($) | vs Config 1 |
|--------|-----------|---------------|-------------|
| 1 (default) | Yes | 156,929 | baseline |
| 2 (hydro slack) | Yes | 158,731 | +1.15% |
| 3 (coal slack) | Yes | 158,643 | +1.09% |

### LMP Comparison (sample buses)

| Bus (pp) | Config 1 | Config 2 | Config 3 | Diff 1-2 | Diff 1-3 |
|----------|----------|----------|----------|----------|----------|
| 0 | 88.13 | 89.82 | 89.82 | 1.69 | 1.69 |
| 2 | 55.77 | 62.31 | 62.31 | 6.54 | 6.54 |
| 5 | 36.85 | 43.95 | 43.95 | 7.10 | 7.10 |
| 18 | 54.60 | 54.60 | 52.50 | 0.00 | 2.10 |
| 33 | 54.60 | 54.60 | 52.50 | 0.00 | 2.10 |

**Maximum LMP change:** 8.58 $/MWh (between configs 1 and 2/3)

### LMP Statistics

| Config | Min LMP | Max LMP | Mean LMP | Spread |
|--------|---------|---------|----------|--------|
| 1 | 12.09 | 88.13 | 44.71 | 76.05 |
| 2 | 11.79 | 89.82 | 48.45 | 78.04 |
| 3 | 11.79 | 89.82 | 48.23 | 78.04 |

### Observations

- Configs 2 and 3 produce nearly identical LMPs at most buses, differing mainly at the buses directly connected to the new slack (bus 18/33 in config 3 shows 52.50 vs 54.60).
- The objective increases by ~1% when moving the slack from the default bus, likely because the nuclear generator at bus 31 (default slack) has lower marginal cost than hydro (bus 30) or coal (bus 34).
- LMP changes are consistent and systematic -- not random numerical noise.

## Workarounds

- **What:** Slack bus reconfiguration requires 5-6 API calls to remove/recreate `ext_grid` and `gen` elements with manual cost function transfer. There is no single `set_slack_bus()` or `set_reference_bus()` API call.
- **Why:** pandapower architecturally ties the slack bus to the `ext_grid` element type. An `ext_grid` is fundamentally different from a `gen` -- it has different columns, different result tables, and different treatment in the OPF. Changing the slack bus means changing the element type of the generator at that bus.
- **Durability:** stable -- All operations use documented public API (`pp.create_ext_grid()`, `pp.create_gen()`, `pp.create_poly_cost()`, DataFrame `drop()`). The approach is verbose but will not break on version upgrades.
- **Grade impact:** The slack is configurable without model reconstruction in the sense that all modifications are in-place on the same network object. However, the process is verbose, error-prone (cost functions must be manually transferred between element types), and requires understanding the ext_grid/gen distinction.

## Timing

- **Wall-clock:** 1.05 s (3 network loads + 3 OPF solves)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b8_reference_bus_config.py`

Key API pattern for moving the slack bus:

```python
# Remove old ext_grid
net.ext_grid.drop(old_idx, inplace=True)
net.poly_cost.drop(old_cost_idx, inplace=True)

# Create gen at old slack bus
new_gen = pp.create_gen(net, bus=old_bus, p_mw=pmax/2, controllable=True)
pp.create_poly_cost(net, element=new_gen, et="gen", ...)

# Create ext_grid at new slack bus
new_ext = pp.create_ext_grid(net, bus=new_bus, vm_pu=1.0)
net.ext_grid.at[new_ext, "controllable"] = True
pp.create_poly_cost(net, element=new_ext, et="ext_grid", ...)
```
