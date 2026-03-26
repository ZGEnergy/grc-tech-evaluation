---
tag: solver-issues
source_dimension: scalability
source_test: C-7
tool: pypsa
severity: medium
timestamp: 2026-03-24T12:00:00Z
---

# Observation: SCIP Not Available, GLPK 14x Slower Than HiGHS on MEDIUM DCOPF

## Finding

Of three required solvers (HiGHS, GLPK, SCIP), only HiGHS and GLPK are installed.
SCIP requires `pyscipopt` which is not in the devcontainer. GLPK solved the 10k-bus
DCOPF but its simplex solver took 116.7s vs HiGHS's ~8s (14x slower). Both produced
identical objectives within $0.0003.

## Context

C-7 tests solver swap on ACTIVSg10k DCOPF (15,191 variables, 43,089 constraints).
Solver swap in PyPSA is a single parameter change (`solver_name=...`) with no
reformulation needed — this is a linopy architectural feature. The LP/MILP model is
solver-agnostic.

The large wall-clock times (546s HiGHS, 731s GLPK) include significant linopy
overhead: LP file serialization, constraint writing, and model construction account
for ~538s (HiGHS) and ~614s (GLPK) beyond the solver's own execution time.

## Implications

The SCIP absence should be noted in the supply chain dimension — pyscipopt is an
optional dependency not included by default. The linopy overhead (>500s on model
build for a 15k-variable LP) is a tool-specific finding relevant to the Scalability
grade; it affects perceived solve time even though the solver itself is fast.
