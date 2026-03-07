---
test_id: A-11
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 0.272
peak_memory_mb: null
loc: 55
solver: "HiGHS"
timestamp: 2026-03-06T01:30:00Z
---

# A-11: Distributed Slack OPF

## Result: FAIL

## Approach

1. Searched for distributed slack options in `OptimalPowerFlowOptions` and `PowerFlowOptions`.
2. Ran single-slack DC OPF as baseline.
3. Tested distributed slack in ACPF (where it exists).
4. Compared single-slack vs distributed-slack ACPF results.

## Findings

### Distributed Slack in OPF

No `distributed_slack` or equivalent option exists in `OptimalPowerFlowOptions`. The DC OPF formulation uses a single reference bus. There is no way to specify participation factors or distribute the slack among generators in the OPF context.

### Distributed Slack in ACPF

`PowerFlowOptions` has a `distributed_slack` attribute (default: `False`). When set to `True`, the ACPF produces significantly different results:

| Metric | Single Slack | Distributed Slack |
|--------|-------------|-------------------|
| Converged | Yes | Yes |
| Max Vm diff (pu) | -- | 0.0085 |
| Max Va diff (deg) | -- | 20.65 |
| Max Sf diff (MW) | -- | 672.37 |
| Total P losses (MW) | 43.64 | 64.29 |

The differences are large, confirming distributed slack is genuinely active in the ACPF solver. The slack bus voltage and angle change substantially, and branch flows redistribute across the network.

### Generator Participation Factors

No `participation_factor` attribute found on generator objects. The distributed slack ACPF likely distributes slack proportionally to generator capacity or equally, but the allocation method is not configurable through the API.

## Why FAIL

The protocol requires a **distributed slack OPF** formulation where LMPs differ from single-slack in a physically consistent manner. GridCal provides:

- Distributed slack for **ACPF** (power flow) -- working correctly.
- No distributed slack for **OPF** -- the optimization always uses a single reference bus.

Since the test specifically requires distributed slack in the OPF context (affecting LMPs and optimal dispatch), and GridCal only supports it in ACPF, this is a fail. The ACPF distributed slack cannot produce LMPs (shadow prices are only available from OPF).

### Single-Slack DC OPF Baseline (from A-3)

| Metric | Value |
|--------|-------|
| Total gen (MW) | 6254.23 |
| LMP range ($/MWh) | 0.3 -- 0.3 (uniform) |
| Wall-clock (s) | 0.272 |

## Workarounds

None available. Distributed slack OPF would require modifying the optimization formulation, which GridCal's API does not support.

## Timing

- **Single-slack DC OPF:** 0.272s
- **Distributed-slack ACPF:** 1.186s

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a11_distributed_slack.py`
