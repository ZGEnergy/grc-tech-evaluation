---
test_id: F-8
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-8: Solver Dependency

## Question

Does MATPOWER function fully on open-source solvers alone, or are there
capabilities that require commercial solvers?

## Solver Inventory

### Open-Source Solvers Available

| Solver | Type | License | Bundled? | Capabilities |
|--------|------|---------|----------|-------------|
| MIPS | NLP/QP/LP | BSD-3 | YES (part of MATPOWER) | AC OPF, DC OPF, general NLP |
| GLPK | LP/MILP | GPL-3 | YES (part of Octave) | DC OPF, MOST LP problems, MILP (UC) |
| HiGHS | LP/MIP/QP | MIT | NO (optional install) | DC OPF, UC, QP problems |
| IPOPT | NLP | EPL-2.0 | NO (requires MEX build) | Large-scale AC OPF |
| OSQP | QP | Apache-2.0 | NO (requires MEX build) | QP problems |

### Commercial Solvers Supported

| Solver | Type | Required? | Notes |
|--------|------|-----------|-------|
| MATLAB linprog/quadprog | LP/QP | NO | Only in MATLAB (not Octave) |
| Gurobi | LP/MILP/QP | NO | Optional high-performance solver |
| CPLEX | LP/MILP/QP | NO | Optional via MATLAB interface |
| MOSEK | LP/QP/SDP | NO | Optional for SDP relaxation |
| BPMPD | QP | NO | Legacy solver, rarely used |

## Capability Matrix (Open-Source Only)

| Analysis Type | Solver Used | Works? | Notes |
|---------------|-------------|--------|-------|
| DC Power Flow | Direct solve (no optimizer) | YES | Matrix inversion, no solver needed |
| AC Power Flow | Newton-Raphson (built-in) | YES | No external solver needed |
| DC OPF | MIPS or GLPK | YES | Fully functional |
| AC OPF | MIPS | YES | Converges on standard cases |
| Large AC OPF (1000+ bus) | MIPS | PARTIAL | MIPS may be slow; IPOPT recommended |
| MOST Economic Dispatch | GLPK or MIPS | YES | LP problem |
| MOST Unit Commitment | GLPK | YES | MILP problem |
| MOST SCOPF | GLPK or MIPS | YES | May have convergence issues (see most_ex5) |
| CPF (Continuation PF) | Built-in | YES | No external solver needed |
| Sensitivity (PTDF/LODF) | Direct computation | YES | Matrix operations only |
| SDP Relaxation (extras) | MOSEK/SeDuMi | PARTIAL | Requires SDP solver (SeDuMi is free) |

## Commercial-Only Capabilities

**None for core functionality.** All standard MATPOWER analyses (PF, OPF, MOST,
CPF, sensitivity) work with open-source solvers.

The only capability that may benefit from commercial solvers is **performance on
very large networks** (10,000+ buses), where IPOPT (open-source, EPL) or Gurobi
(commercial) significantly outperform MIPS.

## GLPK Limitation

GLPK handles LP and MILP but **not QP (quadratic programming)**. This means:
- Quadratic cost curves in OPF require MIPS (or another QP-capable solver)
- MOST with quadratic costs requires piecewise-linear conversion (documented
  in A-5 test workaround)
- This is a **solver limitation**, not a MATPOWER limitation

## Assessment

**PASS.** MATPOWER functions fully on open-source solvers for all core
capabilities. The bundled MIPS solver handles NLP/QP/LP, and GLPK (bundled
with Octave) handles LP/MILP. No commercial solver is required for any
standard analysis type. Commercial solvers offer performance benefits on
large networks but are never functionally required.
