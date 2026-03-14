---
tag: api-friction
source_dimension: scalability
source_test: C-4
tool: pypsa
severity: low
timestamp: 2026-03-14T01:30:00Z
---

# Observation: No MIP gap extraction from PyPSA/linopy API

## Finding

When HiGHS terminates at the time limit, the MIP gap at termination cannot be
extracted programmatically from the PyPSA or linopy API. The gap is only visible
in the solver's console log output.

## Context

C-4 SCUC on ACTIVSg2000 hit the 600-second time limit. HiGHS reports the final
MIP gap in its stdout log, but `n.optimize()` returns only a status string
("ok" with "time_limit" termination condition). There is no API to query
`n.model.solver.mip_gap` or equivalent after solving. The linopy `Model` object
does not expose solver-specific termination metrics.

## Implications

This affects the Accessibility dimension (D-4 error diagnostics). Users running
large MILPs with time limits need to parse console output rather than using the
API to determine solution quality. This is a minor friction point but relevant
for production use where programmatic access to solver diagnostics is expected.
