---
test_id: B-8
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: b179c5dd
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 4.034
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 354
solver: HiGHS
timestamp: 2026-03-24T12:00:00Z
---

# B-8: Reference Bus Configuration (TINY)

## Result: QUALIFIED PASS

## Approach

Three reference bus / slack configurations tested with differentiated generator costs and 70% branch derating to produce congestion and non-uniform LMPs:

**(a) Default single slack** -- bus 31, as specified by `bus_type = 3` in case39.m.

**(b) Alternate single slack** -- bus 1 substituted as reference. Changed via data dict mutation:

```julia
data["bus"]["31"]["bus_type"] = 2   # former slack -> PV bus
data["bus"]["1"]["bus_type"]  = 3   # new slack bus
```

No model reconstruction, no re-parsing from file. Two lines of code.

**(c) Distributed slack** -- Not natively supported by PowerModels.jl v0.21.5. Implemented via manual PTDF-based DC OPF with load-proportional slack weights (~150 lines of JuMP code). Uses `calc_basic_ptdf_matrix` for PTDF computation, then constructs distributed PTDF: `ptdf_dist = ptdf_single - ptdf_single * slack_weights`. [tool-specific: no native distributed slack formulation]

**Solver settings:** HiGHS with `time_limit=300`, `presolve=on`, `threads=1`, `output_flag=false`.

## Output

| Configuration | Status | Objective (pu) | Ref Bus | API Lines |
|---------------|--------|----------------|---------|-----------|
| (a) Default (bus 31) | OPTIMAL | 12.47 | 31 | 0 (default) |
| (b) Alternate (bus 1) | OPTIMAL | 12.47 | 1 | 2 |
| (c) Distributed | OPTIMAL | 12.47 | load-proportional | ~150 |

**Dispatch invariance:** Max dispatch difference between (a) and (b): 4.974e-14 pu. Both configs produce identical generation dispatch.

**LMP behavior:** LMPs are numerically invariant to reference bus selection in DC OPF (physically correct). Maximum LMP difference between configs (a) and (b): 2.545e-08 $/MWh. LMP spread (config a): 0.8879 (non-uniform due to branch derating producing congestion).

Sample LMPs (configs a and b):

| Bus | LMP_a | LMP_b | Diff |
|-----|-------|-------|------|
| 1 | -0.2681 | -0.2681 | ~0 |
| 2 | -0.05 | -0.05 | ~0 |
| 3 | -0.9379 | -0.9379 | ~0 |
| 4 | -0.8106 | -0.8106 | ~0 |
| 5 | -0.7581 | -0.7581 | ~0 |

## Workarounds

### Workaround: Distributed slack not natively supported

- **What:** No native distributed slack formulation in PowerModels.jl. Single-slack reference bus change is trivially supported via data dict mutation. Distributed slack requires manual PTDF-based OPF via JuMP (~150 lines).
- **Why:** PowerModels natively supports single-slack reference bus formulations only. Distributed slack is not a standard MATPOWER-compatible feature.
- **Durability:** stable -- the workaround uses only documented public APIs: `calc_basic_ptdf_matrix`, `make_basic_network`, and standard JuMP model construction. The distributed PTDF formula (`ptdf_dist = ptdf_single - ptdf * w`) is standard power systems math.
- **Grade impact:** Moderate effort (~150 LOC) for distributed slack. Single-slack configuration is near-zero effort (2 LOC). The single-slack API is clean; distributed slack is the gap.
- **Version tested:** PowerModels.jl v0.21.5

## Timing

- **Wall-clock:** 4.034 s (includes JIT compilation on first invocation)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b8_reference_bus_config_tiny.jl`

Single-slack reference bus change (2 lines):

```julia
data_b["bus"]["31"]["bus_type"] = 2   # old ref -> PV
data_b["bus"]["1"]["bus_type"]  = 3   # new ref -> slack
result_b = PowerModels.solve_dc_opf(data_b, optimizer;
    setting=Dict("output" => Dict("duals" => true)))
```
