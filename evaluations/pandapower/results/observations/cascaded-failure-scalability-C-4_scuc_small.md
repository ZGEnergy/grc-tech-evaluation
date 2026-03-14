---
tag: cascaded-failure
dimension: scalability
test_id: C-4
tool: pandapower
blocked_by: A-5
timestamp: "2026-03-13T00:00:00Z"
---

# Cascaded Failure: C-4 blocked by A-5

C-4 (SCUC 24hr on SMALL) cannot be attempted because A-5 (SCUC on TINY) failed with `workaround_class: blocking`. pandapower 3.4.0 does not support unit commitment -- it is a steady-state network analysis tool with continuous OPF only. No binary variables, startup costs, or multi-period temporal coupling are available.

This cascaded failure is permanent for pandapower and applies to all network tiers (SMALL, MEDIUM). It also triggers the Suite C SMALL tier gate condition, which may block MEDIUM tier scalability tests.
