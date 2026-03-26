---
test_id: F-8
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: f07fa63f
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
timestamp: 2026-03-14T00:00:00Z
---

# F-8: Solver Dependency

## Result: PASS

## Finding

MATPOWER ships with MIPS (MATPOWER Interior Point Solver), a built-in open-source solver that handles all core power flow and OPF formulations without any external solver dependency. External open-source solvers (GLPK, IPOPT, HiGHS) are optional and extend capability but are not required for core use cases.

## Evidence

**Built-in solver verification:**

| Use Case | Solver Used | Status | Command |
|----------|------------|--------|---------|
| DC Power Flow | Direct linear solve | Pass | `rundcpf(mpc, mpopt)` -- success=1 |
| AC Power Flow | Newton-Raphson (built-in) | Pass | `runpf(mpc, mpopt)` -- success=1 |
| DC OPF (QP) | MIPS (built-in) | Pass | `rundcopf(mpc, mpopt)` -- success=1 |
| AC OPF (NLP) | MIPS (built-in) | Pass | `runopf(mpc, mpopt)` -- success=1 |

All core formulations solve successfully using only built-in solvers, with no external solver configured (solver option set to `DEFAULT`).

**External solver availability in devcontainer:**

| Solver | License | Installed? | Octave Binding? | Use Case |
|--------|---------|------------|-----------------|----------|
| MIPS | BSD 3-Clause | Yes (bundled) | Built-in | PF, OPF (QP/NLP) |
| GLPK | GPL-3.0 | Yes (`glpsol`) | Yes (`have_feature('glpk')` = 1) | LP/MILP only |
| IPOPT | EPL-2.0 | Yes (`ipopt` binary) | No (`have_feature('ipopt')` = 0) | NLP |
| HiGHS | MIT | No | No (`have_feature('highs')` = 0) | LP/MILP/QP |

**GLPK limitation:** GLPK handles only LP problems. Attempting DCOPF with quadratic costs via GLPK produces: `error: qps_glpk: GLPK handles only LP problems, not QP problems`. GLPK works for linear-cost DCOPF formulations.

**IPOPT note:** IPOPT is installed as a system binary but lacks the Octave MEX interface (`ipopt.mex`/`ipopt.oct`), so MATPOWER cannot use it. This is a devcontainer configuration gap, not a MATPOWER limitation.

**HiGHS note:** HiGHS is not installed in the devcontainer Octave environment. MATPOWER supports HiGHS via the `mpoption_info_highs.m` interface, but the Octave binding is not available.

**Commercial solver requirement:** No commercial solver is required for any core MATPOWER functionality. MIPS handles all PF and OPF formulations natively.

## Implications

MATPOWER's built-in MIPS solver eliminates any hard dependency on external solvers for core power system analysis. This is a significant supply chain advantage: the tool is fully functional out of the box with zero external solver dependencies. External solvers (GLPK, IPOPT, HiGHS) are purely optional performance/capability enhancements.
