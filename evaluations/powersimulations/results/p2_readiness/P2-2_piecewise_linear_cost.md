---
test_id: P2-2
tool: powersimulations
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: HiGHS
timestamp: "2026-03-07T05:30:00Z"
---

# P2-2: Piecewise Linear Cost Curves

## Result: INFORMATIONAL

## Finding

PowerSystems.jl **natively supports piecewise linear cost curves** through
`PiecewiseLinearData` and `PiecewiseLinearSlopeData` cost function types. These integrate
directly into PSI's optimization formulations.

### Supported Cost Function Types

| Type | Description | PSI Support |
|------|-------------|-------------|
| `LinearCurve` | Constant marginal cost | Yes |
| `QuadraticCurve` | Quadratic cost (a*x^2 + b*x + c) | Yes |
| `PiecewiseLinearData` | Points (MW, $) defining segments | Yes |
| `PiecewiseLinearSlopeData` | Initial point + slopes per segment | Yes |
| `PolynomialFunctionData` | Arbitrary polynomial | Yes |

### Formulation Type

PSI uses **SOS2 (Special Ordered Sets Type 2)** for piecewise linear cost curves in MIP
formulations. For LP formulations, it uses incremental/lambda formulation via JuMP's
native piecewise linear support.

### Solver Compatibility

| Solver | PiecewiseLinear | Quadratic | Notes |
|--------|----------------|-----------|-------|
| HiGHS | Yes | Yes (QP) | Full support |
| SCIP | Yes | Limited | MIQP support varies |
| GLPK | Yes (LP only) | No | No QP support |
| Ipopt | Yes | Yes | NLP solver |

### API Example

```julia
using PowerSystems

# Define 3-segment piecewise linear cost
cost_data = PiecewiseLinearData([(0.0, 0.0), (100.0, 2000.0), (200.0, 5000.0), (300.0, 9000.0)])
cost_curve = CostCurve(cost_data)
gen_cost = ThermalGenerationCost(cost_curve, nothing, nothing, nothing)
set_operation_cost!(gen, gen_cost)
```

### Limitations

- MATPOWER `.m` files encode costs as polynomials, not piecewise linear — conversion
  needed if source data uses piecewise format
- Visualization of cost curves is not built-in (must use external plotting)
- No automatic convexity checking on user-provided piecewise data
