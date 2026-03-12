---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-12
tool: powermodels
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Cyclic SoC Requires Manual JuMP Constraint Injection via instantiate_model

## Finding

`PowerModels.build_mn_opf_strg` does not enforce cyclic SoC (`se[T] == energy_initial`). The `constraint_storage_state_initial` constraint pins `se[1]` relative to the `energy` field, but there is no corresponding terminal constraint. Without a cyclic constraint, SCIP optimally depletes the battery with no incentive to recharge, making BESS arbitrage economically impossible.

## Context

Test A-12 required cyclic SoC for realistic BESS dispatch. The fix uses `instantiate_model` + `JuMP.@constraint(pm.model, se[T] == energy_init_pu)`. The constraint adds `se[24] == initial_energy / baseMVA` directly to the JuMP model. Without this, the SCIP solution drains the BESS in off-peak hours (hours 17–20) and never recharges because there is no end-of-horizon penalty for low SoC.

Important subtlety: the cyclic constraint must be `se[T] == energy_initial` (state BEFORE period 1), NOT `se[T] == se[1]` (state AFTER period 1). Using `se[T] == se[1]` is off by one period and produces a 157 MWh energy balance error.

## Implications

- **Extensibility dimension (B-8):** Demonstrates that `instantiate_model` + `PowerModels.var()` + `JuMP.@constraint` is the correct pattern for adding inter-temporal constraints. This pattern should be verified in extensibility tests.
- **Accessibility dimension:** The absence of a cyclic SoC option in the standard API is a usability gap. Users modeling rolling-horizon storage must know to add constraints manually via `instantiate_model`.
- **Expressiveness grade:** The workaround is stable (uses documented APIs) and the pass condition is met. Grade impact is moderate — the capability exists but requires non-obvious workaround.
