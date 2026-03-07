---
test_id: B-7
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.608
peak_memory_mb: null
loc: 125
solver: "HiGHS + NR"
timestamp: 2026-03-06T02:30:00Z
---

# B-7: AC Feasibility Extension

## Result: PASS

## Approach

B-7 checks whether A-4 (DC OPF dispatch -> ACPF verification) required any workaround, and if so, classifies it.

A-4 passed without any workaround. This test re-executes the A-4 workflow to confirm.

## A-4 Workflow (No Workaround Needed)

1. Load grid via `vge.open_file()`
2. Run DC OPF via `vge.linear_opf()` -- get `results.generator_power`
3. Load fresh grid via `vge.open_file()`
4. Set each `gen.P = dispatch[i]`
5. Run ACPF via `vge.power_flow()` with `SolverType.NR`
6. Inspect `results.voltage` and `results.loading` for violations

## Confirmation Results

| Metric | Value |
|--------|-------|
| DC OPF total gen (MW) | 6254.23 |
| ACPF converged | Yes |
| Vm range (pu) | 0.982 -- 1.064 |
| Max branch loading (%) | 98.72 |

## Workaround Classification: None

All steps use the documented public API:
- `vge.open_file()` for MATPOWER loading
- `vge.linear_opf()` for DC OPF
- `gen.P` setter for dispatch application
- `vge.power_flow()` for ACPF
- `results.voltage` and `results.loading` for violation detection

No file export/reimport, no internal API access, and no source patching required.

## Timing

- **Total wall-clock:** 1.608s (DC OPF + ACPF)

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b7_ac_feasibility_extension.py`
