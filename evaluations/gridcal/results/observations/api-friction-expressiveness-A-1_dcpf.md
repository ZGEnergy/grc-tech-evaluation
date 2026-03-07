---
tag: api-friction
source_dimension: expressiveness
source_test: A-1
tool: gridcal
severity: low
timestamp: 2026-03-06T01:00:00Z
---

# Observation: DC power flow named "Linear" not "DC"

## Finding

GridCal names the DC power flow solver `SolverType.Linear` — the standard power systems term "DC" or "DCPF" does not appear in the enum name.

## Context

Discovered during A-1 (DCPF) test setup. The evaluator must know to use `SolverType.Linear` for DC power flow.

## Implications

Minor API friction for new users who search for "DC" in the API. Relevant to accessibility audit (D-2).
