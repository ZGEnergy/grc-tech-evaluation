---
test_id: C-4
tool: powermodels
dimension: scalability
network: SMALL
status: fail
workaround_class: blocking
blocked_by: A-5
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "abc8c20f"
wall_clock_seconds: null
timing_source: null
---

# C-4: scuc_scale — SMALL

## Result: FAIL

## Reason

C-4 measures SCUC scalability at SMALL scale, which requires SCUC to be expressible in PowerModels.jl; because A-5 (SCUC) fails with a blocking unsupported_in_installed_version status, the scalability test cannot be executed.

## Evidence

- **TINY result:** See `evaluations/powermodels/results/expressiveness/A-5_scuc_TINY.md` for the upstream failure that blocks this test.
- **Capability:** PowerModels.jl v0.21.5 does not support unit commitment (SCUC). [Source: research-version.md capability table]

## Implications

With no SCUC capability in the installed version, there is no scalability data to record for this test. The SCUC scalability grade cannot be assessed for PowerModels.jl v0.21.5.
