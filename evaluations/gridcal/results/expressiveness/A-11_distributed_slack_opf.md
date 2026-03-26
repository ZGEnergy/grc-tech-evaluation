---
test_id: A-11
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "95a0e3ae"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 1.41
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 219
solver: "HiGHS"
timestamp: "2026-03-24T00:00:00Z"
---

# A-11: DC OPF with distributed slack (load-proportional) on TINY

## Result: FAIL

## Approach

GridCal has a `distributed_slack` flag in `PowerFlowOptions` that works for power flow
(DCPF/ACPF), distributing the slack bus responsibility across generators proportionally.
The test investigated whether this option affects the DC OPF formulation.

**Investigation steps:**
1. Ran single-slack DCOPF (baseline).
2. Ran DCOPF with `power_flow_options.distributed_slack=True` set on the embedded PF options.
3. Compared dispatch and LMPs between the two runs.
4. Verified that distributed slack works in DCPF (power flow) mode.
5. Inspected the OPF formulation source code to understand the limitation.

## Output

| Metric | Single-Slack | Distributed-Slack | Difference |
|--------|-------------|-------------------|------------|
| Total gen (MW) | 6,254.2 | 6,254.2 | 0.0 |
| LMP min ($/MWh) | 5.00 | 5.00 | 0.0 |
| LMP max ($/MWh) | 84.38 | 84.38 | 0.0 |
| Max gen diff (MW) | -- | -- | 0.0 |
| Max LMP diff ($/MWh) | -- | -- | 0.0 |

**Results are identical.** Setting `distributed_slack=True` has zero effect on the linear OPF
results.

**Root cause:** The linear OPF formulation (`linear_opf_ts.py`, line 3022) hardcodes
`distributed_slack=False` in its internal `LinearAnalysis` call for PTDF computation. The
`PowerFlowOptions.distributed_slack` flag is ignored by the OPF formulation entirely.
[tool-specific]

**DCPF verification:** Distributed slack does work correctly in the power flow context:

| DCPF Mode | Max angle diff (rad) |
|-----------|---------------------|
| Single vs distributed | 3.15 |

The DCPF produces significantly different voltage angles with distributed slack enabled,
confirming the feature works for power flow but not for OPF.

**Weight API:** No API exists for setting distributed slack weights. The distributed slack in
DCPF uses a load-proportional distribution hardcoded in `LinearAnalysis`. Custom weights
(e.g., proportional to generation) are not configurable. [tool-specific]

## Workarounds

- **What:** No workaround available. The OPF formulation hardcodes `distributed_slack=False`.
- **Why:** The PTDF-based OPF computes shift factors relative to a single reference bus.
  Distributed slack would require modifying the PTDF computation to use a weighted reference,
  which is architecturally possible but not implemented in the OPF path.
- **Durability:** blocking -- Would require modifying the OPF formulation source code
  (`linear_opf_ts.py`) to pass the `distributed_slack` parameter through to `LinearAnalysis`.
  There is no public API or configuration option to achieve this.
- **Grade impact:** Fail for this sub-question. The feature is structurally absent from the
  OPF formulation despite existing in the power flow layer.

## Timing

- **Wall-clock:** 1.41 s (includes both single and distributed slack runs + DCPF verification)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a11_distributed_slack_opf.py`

Key finding in source code:

```python
# linear_opf_ts.py line 3022 -- hardcoded False
ls = LinearAnalysis(nc=nc,
                    distributed_slack=False,  # <-- not configurable
                    correct_values=True)
```
