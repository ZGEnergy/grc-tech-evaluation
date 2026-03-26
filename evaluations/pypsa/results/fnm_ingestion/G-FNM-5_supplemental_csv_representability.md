---
test_id: G-FNM-5
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: d1538e6c
status: informational
workaround_class: null
blocked_by: null
ingestion_path: matpower
wall_clock_seconds: 0.086
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 492
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# G-FNM-5: Supplemental CSV Representability

## Result: INFORMATIONAL

Evidence-collection test. All 7 supplemental CSVs analyzed against PyPSA's data
model. PyPSA achieves 34% native (N), 23% extension-representable (E), and 43%
tool-external (X) across the 44-field standardized field set defined in the
analytical reference (supplemental-csv-representability.md). Extension mechanism
empirically verified: custom columns on PyPSA component DataFrames persist correctly.

## Approach

For each of 7 supplemental CSVs, classified every field as:

- **N (Native):** PyPSA has a documented native attribute that directly stores this data
- **E (Extension):** Data storable via PyPSA's documented extension mechanisms
  (custom DataFrame columns, `extra_functionality` callbacks, PTDF constraints)
- **X (External):** No representation path within PyPSA's data model

Per protocol: E classifications require a documented concrete extension approach.
E classifications without such documentation are downgraded to X.

The standardized 44-field set from `supplemental-csv-representability.md` is used
as the authoritative field inventory. The actual FNM supplemental CSVs contain
additional operational fields beyond this standardized set.

## Output

### Cross-CSV Summary (Standardized 44-Field Set)

| Metric | Value |
|--------|-------|
| CSVs analyzed | 7 |
| Total fields (standardized) | 44 |
| Native (N) | 15 (34%) |
| Extension (E) | 10 (23%) |
| External (X) | 19 (43%) |

### Per-CSV Representability (Standardized Fields)

| CSV | Fields | N | E | X | N% | E% | X% |
|-----|--------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER | 10 | 4 | 6 | 0 | 40% | 60% | 0% |
| TRADING_HUB | 4 | 1 | 2 | 1 | 25% | 50% | 25% |
| GEN_DISTRIBUTION_FACTOR | 5 | 2 | 1 | 2 | 40% | 20% | 40% |
| CONTINGENCY | 6 | 3 | 3 | 0 | 50% | 50% | 0% |
| INTERFACE | 5 | 0 | 5 | 0 | 0% | 100% | 0% |
| INTERFACE_ELEMENT | 6 | 2 | 1 | 3 | 33% | 17% | 50% |
| OUTAGE | 8 | 3 | 1 | 4 | 38% | 12% | 50% |

### Per-Field Classifications

#### LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| FROM_BUS | N | Line.bus0 / Transformer.bus0 |
| TO_BUS | N | Line.bus1 / Transformer.bus1 |
| CKT | E | Custom column: `n.lines['ckt'] = values`. PyPSA uses integer index, not PSS/E composite key. |
| ELEMENT_TYPE | E | Custom column: inferrable from component type (Line vs Transformer) but also storable as custom attribute. |
| RATE_A | N | Line.s_nom / Transformer.s_nom (MVA thermal rating) |
| RATE_B | E | Custom column: `n.lines['s_nom_rate_b'] = values`. Only 1 native rating tier. |
| RATE_C | E | Custom column: `n.lines['s_nom_rate_c'] = values`. |
| RATE_D | E | Custom column: `n.lines['s_nom_rate_d'] = values`. ISO-specific 4th tier. |
| STATUS | N | Line.active / Transformer.active (boolean in-service flag) |
| EFFECTIVE_DATE | E | Custom column: `n.lines['effective_date'] = values`. No native temporal rating model. |

#### TRADING_HUB.csv (4 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| HUB_NAME | E | Custom bus attribute: `n.buses['hub_name'] = values`. Post-OPF hub prices derivable via PTDF-weighted bus LMP averaging. |
| BUS_NUMBER | N | Bus index (native bus identifier) |
| DISTRIBUTION_FACTOR | E | Custom bus attribute: `n.buses['hub_alloc_factor'] = values`. Used in post-OPF aggregate hub price calculation. |
| HUB_TYPE | X | No hub type taxonomy in PyPSA. Hub types (GEN/LOAD/TRADING) are market-layer concepts with no power flow analog. |

#### GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| GEN_BUS | N | Generator.bus (native bus reference) |
| GEN_ID | E | Custom column: `n.generators['gen_id'] = values`. PSS/E machine ID. |
| HUB_NAME | X | No hub model. Market settlement concept with no generator-hub mapping analog. |
| PARTICIPATION_FACTOR | X | No generator distribution factor attribute. Market settlement construct. |
| GEN_NAME | N | Generator name (index in n.generators DataFrame) |

#### CONTINGENCY.csv (6 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| CONTINGENCY_NAME | E | Custom DataFrame `n.contingencies` via `extra_functionality` callback. N-1 constraints enforced via BODF matrix + `lp.add_constraints()`. Requires 50-100 lines of custom code. |
| ELEMENT_TYPE | E | Custom column on contingency DataFrame: BRANCH/GENERATOR enum. |
| ELEMENT_FROM_BUS | N | Line.bus0 (native bus reference for branch contingencies) |
| ELEMENT_TO_BUS | N | Line.bus1 (native bus reference for branch contingencies) |
| ELEMENT_CKT | E | Custom column on contingency DataFrame referencing circuit ID. |
| ELEMENT_BUS | N | Generator.bus (native bus reference for generator contingencies) |

#### INTERFACE.csv (5 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| INTERFACE_ID | E | Custom `n.interfaces` DataFrame. Interface definitions stored alongside network. |
| INTERFACE_NAME | E | Custom attribute on interface DataFrame. |
| NORMAL_LIMIT_MW | E | PTDF constraint via `extra_functionality` + `n.model.add_constraints()`. `sum(PTDF_row * Pinj) <= limit`. |
| EMERGENCY_LIMIT_MW | E | PTDF constraint, contingency-conditional via `extra_functionality`. |
| DIRECTION | E | Sign convention in PTDF weighting, storable as custom attribute. |

#### INTERFACE_ELEMENT.csv (6 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| INTERFACE_ID | X | No native interface model. Storing just the ID without the interface concept is semantically meaningless within PyPSA. |
| FROM_BUS | N | Line.bus0 (native bus reference) |
| TO_BUS | N | Line.bus1 (native bus reference) |
| CKT | E | Custom attribute for circuit identifier. |
| DIRECTION_COEFF | X | No interface model. Direction coefficient has no structural analog in PyPSA's data model. |
| WEIGHT_FACTOR | X | No interface model. Interface weighting factor has no structural analog. |

#### OUTAGE.csv (8 fields)

| Field | Tier | Approach / Justification |
|-------|------|--------------------------|
| ELEMENT_TYPE | X | No outage model. Outage management with temporal validity is outside PyPSA's domain. |
| ELEMENT_FROM_BUS | N | Line.bus0 (bus number as physical element identifier) |
| ELEMENT_TO_BUS | N | Line.bus1 (bus number as physical element identifier) |
| ELEMENT_CKT | E | Custom attribute for circuit identifier. |
| ELEMENT_BUS | N | Generator.bus (bus number for generator outages) |
| OUTAGE_START | X | No temporal outage scheduling model in PyPSA. |
| OUTAGE_END | X | No temporal outage scheduling model. |
| OUTAGE_TYPE | X | No outage type classification (PLANNED/FORCED/DERATE) model. |

### Market Solution Fidelity Summary

| Data Concept | Source CSV(s) | Concept Tier | Note |
|--------------|---------------|-------------|------|
| Thermal Ratings (4-tier) | LINE_AND_TRANSFORMER | extension | Only s_nom (RATE_A) native. RATE_B/C/D via custom columns. |
| Seasonal/Temporal Rating Variations | LINE_AND_TRANSFORMER | extension | EFFECTIVE_DATE as custom column. No native temporal rating model. |
| Trading Hub Definitions | TRADING_HUB | external | HUB_NAME and DISTRIBUTION_FACTOR storable as custom bus attrs (E), but HUB_TYPE is X. Conservative aggregation: concept is external. |
| Generator Distribution Factors | GEN_DISTRIBUTION_FACTOR | external | Market settlement construct with no power flow analog. |
| Contingency Definitions | CONTINGENCY | external | CONTINGENCY_NAME and ELEMENT_TYPE representable via `extra_functionality` + BODF (E, complex), but concept-level classification follows conservative lowest-tier rule from analytical reference. |
| Interface Definitions & Flow Limits | INTERFACE, INTERFACE_ELEMENT | external | INTERFACE.csv all E via PTDF constraints, but INTERFACE_ELEMENT has 3 X fields. Conservative aggregation: concept is external. |
| Outage Actions / Planned Outage Params | OUTAGE | external | No temporal outage schedule model. |
| Ownership and Operational Metadata | LINE_AND_TRANSFORMER | extension | CKT, ELEMENT_TYPE, STATUS, EFFECTIVE_DATE -- mix of N and E. |

### Key X (External) Fields

| CSV | Field | Justification |
|-----|-------|---------------|
| TRADING_HUB | HUB_TYPE | Hub type taxonomy (GEN/LOAD/TRADING) is a market-layer concept absent from all power flow tools. |
| GEN_DISTRIBUTION_FACTOR | HUB_NAME | No generator-hub mapping concept in power flow domain. |
| GEN_DISTRIBUTION_FACTOR | PARTICIPATION_FACTOR | Market settlement distribution factors have no power flow analog. |
| INTERFACE_ELEMENT | INTERFACE_ID | No interface model -- ID alone has no semantic meaning in PyPSA. |
| INTERFACE_ELEMENT | DIRECTION_COEFF | No interface flow direction concept. |
| INTERFACE_ELEMENT | WEIGHT_FACTOR | No interface weighting concept. |
| OUTAGE | ELEMENT_TYPE | No outage model. |
| OUTAGE | OUTAGE_START | No temporal outage schedule. |
| OUTAGE | OUTAGE_END | No temporal outage schedule. |
| OUTAGE | OUTAGE_TYPE | No outage type classification. |

### Extension Mechanism Verification

Empirically verified that PyPSA's custom column extension mechanism works:

```python
net.lines["custom_test_field"] = "test_value"
assert net.lines.loc["test_line", "custom_test_field"] == "test_value"  # True
```

Custom columns on component DataFrames (Lines, Transformers, Generators, Buses)
persist and are accessible for post-processing. This is the foundation for all
E-classified fields.

### Comparison with Analytical Reference

The per-CSV percentages in the standardized 44-field set match the analytical
reference document (`supplemental-csv-representability.md`) exactly:

| CSV | Analytical (N/E/X%) | Empirical (N/E/X%) | Match |
|-----|--------------------|--------------------|-------|
| LINE_AND_TRANSFORMER | 40/60/0 | 40/60/0 | Yes |
| TRADING_HUB | 25/50/25 | 25/50/25 | Yes |
| GEN_DISTRIBUTION_FACTOR | 40/20/40 | 40/20/40 | Yes |
| CONTINGENCY | 50/50/0 | 50/50/0 | Yes |
| INTERFACE | 0/100/0 | 0/100/0 | Yes |
| INTERFACE_ELEMENT | 33/17/50 | 33/17/50 | Yes |
| OUTAGE | 38/12/50 | 38/12/50 | Yes |

Note: The TRADING_HUB percentages reflect the v10 reclassification of HUB_NAME
(X->E) and DISTRIBUTION_FACTOR (X->E) documented in the analytical reference.

## Workarounds

None required. This is an evidence-collection test.

## Timing

- **Wall-clock:** 0.086s
- **Timing source:** measured
- **Peak memory:** not measured (analytical test, no power flow)

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_5_supplemental_csv_representability.py`
