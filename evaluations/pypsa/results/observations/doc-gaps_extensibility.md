# Observation: doc-gaps (Extensibility)

## Tool: PyPSA 1.1.2

### PTDF Usage Documentation

PyPSA documents the existence of `sub_network.calculate_PTDF()` in its API reference, but provides no worked example showing how to use the resulting matrix for flow prediction. Key undocumented details:

1. Column ordering follows `sub.buses_o`, not `n.buses.index`
2. The slack bus column is all zeros (flows relative to slack)
3. Branch ordering follows `sub.branches_i()` (MultiIndex of component type + name)

An analyst must read the `calculate_PTDF()` source code to understand these details.

### Contingency Analysis Patterns

No documentation or examples for contingency loop construction. The practical pattern (modify parameters in-place, re-solve, restore) works but is not described in official docs. The `extra_functionality` callback documentation was the closest, but it is deprecated.

### Custom Constraint Examples

The `create_model()` / `add_constraints()` workflow is documented in PyPSA's optimization documentation, but examples focus on global constraints (CO2 limits). Flow gate limits and other per-branch constraint patterns are not covered.
