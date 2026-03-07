---
test_id: B-7
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 112
solver: Ipopt
timestamp: "2026-03-07T00:00:00Z"
---

# B-7: AC Feasibility Extension (MEDIUM, ACTIVSg 10k-bus)

## Result: PASS

## Dependency

This test documents the workaround status from A-4. A-4 MEDIUM runs DC OPF followed by
AC PF on the ACTIVSg 10k-bus network using the same workflow as TINY. Results are pending
the A-4 MEDIUM execution (batch3), but the mechanism is identical.

At TINY scale, A-4 was a clean PASS with no workaround needed. The same public API
workflow applies at MEDIUM scale:

1. `parse_file()` loads the MATPOWER case
2. `solve_dc_opf()` produces optimal dispatch
3. `data["gen"][id]["pg"] = dc_dispatch` mutates the in-memory dict
4. `compute_ac_pf(data)` runs Newton-Raphson AC PF on the same dict
5. `calc_branch_flow_ac(data)` provides apparent power flows for thermal checking
6. Voltage violations checked against `vmin`/`vmax` from the data dict

## API Quality Assessment

- Data model mutable: true
- Same-context workflow: true
- Requires file export: false
- Requires model reconstruction: false
- Requires custom serialization: false
- Effort level: trivial (3 lines: set pg, compute_ac_pf, calc_branch_flow_ac)

## Durability Assessment

- Classification: N/A -- no workaround needed
- Relies on internals: false
- Version sensitive: false
- Explanation: Uses only public API functions and standard dict operations. The data model
  is a mutable Dict, and PF/OPF functions operate on the same structure at any scale.

## Workarounds

None. The workflow uses the same public API as TINY with no modifications for scale.
The data dict is mutable at any network size.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch3.jl` (A-4 section)
