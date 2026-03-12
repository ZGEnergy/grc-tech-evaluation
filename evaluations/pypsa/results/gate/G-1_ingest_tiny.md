---
test_id: G-1
tool: pypsa
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: v9
skill_version: v1
test_hash: 35843a04
wall_clock_seconds: 0.05
timing_source: measured
---

# G-1: Ingest TINY Network (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches (35 lines + 11 transformers) / 10 generators
- **Load time:** 0.05s
- **Data quality notes:**
  - Bus v_nom: no NaN or infinite values
  - Line flow limits present (s_nom populated on all 35 lines)
  - Transformer s_nom populated on all 11 transformers
  - Generator p_nom populated on all 10 generators
  - Generator cost data: 0/10 generators have non-zero marginal cost — gencost array not imported (PyPSA `import_from_pypower_ppc` does not support gencost; this is a known limitation documented in the import warning)
  - Slack/reference bus identified: bus '31' (control = Slack)
- **Errors/warnings:**
  - `WARNING: Note that when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status` — expected; gencost import is not supported by `import_from_pypower_ppc`
  - `WARNING: The attribute 'status' is a standard attribute for other components but not for lines/transformers` — cosmetic warning from PyPSA about the 'status' column name

## Workarounds

PyPSA 1.1.2 has no native MATPOWER .m file reader. The `.m` text file was parsed via
`matpowercaseframes.CaseFrames` to produce a PYPOWER-format dict (bus/branch/gen numpy
arrays), which was then loaded with `pypsa.Network.import_from_pypower_ppc()`. This is
the standard recommended path for MATPOWER ingestion into PyPSA and is well-documented.

Workaround class: format conversion (MATPOWER → PYPOWER dict → PyPSA). This is a
structural limitation, not a bug — the tool requires a two-step ingestion path for
MATPOWER files.

## Test Script

**Path:** `evaluations/pypsa/tests/gate/test_gate_eval.py`
