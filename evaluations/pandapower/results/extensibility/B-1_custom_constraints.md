---
test_id: B-1
tool: pandapower
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: fragile
wall_clock_seconds: 46.22
peak_memory_mb: null
loc: 194
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# B-1: Add a flow gate limit to DC OPF. Read and assert on dual value.

## Result: QUALIFIED PASS

## Approach

1. Loaded ACTIVSg10k (~10,000 buses) and solved base case DC OPF (objective: 2,437,763.82)
2. Identified 3 highest-flow lines as flow gate (lines 1705, 7152, 2142)
3. Applied per-line flow limits at 90% of base case aggregate flow via `max_i_ka`
4. Solved constrained DC OPF -- converged
5. Extracted dual values from `net._ppc["branch"][:, 17:19]` (mu_sf / mu_st)

## Output

| Metric | Value |
|--------|-------|
| Base case objective | 2,437,763.82 |
| Constrained objective | 2,440,688.64 |
| Objective increase | 2,924.83 |
| Constraint level used | 90% of base flow |
| Line 1705 loading | 100.0% (binding) |
| Line 7152 loading | 100.0% (binding) |
| Line 2142 loading | 84.1% (not binding) |
| Dual value line 1705 (mu_st) | 13.69 |
| Dual value line 7152 (mu_sf) | 7.24 |
| Dual values extracted | Yes |

Two of three flow gate lines are binding at the 90% constraint level. Non-zero dual values confirm binding constraints and correct extraction.

## Workarounds

- **What:** Per-line flow limits via `max_i_ka` used as proxy for aggregate flow gate constraint. Dual values extracted from `net._ppc` internal arrays (PYPOWER result structure, columns 17-18).
- **Why:** pandapower has no first-class API for arbitrary linear constraints on DC OPF. Flow limits must be set per-line. Dual values are not exposed via public API but are accessible through the internal `_ppc` structure.
- **Durability:** fragile -- `_ppc` is an internal implementation detail. Per-line limits are public API but aggregate flow gate requires manual decomposition.
- **Grade impact:** Functional but requires knowledge of PYPOWER internals for dual extraction.

## Timing

- **Wall-clock:** 46.22 s (includes base case + constrained solve attempts)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b1_custom_constraints_medium.py`
