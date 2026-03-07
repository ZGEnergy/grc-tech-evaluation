---
test_id: F-5
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-5: Solver Openness

## Criteria

Verify that all required solvers (LP, MILP, NLP) are open-source or that the tool
functions fully on open-source solvers alone.

## Result: PASS

GridCal functions fully on open-source solvers for all tested analyses. No commercial
solver is required.

### Solver Inventory

| Solver | License | Status | Use Case |
|--------|---------|--------|----------|
| HiGHS (via highspy) | MIT | Bundled, works | LP/MILP (OPF, unit commitment) |
| SCIP (via PuLP) | Apache-2.0 | Available, works | MILP alternative |
| CBC (via PuLP) | EPL-2.0 | Listed but fails at runtime | Not functional |
| Newton-Raphson (built-in) | MPL-2.0 | Built-in, works | AC power flow |
| Interior Point (built-in) | MPL-2.0 | Built-in, works | AC power flow |
| scipy.sparse.linalg | BSD | Bundled, works | DC power flow linear solve |

### Evidence

- OPF test cases (IEEE 5-bus, 14-bus) run successfully with HiGHS
- SCIP confirmed functional as alternative MIP solver
- CBC is present in the `MIPSolvers` enum but raises "PuLP Unsupported MIP solver CBC"
  at runtime -- this is a non-issue since HiGHS and SCIP cover all MIP needs
- GLPK is not exposed through GridCal's solver enum
- Ipopt is not used; GridCal implements its own Newton-Raphson and Interior Point
  solvers for nonlinear power flow in pure Python

### Key Finding

The primary solver (HiGHS, MIT license) is bundled as a direct dependency via `highspy`,
requiring no separate installation. This simplifies deployment and eliminates solver
procurement as a concern.
