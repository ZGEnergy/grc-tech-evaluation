---
test_id: G-FNM-5
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "00e6353c"
status: informational
input_path: matpower
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# G-FNM-5: Supplemental CSV representability audit for 7 market-specific CSVs

## Result: INFORMATIONAL

## Approach

For each of the 7 supplemental CSVs, every field was classified as:
- **N (Native):** MATPOWER has a built-in column or struct field that directly
  stores this data (e.g., `mpc.branch` columns RATE_A/B/C).
- **E (Extension):** MATPOWER can carry this data via custom fields on the
  `mpc` struct (e.g., `mpc.contingency = [...]`) without forking the source.
- **X (External):** No representation path within MATPOWER's data model.
  Data must be maintained in an external data structure.

Classifications are derived from the per-field analysis in
`data/fnm/docs/supplemental-csvs.md` and verified against MATPOWER 8.1's
case format specification.

MATPOWER's extension mechanism: the `mpc` (MATPOWER case) struct accepts
arbitrary user-defined fields beyond the standard set (`bus`, `branch`,
`gen`, `gencost`, `baseMVA`). Custom fields like `mpc.contingency`,
`mpc.if`, `mpc.iflim` are documented and used by MATPOWER internally for
interface flow limits. Additional user fields are preserved through
`loadcase()` / `savecase()`.

## Output

### Per-CSV Field Classification

#### LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| FROM_BUS | N | `mpc.branch` col 1 (F_BUS) |
| TO_BUS | N | `mpc.branch` col 2 (T_BUS) |
| CKT | E | Custom `mpc` field (no native circuit ID column) |
| ELEMENT_TYPE | E | Custom `mpc` field |
| RATE_A | N | `mpc.branch` col 6 (RATE_A) |
| RATE_B | N | `mpc.branch` col 7 (RATE_B) |
| RATE_C | N | `mpc.branch` col 8 (RATE_C) |
| RATE_D | E | Custom `mpc` field (no native 4th rating tier) |
| STATUS | N | `mpc.branch` col 11 (BR_STATUS) |
| EFFECTIVE_DATE | E | Custom `mpc` field (no temporal validity) |

**Summary:** 6 N (60%), 4 E (40%), 0 X (0%)

#### TRADING_HUB.csv (4 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| HUB_NAME | X | No hub model in MATPOWER |
| BUS_NUMBER | N | `mpc.bus` col 1 (BUS_I) |
| DISTRIBUTION_FACTOR | X | No hub distribution factor concept |
| HUB_TYPE | X | No hub model in MATPOWER |

**Summary:** 1 N (25%), 0 E (0%), 3 X (75%)

#### GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| GEN_BUS | N | `mpc.gen` col 1 (GEN_BUS) |
| GEN_ID | E | Custom `mpc` field (generators identified by row index, not ID) |
| HUB_NAME | X | No hub model |
| PARTICIPATION_FACTOR | X | No distribution factor attribute |
| GEN_NAME | E | Custom `mpc` field (no native name column in gen matrix) |

**Summary:** 1 N (20%), 2 E (40%), 2 X (40%)

#### CONTINGENCY.csv (6 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| CONTINGENCY_NAME | X | No native contingency definition model |
| ELEMENT_TYPE | X | No contingency model |
| ELEMENT_FROM_BUS | N | `mpc.branch` col 1 (F_BUS) |
| ELEMENT_TO_BUS | N | `mpc.branch` col 2 (T_BUS) |
| ELEMENT_CKT | E | Custom `mpc` field |
| ELEMENT_BUS | N | `mpc.gen` col 1 (GEN_BUS) |

**Summary:** 3 N (50%), 1 E (17%), 2 X (33%)

#### INTERFACE.csv (5 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| INTERFACE_ID | N | `mpc.if` col 1 (interface ID) |
| INTERFACE_NAME | E | Custom `mpc` field (no native name column in `mpc.if`) |
| NORMAL_LIMIT_MW | N | `mpc.iflim` (interface flow limits) |
| EMERGENCY_LIMIT_MW | E | Custom `mpc` field (only one limit tier native) |
| DIRECTION | E | Custom `mpc` field |

**Summary:** 2 N (40%), 3 E (60%), 0 X (0%)

MATPOWER has native interface support via `mpc.if` (interface element
definitions) and `mpc.iflim` (interface flow limits), used in OPF to
enforce aggregate flow constraints on groups of branches.

#### INTERFACE_ELEMENT.csv (6 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| INTERFACE_ID | N | `mpc.if` col 1 |
| FROM_BUS | N | `mpc.branch` col 1 (F_BUS) |
| TO_BUS | N | `mpc.branch` col 2 (T_BUS) |
| CKT | E | Custom `mpc` field |
| DIRECTION_COEFF | N | `mpc.if` direction coefficient |
| WEIGHT_FACTOR | E | Custom `mpc` field |

**Summary:** 4 N (67%), 2 E (33%), 0 X (0%)

#### OUTAGE.csv (8 fields)

| Field | Classification | MATPOWER Representation |
|-------|---------------|------------------------|
| ELEMENT_TYPE | X | No outage schedule model |
| ELEMENT_FROM_BUS | N | `mpc.branch` col 1 (F_BUS) |
| ELEMENT_TO_BUS | N | `mpc.branch` col 2 (T_BUS) |
| ELEMENT_CKT | E | Custom `mpc` field |
| ELEMENT_BUS | N | `mpc.gen` col 1 (GEN_BUS) |
| OUTAGE_START | X | No temporal outage scheduling |
| OUTAGE_END | X | No temporal outage scheduling |
| OUTAGE_TYPE | X | No outage classification model |

**Summary:** 3 N (38%), 1 E (12%), 4 X (50%)

### Cross-CSV Summary

| CSV | Fields | N | E | X | N% | E% | X% |
|-----|--------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER | 10 | 6 | 4 | 0 | 60% | 40% | 0% |
| TRADING_HUB | 4 | 1 | 0 | 3 | 25% | 0% | 75% |
| GEN_DISTRIBUTION_FACTOR | 5 | 1 | 2 | 2 | 20% | 40% | 40% |
| CONTINGENCY | 6 | 3 | 1 | 2 | 50% | 17% | 33% |
| INTERFACE | 5 | 2 | 3 | 0 | 40% | 60% | 0% |
| INTERFACE_ELEMENT | 6 | 4 | 2 | 0 | 67% | 33% | 0% |
| OUTAGE | 8 | 3 | 1 | 4 | 38% | 12% | 50% |
| **Totals** | **44** | **20** | **13** | **11** | **45%** | **30%** | **25%** |

### Concept-Level Representability

| Data Concept | Source CSV(s) | MATPOWER Classification |
|--------------|---------------|------------------------|
| Thermal Ratings (4-tier) | LINE_AND_TRANSFORMER | extension (RATE_D not native) |
| Seasonal/Temporal Ratings | LINE_AND_TRANSFORMER | extension (EFFECTIVE_DATE not native) |
| Trading Hub Definitions | TRADING_HUB | external (no hub model) |
| Generator Distribution Factors | GEN_DISTRIBUTION_FACTOR | external (no dist factor) |
| Contingency Definitions | CONTINGENCY | external (no contingency object) |
| Interface Definitions + Limits | INTERFACE, INTERFACE_ELEMENT | extension (native `mpc.if`/`mpc.iflim`) |
| Outage Schedule | OUTAGE | external (no temporal outage model) |

### Market Solution Fidelity Summary

| Capability | MATPOWER Support | Mechanism | Complexity |
|------------|-----------------|-----------|------------|
| Multi-tier thermal ratings | Partial native | RATE_A/B/C native; RATE_D requires extension | Low |
| Interface flow limits | Native | `mpc.if` + `mpc.iflim` in OPF | Low |
| Contingency analysis | Scripted | External loop modifying `mpc.branch(:, BR_STATUS)` | Medium |
| Trading hub pricing | External | Post-solve: LMP weights from external DataFrame | Medium |
| Generator distribution factors | External | External mapping outside `mpc` struct | Low |
| Outage application | External | Script modifies `BR_STATUS`/`GEN_STATUS` per outage | Medium |
| Seasonal rating switching | External | Script swaps RATE_A values by date | Low |

## Key Findings

1. **MATPOWER ranks second overall** at 45% native field coverage (20 of 44
   fields), behind only PowerSimulations.jl (50%). This is driven by native
   support for 3 thermal rating tiers and interface definitions.

2. **Interface support is a differentiator.** MATPOWER's `mpc.if`/`mpc.iflim`
   structures provide native interface flow limit enforcement in OPF. Only
   PowerSimulations.jl also has native interface support (via
   `TransmissionInterface`). Four of six tools have zero native interface
   coverage.

3. **Market-layer concepts are universally external.** Trading hubs, generator
   distribution factors, and outage schedules have no native representation
   in MATPOWER (or any other evaluated tool). These require external data
   structures and custom post-processing.

4. **Contingency definitions lack native support.** MATPOWER has no
   contingency definition object. N-1/N-2 analysis requires external
   scripting to enumerate and apply contingencies by modifying branch/gen
   status. This is common across 4 of 6 tools (GridCal and
   PowerSimulations.jl are exceptions).

5. **Generator naming is extension-only.** MATPOWER's gen matrix uses
   numeric columns with no native name field. Generator names must be
   stored in a custom `mpc` field, unlike PyPSA/pandapower/GridCal which
   have native name attributes.

## Workarounds

None required. This is an evidence-collection test with no pass/fail gate.

## Test Script

No test script -- this is a data model mapping analysis based on MATPOWER 8.1
case format documentation and the supplemental CSV field definitions in
`data/fnm/docs/supplemental-csvs.md`.
