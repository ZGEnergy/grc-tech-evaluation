---
dimension: expressiveness
tag: solver-issues
tool: powermodels
timestamp: 2026-03-05T19:00:00Z
---

# Solver Issues Observations -- Expressiveness

## 1. HiGHS cannot solve MIQP (A-5)

- **Context:** SCUC requires binary commitment variables + quadratic generation cost
- **Error:** HiGHS rejects the model at solve time when binary variables are present with quadratic objective
- **Fix:** Switch to SCIP solver which handles MINLP/MIQP
- **Impact:** Users must know solver capabilities before choosing; no guidance from PowerModels

## 2. GLPK cannot handle quadratic objectives (A-3)

- **Context:** case39 generators have polynomial cost model (model=2, ncost=3, quadratic)
- **Error:** `MathOptInterface.UnsupportedAttribute` at solve time
- **Fix:** Use HiGHS or Ipopt instead
- **Impact:** Low -- GLPK limitation is well-known, but PowerModels doesn't warn at model construction

## 3. HiGHS fails on DCPLLPowerModel (A-10)

- **Context:** DCPLLPowerModel (lossy DC) introduces quadratic loss approximation constraints
- **Error:** HiGHS cannot handle the quadratic constraints in the loss model
- **Fix:** Use Ipopt (NLP solver)
- **Impact:** Moderate -- users might reasonably expect a "DC" formulation to work with LP solvers

## 4. HiGHS OTHER_ERROR on large multi-network (A-8)

- **Context:** 72-network multi-network OPF (3 scenarios x 24 periods) with quadratic costs
- **Error:** `solve_mn_opf` returns OTHER_ERROR termination status
- **Fix:** Use Ipopt instead of HiGHS for large multi-network problems with quadratic objectives
- **Impact:** Moderate -- the problem size is reasonable but HiGHS struggles at this scale with QP

## 5. Ipopt returns LOCALLY_SOLVED (not OPTIMAL) for LP/QP problems

- **Context:** All Ipopt solves report `LOCALLY_SOLVED` even for convex QPs that have a unique global optimum
- **Impact:** Low -- this is standard NLP solver behavior, but code must check for both `OPTIMAL` and `LOCALLY_SOLVED` termination statuses
- **Affected tests:** A-2, A-8, A-9, A-10

## Summary

PowerModels' solver-agnostic architecture (via JuMP/MathOptInterface) is a strength, but the lack of upfront solver-capability validation means users discover incompatibilities only at solve time. A formulation-solver compatibility matrix in the documentation would help.
