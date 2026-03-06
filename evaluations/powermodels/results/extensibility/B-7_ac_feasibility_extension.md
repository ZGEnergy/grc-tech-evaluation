---
test_id: B-7
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T21:00:00Z
---

# B-7: AC Feasibility Extension Audit (case39)

## Result: PASS (no workaround needed)

## Summary

A-4 (AC PF feasibility check on DC OPF dispatch) required **no workaround**. The DC OPF to AC PF workflow is achievable within the same model context using PowerModels' native API:

1. Solve DC OPF via `solve_dc_opf()` -- returns dispatch as Dict
2. Set generator `pg` values in a fresh data dict
3. Run `compute_ac_pf!(data)` -- Newton-Raphson in-place solve
4. Check voltage/thermal violations from the modified data dict

## Workaround Classification

**None required.** The A-4 workflow uses only documented PowerModels functions:
- `solve_dc_opf()` for DC OPF
- `compute_ac_pf!()` for AC power flow
- `calc_branch_flow_ac()` for branch flow calculation

## API Inconsistency Noted

While no workaround was needed, there is an API inconsistency worth documenting:

- `compute_dc_pf(data)` returns a result Dict and does NOT modify `data`
- `compute_ac_pf!(data)` returns `Nothing` and modifies `data` in-place

The `!` convention (mutating function) is standard Julia, but the asymmetry between DC and AC PF functions could confuse users. The DC PF function requires `update_data!()` to propagate results, while AC PF does it automatically.

## Violation Detection Capability

A-4 demonstrated that voltage and thermal violations are identifiable after AC PF:

| Violation Type | Detection Method | Count (case39) |

|---------------|-----------------|----------------|

| Voltage magnitude | `data["bus"][bid]["vm"]` vs limits | 5 buses (minor, within 1.4% of limit) |

| Thermal loading | `calc_branch_flow_ac(data)` vs `rate_a` | 0 branches |

## Durability Assessment

N/A -- no workaround to assess for durability. The native API pathway is stable.

## Test Script

See A-4: `evaluations/powermodels/tests/expressiveness/A4_ac_feasibility.jl`
