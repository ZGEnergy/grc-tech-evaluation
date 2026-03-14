---
test_id: B-9
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: d8e7210b
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.17
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 218
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-9: Compute the PTDF matrix for TINY (39-bus) and verify against DCPF

## Result: PASS

## Approach

PTDF extraction and validation via PyPSA's native SubNetwork API:

1. **Load network**: `matpower_loader.load_pypsa()` for case39
2. **Run DCPF**: `n.lpf()` to get baseline flows
3. **Build topology**: `n.determine_network_topology()`
4. **Compute PTDF**: `sn_obj.calculate_PTDF()` (native PyPSA method)
5. **Extract matrix**: `sn_obj.PTDF` — dense numpy array (46 branches x 39 buses)
6. **Build injection vector**: Assembled `P_inj` in `sn.buses_o` order (slack-first, critical for correct results)
7. **Validate**: Compared `PTDF @ P_inj_pu` against actual DCPF flows

**Phase-shifter check**: IEEE 39-bus has no phase-shifting transformers (SHIFT=0 on all branches). No Pbusinj/Pfinj correction needed. The 1e-6 tolerance applies directly.

**Bus ordering**: PTDF columns follow `sn.buses_o` order (slack bus first, then pvpq buses), NOT `n.buses` alphabetical order. The injection vector must be assembled in this exact order for correct flow predictions. This is a documented but non-obvious API detail.

## Output

| Metric | Value |
|--------|-------|
| PTDF shape | (46, 39) |
| Slack bus | 31 |
| Phase shifters | 0 |
| Max |predicted - actual| | 1.91e-14 pu |
| Mean |predicted - actual| | 4.14e-15 pu |
| Branches within 1e-6 tolerance | 46 / 46 |
| PTDF sparsity | 39.2% (entries < 1e-10) |

**Sample branch flows (pu on 100 MVA base):**

| Branch | Actual | Predicted | Diff |
|--------|--------|-----------|------|
| Line:L0 | -1.78353726 | -1.78353726 | 2.22e-15 |
| Line:L1 | 0.80753726 | 0.80753726 | 4.77e-15 |
| Line:L2 | 3.33430081 | 3.33430081 | 4.88e-15 |
| Line:L3 | -2.61783807 | -2.61783807 | 6.22e-15 |
| Line:L4 | 0.54115372 | 0.54115372 | 3.11e-15 |

Worst branch: Line:L15 with diff = 1.91e-14 pu (still 8 orders of magnitude below tolerance).

Flow predictions match DCPF results to machine precision (1.91e-14 pu max error vs 1e-6 tolerance).

## Workarounds

None required. The PTDF extraction uses a clean 3-step native API:
1. `n.determine_network_topology()`
2. `sub_network.calculate_PTDF()`
3. Access `sub_network.PTDF` (numpy array)

The only non-obvious detail is the bus ordering (`sn.buses_o` rather than `n.buses.index`), which is documented in the PyPSA source code and consistent with the SubNetwork's internal bus ordering convention.

## Timing

- **Wall-clock:** 1.17s
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b9_ptdf_extraction.py`
