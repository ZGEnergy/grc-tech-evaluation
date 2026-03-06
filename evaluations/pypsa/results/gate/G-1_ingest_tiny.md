---
test_id: G-1
tool: pypsa
network: TINY
status: pass
timestamp: 2026-03-05T00:00:00Z
---

# G-1: Ingest TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Import method:** matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches (35 lines + 11 transformers) / 10 generators
- **Load time:** 1.186s (includes first-import overhead)
- **Data quality notes:**
  - Bus v_nom: no NaN or Inf values
  - Generator limits (p_nom, p_min_pu, p_max_pu): no NaN values
  - Branch flow limits (s_nom): all non-zero for lines and transformers
  - Slack bus: identified (1 Slack generator, 9 PV generators)
  - Generator cost data: gencost present in source file (10x7 matrix) but PyPSA's pypower importer ignores it -- marginal_cost all zero
- **Errors/warnings:**
  - PyPSA warning: "when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"

## Test Script

See `evaluations/pypsa/tests/test_gate.py` (TestGate::test_ingest parametrized with G-1).
