# Observation: Solver Availability and Post-Solve SVD Issue

- **Source:** C-3, C-4, C-7 (scalability)
- **Severity:** High (affects all optimization at 10k+ scale)

## Findings

### 1. Only HiGHS Available

The devcontainer environment has only HiGHS installed. SCIP, GLPK, CBC, CPLEX, and Gurobi are all missing. This limits multi-solver comparison but does not affect PyPSA's solver-swap mechanism, which is confirmed to be zero-reformulation (just change `solver_name` parameter).

### 2. Post-Solve SVD Computation Hangs on Large Networks

After HiGHS solves optimally (in ~3-12 seconds on the 10k-bus LP), `n.optimize()` enters a post-processing phase that:
- Computes shadow prices via SVD on the KVL constraint matrix
- Consumes 500%+ CPU and 3.7+ GB RAM
- Takes >5 minutes (observed >20 minutes without termination)
- Occurs in `pypsa.optimization.optimize` shadow price assignment

This makes `n.optimize()` impractical for networks above ~5k buses.

**Workaround:** Use `n.optimize.create_model()` + `model.solve()` to bypass post-processing, or accept that shadow prices (LMPs) will not be available on large networks without manual computation.

### 3. HiGHS Multi-Threading Speedup

HiGHS LP solver shows 3.6x speedup with 16 threads vs 1 thread on the 10k-bus DC OPF (3.24s vs 11.55s). This is meaningful for the solve phase but irrelevant when model build (37s) and post-solve (>300s) dominate.

### 4. SCOPF Fails on Networks with Bridge Edges (C-8)

`optimize_security_constrained()` uses PTDF-based security constraints. When a contingency line outage disconnects part of the network (bridge edge), the PTDF entry becomes infinite, producing values > 1e+15 in the constraint matrix. HiGHS refuses to solve such models. The ACTIVSg 10k case has many radial/bridge branches, causing 6,810-8,894 inf values for 500 contingencies. PyPSA does not auto-filter bridge edges from the contingency list.

### 5. SCUC Time Limit on 2k-bus Network (C-4)

HiGHS reached its 300s time limit without finding a feasible integer solution for the 24-hour SCUC on ACTIVSg 2000 (39,168 binary variables). The model presolves to 105,709 rows / 82,620 cols. SCIP was not available for comparison.

## Recommendation

For production use on networks > 5k buses:
1. Install SCIP or Gurobi for better MIP performance (HiGHS timed out on 2k-bus SCUC)
2. Use `create_model()` + `solve()` to avoid shadow-price SVD
3. Compute LMPs manually from dual variables if needed
4. Pre-filter bridge edges before passing contingencies to `optimize_security_constrained()`
5. Fix zero-impedance branches (set x=0.0001) before PTDF computation
