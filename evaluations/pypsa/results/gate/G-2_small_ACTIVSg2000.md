---
test_id: G-2
tool: pypsa
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: 2026-03-07T00:15:39Z
protocol_version: v4
---

# G-2: SMALL Network Ingestion (ACTIVSg 2000-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Conversion method:** matpowercaseframes parses .m into DataFrames; assembled into PYPOWER PPC dict (version, baseMVA, bus, gen, branch, gencost arrays); imported via `pypsa.Network.import_from_pypower_ppc(ppc)`. Note: PyPSA warns that gencosts are not supported during PPC import.
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches (2359 lines + 847 transformers) / 544 generators
- **Load time:** 0.138s
- **Data quality notes:**
  - No NaN or infinite values in bus v_nom, line s_nom, transformer s_nom, or generator limits
  - Generator marginal_cost is zero for all 544 generators (gencost not imported by PyPSA -- same limitation as G-1)
  - Branch flow limits (s_nom) are present and non-zero for all lines and transformers
  - Slack bus correctly identified
- **Errors/warnings:** PyPSA emits warning: "when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"

## Test Script

`evaluations/pypsa/tests/test_gate.py::TestGate::test_gate_ingestion[G-2_SMALL_ACTIVSg2000]`
