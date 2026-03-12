---
test_id: A-5
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 0f7e3d47
status: fail
workaround_class: blocking
blocked_by: null
failure_reason: unsupported_in_installed_version
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-5: SCUC (Security-Constrained Unit Commitment)

## Result: FAIL

## Approach

No test script was written or executed. This is a documented capability gap per version-gated execution rules.

Per `research-version.md` (capability table):

> **Security-Constrained Unit Commitment (SCUC):** no — Not provided. PowerModels is a steady-state network optimization library. Unit commitment (integer scheduling) is out of scope.

The capability report confirms:

> SCUC and SCED are **not** built-in; they require fully user-assembled JuMP models using PowerModels only for data parsing.

Per `research-api.md`:

> **What is NOT built-in:**
> - **SCUC**: Not supported. The evaluation test confirms this explicitly: "PowerModels has NO built-in SCUC. It is a steady-state OPF tool." A ~140-line user-assembled JuMP MILP is required. PowerModels is used only for data parsing (`parse_file`) and `make_basic_network`.

## Finding

PowerModels.jl v0.21.5 does not support SCUC natively. It is a steady-state single-period power network optimization library. Unit commitment — requiring binary commitment variables, minimum up/down time constraints, startup/shutdown costs, and ramp rate limits across a multi-period horizon — falls outside its scope.

The tool can parse the network (`parse_file`) and provides the JuMP modeling environment, but the user must assemble approximately 140+ lines of custom JuMP MILP code to express SCUC constraints. This is not a native capability.

## Capability Gap Evidence

1. `research-version.md` (installed version capability table): SCUC = **no**, since = "—", notes = "Not provided. PowerModels is a steady-state network optimization library."
2. `research-api.md`: "Supported built-in problem types: Power Flow (PF), OPF, OPB, OTS, TNEP, and multi-network variants. SCUC and SCED are **not** built-in."
3. PowerModels.jl official documentation (`specifications/`): No `build_uc`, `build_scuc`, or `build_unit_commitment` function exists.
4. Source tree: `src/prob/` directory contains `pf.jl`, `opf.jl`, `opb.jl`, `ots.jl`, `tnep.jl` — no `uc.jl` or `scuc.jl`.

## Workaround Assessment

Implementing SCUC in PowerModels.jl requires:
1. `PowerModels.parse_file` for network data loading
2. `PowerModels.make_basic_network` for normalized bus numbering
3. ~140 lines of custom JuMP MILP code for:
   - Binary commitment variables (`u[g,t] ∈ {0,1}`)
   - Startup/shutdown auxiliary variables
   - Min up/down time constraints (rolling horizon sums)
   - Ramp rate constraints between consecutive periods
   - Reserve requirements
   - Generator output bounds dependent on commitment status

This constitutes a **blocking** workaround: no API path exists to achieve SCUC without assembling the full MILP from scratch. The workaround requires writing a substantial custom optimization problem that the tool does not support.

**Generator cycling note (per cross-tool-watchpoints.md):** Even if SCUC were implemented via custom JuMP code, the base case39.m has a high capacity-to-load ratio with uniform costs. Modified Tiny's differentiated costs (hydro $5, nuclear $10, coal $25, gas CC $40 $/MWh) would be needed to force generator cycling during off-peak hours.

## Implications

This finding directly impacts the A-5 expressiveness criterion grade. SCUC is a core test of the tool's expressiveness for unit commitment workflows. A blocking limitation on a major feature sub-question results in a grade of C or below for the SCUC dimension.

PowerModels.jl is architecturally designed for steady-state single-period optimization. Multi-period commitment with binary variables is not within its design scope — this is an intentional design boundary, not a missing feature that could be added via a plugin or extension.
