---
test_id: B-9
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 8f3fc0f5
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 94.89
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 175
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-9: PTDF Extraction and Flow Prediction (MEDIUM)

## Result: PASS

## Approach

Same PTDF API as TINY (`calculate_PTDF()` → `sn.PTDF`), applied to ACTIVSg10k. ACTIVSg10k has 5 phase-shifting transformers and 970 off-nominal-tap transformers. The simple formula `PTDF @ P_inj` is inaccurate on this network (max error 7.4 pu). The full corrected formula using PyPSA's internal `p_bus_shift` and `p_branch_shift` correction vectors achieves machine-precision accuracy.

**Key discovery:** PyPSA's `SubNetwork` exposes two correction arrays (in MW):
- `sn.p_bus_shift` — bus injection correction term (8 nonzero entries)
- `sn.p_branch_shift` — branch flow offset term (5 nonzero entries)

These correspond to Pbusinj and Pfinj from the cross-tool-watchpoints.md formula. The correct prediction formula is:

```python
flow_pu = PTDF @ (P_inj_pu - p_bus_shift / BASE_MVA) + p_branch_shift / BASE_MVA
```

This correction is required for any network with phase-shifting transformers or off-nominal-tap transformers.

## Output

| Metric | Value |
|--------|-------|
| PTDF shape | 12706 × 10000 (branches × buses) |
| PTDF dtype | float64 |
| PTDF build time | 47.92 s |
| n_phase_shift_branches | 5 |
| n_off_nominal_tap_xfmrs | 970 |
| Simple formula max error | 7.43 pu (7,430 MW at 100 MVA base) |
| Simple formula within 0.01 pu | 9,699 / 12,706 |
| **Corrected formula max error** | **5.2e-11 pu (machine precision)** |
| **Corrected formula within 0.01 pu** | **12,706 / 12,706** |

**PTDF first row (Line:L0 sensitivity):**
- Max absolute sensitivity: 0.440
- Non-zero entries: 9,037 of 10,000 buses

**Sample flow predictions (corrected formula):**

| Branch | Actual (pu) | Predicted (pu) | Diff (pu) |
|--------|------------|----------------|-----------|
| Line:L0 | 0.167152 | 0.167152 | 0.000000 |
| Line:L1 | -0.070752 | -0.070752 | 0.000000 |
| Line:L2 | 0.326952 | 0.326952 | 0.000000 |
| Line:L3 | 0.028771 | 0.028771 | 0.000000 |
| Line:L4 | 0.194130 | 0.194130 | 0.000000 |

**Scaling comparison:**

| Network | Branches | Buses | PTDF shape | Build time |
|---------|----------|-------|------------|------------|
| TINY (39-bus) | 46 | 39 | 46×39 | < 0.001 s |
| MEDIUM (10k-bus) | 12,706 | 10,000 | 12706×10000 | 47.92 s |

PTDF build scales with O(n_buses × n_branches) dense matrix fill and requires solving a 10000×10000 sparse linear system.

## Workarounds

None required for PTDF extraction. The API is the same as TINY.

The phase-shift / tap-ratio correction is a necessary technical step (not a workaround) for accurate flow prediction on networks with off-nominal transformers. PyPSA exposes the required correction vectors as public attributes (`sn.p_bus_shift`, `sn.p_branch_shift`), though this is not documented in user-facing API docs.

## Timing

- **Wall-clock:** 94.89 s total
  - DCPF: 31.46 s
  - Network topology: < 0.1 s
  - PTDF build: 47.92 s
  - Flow prediction: < 0.01 s
- **Timing source:** measured
- **PTDF matrix memory:** ~1.0 GB (12706 × 10000 × 8 bytes)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b9_ptdf_extraction_medium.py`

Key API sequence (extended from TINY to include corrections):
```python
sn_obj.calculate_PTDF()
PTDF = sn_obj.PTDF          # (12706, 10000) numpy array

# Required for accurate predictions on networks with taps/phase shifts:
p_bus_shift = sn_obj.p_bus_shift      # correction in MW, buses_o order
p_branch_shift = sn_obj.p_branch_shift # correction in MW, branches_i order

flow_pu = PTDF @ (P_inj_pu - p_bus_shift / BASE_MVA) + p_branch_shift / BASE_MVA
# max error: 5.2e-11 pu (machine precision)
```
