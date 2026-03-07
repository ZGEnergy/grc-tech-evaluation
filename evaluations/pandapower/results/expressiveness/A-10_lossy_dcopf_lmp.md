---
test_id: A-10
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

# A-10: Solve lossy DC OPF and extract loss-inclusive LMPs

## Result: FAIL

## Approach

Skipped on MEDIUM. A-10 FAILED on TINY due to architectural limitation: pandapower's DC OPF (`rundcopp`) uses the standard lossless DC approximation. There is no option to include transmission losses in the DC OPF formulation, and therefore no way to extract loss-inclusive (marginal loss component) LMPs.

See `A-10_lossy_dcopf_lmp_TINY.md` for full analysis.

## Workarounds

- **What:** No workaround exists within pandapower for lossy DC OPF.
- **Why:** The PYPOWER DC OPF formulation is lossless by design.
- **Durability:** blocking
- **Grade impact:** Complete capability gap.

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a10_lossy_dcopf_lmp.py`
