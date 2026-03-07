---
tag: api-friction
source_dimension: extensibility
source_test: B-8
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Slack bus assignment does not affect OPF LMPs (by design)

## Finding

In PyPSA's DCOPF (`n.optimize()`), changing the slack bus has zero effect on LMPs
or dispatch. The slack bus concept only applies to power flow (`n.pf()`/`n.lpf()`).
This is mathematically correct but may surprise users expecting MATPOWER-like behavior
where the reference bus affects the DC OPF formulation.

## Context

Test B-8 changed the slack bus from bus 31 to bus 30 and re-ran DC OPF. LMPs and
objectives were identical to the digit. This is because PyPSA treats all generators
as decision variables in the LP and enforces power balance as a constraint -- there
is no "slack generator" that absorbs imbalance.

Distributed slack is supported via `n.pf(distribute_slack=True, slack_weights=...)`,
which affects voltage angle profiles in power flow but not optimization results.

## Implications

This distinction between OPF and PF slack semantics should be noted in the
Accessibility assessment. The behavior is correct but underdocumented -- users
migrating from MATPOWER or PowerModels may not realize the slack bus is irrelevant
to OPF in PyPSA.
