# Intermediate Format Schema Reference

**Version:** 1.0
**Phase 1 Schema:** `../intermediate/schemas/` (JSON Schema Draft 2020-12)
**Audience:** evaluate-tool agents, human reviewers
**Normative definitions:** Phase 1 D7 JSON Schema files define data types,
  required/optional status, and valid ranges. This document adds semantic
  descriptions, worked examples, and ingestion verification guidance.

## Table Summary

| Table | PSS/E Record Type | Records | Columns | Primary Key | Purpose |
| ----- | ----------------- | ------- | ------- | ----------- | ------- |
| `bus` | Bus | ~30,000 | 13 | `[I]` | PSS/E v31 Bus record type |
| `load` | Load | ~15,000 | 13 | `[I, ID]` | PSS/E v31 Load record type |
| `fixed_shunt` | Fixed Shunt | ~500 | 5 | `[I, ID]` | PSS/E v31 Fixed Shunt record type |
| `generator` | Generator | ~5,000 | 28 | `[I, ID]` | PSS/E v31 Generator record type |
| `branch` | Branch | ~35,000 | 24 | `[I, J, CKT]` | PSS/E v31 Branch record type |
| `transformer` | Transformer | ~8,000 | 83 | `[I, J, K, CKT]` | PSS/E v31 Transformer record type |
| `area` | Area | ~30 | 5 | `[I]` | PSS/E v31 Area record type |
| `two_terminal_dc` | Two-Terminal DC | ~5 | 46 | `[NAME]` | PSS/E v31 Two-Terminal DC line record type |
| `vsc_dc` | VSC DC | ~2 | 41 | `[NAME]` | PSS/E v31 VSC DC line record type |
| `impedance_correction` | Impedance Correction | ~200 | 23 | `[T]` | PSS/E v31 Impedance Correction table record type |
| `multi_terminal_dc` | Multi-Terminal DC | ~1 | 8 | `[NAME]` | PSS/E v31 Multi-Terminal DC line header record type |
| `multi_section_line` | Multi-Section Line | ~800 | 13 | `[I, J, ID]` | PSS/E v31 Multi-Section Line grouping record type |
| `zone` | Zone | ~40 | 2 | `[I]` | PSS/E v31 Zone record type |
| `interarea_transfer` | Interarea Transfer | ~50 | 4 | `[ARFROM, ARTO, TRID]` | PSS/E v31 Interarea Transfer record type |
| `owner` | Owner | ~100 | 2 | `[I]` | PSS/E v31 Owner record type |
| `facts` | FACTS | ~50 | 14 | `[NAME]` | PSS/E v31 FACTS device record type |
| `switched_shunt` | Switched Shunt | ~3,000 | 26 | `[I]` | PSS/E v31 Switched Shunt record type |

## Bus

**Table name:** `bus`
**Schema file:** [`../intermediate/schemas/bus.schema.json`](../intermediate/schemas/bus.schema.json)
**Primary key:** `[I]`
**Purpose:** Defines every node (bus) in the transmission network. Each bus has a unique number, base voltage, type code (PQ/PV/swing/isolated), and solved-state voltage. All other record types reference buses by number. The bus table is the topological foundation of the network model.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Unique bus number identifying this node in the network topology. All branch, generator, load, and shunt records reference buses by this number. | 10000–99999 for large networks | no | none | Verify I is a positive integer preserved exactly; loss of bus number destroys topology |
| `NAME` | string | — | Alphanumeric bus name, up to 12 characters, padded with trailing spaces. Used for human-readable identification in reports and diagrams. | — | no | `"            "` | Verify NAME is preserved including trailing whitespace; compare after stripping only if the tool normalizes whitespace |
| `BASKV` | number | kV | Bus base voltage in kV. Defines the voltage class for this bus and is the reference for all per-unit voltage calculations at this bus. A value of 0.0 is the PSS/E default but is physically meaningless for real network buses. | 69–500 for transmission | no | 0.0 | Verify BASKV > 0 for all buses with IDE != 4 (non-isolated); verify preserved to at least 1 decimal place |
| `IDE` | integer | — | Bus type code: 1=PQ (load), 2=PV (generator), 3=swing (reference), 4=isolated (disconnected). Determines the power flow solution method at this bus. | 1–4 | no | 1 | Verify IDE is one of {1, 2, 3, 4} and matches the source exactly; confirm bus type code maps to the tool's equivalent enum without silent coercion |
| `AREA` | integer | — | Area number to which this bus is assigned. Areas define interchange control regions in the power flow solution. | 1–50 for large ISOs | no | 1 | Verify AREA references a valid area number in the area table |
| `ZONE` | integer | — | Zone number for geographic or administrative grouping. Zones provide finer-grained grouping than areas, used in reporting and load allocation. | 1–50 | no | 1 | Verify ZONE references a valid zone number in the zone table |
| `OWNER` | integer | — | Owner number identifying the entity that owns this bus. Used for ownership tracking and cost allocation. | 1–200 | no | 1 | Verify OWNER references a valid owner number in the owner table |
| `VM` | number | pu | Bus voltage magnitude in per-unit on the bus base voltage (BASKV). In a solved case, this represents the steady-state voltage. In an unsolved case, this is the initial voltage guess. | 0.95–1.05 for solved case | no | 1.0 | Verify VM preserved to at least 4 decimal places; values outside 0.9–1.1 in a solved case indicate convergence issues |
| `VA` | number | deg | Bus voltage angle in degrees. The swing bus angle is the reference (typically 0.0). All other angles are relative to the swing bus. | -180–180 | no | 0.0 | Verify VA preserved to at least 2 decimal places; swing bus (IDE=3) should have VA near 0.0 |
| `NVHI` | number | pu | Normal operating voltage high limit in per-unit. Used by OPF and monitoring functions to flag voltage violations. | 1.05–1.10 | yes | 1.1 | If field is at PSS/E default (1.1), tool may omit — do not penalize |
| `NVLO` | number | pu | Normal operating voltage low limit in per-unit. Buses with voltage below this limit are flagged as voltage violations. | 0.90–0.95 | yes | 0.9 | If field is at PSS/E default (0.9), tool may omit — do not penalize |
| `EVHI` | number | pu | Emergency voltage high limit in per-unit. Applied during contingency analysis to allow wider voltage tolerance under emergency conditions. | 1.05–1.10 | yes | 1.1 | If field is at PSS/E default (1.1), tool may omit — do not penalize |
| `EVLO` | number | pu | Emergency voltage low limit in per-unit. More relaxed than normal low limit, applied during contingency analysis. | 0.85–0.95 | yes | 0.9 | If field is at PSS/E default (0.9), tool may omit — do not penalize |

### Worked Example

```
I:      30100
NAME:   "MESA 230    "
BASKV:  230.0
IDE:    1
AREA:   5
ZONE:   12
OWNER:  3
VM:     1.0142
VA:     -8.35
NVHI:   1.1
NVLO:   0.9
EVHI:   1.1
EVLO:   0.9
```

### Nullable and Default Behavior

All bus fields are required in PSS/E v31 and have well-defined defaults. BASKV=0.0 is the PSS/E default but indicates an uninitialized bus; real network buses always have BASKV > 0. VM defaults to 1.0 (flat start), and VA defaults to 0.0 degrees. The voltage limit fields (NVHI, NVLO, EVHI, EVLO) default to standard PSS/E values and may be omitted by tools without penalty. The canonical parser writes all fields including those at default values.

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md#bus-voltage) for VM/VA per-unit basis.
- See [Field Criticality Matrix](field-criticality-matrix.md) for DCPF/ACPF criticality tiers.
- See [Record-Type Mapping Guide](mapping-guide.md#bus) for tool-specific bus representations.

## Load

**Table name:** `load`
**Schema file:** [`../intermediate/schemas/load.schema.json`](../intermediate/schemas/load.schema.json)
**Primary key:** `[I, ID]`
**Purpose:** Represents electrical demand at each bus. Loads are modeled with constant-power (PL, QL), constant-current (IP, IQ), and constant-admittance (YP, YQ) components. Multiple loads can exist at one bus, distinguished by their two-character ID.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Bus number at which this load is connected. Multiple loads can exist at the same bus, distinguished by ID. | 10000–99999 | no | none | Verify I references a valid bus number in the bus table |
| `ID` | string | — | Two-character load identifier. Together with I, forms the composite primary key. Default '1 ' (one followed by space). | — | no | `"1 "` | Verify ID is preserved as a 2-character string including trailing space |
| `STATUS` | integer | — | Load status: 1=in-service (included in power flow), 0=out-of-service (excluded from power flow solution). | 0–1 | no | 1 | Verify STATUS is one of {0, 1} and matches the source exactly |
| `AREA` | integer | — | Area number for this load, defaults to the bus's area. Used for area interchange calculations. | 1–50 | no | 1 | Verify AREA is a positive integer; if at default (1), tool may inherit from bus |
| `ZONE` | integer | — | Zone number for this load, defaults to the bus's zone. | 1–50 | no | 1 | Verify ZONE is a positive integer; if at default (1), tool may inherit from bus |
| `PL` | number | MW | Constant-power active load in MW. The primary real power demand at this bus. Positive values consume power. | 0–5000 | no | 0.0 | Verify PL preserved to at least 2 decimal places; sign convention: positive = consumption |
| `QL` | number | MVAR | Constant-power reactive load in MVAR. Positive values consume reactive power (lagging power factor). | -500–1000 | no | 0.0 | Verify QL preserved to at least 2 decimal places; sign convention: positive = lagging (inductive) |
| `IP` | number | MW | Constant-current active load component in MW at 1.0 pu voltage. Scales linearly with voltage magnitude. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `IQ` | number | MVAR | Constant-current reactive load component in MVAR at 1.0 pu voltage. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `YP` | number | MW | Constant-admittance active load component in MW at 1.0 pu voltage. Scales with voltage squared. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `YQ` | number | MVAR | Constant-admittance reactive load component in MVAR at 1.0 pu voltage. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `OWNER` | integer | — | Owner number for this load. | 1–200 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `SCALE` | integer | — | Load scaling flag: 1=load participates in scaling, 0=fixed load. Controls whether the load is adjusted during area interchange scaling. | 0–1 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |

### Worked Example

```
I:      30100
ID:     "1 "
STATUS: 1
AREA:   5
ZONE:   12
PL:     245.80
QL:     85.30
IP:     0.0
IQ:     0.0
YP:     0.0
YQ:     0.0
OWNER:  3
SCALE:  1
```

### Nullable and Default Behavior

The constant-current (IP, IQ) and constant-admittance (YP, YQ) load components default to 0.0, meaning the load is modeled as constant-power only. A zero value is semantically meaningful (not missing) -- it means that load component is absent. OWNER defaults to 1, and SCALE defaults to 1 (load participates in scaling).

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md) for load component scaling.
- See [Record-Type Mapping Guide](mapping-guide.md#load) for tool-specific load representations.

## Fixed Shunt

**Table name:** `fixed_shunt`
**Schema file:** [`../intermediate/schemas/fixed_shunt.schema.json`](../intermediate/schemas/fixed_shunt.schema.json)
**Primary key:** `[I, ID]`
**Purpose:** Represents fixed (non-switchable) shunt compensation devices. Fixed shunts provide reactive power support (capacitive) or absorption (inductive) at a constant value regardless of voltage. Distinguished from switched shunts which have discrete steps.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Bus number at which this fixed shunt is connected. | 10000–99999 | no | none | Verify I references a valid bus number in the bus table |
| `ID` | string | — | Two-character shunt identifier. Together with I, forms the composite primary key. | — | no | `"1 "` | Verify ID is preserved as a 2-character string including trailing space |
| `STATUS` | integer | — | Shunt status: 1=in-service, 0=out-of-service. | 0–1 | no | 1 | Verify STATUS is one of {0, 1} and matches the source exactly |
| `GL` | number | MW | Active component of shunt admittance to ground in MW at 1.0 pu voltage. Positive GL represents real power consumption (resistive losses). | — | no | 0.0 | Verify GL preserved to at least 4 decimal places; most fixed shunts have GL=0 (purely reactive) |
| `BL` | number | MVAR | Reactive component of shunt admittance to ground in MVAR at 1.0 pu voltage. Positive BL is capacitive (generates reactive power), negative BL is inductive (absorbs reactive power). | -500–500 | no | 0.0 | Verify BL is positive for capacitive shunts, negative for inductive; verify preserved to at least 2 decimal places |

### Worked Example

```
I:      42500
ID:     "1 "
STATUS: 1
GL:     0.0
BL:     150.0
```

### Nullable and Default Behavior

GL defaults to 0.0, meaning no active power loss in the shunt (purely reactive). BL defaults to 0.0 but is typically non-zero for any meaningful shunt device. STATUS defaults to 1 (in-service).

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md#shunt-admittance) for BL sign convention.
- See [Record-Type Mapping Guide](mapping-guide.md#fixed-shunt) for tool-specific shunt representations.

## Generator

**Table name:** `generator`
**Schema file:** [`../intermediate/schemas/generator.schema.json`](../intermediate/schemas/generator.schema.json)
**Primary key:** `[I, ID]`
**Purpose:** Represents all generating units including conventional thermal, hydro, wind, and solar plants. Each generator has active/reactive output, capability limits, voltage setpoint, and machine impedance data. Multiple generators at one bus use different IDs.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Bus number at which this generator is connected. | 10000–99999 | no | none | Verify I references a valid bus number in the bus table |
| `ID` | string | — | Two-character machine identifier. Together with I, forms the composite primary key. Allows multiple generators at the same bus. | — | no | `"1 "` | Verify ID is preserved as a 2-character string including trailing space |
| `PG` | number | MW | Active power output of the generator in MW. Positive values indicate generation. Negative values indicate a synchronous condenser consuming real power. | 50–1000 for large units | no | 0.0 | Verify PG preserved to at least 2 decimal places |
| `QG` | number | MVAR | Reactive power output of the generator in MVAR. Determined by the power flow solution within the QB–QT limits. | -500–500 | no | 0.0 | Verify QG preserved to at least 2 decimal places |
| `QT` | number | MVAR | Maximum reactive power output in MVAR. Upper limit for the generator's reactive capability curve. | 0–1000 | no | 9999.0 | Verify QT preserved to at least 1 decimal place; default 9999.0 indicates unconstrained |
| `QB` | number | MVAR | Minimum reactive power output in MVAR. Lower limit for the generator's reactive capability. | -1000–0 | no | -9999.0 | Verify QB preserved to at least 1 decimal place; default -9999.0 indicates unconstrained |
| `VS` | number | pu | Voltage setpoint for voltage-regulating generators in per-unit. The generator adjusts reactive output to maintain this voltage at the regulated bus (local or remote via IREG). | 0.95–1.10 | no | 1.0 | Verify VS preserved to at least 4 decimal places |
| `IREG` | integer | — | **[preservation-critical]** Remote regulated bus number. 0=local voltage regulation (at bus I). Non-zero=remote bus whose voltage is controlled by this generator. Critical for correct voltage regulation topology in power flow. | 0 or valid bus number | no | 0 | MUST be preserved exactly; verify IREG=0 means local regulation, not missing; loss of remote regulation topology is a fidelity finding |
| `MBASE` | number | MVA | Machine MVA base for per-unit impedance conversion. Generator impedances ZR, ZX are on this base. | 50–1500 | no | 100.0 | Verify MBASE preserved to at least 1 decimal place |
| `ZR` | number | pu | Machine resistance in per-unit on MBASE. Part of the generator's internal impedance model for short-circuit studies. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `ZX` | number | pu | Machine reactance in per-unit on MBASE. Sub-transient or transient reactance used in short-circuit calculations. | 0.1–0.4 | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `RT` | number | pu | Step-up transformer resistance in per-unit on MBASE. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `XT` | number | pu | Step-up transformer reactance in per-unit on MBASE. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `GTAP` | number | pu | Step-up transformer off-nominal turns ratio in per-unit on bus base kV. | 0.9–1.1 | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `STAT` | integer | — | Generator status: 1=in-service, 0=out-of-service. | 0–1 | no | 1 | Verify STAT is one of {0, 1} and matches the source exactly |
| `RMPCT` | number | % | Percent of total MVAR range allocated to remote voltage regulation. | 0–100 | yes | 100.0 | If field is at PSS/E default (100.0), tool may omit — do not penalize |
| `PT` | number | MW | Maximum active power output in MW. | 50–2000 | yes | 9999.0 | Verify PT preserved to at least 1 decimal place; default 9999.0 indicates unconstrained |
| `PB` | number | MW | Minimum active power output in MW. | -100–0 | yes | -9999.0 | Verify PB preserved to at least 1 decimal place; default -9999.0 indicates unconstrained |
| `O1` | integer | — | Owner number 1. | 1–200 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `F1` | number | — | Fraction of generator owned by owner 1. | 0.0–1.0 | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `O2` | integer | — | Owner number 2. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F2` | number | — | Fraction owned by owner 2. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O3` | integer | — | Owner number 3. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F3` | number | — | Fraction owned by owner 3. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O4` | integer | — | Owner number 4. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F4` | number | — | Fraction owned by owner 4. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `WMOD` | integer | — | Wind machine reactive power control mode. 0=standard, 1=constant power factor, 2=constant Q, 3=constant voltage. | 0–3 | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `WPF` | number | — | Wind machine power factor for WMOD=1 mode. | 0.8–1.0 | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |

### Worked Example

```
I:      50200
ID:     "1 "
PG:     350.00
QG:     45.20
QT:     200.0
QB:     -100.0
VS:     1.0250
IREG:   0
MBASE:  400.0
ZR:     0.0
ZX:     1.0
RT:     0.0
XT:     0.0
GTAP:   1.0
STAT:   1
RMPCT:  100.0
PT:     400.0
PB:     100.0
O1:     5
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
WMOD:   0
WPF:    1.0
```

### Nullable and Default Behavior

QT=9999.0 and QB=-9999.0 indicate unconstrained reactive capability (PSS/E defaults). IREG=0 means local voltage regulation (at bus I), not 'no regulation'. This distinction is critical: zero is a meaningful value, not a null. ZR, ZX, RT, XT, GTAP are machine impedance parameters that default to their PSS/E values; tools commonly omit these for steady-state power flow. Owner fields O2-O4 default to 0, meaning single ownership.

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md#generator-impedance) for MBASE-based per-unit.
- See [Record-Type Mapping Guide](mapping-guide.md#generator) for tool-specific generator representations.

## Branch

**Table name:** `branch`
**Schema file:** [`../intermediate/schemas/branch.schema.json`](../intermediate/schemas/branch.schema.json)
**Primary key:** `[I, J, CKT]`
**Purpose:** Represents transmission lines, cables, and series elements connecting two buses. Each branch has impedance (R, X, B), thermal ratings, and status. Parallel branches between the same bus pair are distinguished by circuit identifier CKT.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | From-bus number. Together with J and CKT, forms the branch's composite primary key. | 10000–99999 | no | none | Verify I references a valid bus number in the bus table |
| `J` | integer | — | To-bus number. Branch connects bus I to bus J. The sign of J does not matter for topology (absolute value is used). | 10000–99999 | no | none | Verify J references a valid bus number in the bus table |
| `CKT` | string | — | Two-character circuit identifier allowing parallel branches between the same bus pair. | — | no | `"1 "` | Verify CKT is preserved as a 2-character string including trailing space |
| `R` | number | pu | Branch resistance in per-unit on system MVA base (SBASE) and bus base voltage. For transmission lines, R is typically much smaller than X (R/X ratio < 0.5). | 0.0001–0.1 | no | none | Verify R preserved to at least 5 decimal places; verify R < X for transmission lines (R/X < 1.0) |
| `X` | number | pu | Branch reactance in per-unit on system MVA base. The dominant impedance component for transmission lines. X must be non-zero for in-service branches. | 0.001–0.5 | no | none | Verify X is non-zero for all in-service branches (ST=1); verify X preserved to at least 5 decimal places |
| `B` | number | pu | Total branch charging susceptance in per-unit on system MVA base. For overhead lines, B is proportional to line length and voltage. For short lines, B may be 0. | 0.0–5.0 | no | 0.0 | Verify B preserved to at least 5 decimal places; B=0 is valid for short lines and cables |
| `RATEA` | number | MVA | Normal thermal rating in MVA (Rating A). Used for continuous loading monitoring. | 0–3000 | no | 0.0 | Verify RATEA preserved to at least 1 decimal place; 0.0 means no limit (not monitored) |
| `RATEB` | number | MVA | Emergency thermal rating in MVA (Rating B). Short-term overload limit. | 0–4000 | no | 0.0 | Verify RATEB preserved to at least 1 decimal place; 0.0 means no limit |
| `RATEC` | number | MVA | Long-term emergency rating in MVA (Rating C). | 0–5000 | no | 0.0 | Verify RATEC preserved to at least 1 decimal place; 0.0 means no limit |
| `GI` | number | pu | Line shunt conductance at from-bus end in per-unit. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `BI` | number | pu | Line shunt susceptance at from-bus end in per-unit. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `GJ` | number | pu | Line shunt conductance at to-bus end in per-unit. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `BJ` | number | pu | Line shunt susceptance at to-bus end in per-unit. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `ST` | integer | — | Branch status: 1=in-service, 0=out-of-service. Out-of-service branches are excluded from the admittance matrix. | 0–1 | no | 1 | Verify ST is one of {0, 1} and matches the source exactly |
| `MET` | integer | — | Metered end flag: 1=from-bus (I), 2=to-bus (J). Determines which end is used for loss allocation. | 1–2 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `LEN` | number | — | Line length in user-selected units. Informational field, not used in power flow calculations. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O1` | integer | — | Owner number 1. | 1–200 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `F1` | number | — | Fraction owned by owner 1. | 0.0–1.0 | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `O2` | integer | — | Owner number 2. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F2` | number | — | Fraction owned by owner 2. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O3` | integer | — | Owner number 3. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F3` | number | — | Fraction owned by owner 3. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O4` | integer | — | Owner number 4. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F4` | number | — | Fraction owned by owner 4. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |

### Worked Example

```
I:      30100
J:      30200
CKT:    "1 "
R:      0.00320
X:      0.03150
B:      0.52800
RATEA:  600.0
RATEB:  720.0
RATEC:  800.0
GI:     0.0
BI:     0.0
GJ:     0.0
BJ:     0.0
ST:     1
MET:    1
LEN:    0.0
O1:     3
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
```

### Nullable and Default Behavior

R and X have no default -- they must be provided for every branch. B defaults to 0.0 (no line charging), which is valid for short lines. Rating fields (RATEA, RATEB, RATEC) default to 0.0, meaning no thermal limit is enforced. GI, BI, GJ, BJ are line shunt elements that default to 0.0 (no shunt admittance at line ends). Owner fields O2-O4 default to 0.

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md#branch-impedance) for conversion formulas.
- See [Field Criticality Matrix](field-criticality-matrix.md) for DCPF-critical branch fields.
- See [Record-Type Mapping Guide](mapping-guide.md#branch) for tool-specific branch representations.

## Transformer

**Table name:** `transformer`
**Schema file:** [`../intermediate/schemas/transformer.schema.json`](../intermediate/schemas/transformer.schema.json)
**Primary key:** `[I, J, K, CKT]`
**Purpose:** Represents 2-winding and 3-winding power transformers. The PSS/E RAW format uses a multi-line record (up to 5 lines) that is flattened into a single row in the intermediate format. The CW/CZ/CM codes control how impedance and turns-ratio data are interpreted -- these must be preserved exactly.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Winding 1 (primary) bus number. | 10000–99999 | no | none | Verify I references a valid bus number in the bus table |
| `J` | integer | — | Winding 2 (secondary) bus number. | 10000–99999 | no | none | Verify J references a valid bus number in the bus table |
| `K` | integer | — | **[preservation-critical]** Winding 3 bus number. K=0 indicates a 2-winding transformer; K!=0 indicates a 3-winding transformer. This field determines the topology interpretation for all subsequent winding data. | 0 or valid bus number | no | 0 | MUST be preserved exactly; K=0 vs K!=0 changes transformer topology interpretation entirely; loss is a critical fidelity finding |
| `CKT` | string | — | Circuit identifier for parallel transformers. | — | no | `"1 "` | Verify CKT is preserved as a 2-character string including trailing space |
| `CW` | integer | — | **[preservation-critical]** Winding data I/O code controlling how WINDV1/2/3 are interpreted: 1=turns ratio in pu on bus base kV, 2=voltage in kV, 3=turns ratio in pu on nominal kV. | 1–3 | no | 1 | MUST be preserved exactly; CW determines the interpretation of all winding voltage/turns-ratio fields; loss corrupts impedance calculations |
| `CZ` | integer | — | **[preservation-critical]** Impedance data I/O code: 1=pu on system base, 2=pu on winding MVA/kV base, 3=ohms/kV load loss. | 1–3 | no | 1 | MUST be preserved exactly; CZ determines per-unit base for R and X fields |
| `CM` | integer | — | **[preservation-critical]** Magnetizing admittance I/O code: 1=pu on system base, 2=no-load loss/exciting current. | 1–2 | no | 1 | MUST be preserved exactly; CM determines interpretation of MAG1/MAG2 |
| `MAG1` | number | — | Magnetizing conductance or no-load loss, depending on CM. | — | yes | 0.0 | Verify MAG1 preserved to at least 5 decimal places |
| `MAG2` | number | — | Magnetizing susceptance or exciting current, depending on CM. | — | yes | 0.0 | Verify MAG2 preserved to at least 5 decimal places |
| `NMETR` | integer | — | Non-metered end code. | — | yes | 2 | If field is at PSS/E default (2), tool may omit — do not penalize |
| `NAME` | string | — | Transformer name, up to 12 characters. | — | yes | `"            "` | Verify NAME is preserved including trailing whitespace |
| `STAT` | integer | — | Transformer status: 0=out-of-service, 1=in-service, 2=winding 2 out, 3=winding 3 out, 4=winding 2 and 3 out. | 0–4 | no | 1 | Verify STAT is one of {0, 1, 2, 3, 4} and matches the source exactly |
| `O1` | integer | — | Owner number 1. | 1–200 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `F1` | number | — | Fraction by owner 1. | 0.0–1.0 | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `O2` | integer | — | Owner 2. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F2` | number | — | Fraction by owner 2. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O3` | integer | — | Owner 3. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F3` | number | — | Fraction by owner 3. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O4` | integer | — | Owner 4. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F4` | number | — | Fraction by owner 4. | 0.0–1.0 | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `VECGRP` | string | — | Vector group designation (12 chars). | — | yes | `"            "` | If field is at PSS/E default (blank), tool may omit — do not penalize |
| `R1_2` | number | pu | Resistance of winding 1–2 pair, interpretation depends on CZ. | 0.0–0.1 | no | 0.0 | Verify R1_2 preserved to at least 5 decimal places |
| `X1_2` | number | pu | Reactance of winding 1–2 pair, interpretation depends on CZ. | 0.01–0.5 | no | none | Verify X1_2 is non-zero for in-service transformers; verify preserved to at least 5 decimal places |
| `SBASE1_2` | number | MVA | MVA base for winding 1–2 impedance. | 50–2000 | no | 100.0 | Verify SBASE1_2 preserved to at least 1 decimal place |
| `R2_3` | number | pu | Resistance of winding 2–3 pair (3W only). | — | yes | 0.0 | Verify non-null when K != 0; if K=0, tool may omit |
| `X2_3` | number | pu | Reactance of winding 2–3 pair (3W only). | — | yes | 0.0 | Verify non-null when K != 0; if K=0, tool may omit |
| `SBASE2_3` | number | MVA | MVA base for winding 2–3 (3W only). | — | yes | 100.0 | Verify non-null when K != 0; if K=0, tool may omit |
| `R3_1` | number | pu | Resistance of winding 3–1 pair (3W only). | — | yes | 0.0 | Verify non-null when K != 0; if K=0, tool may omit |
| `X3_1` | number | pu | Reactance of winding 3–1 pair (3W only). | — | yes | 0.0 | Verify non-null when K != 0; if K=0, tool may omit |
| `SBASE3_1` | number | MVA | MVA base for winding 3–1 (3W only). | — | yes | 100.0 | Verify non-null when K != 0; if K=0, tool may omit |
| `VMSTAR` | number | pu | Star-point bus voltage magnitude for 3W transformers. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `ANSTAR` | number | deg | Star-point bus voltage angle for 3W transformers. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `WINDV1` | number | — | **[preservation-critical]** Winding 1 off-nominal turns ratio or voltage. Interpretation depends on CW code. | 0.9–1.1 (pu) or kV | no | 1.0 | MUST be preserved exactly to at least 5 decimal places; loss corrupts transformer model |
| `NOMV1` | number | kV | **[preservation-critical]** Winding 1 nominal voltage in kV. Used with CW=3 for turns ratio calculation. Must correspond to a standard transmission voltage class. | 69–500 | no | 0.0 | MUST be preserved exactly; verify drawn from standard kV classes |
| `ANG1` | number | deg | **[preservation-critical]** Winding 1 phase shift angle in degrees. Non-zero for phase-shifting transformers. | -180–180 | no | 0.0 | MUST be preserved exactly to at least 2 decimal places; non-zero ANG1 indicates phase-shifting transformer |
| `RATA1` | number | MVA | **[preservation-critical]** Winding 1 normal rating in MVA. | 50–2000 | no | 0.0 | MUST be preserved exactly to at least 1 decimal place |
| `RATB1` | number | MVA | Winding 1 emergency rating in MVA. | 50–3000 | yes | 0.0 | Verify RATB1 preserved to at least 1 decimal place |
| `RATC1` | number | MVA | Winding 1 long-term emergency rating in MVA. | 50–4000 | yes | 0.0 | Verify RATC1 preserved to at least 1 decimal place |
| `COD1` | integer | — | Winding 1 tap control mode code. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `CONT1` | integer | — | Winding 1 controlled bus number. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RMA1` | number | — | Winding 1 upper tap or voltage limit. | 0.9–1.1 | yes | 1.1 | Verify RMA1 preserved to at least 4 decimal places |
| `RMI1` | number | — | Winding 1 lower tap or voltage limit. | 0.9–1.1 | yes | 0.9 | Verify RMI1 preserved to at least 4 decimal places |
| `VMA1` | number | — | Winding 1 upper voltage limit for control. | 1.0–1.1 | yes | 1.1 | Verify VMA1 preserved to at least 4 decimal places |
| `VMI1` | number | — | Winding 1 lower voltage limit for control. | 0.9–1.0 | yes | 0.9 | Verify VMI1 preserved to at least 4 decimal places |
| `NTP1` | integer | — | Number of tap positions for winding 1. | 11–99 | yes | 33 | If field is at PSS/E default (33), tool may omit — do not penalize |
| `TAB1` | integer | — | Impedance correction table number for winding 1. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `CR1` | number | pu | Load drop compensation resistance for winding 1. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CX1` | number | pu | Load drop compensation reactance for winding 1. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CNXA1` | integer | — | Connection angle for winding 1. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `WINDV2` | number | — | **[preservation-critical]** Winding 2 off-nominal turns ratio or voltage. | 0.9–1.1 (pu) or kV | no | 1.0 | MUST be preserved exactly to at least 5 decimal places |
| `NOMV2` | number | kV | **[preservation-critical]** Winding 2 nominal voltage in kV. | 69–500 | no | 0.0 | MUST be preserved exactly; verify drawn from standard kV classes |
| `ANG2` | number | deg | Winding 2 phase shift angle in degrees. | -180–180 | yes | 0.0 | Verify ANG2 preserved to at least 2 decimal places |
| `RATA2` | number | MVA | **[preservation-critical]** Winding 2 normal rating in MVA. | 50–2000 | yes | 0.0 | MUST be preserved exactly to at least 1 decimal place |
| `RATB2` | number | MVA | Winding 2 emergency rating in MVA. | — | yes | 0.0 | Verify RATB2 preserved to at least 1 decimal place |
| `RATC2` | number | MVA | Winding 2 long-term emergency rating. | — | yes | 0.0 | Verify RATC2 preserved to at least 1 decimal place |
| `COD2` | integer | — | Winding 2 tap control mode code. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `CONT2` | integer | — | Winding 2 controlled bus number. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RMA2` | number | — | Winding 2 upper tap or voltage limit. | 0.9–1.1 | yes | 1.1 | Verify RMA2 preserved to at least 4 decimal places |
| `RMI2` | number | — | Winding 2 lower tap or voltage limit. | 0.9–1.1 | yes | 0.9 | Verify RMI2 preserved to at least 4 decimal places |
| `VMA2` | number | — | Winding 2 upper voltage limit for control. | 1.0–1.1 | yes | 1.1 | Verify VMA2 preserved to at least 4 decimal places |
| `VMI2` | number | — | Winding 2 lower voltage limit for control. | 0.9–1.0 | yes | 0.9 | Verify VMI2 preserved to at least 4 decimal places |
| `NTP2` | integer | — | Number of tap positions for winding 2. | 11–99 | yes | 33 | If field is at PSS/E default (33), tool may omit — do not penalize |
| `TAB2` | integer | — | Impedance correction table for winding 2. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `CR2` | number | pu | Load drop compensation resistance for winding 2. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CX2` | number | pu | Load drop compensation reactance for winding 2. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CNXA2` | integer | — | Connection angle for winding 2. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `WINDV3` | number | — | **[preservation-critical]** Winding 3 off-nominal turns ratio or voltage. Null/default for 2-winding transformers (K=0). | 0.9–1.1 (pu) or kV | yes | 1.0 | MUST be preserved exactly to at least 5 decimal places when K != 0; verify winding 3 fields are non-null when K != 0 |
| `NOMV3` | number | kV | **[preservation-critical]** Winding 3 nominal voltage in kV. Null/default for 2W transformers. | 69–500 | yes | 0.0 | MUST be preserved exactly when K != 0; verify drawn from standard kV classes |
| `ANG3` | number | deg | Winding 3 phase shift angle in degrees. | -180–180 | yes | 0.0 | Verify ANG3 preserved to at least 2 decimal places when K != 0 |
| `RATA3` | number | MVA | **[preservation-critical]** Winding 3 normal rating in MVA. | 50–2000 | yes | 0.0 | MUST be preserved exactly to at least 1 decimal place when K != 0 |
| `RATB3` | number | MVA | Winding 3 emergency rating. | — | yes | 0.0 | If K=0, tool may omit — do not penalize |
| `RATC3` | number | MVA | Winding 3 long-term emergency rating. | — | yes | 0.0 | If K=0, tool may omit — do not penalize |
| `COD3` | integer | — | Winding 3 tap control mode. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `CONT3` | integer | — | Winding 3 controlled bus. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RMA3` | number | — | Winding 3 upper tap/voltage limit. | — | yes | 1.1 | Verify RMA3 preserved to at least 4 decimal places when K != 0 |
| `RMI3` | number | — | Winding 3 lower tap/voltage limit. | — | yes | 0.9 | Verify RMI3 preserved to at least 4 decimal places when K != 0 |
| `VMA3` | number | — | Winding 3 upper voltage limit for control. | — | yes | 1.1 | Verify VMA3 preserved to at least 4 decimal places when K != 0 |
| `VMI3` | number | — | Winding 3 lower voltage limit for control. | — | yes | 0.9 | Verify VMI3 preserved to at least 4 decimal places when K != 0 |
| `NTP3` | integer | — | Number of tap positions for winding 3. | — | yes | 33 | If field is at PSS/E default (33), tool may omit — do not penalize |
| `TAB3` | integer | — | Impedance correction table for winding 3. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `CR3` | number | pu | Load drop compensation resistance for winding 3. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CX3` | number | pu | Load drop compensation reactance for winding 3. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CNXA3` | integer | — | Connection angle for winding 3. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |

### Worked Example

```
I:      30100
J:      30500
K:      0
CKT:    "1 "
CW:     1
CZ:     1
CM:     1
MAG1:   0.0
MAG2:   0.0
NMETR:  2
NAME:   "XF-230/69   "
STAT:   1
O1:     3
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
VECGRP: "            "
R1_2:   0.00250
X1_2:   0.12500
SBASE1_2: 200.0
R2_3:   0.0
X2_3:   0.0
SBASE2_3: 100.0
R3_1:   0.0
X3_1:   0.0
SBASE3_1: 100.0
VMSTAR: 1.0
ANSTAR: 0.0
WINDV1: 1.0125
NOMV1:  230.0
ANG1:   0.0
RATA1:  200.0
RATB1:  240.0
RATC1:  280.0
COD1:   0
CONT1:  0
RMA1:   1.1
RMI1:   0.9
VMA1:   1.1
VMI1:   0.9
NTP1:   33
TAB1:   0
CR1:    0.0
CX1:    0.0
CNXA1:  0
WINDV2: 1.0
NOMV2:  69.0
ANG2:   0.0
RATA2:  200.0
RATB2:  0.0
RATC2:  0.0
COD2:   0
CONT2:  0
RMA2:   1.1
RMI2:   0.9
VMA2:   1.1
VMI2:   0.9
NTP2:   33
TAB2:   0
CR2:    0.0
CX2:    0.0
CNXA2:  0
WINDV3: 1.0
NOMV3:  0.0
ANG3:   0.0
RATA3:  0.0
RATB3:  0.0
RATC3:  0.0
COD3:   0
CONT3:  0
RMA3:   1.1
RMI3:   0.9
VMA3:   1.1
VMI3:   0.9
NTP3:   33
TAB3:   0
CR3:    0.0
CX3:    0.0
CNXA3:  0
```

### Nullable and Default Behavior

K=0 indicates a 2-winding transformer; all winding-3 fields revert to defaults. The CW, CZ, CM codes default to 1 but are preservation-critical because they control how all impedance and turns-ratio fields are interpreted. WINDV1/WINDV2 default to 1.0 (unity turns ratio). NOMV1/NOMV2 default to 0.0, meaning the bus base kV is used. VMSTAR and ANSTAR are meaningful only for 3W transformers.

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md#transformer-impedance) for CW/CZ/CM conversions.
- See [3-Winding Transformer Reference](three-winding-transformers.md) for topology details.
- See [Field Criticality Matrix](field-criticality-matrix.md) for preservation-critical transformer fields.
- See [Record-Type Mapping Guide](mapping-guide.md#transformer) for tool-specific representations.

## Area

**Table name:** `area`
**Schema file:** [`../intermediate/schemas/area.schema.json`](../intermediate/schemas/area.schema.json)
**Primary key:** `[I]`
**Purpose:** Defines interchange control areas for the power flow solution. Each area has a slack bus, desired net interchange (export/import), and tolerance. Areas are the primary aggregation unit for balancing supply and demand.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Unique area number identifying this interchange control area. | 1–50 | no | none | Verify I is a positive integer preserved exactly |
| `ISW` | integer | — | **[preservation-critical]** Area slack bus number. The swing bus that absorbs area interchange mismatch. 0=no area slack bus specified. | 0 or valid bus number | no | 0 | MUST be preserved exactly; loss of area slack assignment corrupts area interchange control |
| `PDES` | number | MW | **[preservation-critical]** Desired net area interchange in MW. Positive=export, negative=import. | -5000–5000 | no | 0.0 | MUST be preserved exactly to at least 2 decimal places |
| `PTOL` | number | MW | **[preservation-critical]** Area interchange tolerance in MW. Convergence criterion for area interchange control. | 1.0–50.0 | no | 10.0 | MUST be preserved exactly to at least 1 decimal place |
| `ARNAME` | string | — | Area name, up to 12 characters. | — | no | `"            "` | Verify ARNAME is preserved including trailing whitespace |

### Worked Example

```
I:      5
ISW:    50200
PDES:   150.0
PTOL:   10.0
ARNAME: "SOUTH ZONE  "
```

### Nullable and Default Behavior

ISW=0 means no area slack bus is designated. PDES=0.0 means no net interchange target. PTOL=10.0 is the default interchange tolerance. All fields are required.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#area) for tool-specific area representations.

## Two-Terminal DC

**Table name:** `two_terminal_dc`
**Schema file:** [`../intermediate/schemas/two_terminal_dc.schema.json`](../intermediate/schemas/two_terminal_dc.schema.json)
**Primary key:** `[NAME]`
**Purpose:** Represents conventional line-commutated converter (LCC) HVDC links with a rectifier and inverter terminal. Each record contains DC line parameters plus full converter transformer and control data for both ends.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `NAME` | string | — | DC line name. | — | no | none | Verify NAME is preserved as a string including any trailing whitespace |
| `MDC` | integer | — | Control mode (0-2). | 0–2 | no | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RDC` | number | ohm | DC line resistance. | — | no | none | Verify RDC preserved to at least 4 decimal places |
| `SETVL` | number | — | Current or power demand. | — | no | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `VSCHD` | number | kV | Scheduled DC voltage. | — | no | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `VCMOD` | number | — | Mode switch DC voltage. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `RCOMP` | number | — | Compounding resistance. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `DELTI` | number | deg | Inverter firing angle margin. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `METER` | string | — | Metered end (R or I). | — | yes | `"I"` | If field is at PSS/E default (I), tool may omit — do not penalize |
| `DCVMIN` | number | pu | Min DC voltage. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `CCCITMX` | integer | — | Max converter ctrl iters. | — | yes | 20 | If field is at PSS/E default (20), tool may omit — do not penalize |
| `CCCACC` | number | — | Converter ctrl accel factor. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `IPR` | integer | — | Rectifier bus. | — | no | none | Verify IPR is a valid integer and matches the source |
| `NBR` | integer | — | Rectifier bridges. | — | no | none | Verify NBR is a valid integer and matches the source |
| `ANMXR` | number | deg | Max rect firing angle. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `ANMNR` | number | deg | Min rect firing angle. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `RCR` | number | — | Rect commutating R. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `XCR` | number | — | Rect commutating X. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `EBASR` | number | kV | Rect primary base kV. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `TRR` | number | — | Rect xfmr ratio. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `TAPR` | number | — | Rect tap setting. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `TMXR` | number | — | Max rect tap. | — | yes | 1.5 | If field is at PSS/E default (1.5), tool may omit — do not penalize |
| `TMNR` | number | — | Min rect tap. | — | yes | 0.51 | If field is at PSS/E default (0.51), tool may omit — do not penalize |
| `STPR` | number | — | Rect tap step. | — | yes | 0.00625 | If field is at PSS/E default (0.00625), tool may omit — do not penalize |
| `ICR` | integer | — | Rect firing angle ctrl bus. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `IFR` | integer | — | Rect commutating bus (from). | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `ITR` | integer | — | Rect commutating bus (to). | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `IDR` | string | — | Rect circuit ID. | — | yes | `"1 "` | If field is at PSS/E default (1 ), tool may omit — do not penalize |
| `XCAPR` | number | — | Rect capacitor reactance. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `IPI` | integer | — | Inverter bus. | — | no | none | Verify IPI is a valid integer and matches the source |
| `NBI` | integer | — | Inverter bridges. | — | no | none | Verify NBI is a valid integer and matches the source |
| `ANMXI` | number | deg | Max inv firing angle. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `ANMNI` | number | deg | Min inv firing angle. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `RCI` | number | — | Inv commutating R. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `XCI` | number | — | Inv commutating X. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `EBASI` | number | kV | Inv primary base kV. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `TRI` | number | — | Inv xfmr ratio. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `TAPI` | number | — | Inv tap setting. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `TMXI` | number | — | Max inv tap. | — | yes | 1.5 | If field is at PSS/E default (1.5), tool may omit — do not penalize |
| `TMNI` | number | — | Min inv tap. | — | yes | 0.51 | If field is at PSS/E default (0.51), tool may omit — do not penalize |
| `STPI` | number | — | Inv tap step. | — | yes | 0.00625 | If field is at PSS/E default (0.00625), tool may omit — do not penalize |
| `ICI` | integer | — | Inv firing angle ctrl bus. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `IFI` | integer | — | Inv commutating bus (from). | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `ITI` | integer | — | Inv commutating bus (to). | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `IDI` | string | — | Inv circuit ID. | — | yes | `"1 "` | If field is at PSS/E default (1 ), tool may omit — do not penalize |
| `XCAPI` | number | — | Inv capacitor reactance. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |

### Worked Example

```
NAME:    "PDCI_NORTH  "
MDC:     1
RDC:     12.5
SETVL:   1600.0
VSCHD:   500.0
VCMOD:   0.0
RCOMP:   0.0
DELTI:   0.0
METER:   "I"
DCVMIN:  0.0
CCCITMX: 20
CCCACC:  1.0
IPR:     60100
NBR:     2
ANMXR:   0.0
ANMNR:   0.0
RCR:     0.0
XCR:     0.0
EBASR:   0.0
TRR:     1.0
TAPR:    1.0
TMXR:    1.5
TMNR:    0.51
STPR:    0.00625
ICR:     0
IFR:     0
ITR:     0
IDR:     "1 "
XCAPR:   0.0
IPI:     60200
NBI:     2
ANMXI:   0.0
ANMNI:   0.0
RCI:     0.0
XCI:     0.0
EBASI:   0.0
TRI:     1.0
TAPI:    1.0
TMXI:    1.5
TMNI:    0.51
STPI:    0.00625
ICI:     0
IFI:     0
ITI:     0
IDI:     "1 "
XCAPI:   0.0
```

### Nullable and Default Behavior

Many fields have PSS/E defaults that represent 'not specified' or 'not applicable'. RDC has no default and must always be present. SETVL and VSCHD are operationally significant and should be preserved. Converter tap limits (TMXR, TMNR, etc.) have standard defaults.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#two-terminal-dc) for tool-specific HVDC representations.

## VSC DC

**Table name:** `vsc_dc`
**Schema file:** [`../intermediate/schemas/vsc_dc.schema.json`](../intermediate/schemas/vsc_dc.schema.json)
**Primary key:** `[NAME]`
**Purpose:** Represents voltage-source converter (VSC) HVDC links. More modern than LCC technology, with independent P and Q control at each converter. Each record contains DC line parameters and two converter specifications.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `NAME` | string | — | VSC DC line name. | — | no | none | Verify NAME is preserved as a string including any trailing whitespace |
| `MDC` | integer | — | Control mode. | — | no | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RDC` | number | ohm | DC line resistance. | — | no | none | Verify RDC preserved to at least 4 decimal places |
| `O1` | integer | — | Owner 1. | — | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `F1` | number | — | Fraction by owner 1. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `O2` | integer | — | Owner 2. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F2` | number | — | Fraction by owner 2. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O3` | integer | — | Owner 3. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F3` | number | — | Fraction by owner 3. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `O4` | integer | — | Owner 4. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `F4` | number | — | Fraction by owner 4. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `IBUS1` | integer | — | Converter 1 AC bus. | — | no | none | Verify IBUS1 is a valid integer and matches the source |
| `TYPE1` | integer | — | Converter 1 type. | — | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `MODE1` | integer | — | Converter 1 mode. | — | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `DCSET1` | number | — | Converter 1 DC setpoint. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `ACSET1` | number | — | Converter 1 AC setpoint. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `ALOSS1` | number | — | Converter 1 loss A. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `BLOSS1` | number | — | Converter 1 loss B. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `MINLOSS1` | number | — | Converter 1 min loss. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `SMAX1` | number | MVA | Converter 1 MVA rating. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `IMAX1` | number | A | Converter 1 current rating. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `PWF1` | number | — | Converter 1 power weight. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `MAXQ1` | number | MVAR | Converter 1 max Q. | — | yes | 9999.0 | If field is at PSS/E default (9999.0), tool may omit — do not penalize |
| `MINQ1` | number | MVAR | Converter 1 min Q. | — | yes | -9999.0 | If field is at PSS/E default (-9999.0), tool may omit — do not penalize |
| `REMOT1` | integer | — | Converter 1 remote bus. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RMPCT1` | number | % | Converter 1 MVAR pct. | — | yes | 100.0 | If field is at PSS/E default (100.0), tool may omit — do not penalize |
| `IBUS2` | integer | — | Converter 2 AC bus. | — | no | none | Verify IBUS2 is a valid integer and matches the source |
| `TYPE2` | integer | — | Converter 2 type. | — | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `MODE2` | integer | — | Converter 2 mode. | — | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `DCSET2` | number | — | Converter 2 DC setpoint. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `ACSET2` | number | — | Converter 2 AC setpoint. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `ALOSS2` | number | — | Converter 2 loss A. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `BLOSS2` | number | — | Converter 2 loss B. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `MINLOSS2` | number | — | Converter 2 min loss. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `SMAX2` | number | MVA | Converter 2 MVA rating. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `IMAX2` | number | A | Converter 2 current rating. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `PWF2` | number | — | Converter 2 power weight. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `MAXQ2` | number | MVAR | Converter 2 max Q. | — | yes | 9999.0 | If field is at PSS/E default (9999.0), tool may omit — do not penalize |
| `MINQ2` | number | MVAR | Converter 2 min Q. | — | yes | -9999.0 | If field is at PSS/E default (-9999.0), tool may omit — do not penalize |
| `REMOT2` | integer | — | Converter 2 remote bus. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `RMPCT2` | number | % | Converter 2 MVAR pct. | — | yes | 100.0 | If field is at PSS/E default (100.0), tool may omit — do not penalize |

### Worked Example

```
NAME:   "VSC_LINK_1  "
MDC:    1
RDC:    5.0
O1:     1
F1:     1.0
O2:     0
F2:     0.0
O3:     0
F3:     0.0
O4:     0
F4:     0.0
IBUS1:  70100
TYPE1:  1
MODE1:  1
DCSET1: 400.0
ACSET1: 1.0
ALOSS1: 0.0
BLOSS1: 0.0
MINLOSS1: 0.0
SMAX1:  500.0
IMAX1:  0.0
PWF1:   1.0
MAXQ1:  200.0
MINQ1:  -200.0
REMOT1: 0
RMPCT1: 100.0
IBUS2:  70200
TYPE2:  1
MODE2:  1
DCSET2: 0.0
ACSET2: 1.0
ALOSS2: 0.0
BLOSS2: 0.0
MINLOSS2: 0.0
SMAX2:  500.0
IMAX2:  0.0
PWF2:   1.0
MAXQ2:  200.0
MINQ2:  -200.0
REMOT2: 0
RMPCT2: 100.0
```

### Nullable and Default Behavior

Owner fields O2-O4 default to 0 (single ownership). Converter loss coefficients (ALOSS, BLOSS, MINLOSS) default to 0.0. SMAX and IMAX default to 0.0 meaning no limit. Q limits default to +/-9999.0.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#vsc-dc) for tool-specific VSC representations.

## Impedance Correction

**Table name:** `impedance_correction`
**Schema file:** [`../intermediate/schemas/impedance_correction.schema.json`](../intermediate/schemas/impedance_correction.schema.json)
**Primary key:** `[T]`
**Purpose:** Defines piecewise-linear impedance correction tables referenced by transformers (via TAB1/TAB2/TAB3). Each table maps tap ratio or phase angle to a correction factor applied to the transformer impedance.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `T` | integer | — | Correction table number. | — | no | none | Verify T is a valid integer and matches the source |
| `T1` | number | — | Tap ratio/angle pair 1. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F1` | number | — | Correction factor pair 1. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T2` | number | — | Tap ratio/angle pair 2. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F2` | number | — | Correction factor pair 2. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T3` | number | — | Tap ratio/angle pair 3. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F3` | number | — | Correction factor pair 3. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T4` | number | — | Tap ratio/angle pair 4. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F4` | number | — | Correction factor pair 4. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T5` | number | — | Tap ratio/angle pair 5. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F5` | number | — | Correction factor pair 5. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T6` | number | — | Tap ratio/angle pair 6. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F6` | number | — | Correction factor pair 6. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T7` | number | — | Tap ratio/angle pair 7. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F7` | number | — | Correction factor pair 7. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T8` | number | — | Tap ratio/angle pair 8. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F8` | number | — | Correction factor pair 8. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T9` | number | — | Tap ratio/angle pair 9. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F9` | number | — | Correction factor pair 9. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T10` | number | — | Tap ratio/angle pair 10. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F10` | number | — | Correction factor pair 10. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `T11` | number | — | Tap ratio/angle pair 11. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `F11` | number | — | Correction factor pair 11. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |

### Worked Example

```
T:   1
T1:  0.9
F1:  0.95
T2:  0.95
F2:  0.98
T3:  1.0
F3:  1.0
T4:  1.05
F4:  0.98
T5:  1.1
F5:  0.95
T6:  0.0
F6:  0.0
T7:  0.0
F7:  0.0
T8:  0.0
F8:  0.0
T9:  0.0
F9:  0.0
T10: 0.0
F10: 0.0
T11: 0.0
F11: 0.0
```

### Nullable and Default Behavior

T1-T11 and F1-F11 pairs define piecewise-linear correction curves. Unused pairs default to 0.0. The table is terminated by the first T value of 0.0.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#impedance-correction) for tool-specific representations.

## Multi-Terminal DC

**Table name:** `multi_terminal_dc`
**Schema file:** [`../intermediate/schemas/multi_terminal_dc.schema.json`](../intermediate/schemas/multi_terminal_dc.schema.json)
**Primary key:** `[NAME]`
**Purpose:** Header record for multi-terminal HVDC systems with more than two converters. Defines the number of converters, DC buses, and DC links in the system. Detailed converter/bus/link data follows in the PSS/E RAW file.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `NAME` | string | — | MT DC line name. | — | no | none | Verify NAME is preserved as a string including any trailing whitespace |
| `NCONV` | integer | — | Number of AC converters. | — | no | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `NDCBS` | integer | — | Number of DC buses. | — | no | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `NDCLN` | integer | — | Number of DC links. | — | no | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `MDC` | integer | — | Control mode. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `VCONV` | integer | — | DC voltage ctrl converter. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `VCMOD` | number | — | Mode switch DC voltage. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `VCONVN` | integer | — | New voltage ctrl converter. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |

### Worked Example

```
NAME:   "MTDC_SYS_1  "
NCONV:  3
NDCBS:  4
NDCLN:  3
MDC:    1
VCONV:  1
VCMOD:  0.0
VCONVN: 0
```

### Nullable and Default Behavior

NCONV, NDCBS, NDCLN define the structure of the multi-terminal DC system. These must be non-zero for a valid record. MDC defaults to 0. VCONV, VCMOD, VCONVN are control parameters with standard defaults.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#multi-terminal-dc) for tool-specific representations.

## Multi-Section Line

**Table name:** `multi_section_line`
**Schema file:** [`../intermediate/schemas/multi_section_line.schema.json`](../intermediate/schemas/multi_section_line.schema.json)
**Primary key:** `[I, J, ID]`
**Purpose:** Groups multiple branch records into a single multi-section transmission line. DUM1-DUM9 define intermediate bus numbers along the line. All sections share the same from-bus (I), to-bus (J), and line identifier (ID).

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | **[preservation-critical]** From bus number. | — | no | none | MUST be preserved exactly; loss of this field is a fidelity finding |
| `J` | integer | — | **[preservation-critical]** To bus number. | — | no | none | MUST be preserved exactly; loss of this field is a fidelity finding |
| `ID` | string | — | **[preservation-critical]** Line identifier. | — | no | `"1 "` | MUST be preserved exactly; loss of this field is a fidelity finding |
| `MET` | integer | — | Metered end flag. | 1–2 | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `DUM1` | integer | — | **[preservation-critical]** Intermediate bus 1. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM2` | integer | — | **[preservation-critical]** Intermediate bus 2. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM3` | integer | — | **[preservation-critical]** Intermediate bus 3. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM4` | integer | — | **[preservation-critical]** Intermediate bus 4. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM5` | integer | — | **[preservation-critical]** Intermediate bus 5. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM6` | integer | — | **[preservation-critical]** Intermediate bus 6. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM7` | integer | — | **[preservation-critical]** Intermediate bus 7. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM8` | integer | — | **[preservation-critical]** Intermediate bus 8. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `DUM9` | integer | — | **[preservation-critical]** Intermediate bus 9. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |

### Worked Example

```
I:    30100
J:    30400
ID:   "1 "
MET:  1
DUM1: 30150
DUM2: 30200
DUM3: 30250
DUM4: 0
DUM5: 0
DUM6: 0
DUM7: 0
DUM8: 0
DUM9: 0
```

### Nullable and Default Behavior

DUM1-DUM9 are intermediate bus numbers defining the multi-section line topology. DUM values of 0 indicate unused slots. At least DUM1 must be non-zero for a valid multi-section line grouping.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#multi-section-line) for tool-specific representations.

## Zone

**Table name:** `zone`
**Schema file:** [`../intermediate/schemas/zone.schema.json`](../intermediate/schemas/zone.schema.json)
**Primary key:** `[I]`
**Purpose:** Defines geographic or administrative zones for reporting and load allocation. Zones provide finer-grained grouping than areas. Each bus is assigned to exactly one zone.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Zone number. | — | no | none | Verify I is a valid integer and matches the source |
| `ZONAME` | string | — | Zone name (12 chars). | — | no | `"            "` | If field is at PSS/E default (            ), tool may omit — do not penalize |

### Worked Example

```
I:      12
ZONAME: "SOUTH BAY   "
```

### Nullable and Default Behavior

Both I and ZONAME are required. ZONAME defaults to blank (12 spaces). No fields are nullable.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#zone) for tool-specific zone representations.

## Interarea Transfer

**Table name:** `interarea_transfer`
**Schema file:** [`../intermediate/schemas/interarea_transfer.schema.json`](../intermediate/schemas/interarea_transfer.schema.json)
**Primary key:** `[ARFROM, ARTO, TRID]`
**Purpose:** Defines scheduled power transfers between interchange areas. Each transfer specifies a from-area, to-area, transfer ID, and scheduled MW amount.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `ARFROM` | integer | — | From area number. | — | no | none | Verify ARFROM is a valid integer and matches the source |
| `ARTO` | integer | — | To area number. | — | no | none | Verify ARTO is a valid integer and matches the source |
| `TRID` | string | — | Transfer ID (2 chars). | — | no | `"1 "` | If field is at PSS/E default (1 ), tool may omit — do not penalize |
| `PTRAN` | number | MW | Transfer amount. | — | no | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |

### Worked Example

```
ARFROM: 5
ARTO:   8
TRID:   "1 "
PTRAN:  200.0
```

### Nullable and Default Behavior

All fields are required. PTRAN defaults to 0.0 (no scheduled transfer). TRID defaults to '1 '.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#interarea-transfer) for tool-specific representations.

## Owner

**Table name:** `owner`
**Schema file:** [`../intermediate/schemas/owner.schema.json`](../intermediate/schemas/owner.schema.json)
**Primary key:** `[I]`
**Purpose:** Defines ownership entities referenced by buses, branches, generators, and transformers. Used for cost allocation and ownership tracking across the network.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Owner number. | — | no | none | Verify I is a valid integer and matches the source |
| `OWNAME` | string | — | Owner name (12 chars). | — | no | `"            "` | If field is at PSS/E default (            ), tool may omit — do not penalize |

### Worked Example

```
I:      3
OWNAME: "SOCAL EDISON"
```

### Nullable and Default Behavior

Both I and OWNAME are required. OWNAME defaults to blank (12 spaces). No fields are nullable.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#owner) for tool-specific owner representations.

## FACTS

**Table name:** `facts`
**Schema file:** [`../intermediate/schemas/facts.schema.json`](../intermediate/schemas/facts.schema.json)
**Primary key:** `[NAME]`
**Purpose:** Represents Flexible AC Transmission System devices including SVCs, STATCOMs, TCSCs, and UPFCs. Each device has control mode, setpoints, and impedance parameters.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `NAME` | string | — | FACTS device name. | — | no | none | Verify NAME is preserved as a string including any trailing whitespace |
| `I` | integer | — | Sending end bus. | — | no | none | Verify I is a valid integer and matches the source |
| `J` | integer | — | Terminal bus (0=shunt). | — | no | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `MODE` | integer | — | FACTS control mode. | — | no | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `SET1` | number | — | Control setpoint 1. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `SET2` | number | — | Control setpoint 2. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `VSREF` | number | pu | Series voltage reference. | — | yes | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `REMOT` | integer | — | Remote bus for V control. | — | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `MESSION` | number | — | Sending end impedance. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `LINX` | number | pu | Series reactance. | — | yes | 0.05 | If field is at PSS/E default (0.05), tool may omit — do not penalize |
| `RMPCT` | number | % | MVAR pct for remote reg. | — | yes | 100.0 | If field is at PSS/E default (100.0), tool may omit — do not penalize |
| `OWNER` | integer | — | Owner number. | — | yes | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `SET3` | number | — | Control setpoint 3. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |
| `SET4` | number | — | Control setpoint 4. | — | yes | 0.0 | If field is at PSS/E default (0.0), tool may omit — do not penalize |

### Worked Example

```
NAME:    "SVC_MESA    "
I:       30100
J:       0
MODE:    1
SET1:    1.0
SET2:    0.0
VSREF:   1.0
REMOT:   0
MESSION: 0.0
LINX:    0.05
RMPCT:   100.0
OWNER:   3
SET3:    0.0
SET4:    0.0
```

### Nullable and Default Behavior

J=0 indicates a shunt FACTS device (no terminal bus). MODE defaults to 1. SET1-SET4 are control setpoints with mode-dependent interpretations; they default to 0.0. VSREF defaults to 1.0 pu. LINX defaults to 0.05 pu.

### Cross-References

- See [Record-Type Mapping Guide](mapping-guide.md#facts) for tool-specific FACTS representations.

## Switched Shunt

**Table name:** `switched_shunt`
**Schema file:** [`../intermediate/schemas/switched_shunt.schema.json`](../intermediate/schemas/switched_shunt.schema.json)
**Primary key:** `[I]`
**Purpose:** Represents switchable shunt compensation with discrete step blocks. Each device has up to 8 blocks (N1-N8, B1-B8) defining the number of steps and MVAR per step. Control mode determines whether switching is discrete or continuous.

### Fields

| Field | Type | Unit | Semantic Description | Expected Range | Nullable | Default | Evaluate-Tool Guidance |
| ----- | ---- | ---- | -------------------- | -------------- | -------- | ------- | ---------------------- |
| `I` | integer | — | Bus number. | — | no | none | Verify I is a valid integer and matches the source |
| `MODSW` | integer | — | **[preservation-critical]** Control mode (0-2). | 0–2 | no | 1 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `ADJM` | integer | — | Adj method (0-1). | 0–1 | yes | 0 | If field is at PSS/E default (0), tool may omit — do not penalize |
| `STAT` | integer | — | Status (1=in, 0=out). | 0–1 | no | 1 | If field is at PSS/E default (1), tool may omit — do not penalize |
| `VSWHI` | number | pu | Ctrl voltage upper limit. | — | no | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `VSWLO` | number | pu | Ctrl voltage lower limit. | — | no | 1.0 | If field is at PSS/E default (1.0), tool may omit — do not penalize |
| `SWREM` | integer | — | **[preservation-critical]** Remote bus (0=local). | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `RMPCT` | number | % | MVAR pct for remote reg. | — | yes | 100.0 | If field is at PSS/E default (100.0), tool may omit — do not penalize |
| `RMIDNT` | string | — | Shunt name. | — | yes | `""` | If field is at PSS/E default (), tool may omit — do not penalize |
| `BINIT` | number | MVAR | **[preservation-critical]** Initial susceptance. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N1` | integer | — | **[preservation-critical]** Steps in block 1. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B1` | number | MVAR | **[preservation-critical]** Susceptance/step blk 1. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N2` | integer | — | **[preservation-critical]** Steps in block 2. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B2` | number | MVAR | **[preservation-critical]** Susceptance/step blk 2. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N3` | integer | — | **[preservation-critical]** Steps in block 3. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B3` | number | MVAR | **[preservation-critical]** Susceptance/step blk 3. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N4` | integer | — | **[preservation-critical]** Steps in block 4. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B4` | number | MVAR | **[preservation-critical]** Susceptance/step blk 4. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N5` | integer | — | **[preservation-critical]** Steps in block 5. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B5` | number | MVAR | **[preservation-critical]** Susceptance/step blk 5. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N6` | integer | — | **[preservation-critical]** Steps in block 6. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B6` | number | MVAR | **[preservation-critical]** Susceptance/step blk 6. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N7` | integer | — | **[preservation-critical]** Steps in block 7. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B7` | number | MVAR | **[preservation-critical]** Susceptance/step blk 7. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `N8` | integer | — | **[preservation-critical]** Steps in block 8. | — | no | 0 | MUST be preserved exactly; loss of this field is a fidelity finding |
| `B8` | number | MVAR | **[preservation-critical]** Susceptance/step blk 8. | — | no | 0.0 | MUST be preserved exactly; loss of this field is a fidelity finding |

### Worked Example

```
I:      42500
MODSW:  1
ADJM:   0
STAT:   1
VSWHI:  1.05
VSWLO:  0.95
SWREM:  0
RMPCT:  100.0
RMIDNT: ""
BINIT:  50.0
N1:     2
B1:     25.0
N2:     3
B2:     50.0
N3:     0
B3:     0.0
N4:     0
B4:     0.0
N5:     0
B5:     0.0
N6:     0
B6:     0.0
N7:     0
B7:     0.0
N8:     0
B8:     0.0
```

### Nullable and Default Behavior

N1-N8 and B1-B8 define discrete switching blocks. Unused blocks have N=0 and B=0.0. BINIT is the initial susceptance and should match the sum of switched-in blocks. MODSW defaults to 1 (discrete mode). SWREM=0 means local voltage control. RMIDNT is an optional name field that may be empty.

### Cross-References

- See [Per-Unit Convention Reference](per-unit-conventions.md#shunt-admittance) for BL sign convention.
- See [Record-Type Mapping Guide](mapping-guide.md#switched-shunt) for tool-specific representations.

## Appendix: Preservation-Critical Fields

Fields with `x-psse-preservation-critical: true` in the Phase 1 JSON Schema. These fields carry elevated fidelity requirements and generate mandatory test cases.

| Record Type | Field | Why Preservation-Critical |
| ----------- | ----- | ------------------------- |
| Generator | `IREG` | Remote regulated bus number |
| Transformer | `K` | Winding 3 bus number |
| Transformer | `CW` | Winding data I/O code controlling how WINDV1/2/3 are interpreted: 1=turns ratio in pu on bus base kV, 2=voltage in kV, 3=turns ratio in pu on nominal kV |
| Transformer | `CZ` | Impedance data I/O code: 1=pu on system base, 2=pu on winding MVA/kV base, 3=ohms/kV load loss |
| Transformer | `CM` | Magnetizing admittance I/O code: 1=pu on system base, 2=no-load loss/exciting current |
| Transformer | `WINDV1` | Winding 1 off-nominal turns ratio or voltage |
| Transformer | `NOMV1` | Winding 1 nominal voltage in kV |
| Transformer | `ANG1` | Winding 1 phase shift angle in degrees |
| Transformer | `RATA1` | Winding 1 normal rating in MVA |
| Transformer | `WINDV2` | Winding 2 off-nominal turns ratio or voltage |
| Transformer | `NOMV2` | Winding 2 nominal voltage in kV |
| Transformer | `RATA2` | Winding 2 normal rating in MVA |
| Transformer | `WINDV3` | Winding 3 off-nominal turns ratio or voltage |
| Transformer | `NOMV3` | Winding 3 nominal voltage in kV |
| Transformer | `RATA3` | Winding 3 normal rating in MVA |
| Area | `ISW` | Area slack bus number |
| Area | `PDES` | Desired net area interchange in MW |
| Area | `PTOL` | Area interchange tolerance in MW |
| Multi-Section Line | `I` | From bus number |
| Multi-Section Line | `J` | To bus number |
| Multi-Section Line | `ID` | Line identifier |
| Multi-Section Line | `DUM1` | Intermediate bus 1 |
| Multi-Section Line | `DUM2` | Intermediate bus 2 |
| Multi-Section Line | `DUM3` | Intermediate bus 3 |
| Multi-Section Line | `DUM4` | Intermediate bus 4 |
| Multi-Section Line | `DUM5` | Intermediate bus 5 |
| Multi-Section Line | `DUM6` | Intermediate bus 6 |
| Multi-Section Line | `DUM7` | Intermediate bus 7 |
| Multi-Section Line | `DUM8` | Intermediate bus 8 |
| Multi-Section Line | `DUM9` | Intermediate bus 9 |
| Switched Shunt | `MODSW` | Control mode (0-2) |
| Switched Shunt | `SWREM` | Remote bus (0=local) |
| Switched Shunt | `BINIT` | Initial susceptance |
| Switched Shunt | `N1` | Steps in block 1 |
| Switched Shunt | `B1` | Susceptance/step blk 1 |
| Switched Shunt | `N2` | Steps in block 2 |
| Switched Shunt | `B2` | Susceptance/step blk 2 |
| Switched Shunt | `N3` | Steps in block 3 |
| Switched Shunt | `B3` | Susceptance/step blk 3 |
| Switched Shunt | `N4` | Steps in block 4 |
| Switched Shunt | `B4` | Susceptance/step blk 4 |
| Switched Shunt | `N5` | Steps in block 5 |
| Switched Shunt | `B5` | Susceptance/step blk 5 |
| Switched Shunt | `N6` | Steps in block 6 |
| Switched Shunt | `B6` | Susceptance/step blk 6 |
| Switched Shunt | `N7` | Steps in block 7 |
| Switched Shunt | `B7` | Susceptance/step blk 7 |
| Switched Shunt | `N8` | Steps in block 8 |
| Switched Shunt | `B8` | Susceptance/step blk 8 |

## Appendix: Present-but-Inactive Fields

Fields with `x-psse-present-but-inactive: true` in the Phase 1 JSON Schema. These fields are uniformly at their default values across the entire dataset. Evaluate-tool should not penalize a tool for omitting or zeroing these fields.

| Record Type | Field | Default Value | Note |
| ----------- | ----- | ------------- | ---- |

## Appendix: Schema Cross-Reference Index

Lookup table mapping each JSON Schema file to its corresponding section in this document.

| Schema File | Document Section |
| ----------- | ---------------- |
| `../intermediate/schemas/bus.schema.json` | [## Bus](#bus) |
| `../intermediate/schemas/load.schema.json` | [## Load](#load) |
| `../intermediate/schemas/fixed_shunt.schema.json` | [## Fixed Shunt](#fixed-shunt) |
| `../intermediate/schemas/generator.schema.json` | [## Generator](#generator) |
| `../intermediate/schemas/branch.schema.json` | [## Branch](#branch) |
| `../intermediate/schemas/transformer.schema.json` | [## Transformer](#transformer) |
| `../intermediate/schemas/area.schema.json` | [## Area](#area) |
| `../intermediate/schemas/two_terminal_dc.schema.json` | [## Two-Terminal DC](#two-terminal-dc) |
| `../intermediate/schemas/vsc_dc.schema.json` | [## VSC DC](#vsc-dc) |
| `../intermediate/schemas/impedance_correction.schema.json` | [## Impedance Correction](#impedance-correction) |
| `../intermediate/schemas/multi_terminal_dc.schema.json` | [## Multi-Terminal DC](#multi-terminal-dc) |
| `../intermediate/schemas/multi_section_line.schema.json` | [## Multi-Section Line](#multi-section-line) |
| `../intermediate/schemas/zone.schema.json` | [## Zone](#zone) |
| `../intermediate/schemas/interarea_transfer.schema.json` | [## Interarea Transfer](#interarea-transfer) |
| `../intermediate/schemas/owner.schema.json` | [## Owner](#owner) |
| `../intermediate/schemas/facts.schema.json` | [## FACTS](#facts) |
| `../intermediate/schemas/switched_shunt.schema.json` | [## Switched Shunt](#switched-shunt) |
