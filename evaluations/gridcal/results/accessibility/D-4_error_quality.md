---
test_id: D-4
tool: gridcal
dimension: accessibility
network: TINY
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# D-4: Error Quality

## Result: FAIL

## Methodology

Introduced three deliberate errors and assessed the quality of error messages produced by VeraGridEngine 5.6.28.

## Error Test (a): Infeasible OPF (line limit = 0)

**Setup:** Set all branch `rate` values to 0.0 on IEEE 39-bus, then ran DC OPF.

**Behavior:** OPF reported `converged: True` with full generation dispatch (6254 MW) and no load shedding. Shadow prices ranged from 0.3 to 473.1 $/MWh.

**Assessment: SILENT FAILURE.** Setting rate=0 did not make the problem infeasible. Instead, GridCal apparently treats rate=0 as "unlimited" rather than "zero capacity". This is a defensible modeling choice but there is no warning that zero-rate branches are being treated as unconstrained. A user intending to model a tripped line by setting rate=0 would get silently wrong results.

**Error quality: Poor** -- no diagnostic, no warning, silent semantic reinterpretation.

## Error Test (b): Missing gen cost curve (Cost = 0)

**Setup:** Set all generator `Cost`, `Cost2`, and `Cost0` to 0.0 on IEEE 39-bus, then ran DC OPF.

**Behavior:** OPF reported `converged: True`. Dispatch was produced (non-trivial allocation across generators). Shadow prices were all 0.0.

**Assessment: SILENT FAILURE.** With zero cost coefficients, the objective function is trivially zero for any feasible dispatch. The solver correctly finds a feasible solution, but there is no warning that all costs are zero and the dispatch is arbitrary. A user who forgot to set cost data would see a "converged" result with zero LMPs and no indication that the dispatch is meaningless.

**Error quality: Poor** -- no diagnostic, no validation of cost data.

## Error Test (c): Invalid bus type

**Setup:** Attempted to set `bus.type` to an invalid string (`"invalid"`) and an invalid integer (`99`).

**Behavior:** Both assignments were accepted without error. The bus object silently stored the invalid value. No validation occurs at assignment time, model construction time, or solve time.

**Additional test -- disconnected bus:** Created a 2-bus system with no connecting line (bus 2 has a load but no path to the slack bus). Power flow returned `converged: False` with `error: 0.0` and voltage magnitude of 0.0 on the isolated bus. No exception raised, no warning about island detection or unserved load.

**Additional test -- negative impedance:** Created a line with `r=-0.01, x=-0.1`. Power flow converged without error or warning.

**Assessment: SILENT ACCEPTANCE.** GridCal does not validate bus types, line parameters, or network connectivity at input time. Invalid data is stored silently and may produce incorrect results without any diagnostic.

**Error quality: Poor** -- no input validation, no diagnostics.

## Summary

| Error | Behavior | Diagnostic Quality |
|-------|----------|-------------------|
| (a) Line limit = 0 | Silent reinterpretation as unlimited | Poor -- no warning |
| (b) Zero cost curve | Converges with zero LMPs | Poor -- no validation |
| (c) Invalid bus type | Silently accepted | Poor -- no input validation |

## Overall Assessment

GridCal provides no input validation and no meaningful error messages for common modeling mistakes. All three deliberate errors were either silently accepted or silently reinterpreted. This is a significant accessibility concern: users will get "converged" results from incorrectly specified models with no indication that anything is wrong.

The tool never raises exceptions for invalid modeling data, never warns about suspicious parameter values, and never validates the consistency of input data before solving.
