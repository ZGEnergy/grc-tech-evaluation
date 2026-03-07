---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-9
tool: pandapower
severity: high
timestamp: 2026-03-06T00:00:00Z
---

# Observation: pandapower has no SCOPF; PYPOWER userfcn path is not viable

## Finding

pandapower has no native SCOPF. The PYPOWER `userfcn` callback system theoretically supports adding custom linear constraints to the OPF, but pandapower does not expose this interface through `rundcopp()`. Using PYPOWER's `opf()` directly bypasses pandapower entirely.

## Context

Test A-9 attempted to solve DC OPF with N-1 contingency constraints embedded in the optimization. The PTDF and LODF matrices were successfully computed (46x39 and 46x46 respectively), and `add_userfcn` was importable. However, `rundcopp()` has no parameter to pass userfcn callbacks or custom constraints. The only path would require manually constructing the PYPOWER ppc structure, calling PYPOWER's opf directly, and mapping results back -- effectively abandoning pandapower's API. pandapower does offer post-hoc contingency screening via `run_contingency`, but this is not optimization-embedded.

## Implications

For extensibility evaluation (B-1 custom constraints), the PYPOWER userfcn mechanism is accessible but fragile and undocumented in pandapower's context. Building blocks (PTDF, LODF) are available. For scalability evaluation, the inability to do SCOPF natively limits the tool's applicability to security-constrained market simulations.
