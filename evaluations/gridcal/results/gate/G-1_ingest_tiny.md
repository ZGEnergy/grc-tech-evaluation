---
test_id: G-1
tool: gridcal
dimension: gate
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "0a74adbf"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.094
timestamp: 2026-03-24T19:05:18Z
---

# G-1: Ingest TINY Network (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches (35 lines + 11 transformers) / 10 generators
- **Load time:** 0.094s
- **Data quality notes:**
  - Bus Vnom: no NaN or infinite values (0/39)
  - Branch flow limits present: all 46 branches have positive rate values (no NaN, Inf, or zero)
  - Generator Pmax: no NaN or infinite values (0/10)
  - Generator cost data present: 10/10 generators have non-zero Cost or Cost2 fields
  - Slack/reference bus identified: bus '31' (code '31')
- **Errors/warnings:** None. VeraGridEngine natively reads MATPOWER .m files via `vge.open_file()` with no format conversion required.

## Test Script

**Path:** `evaluations/gridcal/tests/test_gate.py` (class `TestGateG1`)
