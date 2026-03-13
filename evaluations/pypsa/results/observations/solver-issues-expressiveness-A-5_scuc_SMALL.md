# solver-issues — expressiveness — A-5/A-6 SCUC/SCED SMALL

**Tags:** `solver-issues`
**Tests affected:** A-5 SMALL, A-6 SMALL
**Observed:** 2026-03-11

## Finding

HiGHS 1.13.1 cannot find a feasible integer solution for the ACTIVSg2000 SCUC MILP within a 5-minute time limit (single thread). The MILP correctly formulates with 39,168 binary variables (544 generators × 24 hours × 3 binary types), 121,870 rows, and 79,471 columns after presolve. After 300 seconds of B&B search (exploring only LP relaxation level, 0 B&B nodes branched), HiGHS terminates with `primal_bound = inf` — no integer-feasible solution found.

## Evidence

From A-5 SMALL test execution:
```
MIP linopy-problem-k0crfryk has 372,841 rows; 129,168 cols; 1,720,849 nonzeros; 39,168 binary
After presolve: 121,870 rows, 79,471 cols (31,082 binary)

Solving report
  Status:           Time limit reached
  Primal bound:     inf
  Dual bound:       46,524,901.59
  LP iterations:    61,076 (all in LP relaxation + cutting planes, 0 B&B nodes)
  Timing:           319.38s
```

The LP relaxation dual bound ($46.5M) is finite and reasonable (indicating a valid LP), but HiGHS spent all its time in preprocessing and LP relaxation without branching on a single binary variable.

**A-6 SMALL consequence:** Since A-6 depends on A-5's commitment schedule, A-6 also fails. The UC stage hits the same time limit, the commitment schedule is all zeros (no feasible integer solution), and the resulting ED LP is infeasible (all generators forced off).

## Analysis

The 39k-binary MILP is at the boundary of what single-threaded HiGHS can solve in 5 minutes. The Tiny SCUC (720 binary variables) solved in 1.6s (B&B: 1 node). The SMALL SCUC is 54× larger in binary variables and ~170× larger in nonzeros — a regime where HiGHS's default branching strategy struggles to find an initial feasible integer solution quickly.

Contributing factors:
1. **Large model:** 544 generators × 24 hours × min up/down/startup constraints creates dense constraint matrices
2. **min_up/min_down coupling:** These rolling-window constraints create long-horizon dependencies that slow LP relaxation bound tightening
3. **Startup cost incentives:** With cheap generators ($10–$25/MWh) having 4h min up times and expensive ones ($55–$80/MWh) having 1h min times, the cost structure doesn't strongly drive decommitment

## Potential mitigations (not tested)

- Extend time limit to 30–60 minutes (likely to find feasible solution given finite dual bound)
- Use Gurobi or CPLEX (not available in devcontainer)
- Reduce problem: make only the top-N most expensive generators committable (e.g., N=50 vs all 544)
- Use warm-start from LP relaxation solution

## Grade impact

A-5 and A-6 both `fail` at SMALL scale. The formulation expressiveness is confirmed (MILP correctly built); the failure is a solver scalability issue, not a PyPSA API limitation. This is relevant to the Scalability criterion (Suite C) but not Expressiveness per se — the SCUC formulation is fully expressible in PyPSA at all scales.
