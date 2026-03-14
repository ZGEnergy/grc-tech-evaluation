---
test_id: C-10
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v10
skill_version: v1
test_hash: da310747
status: fail
workaround_class: blocking
blocked_by: A-11
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-13T12:00:00Z
---

# C-10: Distributed Slack DC OPF Scale MEDIUM

## Result: FAIL

## Approach

C-10 measures distributed slack DC OPF scalability at MEDIUM scale (ACTIVSg 10k-bus). This test depends on A-11 (distributed slack OPF), which failed with a blocking workaround classification.

A-11 confirmed that PowerModels.jl v0.21.5 does not natively support distributed slack formulations. All built-in formulations use a single reference bus. The workaround requires ~150 lines of custom JuMP PTDF-based DC OPF code, bypassing PowerModels' problem specification API entirely.

While the custom PTDF-based approach could theoretically be scaled to MEDIUM, the A-11 failure was classified as blocking (not stable or fragile) because it requires assembling a complete optimization problem from scratch. This blocks the MEDIUM scalability assessment.

## Output

| Metric | Value |
|--------|-------|
| Prerequisite test | A-11 (distributed_slack_opf) |
| Prerequisite status | FAIL (blocking workaround) |
| Prerequisite failure reason | unsupported_in_installed_version |
| Distributed slack capability | Not available in PowerModels.jl v0.21.5 |
| Custom workaround feasible | Yes (~150-line PTDF-based JuMP OPF) |
| Workaround classification | Blocking (requires bypassing PowerModels API entirely) |

## Workarounds

- **What:** Distributed slack DC OPF is not available in PowerModels.jl. A ~150-line custom JuMP PTDF-based DC OPF would be required, using PowerModels only for data parsing.
- **Why:** PowerModels.jl v0.21.5 has no distributed slack formulation. No `build_*` function, formulation type, or API parameter supports distributed slack.
- **Durability:** blocking -- No PowerModels API path exists. The workaround requires assembling a complete optimization problem from scratch, bypassing all of PowerModels' problem specification capabilities.
- **Grade impact:** Direct negative impact on scalability grade for distributed slack. Cascaded from A-11 expressiveness failure.

## Timing

- **Wall-clock:** not applicable (blocked)
- **Timing source:** not applicable

## Test Script

No test script created -- test is blocked by A-11 prerequisite failure.
