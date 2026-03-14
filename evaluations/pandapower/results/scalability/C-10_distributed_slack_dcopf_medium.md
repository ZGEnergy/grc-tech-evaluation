---
test_id: C-10
tool: pandapower
dimension: scalability
network: MEDIUM
status: skip
workaround_class: null
blocked_by: C-SMALL-gate
timestamp: 2026-03-13T03:30:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "69a0f28a"
---

# C-10: Distributed slack DC OPF on MEDIUM

## Result: SKIP

Skipped because Suite C SMALL gate failed (C-4 failed with blocked_by: A-5).
The SMALL gate failure was a cascaded failure from A-5 (SCUC unsupported), not a scale-related failure.
