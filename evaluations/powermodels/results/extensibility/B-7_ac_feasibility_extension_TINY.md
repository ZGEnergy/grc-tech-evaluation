---
test_id: B-7
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 13.00
peak_memory_mb: null
loc: 112
solver: Ipopt
timestamp: 2026-03-07T00:00:00Z
---

# B-7: AC Feasibility Extension

## Result: PASS

## Approach
This test documents the workaround status from A-4 (DC OPF -> AC PF feasibility check).
A-4 was a clean PASS with no workaround needed. The workflow uses only public API
functions operating on the same mutable data Dict:

1. `parse_file()` to load MATPOWER case
2. `solve_dc_opf()` with HiGHS to get optimal dispatch
3. Set `data["gen"][id]["pg"] = dc_dispatch` for all generators (in-place dict mutation)
4. `compute_ac_pf(data)` on the same dict (no file I/O, no model rebuild)
5. `calc_branch_flow_ac(data)` for thermal violation check
6. Compare Vm against vmin/vmax for voltage violations

## Output
- DC OPF termination: OPTIMAL
- AC PF converged: true (on flat start)
- Workaround needed: No
- Workaround class: none

API quality assessment:
- Data model mutable: true
- Same-context workflow: true
- Requires file export: false
- Requires model reconstruction: false
- Requires custom serialization: false
- Effort level: trivial (3 lines: set pg, compute_ac_pf, calc_branch_flow_ac)

Durability assessment:
- Classification: N/A -- no workaround needed
- Relies on internals: false
- Version sensitive: false

## Workarounds
None. The data model is a mutable Dict and PF/OPF functions operate on the same
data structure. No workaround was required.

## Timing
- Wall-clock: 13.00s (dominated by Ipopt compilation on first use)

## Test Script
Path: `evaluations/powermodels/tests/extensibility/test_b7_ac_feasibility_extension.jl`
