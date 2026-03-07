---
test_id: A-4
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 12.27
peak_memory_mb: null
loc: 165
solver: PYPOWER interior point + Newton-Raphson
timestamp: 2026-03-06T00:00:00Z
---

# A-4: Take DC OPF dispatch, run full ACPF on that dispatch

## Result: PASS

## Approach

1. Loaded ACTIVSg10k (~10,000 buses)
2. Solved DC OPF via `pp.rundcopp(net)` -- converged (objective: 2,437,763.82)
3. Extracted generator dispatch from `net.res_gen["p_mw"]`
4. Fixed generator active power to DC OPF values via `net.gen.at[idx, "p_mw"] = dispatch[idx]`
5. Ran ACPF on the same `net` object via `pp.runpp(net, init="dc")` -- converged with DC warm start
6. Identified voltage and thermal violations from results

All within the same model context -- no file export/reimport.

## Output

| Metric | Value |
|--------|-------|
| DC OPF converged | Yes |
| ACPF converged | Yes (DC warm start) |
| ACPF init method | dc_warm_start |
| ACPF wall-clock | 1.75 s |
| Same model context | Yes |
| Voltage violations (outside 0.95-1.05 pu) | 523 buses |
| Thermal violations (>100% loading) | 42 lines, 2 trafos |
| Voltage range | 0.868 -- 1.081 pu |
| Max line loading | 1,523.7% |
| Ext grid power difference | 2,850.3 MW |

The large number of violations is expected: DC OPF ignores reactive power, voltage magnitudes, and losses. The AC feasibility check correctly reveals these discrepancies.

## Workarounds

None required.

## Timing

- **Wall-clock:** 12.27 s (total: DC OPF + dispatch fixup + ACPF)
- **ACPF solve only:** 1.75 s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a4_ac_feasibility_medium.py`
