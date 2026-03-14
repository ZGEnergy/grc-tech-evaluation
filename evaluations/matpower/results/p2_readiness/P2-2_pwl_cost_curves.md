---
test_id: P2-2
tool: matpower
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-14T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "f7b76d2b"
---

# P2-2: Piecewise-Linear Cost Curve Support

## Result: INFORMATIONAL

## Capability: Yes -- native, first-class support

MATPOWER's `gencost` matrix natively supports piecewise-linear (PWL) cost curves as one of
two built-in cost models. The `MODEL` column (column 1 of `gencost`) selects the cost type:

| MODEL | Constant | Format |
|-------|----------|--------|
| 1 | `PW_LINEAR` | Breakpoints as (MW, $) pairs |
| 2 | `POLYNOMIAL` | Coefficients of polynomial: c_n, ..., c_1, c_0 |

## Formulation Type

PWL costs are represented as ordered breakpoint pairs in the `gencost` matrix:

```
[MODEL=1, STARTUP, SHUTDOWN, NCOST, p1, f1, p2, f2, ..., pn, fn]
```

Where `(pi, fi)` are (MW output, cost in $/hr) pairs. MATPOWER internally converts PWL
costs to a linear program formulation using auxiliary "helper" variables and constraints:
for each generator with `n` breakpoints, `n-1` auxiliary variables and constraints are
added to represent the cost as the maximum of `n-1` linear segments. This is the standard
LP reformulation of piecewise-linear convex functions.

## Solver Compatibility

Functionally verified on IEEE 9-bus case with 3-breakpoint PWL costs:

| Solver | Problem | Success | Objective |
|--------|---------|---------|-----------|
| MIPS (built-in) | DC OPF | Yes | $7,829.17 |
| MIPS (built-in) | AC OPF | Yes | $7,897.51 |
| GLPK | DC OPF | Yes | $7,829.17 |

PWL costs are compatible with all MATPOWER solvers because the LP/QP reformulation is
performed by MATPOWER's problem builder before dispatching to the solver. Any solver
that handles LP (for PWL) or QP (for polynomial) works.

Specific solver compatibility:
- **DC OPF with PWL:** Pure LP -- compatible with MIPS, GLPK, IPOPT, CPLEX, Gurobi,
  MOSEK, HiGHS, OSQP, CLP, BPMPD
- **AC OPF with PWL:** NLP with linear cost -- compatible with MIPS, IPOPT, KNITRO,
  FMINCON
- **MOST (multi-period) with PWL:** Supported via the same `gencost` mechanism

## Conversion Utility

MATPOWER provides `poly2pwl()` for converting polynomial costs to piecewise-linear
approximations:

```matlab
pwl_cost = poly2pwl(poly_cost, Pmin, Pmax, npts);
```

This generates `npts` breakpoints between `Pmin` and `Pmax` by evaluating the polynomial.
Note: `poly2pwl` fails when `Pmin == Pmax` (zero-width generators), as reported in the
C-3 scalability test.

## Limitations

1. **Convexity required.** PWL cost curves must be convex (slopes must be non-decreasing).
   Non-convex PWL costs will cause solver issues or incorrect results because the LP
   reformulation assumes convexity.

2. **Variable-width gencost matrix.** Because PWL generators may have different numbers
   of breakpoints, the `gencost` matrix must be wide enough to accommodate the generator
   with the most breakpoints. Unused trailing columns are zero-padded. This is a minor
   data handling inconvenience but not a functional limitation.

3. **poly2pwl edge case.** The `poly2pwl()` conversion utility fails on generators with
   `Pmin == Pmax` (degenerate case). This was observed in the C-3 scalability test on the
   ACTIVSg2000 network (117 generators with `Pmin == Pmax`).

## Functional Probe

```matlab
define_constants;
mpc = loadcase('case9');

% Set PWL costs: 3 breakpoints per generator
for g = 1:size(mpc.gen, 1)
    pmin = mpc.gen(g, PMIN);
    pmax = mpc.gen(g, PMAX);
    pmid = (pmin + pmax) / 2;
    mpc.gencost(g, :) = 0;
    mpc.gencost(g, MODEL) = PW_LINEAR;
    mpc.gencost(g, NCOST) = 3;
    mpc.gencost(g, COST:COST+5) = [pmin pmin*20 pmid pmid*25 pmax pmax*35];
end

% Solve -- both DC and AC OPF succeed with PWL costs
mpopt = mpoption('verbose', 0, 'out.all', 0);
results_dc = rundcopf(mpc, mpopt);  % success=1, f=$7829.17
results_ac = runopf(mpc, mpopt);    % success=1, f=$7897.51
```
