---
test_id: G-3
tool: pandapower
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-14T02:50:33Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "d5cc0c0a"
---

# G-3: Ingest reference network (MEDIUM)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 0.331s
- **Element breakdown:**
  - Branches: line=9726, trafo=975, trafo3w=0, impedance=2005
  - Generators: gen=1727, ext_grid=1 (slack), sgen=757
- **Data quality notes:**
  - No NaN or infinite values in line ratings, transformer ratings, or generator limits
  - Generator cost data present: 2485 polynomial cost rows (all generators have cost curves)
  - Slack/reference bus identified via ext_grid (1 ext_grid element)
  - Bus voltage columns (vm_pu, va_degree) not populated pre-solve (expected)
  - No line rating zeros or infinities
  - 2005 branches converted to impedance elements (MATPOWER branches with tap ratio != 0/1 connecting same voltage levels)
  - 975 branches converted to transformer elements
  - 757 generators converted to sgen (static generator) elements
  - Converter warning: "11 branches considered as trafos due to ratio unequal 0 or 1 but connect same voltage levels" (these become impedance elements)
- **Errors/warnings:**
  - Converter warning about 11 branches with nonstandard tap ratios at same voltage level (handled correctly as impedance elements)

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-3_MEDIUM]`
