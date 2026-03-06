# A-8: Stochastic Timeseries Optimization (TINY)

- **Test ID:** A-8
- **Slug:** stochastic_timeseries
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PARTIAL

## Pass Condition

Tool natively supports scenario-indexed timeseries as part of optimization formulation, not just deterministic loop.

## Results

| Metric | Value |
|--------|-------|
| Native API exists | Yes (`n.set_scenarios()`) |
| Works with clean networks | Yes (verified with n.add()-built network) |
| Works with pypower-imported networks | No (crashes in find_bus_controls) |
| Wall clock | 0.338 s (crash, not full solve) |

### Finding

PyPSA 1.1.2 provides `n.set_scenarios()` for native two-stage stochastic programming. This API:

1. Replicates all network components (buses, lines, generators, loads) per scenario with MultiIndex naming
2. Creates scenario-indexed time-varying data columns
3. Solves a single optimization over all scenarios simultaneously

**Verified working** with networks built from scratch using `n.add()`.

**Crashes** with networks imported via `import_from_pypower_ppc()` due to a bug in `find_bus_controls()` which attempts to set bus control types using a flat index on a MultiIndex-indexed DataFrame.

### Error

```
KeyError: "Index(['30', '32', '33', '34', '35', '36', '37', '38', '39'],
dtype='object', name='bus') not in index"
```

Location: `pypsa/network/power_flow.py:1306` in `find_bus_controls()`

### Root Cause

`set_scenarios()` converts all component DataFrames to MultiIndex (`(scenario, name)`). The `find_bus_controls()` method in `determine_network_topology()` tries to use flat bus indices to index into the now-MultiIndex buses DataFrame, causing a KeyError.

## API

```python
n.set_scenarios(["s0", "s1", "s2"])
# Set per-scenario loads:
n.loads_t.p_set["s0", "load0"] = [...]
n.optimize(solver_name="highs")
# Results have MultiIndex columns: (scenario, component)
```

## LOC

~15 lines beyond network loading (set scenarios, populate per-scenario data, solve).

## Workarounds

1. **Rebuild network (fragile):** Reconstruct the network from scratch using `n.add()` instead of `import_from_pypower_ppc()`. This avoids the bus control bug but requires significant code to replicate the import.
2. **Deterministic loop (stable):** Solve each scenario independently in a loop. Loses the joint optimization benefit but avoids the bug entirely.

## Errors

- Native stochastic support crashes on pypower-imported networks due to MultiIndex/bus control incompatibility in `find_bus_controls()`. This appears to be a bug in PyPSA 1.1.2.
