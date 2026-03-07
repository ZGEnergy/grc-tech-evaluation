---
test_id: A-10
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.91
peak_memory_mb: null
loc: 145
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-10: Lossy DC OPF with LMP decomposition

## Result: FAIL

## Approach

pandapower's `rundcopp()` solves a lossless DC OPF. The test verified that:
1. No lossy DC OPF formulation is available.
2. No LMP decomposition (energy/congestion/loss) is provided.
3. AC OPF (`runopp()`) includes losses but is not a DC formulation.

### Parameter Inspection

Inspecting `pp.rundcopp()` parameters found: `net`, `verbose`, `check_connectivity`, `suppress_warnings`, `switch_rx_ratio`, `delta`, `trafo3w_losses`, `kwargs`. The `trafo3w_losses` parameter controls how 3-winding transformer losses are modeled in the network representation but does NOT add loss approximation to the DC OPF formulation.

No parameter enables lossy DC OPF or LMP decomposition.

### Shadow Price Columns

After OPF, `net.res_bus` contains columns `lam_p` and `lam_q` (active and reactive power shadow prices). These are total LMPs with no decomposition into energy, congestion, and loss components.

## Output

### Lossless DC OPF Results

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 41,263.94 |
| LMP min | 13.517 |
| LMP max | 13.517 |
| LMP mean | 13.517 |
| LMP uniform | Yes (std < 0.01) |

LMPs are nearly uniform across all buses, indicating no binding line constraints and no congestion.

### AC OPF Comparison

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 41,872.30 |
| LMP min | 13.372 |
| LMP max | 14.106 |
| LMP mean | 13.711 |
| LMP std | 0.187 |
| Objective difference from lossless | +1.47% |

AC OPF produces non-uniform LMPs because it includes losses and reactive power effects. However, it is a full nonlinear formulation, not a lossy DC approximation. The LMP variation (std 0.187) reflects loss-related price differences.

### Capability Summary

| Feature | Available |
|---------|-----------|
| Lossy DC OPF | No |
| LMP decomposition (energy/congestion/loss) | No |
| Per-line congestion rent computation | No (no decomposition available) |
| AC OPF with losses | Yes (but not DC formulation) |
| Lossless DC OPF with total LMPs | Yes |

## Workarounds

- **What:** No viable workaround exists for lossy DC OPF within pandapower.
- **Why:** The DC OPF formulation (`rundcopp`) is inherently lossless. Adding loss approximation would require modifying the underlying PYPOWER formulation. AC OPF includes losses but is not a DC formulation and still does not provide LMP decomposition.
- **Durability:** blocking -- the capability is not present in any form. LMP decomposition would require either a new formulation or post-processing that pandapower does not support.
- **Grade impact:** Complete absence of lossy DC OPF and LMP decomposition. These are important market simulation features that pandapower cannot provide.

## Timing

- **Wall-clock:** 0.91 s (lossless DC OPF + AC OPF comparison)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a10_lossy_dcopf_lmp.py`
