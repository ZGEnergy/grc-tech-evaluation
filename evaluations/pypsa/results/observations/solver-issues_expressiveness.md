# Observation: solver-issues (expressiveness)

## Source Tests
A-5, A-9

## Findings

### 1. HiGHS Cannot Solve MIQP (A-5)
HiGHS 1.13.1 logs `ERROR: Cannot solve MIQP problems with HiGHS` but does not raise a Python exception. Instead, it returns termination condition "unknown" with a zero objective. The `linopy` wrapper reports this as "Optimization successful" with "unknown" termination — a misleading status.

**Impact:** Unit commitment with quadratic costs silently produces garbage results. Users must either linearize costs or use SCIP for MILP-only.

**Recommendation:** Test SCIP for MIQP capability in scalability phase.

### 2. SCOPF Infeasibility on Case39 (A-9)
The full N-1 SCOPF (35 line contingencies) is infeasible for case39 because the network has high base-case loading (max 90.2%). This is a property of the test case, not the tool. The SCOPF API itself works correctly and solves with reduced contingency sets.

### 3. Solver Option Pass-Through
PyPSA's `n.optimize()` passes `solver_options` directly to the solver backend. Unknown options (like `distribute_slack`) are forwarded to HiGHS which logs a warning but continues. This is both a feature (flexible solver tuning) and a hazard (typos in option names are silently ignored).

### 4. HiGHS MILP Fails on SCUC at SMALL Scale (A-5/A-6 SMALL)
On ACTIVSg2000 (544 generators), SCUC with min_up_time/min_down_time constraints generates ~39,168 binary variables (544 gens x 24 hours x 3 binary vars). HiGHS 1.13.1 cannot find a feasible solution within 300s -- it stalls at the root node with objective=Infinity. This causes A-5 (SCUC) and A-6 (SCED, which depends on SCUC) to both FAIL on SMALL. The same formulation works on TINY (10 generators).

**Impact:** SCUC is not viable with HiGHS on networks with >100 generators. Commercial solvers (Gurobi, CPLEX) would likely handle this.

### 5. SVD Failure in Post-Processing on ACTIVSg10k (A-3/B-1/B-7 MEDIUM)
`n.optimize()` post-processing computes `np.linalg.pinv(B.todense())` on the 10,000x10,000 susceptance matrix. When the B matrix contains zero-impedance branches (3 transformers with x=0 in ACTIVSg10k), the SVD fails. Workaround: set x=1e-4 on zero-impedance branches before calling `n.optimize()`.

### 6. DCPF on MEDIUM is Slow Due to Model Build Overhead (A-3 MEDIUM)
DC OPF on ACTIVSg10k takes 468s total despite HiGHS solving in 18.6s. The remaining ~450s is spent in linopy model construction and PyPSA post-processing (particularly the B matrix pseudo-inverse computation). This post-processing overhead is quadratic in network size.
