---
test_id: A-11
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
workaround_class: blocking
failure_reason: unsupported_in_installed_version
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "45b8d158"
wall_clock_seconds: null
timing_source: null
---

# A-11: distributed_slack_opf — SMALL

## Result: FAIL

## Reason

PowerModels.jl v0.21.5 does not natively support a distributed slack formulation for DC OPF; all built-in formulations use a single reference bus as the slack. This limitation was confirmed at the TINY functional tier and is identical at SMALL scale.

## Evidence

- **TINY result:** See `evaluations/powermodels/results/expressiveness/A-11_distributed_slack_opf_TINY.md` for the same failure documented at the functional tier.
- **Capability:** PowerModels.jl v0.21.5 does not support distributed slack OPF. [Source: research-version.md capability table]

## Implications

The absence of distributed slack support at SMALL scale (ACTIVSg 2000) confirms the gap is architectural rather than scale-dependent. Any implementation would require manual modification of the power balance constraints and variable definitions outside the standard PowerModels.jl API, representing a blocking gap for this test.
