# Observation: Architecture Quality -- B-1 Custom Constraints

**Tag:** arch-quality
**Test:** B-1 (Custom Constraints)
**Dimension:** extensibility

## Observation

The JuMP model access pattern (`PSI.get_jump_model(model)`) is a clean and powerful
extension mechanism. It allows arbitrary constraint injection without source patching,
leveraging the entire JuMP ecosystem for constraint formulation, dual extraction, and
model modification.

The key design decision that enables this is PSI's choice to use JuMP.jl as its
optimization layer rather than a custom solver interface. This means any JuMP-compatible
manipulation works on PSI models, including:
- Custom constraints and variables
- Callback functions
- Warm starting
- Dual/sensitivity analysis

The variable naming convention (`FlowActivePowerVariable_Line_{name, timestep}`) is
consistent and predictable, making it practical to locate specific variables
programmatically.

## Impact

This is a significant strength. Custom constraint injection is one of the most
important extensibility features for production energy trading, and PSI handles it
cleanly through JuMP delegation.
