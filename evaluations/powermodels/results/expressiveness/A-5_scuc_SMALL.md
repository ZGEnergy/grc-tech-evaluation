---
test_id: A-5
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
workaround_class: blocking
failure_reason: unsupported_in_installed_version
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "0f7e3d47"
wall_clock_seconds: null
timing_source: null
---

# A-5: scuc — SMALL

## Result: FAIL

## Reason

PowerModels.jl v0.21.5 does not include a native unit commitment (SCUC/UC-OPF) formulation; the library is limited to continuous OPF relaxations and does not expose MILP commitment variables, min up/down time constraints, or startup cost modeling. This limitation was confirmed at the TINY functional tier and is identical at SMALL scale.

## Evidence

- **TINY result:** See `evaluations/powermodels/results/expressiveness/A-5_scuc_TINY.md` for the same failure documented at the functional tier.
- **Capability:** PowerModels.jl v0.21.5 does not support unit commitment (SCUC). [Source: research-version.md capability table]

## Implications

The inability to model SCUC at SMALL scale (ACTIVSg 2000) confirms that this is an architectural gap, not a scale-related limitation. PowerModels.jl cannot be used for any commitment-based market clearing workflow without a full external reimplementation of UC constraints, which represents a blocking gap for this rubric dimension.
