---
test_id: A-10
tool: gridcal
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: 2.134
peak_memory_mb: null
loc: 50
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-10: Lossy DC OPF (Grade: SMALL)

## Result: QUALIFIED PASS

## Network

ACTIVSg2000 -- 2,000 buses, 3,206 branches, 544 generators.

## Approach

Same as TINY: ran lossless DC OPF as baseline, then enabled `add_losses_approximation=True` and compared.

## Output

### Lossless vs Lossy DC OPF Comparison

| Metric | Lossless | Lossy |
|--------|----------|-------|
| Converged | Yes | Yes |
| Total gen (MW) | 67,109.2 | 67,189.3 |
| LMP range ($/MWh) | 17.702 (uniform) | 17.580 -- 17.751 |
| LMPs uniform | Yes | No |
| Wall-clock (s) | 1.042 | 2.134 |

The lossy DC OPF increases total generation by 80.1 MW to cover losses and introduces non-uniform LMPs across buses. The LMP spread (17.58 to 17.75 $/MWh) is wider than TINY (0.3 to 0.300031), reflecting the more diverse cost structure of ACTIVSg2000.

### LMP Decomposition

Same as TINY: GridCal provides `bus_shadow_prices` (total LMP) but does NOT decompose into energy, congestion, and loss components.

## Scaling from TINY

| Metric | TINY (39 bus) | SMALL (2k bus) | Ratio |
|--------|--------------|---------------|-------|
| Buses | 39 | 2,000 | 51x |
| Lossy solve time (s) | 0.011 | 2.134 | 194x |
| Gen increase for losses (MW) | 0.056 | 80.1 | -- |
| LMP spread ($/MWh) | 0.000031 | 0.172 | -- |

Loss effects are much more pronounced on the larger, more realistic network.

## Why QUALIFIED PASS (not full PASS)

- Lossy DC OPF works and produces loss-inclusive, non-uniform LMPs.
- No LMP decomposition into energy/congestion/loss components.
- No per-line congestion rent calculation.

## Workarounds

None required for the lossy DC OPF itself.

## Timing

- **Lossless DC OPF:** 1.042s
- **Lossy DC OPF:** 2.134s
- **File load time:** 2.04s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a10_lossy_dcopf_small.py`
