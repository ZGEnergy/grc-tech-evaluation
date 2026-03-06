---
test_id: G-2
tool: pypsa
network: SMALL
status: pass
timestamp: 2026-03-05T00:00:00Z
---

# G-2: Ingest SMALL (ACTIVSg 2000)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Import method:** matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches (2359 lines + 847 transformers) / 544 generators
- **Load time:** 0.093s
- **Data quality notes:**
  - Bus v_nom: no NaN or Inf values
  - Generator limits (p_nom, p_min_pu, p_max_pu): no NaN values
  - Branch flow limits (s_nom): all non-zero for lines and transformers
  - Slack bus: identified (1 Slack generator, 543 PV generators)
  - Generator cost data: gencost present in source file (544x7 matrix) but PyPSA's pypower importer ignores it -- marginal_cost all zero
- **Errors/warnings:**
  - PyPSA warning: "when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"

## Test Script

See `evaluations/pypsa/tests/test_gate.py` (TestGate::test_ingest parametrized with G-2).
