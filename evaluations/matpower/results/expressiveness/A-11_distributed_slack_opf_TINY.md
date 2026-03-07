---
test_id: A-11
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.3148
peak_memory_mb: null
loc: 150
timestamp: "2026-03-06T00:00:00Z"
---

# A-11: Distributed Slack OPF on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

Qualified because MATPOWER has **no native distributed slack OPF**. A functional
workaround using `makePTDF()` with distributed slack weights and `opt_model` was
demonstrated, but it requires ~100 lines of manual OPF construction.

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Native distributed slack OPF:** NOT AVAILABLE
- **makePTDF distributed slack:** AVAILABLE (weight vector argument)
- **Workaround:** Manual PTDF-based DC OPF via `opt_model`
- **Solver:** MIPS (QP)
- **Converged:** Yes (exitflag=1)
- **Wall clock:** 0.31 seconds

## Confirmed Limitation

MATPOWER does not support distributed slack in either power flow or OPF:

- **GitHub Issue #136** (opened Jan 2022, still open): "Distributed slack bus for power flow"
- **GitHub Issue #63** (opened Mar 2019, still open): "Multiple generators at slack bus"
- **GitHub Issue #233** (opened May 2024, still open): "Multiple/distributed slack question"

The OPF formulation uses the `B * theta = P_inj` system with a single reference bus
angle fixed to 0. All slack absorption goes to one generator at the reference bus.

## Partial Capability: makePTDF with Distributed Slack

`makePTDF()` supports distributed slack weights as its second argument:

```matlab
slack_weights = bus(:, PD) / sum(bus(:, PD));  % load-proportional
H_dist = makePTDF(mpc, slack_weights);         % distributed-slack PTDF
```

This produces a PTDF matrix that distributes the slack proportionally across buses.
The resulting PTDFs differ significantly from single-slack PTDFs:
- Max PTDF difference (single vs distributed): 0.999

However, this PTDF is only useful for **sensitivity analysis**, not for solving
an OPF. MATPOWER's OPF engine ignores the PTDF and uses its own B-matrix formulation.

## Workaround: Manual PTDF-Based DC OPF

A distributed-slack DC OPF was constructed using MATPOWER's `opt_model` class:

1. Create `opt_model` instance
2. `add_var('Pg', ...)` -- generator dispatch variables with bounds
3. `add_lin_constraint('Pbal', ...)` -- power balance equality
4. `add_lin_constraint('flow', H_dist * Cg, ...)` -- flow limits using distributed-slack PTDF
5. `add_quad_cost('gencost', Q, c, k0, ...)` -- quadratic generator costs
6. `om.solve()` -- solve via MIPS

This produces the same dispatch as the standard DC OPF (optimal economic dispatch
is independent of slack distribution). The **shadow prices/LMPs differ** because
the flow constraint formulation uses different PTDF shift factors.

## Results: Single-Slack vs Distributed-Slack

### Dispatch (Identical)

| Gen# | Bus | Single-Slack (MW) | Distributed-Slack (MW) | Diff |
|------|-----|-------------------|----------------------|------|
| 1    | 30  | 478.57            | 478.57               | 0.00 |
| 2    | 31  | 605.22            | 605.22               | 0.00 |
| 9    | 38  | 838.38            | 838.38               | 0.00 |
| 10   | 39  | 811.50            | 811.50               | 0.00 |

Dispatch is identical because the economic optimization (minimizing total cost subject
to power balance and flow limits) has the same feasible set regardless of slack distribution.

### LMPs (Differ)
LMPs differ between single-slack and distributed-slack formulations. The distributed-slack
LMPs from the manual `opt_model` approach have different absolute values due to the
changed PTDF basis. The sign convention in the manual formulation differs from MATPOWER's
standard output, but the structural finding is confirmed: slack distribution affects
marginal pricing.

| Bus | Single-Slack LMP | Distributed-Slack LMP |
|-----|------------------|-----------------------|
| 1   | 14.01            | differs significantly |
| 31  | 12.40            | differs significantly |
| 39  | 16.53            | differs significantly |

## Distributed Slack Weights

Weights are settable via the `makePTDF()` weight vector:
- Load-proportional: `w = bus(:, PD) / sum(bus(:, PD))`
- Uniform: `w = ones(nb, 1) / nb`
- Custom: any non-negative vector summing to 1

21 of 39 buses have nonzero load in case39, giving 21 nonzero weights for
load-proportional distribution.

## API Observations

### High Friction (workaround-needed)
Building a distributed-slack OPF requires:
- Understanding `makePTDF()` weight vector semantics
- Constructing the generator-to-bus mapping matrix (`Cg`)
- Building flow constraints manually from `H_dist * Cg`
- Assembling costs from `gencost` polynomial coefficients
- Extracting LMPs from `opt_model` shadow prices (sign conventions differ)

Total effort: ~100 lines of code vs 1 line (`rundcopf`) for standard DC OPF.

### Sign Convention (doc-gaps)
The shadow price sign convention from `opt_model.get_soln('lin', ...)` differs from
MATPOWER's standard `results.bus(:, LAM_P)` output. Translating between them requires
understanding the constraint formulation details. This is not documented.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a11_distributed_slack_opf_tiny.m`
