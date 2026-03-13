---
tag: api-friction
source_dimension: expressiveness
source_test: A-5
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: linopy Model Construction for 24h SCUC Takes 15+ Minutes at SMALL Scale

## Finding

For the ACTIVSg2000 SMALL network (2,000 buses, 544 generators × 24 hours), linopy model construction for a SCUC MILP (with committable=True, ramp limits, min up/down) takes in excess of 15 minutes before HiGHS receives the model. At TINY scale (39 buses, 10 generators × 24 hours), model construction is near-instant. This overhead is catastrophically worse for SCUC than for OPF.

## Context

Discovered during the extended A-5 SCUC run (1800s HiGHS time limit). After 16+ minutes wall-clock time with `n.optimize()` called, the Python process is at 40% CPU in container (single-threaded model construction, no HiGHS started yet), 2.9 GB RSS. The primary run's reported "~80s model build" was based on incomplete timing — the extended run confirms the full 544-generator × 24h × UC model with ramp/min-up/min-down constraints takes substantially longer than the OPF case at the same scale.

For comparison, 24h DC OPF (without committable) at SMALL scale completes `n.optimize()` in ~5 seconds total.

Model size: 372,841 rows | 129,168 cols (39,168 binary) | 1,720,849 nonzeros — approximately 37× more binary variables than TINY (720 binary).

## Implications

For Scalability (Suite C), SCUC at SMALL scale in PyPSA is severely constrained by linopy model construction time, independent of solver performance. A 24-hour UC problem for 544 generators cannot be built within a 5-minute wall-clock budget. This represents a fundamental limitation for production market clearing workflows.

The scalability team should test the UC model build time directly (separate from solve time) to characterize the O(N×T) scaling behavior of linopy model construction for MILP problems. This is more severe than the OPF case (which was ~260s for 10k buses) because of the added complexity of binary variable constraints.
