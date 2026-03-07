---
tag: arch-quality
dimension: extensibility
test_id: B-1
slug: custom_constraints
tool: powermodels
---

# arch-quality: Two-level API enables clean constraint injection

PowerModels' two-level API (`instantiate_model` / `optimize_model!`) is a well-designed
extension point. It exposes the underlying JuMP model between construction and solving,
allowing users to add arbitrary constraints, variables, or objective terms without patching
source code.

Key architectural strengths observed:

1. **Clean separation of concerns:** `instantiate_model` builds the JuMP model and returns
   a PowerModels object whose `.model` field is a standard JuMP model. Users can add any
   JuMP-compatible constraint.

2. **Variable access via `PowerModels.var(pm, nw_id, :p)`:** Branch flow variables are
   accessible by a documented indexing scheme `(branch_id, from_bus, to_bus)`. This avoids
   hunting through internal data structures.

3. **Dual extraction via standard JuMP:** `JuMP.dual(constraint_ref)` works on user-added
   constraints. No special PowerModels machinery needed.

4. **No source patching required:** The entire flow gate + dual extraction workflow used
   only public API. The `ref_extensions` and `solution_processors` mechanisms provide
   additional hooks but were not needed for this test.

This is one of the cleanest extensibility patterns among the tools under evaluation.
The JuMP interop means any JuMP-compatible constraint or solver feature is available
without tool-specific wrappers.
