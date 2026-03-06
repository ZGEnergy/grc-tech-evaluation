# Observation: api-friction (Extensibility)

## Tool: PyPSA 1.1.2

### B-1: LMP Shadow Prices Not Auto-Assigned in Manual Workflow

When using the two-phase `create_model()` / `model.solve()` / `assign_solution()` workflow for custom constraints, LMPs (bus marginal prices) are not automatically populated in `n.buses_t.marginal_price`. The shadow prices exist in the linopy model's constraint duals but are not mapped back to the PyPSA network object. Using `n.optimize()` (the one-call path) does assign LMPs correctly. This means analysts using the extension API for custom constraints lose easy access to LMPs unless they extract duals manually from `n.model.constraints`.

**Impact:** Low. The workaround (reading duals directly) is straightforward, but it's a surprising API gap for the most common extension use case.

### B-3: No Dedicated Branch Toggle API

PyPSA lacks a dedicated method to enable/disable individual branches for contingency analysis. The practical approach is setting `branch.x = 1e10` to effectively disconnect a branch. Other tools (e.g., pandapower) provide `in_service` flags. This is a minor friction point for contingency loops.

**Impact:** Low. The `x = 1e10` approach works reliably, but it's less self-documenting than a boolean flag.

### B-9: PTDF Bus Ordering Not Documented

The PTDF matrix columns follow `sub.buses_o` ordering (slack bus first, then non-slack buses), not the network's `n.buses.index` order. This is not documented in the API reference or examples. An analyst who constructs the injection vector in `n.buses.index` order will get incorrect flow predictions with no error or warning. The source code reveals the ordering but this requires reading `calculate_PTDF()` internals.

**Impact:** Medium. Silent incorrect results if bus ordering is wrong. Discovery requires source code reading.
