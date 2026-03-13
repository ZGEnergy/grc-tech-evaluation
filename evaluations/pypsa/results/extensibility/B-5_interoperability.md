---
test_id: B-5
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 876ee72f
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.100
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 135
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-5: Interoperability — DataFrame export

## Result: PASS

## Approach

After running `n.lpf()`, the result attribute `n.buses_t.v_ang` is already a pandas DataFrame — no conversion or extraction required. Export to CSV requires a single `.to_csv()` call.

Lines of code beyond the solve:
1. `v_ang_df = n.buses_t.v_ang` — access the result
2. `v_ang_df.to_csv(output_path)` — write to CSV

Total: **2 lines** (pass condition: < 5).

## Output

| Metric | Value |
|--------|-------|
| DataFrame shape | (1, 39) — 1 snapshot × 39 buses |
| Column labels | Bus names ('1'..'39') |
| Index | Snapshot timestamp ('now') |
| CSV round-trip max error | 9.19e-17 (machine precision) |
| Lines beyond solve | 2 |

**Voltage angles (rad), first 5 buses:**

| Bus | v_ang (rad) |
|-----|-------------|
| 1 | -0.214752 |
| 2 | -0.141448 |
| 3 | -0.191796 |
| 4 | -0.203323 |
| 5 | -0.180579 |

**CSV file:** `evaluations/pypsa/results/extensibility/b5_v_ang_export.csv`

## Workarounds

None required. PyPSA result attributes are natively pandas DataFrames; CSV export is a single method call.

## Timing

- **Wall-clock:** 0.100 s (warm process; includes lpf solve and CSV write)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b5_interoperability_tiny.py`

Key API sequence:
```python
n.lpf()                              # solve
v_ang_df = n.buses_t.v_ang           # already a DataFrame — 1 line
v_ang_df.to_csv("results.csv")       # export — 1 line
# 2 total lines beyond solve
```
