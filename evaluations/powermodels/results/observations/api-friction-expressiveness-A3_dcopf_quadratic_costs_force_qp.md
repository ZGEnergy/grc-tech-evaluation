---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
network: MEDIUM
tool: powermodels
severity: high
timestamp: 2026-03-11T05:15:00Z
---

# API Friction: solve_dc_opf silently switches to QP when generator costs are quadratic

## Observation

When `PowerModels.solve_dc_opf` is called on a network where generator cost models contain quadratic terms (polynomial model 2 with 3 coefficients: `[c2, c1, c0]` where `c2 > 0`), the function silently generates a QP problem instead of the LP that practitioners expect from "DC OPF."

On the ACTIVSg10k network:
- 1130 out of 2485 generators (45.5%) have non-zero quadratic cost terms
- HiGHS receives a problem declared as "QP has 34,924 rows; 24,643 cols; 89,902 matrix nonzeros; 24,643 Hessian nonzeros"
- HiGHS QP solver ran for 300s and hit `TIME_LIMIT` without convergence

The LP formulation (after dropping c2 terms) solved in 89.24s with `OPTIMAL` status. The QP formulation — representing the exact same network with the original cost functions — failed within the 300s budget.

## Root Cause

PowerModels.jl faithfully passes the cost model to JuMP/HiGHS. This is correct behavior — the quadratic costs are in the data. However, the user receives no warning that:
1. The problem is now a QP (not an LP)
2. QP at this scale is substantially harder than LP
3. HiGHS's QP solver (interior-point ASM method) is much slower than its LP solver for large-scale problems

The `solve_dc_opf` function name implies LP semantics ("DC" OPF conventionally uses linearized costs), but the API accepts quadratic costs without comment.

## Evidence

From test run output (A-3 MEDIUM, initial QP attempt):

```

QP has 34924 rows; 24643 cols; 89902 matrix nonzeros; 24643 Hessian nonzeros
...
Model status        : Time limit reached
QP ASM    iterations: 10645
HiGHS run time      :        300.30

```

After dropping c2 terms:

```

LP has 34924 rows; 24643 cols; 89902 nonzeros
Model status        : Optimal
Simplex   iterations: 6032
HiGHS run time      :         89.24

```

## Workaround

Manually drop the quadratic cost coefficient before calling `solve_dc_opf`:

```julia

for (_, gen) in data["gen"]
    if get(gen, "model", 2) == 2 && get(gen, "ncost", 0) >= 3
        if abs(gen["cost"][1]) > 1e-10
            gen["cost"]  = [gen["cost"][2], gen["cost"][3]]
            gen["ncost"] = 2
        end
    end
end

```

This is a **stable** workaround but changes the problem formulation. The evaluator must know to check cost model types before running DC OPF on unfamiliar networks.

## Implications

At MEDIUM scale, DC OPF with quadratic costs is effectively unsolvable via the standard API within the 300s evaluation time limit. Networks loaded from MATPOWER .m files commonly include quadratic cost terms, meaning this issue will arise on any real-world benchmark network. This is a significant usability gap for practitioners running DC OPF on production-scale cases.

## Version

PowerModels.jl v0.21.5, HiGHS 1.13.1, Julia 1.10.
