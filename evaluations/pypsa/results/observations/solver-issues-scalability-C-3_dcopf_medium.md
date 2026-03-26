---
tag: solver-issues
source_dimension: scalability
source_test: C-3
tool: pypsa
severity: low
timestamp: 2026-03-24T17:45:00Z
---

# Observation: GLPK solver options require exact glpsol CLI flag names through linopy

## Finding

Linopy's GLPK interface passes solver options as `--key value` command-line flags
to `glpsol`. This means option keys must use the exact glpsol CLI syntax (e.g.,
`tmlim` not `tm_lim`). The solver-config.md convention `tm_lim: 300000` (milliseconds)
does not work; the correct form is `tmlim: 300` (seconds). An incorrect option name
causes glpsol to fail with "Invalid option" and linopy surfaces an opaque
`EmptyDataError: No columns to parse from file` error.

## Context

During C-3 DCOPF on MEDIUM, the initial GLPK configuration used `tm_lim: 300000`
per the evaluation solver-config.md template. This produced `--tm_lim 300000` on the
command line, which glpsol rejected. The error was diagnosed from the solver log
and corrected to `tmlim: 300`.

## Implications

This is a minor doc-gaps / api-friction finding. Users migrating solver configurations
from one tool to another (e.g., PowerModels.jl GLPK.jl options to PyPSA/linopy GLPK)
need to know that linopy's GLPK interface uses glpsol CLI flag names, not library API
option names. The error message (`EmptyDataError`) does not indicate the actual problem
(invalid solver option).
