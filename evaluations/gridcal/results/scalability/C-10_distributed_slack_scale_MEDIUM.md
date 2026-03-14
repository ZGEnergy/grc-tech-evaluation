---
test_id: C-10
tool: gridcal
dimension: scalability
network: MEDIUM
status: fail
workaround_class: blocking
blocked_by: A-11
protocol_version: "v10"
skill_version: v1
test_hash: "18f272b0"
wall_clock_seconds: 0.0
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 66
solver: null
timestamp: "2026-03-13T22:40:00Z"
---

# C-10: Distributed slack DC OPF on MEDIUM

## Result: FAIL

## Approach

**Cascaded failure from A-11.** This test was not executed because the prerequisite
capability (distributed slack in DC OPF) does not work at any scale.

A-11 demonstrated that GridCal's linear OPF formulation hardcodes `distributed_slack=False`
in its internal `LinearAnalysis` call (`linear_opf_ts.py`, line 3022). The
`PowerFlowOptions.distributed_slack` flag is ignored by the OPF formulation entirely.
Setting it to `True` produces results identical to `False`.

Since distributed slack OPF does not function on TINY (39-bus), it cannot be scaled to
MEDIUM (10000-bus).

## Output

| Metric | Value |
|--------|-------|
| A-11 status | FAIL |
| A-11 workaround class | blocking |
| Root cause | OPF hardcodes `distributed_slack=False` in PTDF computation |
| Source location | `linear_opf_ts.py` line 3022 |
| PF distributed slack works | Yes (DCPF/ACPF) |
| OPF distributed slack works | No |
| Weight API available | No |

## Workarounds

- **What:** No workaround available. This is a cascaded failure from A-11.
- **Why:** The OPF formulation architecturally uses a single-slack PTDF matrix. Distributed
  slack would require modifying the source code to pass the `distributed_slack` parameter
  through to `LinearAnalysis`.
- **Durability:** blocking -- Would require forking or patching the OPF formulation source.
- **Grade impact:** Fail. This is a cascaded failure; the feature is structurally absent
  from the OPF path.

## Timing

- **Wall-clock:** 0.0 s (not executed)
- **Timing source:** measured (trivial -- no computation performed)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c10_distributed_slack_scale_medium.py`
