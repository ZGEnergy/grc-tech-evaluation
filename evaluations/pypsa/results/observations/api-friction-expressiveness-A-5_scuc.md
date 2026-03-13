---
tag: api-friction
source_dimension: expressiveness
source_test: A-5
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: min_up_time / min_down_time must be integer dtype — silent float storage causes crash

## Finding

PyPSA 1.1.2's SCUC constraint builder crashes with `TypeError: pad_width must be of integral type` if `min_up_time` or `min_down_time` generator attributes are stored as floats. The generators DataFrame initializes these columns as int64, but assigning float values via `.at[name, col] = float_value` stores the float silently (with a FutureWarning) without raising an error until the solve.

## Context

Encountered during A-5 (SCUC) when assigning `min_down_time = 4.5` hours (from Modified Tiny gen_temporal_params.csv for gas_CC generators). The FutureWarning appeared at assignment time but the crash only occurred during `n.optimize()` inside `define_operational_constraints_for_committables()` → `su.rolling(snapshot=down_time_value).sum()` → xarray `rolling_window()` → `np.pad(pad_width=4.5, ...)`.

Fix: `n.generators["min_up_time"] = n.generators["min_up_time"].astype(int)` after all assignments.

## Implications

Accessibility dimension (D-x): Error message (`TypeError: pad_width must be of integral type` deep in numpy) is opaque — it does not mention `min_down_time` or that integer dtype is required. New users will struggle to diagnose this. The FutureWarning at assignment time is the only hint, but it appears several lines before the crash and in a different call context. PyPSA should validate these attributes are integers in its consistency checker. Worth noting in accessibility audit.
