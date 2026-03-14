---
tag: api-friction
source_dimension: expressiveness
source_test: A-5
tool: gridcal
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Time profile API requires unix timestamps, not datetime objects

## Finding

GridCal's `MultiCircuit.set_time_profile()` accepts `IntVec` (numpy int64 array of unix
timestamps), not pandas DatetimeIndex or datetime objects. Users must manually convert
datetime to unix timestamps before passing to the grid.

## Context

During A-5 (SCUC), the initial attempt used `pd.date_range()` directly, which failed.
The working pattern requires:

```python
time_array = pd.date_range("2024-01-01", periods=24, freq="h")
unix_ts = (time_array.astype(np.int64) // 10**9).values.astype(np.int64)
grid.set_time_profile(unix_ts)
```

This is a minor friction point -- the conversion is straightforward but not intuitive.

## Implications

For accessibility assessment: The time profile API is lower-level than expected. Other tools
(PyPSA, pandapower) accept datetime objects directly. This pattern adds ~2 lines of
boilerplate but is well-defined and reliable.
