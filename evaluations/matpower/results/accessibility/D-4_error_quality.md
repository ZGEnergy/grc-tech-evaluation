---
test_id: D-4
tool: matpower
dimension: accessibility
network: case39
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# D-4: Error Quality — Deliberate Error Messages on case39

## Methodology

Introduced three deliberate errors into the IEEE 39-bus case and recorded MATPOWER's
error messages. Each error was tested via:

```
.devcontainer/dc-exec -C /workspace/evaluations/matpower octave --eval "<test_code>"
```

## Test (a): Infeasible OPF — Line RATE_A set to 0.001 MW

**Setup:** Set `mpc.branch(1, 6) = 0.001` (RATE_A of branch 1 to near-zero).

**Exact output:**

```
MATPOWER Version 8.1, 12-Jul-2025
Optimal Power Flow -- DC formulation
MATPOWER Interior Point Solver -- MIPS, Version 1.5.2, 12-Jul-2025
 (using built-in linear solver)
Numerically Failed

Did not converge in 14 iterations.
OPF failed

>>>>>  Did NOT converge (0.18 seconds)  <<<<<

SUCCESS flag: 0
```

**Classification: MEANINGFUL but INDIRECT.** The solver reports non-convergence
and sets `success = 0`. However, it does not identify the infeasible constraint
(branch 1 flow limit). The user must diagnose which constraint caused infeasibility
by examining shadow prices or branch flow results. The "Numerically Failed" message
is accurate but not actionable — an "infeasible" classification with the binding
constraint would be more helpful.

**Rating: 6/10** — Correctly signals failure; does not explain cause.

## Test (b): Missing Generator Cost Curve — gencost rows truncated

**Setup:** Set `mpc.gencost = mpc.gencost(1:3, :)` (keep only 3 of 10 gencost rows).

**Exact output:**

```
ERROR: index (10,_): out of bound 3 (dimensions are 3x7)
```

**Classification: CRYPTIC.** The error is a raw Octave indexing error from inside
MATPOWER's internal code. It does not mention "gencost", "generator", or "cost curve"
anywhere. A user unfamiliar with MATPOWER internals would have no idea that the
mismatch between `gen` rows (10) and `gencost` rows (3) is the problem. MATPOWER
performs no validation of the mpc struct dimensions before running.

**Rating: 2/10** — Raw array indexing error with no domain context.

## Test (c): Invalid Bus Type — bus type set to 99

**Setup:** Set `mpc.bus(1, 2) = 99` (invalid BUS_TYPE for bus 1).

**Exact output:**

```
ERROR: ext2int: bus 1 has an invalid BUS_TYPE
```

**Classification: MEANINGFUL and SPECIFIC.** The error message identifies:
- The function where the error occurred (`ext2int`)
- The specific bus (`bus 1`)
- The exact problem (`invalid BUS_TYPE`)

This is the best error message of the three. The `ext2int` conversion step validates
bus types before any computation begins.

**Rating: 9/10** — Clear, specific, actionable.

## Summary

| Error | Message Quality | Classification | Rating |
|-------|----------------|----------------|--------|
| (a) Infeasible OPF | Non-convergence reported, no cause | Meaningful but indirect | 6/10 |
| (b) Missing gencost | Raw indexing error | Cryptic | 2/10 |
| (c) Invalid bus type | Specific, identifies bus and field | Meaningful and specific | 9/10 |

## Key Findings

1. **No input validation layer.** MATPOWER does not validate mpc struct dimensions
   (e.g., `nrow(gencost) == nrow(gen)`) before computation. This leads to cryptic
   array indexing errors deep in the call stack.

2. **Bus type validation exists** in `ext2int()`, demonstrating that validation
   is possible when implemented. The inconsistency suggests piecemeal validation
   rather than systematic input checking.

3. **Solver failures lack root-cause analysis.** When the optimizer fails to
   converge, MATPOWER reports non-convergence but does not attempt to identify
   which constraints are infeasible or which variables are unbounded.

4. **No silent failures observed.** All three errors produce visible output.
   MATPOWER does not silently return incorrect results for these error types.
