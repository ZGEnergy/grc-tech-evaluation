---
test_id: G-3
tool: pypsa
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: v9
skill_version: v1
test_hash: d1b0c952
wall_clock_seconds: 0.13
timing_source: measured
---

# G-3: Ingest MEDIUM Network (ACTIVSg 10k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** ~10000 buses (exact counts verified from .m file)
- **Actual counts:** 10000 buses / 12706 branches (9726 lines + 2980 transformers) / 2485 generators
- **Load time:** 0.13s
- **Data quality notes:**
  - Bus v_nom: no NaN or infinite values
  - Line flow limits: 2459 of 9726 lines have s_nom = 0 (unlimited flow assumed for those branches). PyPSA warns: "there are 2462 branches with s_nom equal to zero, they will probably lead to infeasibilities and should be replaced with a high value using the `overwrite_zero_s_nom` argument." This reflects the source data in ACTIVSg 10k, not a parsing error.
  - Transformer s_nom populated on all 2980 transformers
  - Generator p_nom populated on all 2485 generators
  - Generator cost data: 0/2485 generators have non-zero marginal cost — gencost not imported (same structural limitation as G-1/G-2)
  - Slack/reference bus identified: bus '40845' (control = Slack)
- **Errors/warnings:**
  - Same import warnings as G-1/G-2
  - `WARNING: there are 2462 branches with s_nom equal to zero` — data quality issue in source network (ACTIVSg 10k has many lines without explicit thermal ratings). Not a parser failure.

## Workarounds

Same two-step ingestion path as G-1/G-2: `matpowercaseframes.CaseFrames` → PYPOWER dict →
`pypsa.Network.import_from_pypower_ppc()`. No additional workarounds required for the
MEDIUM network.

The zero s_nom branches are a known characteristic of the ACTIVSg 10k dataset. For OPF
studies, the `overwrite_zero_s_nom` parameter should be used to assign a large finite value.

## Test Script

**Path:** `evaluations/pypsa/tests/gate/test_gate_eval.py`
