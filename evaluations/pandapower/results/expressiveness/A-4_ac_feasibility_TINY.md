---
test_id: A-4
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.21
peak_memory_mb: null
loc: 130
solver: PYPOWER interior point (DC OPF) + Newton-Raphson (ACPF)
timestamp: 2026-03-06T00:00:00Z
---

# A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

## Result: PASS

## Approach

1. Loaded IEEE 39-bus network via `from_mpc()`.
2. Solved DC OPF using `pp.rundcopp(net)` to obtain generator dispatch (replicating A-3).
3. Fixed generator active power to DC OPF dispatch values by setting `net.gen.at[idx, "p_mw"]` for each generator.
4. Ran ACPF on the same `net` object with `pp.runpp(net, init="flat")` -- flat start converged successfully.
5. Extracted voltage violations and thermal violations from `net.res_bus.vm_pu` and `net.res_line.loading_percent`.

The entire workflow was done within the same model context (same `net` object). No export/reimport was required. This is a natural workflow in pandapower.

## Output

| Metric | Value |
|--------|-------|
| DC OPF converged | Yes |
| DC OPF objective | 41,263.94 |
| ACPF converged | Yes (flat start) |
| ACPF init method | flat |

### Voltage Profile

| Metric | Value |
|--------|-------|
| V min (pu) | 0.982 |
| V max (pu) | 1.064 |
| V mean (pu) | 1.025 |
| Buses with V > 1.05 pu | 5 |

Voltage violations (V > 1.05 pu):

| Bus | vm_pu |
|-----|-------|
| 24 | 1.0534 |
| 25 | 1.0528 |
| 27 | 1.0536 |
| 28 | 1.0532 |
| 35 | 1.0636 |

### Thermal Loading

| Metric | Value |
|--------|-------|
| Max line loading | 86.3% |
| Mean line loading | 40.3% |
| Thermal violations (>100%) | 0 |
| Max trafo loading | 78.6% |
| Trafo violations (>100%) | 0 |

### Reactive Power

| Metric | Value |
|--------|-------|
| Q gen min | -7.87 Mvar |
| Q gen max | 218.24 Mvar |
| Q limit violations | 1 |

### Slack Bus Power Difference

| Metric | Value |
|--------|-------|
| Ext grid P (DC OPF) | 646.0 MW |
| Ext grid P (ACPF) | 691.8 MW |
| Difference | +45.8 MW |

The 45.8 MW increase at the slack bus reflects network losses that are absent in the lossless DC OPF formulation.

## Workarounds

None required.

pandapower's API naturally supports this workflow: modify generator setpoints in-place, then re-solve power flow on the same network object. Voltage and thermal violations are directly accessible from result DataFrames.

## Timing

- **Wall-clock:** 1.21 s (including DC OPF + ACPF)
- **ACPF solve only:** 1.03 s
- **Peak memory:** not measured
- **ACPF convergence:** flat start, no DC warm start needed

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a4_ac_feasibility.py`
