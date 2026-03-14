---
test_id: G-2
tool: pandapower
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-14T02:50:33Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "326e8597"
---

# G-2: Ingest reference network (SMALL)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.124s
- **Element breakdown:**
  - Branches: line=2359, trafo=0, trafo3w=0, impedance=847
  - Generators: gen=484, ext_grid=1 (slack), sgen=59
- **Data quality notes:**
  - No NaN or infinite values in line ratings or generator limits
  - Generator cost data present: 544 polynomial cost rows (all generators have cost curves)
  - Slack/reference bus identified via ext_grid (1 ext_grid element)
  - Bus voltage columns (vm_pu, va_degree) not populated pre-solve (expected)
  - No line rating zeros or infinities
  - 847 branches converted to impedance elements (MATPOWER branches with tap ratio != 0/1 connecting same voltage levels)
  - 59 generators converted to sgen (static generator) elements
- **Errors/warnings:**
  - FutureWarning from pandas about incompatible dtype when setting trafo lookup (cosmetic, does not affect results)

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-2_SMALL]`
