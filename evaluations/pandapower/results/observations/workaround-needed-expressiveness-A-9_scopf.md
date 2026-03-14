---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-9
tool: pandapower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: pandapower OPF solver does not support custom constraint injection for SCOPF

## Finding

pandapower's PYPOWER-based OPF solver is a black box with no API for injecting user-defined constraints. This makes SCOPF (Security-Constrained OPF) impossible without bypassing pandapower's OPF entirely and building a custom optimization model from scratch.

## Context

During A-9 (SCOPF) evaluation, pandapower's contingency analysis (`run_contingency`) was confirmed to be post-hoc only — it checks N-1 violations after OPF, not during optimization. The PYPOWER interior-point solver's constraint set is hard-coded. The only path to SCOPF would be constructing a complete LP/MILP externally (using pandapower only for PTDF extraction), which constitutes a blocking workaround.

## Implications

This finding is relevant to the extensibility dimension (B-1 custom constraint injection). pandapower's inability to inject arbitrary linear constraints into its OPF solver limits not just SCOPF but any formulation that requires constraints beyond the built-in set (voltage limits, loading limits, P/Q generator limits). The PYPOWER solver's closed architecture is a significant extensibility limitation.
