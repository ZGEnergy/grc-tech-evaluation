---
tag: doc-gaps
source_dimension: scalability
source_test: C-4
tool: pypsa
severity: medium
timestamp: 2026-03-24T22:30:00Z
---

# Observation: SCIP solver not available despite devcontainer feature

## Finding

The SCIP solver is listed as available in the devcontainer configuration but
`n.optimize(solver_name="scip")` raises `AssertionError: Solver scip not
installed`. This prevents the C-4 dual-solver comparison.

## Context

C-4 requires testing SCUC with both HiGHS and SCIP. The devcontainer Dockerfile
includes SCIP installation steps, but the linopy/PyPSA solver detection does not
find the SCIP binary or Python bindings. The error occurs during solver validation
before any optimization begins.

## Implications

This is an environment configuration issue, not a PyPSA limitation. PyPSA
supports SCIP via linopy's solver interface. The missing SCIP installation
means the dual-solver comparison cannot be performed, but this does not
affect the PyPSA grade directly. It does mean C-4 can only report HiGHS results.
