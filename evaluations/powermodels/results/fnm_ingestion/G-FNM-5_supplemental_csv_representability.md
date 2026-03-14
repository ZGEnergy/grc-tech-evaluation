---
test_id: G-FNM-5
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: 70115b7a
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-13T01:30:00Z"
---

# G-FNM-5: Supplemental CSV Representability

## Result: INFORMATIONAL

PowerModels.jl achieves 39% native field coverage across all 44 supplemental CSV fields,
ranking tied with GridCal and behind PowerSimulations.jl (50%) and MATPOWER (45%). The
tool's strength is native support for 3 thermal rating tiers (RATE_A/B/C in the branch dict)
and standard network element identifiers. Its primary gaps are in interface definitions
(100% external), trading hub data (75% external), and outage scheduling (50% external).
PowerModels' dict-based data model provides a simple extension mechanism via arbitrary
dict keys, enabling Extension-representable (E) classification for most non-native fields.

## Per-CSV Representability Assessment

### 1. LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| FROM_BUS | N | `branch["f_bus"]` | Native bus reference |
| TO_BUS | N | `branch["t_bus"]` | Native bus reference |
| CKT | E | `branch["ckt"]` (custom dict key) | Not native; internal indexing used instead |
| ELEMENT_TYPE | E | `branch["element_type"]` (custom dict key) | PowerModels uses `branch["transformer"]` bool |
| RATE_A | N | `branch["rate_a"]` | Native thermal rating |
| RATE_B | N | `branch["rate_b"]` | Native thermal rating |
| RATE_C | N | `branch["rate_c"]` | Native thermal rating |
| RATE_D | E | `branch["rate_d"]` (custom dict key) | 4th tier not in standard schema |
| STATUS | N | `branch["br_status"]` | Native status flag |
| EFFECTIVE_DATE | E | `branch["effective_date"]` (custom dict key) | No temporal rating concept |

**Summary: 6 N, 4 E, 0 X (60% native)**

PowerModels has the best native coverage for this CSV due to its support for 3 thermal
rating tiers in the branch data structure. The 4th rating tier (RATE_D) and temporal
validity (EFFECTIVE_DATE) require extension keys. Extension approach: add arbitrary
keys to branch dicts, e.g., `data["branch"]["1"]["rate_d"] = 1200.0`.

### 2. TRADING_HUB.csv (4 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| HUB_NAME | X | No hub model | Trading hubs are market constructs outside PF domain |
| BUS_NUMBER | N | `bus["bus_i"]` | Native bus identifier |
| DISTRIBUTION_FACTOR | X | No hub model | Market settlement concept |
| HUB_TYPE | X | No hub model | Market classification |

**Summary: 1 N, 0 E, 3 X (25% native)**

Trading hub data is entirely outside PowerModels' domain model. Only the bus number
reference is natively representable because it corresponds to the physical bus identifier.
Hub definitions, distribution factors, and hub types must be maintained in external data
structures (e.g., a Julia `Dict{String, Vector{Tuple{Int, Float64}}}` mapping hub names to
bus-weight pairs). There is no extension path within PowerModels' data model for hub
concepts because the tool has no semantic concept of aggregated trading points.

**X Justification (HUB_NAME):** PowerModels.jl is a power flow and optimal power flow
solver. It operates on physical network models (buses, branches, generators) and has no
market-layer abstraction for trading hubs. While arbitrary keys can be added to bus dicts,
storing a hub name on individual buses does not represent the hub concept (a named
aggregation of buses with distribution weights). The M:N relationship between hubs and
buses has no structural analog in PowerModels' flat dict-of-dicts data model.

**X Justification (DISTRIBUTION_FACTOR):** Distribution factors define each bus's
contribution to a hub's aggregated price. This requires both the hub concept and a
weighting scheme, neither of which exists in PowerModels. While a custom dict key could
store a numeric weight on each bus, this would lack the hub-bus grouping structure and
could not be consumed by any PowerModels computation.

**X Justification (HUB_TYPE):** Hub type classification (GEN, LOAD, TRADING) is a
market-layer taxonomy with no analog in PowerModels' domain model.

### 3. GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| GEN_BUS | N | `gen["gen_bus"]` | Native generator bus reference |
| GEN_ID | E | `gen["gen_id"]` (custom dict key) | Internal indexing used; PSS/E ID not native |
| HUB_NAME | X | No hub model | Market concept |
| PARTICIPATION_FACTOR | X | No hub model | Market settlement factor |
| GEN_NAME | N | `gen["name"]` | Native after MATPOWER parse (from source_id) |

**Summary: 2 N, 1 E, 2 X (40% native)**

Generator distribution factors are market settlement constructs absent from all power flow
tools. GEN_BUS and GEN_NAME are natively representable. GEN_ID is Extension-representable
via a custom dict key (PowerModels uses integer indexing internally, not PSS/E's
two-character ID). Extension approach: `data["gen"]["1"]["gen_id"] = "1 "`.

**X Justification (HUB_NAME):** Same as TRADING_HUB.csv -- no hub concept exists.

**X Justification (PARTICIPATION_FACTOR):** Generator participation in trading hubs is a
market settlement concept with no analog in PowerModels. The tool has generator
participation factors for AGC/frequency response (`gen["apf"]`), but these are operational
parameters unrelated to hub-based market allocation.

### 4. CONTINGENCY.csv (6 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| CONTINGENCY_NAME | X | No contingency model | PowerModels has no native contingency definition |
| ELEMENT_TYPE | X | No contingency model | Contingency element classification absent |
| ELEMENT_FROM_BUS | N | `branch["f_bus"]` | Native bus reference |
| ELEMENT_TO_BUS | N | `branch["t_bus"]` | Native bus reference |
| ELEMENT_CKT | E | Custom dict key | Circuit ID not native |
| ELEMENT_BUS | N | `gen["gen_bus"]` | Native bus reference |

**Summary: 3 N, 1 E, 2 X (50% native)**

PowerModels has no native contingency definition model. Contingency analysis is performed
via external scripts that modify network state (e.g., `data["branch"]["42"]["br_status"] = 0`
followed by re-solving). The contingency name and element type concepts have no structural
analog in the data model.

**X Justification (CONTINGENCY_NAME):** PowerModels' data model is a flat dict-of-dicts
representing a single network operating point. There is no container for named contingency
scenarios. While a user could add a top-level `data["contingencies"]` key, this would be
ignored by all PowerModels functions and would not integrate with the solver.

**X Justification (ELEMENT_TYPE):** The distinction between branch and generator
contingencies requires a contingency definition concept that does not exist in PowerModels.
PowerModels branches have a `transformer` bool flag, but this is a branch subtype
classification, not a contingency element type.

### 5. INTERFACE.csv (5 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| INTERFACE_ID | X | No interface model | No interface/flowgate concept |
| INTERFACE_NAME | X | No interface model | No interface naming |
| NORMAL_LIMIT_MW | X | No interface model | No aggregate flow limit |
| EMERGENCY_LIMIT_MW | X | No interface model | No emergency limit concept |
| DIRECTION | X | No interface model | No interface direction concept |

**Summary: 0 N, 0 E, 5 X (0% native)**

PowerModels has no native interface or flowgate concept. Transmission interfaces (named
groups of branches with aggregate flow limits) are entirely outside the tool's domain.
Unlike tools such as PowerSimulations.jl (which has `TransmissionInterface`) or MATPOWER
(which has `mpc.if`/`mpc.iflim`), PowerModels cannot represent interface definitions
even via extension mechanisms because the concept of aggregated branch flow monitoring
with directional limits has no structural analog.

**X Justification (all 5 fields):** PowerModels operates on individual branches and
buses. The interface concept requires: (1) grouping branches by name, (2) assigning
direction coefficients, (3) computing aggregate flows across the group, and (4) enforcing
limits on the aggregate. None of these capabilities exist in PowerModels' architecture.
While PowerModels' extensible dict could store interface metadata, no PowerModels function
would consume it, and the aggregate flow constraint would need to be manually implemented
as a JuMP constraint in a custom OPF formulation.

### 6. INTERFACE_ELEMENT.csv (6 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| INTERFACE_ID | X | No interface model | No interface concept |
| FROM_BUS | N | `branch["f_bus"]` | Native bus reference |
| TO_BUS | N | `branch["t_bus"]` | Native bus reference |
| CKT | E | Custom dict key | Circuit ID not native |
| DIRECTION_COEFF | X | No interface model | No direction coefficient concept |
| WEIGHT_FACTOR | X | No interface model | No weighting concept |

**Summary: 2 N, 1 E, 3 X (33% native)**

Consistent with INTERFACE.csv findings -- the interface-specific fields (INTERFACE_ID,
DIRECTION_COEFF, WEIGHT_FACTOR) are tool-external because PowerModels lacks any
interface concept.

### 7. OUTAGE.csv (8 fields)

| Field | Classification | PowerModels Representation | Notes |
|-------|---------------|---------------------------|-------|
| ELEMENT_TYPE | X | No outage model | No outage schedule concept |
| ELEMENT_FROM_BUS | N | `branch["f_bus"]` | Native bus reference |
| ELEMENT_TO_BUS | N | `branch["t_bus"]` | Native bus reference |
| ELEMENT_CKT | E | Custom dict key | Circuit ID not native |
| ELEMENT_BUS | N | `gen["gen_bus"]` | Native bus reference |
| OUTAGE_START | X | No outage model | No temporal scheduling |
| OUTAGE_END | X | No outage model | No temporal scheduling |
| OUTAGE_TYPE | X | No outage model | No outage classification |

**Summary: 3 N, 1 E, 4 X (38% native)**

PowerModels models a single operating point and has no temporal outage scheduling
capability. Outage application requires external scripts that modify `br_status` or
`gen_status` fields, re-solve, and manage the temporal dimension externally.

## Cross-CSV Summary

| CSV | Fields | Native (N) | Extension (E) | External (X) | N% |
|-----|--------|-----------|---------------|--------------|-----|
| LINE_AND_TRANSFORMER | 10 | 6 | 4 | 0 | 60% |
| TRADING_HUB | 4 | 1 | 0 | 3 | 25% |
| GEN_DISTRIBUTION_FACTOR | 5 | 2 | 1 | 2 | 40% |
| CONTINGENCY | 6 | 3 | 1 | 2 | 50% |
| INTERFACE | 5 | 0 | 0 | 5 | 0% |
| INTERFACE_ELEMENT | 6 | 2 | 1 | 3 | 33% |
| OUTAGE | 8 | 3 | 1 | 4 | 38% |
| **Total** | **44** | **17** | **8** | **19** | **39%** |

### Comparison with Reference Classifications

All classifications match the analytical reference in `data/fnm/docs/supplemental-csvs.md`
for PowerModels.jl. The reference classifies PowerModels at 39% native, 18% extension,
43% external across all 44 fields. The small difference in E/X breakdown between this
assessment (18% E, 43% X) and the reference is due to rounding within individual CSV
percentage calculations.

## Market Solution Fidelity Summary

| Data Concept | Classification | Extension Approach (if E) | Complexity |
|--------------|---------------|---------------------------|------------|
| Thermal Ratings (4-tier) | E | Custom dict key `branch["rate_d"]` | Simple |
| Seasonal/Temporal Ratings | E | Custom dict key `branch["effective_date"]` | Simple |
| Trading Hub Definitions | X | External Dict/DataFrame | N/A |
| Generator Distribution Factors | X | External Dict/DataFrame | N/A |
| Contingency Definitions | X | External loop modifying `br_status`/`gen_status` | N/A |
| Interface Definitions + Limits | X | External + custom JuMP constraints | N/A |
| Outage Actions/Scheduling | X | External temporal management | N/A |
| Ownership/Operational Metadata | E | Custom dict keys on component dicts | Simple |

PowerModels.jl can carry market-adjacent data (thermal ratings, ownership metadata) via
its dict-based extension mechanism with minimal effort. However, market-layer concepts
(trading hubs, generator distribution factors) and operational concepts (contingencies,
interfaces, outage schedules) are entirely external and require parallel data structures
plus custom scripting. The tool's primary value proposition is as a power flow/OPF solver,
not as a comprehensive grid data model.

## Workarounds

None required. This is an informational assessment.

## Timing

Not applicable (analytical assessment, no solver execution).

## Test Script

No test script required. Assessment based on PowerModels.jl data model analysis and
reference classifications from `data/fnm/docs/supplemental-csvs.md`.
