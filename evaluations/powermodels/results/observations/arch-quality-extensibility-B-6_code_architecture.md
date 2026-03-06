# Observation: arch-quality — B-6 Code Architecture

## Tool
PowerModels.jl v0.21.5

## Finding
PowerModels has a well-structured four-layer architecture (I/O, Core, Formulations, Problems) with strong separation of concerns. Key architectural qualities:

**Strengths:**
1. **Julia multiple dispatch as extension mechanism**: New formulations are added by subtyping `AbstractPowerModel` and overriding `constraint_*`/`variable_*` methods. No modification to existing code required. This is the cleanest extension pattern among the evaluated tools.
2. **Composable problem builders**: `build_*` functions in `prob/` assemble variables, constraints, and objectives from reusable components. Users can write custom `build_*` functions and pass them directly to `solve_model()`.
3. **Solver-agnostic**: Solver is passed as a JuMP optimizer factory. Switching from HiGHS to GLPK to Ipopt is a one-argument change.
4. **Direct JuMP model access**: `pm.model` gives full access to the underlying JuMP model for custom constraints, variable inspection, and dual extraction.

**Weaknesses:**
1. **Heavy InfrastructureModels dependency**: Core model instantiation, ref building, and optimization are delegated to InfrastructureModels.jl. Users must understand both packages to extend PowerModels deeply.
2. **Constraint template indirection**: The `constraint_template.jl` -> `form/*.jl` dispatch pattern is powerful but not explicitly documented. New users must trace through multiple dispatch to understand which function body actually executes.
3. **Data model is untyped**: The canonical `Dict{String,Any}` data representation has no schema validation. Typos in key names (e.g., `"br_staus"` vs `"br_status"`) fail silently.
4. **No developer architecture guide**: The separation of concerns is discoverable by reading source but not documented in any design document.

## Impact
- Extension is straightforward for users familiar with Julia's type system
- The untyped Dict data model is a reliability risk for programmatic modifications
- Total codebase (~19K LOC) is manageable for code auditing

## Quantitative Summary
- 4 abstraction layers, 43 source files, 18,963 LOC
- 20+ formulation types in type hierarchy
- DCPF solve path traverses 3-4 layers depending on JuMP vs direct solve
