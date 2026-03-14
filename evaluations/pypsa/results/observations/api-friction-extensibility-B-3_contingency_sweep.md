---
tag: api-friction
source_dimension: extensibility
source_test: B-3
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: n.lpf_contingency() broken on Python 3.12+, but BODF alternative exists

## Finding

PyPSA's `n.lpf_contingency()` method, intended for N-1 contingency analysis, is broken on Python 3.12+ due to an internal compatibility issue. However, the `sub_network.calculate_BODF()` method provides an equivalent analytical N-1 capability, and the `n.copy()` + `n.lpf()` pattern supports arbitrary N-M contingency sweeps. The broken method is not blocking, but represents API friction for users following the documentation.

## Context

During B-3 (N-M contingency sweep), `n.lpf_contingency()` was not used because of the known Python 3.12 incompatibility (discovered in v9 testing). The test used `n.copy()` + branch modification + `n.lpf()` for the N-3 sweep, which works correctly but is slower than analytical approaches. For N-1 specifically, `sub_network.calculate_BODF()` provides the analytical alternative.

## Implications

For maturity assessment: a broken public API method (`lpf_contingency`) that has not been fixed across multiple releases (present in 1.1.2 on Python 3.12) indicates a maintenance gap. For accessibility: users following the documentation will hit this error and need to discover the BODF workaround on their own.
