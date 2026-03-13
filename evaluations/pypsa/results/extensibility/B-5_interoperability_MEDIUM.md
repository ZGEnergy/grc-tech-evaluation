---
test_id: B-5
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 876ee72f
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 36.42
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 2
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-5: Interoperability — DataFrame export (MEDIUM)

## Result: PASS

## Approach

Loaded ACTIVSg10k and ran `n.lpf()` (DCPF). Accessed `n.buses_t.v_ang` (already a pandas DataFrame) and wrote to CSV via `.to_csv()`. Identical to TINY — 2 lines of code beyond the solve.

## Output

| Metric | Value |
|--------|-------|
| DataFrame shape | (1, 10000) — 1 snapshot × 10,000 buses |
| Non-zero angle entries | 9,999 / 10,000 |
| Max \|voltage angle\| (rad) | 1.831 |
| CSV round-trip max error | 1.11e-16 (machine precision) |
| CSV write time | 0.015 s |
| Lines beyond solve | 2 |

**Sample voltage angles (first 5 buses):**

| Bus | v_ang (rad) |
|-----|-------------|
| 10001 | 0.8496 |
| 10002 | 0.8994 |
| 10003 | 0.9539 |
| 10004 | 0.9560 |
| 10005 | 0.9559 |

**Scaling comparison:**

| Network | Buses | DataFrame shape | DCPF time (s) | CSV write (s) |
|---------|-------|-----------------|---------------|----------------|
| TINY (39-bus) | 39 | (1, 39) | ~0.05 s | < 0.001 s |
| MEDIUM (10k-bus) | 10,000 | (1, 10,000) | 26.66 s | 0.015 s |

## Workarounds

None required. The DataFrame export API is identical across network sizes.

## Timing

- **Wall-clock:** 36.42 s (DCPF: 26.66 s, CSV write: 0.015 s, network load: ~1.6 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **CSV file:** `evaluations/pypsa/results/extensibility/b5_v_ang_export_medium.csv`

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b5_interoperability_medium.py`

Key API sequence (identical to TINY):
```python
n.lpf()                              # DCPF on 10k-bus
v_ang_df = n.buses_t.v_ang           # already a DataFrame (1, 10000)
v_ang_df.to_csv(output_path)         # 2 lines beyond solve
```
