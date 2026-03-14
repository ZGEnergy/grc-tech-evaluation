---
test_id: G-FNM-5
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: d1538e6c
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.086
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 495
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# G-FNM-5: Supplemental CSV representability assessment on LARGE

## Result: INFORMATIONAL

Evidence-collection test. All 7 supplemental CSVs analyzed. PyPSA achieves 20.5%
native (N), 61.6% extension-representable (E), and 17.8% tool-external (X) across
73 total fields. Zero mismatches against analytical classifications (21/21 matched).

Extension mechanism empirically verified: custom columns on PyPSA component DataFrames
persist correctly.

## Approach

For each of 7 supplemental CSVs from the FNM Annual S01 variant, assessed each field's
representability tier in PyPSA's data model:

- **N (Native):** PyPSA has a documented native attribute directly storing this data
- **E (Extension):** Data storable via PyPSA's documented extension mechanisms
  (custom DataFrame columns, extra_functionality callbacks, PTDF constraints)
- **X (External):** No representation path within PyPSA's data model

Per protocol: E classifications require a documented concrete extension approach.
E classifications without such documentation are downgraded to X. All E classifications
in this assessment include specific extension approaches.

v10 reclassifications applied per protocol notes:
- CONTINGENCY.csv: CONTINGENCY_NAME, ELEMENT_TYPE reclassified X->E (extra_functionality + BODF)
- INTERFACE.csv: All 5 core fields reclassified X->E (PTDF + extra_functionality constraints)
- TRADING_HUB.csv: HUB_NAME, DISTRIBUTION_FACTOR reclassified X->E (custom bus attributes + PTDF-weighted LMP averaging)

## Output

### Cross-CSV Summary

| Metric | Value |
|--------|-------|
| CSVs analyzed | 7 |
| Total fields | 73 |
| Native (N) | 15 (20.5%) |
| Extension (E) | 45 (61.6%) |
| External (X) | 13 (17.8%) |
| Analytical cross-references | 21 |
| Matches | 21 (100%) |
| Mismatches | 0 |

### Per-CSV Representability

| CSV | Fields | N | E | X | N% | E% | X% |
|-----|--------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER | 19 | 6 | 13 | 0 | 31.6% | 68.4% | 0.0% |
| CONTINGENCY | 9 | 0 | 7 | 2 | 0.0% | 77.8% | 22.2% |
| INTERFACE | 17 | 2 | 14 | 1 | 11.8% | 82.4% | 5.9% |
| RESOURCE | 9 | 4 | 5 | 0 | 44.4% | 55.6% | 0.0% |
| TRADING_HUB | 4 | 0 | 3 | 1 | 0.0% | 75.0% | 25.0% |
| GEN_DISTRIBUTION_FACTOR | 4 | 1 | 2 | 1 | 25.0% | 50.0% | 25.0% |
| OUTAGE | 11 | 2 | 1 | 8 | 18.2% | 9.1% | 72.7% |

### Market Solution Fidelity Summary

| Data Concept | Concept Tier | Note |
|--------------|-------------|------|
| Thermal Ratings (4-tier) | extension | Only s_nom (RATE_A) native. RATE_B/C/D via custom columns. |
| Seasonal/Temporal Rating Variations | extension | EFFECTIVE_DATE as custom column. No native temporal rating model. |
| Trading Hub Definitions | extension | v10: Hub names and allocation factors as custom bus attrs. Post-OPF hub prices via PTDF-weighted LMP averaging. Complex. |
| Generator Distribution Factors | external | Market settlement concept with no power flow analog. |
| Contingency Definitions | extension | v10: extra_functionality + BODF matrix. 50-100 lines custom code. Complex. |
| Interface Definitions & Flow Limits | extension | v10: PTDF matrix + extra_functionality constraints. Complex. |
| Outage Actions / Planned Outage Params | external | No temporal outage schedule model. |

### Key X (External) Fields

| CSV | Field | Justification |
|-----|-------|---------------|
| TRADING_HUB | APNode | Abstract settlement point ID (string), not physical bus. No semantic mapping to PyPSA's bus model. |
| GEN_DISTRIBUTION_FACTOR | Distribution Factor | Market settlement construct. No generator distribution factor attribute in any power flow tool. |
| CONTINGENCY | Action | No contingency action model beyond simple trip. Derate actions require external logic. |
| CONTINGENCY | Outage | No contingency-outage link model. Outage scheduling outside PyPSA's domain. |
| INTERFACE | Outage | No interface-outage link. Conditional interfaces require external logic. |
| OUTAGE | (6 fields) | No temporal outage schedule model. All outage-specific fields (ID, Duration, Action, Device Type/Name, Limits) are external. |

### Extension Mechanism Verification

Empirically verified that PyPSA's custom column extension mechanism works:

```python
net.lines["custom_test_field"] = "test_value"
assert net.lines.loc["test_line", "custom_test_field"] == "test_value"  # True
```

Custom columns on component DataFrames (Lines, Transformers, Generators, Buses)
persist and are accessible for post-processing. This is the foundation for all
E-classified fields.

### Comparison with Analytical Classifications (supplemental-csv-representability.md)

All 21 fields that have analytical cross-reference classifications match the empirical
classifications exactly. No downgrades or upgrades were needed. The v10 reclassifications
(CONTINGENCY, INTERFACE, TRADING_HUB) align with the updated analytical document.

## Workarounds

None required. This is an evidence-collection test.

## Timing

- **Wall-clock:** 0.086s
- **Timing source:** measured
- **Peak memory:** not measured (analytical test, no power flow)

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_5_supplemental_csv_representability.py`
