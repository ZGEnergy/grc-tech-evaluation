---
tag: workaround-needed
source_dimension: extensibility
source_test: B-3
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: lpf_contingency() crashes in v1.1.2

## Finding

PyPSA's `n.lpf_contingency()` method, designed for N-1 contingency analysis, crashes
with `AttributeError: 'DataFrame' object has no attribute 'to_frame'` in v1.1.2. This
appears to be a pandas API compatibility bug where the internal code assumes a Series
return but receives a DataFrame.

## Context

During B-3 (Contingency Loop), `n.lpf_contingency()` was tested first as the native API
for contingency analysis. It crashes immediately after running the base case LPF. The
workaround used `n.copy()` + manual branch disabling in a loop, which works correctly
but is slower and more verbose.

## Implications

This is a quality/maturity issue. The method exists and is documented, but is broken in
the current release. The maturity audit should note this as a regression or untested code
path. The workaround is stable (uses only documented public API), but the existence of a
broken convenience method suggests insufficient test coverage for this feature.
