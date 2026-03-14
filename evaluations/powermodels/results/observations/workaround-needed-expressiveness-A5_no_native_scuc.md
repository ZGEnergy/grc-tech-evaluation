---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-5
tool: powermodels
severity: high
timestamp: 2026-03-13T18:00:00Z
---

# Observation: SCUC requires full user-assembly as JuMP MILP (~250 LOC)

## Finding

PowerModels.jl v0.21.5 has no native SCUC support. A working 24-hour SCUC with generator cycling was achieved, but required ~250 lines of custom JuMP MILP code covering commitment variables, startup/shutdown logic, min up/down constraints, ramp rates, and DC power flow. PowerModels was used only for `parse_file`.

## Context

Test A-5 required a 24-hour SCUC with cycling. The user-assembled model solved optimally (MIP gap 0.004%, 3 generators cycling) in 0.077s with HiGHS. The JuMP foundation makes this feasible but it is entirely user-side effort -- no UC-related API exists in PowerModels.

## Implications

This is a blocking workaround: no API path (public or private) achieves SCUC without assembling the full MILP from scratch. For the Extensibility audit, this confirms that PowerModels is architecturally limited to steady-state single-period optimization. For Accessibility, the significant JuMP expertise required to formulate SCUC is a barrier for users coming from MATPOWER/PSS/E backgrounds where UC extensions exist.
