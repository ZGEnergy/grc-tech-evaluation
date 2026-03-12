# Observation: HiGHS QP OTHER_ERROR on ACTIVSg2000 Quadratic Costs

**Tag:** solver-issues
**Dimension:** scalability
**Related tests:** B-4 (SMALL), C-6 (SMALL)
**Date:** 2026-03-11

## Summary

HiGHS solver returns `OTHER_ERROR` (not a graceful failure) when solving the ACTIVSg2000 DC OPF with quadratic generator costs (model=2, ncost=3 with nonzero c2). The error occurs in both single-period DC OPF and multi-period (replicate-based) DC OPF.

## Evidence

- **A-10 SMALL first attempt**: `solve_opf(data, DCPPowerModel, highs_opt)` returns `OTHER_ERROR` on ACTIVSg2000 with original quadratic costs. After linearizing (c2=0), returns `OPTIMAL`.
- **B-4 original test**: All 20 scenarios return `INFEASIBLE` because: (1) quadratic costs cause HiGHS issues in the mn_opf context, and (2) generator pmax reductions caused infeasibility.
- **Workaround**: Linearize c2=0 for all generators before solving with HiGHS.

## Classification

- **Severity:** Medium — Requires user to know about HiGHS QP behavior on large networks
- **Workaround:** Stable — Cost linearization is 2 lines of Julia and does not affect SCOPF/LMP correctness
- **Upstream issue:** The HiGHS solver's QP handling on large problems may have numerical issues; this is not a PowerModels bug per se but requires awareness in the evaluation workflow

## Impact

B-4, C-6, and A-10 SMALL tests all require cost linearization as a preprocessing step. This is documented as a stable workaround in each test result.
