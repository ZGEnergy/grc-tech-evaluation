---
test_id: A-6
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
workaround_class: blocking
blocked_by: A-5
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "88fa3558"
wall_clock_seconds: null
timing_source: null
---

# A-6: sced — SMALL

## Result: FAIL

## Reason

A-6 (SCED) requires a commitment schedule from A-5 (SCUC) as a prerequisite input; because A-5 fails with a blocking unsupported_in_installed_version status, no commitment schedule is available and A-6 cannot be executed.

## Evidence

- **TINY result:** See `evaluations/powermodels/results/expressiveness/A-6_sced_TINY.md` for the same failure documented at the functional tier.
- **Capability:** PowerModels.jl v0.21.5 does not support unit commitment (SCUC), which is required to produce the commitment schedule that A-6 fixes before solving economic dispatch. [Source: research-version.md capability table]

## Implications

The SCED test is blocked by the SCUC gap. Both stages of the two-stage UC/ED workflow are unavailable in PowerModels.jl v0.21.5, representing a complete absence of commitment-aware dispatch capability at SMALL scale.
