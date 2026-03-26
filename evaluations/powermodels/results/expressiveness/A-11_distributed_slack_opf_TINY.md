---
test_id: A-11
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: a660e68c
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 2.30
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 160
solver: "HiGHS (single-slack baseline only)"
timestamp: 2026-03-24T18:00:00Z
---

# A-11: DC OPF with Load-Proportional Distributed Slack

## Result: FAIL

## Approach

Capability absence verified against `research-version.md` and `research-api.md`. Three API paths were attempted programmatically:

1. `solve_dc_opf` with a `distributed_slack` setting -- no such parameter exists in PowerModels API
2. `solve_opf` with `DCPPowerModel` -- standard single-slack formulation only
3. `instantiate_model` with `build_opf` -- no distributed slack in any standard `build_*` function

A single-slack DC OPF baseline was run with HiGHS to confirm standard OPF works and to document LMP reference values.

## Output

### Single-slack baseline (for reference):

| Metric | Value |
|--------|-------|
| Status | OPTIMAL |
| LMPs extracted | 39 buses |
| LMP range | $7.7564 - $290.114/MWh |

### Capability investigation:

| API path | Result |
|----------|--------|
| `solve_dc_opf` with `distributed_slack` setting | No such parameter |
| `solve_opf` with `DCPPowerModel` | No distributed slack support |
| `instantiate_model` with `build_opf` | No distributed slack in any `build_*` |
| PowerModels formulations with distributed slack | None found |

None of the 18 built-in formulation types (DCPPowerModel, DCMPPowerModel, NFAPowerModel, BFAPowerModel, etc.) support distributed slack. The standard single-slack `DCPPowerModel` fixes one bus as the reference and balances all power at that bus. [tool-specific]

## Workarounds

- **What:** ~150-line custom JuMP PTDF-based DC OPF is required.
- **Why:** PowerModels.jl has no native distributed slack formulation. The `src/prob/` source tree contains `pf.jl`, `opf.jl`, `opb.jl`, `ots.jl`, `tnep.jl` -- no distributed slack formulation exists. The tool can be used only for network data parsing (`parse_file`, `make_basic_network`); the entire distributed slack DC OPF problem must be assembled manually in JuMP using PTDF matrix construction.
- **Durability:** blocking -- No PowerModels API path exists. The workaround requires assembling a complete optimization problem from scratch, bypassing all of PowerModels' problem specification capabilities. This is not a non-obvious use of an existing feature; it is a missing feature that requires substituting PowerModels with manual JuMP code.
- **Grade impact:** Direct negative impact on expressiveness grade for distributed slack. A blocking workaround on a primary expressiveness sub-question results in a score of C or below for this criterion.

## Timing

- **Wall-clock:** 2.30s
- **Timing source:** measured (warm JIT)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a11_distributed_slack_opf_tiny.jl`

The script documents the capability absence via inline evidence and runs the single-slack baseline to confirm standard OPF works at this network size.
