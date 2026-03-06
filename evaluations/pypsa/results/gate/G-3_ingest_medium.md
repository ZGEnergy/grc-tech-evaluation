---
test_id: G-3
tool: pypsa
network: MEDIUM
status: pass
timestamp: 2026-03-05T00:00:00Z
---

# G-3: Ingest MEDIUM (ACTIVSg 10000)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Import method:** matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches (9726 lines + 2980 transformers) / 2485 generators
- **Load time:** 0.341s
- **Data quality notes:**
  - Bus v_nom: no NaN or Inf values
  - Generator limits (p_nom, p_min_pu, p_max_pu): no NaN values
  - Branch flow limits (s_nom): 2459/9726 lines and 3/2980 transformers have s_nom=0 (PyPSA warns these will cause OPF infeasibilities; use `overwrite_zero_s_nom` argument to fix)
  - Slack bus: identified (1 Slack generator, 2484 PV generators)
  - Generator cost data: gencost present in source file (2485x7 matrix) but PyPSA's pypower importer ignores it -- marginal_cost all zero
- **Errors/warnings:**
  - PyPSA warning: "when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"
  - PyPSA warning: "there are 2462 branches with s_nom equal to zero, they will probably lead to infeasibilities and should be replaced with a high value using the `overwrite_zero_s_nom` argument"

## Test Script

See `evaluations/pypsa/tests/test_gate.py` (TestGate::test_ingest parametrized with G-3).
