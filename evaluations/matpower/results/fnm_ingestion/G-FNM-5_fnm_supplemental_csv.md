---
test_id: G-FNM-5
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: "00e6353c"
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
input_path: matpower
timestamp: "2026-03-24T18:00:00Z"
---

# G-FNM-5: Supplemental CSV representability audit

## Result: INFORMATIONAL

## Finding

MATPOWER achieves 45% native (N), 27% extension (E), and 28% external (X)
field coverage across the 7 supplemental CSVs (44 total classifiable
fields). This ranks second among all six evaluated tools, behind
PowerSimulations.jl (50% native). MATPOWER's native interface support
(`mpc.if`/`mpc.iflim`) is a significant differentiator shared only with
PowerSimulations.jl.

## Approach

For each of the 7 supplemental CSVs, every field was classified as Native
(N), Extension (E), or External (X) per the representability tier system
defined in `data/fnm/docs/supplemental-csvs.md`. Classifications are
based on MATPOWER 8.1's `mpc` struct format and documented extension
mechanisms. No code execution was required -- this is an analytical audit.

MATPOWER's extension mechanism is the ability to add arbitrary fields to
the `mpc` struct (e.g., `mpc.bus_name`, `mpc.gentype`, `mpc.genfuel`).
These custom fields are preserved by `loadcase()` and `savecase()` for
`.mat` files, and by `loadcase()` for `.m` files that define them.
Custom struct fields are not interpreted by MATPOWER's solvers but are
carried through the data pipeline.

## Per-CSV Per-Field Representability

### LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| FROM_BUS | N | `mpc.branch` col 1 (F_BUS) | Native bus index |
| TO_BUS | N | `mpc.branch` col 2 (T_BUS) | Native bus index |
| CKT | E | Custom `mpc` field | PSS/E circuit ID; no native analog |
| ELEMENT_TYPE | E | Custom `mpc` field | LINE vs TRANSFORMER distinction lost in unified branch matrix |
| RATE_A | N | `mpc.branch` col 6 (RATE_A) | Normal thermal rating |
| RATE_B | N | `mpc.branch` col 7 (RATE_B) | Short-term emergency rating |
| RATE_C | N | `mpc.branch` col 8 (RATE_C) | Emergency rating |
| RATE_D | E | Custom `mpc` field | 4th tier rating not in standard branch matrix |
| STATUS | N | `mpc.branch` col 11 (BR_STATUS) | In-service flag |
| EFFECTIVE_DATE | E | Custom `mpc` field | No temporal validity in MATPOWER |

**Summary:** 6 N, 4 E, 0 X (60% native)

### TRADING_HUB.csv (4 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| HUB_NAME | X | None | No hub model in MATPOWER |
| BUS_NUMBER | N | `mpc.bus` col 1 (BUS_I) | Physical bus identifier |
| DISTRIBUTION_FACTOR | X | None | No hub distribution factor concept |
| HUB_TYPE | X | None | No hub classification |

**Summary:** 1 N, 0 E, 3 X (25% native)

### GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| GEN_BUS | N | `mpc.gen` col 1 (GEN_BUS) | Generator bus number |
| GEN_ID | E | Custom `mpc` field | Machine ID not in standard gen matrix |
| HUB_NAME | X | None | No hub model |
| PARTICIPATION_FACTOR | X | None | No distribution factor attribute |
| GEN_NAME | E | Custom `mpc` field (or `mpc.gentype`) | No native name column in gen matrix |

**Summary:** 1 N, 2 E, 2 X (20% native)

### CONTINGENCY.csv (6 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| CONTINGENCY_NAME | X | None | No contingency definition model |
| ELEMENT_TYPE | X | None | No contingency element type |
| ELEMENT_FROM_BUS | N | `mpc.branch` col 1 (F_BUS) | Bus identifier for branch contingencies |
| ELEMENT_TO_BUS | N | `mpc.branch` col 2 (T_BUS) | Bus identifier for branch contingencies |
| ELEMENT_CKT | E | Custom `mpc` field | Circuit identifier |
| ELEMENT_BUS | N | `mpc.gen` col 1 (GEN_BUS) | Bus identifier for generator contingencies |

**Summary:** 3 N, 1 E, 2 X (50% native)

### INTERFACE.csv (5 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| INTERFACE_ID | N | `mpc.if` col 1 | Native interface ID via `toggle_iflims` |
| INTERFACE_NAME | E | Custom `mpc` field | No native name attribute for interfaces |
| NORMAL_LIMIT_MW | N | `mpc.iflim` | Interface flow limits enforced in OPF |
| EMERGENCY_LIMIT_MW | E | Custom `mpc` field | Only one limit tier natively supported |
| DIRECTION | E | Custom `mpc` field | Direction embedded in `mpc.if` element signs |

**Summary:** 2 N, 2 E, 1 X (40% native)

MATPOWER supports interface definitions via `mpc.if` (interface element
membership with direction coefficients) and `mpc.iflim` (interface flow
limits). Interface constraints are enforced in OPF via `toggle_iflims`.
This is a documented public API. The DIRECTION field is classified as E
rather than N because the sign convention is embedded in the element
direction coefficients rather than being a standalone attribute.

**Extension approach for INTERFACE_NAME:** Store as
`mpc.interface_names{interface_id} = 'Path_15'` in a custom cell array
field on the mpc struct.

**Extension approach for EMERGENCY_LIMIT_MW:** Store in a custom field
`mpc.iflim_emergency` paralleling the `mpc.iflim` structure.

### INTERFACE_ELEMENT.csv (6 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| INTERFACE_ID | N | `mpc.if` col 1 | Links element to parent interface |
| FROM_BUS | N | `mpc.branch` col 1 | Element from-bus |
| TO_BUS | N | `mpc.branch` col 2 | Element to-bus |
| CKT | E | Custom `mpc` field | Circuit identifier |
| DIRECTION_COEFF | N | `mpc.if` direction sign | +1/-1 for flow contribution |
| WEIGHT_FACTOR | E | Custom `mpc` field | Weighting not natively supported |

**Summary:** 4 N, 2 E, 0 X (67% native)

### OUTAGE.csv (8 fields)

| Field | Tier | MATPOWER Attribute | Notes |
|-------|------|-------------------|-------|
| ELEMENT_TYPE | X | None | No outage schedule model |
| ELEMENT_FROM_BUS | N | `mpc.branch` col 1 (F_BUS) | Bus identifier |
| ELEMENT_TO_BUS | N | `mpc.branch` col 2 (T_BUS) | Bus identifier |
| ELEMENT_CKT | E | Custom `mpc` field | Circuit identifier |
| ELEMENT_BUS | N | `mpc.gen` col 1 (GEN_BUS) | Bus identifier |
| OUTAGE_START | X | None | No temporal scheduling |
| OUTAGE_END | X | None | No temporal scheduling |
| OUTAGE_TYPE | X | None | No outage classification |

**Summary:** 3 N, 1 E, 4 X (38% native)

## Market Solution Fidelity Summary

### Aggregate Field Coverage

| Tier | Fields | Percentage |
|------|--------|------------|
| Native (N) | 20 / 44 | 45% |
| Extension (E) | 12 / 44 | 27% |
| External (X) | 12 / 44 | 28% |

### Concept-Level Representability

| Data Concept | Source CSV(s) | Tier | Notes |
|--------------|---------------|------|-------|
| Thermal Ratings (4-tier) | LINE_AND_TRANSFORMER | E | 3 tiers native (RATE_A/B/C), 4th tier via extension |
| Seasonal/Temporal Rating Variations | LINE_AND_TRANSFORMER | E | EFFECTIVE_DATE via custom field |
| Trading Hub Definitions | TRADING_HUB | X | No hub model; must use external DataFrame |
| Generator Distribution Factors | GEN_DISTRIBUTION_FACTOR | X | No participation factor concept |
| Contingency Definitions | CONTINGENCY | X | No native contingency object; must script BR_STATUS toggling |
| Interface Definitions and Flow Limits | INTERFACE, INTERFACE_ELEMENT | E | `mpc.if`/`mpc.iflim` provide native interface support but EMERGENCY_LIMIT_MW and WEIGHT_FACTOR require extension |
| Outage Actions / Planned Outage Parameters | OUTAGE | X | No temporal outage scheduling |
| Ownership and Operational Metadata | LINE_AND_TRANSFORMER | E | CKT, ELEMENT_TYPE, EFFECTIVE_DATE via custom fields |

### Key Strengths

1. **Native interface support:** MATPOWER's `mpc.if`/`mpc.iflim` with
   `toggle_iflims` provides first-class interface flow constraint
   enforcement in OPF. This is a significant differentiator -- only
   PowerSimulations.jl also has native interface support.

2. **Three-tier thermal ratings:** `mpc.branch` columns RATE_A, RATE_B,
   RATE_C provide native support for normal, short-term emergency, and
   emergency ratings. Most other tools support only one native rating tier.

3. **Flexible extension mechanism:** Arbitrary fields can be added to the
   `mpc` struct and persisted through `.mat` file save/load cycles. This
   provides a straightforward path for carrying supplemental data alongside
   the network model without external data structures.

### Key Gaps

1. **No contingency definitions:** MATPOWER has no native contingency
   object. N-1/N-2 analysis requires external scripting to enumerate
   contingencies and modify `BR_STATUS` for each scenario. Compare with
   GridCal (`ContingencyGroup`) and PowerSimulations.jl (`Contingency`).

2. **No generator name field:** The standard gen matrix is purely numeric.
   Generator names require the optional `mpc.gentype` or custom fields.

3. **No temporal concepts:** Effective dates, outage schedules, and
   seasonal rating changes have no representation path. MATPOWER models a
   single operating point.

4. **No market-layer data:** Trading hubs, generator distribution factors,
   and hub types are entirely outside MATPOWER's domain model.

## Implications

MATPOWER's 45% native coverage is competitive for a power flow tool
focused on single-operating-point analysis. The interface support is a
meaningful advantage for Phase 2 congestion analysis readiness. The gaps
in contingency definitions and market-layer data are consistent with
MATPOWER's design as a research-grade power system simulation tool rather
than a market operations platform.

For extensibility grading: the 27% extension-representable fields benefit
from MATPOWER's permissive struct extension mechanism, but the data is not
semantically interpreted by solvers. The 28% external fields represent
concepts fundamentally outside MATPOWER's domain (hubs, outage schedules).

## Test Script

No test script -- this is an analytical audit based on MATPOWER 8.1
documentation, the `mpc` case format specification, and the per-field
representability analysis in `data/fnm/docs/supplemental-csvs.md`.
