---
test_id: A-11
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.792
peak_memory_mb: null
loc: 195
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-11: Distributed Slack OPF

## Result: PASS

## Approach

Investigated distributed slack support in both PyPSA's power flow and optimization
contexts.

**Power Flow:** Ran `n.pf(distribute_slack=True, slack_weights="p_set")` to distribute
the slack across all generators proportionally to their active power setpoint. This
is the documented API for distributed slack in PyPSA's AC power flow.

**Optimization:** PyPSA's LOPF (`n.optimize()`) does not have a `distribute_slack`
parameter because OPF inherently distributes generation optimally. In LOPF, the
optimizer sets all generator outputs simultaneously to minimize cost while satisfying
power balance at every bus. There is no single slack bus absorbing the mismatch --
the formulation is architecturally distributed by design.

Compared single-slack PF vs distributed-slack PF on the DCOPF dispatch to verify
the API works and produces physically consistent results.

## Output

**DCOPF Baseline (A-3):**

| Metric | Value |
|--------|-------|
| Objective | 1876.269 |
| LMP range | 0.30 - 0.30 $/MWh (uniform) |

**PF Comparison (single vs distributed slack):**

| Metric | Value |
|--------|-------|
| Both converged | Yes |
| Max dispatch diff | 47.97 MW |
| Max voltage mag diff | 0.00065 pu |
| Max voltage angle diff | 0.025 rad |
| Generators with dispatch change | 9 of 10 |

**Generator dispatch differences (distributed - single, MW):**

| Generator | Diff (MW) |
|-----------|-----------|
| G0 | +7.74 |
| G1 | -47.97 |
| G2 | +6.23 |
| G3 | +5.61 |
| G4 | +4.37 |
| G5 | +5.91 |
| G6 | +4.99 |
| G7 | +3.92 |
| G9 | +9.46 |

The distributed slack redistributes the system mismatch (caused by losses in AC PF)
across all generators proportionally rather than absorbing it at the single slack
bus (G1). G1's output decreases by 48 MW while all other generators increase slightly.
This is physically consistent: in single-slack mode, G1 alone compensates for all
system losses; in distributed mode, each generator picks up a share proportional to
its p_set.

**Distributed Slack API:**

| Feature | Supported |
|---------|-----------|
| `distribute_slack` parameter | Yes (`n.pf(distribute_slack=True)`) |
| Settable weights | Yes (`slack_weights="p_set"`) |
| Custom weights | Yes (via generator `slack_weight` attribute) |
| In LOPF | Not applicable (inherently distributed) |

## Workarounds

None required. The `distribute_slack` and `slack_weights` parameters are documented
public API. The architectural distinction between PF (needs explicit distributed slack)
and OPF (inherently distributed) is correct and well-designed.

## Timing

- **Wall-clock:** 0.792 s (includes DCOPF + single-slack PF + distributed-slack PF)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a11_distributed_slack_opf.py`

Key API patterns:

```python
# Distributed slack PF
n.pf(distribute_slack=True, slack_weights="p_set")

# Results differ from single-slack
n.generators_t.p  # dispatch reflects distributed mismatch absorption
```
