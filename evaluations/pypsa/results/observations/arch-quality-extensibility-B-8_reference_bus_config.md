---
tag: arch-quality
source_dimension: extensibility
source_test: B-8
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: DCOPF LMPs invariant to slack bus choice — mathematically correct

## Finding

PyPSA's LP-based DCOPF (`n.optimize()`) produces identical LMPs regardless of which bus is designated as the slack/reference bus. Three configurations (bus 31, bus 1, bus 20) all produced the same objective ($370,208.16), LMP range ($10.00 - $763.27), and per-bus LMP values. This is mathematically correct: in the LP formulation, the slack bus determines which angle is zero, but the dual variables (LMPs) are invariant to this choice.

## Context

The B-8 test changed the slack bus via `n.buses.at[bus_name, 'control'] = 'Slack'` — a 2-line API change with no model reconstruction. The finding that LMPs don't change is a property of the formulation, not a limitation.

## Implications

For accessibility assessment: users expecting LMP shifts when changing the slack bus (as would happen in DCPF) will find this behavior counterintuitive. Documentation could clarify that the slack bus affects DCPF angle assignments but not OPF dual variables.
