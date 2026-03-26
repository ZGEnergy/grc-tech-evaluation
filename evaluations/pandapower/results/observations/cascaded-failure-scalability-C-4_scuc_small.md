---
tag: cascaded-failure
dimension: scalability
test_id: C-4
tool: pandapower
blocked_by: A-5
timestamp: "2026-03-24T00:00:00Z"
---

# Cascaded Failure: C-4 blocked by A-5

C-4 (SCUC 24hr on SMALL) cannot be attempted because A-5 (SCUC on TINY) failed with `workaround_class: blocking`. pandapower 3.4.0 does not support unit commitment -- it is a steady-state network analysis tool with continuous OPF only [tool-specific]. No binary variables, startup costs, or multi-period temporal coupling are available.

This cascaded failure is permanent for pandapower and applies to all network tiers (SMALL, MEDIUM). Per v11 protocol, the C-SMALL gate failure only blocks MILP MEDIUM tests -- LP and power-flow MEDIUM tests (C-1, C-2, C-3, C-5, C-9, C-10) run unconditionally.
