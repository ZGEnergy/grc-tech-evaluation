---
test_id: B-9
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 8f3fc0f5
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.186
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 204
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-9: PTDF Extraction and Flow Prediction

## Result: PASS

## Approach

Used PyPSA's native `calculate_PTDF()` API on a `SubNetwork` object. The PTDF matrix is exposed as a dense numpy array. Flow predictions using `PTDF @ P_inj` match DCPF flows to machine precision (< 2e-14 pu).

**API sequence:**
```python
n.determine_network_topology()
sn = n.sub_networks.at["0", "obj"]
sn.calculate_PTDF()
PTDF = sn.PTDF                      # numpy array: (46 branches × 39 buses)
```

**Key finding — bus ordering:** PTDF columns are in `sn.buses_o` order (slack bus first, then pvpq buses in pvpq order), NOT in `n.buses` alphabetical order. The injection vector must be assembled in `buses_o` order for `PTDF @ P_inj` to yield correct flows. This ordering is not documented in user-facing docs and must be inferred from source code inspection.

For IEEE 39-bus: slack bus = '31', `buses_o` = `['31', '30', '32', '33', '34', ...]`.

The `n.buses_t.p` result from `n.lpf()` contains net nodal injection (gen − load) in MW with correct sign convention. No phase-shift correction needed (case39 has SHIFT=0 on all branches).

## Output

| Metric | Value |
|--------|-------|
| PTDF shape | 46 × 39 (branches × buses) |
| PTDF dtype | float64 |
| PTDF value range | [−1.0, 1.0] |
| Slack bus | '31' (bus index 0 in buses_o) |
| Phase-shifting branches | 0 (no correction needed) |
| Max \|predicted − actual\| flow | 1.91e-14 pu |
| Mean \|predicted − actual\| flow | 4.14e-15 pu |
| Branches within 0.01 pu tolerance | 46 / 46 |

**Sample flow predictions (first 5 branches):**

| Branch | Actual (pu) | Predicted (pu) | Diff (pu) |
|--------|------------|---------------|----------|
| Line:L0 | −1.783537 | −1.783537 | 0.000000 |
| Line:L1 | 0.807537 | 0.807537 | 0.000000 |
| Line:L2 | 3.334301 | 3.334301 | 0.000000 |
| Line:L3 | −2.617838 | −2.617838 | 0.000000 |
| Line:L4 | 0.541154 | 0.541154 | 0.000000 |

**PTDF first row (Line L0 sensitivity):**
- Max absolute sensitivity: 0.546 (bus '31')
- Non-zero entries: 37 of 39 buses

## Workarounds

None required for PTDF extraction. The API is native and documented.

The bus ordering discovery (`buses_o` vs `n.buses`) is a necessary API subtlety, not a workaround — once known, the code is clean and uses only public API attributes.

## Timing

- **Wall-clock:** 0.186 s (warm process; includes network load, lpf, topology, PTDF)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b9_ptdf_extraction_tiny.py`

Key API sequence:
```python
n.lpf()
n.determine_network_topology()
sn = n.sub_networks.at["0", "obj"]
sn.calculate_PTDF()
PTDF = sn.PTDF                          # (46, 39) numpy array

# Critical: inject in buses_o order, not n.buses order
buses_o = list(sn.buses_o)             # ['31', '30', '32', ...]
P_inj_pu = [p_bus_mw[b] / 100.0 for b in buses_o]
predicted_flows_pu = PTDF @ P_inj_pu   # max error: 1.9e-14 pu
```
