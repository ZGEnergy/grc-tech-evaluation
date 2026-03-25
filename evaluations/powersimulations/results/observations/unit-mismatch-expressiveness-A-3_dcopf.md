---
tag: unit-mismatch
source_dimension: expressiveness
source_test: A-3
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Inconsistent units between dispatch variables and dual values

## Finding

PowerSimulations.jl returns dispatch values from `read_variable` in MW (natural units)
but returns nodal balance duals from `read_dual` in internal per-unit-based units.
Converting LMP duals to $/MWh requires dividing by `base_power` (100 MVA) and negating
the sign. This unit inconsistency is not documented.

## Context

Discovered during A-3 (DCOPF) evaluation. The raw dual value for
`NodalBalanceActiveConstraint__ACBus` is in units of $/pu, not $/MWh. The conversion
formula is `LMP_$/MWh = -dual_value / base_power`. Getting the sign convention wrong
produces negative LMPs; getting the unit conversion wrong produces LMPs that are 100x
too large.

## Implications

For Accessibility audit: this undocumented unit mismatch is a significant source of user
error. The mixed-unit convention (MW for variables, per-unit for duals) is unusual and
not described in the PowerSimulations.jl documentation or API reference. Users must
discover the conversion empirically or by reading source code.
