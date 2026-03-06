---
test_id: D-4
tool: pypsa
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-4: Error quality -- deliberate error testing

## Finding

PyPSA's error reporting is inconsistent. NaN costs produce a clear, actionable error.
Zero line limits produce a solver-level "infeasible" status without explaining which
constraint caused infeasibility. Invalid bus types are silently accepted with no
validation, producing potentially incorrect results.

## Evidence

### (a) Line limit set to 0 in DC OPF

Setting `n.lines.loc["L0", "s_nom"] = 0` and running `n.optimize()`:

- **Result:** `('warning', 'infeasible')` returned as status tuple
- **No exception raised.** The solver returns infeasible status, but PyPSA does not
  explain which constraint caused infeasibility
- **Objective:** `None` (correctly reflects no solution)
- **Assessment:** The user gets a status code but no diagnostic help. A power-systems
  tool should identify zero-capacity lines as likely infeasibility sources. The error
  is not actionable without manual debugging.

### (b) All generator marginal_cost set to NaN

Setting `n.generators['marginal_cost'] = float('nan')` and running `n.optimize()`:

- **Warning emitted:** `"Encountered nan's in static data for columns ['marginal_cost']
  of component 'Generator'."`
- **Exception raised:** `ValueError: LinearExpression contains nan's in field(s) ['coeffs']`
- **Assessment:** Good error reporting. The consistency check warns about NaN data before
  the solve attempt, and the linopy layer catches the NaN propagation with a clear message.
  The user can trace the problem to the specific field.

### (c) Invalid bus type

Setting `n.buses.loc["1", "control"] = "InvalidType"`:

- **No validation on assignment.** The string "InvalidType" is accepted silently.
- **`n.lpf()` succeeds** despite the invalid bus type. The bus control column shows
  `['InvalidType', 'PQ', 'PV', 'Slack']`.
- **`n.pf()` succeeds** despite the invalid bus type.
- **`n.optimize()` succeeds** and returns optimal status with an objective value.
- **Assessment:** This is a silent-failure pattern. There is no input validation on bus
  control types. The invalid value is silently ignored by all solvers, producing results
  of unknown correctness. A defensive API should reject or warn on unrecognized
  enumeration values.

### Summary

| Scenario | Behavior | Error quality |
|----------|----------|---------------|
| Line limit = 0 | Solver returns infeasible, no diagnostic | Poor |
| Costs = NaN | Warning + clear ValueError | Good |
| Invalid bus type | Silently accepted, solve succeeds | Poor (silent failure) |

## Implications

Error handling follows a pattern: linopy/solver-level checks (NaN detection) work well,
but PyPSA's own validation layer is weak. The tool does not validate enumeration fields
on assignment, does not explain solver infeasibility, and silently accepts nonsensical
input. This creates debugging burden for users, particularly in production workflows where
silent acceptance of invalid data is a correctness risk.
