---
test_id: A-11
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-11: Solve DC OPF with distributed slack and compare LMPs

## Result: FAIL

## Approach

Skipped on MEDIUM. A-11 FAILED on TINY due to architectural limitation: pandapower supports distributed slack for power flow (`runpp(distributed_slack=True)`) but NOT for OPF (`rundcopp` does not accept `distributed_slack` parameter). The test requires distributed slack in the OPF formulation to observe LMP impact.

See `A-11_distributed_slack_opf_TINY.md` for full analysis.

## Workarounds

- **What:** No workaround exists. Distributed slack is available for PF but not OPF.
- **Why:** `rundcopp()` API does not expose distributed slack formulation.
- **Durability:** blocking
- **Grade impact:** Fail for OPF with distributed slack. PF with distributed slack works.

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a11_distributed_slack_opf.py`
