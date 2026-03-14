---
tag: solver-issues
source_dimension: expressiveness
source_test: A-3
tool: matpower
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: HiGHS solver not available in MATPOWER 8.1 Octave environment

## Finding

`have_feature('highs')` returns 0 in the devcontainer (GNU Octave 9.2.0 + MATPOWER 8.1). The HiGHS solver, while documented as supported in MATPOWER 8.1 via MP-Opt-Model 5.0, is not available in the Octave environment. The built-in MIPS solver was used as fallback.

## Context

During A-3 DC OPF testing, the test attempted to use HiGHS per the eval-config solver specification. MATPOWER 8.1's release notes mention HiGHS integration via MP-Opt-Model 5.0, but this requires the HiGHS MEX interface or the Octave `highs` package to be installed separately. The MATPOWER distribution does not bundle HiGHS binaries.

MIPS (MATPOWER Interior Point Solver) worked as fallback and produced correct results, but it generated singular matrix warnings (rcond ~4e-17) during the solve. Despite the warnings, the solution converged and produced economically rational dispatch with 5 binding branches and a 293 $/MWh LMP spread.

## Implications

For scalability tests (C-3, C-7) that specify HiGHS and GLPK solver comparison, HiGHS unavailability may limit the solver swap evaluation. The solver ecosystem for MATPOWER on Octave is more limited than on MATLAB, where commercial solvers (Gurobi, CPLEX) and HiGHS MEX are more readily available. This should be noted in the Scalability assessment. The devcontainer may need HiGHS Octave bindings installed to complete C-7.
