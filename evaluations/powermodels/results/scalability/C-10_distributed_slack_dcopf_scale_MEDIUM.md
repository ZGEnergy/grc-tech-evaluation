---
test_id: C-10
tool: powermodels
dimension: scalability
network: MEDIUM
status: fail
workaround_class: blocking
blocked_by: A-11
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "823ca6ca"
wall_clock_seconds: null
timing_source: null
---

# C-10: distributed_slack_dcopf_scale — MEDIUM

## Result: FAIL

## Reason

C-10 measures distributed slack DC OPF scalability at MEDIUM scale, which requires the distributed slack formulation to be supported; because A-11 (distributed_slack_opf) fails with a blocking unsupported_in_installed_version status, the scalability test cannot be executed.

## Evidence

- **TINY result:** See `evaluations/powermodels/results/expressiveness/A-11_distributed_slack_opf_TINY.md` for the upstream failure that blocks this test.
- **Capability:** PowerModels.jl v0.21.5 does not support distributed slack OPF. [Source: research-version.md capability table]

## Implications

With no distributed slack capability in the installed version, there is no scalability data to record at MEDIUM scale (ACTIVSg 10000). The distributed slack scalability grade cannot be assessed for PowerModels.jl v0.21.5.
