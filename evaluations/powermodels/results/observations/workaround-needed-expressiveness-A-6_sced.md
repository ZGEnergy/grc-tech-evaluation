---
tag: workaround-needed
dimension: expressiveness
test_id: A-6
tool: powermodels
---

# Workaround: No Built-in SCED

PowerModels has no built-in Security-Constrained Economic Dispatch (SCED) formulation. The test required ~50 lines of custom JuMP code to:

1. Fix commitment from A-5 as parameters (not variables)
2. Add inter-period ramp rate constraints
3. Solve as continuous QP with HiGHS

This is the same two-stage pattern used in A-5 (SCUC) but simpler since no binary variables are involved. The `instantiate_model` + JuMP model access pattern works reliably for this use case.

The UC/ED separation is clean: fixing commitment and re-solving as continuous QP produces the same objective (682,850) as the full MILP, confirming consistency. However, the lack of a native SCED API means users must understand PowerModels' internal variable naming conventions (e.g., `PowerModels.var(pm, nw, :pg, gen_id)`).
