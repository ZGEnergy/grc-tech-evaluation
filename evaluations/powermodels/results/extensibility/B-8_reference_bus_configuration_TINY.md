---
test_id: B-8
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 2460b2bb
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2.665
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 50
solver: HiGHS
timestamp: 2026-03-11T00:00:00Z
---

# B-8: Reference Bus Configuration (TINY)

## Result: QUALIFIED PASS

## Approach

Three reference bus / slack configurations were tested:

**(a) Default single slack** — bus 31, as specified by `bus_type = 3` in case39.m. Solved as-is.

**(b) Alternate single slack** — bus 1 substituted as reference. Changed via data dict mutation:

```julia

data["bus"]["31"]["bus_type"] = 2   # former slack → PV bus
data["bus"]["1"]["bus_type"]  = 3   # new slack bus

```

No model reconstruction, no re-parsing from file — fresh `parse_file` call only to avoid
contaminating config (a) data.

**(c) Distributed slack** — Not natively supported by PowerModels.jl v0.21.5. Requires manual
construction of a PTDF-based DC OPF via JuMP (~150 lines). Full implementation in
`test_b8_reference_bus_config.jl`. Documented here as a stable workaround (high effort,
entirely within documented public API).

**Single-slack API calls required:** 2 lines (set `bus_type = 2` on old ref, `bus_type = 3`
on new ref). No model reconstruction, no `instantiate_model` re-call.

## Output

| Configuration | Status | Objective ($/h) | Ref Bus | API Lines |
|---------------|--------|----------------|---------|-----------|
| (a) Default (bus 31) | OPTIMAL | 41,263.94 | 31 | 0 (default) |
| (b) Alternate (bus 1) | OPTIMAL | 41,263.94 | 1 | 2 |

**Dispatch invariance:** Max dispatch difference between (a) and (b): 6.7e-11 pu. Both configs
produce identical generation dispatch (same feasible region, same objective function).

**LMP behavior:** LMPs are numerically invariant to reference bus selection in DC OPF. Maximum
LMP difference between configs: 1.8e-8 $/MWh. This is correct and expected physics: in a DC OPF
LP formulation, the dual variables on power balance constraints (LMPs) are independent of the
voltage angle reference chosen. The LMP spread in this uncongested case is 3e-6 $/MWh (essentially
uniform), confirming no binding congestion with vanilla case39.m costs.

Sample LMPs (configs a and b, first 5 buses):

| Bus | LMP_a ($/MWh) | LMP_b ($/MWh) | Diff |
|-----|---------------|---------------|------|
| 1 | -1351.692002 | -1351.692002 | ~0 |
| 2 | -1351.692001 | -1351.692001 | ~0 |
| 3 | -1351.692002 | -1351.692002 | ~0 |
| 4 | -1351.692002 | -1351.692002 | ~0 |
| 5 | -1351.692002 | -1351.692002 | ~0 |

### Distributed slack (config c) summary:
- Native support: No
- Required effort: ~150 lines of manual JuMP code
- Components: `calc_basic_ptdf_matrix` + distributed PTDF derivation (`ptdf_dist = ptdf_single - ptdf_single * slack_weights`) + full OPF model construction + LMP extraction from LP duals
- Workaround class: stable (all components are documented public API)

## Workarounds

### Workaround: Distributed slack not natively supported

- **What:** No native distributed slack formulation in PowerModels.jl. Single-slack reference bus change is trivially supported via data dict mutation. Distributed slack requires manual PTDF-based OPF via JuMP.
- **Why:** PowerModels natively supports single-slack reference bus formulations. Distributed slack is not a standard MATPOWER-compatible feature and is not implemented.
- **Durability:** stable — the workaround uses only documented public APIs: `calc_basic_ptdf_matrix`, `make_basic_network`, and standard JuMP model construction. No undocumented internals. The distributed PTDF formula (`ptdf_dist = ptdf_single - ptdf * w`) is standard power systems math.
- **Grade impact:** Moderate effort (150 LOC) to achieve distributed slack. Single-slack configuration is near-zero effort (2 LOC). The single-slack API is clean; distributed slack is the gap.
- **Version tested:** PowerModels.jl v0.21.5

## Timing

- **Wall-clock:** 2.665s (includes Julia JIT on first invocation; both DC OPF solves)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b8_reference_bus_configuration_tiny.jl`

Single-slack reference bus change (key lines):

```julia

# Change reference bus from bus 31 to bus 1 — 2 lines, no model reconstruction
for (id, bus) in data_b["bus"]
    bid = parse(Int, id)
    if bid == 31;  bus["bus_type"] = 2; end  # old ref → PV bus
    if bid == 1;   bus["bus_type"] = 3; end  # new ref → slack
end

# Re-solve — same API, same optimizer, no instantiate_model re-call
result_b = PowerModels.solve_dc_opf(data_b, optimizer;
    setting = Dict("output" => Dict("duals" => true)))

```
