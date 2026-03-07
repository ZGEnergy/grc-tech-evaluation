---
tag: api-friction
source_dimension: expressiveness
source_test: A-5
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Reserve constraint via extra_functionality requires undocumented dimension names

## Finding

Adding spinning reserve constraints via `extra_functionality` for committable generators requires knowledge of internal Linopy variable dimension names (`Generator-com` vs `Generator-ext`) that are not documented in the PyPSA API reference. The attempt failed with `ValueError: ('Generator-com',) are not coordinates with an index`.

## Context

During A-5 SCUC testing, a spinning reserve constraint was implemented via the `extra_functionality` callback using `n.model.add_constraints()`. The constraint needed to reference both the generator status variable (binary, from committable) and the dispatch variable. These use different Linopy dimension names (`Generator-com` for committable status, `Generator-ext` for dispatch), which are not documented and must be discovered by inspecting the model object or reading source code.

## Implications

This affects Accessibility assessment: the `extra_functionality` mechanism is powerful but requires understanding internal variable naming conventions. Users attempting to add custom constraints for UC problems (reserves, must-run, etc.) will encounter this friction. Documentation should be checked for coverage of Linopy model variable naming conventions.
