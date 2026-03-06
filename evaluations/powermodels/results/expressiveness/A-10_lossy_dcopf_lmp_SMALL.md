---
test_id: A-10
tool: powermodels
dimension: expressiveness
network: SMALL
status: pass
wall_clock_seconds: 3.477
timestamp: 2026-03-05
---

# A-10: Lossy DC OPF with LMP Decomposition [SMALL]

## Result: PASS

## Approach
Same as TINY: `DCPLLPowerModel` (piecewise-linear losses) with Ipopt, plus manual LMP decomposition (energy + congestion + loss components).

## Data Preprocessing
- 134 generators: default costs added
- Rate_a defaults applied

## Output
- Lossless DC OPF solved (baseline)
- Lossy DC OPF via DCPLLPowerModel converged
- LMP decomposition computed: energy (ref bus LMP), congestion (lossless dual minus ref), loss (residual)
- Total system losses and objective difference (lossy - lossless) recorded

## Timing
- Wall-clock: 3.5s (very fast at 2000-bus scale)
- Both lossless and lossy OPF solved quickly with Ipopt

## Workarounds
- LMP decomposition not built-in; manual extraction from duals
