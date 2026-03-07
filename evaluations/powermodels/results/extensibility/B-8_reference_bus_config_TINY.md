---
test_id: B-8
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 11.40
peak_memory_mb: null
loc: 347
solver: HiGHS
timestamp: 2026-03-07T00:00:00Z
---

# B-8: Reference Bus Configuration

## Result: PASS

## Approach
Tested three slack bus configurations on IEEE 39-bus DC OPF:

**(a) Default single slack (bus 31):** Standard solve via `solve_dc_opf()`.

**(b) Different single slack (bus 1):** Changed reference bus by setting
`bus_type=2` on old ref (bus 31) and `bus_type=3` on new ref (bus 1) in the data
dict. No model reconstruction needed -- just 2 lines of dict mutation before calling
`solve_dc_opf()` again.

**(c) Distributed slack (load-proportional weights):** PowerModels has no native
distributed slack support. Required ~150 lines of manual JuMP code:
compute PTDF via `calc_basic_ptdf_matrix()`, derive distributed-slack PTDF
(`ptdf_dist = ptdf_single - ptdf_single * weights`), build a JuMP model with
power balance, line flow constraints, and quadratic cost objective, extract LMPs
from duals.

## Output
- Config (a) objective: 41,263.94 (bus 31 slack, OPTIMAL)
- Config (b) objective: 41,263.94 (bus 1 slack, OPTIMAL)
- Config (c) objective: 41,263.94 (distributed slack, OPTIMAL)
- Objectives match: true (all within 0.01)
- Dispatch invariant across configs: true (max diff a-vs-b: 0.0, a-vs-c: 8.0e-9)
- LMP range (a): 3.0e-6 (negligible congestion)
- LMP range (b): 3.0e-6
- LMP range (c): 0.0
- Max LMP diff a-vs-b: 0.0 (no congestion -> LMPs identical)
- Max LMP diff a-vs-c: 2703.38 (sign flip due to different slack convention)

## Workarounds
- **Single-slack reference bus change:** TRIVIAL -- set `bus_type=2` on old ref,
  `bus_type=3` on new ref in data dict. No model reconstruction.
- **Distributed slack:** MAJOR WORKAROUND -- no native support. Requires manual
  PTDF-based OPF via JuMP (~150 lines). PowerModels provides
  `calc_basic_ptdf_matrix` but the distributed-slack formulation and LMP extraction
  must be user-built. Classified as **stable** workaround since it uses only
  public API (`calc_basic_ptdf_matrix`) and standard JuMP constructs.

## Timing
- Wall-clock: 11.40s

## Test Script
Path: `evaluations/powermodels/tests/extensibility/test_b8_reference_bus_config.jl`
