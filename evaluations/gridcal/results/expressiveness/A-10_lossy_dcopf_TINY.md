---
test_id: A-10
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: 0.011
peak_memory_mb: null
loc: 50
solver: "HiGHS"
timestamp: 2026-03-06T01:30:00Z
---

# A-10: Lossy DC OPF with LMP Decomposition

## Result: QUALIFIED PASS

## Approach

1. Ran standard (lossless) DC OPF as baseline.
2. Enabled `add_losses_approximation=True` on `OptimalPowerFlowOptions` and re-ran DC OPF.
3. Compared generation totals and shadow prices (LMPs) between lossless and lossy.
4. Searched for LMP decomposition (energy/congestion/loss components) and per-line congestion rent.

## Output

### Lossless vs Lossy DC OPF Comparison

| Metric | Lossless | Lossy |
|--------|----------|-------|
| Converged | Yes | Yes |
| Total gen (MW) | 6254.23 | 6254.29 |
| LMP range ($/MWh) | 0.3 -- 0.3 | 0.3 -- 0.300031 |
| LMPs uniform | Yes | No |
| Wall-clock (s) | 0.104 | 0.011 |

The lossy DC OPF increases total generation by 0.056 MW to cover losses and introduces non-uniform LMPs across buses. LMPs range from 0.3 to 0.300031 $/MWh, reflecting loss-dependent marginal costs at each bus. The loss component is small because all generators have identical cost (0.3 $/MWh) and the loss approximation adds incremental resistance-based terms.

### LMP Decomposition

GridCal provides `bus_shadow_prices` (total LMP per bus) but does **not** decompose LMPs into:
- Energy component
- Congestion component
- Loss component

No built-in LMP decomposition method exists in `OptimalPowerFlowResults`.

### Per-Line Congestion Rent

No built-in per-line congestion rent calculation. Could be computed manually from shadow prices and branch flows, but this is not provided by the tool.

## Why QUALIFIED PASS (not full PASS)

- **Lossy DC OPF works**: `add_losses_approximation=True` produces loss-inclusive LMPs that vary by bus.
- **LMP decomposition missing**: No built-in decomposition into energy/congestion/loss components.
- **Congestion rent missing**: No per-line congestion rent reconciliation.

The protocol requires "Loss-inclusive LMPs, LMP decomposition (energy/congestion/loss), per-line congestion rent reconciliation." GridCal satisfies the first requirement but not the latter two.

## Workarounds

None required for the lossy DC OPF itself. LMP decomposition and congestion rent would require manual post-processing outside GridCal's API.

## Timing

- **Lossless DC OPF:** 0.104s
- **Lossy DC OPF:** 0.011s

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a10_lossy_dcopf.py`
