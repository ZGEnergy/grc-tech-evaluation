---
test_id: G-3
tool: pypsa
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: 2026-03-07T00:15:39Z
protocol_version: v4
---

# G-3: MEDIUM Network Ingestion (ACTIVSg 10000-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Conversion method:** matpowercaseframes parses .m into DataFrames; assembled into PYPOWER PPC dict (version, baseMVA, bus, gen, branch, gencost arrays); imported via `pypsa.Network.import_from_pypower_ppc(ppc)`. Note: PyPSA warns that gencosts are not supported during PPC import.
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches (9726 lines + 2980 transformers) / 2485 generators
- **Load time:** 0.436s
- **Data quality notes:**
  - No NaN or infinite values in bus v_nom or generator limits
  - 2459 lines (of 9726) have s_nom = 0 and 3 transformers (of 2980) have s_nom = 0. This originates from the source .m file (2462 branches with RATE_A = 0), not from conversion loss. These represent unconstrained branches in the MATPOWER data.
  - Generator marginal_cost is zero for all 2485 generators (gencost not imported by PyPSA -- same limitation as G-1/G-2)
  - Slack bus correctly identified
- **Errors/warnings:** PyPSA emits warning: "when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"

## Test Script

`evaluations/pypsa/tests/test_gate.py::TestGate::test_gate_ingestion[G-3_MEDIUM_ACTIVSg10k]`
