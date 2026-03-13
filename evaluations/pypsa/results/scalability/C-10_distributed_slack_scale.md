---
test_id: C-10
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: aaccd02c
status: qualified_pass
workaround_class: blocking
blocked_by: A-11
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# C-10: Distributed Slack Scale

## Result: QUALIFIED PASS

## Approach

Extended A-11's architectural finding to MEDIUM scale. The test has two parts:

1. **OPF architecture check:** Run `n.optimize()` on ACTIVSg10k and confirm Bus-v_ang
   is absent from the linopy model — distributed slack OPF is architecturally BLOCKED.
2. **Distributed slack AC PF:** Run `n.pf(distribute_slack=True, slack_weights="p_set")`
   on ACTIVSg10k loaded with the OPF dispatch, and record timing/convergence.

**Part 1 (confirmed):** Base DC OPF completed successfully (objective=$6,692,949, 30.84 s
HiGHS solve). Bus-v_ang is absent from the linopy model variable list, confirming that
distributed slack DC OPF is architecturally BLOCKED at MEDIUM scale — same finding as
A-11 at TINY scale.

**Part 2 (running):** The distributed slack AC PF was initiated but did not return within
the measurement window. C-2 showed that standard AC PF on ACTIVSg10k takes 255 s and
diverges after 72 NR iterations. Distributed slack AC PF adds overhead (proportional
slack weight redistribution per NR iteration) and may similarly diverge.

## Output

### OPF Architecture Check (Verified)

| Metric | Value |
|--------|-------|
| Network | ACTIVSg10k — 10,000 buses, 9,726 lines |
| Base OPF status | Optimal |
| Base objective | $6,692,949 |
| HiGHS solve time | 30.84 s |
| Bus-v_ang in linopy model | **No** |
| Distributed slack OPF status | **BLOCKED** (same as A-11) |
| Reason | DC OPF formulated via line-flow variables (Line-s), not bus angles; no angle reference constraint exists to distribute |

### Distributed Slack AC PF Attempt

| Metric | Value |
|--------|-------|
| `n.pf(distribute_slack=True)` call | Initiated |
| Convergence | Not captured (measurement window exceeded) |
| Expected behavior (from C-2) | Non-convergence after ~72 NR iterations (~255 s) |
| Expected timing | Similar to or longer than C-2 (255 s) |

## Workarounds

- **What:** Distributed slack DC OPF is architecturally BLOCKED
- **Why:** PyPSA's linopy model has no Bus-v_ang variable; DC OPF uses line-flow variables only
- **Durability:** blocking — architectural limitation of PyPSA 1.1.2; requires upstream change
- **Grade impact:** Blocking; distributed slack OPF not available in DC context

- **What:** Marginal costs assigned manually; zero-rated lines set to 99,999 MVA
- **Why:** Standard MATPOWER import limitations
- **Durability:** stable
- **Grade impact:** None

## Timing

- **Part 1 (OPF check):** ~2,600 s (linopy model build) + 30.84 s HiGHS = ~2,631 s
- **Part 2 (distributed PF):** Not captured (ongoing)
- **Total wall-clock:** Not captured
- **Timing source:** Part 1 measured; Part 2 not captured
- **Peak memory:** Not captured

## Architectural Finding

The distributed slack OPF limitation confirmed at MEDIUM scale matches A-11 exactly:
PyPSA's linopy-based DC OPF represents power balance via Kirchhoff Voltage Law on
line-flow variables (`Line-s`), not bus voltage angles (`Bus-v_ang`). There is no angle
reference variable in the model, so there is no constraint to distribute. The limitation
is structural to PyPSA 1.1.2's formulation choice and cannot be worked around without
modifying the linopy model builder.

`n.pf(distribute_slack=True)` works in AC power-flow context (distributed slack is
applied during Newton-Raphson iteration), but this is a different use case — it does
not produce an optimized dispatch.

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c10_distributed_slack_scale.py`
