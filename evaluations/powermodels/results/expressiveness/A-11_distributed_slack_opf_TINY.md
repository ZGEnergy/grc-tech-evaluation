---
test_id: A-11
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: ed1721bb
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 2.29
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 160
solver: "HiGHS (single-slack baseline only)"
timestamp: 2026-03-13T00:00:00Z
---

# A-11: DC OPF with Load-Proportional Distributed Slack

## Result: FAIL

## Approach

Capability absence verified against `research-version.md` and `research-context.md`. Three API paths were attempted programmatically:

1. `solve_dc_opf` with a `distributed_slack` setting — no such parameter exists in PowerModels API
2. `solve_opf` with `DCPPowerModel` — standard single-slack formulation only
3. `instantiate_model` with `build_opf` — no distributed slack in any standard `build_*` function

A single-slack DC OPF baseline was run with HiGHS to confirm standard OPF works and to document LMP reference values.

## Output

### Single-slack baseline (for reference):

| Metric | Value |
|---|---|
| Status | OPTIMAL |
| LMPs extracted | 39 buses |
| LMP range | $7.76 – $290.11/MWh |

#### Capability investigation:

| API path | Result |
|---|---|
| `solve_dc_opf` with `distributed_slack` setting | No such parameter |
| `solve_opf` with `DCPPowerModel` | No distributed slack support |
| `instantiate_model` with `build_opf` | No distributed slack in any `build_*` |
| PowerModels formulations with distributed slack | None found |

## Workarounds

- **What:** ~150-line custom JuMP PTDF-based DC OPF is required.
- **Why:** PowerModels.jl has no native distributed slack formulation. The `src/prob/` source tree contains `pf.jl`, `opf.jl`, `opb.jl`, `ots.jl`, `tnep.jl` — no distributed slack formulation exists. The tool can be used only for network data parsing (`parse_file`, `make_basic_network`); the entire distributed slack DC OPF problem must be assembled manually in JuMP using PTDF matrix construction.
- **Durability:** blocking — No PowerModels API path exists. The workaround requires assembling a complete optimization problem from scratch, bypassing all of PowerModels' problem specification capabilities. This is not a non-obvious use of an existing feature; it is a missing feature that requires substituting PowerModels with manual JuMP code.
- **Grade impact:** Direct negative impact on expressiveness grade for distributed slack. A blocking workaround on a primary expressiveness sub-question results in a score of C or below for this criterion.

## Finding

PowerModels.jl v0.21.5 does not support distributed slack formulations. The standard `DCPPowerModel` fixes one bus as the reference and balances all power at that bus. No API parameter, formulation type, or `build_*` function provides distributed slack capability.

The workaround confirmed in test B-8 requires ~150 lines of custom JuMP PTDF-based OPF code, using PowerModels only for data parsing. This exceeds the "non-obvious but workable" threshold for a stable workaround.

`research-context.md` confirms: "Distributed slack: No built-in support. Requires manual PTDF-based DC OPF construction (~150 lines in test B-8)."

## Timing

- **Wall-clock:** 2.29s
- **Timing source:** measured (warm JIT)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a11_distributed_slack_opf_tiny.jl`

The script documents the capability absence via inline evidence and runs the single-slack baseline to confirm standard OPF works at this network size.
