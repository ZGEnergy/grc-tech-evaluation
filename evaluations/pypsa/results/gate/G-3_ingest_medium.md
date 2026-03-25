---
test_id: G-3
tool: pypsa
dimension: gate
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: d5cc0c0a
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.154
timestamp: 2026-03-24T12:00:00Z
---

# G-3: Ingest reference network — MEDIUM (ACTIVSg 10k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Import method:** matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches (9726 lines + 2980 transformers) / 2485 generators
- **Load time:** 0.154s
- **Data quality notes:**
  - No NaN/infinite values in bus voltages or generator limits
  - 2462 branches with zero s_nom (2459 lines + 3 transformers) — this is a source data characteristic, not an import error. PyPSA warns these "will probably lead to infeasibilities and should be replaced with a high value using the `overwrite_zero_s_nom` argument"
  - Slack bus identified (bus 40845)
  - Generator cost data NOT imported (same limitation as G-1)
- **Errors/warnings:** PyPSA warns about zero s_nom branches and `status` attribute naming conflict (cosmetic, non-blocking)

## Test Script

`evaluations/pypsa/tests/test_gate.py` — class `TestGateG3` (4 subtests: bus count, branch count, generator count, data quality)
