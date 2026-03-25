---
test_id: G-2
tool: pypsa
dimension: gate
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: 326e8597
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.080
timestamp: 2026-03-24T12:00:00Z
---

# G-2: Ingest reference network — SMALL (ACTIVSg 2k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Import method:** matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches (2359 lines + 847 transformers) / 544 generators
- **Load time:** 0.080s
- **Data quality notes:**
  - No NaN/infinite values in bus voltages, line ratings, or generator limits
  - Branch flow limits present (s_nom populated, zero s_nom branches: 0)
  - Slack bus identified (bus 7098)
  - Generator cost data NOT imported (same limitation as G-1)
- **Errors/warnings:** PyPSA warns about `status` attribute naming conflict on lines and transformers (cosmetic, non-blocking)

## Test Script

`evaluations/pypsa/tests/test_gate.py` — class `TestGateG2` (4 subtests: bus count, branch count, generator count, data quality)
