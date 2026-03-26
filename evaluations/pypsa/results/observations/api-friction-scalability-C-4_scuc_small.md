---
tag: api-friction
source_dimension: scalability
source_test: C-4
tool: pypsa
severity: low
timestamp: 2026-03-24T22:30:00Z
---

# Observation: No MIP gap extraction from PyPSA/linopy API

## Finding

When HiGHS terminates at the time limit with a feasible solution, the MIP gap
at termination cannot be extracted programmatically from the PyPSA or linopy API.
The gap (1.63%) is only visible in the solver's console log output.

## Context

C-4 SCUC on ACTIVSg2000 hit the 1800-second time limit on 32-thread HiGHS.
HiGHS reports the final MIP gap (1.63%), primal bound, and dual bound in its
stdout log, but `n.optimize()` returns only a status string ("ok" with
"time_limit" termination condition). There is no API to query
`n.model.solver.mip_gap` or equivalent after solving. The linopy `Model`
object does not expose solver-specific termination metrics.

Additionally, linopy reports `Status: ok` for time-limit terminations even
when no feasible solution was found (1-thread case), which is misleading.
The "ok" status means "solver ran without errors," not "optimal solution found."

## Implications

This affects the Accessibility dimension (D-4 error diagnostics). Users running
large MILPs with time limits need to parse console output rather than using the
API to determine solution quality. This is a minor friction point but relevant
for production use where programmatic access to solver diagnostics is expected.
