---
test_id: D-4
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "683bbbed"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-4: Error Quality

## Result: INFORMATIONAL

## Finding

MATPOWER produces diagnostic errors of mixed quality. Two of three deliberate error tests produce clear, actionable error messages. One test (infeasible OPF via zero line limit) silently succeeds, which is a diagnostic gap.

## Evidence

Three deliberate errors were introduced and tested in the devcontainer.

### Error (a): Infeasible OPF -- line limit set to 0

**Input:** `mpc.branch(1, RATE_A) = 0;` then `rundcopf(mpc, mpopt)`

**Expected behavior:** Error or infeasibility report indicating the zero-capacity branch constraint.

**Actual behavior:**
```
MATPOWER Interior Point Solver -- MIPS, Version 1.5.2, 12-Jul-2025
 (using built-in linear solver)
Converged!
OPF successful
Success: 1
Objective: 41263.9408
```

**Assessment: POOR.** MATPOWER treats `RATE_A = 0` as "no limit" (unlimited capacity), not as "zero capacity." This is documented behavior (`RATE_A = 0` means unconstrained in the MATPOWER convention), but it is counterintuitive and a trap for users who expect `0` to mean "zero capacity." The solver silently succeeds with a different problem than intended. No warning is issued.

**Diagnostic quality:** 1/5 -- Silent misinterpretation of user intent. A user trying to model a disconnected line by setting its limit to zero will get incorrect results with no indication of the problem.

### Error (b): Missing gencost field

**Input:** `mpc2 = rmfield(mpc2, 'gencost');` then `rundcopf(mpc2, mpopt)`

**Expected behavior:** Error message indicating missing cost data.

**Actual behavior:**
```
ERROR: structure has no member 'gencost'
```

**Assessment: GOOD.** The error message is clear and directly identifies the missing field. A user can immediately understand what needs to be fixed. The error occurs early in the execution path (during problem setup, not during the solve).

**Diagnostic quality:** 4/5 -- Clear field name, immediate failure. Could be improved by suggesting the fix (e.g., "OPF requires a gencost matrix -- see help gencost or caseformat").

### Error (c): Invalid bus type

**Input:** `mpc3.bus(1, BUS_TYPE) = 99;` then `rundcpf(mpc3, mpopt)`

**Expected behavior:** Error message indicating invalid bus type.

**Actual behavior:**
```
ERROR: ext2int: bus 1 has an invalid BUS_TYPE
```

**Assessment: EXCELLENT.** The error message identifies:
1. The function where the error was caught (`ext2int`)
2. The specific bus number (bus 1)
3. The specific field that is invalid (`BUS_TYPE`)

**Diagnostic quality:** 5/5 -- Pinpoints the exact bus, the exact field, and the validation stage. A user can fix this immediately.

### Summary Table

| Error | Input | Behavior | Quality | Score |
|-------|-------|----------|---------|-------|
| (a) Zero line limit | `RATE_A = 0` | Silent success (0 = unconstrained) | POOR | 1/5 |
| (b) Missing gencost | `rmfield(mpc, 'gencost')` | Clear error: "structure has no member 'gencost'" | GOOD | 4/5 |
| (c) Invalid bus type | `BUS_TYPE = 99` | Clear error: "bus 1 has an invalid BUS_TYPE" | EXCELLENT | 5/5 |

### Consumed Observations

- [convergence-quality: NR residual not in results struct](../observations/convergence-quality-expressiveness-A-2_acpf.md) -- convergence diagnostics accessible only via verbose output, not programmatically
- [api-friction: MIPS solver fails with user constraints](../observations/solver-issues-extensibility-B-1_custom_constraints.md) -- MIPS produces "matrix singular to machine precision" warnings but continues iterating rather than failing fast

### Additional Error Quality Observations from Suite A/B Testing

- **MIPS numerical singularity:** When custom constraints cause numerical issues, MIPS prints `warning: matrix singular to machine precision, rcond = X.XXe-XX` but continues iterating until `max iterations` rather than failing fast. The eventual failure message (`MIPS: Numerically Failed`) does not indicate which constraint caused the problem. (Score: 2/5)
- **GLPK exitflag mapping:** GLPK's `GLP_EMIPGAP` (gap tolerance reached) is mapped to `exitflag=-9` by MATPOWER, which is treated as failure. No error message explains this -- the user sees only `exitflag=-9` and must read GLPK source to understand. (Score: 1/5)
- **AC PF convergence:** When NR fails to converge, MATPOWER prints "Newton's method power flow did not converge in N iterations." Clear and actionable. (Score: 4/5)

## Implications

MATPOWER's error diagnostics are strong for data validation (invalid bus types, missing fields) but weak for solver-level issues (numerical singularity, solver return codes) and semantic traps (`RATE_A = 0` meaning unconstrained). The RATE_A convention is particularly problematic because it produces silently wrong results rather than an error -- a user cannot discover the problem without carefully inspecting dispatch results.

For operational use, the weak MIPS diagnostics and GLPK exitflag mapping issues would require defensive programming (pre-validation of inputs, post-validation of outputs) to catch problems that the tool does not surface.
