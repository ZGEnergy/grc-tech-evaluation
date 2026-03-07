---
test_id: B-1
tool: gridcal
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.0
peak_memory_mb: null
loc: 230
solver: HiGHS
timestamp: 2026-03-06T03:00:00Z
---

# B-1: Custom Constraints (MEDIUM)

## Result: FAIL

## Note

Not re-run on MEDIUM network. The failure is architectural, not scale-dependent. GridCal has no API to inject custom linear constraints into the OPF formulation. This was confirmed on TINY (IEEE 39-bus) and applies identically to all network sizes.

See `B-1_custom_constraints_TINY.md` for the detailed investigation.

### Summary of Architectural Limitation

1. **No custom constraint API** -- The OPF formulation is hardcoded in PuLP model-building code. No user-facing API to inject additional linear constraints.
2. **No per-constraint duals** -- Only nodal LMPs (bus_shadow_prices) are returned. Per-branch or per-constraint shadow prices are not accessible.
3. **Rate modification only** -- Single-branch flow gates can be emulated by modifying `branch.rate`, but this cannot express multi-branch interface limits, generator group constraints, or arbitrary linear constraints.
4. **Source patching required** -- Adding custom constraints would require modifying the internal LP formulation files.

## Workaround Classification: BLOCKING

Same architectural limitation regardless of network size.

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b1_custom_constraints.py` (TINY version; not re-run on MEDIUM)
