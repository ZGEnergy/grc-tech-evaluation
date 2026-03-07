---
tag: solver-issues
dimension: expressiveness
test_id: A-10
slug: lossy_dcopf_lmp
tool: powermodels
network: TINY
---

# solver-issues: DCPLLPowerModel incompatible with HiGHS

## Finding

PowerModels' `DCPLLPowerModel` (DC with linear losses) generates quadratic constraints
(`ScalarQuadraticFunction-in-GreaterThan`) from its loss linearization. HiGHS only
supports LP/QP/MIP (quadratic *objective* with linear constraints), not QCQP (quadratic
*constraints*). The solve fails with `UnsupportedConstraint` before any optimization
begins.

## Impact

- The protocol-specified solver (HiGHS) cannot be used with the tool's built-in lossy
  DC OPF formulation
- Ipopt (NLP solver) must be used as a fallback, introducing a different solver dependency
- The formulation name "DC with *linear* losses" is misleading -- the linearization
  still produces quadratic constraints in the JuMP model
- Users expecting a "linear" formulation to work with LP solvers will encounter this
  error without clear documentation explaining why

## Severity

Moderate. The lossy DC formulation works correctly with Ipopt, producing valid results
with non-zero losses (0.73% of load). The solver restriction is a usability and
documentation issue rather than a correctness issue.

## Recommendation

Document solver requirements per formulation type. DCPLLPowerModel should clearly
state that an NLP/QCQP solver (Ipopt, KNITRO) is required, not LP/QP solvers.
