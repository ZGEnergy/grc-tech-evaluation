---
test_id: D-4
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 02801176
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# D-4: Error Quality (error_quality)

## Result: QUALIFIED PASS

## Finding

Two of three deliberate errors produce meaningful diagnostics; one produces only a WARNING (silent failure). Error quality is good for model-building errors but inadequate for invalid topology references.

## Evidence

**Error 1: Infeasible OPF (zero line capacity)**

Command: Load case39, set all `n.lines.s_nom = 0`, call `n.optimize(solver_name='highs')`.

Output excerpt:
```
Presolving model
Problem status detected on presolve: Infeasible
Model status        : Infeasible
Objective value     :  0.0000000000e+00
HiGHS run time      :          0.00
WARNING:linopy.constants:Optimization potentially failed:
Status: warning
Termination condition: infeasible
Solution: 0 primals, 0 duals
Objective: nan
Solver message: Infeasible
```

**Classification: meaningful diagnostic.** HiGHS correctly reports `Infeasible` with presolve detection. The `linopy` layer surfaces this as `TerminationCondition.infeasible` with a WARNING. The function returns a tuple `(status, condition)` rather than raising — user must check return value rather than catching an exception. This is documented behavior.

---

**Error 2: Generator with no cost curve**

Command: Add `Generator('G1', bus='A')` with no `marginal_cost`, then call `n.optimize()`.

Output:
```
Traceback (most recent call last):
  File "pypsa/optimization/optimize.py", line 323, in define_objective
    raise ValueError(msg)
ValueError: Objective function could not be created. Please make sure the components have assigned costs.
```

**Classification: meaningful diagnostic.** Clear `ValueError` with an actionable message. The traceback points directly to the objective construction failure. The fix is obvious: assign `marginal_cost` to the generator.

---

**Error 3: Line referencing invalid bus**

Command: Add `Line('L1', bus0='INVALID_BUS', bus1='B', x=0.1, s_nom=100)`.

Output:
```
WARNING:pypsa.consistency:The following lines have buses which are not defined. Add them using n.add() or run n.sanitize() to add them automatically. Components with undefined buses:
Index(['L1'], dtype='object', name='name')
```

**Classification: silent failure.** `n.add()` succeeds without raising an exception. The invalid bus reference produces only a WARNING (not an error), and the network object is left in an inconsistent state. The WARNING message is clear and actionable, but a user who does not check logs would proceed with a broken network. No exception is raised at add time or at solve time (solve might fail later with a less obvious error).

---

**Summary:**

| Error | Output | Classification |
|-------|--------|----------------|
| Infeasible OPF (zero capacity) | `TerminationCondition.infeasible` + `Objective: nan` | Meaningful diagnostic |
| Missing cost curve | `ValueError: Objective function could not be created` | Meaningful diagnostic |
| Invalid bus reference | WARNING only, no exception | Silent failure |

## Implications

Error quality is mixed: model-building errors produce clear, actionable exceptions, but topology/referential integrity errors produce only warnings. PyPSA's design choice to defer validation to consistency checks (rather than raising at `n.add()`) means broken networks can be constructed silently. The `n.sanitize()` suggestion in the warning message is helpful but requires the user to check logs. Grade impact: B level — two good, one silent failure on a common mistake (typo in bus name).
