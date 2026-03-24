---
probe_id: probe-009
tool: powermodels
source_test: A-9
probe_type: formulation_audit
classification: inconclusive
reason: "The evaluator explicitly documented N-1 infeasibility and 1-iteration behavior. The Benders mechanism is demonstrated but convergence to a secure solution was never tested because the network has no feasible N-1 secure dispatch. The key question — does iterative Benders converge when a feasible SCOPF solution exists? — remains unanswered."
solver_version: "Julia 1.10.7 / PowerModels 0.21.5 / HiGHS 1.x"
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 0
timestamp: "2026-03-14T00:00:00Z"
---

# Probe 009: SCOPF TINY — Benders Convergence Claim

## Verdict: INCONCLUSIVE

No code was run for this probe. The A-9 result file (`evaluations/powermodels/results/expressiveness/A-9_scopf_TINY.md`) already contains a thorough and transparent account of what happened. The probe is resolved by document analysis.

## What the Result File Says

The evaluator explicitly documents all relevant facts:

1. **N-1 infeasibility is stated**: "The IEEE 39-bus system with the Modified Tiny load/generation profile is not fully N-1 secure at original branch ratings." The full SCOPF LP (all 4,140 N-1 constraints simultaneously) is **INFEASIBLE**.

2. **1-iteration behavior is documented**: The `convergence_iterations: 1` frontmatter field and the table entry "Iterative iterations: 1 (hits infeasibility at iteration 2)" are explicit.

3. **The evaluator's framing**: The result treats N-1 infeasibility as a "physical property of the network configuration and load profile, not a code limitation." The `qualified_pass` is awarded for demonstrating the API mechanism (PTDF/LODF computation, constraint injection via two-level API, re-solve), not for demonstrating multi-iteration Benders convergence.

## Assessment of the Claim

The sweep claim that "SCOPF TINY qualified_pass demonstrates Benders convergence" is **not supported by the result file itself**. The file does not claim Benders converged — it explicitly says the algorithm terminated at 1 iteration due to infeasibility of the augmented problem at iteration 2.

What the result *does* demonstrate:
- The PowerModels two-level API (instantiate_model → var(pm,:p) → @constraint → optimize_model!) supports security constraint injection
- PTDF/LODF computation using `calc_basic_ptdf_matrix` is functional
- The base OPF is solved and N-1 violations are correctly identified by LODF screening
- The cost differential between unconstrained ($98,091/h) and security-constrained ($144,663/h) is plausible

What the result **does not** demonstrate:
- Multi-iteration Benders convergence on a feasible SCOPF instance
- That the iterative algorithm would converge to an optimal secure dispatch if given a network where such a dispatch exists

## Root Cause of the Test Design Gap

The TINY network (IEEE 39-bus with Modified Tiny load profile) is N-1 infeasible at 100% ratings. The evaluator discovered this, tried 70% derating (which made individual contingencies infeasible), and settled on 100% ratings — but the full SCOPF remains infeasible. There is no tested network configuration for which the iterative Benders loop completes multiple iterations and converges.

The `qualified_pass` grade is defensible as a mechanism verification (the API works, the formulation is correct), but the specific claim of "demonstrates Benders convergence" overstates what was shown.

## Classification Rationale

**inconclusive**: The evaluator correctly documented the network's N-1 infeasibility and the 1-iteration behavior. The documentation is transparent and accurate. However, the test design did not produce a scenario where Benders convergence could be observed. The claim that the result "demonstrates Benders convergence" is an overstatement of what was proven, but the underlying capability is plausible and the API mechanism is real. A definitive pass or fail requires a feasible SCOPF test network.

## No Code Run

The A-9 result file is sufficiently detailed. Running additional code would require:
1. Finding or constructing a network that is N-1 feasible with the TINY load profile (non-trivial)
2. Verifying multi-iteration convergence on that network

This is beyond the scope of a formulation audit probe and would constitute a new evaluation test.
