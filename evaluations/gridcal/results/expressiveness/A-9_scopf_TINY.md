---
test_id: A-9
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 0.100
peak_memory_mb: null
loc: 60
solver: "HiGHS"
timestamp: 2026-03-06T01:30:00Z
---

# A-9: SCOPF (Preventive Security-Constrained OPF)

## Result: FAIL

## Approach

1. Checked for SCOPF-related modules, classes, and OPF options.
2. Created N-1 contingencies for all 46 branches using `Contingency` and `ContingencyGroup` objects.
3. Set `consider_contingencies=True` on `OptimalPowerFlowOptions`.
4. Ran DC OPF with contingencies and compared dispatch to baseline (no contingencies).

## Findings

### API Surface

- `consider_contingencies` flag exists in `OptimalPowerFlowOptions` (default: False).
- `contingency_groups_used` tuple exists in options.
- `ContingencyAnalysis` module exists with drivers and results classes.
- No `SCOPF` or `SecurityConstrainedOPF` module exists.

### Contingency Setup

Successfully created 46 N-1 contingencies (one per branch) using:

```python
Contingency(device=branch, name=f"N-1_{branch.name}", group=group)
```

Added to grid via `grid.add_contingency()` and `grid.add_contingency_group()`.

### OPF with consider_contingencies=True

The OPF converged but **produced identical dispatch** to the baseline DC OPF without contingencies:

| Generator | Base DC OPF (MW) | With Contingencies (MW) |
|-----------|-----------------|------------------------|
| Gen 0 | 427.93 | 427.93 |
| Gen 1 | 183.89 | 183.89 |
| Gen 2 | 686.41 | 686.41 |
| Gen 3 | 652.00 | 652.00 |
| Gen 4 | 508.00 | 508.00 |
| Gen 5 | 687.00 | 687.00 |
| Gen 6 | 580.00 | 580.00 |
| Gen 7 | 564.00 | 564.00 |
| Gen 8 | 865.00 | 865.00 |
| Gen 9 | 1100.00 | 1100.00 |

The `consider_contingencies` flag does not modify the OPF formulation to include N-1 security constraints. It may only be used by the separate `ContingencyAnalysis` post-hoc screening module.

### ContingencyAnalysis (Post-Hoc, Not SCOPF)

The `ContingencyAnalysis` module performs N-1 contingency screening after a dispatch is fixed. It runs power flow under each contingency to identify violations, but does **not** re-optimize dispatch to respect all N-1 limits simultaneously. This is fundamentally different from preventive SCOPF.

## Assessment

GridCal does not implement preventive SCOPF (issue #364). The `consider_contingencies` flag in OPF options is non-functional for security-constrained optimization. `ContingencyAnalysis` provides post-hoc N-1 screening but not simultaneous optimization respecting all N-1 constraints.

## Workarounds

None available. SCOPF would require building the N-1 constraint set manually and adding it to the optimization, which GridCal's API does not support (no custom constraint injection).

## Timing

- **OPF with contingencies:** 0.100s (identical to base, confirming constraints are ignored)

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a9_scopf.py`
