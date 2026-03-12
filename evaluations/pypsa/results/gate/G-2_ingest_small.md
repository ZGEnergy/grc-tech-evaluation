---
test_id: G-2
tool: pypsa
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: v9
skill_version: v1
test_hash: fdeb3359
wall_clock_seconds: 0.07
timing_source: measured
---

# G-2: Ingest SMALL Network (ACTIVSg 2k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** ~2000 buses (exact counts verified from .m file)
- **Actual counts:** 2000 buses / 3206 branches (2359 lines + 847 transformers) / 544 generators
- **Load time:** 0.07s
- **Data quality notes:**
  - Bus v_nom: no NaN or infinite values
  - Line flow limits present (s_nom populated on all 2359 lines)
  - Transformer s_nom populated on all 847 transformers
  - Generator p_nom populated on all 544 generators
  - Generator cost data: 0/544 generators have non-zero marginal cost — gencost not imported (same limitation as G-1: `import_from_pypower_ppc` does not support gencost)
  - Slack/reference bus identified: bus '7098' (control = Slack)
- **Errors/warnings:**
  - Same import warnings as G-1 (areas/gencosts/component status not supported; cosmetic 'status' attribute warning)

## Workarounds

Same two-step ingestion path as G-1: `matpowercaseframes.CaseFrames` → PYPOWER dict →
`pypsa.Network.import_from_pypower_ppc()`. No additional workarounds required for the
SMALL network.

## Test Script

**Path:** `evaluations/pypsa/tests/gate/test_gate_eval.py`
