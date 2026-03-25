---
test_id: A-11
tool: pandapower
dimension: expressiveness
network: TINY
status: fail
workaround_class: blocking
blocked_by: null
protocol_version: "v11"
skill_version: "v2"
test_hash: "95a0e3ae"
wall_clock_seconds: 6.42
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 331
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-24T00:00:00Z"
---

# A-11: Solve DC OPF with distributed slack

## Result: FAIL

## Approach

1. Loaded the IEEE 39-bus network using `load_pandapower`.
2. Inspected function signatures to check distributed slack support:
   - `runpp()` (AC PF): **has** `distributed_slack` parameter.
   - `rundcopp()` (DC OPF): **does not** have `distributed_slack` parameter.
   - `runopp()` (AC OPF): **does not** have `distributed_slack` parameter.
3. Confirmed `slack_weight` column exists in both `net.gen` and `net.ext_grid` DataFrames.
4. Ran distributed slack AC power flow (`runpp(distributed_slack=True)`) successfully to confirm the feature works for PF.
5. Ran single-slack DC OPF as baseline and extracted LMPs.
6. Attempted `rundcopp(net, distributed_slack=True)` -- the call succeeds (parameter silently consumed by `**kwargs`) but produces **identical LMPs** to single-slack results (max difference = 0.0).

## Output

**Distributed slack support by function:**

| Function | Purpose | distributed_slack param | Works |
|---|---|---|---|
| `runpp()` | AC Power Flow | Yes (explicit) | Yes |
| `rundcpp()` | DC Power Flow | Not checked (not OPF) | N/A |
| `rundcopp()` | DC OPF | No (silently swallowed via `**kwargs`) | No |
| `runopp()` | AC OPF | No | N/A |

**Power flow comparison (single vs distributed slack):**

| Metric | Single Slack | Distributed Slack |
|---|---|---|
| ext_grid P (MW) | 677.87 | 89.73 |
| Converged | Yes | Yes |

The distributed slack PF works correctly -- the ext_grid dispatch differs significantly (677.87 vs 89.73 MW) because slack is distributed across all generators proportionally to their `slack_weight`.

**OPF LMP comparison:**

| Bus | Single-Slack LMP | "Distributed Slack" LMP | Difference |
|---|---|---|---|
| 0 | $47.0043 | $47.0043 | 0.0 |
| 1 | $42.5412 | $42.5412 | 0.0 |
| 2 | $43.0123 | $43.0123 | 0.0 |
| 3 | $43.4822 | $43.4822 | 0.0 |
| 4 | $43.3098 | $43.3098 | 0.0 |

LMPs are identical across all 39 buses. The `distributed_slack=True` kwarg is silently accepted by `rundcopp()` via `**kwargs` but has zero effect on the PYPOWER optimization. The DC OPF always uses a single-slack reference bus.

**LMP range (single-slack baseline):** $14.00 -- $47.00/MWh

## Workarounds

- **What:** No workaround available. Distributed slack in OPF cannot be achieved via pandapower's API.
- **Why:** The distributed slack mechanism in pandapower is implemented only in the power flow solver (Newton-Raphson). The OPF formulation in PYPOWER uses a fixed single-slack reference bus in its constraint formulation, and there is no extension point to modify this.
- **Durability:** blocking -- the OPF solver's slack bus handling is hardcoded. The `**kwargs` passthrough silently absorbs the parameter without error, which is a misleading API behavior.
- **Grade impact:** Blocking limitation for distributed slack OPF expressiveness.

**Notable API friction:** `rundcopp()` accepts arbitrary `**kwargs` and silently ignores `distributed_slack=True` without raising an error or warning. This could mislead users into thinking the feature is active.

## Timing

- **Wall-clock:** 6.42 s (includes AC PF comparison and multiple OPF solves)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a11_distributed_slack_opf.py`
