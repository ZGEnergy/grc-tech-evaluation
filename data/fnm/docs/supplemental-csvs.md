# Supplemental CSV Reference Documentation

**Version:** 1.0
**Audience:** evaluate-tool agents, human reviewers
**Scope:** 7 supplemental CSVs from the CAISO FNM Annual S01 variant
**Join key source:** Phase 1 D9 join-key mapping report
**Representability method:** Analytical classification with empirical spot-checks
**Tools evaluated:** PyPSA, pandapower, GridCal, PowerModels.jl, PowerSimulations.jl, MATPOWER

## Representability Classification System

This document classifies every field in the 7 supplemental CSVs according to a three-tier representability system that determines whether and how each tool can carry the data. The three tiers are:

**Natively-representable (N):** The tool has a documented native attribute that directly stores this data without any extension mechanism. Every N classification in this document cites the specific native attribute -- for example, MATPOWER `mpc.branch` column `RATE_A` for a thermal rating field. A field classified as N can be ingested into the tool's data model and participates in the tool's standard computations (power flow, OPF, contingency analysis) without custom code.

**Extension-representable (E):** The tool can carry this data via its documented extension mechanisms (custom attributes, metadata dictionaries, user-defined fields) without forking or patching the tool's source code. Every E classification cites the specific extension mechanism -- for example, PyPSA custom component attributes via DataFrame column assignment, or PowerSystems.jl `ext::Dict{String,Any}` on component types. Extension-representable data is preserved within the tool's data model but is not semantically interpreted by the tool's solvers or algorithms. It must be accessed and processed by custom user code.

**Tool-external (X):** No representation path exists within the tool's data model. The data must be maintained in an external data structure (DataFrame, dict, database) alongside the tool's network model. Every X classification states the reason -- either the data concept has no analog in the tool's domain model, or the tool lacks extension mechanisms that could accommodate it. In practice, all six evaluated tools have some extension mechanism, so X classifications typically arise when the data concept is entirely outside the tool's domain (e.g., trading hub definitions in a power flow solver).

The relationship between this field-level representability classification and the record-type support matrix in the Record-Type Mapping Guide (Phase 2 D2) is important: a record type with "Y" (native) support in D2 does not guarantee that all supplemental CSV fields associated with that record type are Natively-representable (N) at the field level. For example, a tool may natively represent branches (Y for Branch record type) but have no native attribute for a 4th thermal rating tier. Field-level classification is strictly more granular than record-type classification.

The proportion of X (tool-external) fields for a given CSV directly indicates the post-ingestion extension burden for an analyst using that tool. A tool with many X fields requires the analyst to maintain parallel data structures and manually associate them with network elements, increasing complexity and error risk. This informs the Extensibility dimension of the evaluation rubric.

## CSV Overview

| CSV File | Domain | Purpose | Columns | Join Target | Join Cardinality | Join Match Rate |
|----------|--------|---------|---------|-------------|-----------------|-----------------|
| `LINE_AND_TRANSFORMER.csv` | Transmission | Thermal ratings and operational parameters for lines and transformers | 10 | branch, transformer | N:1 | 97.2% |
| `CONTINGENCY.csv` | Transmission | Contingency definitions for N-1/N-2 reliability analysis | 6 | branch, generator | M:N | 94.8% |
| `INTERFACE.csv` | Transmission | Transmission interface definitions with flow limits | 5 | (via INTERFACE_ELEMENT) | 1:N | N/A |
| `INTERFACE_ELEMENT.csv` | Transmission | Branch elements comprising each interface with direction and weighting | 6 | branch | N:1 | 96.5% |
| `GEN_DISTRIBUTION_FACTOR.csv` | Generation | Generator participation/distribution factors for hub allocation | 5 | generator | N:1 | 98.1% |
| `TRADING_HUB.csv` | Market | Trading hub definitions mapping hubs to buses with distribution factors | 4 | bus | N:1 | 99.3% |
| `OUTAGE.csv` | Outage | Scheduled and forced outage definitions with dates and types | 8 | branch, generator | M:N | 95.6% |

## Extension Mechanisms by Tool

| Tool | Extension Mechanism | Mechanism Description | Citation |
|------|--------------------|-----------------------|----------|
| PyPSA | Custom component attributes | Additional columns on component DataFrames via `n.madd()` or direct DataFrame assignment | PyPSA docs: Custom Components |
| pandapower | `std_types` / user-defined columns | Custom columns on element DataFrames; `std_types` for equipment type libraries | pandapower docs: User-defined data |
| GridCal | Device properties / custom fields | GridCal devices support arbitrary property attachment via the property system | GridCal API: Device properties |
| PowerModels.jl | Dict extension keys | Network data dicts accept arbitrary keys beyond the standard set | PowerModels.jl docs: Network Data |
| PowerSimulations.jl | `ext` field on component types | PowerSystems.jl component types include an `ext::Dict{String,Any}` field for arbitrary metadata | PowerSystems.jl docs: Type hierarchy |
| MATPOWER | Custom `mpc` struct fields | MATPOWER case structs accept arbitrary fields beyond the standard set (bus, gen, branch, etc.) | MATPOWER docs: Case format |

## LINE_AND_TRANSFORMER.csv

**Domain:** Transmission
**Purpose:** Provides thermal ratings (up to 4 tiers: Rate A/B/C/D), emergency ratings, and operational parameters for transmission lines and transformers. These ratings define the MVA transfer limits used in security-constrained dispatch and congestion management. The 4-tier rating hierarchy supports normal, long-term emergency, short-term emergency, and extreme emergency operating conditions as defined by CAISO operating procedures.
**Row count:** ~15,000 rows
**Join key:** FROM_BUS + TO_BUS + CKT
**Join target:** branch, transformer
**Cardinality:** N:1 (multiple rating tiers per element)
**Match rate:** 97.2%

### Join Keys

The composite key FROM_BUS + TO_BUS + CKT identifies each transmission element by its terminal buses and circuit identifier, directly corresponding to the PSS/E branch record identifiers (I, J, CKT) in the intermediate format branch and transformer tables. The D9 validation found a 97.2% match rate against the branch table, with the unmatched 2.8% primarily comprising transformer records that join to the transformer table instead. When validated against both branch and transformer tables together, the effective match rate exceeds 99%.

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "LINE_AND_TRANSFORMER.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| FROM_BUS | integer | Source bus number of the transmission element, corresponding to PSS/E bus number I at the from-end of the branch or transformer. | 10523 | yes |
| TO_BUS | integer | Destination bus number of the transmission element, corresponding to PSS/E bus number J at the to-end of the branch or transformer. | 20847 | yes |
| CKT | string | Circuit identifier distinguishing parallel elements between the same bus pair. Matches the PSS/E CKT field. | 1 | yes |
| ELEMENT_TYPE | enum | Type of network element: LINE for transmission lines, TRANSFORMER for power transformers. Determines which intermediate format table the record joins to. | LINE | no |
| RATE_A | float | Normal (continuous) thermal rating in MVA. The maximum power transfer under normal operating conditions. Corresponds to PSS/E RATEA. | 785.0 | no |
| RATE_B | float | Long-term emergency thermal rating in MVA. Applicable during planned outage conditions or system restoration. Corresponds to PSS/E RATEB. | 890.0 | no |
| RATE_C | float | Short-term emergency thermal rating in MVA. Applicable during contingency conditions for limited duration. Corresponds to PSS/E RATEC. | 1050.0 | no |
| RATE_D | float | Extreme emergency thermal rating in MVA. A CAISO-specific 4th rating tier not present in PSS/E, used for extreme contingency analysis. | 1200.0 | no |
| STATUS | enum | Operational status of the element: IN_SERVICE or OUT_OF_SERVICE. Elements with OUT_OF_SERVICE status are excluded from thermal limit enforcement. | IN_SERVICE | no |
| EFFECTIVE_DATE | date | Date from which these ratings become effective, in ISO 8601 format. Supports seasonal rating changes. | 2024-06-01 | no |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| FROM_BUS | N (Line.bus0) | N (line.from_bus) | N (Line.bus_from) | N (branch["f_bus"]) | N (Arc.from) | N (mpc.branch col 1) |
| TO_BUS | N (Line.bus1) | N (line.to_bus) | N (Line.bus_to) | N (branch["t_bus"]) | N (Arc.to) | N (mpc.branch col 2) |
| CKT | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| ELEMENT_TYPE | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| RATE_A | N (Line.s_nom) | N (line.max_i_ka) | N (Line.rate) | N (branch["rate_a"]) | N (ThermalStandard.rating) | N (mpc.branch RATE_A) |
| RATE_B | E (custom attr) | E (custom column) | E (custom field) | N (branch["rate_b"]) | E (ext dict) | N (mpc.branch RATE_B) |
| RATE_C | E (custom attr) | E (custom column) | E (custom field) | N (branch["rate_c"]) | E (ext dict) | N (mpc.branch RATE_C) |
| RATE_D | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| STATUS | N (Line.active) | N (line.in_service) | N (Line.active) | N (branch["br_status"]) | N (available) | N (mpc.branch BR_STATUS) |
| EFFECTIVE_DATE | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 4 | 6 | 0 | 40% | 60% | 0% |
| pandapower | 4 | 6 | 0 | 40% | 60% | 0% |
| GridCal | 4 | 6 | 0 | 40% | 60% | 0% |
| PowerModels.jl | 6 | 4 | 0 | 60% | 40% | 0% |
| PowerSimulations.jl | 4 | 6 | 0 | 40% | 60% | 0% |
| MATPOWER | 6 | 4 | 0 | 60% | 40% | 0% |

### Key Findings

- RATE_D (4th thermal rating tier) is Extension-representable (E) across all 6 tools -- no tool has a native 4th rating tier. This is a CAISO-specific concept not present in PSS/E or IEEE standards.
- MATPOWER and PowerModels.jl have the best native coverage (60%) because they natively support 3 thermal rating tiers (RATE_A/B/C) in the branch data structure, while other tools support only 1 native rating.
- The CKT (circuit identifier) field is Extension-representable in all tools despite being a fundamental PSS/E identifier, because tools use internal element indexing rather than PSS/E's bus-pair-circuit composite key.
- EFFECTIVE_DATE is universally Extension-representable -- no power flow tool has native temporal validity concepts for ratings.

## TRADING_HUB.csv

**Domain:** Market
**Purpose:** Defines trading hub compositions by mapping hub names to sets of buses with associated distribution factors. Trading hubs are market constructs used by CAISO for energy market settlement and congestion pricing -- they aggregate physical buses into commercial trading points. No power flow tool has a native trading hub concept because hubs are a market-layer abstraction that sits above the physical network model.
**Row count:** ~500 rows
**Join key:** BUS_NUMBER
**Join target:** bus
**Cardinality:** N:1
**Match rate:** 99.3%

### Join Keys

The BUS_NUMBER column joins each hub-bus mapping record to the bus table via the PSS/E bus number (I). The D9 validation found a 99.3% match rate, with unmatched rows corresponding to retired or planned buses not present in the current network model snapshot.

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "TRADING_HUB.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| HUB_NAME | string | Name of the trading hub as defined in the CAISO market. Uses standardized naming conventions reflecting geographic regions and hub types. | SP15_GEN_HUB | no |
| BUS_NUMBER | integer | Bus number of a physical bus participating in this trading hub. Each bus may appear in multiple hubs. Corresponds to PSS/E bus number I. | 24510 | yes |
| DISTRIBUTION_FACTOR | float | Weight factor for this bus within the hub. Distribution factors within a hub sum to 1.0 and determine each bus's contribution to the hub's aggregated price or quantity. | 0.0234 | no |
| HUB_TYPE | enum | Classification of the hub: GEN for generation-weighted hubs, LOAD for load-weighted hubs, TRADING for pure trading points. | GEN | no |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| HUB_NAME | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) |
| BUS_NUMBER | N (Bus index) | N (bus index) | N (Bus index) | N (bus["bus_i"]) | N (ACBus.number) | N (mpc.bus BUS_I) |
| DISTRIBUTION_FACTOR | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) |
| HUB_TYPE | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 1 | 0 | 3 | 25% | 0% | 75% |
| pandapower | 1 | 0 | 3 | 25% | 0% | 75% |
| GridCal | 1 | 0 | 3 | 25% | 0% | 75% |
| PowerModels.jl | 1 | 0 | 3 | 25% | 0% | 75% |
| PowerSimulations.jl | 1 | 0 | 3 | 25% | 0% | 75% |
| MATPOWER | 1 | 0 | 3 | 25% | 0% | 75% |

### Key Findings

- Trading hub data is universally tool-external (X) across all 6 tools for 3 of 4 fields (HUB_NAME, DISTRIBUTION_FACTOR, HUB_TYPE). No tool has a native trading hub concept because hubs are a market-layer abstraction.
- Only BUS_NUMBER is natively representable because it corresponds to the physical bus identifier that all tools model.
- All tools have identical representability profiles (25% N, 75% X) because hub concepts are equally absent from all six tools' domain models.
- Trading hub data must be maintained in external data structures (DataFrames or dictionaries) alongside the network model in every tool.

## GEN_DISTRIBUTION_FACTOR.csv

**Domain:** Generation
**Purpose:** Maps generators to trading hubs with percentage participation factors that determine each generator's contribution to hub-level generation allocation. These distribution factors are used in market settlement to allocate generator output across trading hubs. The relationship is many-to-many: a generator may participate in multiple hubs, and a hub contains contributions from multiple generators.
**Row count:** ~2,000 rows
**Join key:** GEN_BUS + GEN_ID
**Join target:** generator
**Cardinality:** N:1
**Match rate:** 98.1%

### Join Keys

The composite key GEN_BUS + GEN_ID identifies each generator by its bus number and machine identifier, corresponding to the PSS/E generator record fields I and ID in the intermediate format generator table. The D9 validation found a 98.1% match rate, with unmatched rows corresponding to generators present in market systems but absent from the planning network model.

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "GEN_DISTRIBUTION_FACTOR.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| GEN_BUS | integer | Bus number where the generator is connected. Corresponds to PSS/E generator bus number I. | 31205 | yes |
| GEN_ID | string | Machine identifier distinguishing multiple generators at the same bus. Corresponds to PSS/E machine ID. | 1 | yes |
| HUB_NAME | string | Name of the trading hub this generator participates in. References the HUB_NAME in TRADING_HUB.csv. | NP15_GEN_HUB | no |
| PARTICIPATION_FACTOR | float | Fractional participation of this generator in the specified hub. Values between 0.0 and 1.0. A generator's participation factors across all hubs sum to 1.0. | 0.156 | no |
| GEN_NAME | string | Human-readable name of the generator unit for cross-referencing with other market systems. | DIABLO_CANYON_1 | no |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| GEN_BUS | N (Generator.bus) | N (gen.bus) | N (Generator.bus) | N (gen["gen_bus"]) | N (ThermalStandard.bus) | N (mpc.gen GEN_BUS) |
| GEN_ID | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| HUB_NAME | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) | X (no hub model) |
| PARTICIPATION_FACTOR | X (no dist factor attr) | X (no dist factor attr) | X (no dist factor attr) | X (no dist factor attr) | X (no dist factor attr) | X (no dist factor attr) |
| GEN_NAME | N (Generator.name) | N (gen.name) | N (Generator.name) | N (gen["name"]) | N (ThermalStandard.name) | E (custom mpc field) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 2 | 1 | 2 | 40% | 20% | 40% |
| pandapower | 2 | 1 | 2 | 40% | 20% | 40% |
| GridCal | 2 | 1 | 2 | 40% | 20% | 40% |
| PowerModels.jl | 2 | 1 | 2 | 40% | 20% | 40% |
| PowerSimulations.jl | 2 | 1 | 2 | 40% | 20% | 40% |
| MATPOWER | 1 | 2 | 2 | 20% | 40% | 40% |

### Key Findings

- HUB_NAME and PARTICIPATION_FACTOR are universally tool-external (X) across all 6 tools. No tool has native generator distribution factor attributes because these are market settlement constructs.
- GEN_NAME is natively representable in 5 of 6 tools but only Extension-representable in MATPOWER, which stores generators in a numeric matrix without a native name field.
- All tools have identical or near-identical representability profiles, reflecting that generator distribution factors are a market-layer concept absent from all power flow tools.
- The 40% X rate means nearly half the fields in this CSV must be maintained externally regardless of tool choice.

## CONTINGENCY.csv

**Domain:** Transmission
**Purpose:** Defines contingency scenarios specifying which network elements are tripped for N-1 and N-2 reliability analysis. Each row describes a single element outage within a named contingency case, with the contingency name grouping multiple element outages into a scenario. Contingencies are fundamental to security-constrained economic dispatch (SCED) and transmission planning studies.
**Row count:** ~5,000 rows
**Join key:** ELEMENT_FROM_BUS + ELEMENT_TO_BUS + ELEMENT_CKT (for branch contingencies), ELEMENT_BUS + ELEMENT_ID (for generator contingencies)
**Join target:** branch, generator
**Cardinality:** M:N
**Match rate:** 94.8%

### Join Keys

Branch contingencies use the composite key ELEMENT_FROM_BUS + ELEMENT_TO_BUS + ELEMENT_CKT, which joins to the branch table via I, J, CKT. Generator contingencies use ELEMENT_BUS + ELEMENT_ID, joining to the generator table via I, ID. The file contains mixed element types (both branch and generator contingencies), so the applicable join depends on the ELEMENT_TYPE field. The D9 validation found a 94.8% aggregate match rate; the lower rate compared to other CSVs reflects contingency definitions referencing planned or hypothetical elements not in the base case model. Secondary join to the transformer table was also validated for transformer contingencies.

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "CONTINGENCY.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| CONTINGENCY_NAME | string | Unique name identifying the contingency scenario. Multiple rows with the same name define a multi-element (N-2 or higher) contingency. | CTG_001_LINE_10001_20001 | no |
| ELEMENT_TYPE | enum | Type of element being tripped: BRANCH for transmission lines or transformers, GENERATOR for generating units. Determines which join key set and target table apply. | BRANCH | no |
| ELEMENT_FROM_BUS | integer | From-bus number of the contingency element (for branch/transformer contingencies). Null for generator contingencies. Corresponds to PSS/E bus number I. | 10001 | yes |
| ELEMENT_TO_BUS | integer | To-bus number of the contingency element (for branch/transformer contingencies). Null for generator contingencies. Corresponds to PSS/E bus number J. | 20001 | yes |
| ELEMENT_CKT | string | Circuit identifier of the contingency element (for branch/transformer contingencies). Null for generator contingencies. Corresponds to PSS/E CKT. | 1 | yes |
| ELEMENT_BUS | integer | Bus number of the contingency generator (for generator contingencies). Null for branch contingencies. Corresponds to PSS/E generator bus I. | 31205 | yes |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| CONTINGENCY_NAME | X (no contingency model) | X (no contingency model) | N (ContingencyGroup.name) | X (no contingency model) | N (Contingency.name) | X (no contingency model) |
| ELEMENT_TYPE | X (no contingency model) | X (no contingency model) | N (Contingency.device_type) | X (no contingency model) | N (Contingency element type) | X (no contingency model) |
| ELEMENT_FROM_BUS | N (Line.bus0) | N (line.from_bus) | N (Line.bus_from) | N (branch["f_bus"]) | N (Arc.from) | N (mpc.branch col 1) |
| ELEMENT_TO_BUS | N (Line.bus1) | N (line.to_bus) | N (Line.bus_to) | N (branch["t_bus"]) | N (Arc.to) | N (mpc.branch col 2) |
| ELEMENT_CKT | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| ELEMENT_BUS | N (Generator.bus) | N (gen.bus) | N (Generator.bus) | N (gen["gen_bus"]) | N (ThermalStandard.bus) | N (mpc.gen GEN_BUS) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 3 | 1 | 2 | 50% | 17% | 33% |
| pandapower | 3 | 1 | 2 | 50% | 17% | 33% |
| GridCal | 5 | 1 | 0 | 83% | 17% | 0% |
| PowerModels.jl | 3 | 1 | 2 | 50% | 17% | 33% |
| PowerSimulations.jl | 5 | 1 | 0 | 83% | 17% | 0% |
| MATPOWER | 3 | 1 | 2 | 50% | 17% | 33% |

### Key Findings

- GridCal and PowerSimulations.jl have the best contingency data coverage (83% N) because both have native contingency definition objects (`ContingencyGroup`/`Contingency` and `Contingency` type respectively).
- CONTINGENCY_NAME and ELEMENT_TYPE are tool-external (X) in PyPSA, pandapower, PowerModels.jl, and MATPOWER -- these tools have no native contingency definition model. Contingency analysis in these tools is typically handled by external scripts that modify network state.
- The network element identifier fields (FROM_BUS, TO_BUS, ELEMENT_BUS) are natively representable in all tools because they correspond to existing bus identifiers.
- ELEMENT_CKT is universally Extension-representable, consistent with the pattern seen in LINE_AND_TRANSFORMER.csv.

## INTERFACE.csv

**Domain:** Transmission
**Purpose:** Defines named transmission interfaces with normal and emergency flow limits. Interfaces are groupings of monitored transmission paths whose aggregate flow is constrained for reliability purposes. CAISO uses interfaces (also called paths or flowgates) to manage power transfers across critical transmission corridors. Interface definitions do not directly reference individual network elements -- the element composition is specified in INTERFACE_ELEMENT.csv.
**Row count:** ~100 rows
**Join key:** INTERFACE_ID
**Join target:** (indirect via INTERFACE_ELEMENT.csv)
**Cardinality:** 1:N
**Match rate:** N/A

### Join Keys

INTERFACE.csv does not join directly to any intermediate format network table. Instead, INTERFACE_ID serves as the linking key to INTERFACE_ELEMENT.csv, which in turn joins to the branch table via FROM_BUS + TO_BUS + CKT. The relationship is 1:N -- each interface contains multiple branch elements. D9 validated the INTERFACE_ID link between INTERFACE.csv and INTERFACE_ELEMENT.csv with 100% match rate (every interface has at least one element).

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "INTERFACE.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| INTERFACE_ID | integer | Unique numeric identifier for the interface. Referenced by INTERFACE_ELEMENT.csv to associate branch elements with this interface. | 15 | yes |
| INTERFACE_NAME | string | Human-readable name of the interface, typically referencing the transmission corridor or NERC path designation. Some names are publicly known (e.g., Path 15, Path 26). | Path_15 | no |
| NORMAL_LIMIT_MW | float | Normal (continuous) flow limit for the interface in MW. The maximum aggregate power transfer across all member elements under normal operating conditions. | 2500.0 | no |
| EMERGENCY_LIMIT_MW | float | Emergency flow limit for the interface in MW. The maximum aggregate power transfer permitted during contingency conditions for limited duration. | 3000.0 | no |
| DIRECTION | enum | Flow direction convention: FORWARD or REVERSE. Defines the positive flow direction for limit enforcement. | FORWARD | no |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| INTERFACE_ID | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | N (TransmissionInterface.name) | N (mpc.if col 1) |
| INTERFACE_NAME | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | N (TransmissionInterface.name) | E (custom mpc field) |
| NORMAL_LIMIT_MW | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | N (TransmissionInterface limits) | N (mpc.iflim) |
| EMERGENCY_LIMIT_MW | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | E (ext dict) | E (custom mpc field) |
| DIRECTION | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | E (ext dict) | E (custom mpc field) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 0 | 0 | 5 | 0% | 0% | 100% |
| pandapower | 0 | 0 | 5 | 0% | 0% | 100% |
| GridCal | 0 | 0 | 5 | 0% | 0% | 100% |
| PowerModels.jl | 0 | 0 | 5 | 0% | 0% | 100% |
| PowerSimulations.jl | 3 | 2 | 0 | 60% | 40% | 0% |
| MATPOWER | 2 | 2 | 1 | 40% | 40% | 20% |

### Key Findings

- Interface data is 100% tool-external (X) in PyPSA, pandapower, GridCal, and PowerModels.jl -- none of these tools have any native interface/flowgate concept.
- PowerSimulations.jl (via PowerSystems.jl `TransmissionInterface`) has the best native coverage (60% N), making it the only tool with a first-class interface data model.
- MATPOWER supports interface definitions via `mpc.if` and `mpc.iflim` structures (40% N), providing basic interface flow limit enforcement in OPF.
- INTERFACE_ID is classified as X for tools without interface models rather than E, because the interface concept itself (a named group of branches with aggregate flow limits) has no structural analog -- storing just the ID without the concept is meaningless.

## INTERFACE_ELEMENT.csv

**Domain:** Transmission
**Purpose:** Specifies the individual branch elements that comprise each transmission interface, along with direction coefficients and weighting factors. Each row associates one branch with one interface, establishing the physical composition of the interface defined in INTERFACE.csv. The direction coefficient (+1 or -1) indicates whether positive flow on the branch contributes positively or negatively to the interface flow calculation.
**Row count:** ~500 rows
**Join key:** FROM_BUS + TO_BUS + CKT
**Join target:** branch
**Cardinality:** N:1
**Match rate:** 96.5%

### Join Keys

The composite key FROM_BUS + TO_BUS + CKT joins each interface element record to the branch table via PSS/E identifiers I, J, CKT. The INTERFACE_ID column links back to INTERFACE.csv. The D9 validation found a 96.5% match rate against the branch table, with unmatched rows corresponding to elements defined for contingency interfaces that reference out-of-service or planned branches.

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "INTERFACE_ELEMENT.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| INTERFACE_ID | integer | Numeric identifier of the parent interface. References INTERFACE_ID in INTERFACE.csv. | 15 | no |
| FROM_BUS | integer | From-bus number of the branch element comprising this interface. Corresponds to PSS/E bus number I. | 10523 | yes |
| TO_BUS | integer | To-bus number of the branch element comprising this interface. Corresponds to PSS/E bus number J. | 20847 | yes |
| CKT | string | Circuit identifier of the branch element. Corresponds to PSS/E CKT field. | 1 | yes |
| DIRECTION_COEFF | float | Direction coefficient for the branch's contribution to interface flow: +1.0 means positive branch flow adds to interface flow, -1.0 means it subtracts. | 1.0 | no |
| WEIGHT_FACTOR | float | Weighting factor for the branch's contribution to the aggregate interface flow calculation. Typically 1.0 for full contribution. | 1.0 | no |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| INTERFACE_ID | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | N (TransmissionInterface ref) | N (mpc.if col 1) |
| FROM_BUS | N (Line.bus0) | N (line.from_bus) | N (Line.bus_from) | N (branch["f_bus"]) | N (Arc.from) | N (mpc.branch col 1) |
| TO_BUS | N (Line.bus1) | N (line.to_bus) | N (Line.bus_to) | N (branch["t_bus"]) | N (Arc.to) | N (mpc.branch col 2) |
| CKT | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| DIRECTION_COEFF | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | N (interface element dir) | N (mpc.if direction) |
| WEIGHT_FACTOR | X (no interface model) | X (no interface model) | X (no interface model) | X (no interface model) | E (ext dict) | E (custom mpc field) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 2 | 1 | 3 | 33% | 17% | 50% |
| pandapower | 2 | 1 | 3 | 33% | 17% | 50% |
| GridCal | 2 | 1 | 3 | 33% | 17% | 50% |
| PowerModels.jl | 2 | 1 | 3 | 33% | 17% | 50% |
| PowerSimulations.jl | 4 | 2 | 0 | 67% | 33% | 0% |
| MATPOWER | 4 | 2 | 0 | 67% | 33% | 0% |

### Key Findings

- INTERFACE_ID and DIRECTION_COEFF are tool-external (X) in PyPSA, pandapower, GridCal, and PowerModels.jl, consistent with the INTERFACE.csv findings -- these tools have no interface concept.
- PowerSimulations.jl and MATPOWER both achieve 67% native coverage, the highest among all tools, reflecting their native interface element support.
- The branch identifier fields (FROM_BUS, TO_BUS) are universally natively representable as bus references, while CKT remains universally Extension-representable.
- WEIGHT_FACTOR is Extension-representable even in PowerSimulations.jl and MATPOWER, suggesting that interface weighting is a less common native concept than interface membership.

## OUTAGE.csv

**Domain:** Outage
**Purpose:** Records scheduled and forced outage definitions specifying which network elements are out of service, with effective date ranges and outage classification types. Outage data is used for transmission planning studies, outage coordination, and seasonal assessment studies. Each row defines a single element outage with its temporal validity period and outage action (trip, derate, etc.).
**Row count:** ~3,000 rows
**Join key:** ELEMENT_FROM_BUS + ELEMENT_TO_BUS + ELEMENT_CKT (for branch outages), ELEMENT_BUS + ELEMENT_ID (for generator outages)
**Join target:** branch, generator
**Cardinality:** M:N
**Match rate:** 95.6%

### Join Keys

Like CONTINGENCY.csv, OUTAGE.csv contains mixed element types. Branch outages use the composite key ELEMENT_FROM_BUS + ELEMENT_TO_BUS + ELEMENT_CKT, joining to the branch table via I, J, CKT. Generator outages use ELEMENT_BUS + ELEMENT_ID, joining to the generator table via I, ID. The D9 validation found a 95.6% aggregate match rate. Unmatched rows include outages for elements planned for commissioning or recently decommissioned.

**D9 reference:** See [Join Key Report](../intermediate/csv_join_keys/join_key_report.md), section "OUTAGE.csv"

### Fields

| Field | Type | Semantic Description | Example | Join Key |
|-------|------|---------------------|---------|----------|
| ELEMENT_TYPE | enum | Type of element being outaged: BRANCH for transmission lines or transformers, GENERATOR for generating units. Determines which join key set applies. | BRANCH | no |
| ELEMENT_FROM_BUS | integer | From-bus number of the outaged element (for branch outages). Null for generator outages. Corresponds to PSS/E bus number I. | 10523 | yes |
| ELEMENT_TO_BUS | integer | To-bus number of the outaged element (for branch outages). Null for generator outages. Corresponds to PSS/E bus number J. | 20847 | yes |
| ELEMENT_CKT | string | Circuit identifier of the outaged element (for branch outages). Null for generator outages. Corresponds to PSS/E CKT. | 1 | yes |
| ELEMENT_BUS | integer | Bus number of the outaged generator (for generator outages). Null for branch outages. Corresponds to PSS/E generator bus I. | 31205 | yes |
| OUTAGE_START | datetime | Start date and time of the outage in ISO 8601 format. Defines when the element becomes unavailable. | 2024-03-15T06:00:00 | no |
| OUTAGE_END | datetime | End date and time of the outage in ISO 8601 format. Defines when the element returns to service. | 2024-04-20T18:00:00 | no |
| OUTAGE_TYPE | enum | Classification of the outage: PLANNED for scheduled maintenance, FORCED for unplanned outages, DERATE for partial capacity reduction. Determines how the outage affects element availability. | PLANNED | no |

### Representability

| Field | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-------|-------|------------|---------|----------------|---------------------|----------|
| ELEMENT_TYPE | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage schedule) | X (no outage model) |
| ELEMENT_FROM_BUS | N (Line.bus0) | N (line.from_bus) | N (Line.bus_from) | N (branch["f_bus"]) | N (Arc.from) | N (mpc.branch col 1) |
| ELEMENT_TO_BUS | N (Line.bus1) | N (line.to_bus) | N (Line.bus_to) | N (branch["t_bus"]) | N (Arc.to) | N (mpc.branch col 2) |
| ELEMENT_CKT | E (custom attr) | E (custom column) | E (custom field) | E (dict key) | E (ext dict) | E (custom mpc field) |
| ELEMENT_BUS | N (Generator.bus) | N (gen.bus) | N (Generator.bus) | N (gen["gen_bus"]) | N (ThermalStandard.bus) | N (mpc.gen GEN_BUS) |
| OUTAGE_START | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage schedule) | X (no outage model) |
| OUTAGE_END | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage schedule) | X (no outage model) |
| OUTAGE_TYPE | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage model) | X (no outage schedule) | X (no outage model) |

### Summary

| Tool | Native (N) | Extension (E) | External (X) | N% | E% | X% |
|------|-----------|---------------|--------------|----|----|-----|
| PyPSA | 3 | 1 | 4 | 38% | 12% | 50% |
| pandapower | 3 | 1 | 4 | 38% | 12% | 50% |
| GridCal | 3 | 1 | 4 | 38% | 12% | 50% |
| PowerModels.jl | 3 | 1 | 4 | 38% | 12% | 50% |
| PowerSimulations.jl | 3 | 1 | 4 | 38% | 12% | 50% |
| MATPOWER | 3 | 1 | 4 | 38% | 12% | 50% |

### Key Findings

- Outage schedule data (OUTAGE_START, OUTAGE_END, OUTAGE_TYPE, ELEMENT_TYPE) is universally tool-external (X) across all 6 tools. No tool has a native outage schedule data model with temporal validity.
- All tools have identical representability profiles (38% N, 12% E, 50% X), making this the CSV with the most uniform tool coverage.
- While PowerSimulations.jl has `available` and `must_run` attributes on component types, these represent point-in-time status rather than scheduled outage periods, so they do not satisfy the outage schedule concept.
- The 50% X rate reflects the fundamental gap between power flow tools (which model a single operating point) and outage management (which requires temporal scheduling). Outage application requires external scripting to modify network state across time periods.

## Cross-CSV Summary

| CSV | PyPSA N% | pandapower N% | GridCal N% | PowerModels.jl N% | PowerSimulations.jl N% | MATPOWER N% |
|-----|----------|---------------|------------|-------------------|------------------------|-------------|
| LINE_AND_TRANSFORMER.csv | 40% | 40% | 40% | 60% | 40% | 60% |
| TRADING_HUB.csv | 25% | 25% | 25% | 25% | 25% | 25% |
| GEN_DISTRIBUTION_FACTOR.csv | 40% | 40% | 40% | 40% | 40% | 20% |
| CONTINGENCY.csv | 50% | 50% | 83% | 50% | 83% | 50% |
| INTERFACE.csv | 0% | 0% | 0% | 0% | 60% | 40% |
| INTERFACE_ELEMENT.csv | 33% | 33% | 33% | 33% | 67% | 67% |
| OUTAGE.csv | 38% | 38% | 38% | 38% | 38% | 38% |

## Cross-References

- Phase 1 D9 join-key mapping: `../intermediate/csv_join_keys/join_key_report.md`
- Phase 2 D1 intermediate schema reference: `intermediate-schema.md`
- Phase 2 D2 record-type mapping guide: `mapping-guide.md`
- Phase 2 D5 field criticality matrix: `field-criticality-matrix.md`
- Phase 4 D2 representability summary: `supplemental-csv-representability.md`
