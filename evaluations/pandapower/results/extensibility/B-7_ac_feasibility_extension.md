---
test_id: B-7
tool: pandapower
dimension: extensibility
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-7: AC feasibility extension assessment (depends on A-4)

## Result: PASS

## Finding

A-4 (AC feasibility check on DC OPF dispatch) PASSED with no workaround required. pandapower's API naturally supports the DC OPF -> AC PF workflow within a single model context.

## Evidence

From A-4 test results:

1. DC OPF solved via `pp.rundcopp(net)` producing generator dispatch.
2. Generator setpoints were updated in-place: `net.gen.at[idx, "p_mw"] = dispatch_value`.
3. AC PF ran on the same `net` object: `pp.runpp(net, init="flat")`.
4. Voltage and thermal violations were directly accessible from `net.res_bus.vm_pu` and `net.res_line.loading_percent`.

No export/reimport, no model reconstruction, no workaround of any kind was needed. This is a first-class workflow in pandapower's API.

### API Calls Used

```python
pp.rundcopp(net)                          # Step 1: DC OPF
net.gen.at[idx, "p_mw"] = dispatch_value  # Step 2: Fix dispatch
pp.runpp(net, init="flat")                # Step 3: AC PF check
violations = net.res_bus["vm_pu"]         # Step 4: Check results
```

### Key Metrics from A-4

| Metric | Value |
|--------|-------|
| DC OPF converged | Yes |
| AC PF converged | Yes (flat start) |
| V min / V max | 0.982 / 1.064 pu |
| Max line loading | 86.3% |
| Thermal violations | 0 |
| Slack bus P difference | +45.8 MW (losses) |

## Workarounds

None required.

## Implications

The absence of any workaround for A-4 is a positive finding for extensibility. It means that the DC OPF and AC PF formulations share a common network model, and results from one analysis can feed directly into another without data translation. This is consistent with pandapower's single-model architecture where all analyses operate on the same `pandapowerNet` object.
