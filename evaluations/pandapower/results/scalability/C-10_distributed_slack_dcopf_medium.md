---
test_id: C-10
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "69a0f28a"
status: fail
workaround_class: blocking
blocked_by: A-11
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 0
solver: null
cpu_threads_used: null
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-10: Distributed Slack DC OPF on MEDIUM

## Result: FAIL

## Approach

This test is a cascaded failure from A-11 (distributed slack OPF on TINY).

A-11 established that pandapower's `rundcopp()` (DC OPF) does not support
`distributed_slack`. The parameter is silently consumed via `**kwargs` but has zero
effect on the PYPOWER optimization, which always uses a single-slack reference bus.

Since the fundamental capability (distributed slack in DC OPF) is not available at any
scale, running at MEDIUM scale would produce identical results to the single-slack
baseline -- making the LMP comparison meaningless.

### Evidence from A-11

- `runpp(distributed_slack=True)` works for AC power flow (changes ext_grid dispatch
  from 677.87 MW to 89.73 MW on case39).
- `rundcopp(distributed_slack=True)` silently accepts the parameter but produces
  **identical LMPs** to single-slack (max difference = 0.0 across all 39 buses).
- The distributed slack mechanism is implemented only in the Newton-Raphson power flow
  solver, not in the PYPOWER OPF formulation [tool-specific].

## Output

| Aspect | Finding |
|--------|---------|
| Blocked by | A-11 (distributed slack OPF) |
| Root cause | `rundcopp()` does not support `distributed_slack` |
| Available at any scale | No [tool-specific] |
| LMP comparison possible | No (single-slack = "distributed slack" in OPF) |

## Workarounds

- **What:** No workaround available. Distributed slack in OPF cannot be achieved via pandapower's API.
- **Why:** The OPF solver's slack bus handling is hardcoded in PYPOWER. The `**kwargs` passthrough silently absorbs the parameter without error.
- **Durability:** blocking -- would require modifying the PYPOWER OPF formulation internals [tool-specific].
- **Grade impact:** Cascaded blocking failure; no distributed slack OPF at any scale.

## Timing

- **Wall-clock:** N/A (not executed -- cascaded failure)
- **Timing source:** N/A
- **Peak memory:** N/A
- **CPU threads available:** 32

## Test Script

No test script written. This is a cascaded failure documented from A-11 findings.
See: `evaluations/pandapower/tests/expressiveness/test_a11_distributed_slack_opf.py`
