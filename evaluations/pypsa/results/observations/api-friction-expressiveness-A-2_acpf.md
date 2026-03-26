---
tag: api-friction
source_dimension: expressiveness
source_test: A-2
tool: pypsa
severity: medium
timestamp: 2026-03-24T12:01:00Z
---

# Observation: Shared loader transformer patch breaks ACPF convergence

## Finding

The shared MATPOWER loader's Patch 1 (setting transformer `b = 1/x` for DCPF
B-matrix correctness) causes PyPSA's ACPF to diverge catastrophically. The
transformer `b` field has different semantics in DC vs AC contexts: in DCPF it
is the series susceptance (B-matrix entry), but in ACPF it is the shunt
susceptance of the transformer pi-model.

## Context

During A-2 (ACPF on TINY), the initial attempt using `load_pypsa()` from the
shared loader produced NR divergence to 10^42 after 100 iterations. Removing
Patch 1 (using raw `import_from_pypower_ppc` without the `b = 1/x` override)
produced convergence in 4 iterations with residual 3.3e-9.

This means DCPF and ACPF require different loading paths in PyPSA, which is
a subtle API inconsistency. The `b` attribute on transformers is overloaded
with different physical meanings depending on which solver method is used.

## Implications

- The shared loader should document that Patch 1 is DCPF-specific and must not
  be applied before running `n.pf()`.
- This finding is relevant to Accessibility (documenting the dual meaning of
  the `b` field) and Maturity (the overloaded semantics are a design issue
  in PyPSA's data model).
- Any test that chains DCPF and ACPF on the same network object will need to
  manage the `b` field carefully.
