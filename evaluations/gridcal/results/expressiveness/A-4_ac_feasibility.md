---
test_id: A-4
tool: gridcal
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 7.310
peak_memory_mb: null
loc: 50
solver: "HiGHS + Newton-Raphson"
timestamp: 2026-03-06T03:00:00Z
---

# A-4: AC Feasibility Check (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 2,485 generators.

## Approach

Same as TINY: DC OPF (HiGHS) -> fix dispatch -> ACPF (NR) -> identify violations.

## Output

| Metric | Value |
|--------|-------|
| DC OPF converged | Yes |
| DC OPF total gen (MW) | 150,916.9 |
| DC OPF active gens | 1,937 |
| ACPF converged | Yes |
| ACPF convergence error | 1.54e-07 |
| Vm range (pu) | 0.928 -- 1.095 |
| Voltage violations (0.95-1.05) | 143 (7 under, 136 over) |
| Thermal violations (>100%) | 22 |
| Max loading | 1586.9% |
| Total P losses (MW) | 2899.5 |

The DC-to-AC feasibility gap is clearly visible: 143 voltage violations and 22 thermal violations emerge when the lossless DC OPF dispatch is tested under full AC power flow. The max branch loading of 1587% indicates severe thermal violations on some branches.

## Scaling from TINY

| Metric | TINY (39 bus) | MEDIUM (10k bus) |
|--------|--------------|-----------------|
| ACPF converged | Yes | Yes |
| Voltage violations | 0 | 143 |
| Thermal violations | 0 | 22 |
| Total wall clock (s) | ~0.2 | 7.31 |

The MEDIUM network reveals far more DC-vs-AC feasibility gaps than TINY, as expected for a realistic large-scale network.

## Workarounds

None required. Both DC OPF and ACPF converge, and violations are fully identifiable.

## Timing

- **DC OPF:** 5.57s
- **ACPF:** 1.74s
- **Total wall-clock:** 7.31s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a4_ac_feasibility_medium.py`
