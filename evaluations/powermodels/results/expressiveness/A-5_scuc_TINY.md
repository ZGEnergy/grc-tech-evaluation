---
test_id: A-5
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 8523d29e
status: fail
failure_reason: unsupported_in_installed_version
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T12:00:00Z
---

# A-5: 24-Hour SCUC as MILP

## Result: FAIL

## Approach

PowerModels.jl v0.21.5 does **not** natively support Security-Constrained Unit Commitment (SCUC). The tool is a steady-state single-period power network optimization library. Unit commitment -- requiring binary commitment variables, minimum up/down time constraints, startup/shutdown costs, and multi-period coupling -- is entirely outside its scope.

No `build_uc`, `build_scuc`, `solve_uc`, or equivalent functions exist in the PowerModels.jl API. The problem specification catalog (`build_opf`, `build_pf`, `build_ots`, `build_tnep`, `build_opb`) contains no unit commitment variant. The `replicate()` multi-network infrastructure provides a multi-period data structure, but it does not include UC binary variables, minimum up/down time constraints, or startup/shutdown logic.

This is recorded as `fail` with `failure_reason: unsupported_in_installed_version` rather than attempting to build a custom MILP from scratch. Building a complete SCUC formulation from raw JuMP primitives (using PowerModels only for data parsing) would not be a fair evaluation of the tool's expressiveness -- it would test JuMP's capabilities, not PowerModels'.

## Output

No test execution performed. The capability is absent from the installed version.

| Metric | Value |
|--------|-------|
| Native SCUC support | No |
| PowerModels version | v0.21.5 |
| Related functions searched | `build_uc`, `build_scuc`, `solve_uc`, `solve_mn_uc` -- none exist |
| Multi-network infrastructure | `replicate()` + `solve_mn_opf` exist but contain no UC formulation |
| Ecosystem packages | PowerModelsSecurityConstrained.jl addresses SCOPF, not SCUC |

## Context

PowerModels.jl focuses on single-period power network optimization. Its problem specification catalog covers: Power Flow (PF), Optimal Power Flow (OPF), Optimal Power Balance (OPB), Optimal Transmission Switching (OTS), and Transmission Network Expansion Planning (TNEP). Multi-period extensions exist via `replicate()` and `solve_mn_opf_strg` for storage-coupled OPF, but these do not include unit commitment decision variables.

The JuMP foundation means a user *could* assemble a SCUC MILP using PowerModels for data parsing only (~200+ lines of custom constraint code), but this tests JuMP's optimization modeling capabilities, not PowerModels' expressiveness as a power systems tool. [tool-specific]

## Workarounds

None attempted. The absence of native SCUC is a fundamental scope limitation of PowerModels.jl, not a workaround-addressable gap.

## Timing

No execution performed.

## Test Script

No test script executed. The existing `test_a5_scuc_tiny.jl` demonstrates that a user-assembled JuMP MILP can solve SCUC using PowerModels for data parsing, but this is recorded as context rather than a pass -- it would be unfair to credit or penalize the tool for hand-built JuMP code.

**Path:** `evaluations/powermodels/tests/expressiveness/test_a5_scuc_tiny.jl` (historical reference only)
