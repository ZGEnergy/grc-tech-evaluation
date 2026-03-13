---
tag: arch-quality
source_dimension: extensibility
source_test: B-8
tool: pypsa
severity: low
timestamp: 2026-03-11T00:00:00Z
---

# Observation: PyPSA DC OPF uses KVL formulation — LMPs are reference-bus-agnostic

## Finding

PyPSA's DC OPF optimizer uses a KVL (Kirchhoff Voltage Law) formulation that solves for branch flows via voltage angle differences. This formulation does not require a reference bus to anchor the angle vector for the LP solution. As a result, changing `n.buses["control"]` to designate a different slack bus has no effect on LMPs or dispatch in `n.optimize()`.

## Context

Discovered during B-8 (reference bus configuration). All three slack configurations (default bus 31, alternate bus 1, and distributed slack via extra_functionality) produced identical LMPs ($10–$763/MWh, spread $753/MWh) and identical objectives ($370,208/h).

## Implications

This is a positive architectural property for the Maturity dimension (E-series): PyPSA's formulation avoids the spurious LMP sensitivity to reference bus choice that exists in B-matrix OPF implementations. Practitioners migrating from MATPOWER (which uses a B-matrix / angle-injection formulation) may be confused by this difference and mistakenly interpret identical LMPs as a bug.

For the Accessibility dimension (D-4 error quality): the API accepts `n.buses["control"]` updates silently without warning that this has no effect on the LP optimizer. A developer expecting LMP changes when swapping the slack bus will see no change and no explanation. A warning or documentation note would improve usability.
