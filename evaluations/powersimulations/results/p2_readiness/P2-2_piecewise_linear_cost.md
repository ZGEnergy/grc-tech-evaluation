---
test_id: P2-2
tool: powersimulations
dimension: p2_readiness
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "e6aab840"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# P2-2: Piecewise-Linear Cost Curve Support

## Result: INFORMATIONAL

## Capability Assessment

| Question | Answer |
|----------|--------|
| Piecewise-linear cost curves supported? | **Yes** -- first-class support |
| Formulation type | SOS2 (Special Ordered Sets of Type 2) |
| Data representation | `PiecewiseLinearData` (input-output points) or `PiecewiseStepData` (incremental) |
| All thermal formulations supported? | Yes -- all 9 dispatch and UC formulations |
| Solver compatibility | Any solver supporting SOS2 constraints (HiGHS, GLPK, Gurobi, CPLEX) |

## Type Hierarchy (Verified in Devcontainer)

PowerSystems.jl provides a layered cost curve type system:

### FunctionData (raw curve shapes)

```
FunctionData (abstract)
  +-- LinearFunctionData          # y = mx + b
  +-- QuadraticFunctionData       # y = ax^2 + bx + c
  +-- PiecewiseLinearData          # [(x1,y1), (x2,y2), ...] input-output points
  +-- PiecewiseStepData            # [x_coords], [y_coords] step function (incremental)
```

### ValueCurve (semantic curve wrappers)

```
ValueCurve (abstract)
  +-- InputOutputCurve            # Total cost = f(power)
  +-- IncrementalCurve            # Marginal cost = f(power)
  +-- AverageRateCurve            # Average cost = f(power)
```

Any `ValueCurve` variant can wrap any `FunctionData` variant. For piecewise-linear costs:
- `InputOutputCurve(PiecewiseLinearData(...))` = total cost breakpoints (PiecewisePointCurve)
- `IncrementalCurve(PiecewiseStepData(...))` = marginal cost blocks (PiecewiseIncrementalCurve)

### ProductionVariableCostCurve (cost model wrappers)

```
ProductionVariableCostCurve (abstract)
  +-- CostCurve{T<:ValueCurve}   # Cost in $/h
  +-- FuelCurve{T<:ValueCurve}   # Fuel in MBTU/h (multiplied by fuel price)
```

### Construction Example (Verified)

```julia
# Input-output breakpoints: (MW, $/h)
pts = [(0.0, 0.0), (100.0, 2500.0), (200.0, 6000.0), (300.0, 10500.0)]
pwd = PiecewiseLinearData(pts)
ioc = InputOutputCurve(pwd)
cc = CostCurve(ioc)
# Result type: CostCurve{PiecewisePointCurve}
```

This was verified in the devcontainer:
```
CostCurve{PiecewisePointCurve}(
  PiecewisePointCurve([(x = 0.0, y = 0.0), (x = 100.0, y = 2500.0),
   (x = 200.0, y = 6000.0), (x = 300.0, y = 10500.0)]),
  UnitSystem.NATURAL_UNITS = 2, LinearCurve(0.0, 0.0))
```

## PSI Formulation Details

### SOS2 Implementation

PowerSimulations.jl uses **SOS2 constraints** for piecewise-linear cost curves. The
relevant internal functions identified in the PSI namespace:

| Symbol | Purpose |
|--------|---------|
| `_add_pwl_sos_constraint!` | Adds SOS2 constraint set for piecewise breakpoints |
| `_get_sos_value` | Extracts SOS2 variable values |
| `get_sos_status` / `sos_status` | Queries SOS2 variable status |
| `SOSStatusVariableModule` | Module managing SOS2 status variables |
| `PieceWiseLinearCostVariable` | Sparse variable for PWL cost segments |
| `PieceWiseLinearCostConstraint` | Constraint linking PWL cost to dispatch |
| `PieceWiseLinearUpperBoundConstraint` | Upper bound on PWL segments |
| `PieceWiseLinearBlockOffer` / `...Constraint` | Block offer formulation variant |

### Formulation Compatibility

Per the PSI documentation, **all thermal formulations** support piecewise-linear costs:

| Formulation | PWL Cost Support |
|-------------|-----------------|
| ThermalBasicDispatch | Yes |
| ThermalDispatchNoMin | Yes |
| ThermalCompactDispatch | Yes |
| ThermalStandardDispatch | Yes |
| ThermalBasicUnitCommitment | Yes |
| ThermalBasicCompactUnitCommitment | Yes |
| ThermalCompactUnitCommitment | Yes |
| ThermalStandardUnitCommitment | Yes |
| ThermalMultiStartUnitCommitment | Yes |

The documentation states: "variable costs can be linear, quadratic or piecewise-linear
formulations." The formulation is selected automatically based on the `FunctionData` type
in the generator's `CostCurve`.

### Solver Compatibility

SOS2 constraints are supported by:
- **HiGHS** (open source, installed in evaluation environment)
- **GLPK** (open source, installed in evaluation environment)
- **Gurobi** (commercial)
- **CPLEX** (commercial)
- **SCIP** (open source, installed in evaluation environment)

Ipopt (NLP solver) does **not** support SOS2 constraints, but piecewise-linear costs are
only used in LP/MIP formulations, not NLP.

## Implications for Phase 2

Piecewise-linear cost curves are **fully supported** with no workarounds needed. The
implementation uses industry-standard SOS2 formulation, which is well-supported by all
major MIP solvers. The type system is flexible enough to represent both input-output
(total cost) and incremental (marginal cost) piecewise curves.

For a production deployment:
- Generator cost data can be loaded as `PiecewiseLinearData` breakpoints
- PSI automatically generates SOS2 constraints in the JuMP model
- No custom constraint assembly or formulation work required
- Both dispatch (ED) and commitment (UC) formulations support PWL costs natively
