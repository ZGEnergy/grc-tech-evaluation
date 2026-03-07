---
test_id: A-4
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.528
peak_memory_mb: null
loc: 55
solver: "NR (built-in)"
timestamp: 2026-03-06T01:30:00Z
---

# A-4: AC Feasibility Check (DC OPF dispatch -> ACPF)

## Result: PASS

## Approach

1. Ran DC OPF via `vge.linear_opf()` with HiGHS to get optimal dispatch (6254.23 MW total).
2. Reloaded grid from the same MATPOWER file (no export/reimport to external format).
3. Set each generator's `gen.P` to the DC OPF dispatch value.
4. Ran full ACPF via `vge.power_flow()` with Newton-Raphson solver.
5. Inspected voltage magnitudes and branch loading for violations.

All steps performed within the same model context using the GridCal API directly.

## Output

| Metric | Value |
|--------|-------|
| DC OPF converged | Yes |
| DC OPF total gen (MW) | 6254.23 |
| ACPF converged | Yes |
| ACPF convergence error | 3.75e-11 |
| Vm range (pu) | 0.982 -- 1.064 |
| Va range (deg) | -5.78 -- 16.60 |
| Voltage violations (0.95--1.05 band) | 2 buses |
| Thermal violations (>100% loading) | 0 branches |
| Max branch loading (%) | 98.72 |
| Total P losses (MW) | 49.21 |

### Voltage Violations Identified

| Bus Index | Vm (pu) | Type |
|-----------|---------|------|
| 24 | 1.0563 | over-voltage |
| 35 | 1.0636 | over-voltage |

No thermal violations were found -- the DC OPF dispatch respects thermal limits in the AC solution, though two buses slightly exceed the 1.05 pu voltage upper bound.

## Feasibility Assessment

- DC OPF dispatch is achievable within the same model context (no file export/reimport required).
- Voltage violations are identifiable from `np.abs(results.voltage)`.
- Thermal violations are identifiable from `results.loading`.
- Both violation types can be programmatically detected post-ACPF.

## Workarounds

None required.

## Timing

- **DC OPF:** 0.121s
- **ACPF:** 1.407s
- **Total wall-clock:** 1.528s

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a4_ac_feasibility.py`
