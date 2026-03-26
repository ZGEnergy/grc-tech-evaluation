---
tag: cascaded-failure
source_dimension: scalability
source_test: C-10
tool: gridcal
severity: high
timestamp: "2026-03-24T18:00:00Z"
---

# Observation: Distributed slack OPF cascaded failure from A-11

## Finding

C-10 (distributed slack DC OPF on MEDIUM) is a cascaded failure from A-11 (distributed
slack DC OPF on TINY). GridCal's linear OPF formulation hardcodes `distributed_slack=False`
in its internal `LinearAnalysis` call (`linear_opf_ts.py`, line 3022). The
`PowerFlowOptions.distributed_slack` flag is accepted by the API but ignored by the OPF
path entirely. [tool-specific: distributed_slack parameter architecturally excluded from OPF]

This is a structural limitation, not a solver issue. The PTDF matrix used by the OPF is
always computed with single-slack reference, regardless of user configuration. Distributed
slack works correctly in the power flow path (DCPF/ACPF) but not in the optimization path.

## Context

- **A-11 status:** fail (workaround_class: blocking)
- **C-10 status:** fail (blocked_by: A-11)
- **Root cause:** `linear_opf_ts.py` line 3022 passes `distributed_slack=False` to
  `LinearAnalysis` regardless of user options
- **Distributed slack in PF:** Works correctly (tested in A-11)
- **Distributed slack in OPF:** Structurally absent

## Implications

This is a clear cascaded failure pattern. The feature gap in the OPF formulation prevents
scaling to any network tier. The fix would require modifying the OPF source code to
propagate the `distributed_slack` parameter through to the `LinearAnalysis` call -- a
one-line change in principle but requiring a fork or upstream patch. This finding affects
both the expressiveness (A-11) and scalability (C-10) criterion grades.
