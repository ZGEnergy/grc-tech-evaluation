---
tag: solver-issues
source_dimension: expressiveness
source_test: A-7
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: lpf_contingency() broken in PyPSA v1.1.2

## Finding

`n.lpf_contingency(branch_outages=...)` raises `'DataFrame' object has no attribute
'to_frame'` on the case39 network imported via the PPC pipeline. This prevents use
of the efficient built-in contingency analysis and forces a manual fallback.

## Context

During the A-7 N-M contingency sweep, `lpf_contingency()` was the intended method
for efficient N-1 analysis without model reconstruction. The method exists and is
documented, but fails at runtime. The same error was observed in A-9 when attempting
post-SCOPF verification. The fallback (modifying line reactance to 1e10 and re-running
`n.lpf()`) works but is significantly slower.

## Implications

This bug affects scalability assessments (Suite C) where contingency analysis at
scale depends on `lpf_contingency()` being functional. The manual fallback requires
O(n) full LPF solves instead of the efficient matrix factorization approach that
`lpf_contingency()` is designed to provide. This should be noted in the maturity
assessment as a regression or compatibility issue.
