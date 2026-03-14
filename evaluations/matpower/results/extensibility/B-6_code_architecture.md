---
test_id: B-6
tool: matpower
dimension: extensibility
network: N/A
protocol_version: v10
skill_version: v1
test_hash: "0f337d8d"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-6: Qualitative assessment of source code architecture for DCPF solve path

## Result: PASS

## Finding

MATPOWER 8.1 ships two complete, parallel architectures for the DCPF solve path: a **legacy procedural framework** (stable since 1997) and a **new object-oriented MP-Core framework** (introduced in 8.0, May 2024). Both produce identical results and coexist via backward-compatibility wrappers. The legacy framework is lean and transparent; the new framework provides clean separation of concerns with 4 abstraction layers and a formal Extension API. Internal interfaces are documented via inline docstrings and a Developer Manual.

## Architecture Analysis

### 1. Legacy Framework (Procedural)

**Call chain for DCPF:**
```
rundcpf(casedata, mpopt)
  → runpf(casedata, mpopt)  [sets mpopt.model = 'DC']
      → loadcase(casedata)           — data loading
      → ext2int(mpc)                 — external→internal bus numbering
      → bustypes(bus, gen)           — classify buses (PQ/PV/REF)
      → makeBdc(baseMVA, bus, branch) — build B matrices + phase shift injections
      → dcpf(B, Pbus, Va0, ref, pv, pq) — solve B\Pbus for voltage angles
      → int2ext(results)             — restore external bus numbering
      → printpf(results, ...)        — format output
```

**File inventory (legacy DCPF):**

| File | Lines | Role |
|------|-------|------|
| `rundcpf.m` | 74 | Entry point, sets DC model flag, delegates to `runpf` |
| `runpf.m` | 520 | Main PF dispatcher (AC/DC branching, Q-limit enforcement) |
| `dcpf.m` | 46 | Core solver: sparse linear system solve `B\P` |
| `makeBdc.m` | 86 | Build B-matrix with tap ratio and phase shift corrections |
| `bustypes.m` | ~30 | Classify bus types from bus/gen data |
| `ext2int.m` / `int2ext.m` | ~200 | Bus renumbering and data ordering |

**Layers:** 3 (entry → dispatcher → solver). No formal separation between network model and solver -- `runpf.m` handles both the formulation setup and the solve invocation inline.

### 2. New MP-Core Framework (Object-Oriented)

**Call chain for DCPF (via `run_pf`):**
```
run_pf(d, mpopt, mpx)
  → mp.task_pf.run(d, mpopt)
      → task.load_dm(d)                         — DATA MODEL layer
          → mp.dm_converter_mpc2.import(d)
          → mp.data_model.build(dmc)
              → mp.dme_bus.build()
              → mp.dme_gen.build()
              → mp.dme_branch.build()
              → mp.dme_load.build()
              → mp.dme_shunt.build()
      → task.network_model_build(dm)             — NETWORK MODEL layer
          → mp.net_model_dc.build(dm)
              → mp.nme_bus_dc.build_params()
              → mp.nme_gen_dc.build_params()
              → mp.nme_branch_dc.build_params()  — B,K,p matrices
              → mp.nme_load_dc.build_params()
              → mp.nme_shunt_dc.build_params()
      → task.math_model_build(nm, dm)            — MATHEMATICAL MODEL layer
          → mp.math_model_pf_dc.build(nm, dm)
              → add_node_balance_constraints()    — B*Va = Pbus
              → solve()                           — direct linear system solve
      → task.network_model_update(mm, nm)        — RESULTS layer
          → port_inj_soln()                      — compute branch flows
```

**Abstraction layers:** 4 distinct layers

| Layer | Base Class | DC Concrete Class | Responsibility |
|-------|-----------|-------------------|----------------|
| Data Model | `mp.data_model` | `mp.data_model` | Data parsing, validation, element tables |
| Network Model | `mp.net_model` | `mp.net_model_dc` | Port-injection parameters (B, K, p matrices) |
| Mathematical Model | `mp.math_model` | `mp.math_model_pf_dc` | Constraint formulation, solver interface |
| Task | `mp.task` | `mp.task_pf` | Orchestration, iteration control |

### 3. Separation Quality

| Aspect | Legacy | MP-Core |
|--------|--------|---------|
| Network / Formulation separation | **Partial** -- `makeBdc` builds network params, but `runpf` mixes formulation and solve logic | **Clean** -- `net_model_dc` builds params, `math_model_pf_dc` owns formulation |
| Solver interface separation | **Minimal** -- inline `B\P` call in `dcpf.m` | **Clean** -- `mm.solve()` dispatches through `mp-opt-model` |
| Results extraction | **Inline** -- results written directly into mpc struct within `runpf` | **Layered** -- `port_inj_soln()` computes flows, `network_model_update` populates results |
| Data model | **Flat matrices** -- bus/gen/branch as numeric arrays with named column constants | **Element objects** -- `dme_bus`, `dme_gen`, `dme_branch` classes with typed table storage |

### 4. Internal Interface Documentation

- **Legacy:** Functions documented via MATLAB-style help blocks (docstring at top of file). Column indices documented in `idx_bus.m`, `idx_gen.m`, `idx_brch.m`, `idx_cost.m`. The MATPOWER User's Manual (240+ pages) covers the legacy API comprehensively.
- **MP-Core:** Classes documented with structured docstrings listing Properties and Methods. Mathematical formulations use LaTeX notation in comments (e.g., `form_dc.m` documents `gP(x) = B*Va + K*z + p`). A separate Developer Manual describes the layered architecture. However, the Developer Manual was introduced in 8.0 and is less mature than the User's Manual.
- **Extension API:** `mp.extension` base class has comprehensive docstrings. Two reference extensions (`mp.xt_reserves`, `mp.xt_3p`) serve as templates. The Extension API allows adding custom elements, formulations, constraints, and costs without modifying core source files.

### 5. File Inventory Summary

| Directory | File Count | Focus |
|-----------|-----------|-------|
| `lib/` (top-level) | 202 | Legacy functions + shared utilities |
| `lib/+mp/` | 208 | MP-Core classes (data/network/math models, elements, forms) |
| `mp-opt-model/lib/` | 50+ | Optimization model abstraction + solver interfaces |
| `mips/lib/` | ~20 | Built-in interior-point solver (MIPS) |
| `most/lib/` | ~25 | Multi-period scheduling extension |

Total: ~505 source files in the core library.

### 6. Solver Interface Architecture

The solver interface is cleanly separated through `mp-opt-model` (a standalone package):

```
User code → mpoption('opf.dc.solver', 'GLPK')  — solver selection
         → dcopf_solver(om, mpopt)              — legacy path
            → om.solve(opt)                      — dispatches to solver
               → qps_master(H, c, A, ...)       — LP/QP dispatcher
                  → qps_glpk / qps_mips / qps_highs / ...  — solver-specific wrappers
```

Each solver has its own options-conversion function (e.g., `glpk_options.m`, `gurobi_options.m`) and feature-detection function (e.g., `have_feature_glpk.m`). Solver swap is a single parameter change with no reformulation.

### 7. Architectural Strengths

1. **Backward compatibility:** Legacy code from 1997 still runs unmodified on 8.1. The `rundcpf` function is a 2-line wrapper.
2. **Extension API:** The MP-Core framework provides a principled mechanism for adding custom element types, formulations, and constraints without forking.
3. **Mathematical transparency:** The core solver (`dcpf.m`) is 46 lines. The entire DCPF computation is a sparse matrix backslash operation -- fully inspectable.
4. **Modular solver interface:** 12+ solver backends accessible through a unified `mpoption` parameter.

### 8. Architectural Weaknesses

1. **Dual-framework complexity:** Having two complete parallel architectures (legacy + MP-Core) increases the surface area for new developers. It is unclear which framework to target for new work.
2. **Monolithic `runpf.m`:** At 520 lines, the legacy PF dispatcher handles AC/DC branching, Q-limit enforcement, bus type management, and result formatting in a single function.
3. **No native multi-period in core:** Multi-period and storage require MOST, which has its own data model (`mdi` struct) that is not integrated with the MP-Core data model.
4. **Flat data model:** The legacy `mpc` struct uses numeric matrices with integer column indices. While fast and transparent, it provides no type safety or column-name validation. Typos in column indices produce silent wrong results.

## Implications

MATPOWER's architecture earns strong marks for transparency and extensibility. The dual-framework design (legacy + MP-Core) is a transitional pattern, but both are well-documented and the legacy API's simplicity is a significant advantage for inspectability. The clean solver interface separation and the formal Extension API place MATPOWER among the most architecturally mature tools in this evaluation.
