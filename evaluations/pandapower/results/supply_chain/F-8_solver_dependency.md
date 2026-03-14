---
test_id: F-8
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "474ecf01"
---

# F-8: Open-Source Solver Sufficiency

## Summary

pandapower includes its own internal PYPOWER-based solver for both power flow and
optimal power flow. No external solver binary is required. All built-in algorithms
are open-source. **Grade: A.**

## Findings

### Internal Solver Architecture

pandapower embeds a fork of PYPOWER (itself a Python port of MATPOWER) as its core
solver engine. This solver is shipped as part of the pandapower package — no separate
installation, licensing, or binary download is needed.

### Power Flow Algorithms (all built-in)

| Algorithm          | Flag     | Status    |
|--------------------|----------|-----------|
| Newton-Raphson     | `nr`     | Converged |
| Gauss-Seidel       | `gs`     | Converged |
| Fast-Decoupled BX  | `fdbx`   | Converged |
| Fast-Decoupled XB  | `fdxb`   | Converged |
| Backward/Forward   | `bfsw`   | Available (radial networks) |

All five algorithms are implemented in pure Python (with optional Numba JIT
acceleration) and require no external solver.

### Optimal Power Flow (built-in)

The internal OPF solver (`pp.runopp()`) uses PYPOWER's interior-point method.
Verified functional on the IEEE 9-bus case with no external solver dependency.

### Optional External Solvers

| Solver         | Access Path              | Required? |
|----------------|--------------------------|-----------|
| lightsim2grid  | `[performance]` extra    | No — C++ accelerator for NR, not a different solver |
| PandaModels.jl | `[pandamodels]` extra    | No — alternative OPF via Julia bridge |
| OR-Tools       | `[performance]` extra    | No — optional for network optimization tasks |

### Commercial Solver Requirements

**None.** No test case or documented workflow in pandapower requires a commercial
solver. The tool is fully functional on its bundled open-source solver stack.

Unlike tools that delegate to external LP/NLP solvers (e.g., HiGHS, Ipopt, GLPK),
pandapower's architecture bundles the solver directly, eliminating solver procurement
as a deployment concern.

## Risks

None. The self-contained solver architecture is a supply-chain strength — there is
no external solver binary to version-manage, license-audit, or air-gap-transfer.
