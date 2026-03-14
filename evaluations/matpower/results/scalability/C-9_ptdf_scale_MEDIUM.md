---
test_id: C-9
tool: matpower
dimension: scalability
network: MEDIUM
status: skip
workaround_class: null
blocked_by: C-SMALL-gate
timestamp: 2026-03-14T06:33:04Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "93bf8543"
---

# C-9: Skipped — Suite C SMALL gate failed

## Result: SKIP

C-4 (SCUC on SMALL) failed, triggering the Suite C SMALL gate.
All MEDIUM-tier scalability tests are skipped per protocol.

The C-4 failure is a cascaded failure (blocked_by: A-5) caused by the
MATPOWER-GLPK exit flag mapping bug, not a scalability limitation.
