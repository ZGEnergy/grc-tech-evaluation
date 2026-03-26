---
test_id: G-FNM-5
tool: gridcal
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: "0589716f"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
ingestion_path: matpower_raw
test_category: null
timestamp: 2026-03-24T00:00:00Z
---

# G-FNM-5: Supplemental CSV representability -- 7 CSVs, per-field N/E/X classification

## Result: INFORMATIONAL

Evidence-collection test. GridCal achieves 39% native, 23% extension, and 38%
external representability across all 44 fields in the 7 supplemental CSVs.
GridCal's standout strength is its native contingency model (`ContingencyGroup`,
`Contingency`), giving it the highest contingency coverage among Python tools
(83% native). Its principal gap is the absence of any interface/flowgate model
(100% external for INTERFACE.csv), trading hub model (75% external for
TRADING_HUB.csv), and outage schedule model (50% external for OUTAGE.csv).

## Approach

For each of the 7 supplemental CSVs documented in `data/fnm/docs/supplemental-csvs.md`,
each field was classified as:

- **N (native):** Field maps to a documented GridCal device property that participates
  in the tool's standard computations without custom code.
- **E (extension):** Field can be stored via GridCal's property system or custom fields
  on device objects. The data is preserved but not semantically interpreted by solvers.
- **X (tool-external):** No representation path within GridCal's data model. Data must
  be maintained in an external data structure.

Classifications were verified against the installed VeraGridEngine v5.6.28 API by
inspecting device class signatures (`Line`, `Transformer2W`, `Generator`, `Bus`,
`Contingency`, `ContingencyGroup`) and `MultiCircuit` attributes. The analytical
classifications from `supplemental-csv-representability.md` were confirmed empirically
where applicable.

### Extension mechanism

GridCal devices are Python objects with public properties. Custom metadata can be
attached via standard Python attribute assignment on device instances (e.g.,
`line.my_custom_field = value`). This is documented behavior -- the property system
does not reject unknown attributes. For structured extension, the VeraGrid/GridCal
`.veragrid` save format (SQLite-based) and `.ejson` format can persist custom
properties. However, custom attributes are not preserved through MATPOWER or PSS/e
round-trips.

## Per-CSV Representability Tables

### LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| FROM_BUS | N | `Line.bus_from` / `Transformer2W.bus_from` | Direct bus reference |
| TO_BUS | N | `Line.bus_to` / `Transformer2W.bus_to` | Direct bus reference |
| CKT | E | custom field | GridCal uses internal UUID indexing, not PSS/e CKT |
| ELEMENT_TYPE | E | custom field | Distinguishable by class type (`Line` vs `Transformer2W`) |
| RATE_A | N | `Line.rate` / `Transformer2W.rate` | Single native rating (MVA) |
| RATE_B | E | custom field | No native 2nd rating tier |
| RATE_C | E | custom field | No native 3rd rating tier |
| RATE_D | E | custom field | No native 4th rating tier |
| STATUS | N | `Line.active` / `Transformer2W.active` | Boolean in-service flag |
| EFFECTIVE_DATE | E | custom field | No native temporal validity |

**Summary:** 4 N (40%), 6 E (60%), 0 X (0%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly.

### TRADING_HUB.csv (4 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| HUB_NAME | X | no hub model | Trading hubs are a market-layer abstraction absent from GridCal |
| BUS_NUMBER | N | `Bus.code` (bus index) | Physical bus identifier |
| DISTRIBUTION_FACTOR | X | no hub model | Hub distribution weights have no analog |
| HUB_TYPE | X | no hub model | Hub type classification has no analog |

**Summary:** 1 N (25%), 0 E (0%), 3 X (75%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly. GridCal's
`MultiCircuit` has no hub, trading point, or market zone concept beyond `Area` and
`Zone` (which are topological, not market constructs).

### GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| GEN_BUS | N | `Generator.bus` | Bus reference via parent bus |
| GEN_ID | E | custom field | GridCal uses UUID `idtag`, not PSS/e machine ID |
| HUB_NAME | X | no hub model | Market concept, see TRADING_HUB |
| PARTICIPATION_FACTOR | X | no distribution factor | Not a power flow concept |
| GEN_NAME | N | `Generator.name` | Native name property |

**Summary:** 2 N (40%), 1 E (20%), 2 X (40%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly.

### CONTINGENCY.csv (6 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| CONTINGENCY_NAME | N | `ContingencyGroup.name` | Native named group container |
| ELEMENT_TYPE | N | `Contingency.device` type | Inferred from device class (Line, Generator, etc.) |
| ELEMENT_FROM_BUS | N | `Line.bus_from` / `Transformer2W.bus_from` | Via device reference |
| ELEMENT_TO_BUS | N | `Line.bus_to` / `Transformer2W.bus_to` | Via device reference |
| ELEMENT_CKT | E | custom field | CKT not native; device identified by `idtag` |
| ELEMENT_BUS | N | `Generator.bus` | Via generator's parent bus |

**Summary:** 5 N (83%), 1 E (17%), 0 X (0%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly. GridCal's
`ContingencyGroup` and `Contingency` classes provide first-class support for named
contingency definitions. A `Contingency` references a device directly (by object
reference), and `ContingencyGroup` groups multiple contingencies. The
`ContingencyOperationTypes` enum supports `active` (trip) and `%` (derate) operations.
The contingency analysis driver (`ContingencyAnalysisDriver`) natively consumes these
definitions.

### INTERFACE.csv (5 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| INTERFACE_ID | X | no interface model | No flowgate/interface concept in GridCal |
| INTERFACE_NAME | X | no interface model | — |
| NORMAL_LIMIT_MW | X | no interface model | — |
| EMERGENCY_LIMIT_MW | X | no interface model | — |
| DIRECTION | X | no interface model | — |

**Summary:** 0 N (0%), 0 E (0%), 5 X (100%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly. The
`MultiCircuit` class was inspected for any attribute containing "interface" or
"flowgate" -- none found. GridCal has no concept of a named group of branches
with aggregate flow limits. Interface flow monitoring would require entirely
external data structures and post-processing code.

### INTERFACE_ELEMENT.csv (6 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| INTERFACE_ID | X | no interface model | See INTERFACE.csv |
| FROM_BUS | N | `Line.bus_from` | Bus reference (as identifier only) |
| TO_BUS | N | `Line.bus_to` | Bus reference (as identifier only) |
| CKT | E | custom field | Not native; PSS/e circuit ID |
| DIRECTION_COEFF | X | no interface model | Interface flow direction has no analog |
| WEIGHT_FACTOR | X | no interface model | Interface element weighting has no analog |

**Summary:** 2 N (33%), 1 E (17%), 3 X (50%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly.

### OUTAGE.csv (8 fields)

| Field | Classification | GridCal Attribute | Notes |
|-------|---------------|-------------------|-------|
| ELEMENT_TYPE | X | no outage model | No temporal outage schedule concept |
| ELEMENT_FROM_BUS | N | `Line.bus_from` | Bus identifier only |
| ELEMENT_TO_BUS | N | `Line.bus_to` | Bus identifier only |
| ELEMENT_CKT | E | custom field | PSS/e circuit ID not native |
| ELEMENT_BUS | N | `Generator.bus` | Bus identifier only |
| OUTAGE_START | X | no outage model | No temporal validity on device status |
| OUTAGE_END | X | no outage model | No temporal validity on device status |
| OUTAGE_TYPE | X | no outage model | No outage classification (planned/forced/derate) |

**Summary:** 3 N (38%), 1 E (12%), 4 X (50%)

**Verification vs analytical:** Matches `supplemental-csvs.md` exactly. GridCal
has `active` flags on devices and time-series profiles, but no scheduled outage
data model with start/end dates and outage types.

## Cross-CSV Summary

| CSV | Fields | N | E | X | N% | E% | X% |
|-----|--------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER.csv | 10 | 4 | 6 | 0 | 40% | 60% | 0% |
| TRADING_HUB.csv | 4 | 1 | 0 | 3 | 25% | 0% | 75% |
| GEN_DISTRIBUTION_FACTOR.csv | 5 | 2 | 1 | 2 | 40% | 20% | 40% |
| CONTINGENCY.csv | 6 | 5 | 1 | 0 | 83% | 17% | 0% |
| INTERFACE.csv | 5 | 0 | 0 | 5 | 0% | 0% | 100% |
| INTERFACE_ELEMENT.csv | 6 | 2 | 1 | 3 | 33% | 17% | 50% |
| OUTAGE.csv | 8 | 3 | 1 | 4 | 38% | 12% | 50% |
| **Totals** | **44** | **17** | **10** | **17** | **39%** | **23%** | **38%** |

## Market Solution Fidelity Summary

| Data Concept | Source CSV(s) | GridCal | Mechanism |
|--------------|---------------|---------|-----------|
| Thermal Ratings (4-tier) | LINE_AND_TRANSFORMER.csv | `extension` | 1 native rating (`rate`); 3 additional tiers via custom fields |
| Seasonal / Temporal Ratings | LINE_AND_TRANSFORMER.csv | `extension` | No native temporal validity; custom fields or time profiles |
| Trading Hub Definitions | TRADING_HUB.csv | `external` | No hub concept; external DataFrame required |
| Generator Distribution Factors | GEN_DISTRIBUTION_FACTOR.csv | `external` | No distribution factor concept; external mapping required |
| Contingency Definitions | CONTINGENCY.csv | `native` | `ContingencyGroup` + `Contingency` classes; `ContingencyAnalysisDriver` consumes natively |
| Interface Definitions and Flow Limits | INTERFACE.csv + INTERFACE_ELEMENT.csv | `external` | No interface/flowgate model; external data + post-processing required |
| Outage Actions / Schedules | OUTAGE.csv | `external` | No temporal outage schedule; `active` flag is point-in-time only |
| Ownership and Operational Metadata | LINE_AND_TRANSFORMER.csv | `extension` | CKT, ELEMENT_TYPE, EFFECTIVE_DATE via custom fields |

### Key Findings

1. **Contingency definitions are GridCal's strongest supplemental coverage area.**
   GridCal is one of only two tools (alongside PowerSimulations.jl) with native
   contingency group and contingency element objects. The `Contingency` class
   directly references device objects and supports trip (`active`) and derate
   (`%`) operations via `ContingencyOperationTypes`. This gives GridCal 83%
   native coverage on CONTINGENCY.csv, the highest among all tools.

2. **Interface definitions are GridCal's largest gap.** INTERFACE.csv is 100%
   external with no extension path. Unlike MATPOWER (`mpc.if`/`mpc.iflim`) or
   PowerSimulations.jl (`TransmissionInterface`), GridCal has no concept of
   named branch groups with aggregate flow limits. This gap is consequential for
   Phase 2 congestion analysis readiness: flowgate monitoring and SCOPF with
   interface constraints would require entirely external implementation.

3. **Market-layer concepts are universally external.** Trading hubs, generator
   distribution factors, and outage schedules fall outside GridCal's domain model,
   consistent with the tool's focus on physical network analysis rather than
   market settlement. This is shared across all evaluated tools except
   PowerSimulations.jl (which partially covers interfaces).

4. **Single thermal rating is a limitation.** GridCal's `Line.rate` and
   `Transformer2W.rate` provide only one thermal rating tier. RATE_B, RATE_C,
   and RATE_D require extension storage. MATPOWER and PowerModels.jl natively
   support 3 tiers (RATE_A/B/C), giving them 60% native coverage on
   LINE_AND_TRANSFORMER.csv versus GridCal's 40%.

5. **Extension mechanism is lightweight but unstructured.** GridCal's extension
   path (custom attributes on device objects) is simple to use but offers no
   schema enforcement, type validation, or persistence guarantee across format
   conversions. Custom attributes survive in `.veragrid` native format but are
   lost in MATPOWER or PSS/e export.

## Comparison with Analytical Classifications

All 44 per-field classifications match the analytical reference in
`data/fnm/docs/supplemental-csvs.md` exactly. No reclassifications were
required.

## Test Script

No test script required -- this is an analytical/documentation test.
Classifications were derived from API inspection of VeraGridEngine v5.6.28
device classes and verified against the analytical reference document.
