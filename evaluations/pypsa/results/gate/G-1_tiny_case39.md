---
test_id: G-1
tool: pypsa
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: 2026-03-07T00:15:39Z
protocol_version: v4
---

# G-1: TINY Network Ingestion (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Conversion method:** matpowercaseframes parses .m into DataFrames; assembled into PYPOWER PPC dict (version, baseMVA, bus, gen, branch, gencost arrays); imported via `pypsa.Network.import_from_pypower_ppc(ppc)`. Note: PyPSA warns that gencosts are not supported during PPC import.
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches (35 lines + 11 transformers) / 10 generators
- **Load time:** 0.059s
- **Data quality notes:**
  - No NaN or infinite values in bus v_nom, line s_nom, transformer s_nom, or generator limits (p_nom, p_min_pu, p_max_pu)
  - Generator marginal_cost is zero for all 10 generators. PyPSA's `import_from_pypower_ppc` explicitly does not import gencost data (logged warning: "gencosts not supported"). The source .m file does contain polynomial cost data (model=2, 3 coefficients per generator). This would need manual post-processing for OPF.
  - Branch flow limits (s_nom) are present and non-zero for all lines and transformers
  - Slack bus correctly identified
- **Errors/warnings:** PyPSA emits warning: "when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"

## Test Script

`evaluations/pypsa/tests/test_gate.py::TestGate::test_gate_ingestion[G-1_TINY_case39]`
