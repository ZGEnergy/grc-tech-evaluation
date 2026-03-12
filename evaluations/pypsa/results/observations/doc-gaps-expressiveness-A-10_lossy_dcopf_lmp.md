---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-10
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: transmission_losses parameter deprecated without clear migration path in docs

## Finding

`n.optimize(transmission_losses=3)` works but emits a FutureWarning: `"Passing an int for transmission_losses is deprecated and will be removed in PyPSA 2.0. Explicitly pass {'mode': 'tangents', 'segments': 3}"`. The deprecation message is clear, but the API docs do not yet show the new dict syntax prominently. The new syntax `transmission_losses={'mode': 'tangents', 'segments': 3}` also doesn't document the alternative `secant` mode or its tradeoffs vs tangent linearization.

## Context

Test A-10 (lossy DCOPF) requires loss-inclusive DC OPF. The `transmission_losses` parameter is the primary API for this. The parameter is documented in the `n.optimize()` docstring but the deprecation path and mode options are not in the user guide. To discover the `secant` mode and its loss accuracy implications, you must read the optimization source code (`optimize.py`).

## Implications

Accessibility evaluators should flag this as a documentation gap: loss modeling configuration is not self-documenting from the API surface. Users upgrading to v2.0 will need to update all uses of `transmission_losses=int` to the dict form.
