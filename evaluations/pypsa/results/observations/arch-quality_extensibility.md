# Observation: arch-quality (Extensibility)

## Tool: PyPSA 1.1.2

### Overall Architecture Assessment

PyPSA demonstrates strong software engineering quality with clear separation of concerns across five well-defined layers:

1. **Data Model** (pypsa.Network): pandas DataFrames for components, time-varying data in `*_t` attributes
2. **Power Flow** (pypsa.network.power_flow): Direct DCPF/ACPF solvers using numpy sparse linear algebra
3. **Optimization Formulation** (pypsa.optimization.*): Separate modules for variables (323 lines), constraints (2159 lines), global constraints (867 lines)
4. **Solver Interface** (linopy): Fully abstracted -- solver swap is a parameter change
5. **Results Assignment** (assign_solution): Maps solver output back to Network DataFrames

### Extension Design

The `create_model()` / `add_constraints()` / `solve_model()` pattern is well-designed for extensibility. Users get access to a linopy algebraic model where they can:
- Select variables by name and dimension (`model.variables["Line-s"].sel(name=...)`)
- Build constraint expressions using standard arithmetic operators
- Add/remove constraints before solving

This is a significant architectural strength -- the tool was designed with custom constraint addition as a first-class use case.

### NetworkX Integration

The `n.graph()` method returns a standard NetworkX OrderedGraph, giving analysts immediate access to the full NetworkX algorithm library (BFS, DFS, shortest path, centrality, community detection, etc.) without any wrapper code.

### Areas for Improvement

1. The `pypsa.optimization.constraints` module at 2159 lines could benefit from decomposition
2. PTDF bus ordering is an internal detail that leaks to users without documentation
3. The contingency loop pattern is common enough to warrant a built-in API (even a simple branch enable/disable flag)
4. Shadow price assignment in the manual solve workflow should be automatic

### Comparison to Thesis-Project Architecture

PyPSA is decidedly not a thesis-project tool. It shows evidence of intentional design: the linopy separation, the pandas-first data model, the accessor pattern for optimization, and the multi-solver support all indicate a tool designed for production use by teams, not a single researcher's prototype.
