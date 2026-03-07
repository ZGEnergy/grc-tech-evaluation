---
test_id: P2-2
tool: matpower
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: 0.4487
peak_memory_mb: null
loc: 120
solver: MIPS
timestamp: "2026-03-06T00:00:00Z"
---

# P2-2: Piecewise-Linear Cost Curve Support

## Result: INFORMATIONAL -- Native Support, Fully Functional

## Capability: YES (Native, First-Class)

MATPOWER natively supports piecewise-linear (PWL) cost curves as a first-class cost
model alongside polynomial costs. PWL is MODEL=1 in the gencost matrix (polynomial
is MODEL=2).

## Formulation

PWL costs are defined in the `gencost` matrix with the following row format:

```
[1, startup, shutdown, n, x1, y1, x2, y2, ..., xn, yn]
```

Where `n` is the number of breakpoints and `(xi, yi)` are power-cost pairs.
MATPOWER internally converts PWL to a linear program using Constrained Cost
Variables (CCV) -- one auxiliary "basin constraint" variable per PWL generator
(see `opf_setup.m` lines 369-484). Single-segment PWL costs are optimized
by converting directly to equivalent linear polynomial costs. This formulation
is compatible with all LP solvers. Note: MATPOWER does not use SOS2 or lambda
formulations.

## Functional Probe: 3-Segment PWL on TINY

### Setup
- Generator 1 (bus 30, PMAX=1040 MW) modified from polynomial to 3-segment PWL
- Segments: $8/MWh (0-347 MW), $12/MWh (347-693 MW), $20/MWh (693-1040 MW)
- Remaining 9 generators retained polynomial costs (mixed model test)

### PWL Breakpoints Defined

| Point | Power (MW) | Cost ($/hr) |
|-------|-----------|-------------|
| 1     | 0.0       | 0.2         |
| 2     | 346.7     | 2,773.5     |
| 3     | 693.3     | 6,933.5     |
| 4     | 1040.0    | 13,866.9    |

### Results

- **DCOPF converged:** Yes
- **Objective:** $43,195.36/hr (vs $41,263.94/hr baseline polynomial)
- **Gen 1 dispatch:** 693.3 MW (operating at segment 2/3 boundary)
- **Gen 1 operating segment:** Segment 2 (marginal cost $12/MWh)
- The optimizer correctly dispatched Gen 1 up to the segment 2/3 boundary,
  avoiding the expensive $20/MWh segment 3

### Dispatch Impact

| Gen# | Bus | Polynomial (MW) | PWL-Mix (MW) | Delta (MW) |
|------|-----|-----------------|--------------|------------|
| 1    | 30  | 660.8           | 693.3        | +32.5      |
| 2    | 31  | 646.0           | 646.0        | 0.0        |
| 3    | 32  | 660.8           | 652.7        | -8.1       |
| 6    | 35  | 660.8           | 652.7        | -8.1       |
| 9    | 38  | 660.8           | 652.7        | -8.1       |
| 10   | 39  | 660.8           | 652.7        | -8.1       |

Gen 1 increased dispatch (cheap segments) while others reduced, consistent with
the optimizer exploiting the lower marginal cost in Gen 1's first two segments.

## All-PWL Test (10-Segment Approximation)

All 10 generators converted from polynomial to 10-segment PWL (approximating
the original quadratic curves):

- **Converged:** Yes
- **Polynomial objective:** $41,263.94/hr
- **All-PWL objective:** $41,296.61/hr
- **Difference:** 0.08% (expected approximation error from discretization)

This confirms that 10-segment PWL closely approximates the original quadratic costs.

## Solver Compatibility

| Solver | PWL Support | Notes |
|--------|-------------|-------|
| MIPS   | Yes         | Built-in interior point, handles LP from PWL |
| GLPK   | Yes         | LP/MILP solver, natural fit for PWL |
| Gurobi | Yes         | Commercial LP/QP/MILP |
| CPLEX  | Yes         | Commercial LP/QP/MILP |

PWL costs convert the OPF to a pure LP (no quadratic terms in objective), making
them compatible with any LP solver. This is advantageous for MILP UC problems
where GLPK cannot handle QP but can handle LP+integers.

## Limitations

1. **Convexity required:** PWL curves must be convex (increasing marginal costs) for
   OPF. Non-convex PWL curves will produce incorrect results or solver failures.
2. **Manual definition:** No helper function to auto-convert polynomial to PWL; user
   must construct the breakpoints (though the pattern is straightforward, ~15 LOC).
3. **gencost matrix width:** PWL rows with many segments may require expanding the
   gencost matrix (different generators can have different numbers of segments, but
   the matrix must accommodate the widest row).

## Test Script

`evaluations/matpower/tests/p2_readiness/test_p2_2_piecewise_linear_costs_tiny.m`
