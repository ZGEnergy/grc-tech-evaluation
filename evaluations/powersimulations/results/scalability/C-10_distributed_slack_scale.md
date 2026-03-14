---
test_id: C-10
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "0346f66d"
status: fail
workaround_class: blocking
blocked_by: A-11
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 44
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# C-10: Distributed Slack DC OPF on MEDIUM

## Result: FAIL (cascaded failure from A-11)

## Approach

C-10 tests distributed slack DC OPF at MEDIUM scale (ACTIVSg 10k-bus). This requires the tool
to support a distributed slack formulation where the power balance reference is spread across
multiple generators according to participation factors, rather than concentrated at a single
reference bus.

This test is **blocked by A-11** (Distributed Slack DC OPF on TINY), which found that the
capability does not exist in PowerSimulations.jl or PowerModels.jl at any scale.

## Why This Fails

A-11 established that:

1. **DCPPowerModel** fixes one bus's voltage angle to 0 (single reference bus).
2. **PTDFPowerModel** constructs the PTDF matrix relative to a single slack bus.
3. **CopperPlatePowerModel** is single-node aggregation, not distributed slack.
4. **No API parameter, network model option, or formulation variant** distributes slack across buses.
5. **PTDFPowerModel's `use_slacks` option** adds slack variables for constraint feasibility
   relaxation (penalty-based soft constraints), not for distributing the power balance reference.

Since distributed slack is not available at TINY scale, scaling it to MEDIUM is not possible.

## Output

No output. Test not executed.

## Workarounds

None available. A manual workaround via JuMP constraint modification could approximate distributed
slack, but this would require building a custom formulation outside PSI's modeling framework
(removing the reference bus angle constraint and adding weighted power balance constraints). This
goes beyond "workaround" into "reimplementation."

## Timing

- **Wall-clock:** N/A (not executed)
- **Timing source:** N/A
- **Peak memory:** N/A

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c10_distributed_slack_scale.jl`

Stub script that emits the cascaded failure result as JSON.

## Observations

- **cascaded-failure:** C-10 is a cascaded failure from A-11. The distributed slack formulation
  is not available in PowerSimulations.jl/PowerModels.jl at any scale. This blocks both the
  expressiveness test (A-11) and the scalability test (C-10).
