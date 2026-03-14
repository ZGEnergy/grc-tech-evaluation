---
test_id: A-9
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "e3ccffc8"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 288
solver: "MIPS"
timestamp: 2026-03-13T00:00:00Z
---

# A-9: Solve DC OPF with N-1 contingency constraints embedded in optimization

## Result: FAIL

## Approach

MATPOWER has no native SCOPF function (`runSCOPF()` or equivalent). Three approaches were attempted:

### Approach 1: User constraint injection via mpc.A/l/u

Built LODF matrix via `makeLODF(branch, PTDF)` (documented API). For each N-1 contingency (41 non-radial branches), computed post-contingency flow coefficients as `Bf(l,:) + LODF(l,k)*Bf(k,:)` and injected as linear constraints via `mpc.A`, `mpc.l`, `mpc.u`. This is the documented MATPOWER extension mechanism for adding user constraints to OPF.

**Result:** MIPS solver fails with numerical singularity when user constraints are added to the DC OPF with quadratic costs. Even a single user constraint causes MIPS to fail to converge. The issue appears to be the interaction between the quadratic cost Hessian and the augmented constraint matrix in the interior-point method.

With linear costs (c2=0), MIPS can handle a small number of user constraints (tested up to 5 successfully), but fails with the full N-1 set.

### Approach 2: Iterative limit tightening

Instead of injecting constraints, iteratively tighten base-case RATE_A values on branches with post-contingency violations, then re-solve DC OPF.

**Result:** The 70%-derated case39 network is already near its feasibility boundary. Any further tightening of RATE_A makes the problem infeasible — there is not enough transmission capacity to serve load with tighter limits.

### Approach 3: MOST contingency framework

MOST supports contingency states with probability weighting. However, MOST requires substantial setup boilerplate (mdi struct construction) and was not pursued after Approaches 1 and 2 failed, as the test protocol prioritizes the standard OPF extension mechanism.

## Output

| Metric | Value |
|--------|-------|
| Baseline DC OPF cost (A-3) | $219,748.32 |
| N-1 contingencies screened | 41 (5 radial excluded) |
| Post-contingency violations | 83 |
| Worst post-contingency overload | 403.1% |
| SCOPF solve | Failed (MIPS numerical singularity) |

### N-1 Contingency Screening

Using `makePTDF()` and `makeLODF()` (documented APIs), 83 post-contingency flow violations were identified in the base-case DC OPF dispatch. 5 radial branches were excluded (LODF contains Inf for island-creating outages). The worst violation is 403% overload — branch 13 (6->11) under outage of branch 33, with LODF = 1.75.

## Workarounds

- **What:** Attempted LODF-based N-1 constraint injection via `mpc.A/l/u` user constraint interface
- **Why:** No native SCOPF function in MATPOWER
- **Durability:** blocking — MIPS solver (the only available solver in the devcontainer for QP problems) cannot handle the N-1 constraint matrix with quadratic costs. HiGHS was unavailable. A commercial solver (Gurobi, CPLEX) or HiGHS might succeed, but the open-source evaluation environment cannot produce a solution.
- **Grade impact:** Fail on A-9. MATPOWER can formulate SCOPF constraints (the API exists via `mpc.A/l/u` and LODF/PTDF are readily computable), but the available solver cannot solve the resulting problem.

## Timing

- **Wall-clock:** N/A (solve failed)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a9_scopf.m`

Key API calls: `makePTDF()`, `makeLODF()`, `makeBdc()`, `rundcopf()` with `mpc.A/l/u` user constraints.
