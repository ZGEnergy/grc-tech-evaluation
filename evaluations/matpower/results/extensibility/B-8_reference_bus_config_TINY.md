---
test_id: B-8
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.2484
peak_memory_mb: null
loc: 80
timestamp: "2026-03-06T00:00:00Z"
---

# B-8: Reference Bus Configuration on TINY

## Result: QUALIFIED PASS

Parts (a) and (b) pass cleanly. Part (c) distributed slack is supported for PTDF
computation but not for the OPF formulation, requiring a stable workaround.

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Wall clock:** 0.25 seconds (all three configurations)

## Configuration Results

### (a) Default Single Slack (Bus 31)

- Converged: YES
- Objective: 41,263.94
- LMP range: [13.5169, 13.5169] $/MWh (uniform -- no binding flow limits)

### (b) Different Single Slack (Bus 39)

- Reference bus changed from 31 to 39 via two struct assignments:

  ```matlab
  mpc.bus(old_ref_idx, BUS_TYPE) = PV;   % demote old ref
  mpc.bus(new_ref_idx, BUS_TYPE) = REF;  % promote new ref
  ```

- Converged: YES
- Objective: 41,263.94 (diff: 3.6e-11)
- LMP range: [13.5169, 13.5169] $/MWh (identical to (a))
- Max dispatch difference vs (a): 2.3e-12 MW

The DC OPF economic dispatch and LMPs are invariant to reference bus choice, as
expected. The reference bus only affects voltage angle values, not the optimization
feasible set. With no binding flow constraints on case39, all LMPs are uniform.

### (c) Custom-Weighted Distributed Slack

**MATPOWER OPF does not support distributed slack natively.** The OPF formulation
uses a single reference bus internally. However, distributed slack IS supported for
PTDF matrix computation:

```matlab
slack_weights = zeros(nb, 1);
% ... set generation-proportional weights ...
H_dist = makePTDF(mpc, slack_weights);
```

- Generation-proportional weights: non-zero at 10 generator buses
- Distributed-slack PTDF differs from single-slack PTDF (max diff: 0.91)
- Flows computed with the same bus injections are identical because the case has
  no binding constraints and the injection vector sums to zero

**Workaround for distributed-slack OPF:** Use the PTDF-based DC OPF reformulation
(construct the LP/QP manually using `makePTDF` with distributed slack weights).
This is a stable workaround but requires reimplementing the OPF rather than using
`rundcopf`. The PTDF is well-documented and the reformulation is standard.

## API Assessment

**Low friction for (a) and (b).** Changing the reference bus requires exactly two
lines: demote old ref to PV, promote new bus to REF. No model rebuild, no
reinitialization. The mutable struct model makes this trivial.

**Moderate friction for (c).** Distributed slack in the OPF requires building a
custom optimization problem using the PTDF matrix. `makePTDF(mpc, weights)` provides
the distributed-slack sensitivity matrix, but the OPF wrapper `rundcopf` does not
accept it. This is a documented architectural limitation: the OPF uses the B-theta
formulation which requires a single angle reference, not the PTDF formulation which
supports distributed slack naturally.

## LMP Comparison

| Bus | LMP (a) | LMP (b) | Diff |
|-----|---------|---------|------|
| 1 | 13.5169 | 13.5169 | 0.000000 |
| 10 | 13.5169 | 13.5169 | 0.000000 |
| 16 | 13.5169 | 13.5169 | 0.000000 |
| 25 | 13.5169 | 13.5169 | 0.000000 |
| 31 | 13.5169 | 13.5169 | 0.000000 |
| 39 | 13.5169 | 13.5169 | 0.000000 |

All LMPs are uniform because case39 has no `RATE_A` branch flow limits.

## Test Script

`evaluations/matpower/tests/extensibility/test_b8_reference_bus_config_tiny.m`
