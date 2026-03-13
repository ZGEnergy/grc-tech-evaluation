---
test_id: B-7
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 181fa512
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 3.387
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 85
solver: NLsolve (compute_ac_pf); HiGHS (DC OPF)
timestamp: 2026-03-11T00:00:00Z
---

# B-7: AC Feasibility Extension (TINY)

## Result: QUALIFIED PASS

## Approach

B-7 is a workaround classification and effort assessment for the AC feasibility checking workflow
established in A-4. A-4 achieved a QUALIFIED PASS: the workflow is clean and in-memory, but
requires two stable workarounds.

The B-7 test script (`test_b7_ac_feasibility_extension_tiny.jl`) reproduces the A-4 workflow,
measures timing, counts LOC, and formally classifies each workaround per `workaround-classification.md`.

### The extension approach (documented from A-4):

1. `PowerModels.solve_dc_opf(data, highs_opt)` — DC OPF to get optimal dispatch
2. In-place data dict mutation to fix generator outputs: `data["gen"][id]["pg"] = pg_pu`, `pmin = pmax = pg_pu`
3. Flat start: `bus["vm"] = 1.0; bus["va"] = 0.0` on all buses
4. `PowerModels.compute_ac_pf(data)` — AC power flow on the same in-memory dict
5. `PowerModels.update_data!(data, ac_result["solution"])` + `PowerModels.calc_branch_flow_ac(data)` — extract branch flows (Workaround 1)

No file export, no reimport, no model reconstruction. The workflow is entirely in-memory using the
same mutable data dict.

#### Is this a "clean extension" or fighting the tool?

This is a clean extension. PowerModels' design of using a mutable `Dict{String,Any}` as the primary
data model makes the DC OPF → ACPF handoff trivial: dispatch results are written directly into the
same dict that `compute_ac_pf` reads. The two-stage workflow aligns with how PowerModels is
architecturally intended to be used — the data dict is the central data exchange medium, not a
JuMP model object.

The two workarounds are documentation quality issues, not capability gaps.

## Output

| Metric | Value |
|--------|-------|
| DC OPF status | OPTIMAL |
| ACPF converged | true (Bool) |
| ACPF wall clock | 0.0179s |
| Total wall clock | 3.387s (includes Julia JIT on first invocation) |
| Thermal violations (A-4) | 4 branches |
| Voltage violations (A-4) | 0 buses |

### LOC breakdown:

| Component | LOC |
|-----------|-----|
| Core two-stage workflow (DC OPF → fix gen → flat start → ACPF → branch flows) | 17 |
| Full A-4 test script | 155 |
| B-7 assessment script | 85 |

The 17 core workflow lines span: `solve_dc_opf` call (1), generator fix loop (4), flat start loop (3),
`compute_ac_pf` (1), `update_data!` (1), `calc_branch_flow_ac` (1), violation extraction (6).
All boilerplate (function wrapper, logging, result dict population) excluded.

## Workarounds

### Workaround 1: Branch flow post-processing via `calc_branch_flow_ac`

- **What:** `compute_ac_pf` does not populate `result["solution"]["branch"]` with AC branch flows. Flows are obtained via `PowerModels.calc_branch_flow_ac(data)` after merging solution voltages with `PowerModels.update_data!`.
- **Why:** `compute_ac_pf` uses NLsolve directly (bypassing JuMP) and only returns bus voltages and generator dispatch in its solution dict.
- **Durability:** stable — `calc_branch_flow_ac` is a documented public API function, present since v0.18.3. The same pattern was used in A-2 and A-4. No undocumented internals accessed. Two explicit function calls.
- **Grade impact:** Minor — adds two public-API lines to the workflow; no capability limitation.
- **Version tested:** PowerModels.jl v0.21.5

### Workaround 2: Bool termination status — no NR diagnostics

- **What:** `compute_ac_pf` returns `termination_status` as a `Bool` (true = converged, false = failed), not a JuMP/MOI `TerminationStatusCode`. NR iteration count and convergence residual are not exposed.
- **Why:** `compute_ac_pf` delegates to NLsolve internally; NLsolve diagnostics (iterations, residual norm) are not forwarded to the PowerModels result dict.
- **Durability:** stable — the `Bool` return type is the documented behavior of `compute_ac_pf`, consistent across v0.18–v0.21. This is the designed API, not an internal quirk. No undocumented internals. Convergence verified via Bool + voltage profile quality check.
- **Grade impact:** Minor diagnostic quality limitation — convergence cannot be numerically verified via residual, only by Bool + post-solve voltage profile. Does not affect the ability to identify violations.
- **Version tested:** PowerModels.jl v0.21.5

**Overall workaround class: stable** (worst of two stable = stable).

## Timing

- **Wall-clock:** 3.387s (includes Julia JIT compilation on first invocation)
- **ACPF solve only:** 0.0179s
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not available (NLsolve internal, not exposed by `compute_ac_pf`)
- **Convergence residual:** not available (NLsolve internal, not exposed)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b7_ac_feasibility_extension_tiny.jl`

Key API sequence:

```julia

# Stage 1: DC OPF dispatch
dc_result = PowerModels.solve_dc_opf(data, highs_opt;
    setting = Dict("output" => Dict("duals" => true)))

# Fix generation dispatch (in-place dict mutation, no model reconstruction)
for (gen_id, gen_sol) in dc_result["solution"]["gen"]
    pg_pu = get(gen_sol, "pg", 0.0)
    data["gen"][gen_id]["pg"]   = pg_pu
    data["gen"][gen_id]["pmin"] = pg_pu
    data["gen"][gen_id]["pmax"] = pg_pu
end

# Flat start
for (_, bus) in data["bus"]
    bus["vm"] = 1.0; bus["va"] = 0.0
end

# Stage 2: AC PF — same data dict, no file I/O
ac_result = PowerModels.compute_ac_pf(data)

# Workaround 1: extract branch flows (compute_ac_pf doesn't populate branch)
PowerModels.update_data!(data, ac_result["solution"])
flow_data = PowerModels.calc_branch_flow_ac(data)

```
