---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-8
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: No native stochastic OPF — scenario loop is the only available approach

## Finding

PyPSA 1.1.2 has no native stochastic programming formulation. While `n.set_snapshots()` accepts a MultiIndex (verified), this creates a flat timeline of (scenario, period) tuples — it does not provide a scenario-weighted objective, non-anticipativity constraints, or two-stage decision structure. `pypsa.optimization` contains zero stochastic-specific methods.

## Context

Discovered during A-8 (Stochastic Multi-period DCOPF). Checked:
1. `n.set_snapshots(MultiIndex)` — accepts without error but is designed for multi-investment-period analysis, not stochastic programming
2. `dir(pypsa.optimization)` filtered for "stochast"/"scenario" — 0 matches
3. `n.optimize()` signature — no `scenario_weights`, `non_anticipativity`, or similar parameters

The only viable approach is a scenario loop: 3 independent LP solves. This produces scenario *analysis* (Monte Carlo DCOPF) not stochastic *optimization*.

## Implications

Expressiveness dimension: blocking gap for stochastic OPF use cases (energy markets with renewable uncertainty, robust scheduling). Any assessment of PyPSA for stochastic market clearing must account for this limitation. The extensibility dimension (B-x) should note that adding stochastic support via `extra_functionality` would require building a multi-scenario linopy model from scratch — significant custom code, not a clean extension pattern.
