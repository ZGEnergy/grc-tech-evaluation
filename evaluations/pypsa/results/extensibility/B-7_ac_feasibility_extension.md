---
test_id: B-7
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.0002
peak_memory_mb: null
loc: 149
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-7: AC Feasibility Extension

## Result: PASS

## Approach

Audited the A-4 (AC Feasibility Check) result file to assess whether workarounds were
needed and classify their durability. A-4 passed with `workaround_class: stable`.

## Finding

A-4 required two workarounds, both classified as **stable**:

### Workaround 1: OPF-to-PF dispatch transfer

- **What:** Manually set `p_set` on generators from DC OPF dispatch results before
  running `n.pf()`.
- **Why:** PyPSA separates OPF (`n.optimize()`) from PF (`n.pf()`). To run AC PF on
  OPF dispatch, the user must transfer dispatch results to generator `p_set` attributes.
- **Durability:** stable -- Uses documented public API (`generators.p_set` and `n.pf()`).
  The approach is shown in PyPSA examples and the convenience method
  `n.optimize.optimize_and_run_non_linear_powerflow()` exists for this exact pattern.
- **Effort level:** Low (3-4 lines of code). A one-liner convenience method also exists.
- **Version risk:** Low -- public API, stable across versions.
- **Grade impact:** Minimal. Standard two-step pattern.

### Workaround 2: Manual gencost assignment (inherited from A-3)

- **What:** Manually parsed gencost data from MATPOWER `.m` file and set
  `n.generators['marginal_cost']` for each generator.
- **Why:** `import_from_pypower_ppc()` does not import the `gencost` table.
- **Durability:** stable -- Uses documented public `marginal_cost` attribute. The
  limitation is well-documented (PyPSA emits a warning about unsupported PPC features).
- **Effort level:** Low (5 lines of code). Import limitation, not API limitation.
- **Version risk:** Low -- `marginal_cost` is a core generator attribute.
- **Grade impact:** Minor.

## Overall Assessment

- **Overall durability class:** stable
- **Overall effort level:** low
- **Convenience method exists:** Yes (`n.optimize.optimize_and_run_non_linear_powerflow()`)
- Neither workaround requires internal access or source modification.
- Both workarounds use documented public API exclusively.

## Workarounds

See "Finding" section above. Both workarounds are stable.

## Timing

- **Wall-clock:** < 0.001 s (audit only, no solver invocation)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b7_ac_feasibility_extension.py`
