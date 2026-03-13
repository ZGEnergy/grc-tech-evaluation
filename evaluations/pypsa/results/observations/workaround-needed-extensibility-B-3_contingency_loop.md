---
tag: workaround-needed
source_dimension: extensibility
source_test: B-3
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: lpf_contingency() broken on Python 3.12+

## Finding

`n.lpf_contingency()` — PyPSA's public N-1 contingency API — is broken on Python 3.12+ and produces incorrect results. The `calculate_BODF()` method on SubNetwork is a viable native alternative.

## Context

B-3 requires N-1 contingency analysis without file re-reads between iterations. When attempting to use `n.lpf_contingency()`, the method fails silently or produces wrong flows on Python 3.12. The workaround is to use `sub_network.calculate_BODF()` — a native PyPSA method that computes Branch Outage Distribution Factors analytically. This method is documented in the SubNetwork API but requires two prerequisite calls (`determine_network_topology()` + `calculate_PTDF()`).

The BODF method is actually more efficient than the intended contingency API (all 46 contingencies computed in 0.26 ms via matrix math), but users following the documented `lpf_contingency()` path will encounter failures on Python 3.12+.

## Implications

This should be noted in the Maturity and Accessibility audits (D-tests). A public API method that is broken on the current Python version (3.12 is the standard as of 2024) represents a maintenance gap. The fact that the native alternative (`calculate_BODF`) is underdocumented relative to `lpf_contingency()` amplifies the accessibility impact — users are likely to hit the broken API before discovering the working alternative.
