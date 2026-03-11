# Record-Type Mapping Guide

## S1: Purpose and Audience

This document maps every PSS/E v31 record type to a tool-agnostic power-system abstraction and documents which of the six evaluated tools (PyPSA, pandapower, GridCal, PowerModels.jl, PowerSimulations.jl, MATPOWER) have native objects for each abstraction. It serves as the primary reference for determining whether a tool can represent a given record type, what abstraction it maps to, and what alternatives exist for tools that lack native support.

**Audience:** This document is written for LLM-based evaluate-tool agents that compile FNM ingestion tests at runtime.

For field-level details (column names, value ranges, per-unit conventions, and worked examples), refer to the intermediate format schema reference at `intermediate-schema.md`.

The set of non-empty record types is determined by the Phase 1 D3 raw record counter output. The parser fidelity comparison report (Phase 1 D6) informed the alternative representation descriptions and structural transform documentation used throughout this guide.

## S2: Abstraction Vocabulary

The following table defines the canonical abstraction names used throughout this document and all other Phase 2 reference documents. Each abstraction corresponds to one or more PSS/E v31 record sections.

| Abstraction | PSS/E Record Type(s) | Description |
|---|---|---|
| Bus | Bus (Section 1) | A network node where electrical equipment connects; defined by voltage level, type (PQ, PV, slack, isolated), and area/zone membership. |
| Load | Load (Section 2) | A real and reactive power consumption at a bus, modeled as constant power, constant current, or constant impedance components. |
| Fixed Shunt | Fixed Shunt (Section 3) | A fixed shunt admittance (conductance and susceptance) connected to a bus for reactive compensation or loss representation. |
| Generator | Generator (Section 4) | A synchronous machine or equivalent injection at a bus, defined by real power output, reactive power limits, voltage setpoint, and machine parameters. |
| AC Line | Branch (Section 5) | A transmission line or cable connecting two buses, characterized by series impedance (R + jX) and shunt charging susceptance. |
| 2-Winding Transformer | Transformer (Section 6, K=0) | A two-winding transformer connecting two buses, with tap ratio, phase shift, impedance, and tap changer control parameters. |
| 3-Winding Transformer | Transformer (Section 6, K!=0) | A three-winding transformer connecting three buses, defined by three sets of winding parameters; internally decomposed to a star-bus topology for computation. |
| Area | Area (Section 7) | A control area for interchange scheduling, defined by a slack bus and a desired net interchange value. |
| Two-Terminal HVDC Line | Two-Terminal DC (Section 8) | A point-to-point high-voltage DC transmission link between two AC buses via rectifier and inverter converter stations. |
| VSC HVDC Line | VSC DC (Section 9) | A voltage-source converter HVDC link providing independent real and reactive power control at each terminal. |
| Impedance Correction Table | Impedance Correction (Section 10) | A lookup table that adjusts branch or transformer impedance as a function of tap position or other operating conditions. |
| Multi-Terminal DC | Multi-Terminal DC (Section 11) | A DC network with three or more converter terminals interconnected by DC buses and DC branches. |
| Multi-Section Line | Multi-Section Line (Section 12) | A transmission line composed of multiple series-connected sections with different impedance characteristics, sharing a common metered end. |
| Zone | Zone (Section 13) | A grouping of buses for loss allocation, reporting, or market settlement purposes; purely organizational with no electrical effect. |
| Interarea Transfer | Interarea Transfer (Section 14) | A scheduled real power transfer between two areas, used for interchange accounting and area-based dispatch constraints. |
| Owner | Owner (Section 15) | An ownership entity for tracking asset ownership fractions across generators, branches, and transformers for settlement and reporting. |
| FACTS Device | FACTS (Section 16) | A flexible AC transmission system device (SVC, STATCOM, TCSC, UPFC) providing dynamic voltage and power flow control. |
| Switched Shunt | Switched Shunt (Section 17) | A shunt device with discrete switchable steps (capacitor or reactor banks) that adjusts susceptance to regulate bus voltage within a target range. |

## S3: Summary Matrix

| # | PSS/E Record Type | Abstraction | Tier | FNM Status | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Bus | Bus | 1 | Non-empty | Y | Y | Y | Y | Y | Y |
| 2 | Load | Load | 1 | Non-empty | Y | Y | Y | Y | Y | Y |
| 3 | Fixed Shunt | Fixed Shunt | 2 | Non-empty | Y | Y | Y | Y | Y | P |
| 4 | Generator | Generator | 1 | Non-empty | Y | Y | Y | Y | Y | Y |
| 5 | Branch | AC Line | 1 | Non-empty | Y | Y | Y | Y | Y | Y |
| 6 | Transformer | 2-Winding / 3-Winding Transformer | 1 | Non-empty | P | Y | Y | P | P | P |
| 7 | Area | Area | 2 | Non-empty | N | Y | Y | P | P | Y |
| 8 | Two-Terminal DC | Two-Terminal HVDC Line | 2 | Empty | -- | -- | -- | -- | -- | -- |
| 9 | VSC DC | VSC HVDC Line | 2 | Empty | -- | -- | -- | -- | -- | -- |
| 10 | Impedance Correction | Impedance Correction Table | 2 | Empty | -- | -- | -- | -- | -- | -- |
| 11 | Multi-Terminal DC | Multi-Terminal DC | 2 | Empty | -- | -- | -- | -- | -- | -- |
| 12 | Multi-Section Line | Multi-Section Line | 2 | Empty | -- | -- | -- | -- | -- | -- |
| 13 | Zone | Zone | 3 | Non-empty | P | Y | Y | P | P | Y |
| 14 | Interarea Transfer | Interarea Transfer | 3 | Empty | -- | -- | -- | -- | -- | -- |
| 15 | Owner | Owner | 3 | Non-empty | N | N | Y | N | N | N |
| 16 | FACTS | FACTS Device | 2 | Empty | -- | -- | -- | -- | -- | -- |
| 17 | Switched Shunt | Switched Shunt | 2 | Non-empty | P | Y | Y | P | P | P |

**Legend:**

- **Y** -- Native first-class object exists for this abstraction
- **P** -- Partial support (object exists but cannot represent all PSS/E fields for this record type, or requires workaround representation)
- **N** -- No native representation; data must be approximated, discarded, or stored in extension fields
- **--** -- Record type is empty in FNM; tool support not evaluated

## S4: Tier Classification Rationale

The three-tier system classifies PSS/E v31 record types by their impact on power flow computation. The tiers determine evaluation priority: Tier 1 types are tested first and most rigorously, Tier 2 types are tested for ACPF fidelity, and Tier 3 types are checked for preservation but do not affect electrical results.

**Tier 1 (Essential for any power flow)** includes Bus, Load, Generator, Branch, and Transformer. These five record types define the three prerequisites for any power flow calculation: network topology (buses and their connectivity via branches and transformers), power injections (generators and loads), and impedance (branch series impedance and transformer winding parameters). Without any one of these, neither DCPF nor ACPF can produce meaningful results. A tool that cannot represent all five Tier 1 types cannot perform the most basic power flow analysis on the FNM.

**Tier 2 (Needed for full ACPF fidelity)** includes Fixed Shunt, Switched Shunt, Area, Two-Terminal DC, VSC DC, Multi-Terminal DC, Impedance Correction, Multi-Section Line, and FACTS. These record types affect ACPF convergence and accuracy: shunts provide reactive power compensation that influences bus voltages, area interchange constrains inter-area real power flows, HVDC links inject and withdraw real power at converter buses, impedance correction tables adjust branch parameters with operating conditions, multi-section lines define composite branch topologies, and FACTS devices regulate voltage and power flow dynamically. A DCPF can run without these types (since DCPF ignores reactive power and assumes flat voltage), but ACPF results will be inaccurate or may fail to converge without them.

**Tier 3 (Market/administrative data)** includes Zone, Owner, and Interarea Transfer. These record types are organizational and market constructs with no direct effect on the power flow Jacobian or its solution. Zones group buses for reporting and loss allocation, owners track asset ownership fractions for settlement, and interarea transfers record scheduled interchange. A tool that cannot represent Tier 3 types loses no electrical fidelity; the data is preserved in the intermediate format for completeness and downstream market analysis.

The record-type tier classification is related to but distinct from the field-level criticality tiers defined in the field criticality matrix (PRD 05). A record type's tier constrains the maximum criticality of its fields: for example, a field in a Tier 3 record type cannot be classified as DCPF-critical at the field level. However, not all fields in a Tier 1 record type are necessarily critical -- some fields (such as bus NAME) are informational even within essential record types.

## S5: Per-Record-Type Mapping

### S5.1: Bus (Section 1)

**Abstraction:** Bus
**Tier:** 1 -- Buses define the network topology nodes required for any power flow formulation.
**FNM record count:** Non-empty
**Intermediate format table:** `bus`

#### Description

A bus represents a network node in the power system where electrical equipment (generators, loads, shunts, and branch terminals) connects. Each bus is defined by a unique integer identifier, a base voltage level (kV), and a type code that determines its role in the power flow solution: PQ bus (type 1, both P and Q are specified), PV bus (type 2, P and voltage magnitude are specified), slack/swing bus (type 3, voltage magnitude and angle are specified), and isolated bus (type 4, disconnected from the network). Buses also carry area, zone, and owner assignments that provide organizational context.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | Y | `Bus` component | Full bus representation with voltage, type, and zone attributes |
| pandapower | Y | `create_bus()` | Native bus table with all PSS/E bus fields |
| GridCal | Y | `Bus` | Full bus object with voltage, type, area, and zone |
| PowerModels.jl | Y | `bus` dict | Bus dictionary with standard power flow fields |
| PowerSimulations.jl | Y | `ACBus` | Bus type with voltage limits, type, and area |
| MATPOWER | Y | `mpc.bus` | Standard bus matrix with all IEEE CDF fields |

#### Alternative Representations

All evaluated tools have native support; no alternatives needed.

#### Evaluate-Tool Guidance

Verify the tool creates one bus object per intermediate format record. Check that bus type codes (PQ=1, PV=2, slack=3, isolated=4) are preserved or mapped to equivalent tool-specific enumerations. Confirm base voltage (BASKV) and voltage magnitude/angle initial values are ingested without transformation.

### S5.2: Load (Section 2)

**Abstraction:** Load
**Tier:** 1 -- Loads define the real and reactive power demand that drives the power flow solution.
**FNM record count:** Non-empty
**Intermediate format table:** `load`

#### Description

A load record specifies real and reactive power consumption at a bus, decomposed into constant power (MW/Mvar at nominal voltage), constant current (MW/Mvar scaled linearly with voltage magnitude), and constant impedance (MW/Mvar scaled with voltage magnitude squared) components. Each load also carries a status flag (in-service or out-of-service), an area assignment for interchange accounting, and a zone assignment for loss allocation. Multiple loads may be connected to a single bus, distinguished by a load identifier string.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | Y | `Load` component | Supports active/reactive power specification |
| pandapower | Y | `create_load()` | Constant power load with ZIP model extensions |
| GridCal | Y | `Load` | Full load model with constant power, current, and impedance components |
| PowerModels.jl | Y | `load` dict | Load dictionary with Pd/Qd fields |
| PowerSimulations.jl | Y | `PowerLoad` | Load type with active and reactive power |
| MATPOWER | Y | `mpc.bus` Pd/Qd columns | Loads aggregated into bus table columns |

#### Alternative Representations

All evaluated tools have native support; no alternatives needed.

#### Evaluate-Tool Guidance

Verify that each load record maps to a distinct load object (not aggregated at the bus level unless the tool's data model requires it, as with MATPOWER). Check that constant power components (PL, QL) are preserved. If the tool supports ZIP load models, verify that constant current (IP, IQ) and constant impedance (YP, YQ) components are ingested.

### S5.3: Fixed Shunt (Section 3)

**Abstraction:** Fixed Shunt
**Tier:** 2 -- Fixed shunts provide reactive compensation affecting ACPF voltage profiles but are not required for basic DCPF.
**FNM record count:** Non-empty
**Intermediate format table:** `fixed_shunt`

#### Description

A fixed shunt is a constant admittance element connected to a bus, specified as conductance (MW at 1.0 p.u. voltage) and susceptance (Mvar at 1.0 p.u. voltage). Fixed shunts model permanently connected reactive compensation devices (capacitor banks, reactor banks) and equivalent representations of distributed loads or losses. Unlike switched shunts, fixed shunts have no discrete steps or voltage regulation capability -- their admittance is constant regardless of bus voltage.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | Y | `ShuntImpedance` component | Supports conductance and susceptance specification |
| pandapower | Y | `create_shunt()` | Shunt element with G and B parameters |
| GridCal | Y | `Shunt` | Shunt admittance object |
| PowerModels.jl | Y | `shunt` dict | Shunt dictionary with gs/bs fields |
| PowerSimulations.jl | Y | `FixedAdmittance` | Fixed admittance type |
| MATPOWER | P | `mpc.bus` GS/BS columns | Shunts folded into bus table columns; not a separate object |

#### Alternative Representations

- **MATPOWER:** Fixed shunts are represented as GS (conductance) and BS (susceptance) columns in the `mpc.bus` matrix rather than as separate shunt objects. This means multiple fixed shunts at the same bus are summed into a single pair of values, losing individual shunt identity. The total admittance is preserved, but per-shunt status control and individual shunt identification are lost.

#### Evaluate-Tool Guidance

Verify that shunt conductance (GL) and susceptance (BL) values are ingested. For tools with separate shunt objects, verify one-to-one mapping from intermediate format records. For MATPOWER, verify that bus-level GS/BS columns reflect the sum of all fixed shunts at each bus.

### S5.4: Generator (Section 4)

**Abstraction:** Generator
**Tier:** 1 -- Generators define real power injection and voltage regulation essential to any power flow.
**FNM record count:** Non-empty
**Intermediate format table:** `generator`

#### Description

A generator record represents a synchronous machine or equivalent power injection at a bus. Key parameters include real power output (PG), reactive power output (QG), reactive power limits (QT max, QB min), regulated voltage setpoint (VS), machine MVA base (MBASE), and impedance data for fault analysis (ZSORCE). Generators also carry status flags, remote bus regulation targets, and participation factors for area interchange control. The generator at the swing bus sets the system voltage angle reference.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | Y | `Generator` component | Full generator representation with dispatch and voltage control |
| pandapower | Y | `create_gen()` / `create_sgen()` | Separate slack and PV generator types |
| GridCal | Y | `Generator` | Generator object with full PSS/E field mapping |
| PowerModels.jl | Y | `gen` dict | Generator dictionary with standard fields |
| PowerSimulations.jl | Y | `ThermalStandard` / `RenewableDispatch` | Multiple generator types by fuel/technology |
| MATPOWER | Y | `mpc.gen` | Standard generator matrix |

#### Alternative Representations

All evaluated tools have native support; no alternatives needed.

#### Evaluate-Tool Guidance

Verify one generator object per intermediate format record. Check that real power (PG), reactive limits (QT, QB), voltage setpoint (VS), and machine base (MBASE) are preserved. Confirm the swing bus generator is identified correctly.

### S5.5: Branch (Section 5)

**Abstraction:** AC Line
**Tier:** 1 -- Branches define network connectivity and impedance required for any power flow formulation.
**FNM record count:** Non-empty
**Intermediate format table:** `branch`

#### Description

A branch record represents an AC transmission line or cable connecting two buses. Each branch is characterized by series resistance (R) and reactance (X) in per-unit on system MVA base, total line charging susceptance (B), and up to three thermal rating levels (RATEA, RATEB, RATEC) in MVA. The branch also carries a circuit identifier (for parallel lines between the same bus pair), a status flag, and metered-end designation. Branch impedance values are specified in per-unit on 100 MVA system base.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | Y | `Line` component | AC line with R, X, B, and rating parameters |
| pandapower | Y | `create_line_from_parameters()` | Line element with impedance and rating fields |
| GridCal | Y | `Line` | Transmission line object |
| PowerModels.jl | Y | `branch` dict | Branch dictionary (shared with transformers, distinguished by flags) |
| PowerSimulations.jl | Y | `ACBranch` / `Line` | Branch types for AC lines |
| MATPOWER | Y | `mpc.branch` | Standard branch matrix rows (non-transformer entries) |

#### Alternative Representations

All evaluated tools have native support; no alternatives needed.

#### Evaluate-Tool Guidance

Verify one branch object per intermediate format record. Check that series impedance (R, X), charging susceptance (B), and thermal ratings (RATEA, RATEB, RATEC) are preserved. Confirm that circuit identifiers (CKT) and status flags (ST) are ingested.

### S5.6: Transformer (Section 6)

**Abstraction:** 2-Winding Transformer / 3-Winding Transformer
**Tier:** 1 -- Transformers are essential for voltage transformation and network connectivity in any power flow.
**FNM record count:** Non-empty
**Intermediate format table:** `transformer`

#### Description

PSS/E v31 section 6 contains both 2-winding and 3-winding transformer records, distinguished by the K field (third winding bus number). When K=0, the record is a 2-winding transformer connecting two buses with a turns ratio, phase shift angle, and winding impedance. When K is nonzero, the record is a 3-winding transformer connecting three buses, specified by three sets of winding parameters (impedance, tap ratio, phase shift) that are internally decomposed to a star-bus equivalent topology for power flow computation.

Transformer records are multi-line entries in the PSS/E raw file: 2-winding transformers span 4 lines and 3-winding transformers span 5 lines. Key parameters include winding impedances (R, X), magnetizing admittance (MAG1, MAG2), turns ratios (WINDV), phase shift angles (ANG), tap changer control modes (COD), and winding MVA bases (SBASE1-2, SBASE2-3, SBASE3-1 for 3-winding).

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | P | `Transformer` component | Supports 2-winding natively; 3-winding requires star-bus decomposition into multiple 2-winding transformers |
| pandapower | Y | `create_transformer()` / `create_transformer3w()` | Native support for both 2-winding and 3-winding transformers |
| GridCal | Y | `Transformer2W` / `Transformer3W` | Dedicated objects for both winding configurations |
| PowerModels.jl | P | `branch` dict with transformer flag | 2-winding via branch dict; 3-winding requires star-bus decomposition into branch entries |
| PowerSimulations.jl | P | `TapTransformer` / `PhaseShiftingTransformer` | 2-winding types available; 3-winding requires star-bus decomposition |
| MATPOWER | P | `mpc.branch` with TAP/SHIFT fields | 2-winding via branch rows; 3-winding auto-decomposed by psse2mpc into star-bus branch rows |

#### Alternative Representations

- **PyPSA:** 3-winding transformers must be decomposed into three 2-winding `Transformer` components connected at an auxiliary star bus. This loses the unified 3-winding parameterization and requires manual calculation of equivalent winding impedances. The star-bus voltage level must be chosen consistently.
- **PowerModels.jl:** 3-winding transformers are represented as three `branch` dictionary entries connected at a star bus. The decomposition preserves electrical equivalence but loses the original 3-winding record structure.
- **PowerSimulations.jl:** 3-winding transformers are decomposed into per-winding `TapTransformer` or `PhaseShiftingTransformer` objects at a star bus. Individual winding control modes are preserved but the unified 3-winding specification is lost.
- **MATPOWER:** The `psse2mpc` converter automatically decomposes 3-winding transformers into star-bus branch rows. The decomposition is transparent to the user but the original K-field and 3-winding record structure are not preserved in the MATPOWER case struct.

#### Evaluate-Tool Guidance

Verify that 2-winding transformer records (K=0) create one transformer object each. For 3-winding transformer records (K!=0), verify the tool either creates a native 3-winding object or correctly decomposes into three 2-winding equivalents at a star bus. Check that tap ratios (WINDV1, WINDV2), phase shift angles (ANG1), and winding impedances (R1-2, X1-2) are preserved. Refer to the 3-winding transformer reference (`three-winding-transformers.md`) for detailed decomposition validation.

### S5.7: Area (Section 7)

**Abstraction:** Area
**Tier:** 2 -- Area interchange constraints affect ACPF convergence but are not needed for basic DCPF topology.
**FNM record count:** Non-empty
**Intermediate format table:** `area`

#### Description

An area record defines a control area for interchange scheduling. Each area is identified by an integer number and a name, and specifies a slack bus (ISW) for area interchange control and a desired net interchange value (PDES) in MW. Areas partition the network into regions whose net real power interchange is monitored and controlled during ACPF solution. The area slack bus absorbs mismatch between scheduled and actual interchange within its area.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | N | -- | No area object; area membership must be stored as custom bus attributes |
| pandapower | Y | `create_area()` | Dedicated area table |
| GridCal | Y | `Area` | Area object with interchange and slack bus fields |
| PowerModels.jl | P | `area` dict | Area dictionary exists but interchange scheduling fields are limited |
| PowerSimulations.jl | P | `Area` type | Area type exists but no native interchange (PDES) field |
| MATPOWER | Y | `mpc.areas` | Areas matrix with ISW and PDES fields |

#### Alternative Representations

- **PyPSA:** Areas have no native representation. Area membership can be stored as a custom attribute on Bus components (e.g., `bus.area = 1`), but there is no mechanism for interchange scheduling or area slack bus designation. Area interchange constraints must be implemented as custom constraints if needed.
- **PowerModels.jl:** The `area` dictionary stores area identifiers but has limited support for interchange scheduling parameters. PDES and ISW fields may need to be stored as extension data.
- **PowerSimulations.jl:** The `Area` type provides area grouping but does not natively support interchange (PDES) or area slack bus (ISW) specification. These must be handled through custom extensions.

#### Evaluate-Tool Guidance

Verify one area object per intermediate format record. Check that area number (I), slack bus (ISW), desired interchange (PDES), and interchange tolerance (PTOL) are preserved where the tool's data model supports them. For tools without native area support, verify that area identifiers are at minimum stored as bus attributes.

### S5.8: Two-Terminal DC (Section 8)

**Abstraction:** Two-Terminal HVDC Line
**Tier:** 2
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for point-to-point HVDC transmission links but has zero records in the FNM.

### S5.9: VSC DC (Section 9)

**Abstraction:** VSC HVDC Line
**Tier:** 2
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for voltage-source converter HVDC links but has zero records in the FNM.

### S5.10: Impedance Correction (Section 10)

**Abstraction:** Impedance Correction Table
**Tier:** 2
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for lookup tables that adjust branch or transformer impedance as a function of operating conditions but has zero records in the FNM.

### S5.11: Multi-Terminal DC (Section 11)

**Abstraction:** Multi-Terminal DC
**Tier:** 2
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for multi-terminal DC networks but has zero records in the FNM.

### S5.12: Multi-Section Line (Section 12)

**Abstraction:** Multi-Section Line
**Tier:** 2
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for composite transmission lines with multiple series-connected sections but has zero records in the FNM.

### S5.13: Zone (Section 13)

**Abstraction:** Zone
**Tier:** 3 -- Zones are organizational groupings for reporting and loss allocation with no effect on power flow computation.
**FNM record count:** Non-empty
**Intermediate format table:** `zone`

#### Description

A zone record defines a named grouping of buses used for loss allocation, generation summary reporting, and market settlement purposes. Each zone is identified by an integer number and a name string. Zones have no electrical effect on the power flow solution -- they do not constrain interchange, regulate voltage, or modify impedance. Bus-to-zone assignments are specified in the bus record (ZONE field), and the zone table provides the zone name lookup.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | P | Bus attribute | No dedicated zone object; zone IDs stored as bus attributes only |
| pandapower | Y | `zone` column on bus table | Zone tracked as bus attribute with zone lookup |
| GridCal | Y | `Zone` | Dedicated zone object |
| PowerModels.jl | P | Bus `zone` attribute | Zone stored as bus dictionary attribute; no separate zone table |
| PowerSimulations.jl | P | `LoadZone` | LoadZone type exists but primarily for load aggregation, not general zone semantics |
| MATPOWER | Y | `mpc.bus` ZONE column | Zone tracked as bus matrix column |

#### Alternative Representations

- **PyPSA:** Zone identifiers can be stored as custom attributes on Bus components. Zone names and metadata are not natively supported and must be stored in external data structures.
- **PowerModels.jl:** Zone is stored only as a bus attribute integer. The zone name string from the zone table has no native storage location and must be tracked externally.
- **PowerSimulations.jl:** `LoadZone` provides zone-like grouping but is semantically tied to load aggregation rather than general-purpose zoning. The mapping is approximate.

#### Evaluate-Tool Guidance

Verify that zone identifiers (I) are preserved, either as dedicated zone objects or as bus attributes. Check that zone names (ZONAME) are stored where the tool's data model supports them. For tools without dedicated zone tables, verify that bus-to-zone assignments are preserved in bus records.

### S5.14: Interarea Transfer (Section 14)

**Abstraction:** Interarea Transfer
**Tier:** 3
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for scheduled real power transfers between areas but has zero records in the FNM.

### S5.15: Owner (Section 15)

**Abstraction:** Owner
**Tier:** 3 -- Ownership data is administrative metadata with no effect on power flow computation.
**FNM record count:** Non-empty
**Intermediate format table:** `owner`

#### Description

An owner record defines an ownership entity identified by an integer number and a name string. Ownership assignments appear as fractional ownership fields on generators, branches, and transformers (up to four co-owners per element with ownership fractions summing to 1.0). Owners provide asset tracking for settlement, regulatory reporting, and cost allocation. They have no effect on the power flow Jacobian or solution.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | N | -- | No owner object or ownership fraction fields |
| pandapower | N | -- | No owner object or ownership fraction fields |
| GridCal | Y | `Owner` | Dedicated owner object with ownership fraction tracking |
| PowerModels.jl | N | -- | No owner representation |
| PowerSimulations.jl | N | -- | No owner representation |
| MATPOWER | N | -- | No owner representation in mpc struct |

#### Alternative Representations

- **PyPSA, pandapower, PowerModels.jl, PowerSimulations.jl, MATPOWER:** Owner data has no native representation and must be stored in user-defined extension fields, custom annotations, or external lookup tables. Ownership fractions on generators, branches, and transformers are silently discarded during ingestion. This has no effect on power flow results but means settlement and cost allocation data is lost.

#### Evaluate-Tool Guidance

Verify that owner records are ingested where the tool supports them (GridCal). For tools without owner support, document the gap but do not fail the test -- owner data is Tier 3 administrative metadata.

### S5.16: FACTS (Section 16)

**Abstraction:** FACTS Device
**Tier:** 2
**FNM status:** Empty -- not present in the FNM Annual S01 file.

This record type is defined in PSS/E v31 for flexible AC transmission system devices but has zero records in the FNM.

### S5.17: Switched Shunt (Section 17)

**Abstraction:** Switched Shunt
**Tier:** 2 -- Switched shunts provide discrete reactive compensation affecting ACPF voltage regulation but are not needed for basic DCPF.
**FNM record count:** Non-empty
**Intermediate format table:** `switched_shunt`

#### Description

A switched shunt record defines a bus-connected reactive compensation device with discrete switchable steps. Each step specifies a number of capacitor or reactor bank blocks and the susceptance per block. The switched shunt has a control mode (fixed, discrete, continuous), a voltage regulation target range (VSWHI, VSWLO), and optionally a remote regulated bus. During ACPF solution, the solver adjusts the shunt susceptance within the available discrete steps to maintain bus voltage within the target range. The total susceptance range is bounded by BINIT (initial value) and the sum of all step blocks.

#### Tool Support

| Tool | Support | Native Object | Notes |
|---|---|---|---|
| PyPSA | P | `ShuntImpedance` component | Can represent shunt admittance but has no discrete step model or voltage regulation target |
| pandapower | Y | `create_shunt()` with step parameter | Supports switched shunt with step control and voltage regulation |
| GridCal | Y | `ControllableShunt` | Full switched shunt model with discrete steps and voltage targets |
| PowerModels.jl | P | `shunt` dict | Shunt dictionary supports admittance but has no discrete step or voltage regulation model |
| PowerSimulations.jl | P | `SwitchedAdmittance` | Switched admittance type exists but with limited step representation |
| MATPOWER | P | `mpc.bus` BS column + shunt data | Continuous min/max susceptance only; discrete step structure is lost |

#### Alternative Representations

- **PyPSA:** Switched shunts are approximated as `ShuntImpedance` components with a fixed susceptance value (typically BINIT). The discrete step structure, voltage regulation targets, and control mode are lost. The shunt behaves as a fixed shunt in the power flow solution.
- **PowerModels.jl:** Switched shunts are stored in the `shunt` dictionary with a single susceptance value. The discrete step model and voltage regulation targets are not represented. The shunt is treated as fixed during OPF.
- **PowerSimulations.jl:** `SwitchedAdmittance` exists but the discrete step block structure (N1/B1, N2/B2, etc.) may not be fully representable. Voltage regulation targets may require custom constraints.
- **MATPOWER:** Switched shunts are represented through the bus table BS column (initial susceptance) and optionally a shunt data structure with continuous min/max bounds. The discrete step structure (number of blocks, susceptance per block) is collapsed into a continuous range, losing the constraint that susceptance can only take values at specific discrete steps.

#### Evaluate-Tool Guidance

Verify that switched shunt initial susceptance (BINIT) is ingested. For tools with discrete step support, verify that step blocks (N1/B1 through N8/B8) are preserved. Check that voltage regulation targets (VSWHI, VSWLO) and control mode (MODSW) are ingested where supported. For tools with only continuous shunt models, verify that the susceptance range (min/max from step blocks) is correctly computed.

## S6: Cross-References

The following related documents provide additional detail for specific aspects of the FNM intermediate format:

- **Intermediate format schema reference** -- `intermediate-schema.md` (PRD 01): Field-level definitions, value ranges, and data types for all intermediate format tables.
- **Per-unit convention reference** -- `per-unit-conventions.md` (PRD 03): Per-unit base conventions for impedance, tap ratio, and admittance fields across record types.
- **3-winding transformer reference** -- `three-winding-transformers.md` (PRD 04): Star-bus decomposition methodology, winding parameter mapping, and tap changer control semantics.
- **Field criticality matrix** -- `field-criticality-matrix.md` (PRD 05): Field-level criticality classification (DCPF-critical, ACPF-critical, informational) for prioritizing ingestion verification.
- **Parser fidelity comparison** -- `../scripts/parser_comparison.py` (Phase 1 D6): Parser output comparison documenting structural transforms (star-bus decomposition, shunt collapsing) and record count discrepancies.
- **Intermediate format JSON Schema files** -- `../intermediate/schemas/` (Phase 1 D7): Machine-readable JSON Schema definitions for each intermediate format table.
