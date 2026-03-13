---
tag: api-friction
source_dimension: expressiveness
source_test: A-7
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: n.lpf_contingency() broken in PyPSA v1.1.2 on Python 3.12+

## Finding

`n.lpf_contingency()` has a bug in PyPSA v1.1.2 on Python 3.12+: `isinstance(pd.Index, collections.abc.Sequence)` evaluates to False, causing the function to use the full `pd.Index` as the snapshot argument. `p0.loc[pd.Index]` then returns a DataFrame instead of a Series, which fails at `p0_base.to_frame("base")` (power_flow.py line 934) with `AttributeError: 'DataFrame' object has no attribute 'to_frame'`. The bug affects all calling conventions.

## Context

Test A-7 (contingency sweep) uses `n.lpf_contingency()` as the primary N-1 API. The function signature suggests it accepts `snapshots` parameter, but none of the valid calling patterns work:
- `n.lpf_contingency(n.snapshots, ...)` → pd.Index not a Sequence → fails
- `n.lpf_contingency(None, ...)` → same path → fails
- `n.lpf_contingency('now', ...)` → string IS a Sequence → `snapshot = 'n'` not in network → ValueError

Workaround: implement N-1 sweep directly using `sub_network.calculate_BODF()`, which is the correct and documented approach. The BODF-based N-1 sweep works correctly and is more efficient than the broken API.

## Implications

Scalability evaluators should be aware that `n.lpf_contingency()` is broken on the installed Python/pandas version. The BODF-based workaround is the correct path. This should be reported as a bug against PyPSA v1.1.2 + Python 3.12. The BODF approach (`sub_network.calculate_BODF()`) is itself a clean, documented public API.
