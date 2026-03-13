# Observation: solve_mn_opf Slow on ACTIVSg2000 (12-period × 2000-bus)

**Tag:** api-friction
**Dimension:** scalability
**Related tests:** B-4 (SMALL), C-6 (SMALL)
**Date:** 2026-03-11

## Summary

`PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)` with T=12 periods on the ACTIVSg2000 2000-bus network takes 160–310 seconds per scenario. This produces a total runtime of roughly 55–100 minutes for 20 scenarios, far exceeding what would be expected for a pure LP.

## Evidence

- B-4 SMALL test: scenarios 1-8 complete in 157–308s each (measured wall-clock per scenario)
- C-6 SMALL test: scenarios 1-5 complete in 188–285s each
- The `replicate(data, 12)` creates a 12-period multi-network with 2000 buses × 12 = 24,000 bus nodes, 3206 branches × 12 = 38,472 branch nodes, and 544 generators × 12 = 6,528 generator nodes
- HiGHS LP (pure LP with linearized costs) still takes this long, indicating the bottleneck is either model construction or the LP itself at this scale

## Classification

- **Type:** Performance characteristic, not a bug
- **API friction:** `solve_mn_opf` creates a fully-coupled LP across all periods — no temporal decomposition. For 12 periods × 2000 buses, the LP has ~25,000+ variables and ~75,000+ constraints
- **Workaround:** None needed for correctness; timing recorded as measured

## Impact

B-4 and C-6 SMALL tests complete but take significant wall-clock time (~55–100 minutes). The per-scenario timing is itself a key result metric for C-6. Results are recorded with measured timings.
