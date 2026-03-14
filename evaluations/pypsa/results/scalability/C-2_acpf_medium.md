---
test_id: C-2
tool: pypsa
dimension: scalability
network: MEDIUM
status: skip
blocked_by: C-SMALL-gate
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: fd60e14f
---

# C-2: ACPF on MEDIUM

## Result: SKIP

Blocked by Suite C SMALL gate failure. C-4 (SCUC 24hr on SMALL) failed — HiGHS
hit the 600-second time limit without finding a feasible integer solution for the
2000-bus network (39,168 binary variables). SCIP solver not available in devcontainer.

This MEDIUM-tier test was skipped per the protocol's cascading gate logic.
