# 3-Winding Transformer Reference

## Purpose

This document provides the authoritative reference for PSS/E v31 3-winding transformer records -- the most complex record type in the PSS/E data format. A single 3-winding transformer record spans 5 data lines and contains 83 fields, more than any other PSS/E record type by a factor of three. The document covers record structure, field semantics, star-bus equivalent topology, winding parameters, intermediate format representation, and tool-specific handling for all six evaluated power-system modeling tools. It complements the intermediate format schema reference (`intermediate-schema.md`, PRD 01) by providing topology and parametric detail specific to 3-winding transformers, references the per-unit convention reference (`per-unit-conventions.md`, PRD 03) for base conversion formulas, and extends the record-type mapping guide (`mapping-guide.md`, PRD 02) with detailed parametric treatment beyond the record-type-level summary.

## Audience

This document is written for evaluate-tool agents assessing FNM ingestion fidelity for 3-winding transformer records across six power-system modeling tools.

## PSS/E v31 Record Structure

### Overview

A 3-winding transformer record in PSS/E v31 is distinguished from a 2-winding transformer by having a nonzero third winding bus number (K != 0). The record spans 5 data lines and contains a total of 83 fields. The data lines are organized as follows:

- **Data Line 1** (21 fields): Bus identifiers, control codes, magnetizing admittance, status, ownership, and vector group
- **Data Line 2** (11 fields): Pairwise winding impedances (R and X for each winding pair) and star bus initial voltage
- **Data Line 3** (17 fields): Winding 1 (primary/HV) parameters -- tap ratio, ratings, tap changer control
- **Data Line 4** (17 fields): Winding 2 (secondary/MV) parameters -- tap ratio, ratings, tap changer control
- **Data Line 5** (17 fields): Winding 3 (tertiary/LV) parameters -- tap ratio, ratings, tap changer control

The 2-winding transformer (K=0) uses only 4 data lines and approximately 54 fields. This document covers only the 3-winding case.

### Data Line 1 -- Bus Identifiers, Impedances, and Admittance

Data Line 1 contains 21 fields that identify the three winding buses, specify control codes for impedance and tap interpretation, define magnetizing admittance, and provide status and ownership information.

| Field | Position | Type | Unit | Description |
|-------|----------|------|------|-------------|
| `I` | 1 | int | -- | Winding 1 (primary) bus number |
| `J` | 2 | int | -- | Winding 2 (secondary) bus number |
| `K` | 3 | int | -- | Winding 3 (tertiary) bus number; nonzero distinguishes 3-winding from 2-winding |
| `CKT` | 4 | str | -- | Circuit identifier (up to 2 characters) |
| `CW` | 5 | int | -- | Winding data I/O code: 1=pu of bus BASKV, 2=kV, 3=pu of NOMV |
| `CZ` | 6 | int | -- | Impedance data I/O code: 1=pu on winding base, 2=pu on system base, 3=losses in W |
| `CM` | 7 | int | -- | Magnetizing admittance I/O code: 1=pu on system base, 2=exciting current %/losses W |
| `MAG1` | 8 | float | CM-dependent | Magnetizing admittance component 1 (G if CM=1, exciting current % if CM=2) |
| `MAG2` | 9 | float | CM-dependent | Magnetizing admittance component 2 (B if CM=1, core losses in watts if CM=2) |
| `NMETR` | 10 | int | -- | Nonmetered end code: 1, 2, or 3 indicating which winding is nonmetered |
| `NAME` | 11 | str | -- | Transformer name (up to 12 characters) |
| `STAT` | 12 | int | -- | Status: 1=in-service (all windings), 2=winding 2 out, 3=winding 3 out, 4=winding 2&3 out, 0=all out |
| `O1` | 13 | int | -- | Owner 1 number |
| `F1` | 14 | float | -- | Owner 1 fraction (0.0 to 1.0) |
| `O2` | 15 | int | -- | Owner 2 number |
| `F2` | 16 | float | -- | Owner 2 fraction |
| `O3` | 17 | int | -- | Owner 3 number |
| `F3` | 18 | float | -- | Owner 3 fraction |
| `O4` | 19 | int | -- | Owner 4 number |
| `F4` | 20 | float | -- | Owner 4 fraction |
| `VECGRP` | 21 | str | -- | Vector group identifier (v31 addition, e.g., "YNyn0") |

### Data Line 2 -- Winding 1-2 and 2-3 and 3-1 Impedances

Data Line 2 contains 11 fields specifying the pairwise impedances between each pair of windings and the star bus initial voltage.

| Field | Position | Type | Unit | Description |
|-------|----------|------|------|-------------|
| `R1-2` | 1 | float | CZ-dependent | Resistance between windings 1 and 2 |
| `X1-2` | 2 | float | CZ-dependent | Reactance between windings 1 and 2 |
| `SBASE1-2` | 3 | float | MVA | MVA base for winding 1-2 impedance (used when CZ=1) |
| `R2-3` | 4 | float | CZ-dependent | Resistance between windings 2 and 3 |
| `X2-3` | 5 | float | CZ-dependent | Reactance between windings 2 and 3 |
| `SBASE2-3` | 6 | float | MVA | MVA base for winding 2-3 impedance (used when CZ=1) |
| `R3-1` | 7 | float | CZ-dependent | Resistance between windings 3 and 1 |
| `X3-1` | 8 | float | CZ-dependent | Reactance between windings 3 and 1 |
| `SBASE3-1` | 9 | float | MVA | MVA base for winding 3-1 impedance (used when CZ=1) |
| `VMSTAR` | 10 | float | pu | Star bus voltage magnitude initial value |
| `ANSTAR` | 11 | float | degrees | Star bus voltage angle initial value |

### Data Line 3 -- Winding 1 Parameters

Data Line 3 contains 17 fields specifying winding 1 (primary/HV) tap ratio, ratings, and tap changer control parameters.

| Field | Position | Type | Unit | Description |
|-------|----------|------|------|-------------|
| `WINDV1` | 1 | float | CW-dependent | Winding 1 tap ratio or voltage |
| `NOMV1` | 2 | float | kV | Winding 1 nominal voltage |
| `ANG1` | 3 | float | degrees | Winding 1 phase shift angle |
| `RATA1` | 4 | float | MVA | Winding 1 rate A (normal) MVA rating |
| `RATB1` | 5 | float | MVA | Winding 1 rate B (emergency) MVA rating |
| `RATC1` | 6 | float | MVA | Winding 1 rate C (short-term) MVA rating |
| `COD1` | 7 | int | -- | Winding 1 tap changer control mode code |
| `CONT1` | 8 | int | -- | Winding 1 controlled bus number |
| `RMA1` | 9 | float | CW-dependent | Winding 1 maximum tap ratio or angle |
| `RMI1` | 10 | float | CW-dependent | Winding 1 minimum tap ratio or angle |
| `VMA1` | 11 | float | pu or MVA | Winding 1 maximum voltage or flow limit |
| `VMI1` | 12 | float | pu or MVA | Winding 1 minimum voltage or flow limit |
| `NTP1` | 13 | int | -- | Winding 1 number of tap positions |
| `TAB1` | 14 | int | -- | Winding 1 impedance correction table number |
| `CR1` | 15 | float | pu | Winding 1 load drop compensation resistance |
| `CX1` | 16 | float | pu | Winding 1 load drop compensation reactance |
| `CNXA1` | 17 | float | degrees | Winding 1 connection angle for wye-delta transformers |

### Data Line 4 -- Winding 2 Parameters

Data Line 4 contains 17 fields specifying winding 2 (secondary/MV) tap ratio, ratings, and tap changer control parameters.

| Field | Position | Type | Unit | Description |
|-------|----------|------|------|-------------|
| `WINDV2` | 1 | float | CW-dependent | Winding 2 tap ratio or voltage |
| `NOMV2` | 2 | float | kV | Winding 2 nominal voltage |
| `ANG2` | 3 | float | degrees | Winding 2 phase shift angle |
| `RATA2` | 4 | float | MVA | Winding 2 rate A (normal) MVA rating |
| `RATB2` | 5 | float | MVA | Winding 2 rate B (emergency) MVA rating |
| `RATC2` | 6 | float | MVA | Winding 2 rate C (short-term) MVA rating |
| `COD2` | 7 | int | -- | Winding 2 tap changer control mode code |
| `CONT2` | 8 | int | -- | Winding 2 controlled bus number |
| `RMA2` | 9 | float | CW-dependent | Winding 2 maximum tap ratio or angle |
| `RMI2` | 10 | float | CW-dependent | Winding 2 minimum tap ratio or angle |
| `VMA2` | 11 | float | pu or MVA | Winding 2 maximum voltage or flow limit |
| `VMI2` | 12 | float | pu or MVA | Winding 2 minimum voltage or flow limit |
| `NTP2` | 13 | int | -- | Winding 2 number of tap positions |
| `TAB2` | 14 | int | -- | Winding 2 impedance correction table number |
| `CR2` | 15 | float | pu | Winding 2 load drop compensation resistance |
| `CX2` | 16 | float | pu | Winding 2 load drop compensation reactance |
| `CNXA2` | 17 | float | degrees | Winding 2 connection angle for wye-delta transformers |

### Data Line 5 -- Winding 3 Parameters

Data Line 5 contains 17 fields specifying winding 3 (tertiary/LV) tap ratio, ratings, and tap changer control parameters.

| Field | Position | Type | Unit | Description |
|-------|----------|------|------|-------------|
| `WINDV3` | 1 | float | CW-dependent | Winding 3 tap ratio or voltage |
| `NOMV3` | 2 | float | kV | Winding 3 nominal voltage |
| `ANG3` | 3 | float | degrees | Winding 3 phase shift angle |
| `RATA3` | 4 | float | MVA | Winding 3 rate A (normal) MVA rating |
| `RATB3` | 5 | float | MVA | Winding 3 rate B (emergency) MVA rating |
| `RATC3` | 6 | float | MVA | Winding 3 rate C (short-term) MVA rating |
| `COD3` | 7 | int | -- | Winding 3 tap changer control mode code |
| `CONT3` | 8 | int | -- | Winding 3 controlled bus number |
| `RMA3` | 9 | float | CW-dependent | Winding 3 maximum tap ratio or angle |
| `RMI3` | 10 | float | CW-dependent | Winding 3 minimum tap ratio or angle |
| `VMA3` | 11 | float | pu or MVA | Winding 3 maximum voltage or flow limit |
| `VMI3` | 12 | float | pu or MVA | Winding 3 minimum voltage or flow limit |
| `NTP3` | 13 | int | -- | Winding 3 number of tap positions |
| `TAB3` | 14 | int | -- | Winding 3 impedance correction table number |
| `CR3` | 15 | float | pu | Winding 3 load drop compensation resistance |
| `CX3` | 16 | float | pu | Winding 3 load drop compensation reactance |
| `CNXA3` | 17 | float | degrees | Winding 3 connection angle for wye-delta transformers |

### Field Count Summary

| Data Line | Field Count | Purpose |
|-----------|-------------|---------|
| 1 | 21 | Bus identifiers, control codes, admittance, status, ownership |
| 2 | 11 | Pairwise winding impedances and star bus voltage |
| 3 | 17 | Winding 1 (primary/HV) parameters |
| 4 | 17 | Winding 2 (secondary/MV) parameters |
| 5 | 17 | Winding 3 (tertiary/LV) parameters |
| **Total** | **83 fields** | All 3-winding transformer parameters |

## Star-Bus Equivalent Topology

### Concept

A 3-winding transformer with winding buses I, J, and K is electrically equivalent to three 2-winding transformers connected at a synthetic star bus S. The star bus is a zero-injection bus (no generation or load) located at the electrical center of the transformer. Each of the three equivalent 2-winding transformers connects one physical winding bus to the star bus, carrying its respective winding impedance, tap ratio, and phase angle. This decomposition is essential for tools that lack a native 3-winding transformer object and is the standard computational approach used during power flow solution even in tools that preserve the 3-winding parameterization in their data model.

### Textual Topology Diagram

```
              Bus I (Winding 1 / Primary / HV)
                |
                |  Z1, WINDV1, ANG1
                |
          Star Bus S (synthetic, VMSTAR/ANSTAR)
              / \
             /   \
            /     \
           /       \
     Z2,  /         \  Z3,
   WINDV2/           \WINDV3
   ANG2 /             \ANG3
       /               \
    Bus J             Bus K
  (Winding 2 /      (Winding 3 /
   Secondary /       Tertiary /
   MV)                LV)

  [MAG1, MAG2 placed on winding 1 branch (primary side)]
```

The diagram shows:
- **Bus I** (winding 1, primary, high voltage): connected to star bus via impedance Z1
- **Bus J** (winding 2, secondary, medium voltage): connected to star bus via impedance Z2
- **Bus K** (winding 3, tertiary, low voltage): connected to star bus via impedance Z3
- **Star Bus S** (synthetic, zero-injection): voltage initialized to `VMSTAR`/`ANSTAR`
- Three equivalent branches with per-winding impedances Z1, Z2, Z3, tap ratios WINDV1/WINDV2/WINDV3, and phase angles ANG1/ANG2/ANG3
- Magnetizing admittance (`MAG1`, `MAG2`) placed on the winding 1 (primary) branch

### Pairwise to Star-Leg Impedance Conversion

PSS/E stores pairwise impedances (Z1-2, Z2-3, Z3-1) measured between two windings with the third open-circuited. These must be converted to per-winding star-leg impedances (Z1, Z2, Z3) for the star-bus equivalent:

**All pairwise impedances must be on a common per-unit base before applying these formulas.** If `SBASE1-2`, `SBASE2-3`, and `SBASE3-1` differ, convert each to the system base first (see [Per-Unit Convention Reference](per-unit-conventions.md#three-winding-transformer-per-unit-bases)).

```
Z_1 = (Z_12 + Z_31 - Z_23) / 2
Z_2 = (Z_12 + Z_23 - Z_31) / 2
Z_3 = (Z_23 + Z_31 - Z_12) / 2
```

**Inverse (star to pairwise):**

```
Z_12 = Z_1 + Z_2
Z_23 = Z_2 + Z_3
Z_31 = Z_3 + Z_1
```

**Note on negative impedance:** In autotransformers, it is common for one of the star-leg impedances (typically Z3, the tertiary) to be negative. This is physically meaningful and indicates a magnetizing effect for that winding. A negative star-leg impedance does not indicate an error -- it is a mathematically valid result of the decomposition and must be preserved in the equivalent circuit.

### Star Bus Properties

- **Voltage magnitude:** `VMSTAR` (per-unit), typically initialized to 1.0
- **Voltage angle:** `ANSTAR` (degrees), typically initialized to 0.0
- **Bus type:** PQ (type 1) -- no generation or load at the star bus; it is a zero-injection node
- **Base voltage:** Determined by the transformer winding voltages; typically set to the winding 1 nominal voltage (NOMV1) or the bus I base voltage (BASKV of bus I)
- **Bus number convention:** Tools that create star buses assign bus numbers sequentially starting from `max_bus_number + 1` in the network

### Magnetizing Admittance Placement

The magnetizing admittance fields `MAG1` and `MAG2` represent the transformer core losses and magnetizing current. In PSS/E, these are referenced to the winding 1 (primary) bus voltage base.

In the star-bus equivalent circuit, the magnetizing admittance is placed on the winding 1 branch (between bus I and star bus S) as a shunt element at the from-bus (bus I) side. This is the convention used by MATPOWER's `psse2mpc` converter and most other tools that perform star-bus decomposition. Some tools (e.g., GridCal) may place the admittance at the star bus itself or distribute it differently, but the winding 1 branch placement is the most common convention.

The interpretation of `MAG1` and `MAG2` depends on the `CM` code:
- **CM=1:** `MAG1` = per-unit conductance (G) on system base, `MAG2` = per-unit susceptance (B) on system base
- **CM=2:** `MAG1` = exciting current as percentage of nominal current, `MAG2` = core losses in watts

## Winding Parameters

### Impedance Parameters

Each winding pair has its own resistance (R) and reactance (X) specified in Data Line 2:

- **`R1-2`, `X1-2`, `SBASE1-2`:** Impedance between winding 1 and winding 2, on `SBASE1-2` MVA base (when CZ=1)
- **`R2-3`, `X2-3`, `SBASE2-3`:** Impedance between winding 2 and winding 3, on `SBASE2-3` MVA base (when CZ=1)
- **`R3-1`, `X3-1`, `SBASE3-1`:** Impedance between winding 3 and winding 1, on `SBASE3-1` MVA base (when CZ=1)

The impedance interpretation depends on the `CZ` code:

| CZ Mode | R Interpretation | X Interpretation | Base |
|---------|-----------------|-----------------|------|
| CZ=1 | Per-unit resistance on winding MVA base | Per-unit reactance on winding MVA base | `SBASEn-m` |
| CZ=2 | Per-unit resistance on system base | Per-unit reactance on system base | `SBASE` (system) |
| CZ=3 | Load loss in watts | Per-unit reactance on winding base | Mixed |

**Base conversion (CZ=1 to system base):** Z_pu,system = Z_pu,winding \* (SBASE / SBASEn-m)

See [Per-Unit Convention Reference](per-unit-conventions.md#three-winding-transformer-per-unit-bases) for detailed conversion formulas and worked examples.

### Tap Ratios (WINDV1, WINDV2, WINDV3)

Each winding has its own tap ratio specified in the respective data line (3, 4, or 5). The tap ratio interpretation depends on the `CW` code:

| CW Mode | Interpretation | Conversion to per-unit of BASKV |
|---------|---------------|-------------------------------|
| CW=1 | Per-unit of bus BASKV | Already in target form |
| CW=2 | Actual kV | WINDV_pu = WINDV_kV / BASKV |
| CW=3 | Per-unit of NOMV | WINDV_pu = WINDV \* (NOMV / BASKV) |

The `CW` code applies uniformly to all three windings -- PSS/E does not allow different CW modes per winding within the same transformer record.

See [Per-Unit Convention Reference](per-unit-conventions.md#two-winding-transformer-tap-ratios) for conversion formulas.

### Phase Angles (ANG1, ANG2, ANG3)

Each winding has a phase shift angle specified in degrees:

- **`ANG1`:** Phase shift angle for winding 1, in degrees
- **`ANG2`:** Phase shift angle for winding 2, in degrees
- **`ANG3`:** Phase shift angle for winding 3, in degrees

Convention: a positive angle means the winding bus voltage leads the star bus voltage by that angle. For standard power transformers without phase shifting, ANG = 0.0 for all windings. Phase-shifting transformers typically have angles in the range -60 to +60 degrees.

### MVA Ratings (RATA/B/C per winding)

Each winding has three MVA rating levels:

| Rating | Winding 1 | Winding 2 | Winding 3 | Description |
|--------|-----------|-----------|-----------|-------------|
| Rate A | `RATA1` | `RATA2` | `RATA3` | Normal operating MVA rating |
| Rate B | `RATB1` | `RATB2` | `RATC2` | Emergency MVA rating |
| Rate C | `RATC1` | `RATC2` | `RATC3` | Short-term (extreme) MVA rating |

Ratings are per-winding, not per-transformer. Each winding may have a different MVA rating reflecting its physical capacity. The winding 1 (primary) typically has the highest rating.

`RATA` also serves as the per-winding MVA base for impedance normalization when `SBASE1-2` is zero (defaults to `RATA1` for winding 1-2 pair).

### Tap Changer Control Fields

Each winding has a full set of tap changer control fields:

| Field | Winding 1 | Winding 2 | Winding 3 | Description |
|-------|-----------|-----------|-----------|-------------|
| COD | `COD1` | `COD2` | `COD3` | Control mode code |
| CONT | `CONT1` | `CONT2` | `CONT3` | Controlled bus number |
| RMA | `RMA1` | `RMA2` | `RMA3` | Maximum tap ratio or angle |
| RMI | `RMI1` | `RMI2` | `RMI3` | Minimum tap ratio or angle |
| VMA | `VMA1` | `VMA2` | `VMA3` | Maximum voltage or flow limit |
| VMI | `VMI1` | `VMI2` | `VMI3` | Minimum voltage or flow limit |
| NTP | `NTP1` | `NTP2` | `NTP3` | Number of tap positions |
| TAB | `TAB1` | `TAB2` | `TAB3` | Impedance correction table number |
| CR | `CR1` | `CR2` | `CR3` | Load drop compensation resistance |
| CX | `CX1` | `CX2` | `CX3` | Load drop compensation reactance |
| CNXA | `CNXA1` | `CNXA2` | `CNXA3` | Connection angle for wye-delta transformers |

**COD mode values:**

| Code | Description |
|------|-------------|
| 0 | No tap changer control |
| 1 | Voltage control -- adjust tap to regulate `CONT` bus voltage |
| 2 | Reactive power flow control |
| 3 | Active power flow control |
| 4 | Control for HVDC converter transformer |
| -1 to -4 | Same as 1-4 but with step-up/step-down direction constraint |

### Magnetizing Admittance (MAG1, MAG2)

The magnetizing admittance is specified once per transformer (not per winding) in Data Line 1. Its interpretation depends on the `CM` code:

| CM Mode | MAG1 | MAG2 |
|---------|------|------|
| CM=1 | Per-unit conductance (G) on system MVA base | Per-unit susceptance (B) on system MVA base |
| CM=2 | Exciting current as % of nominal current | Core losses in watts |

The magnetizing admittance is referenced to winding 1 (primary) bus. In the star-bus equivalent, it is placed on the winding 1 branch as a shunt element.

## Intermediate Format Representation

### Single-Record Representation

If the canonical parser preserves the 3-winding transformer as a single record, the intermediate format represents each 3-winding transformer as one row in the `transformer` table with all 83 fields as columns. Fields are organized by data line origin:

- **Columns from Data Line 1:** `I`, `J`, `K`, `CKT`, `CW`, `CZ`, `CM`, `MAG1`, `MAG2`, `NMETR`, `NAME`, `STAT`, `O1`-`O4`, `F1`-`F4`, `VECGRP`
- **Columns from Data Line 2:** `R1-2`, `X1-2`, `SBASE1-2`, `R2-3`, `X2-3`, `SBASE2-3`, `R3-1`, `X3-1`, `SBASE3-1`, `VMSTAR`, `ANSTAR`
- **Columns from Data Lines 3-5:** Per-winding fields for windings 1, 2, and 3 (WINDV, NOMV, ANG, RATA/B/C, COD, CONT, RMA, RMI, VMA, VMI, NTP, TAB, CR, CX, CNXA)

This representation preserves maximum fidelity -- all 83 fields are directly accessible and no information is lost. Tools with native 3-winding objects (pandapower, GridCal) can map directly from this representation.

### Star-Bus Decomposition Representation

If the canonical parser decomposes to star-bus equivalents, the intermediate format represents each 3-winding transformer as:

- **Three 2-winding transformer records** in the `transformer` (or `branch`) table, one per winding, each connecting a physical winding bus (I, J, or K) to the synthetic star bus S
- **One synthetic star bus record** in the `bus` table

**Star bus numbering:** The star bus number is assigned sequentially starting from `max_bus_number + 1`. For example, if the network has buses numbered up to 50000, the first 3-winding transformer's star bus is 50001, the second is 50002, and so on.

**Branch records:** Each of the three 2-winding transformer branch records contains:
- From bus: physical winding bus (I, J, or K)
- To bus: star bus S
- Series impedance: star-leg impedance (Z1, Z2, or Z3) computed from pairwise impedances
- Tap ratio: per-winding tap ratio (WINDV1, WINDV2, or WINDV3)
- Phase angle: per-winding phase shift (ANG1, ANG2, or ANG3)
- MVA ratings: per-winding ratings (RATA/B/C for the respective winding)

**Fields preserved in decomposition:**
- Winding impedances (converted to star-leg values)
- Tap ratios (WINDV1, WINDV2, WINDV3)
- Phase angles (ANG1, ANG2, ANG3)
- MVA ratings (RATA/B/C per winding)
- Status (STAT, applied per-winding)

**Fields lost in decomposition:**
- Unified 3-winding record structure (K field, original pairwise impedances)
- Tap changer control modes and parameters (COD, CONT, NTP, TAB, CR, CX per winding)
- Impedance correction table references (TAB1, TAB2, TAB3)
- Ownership fields (O1-O4, F1-F4)
- Transformer name (NAME)
- Vector group (VECGRP)
- CW/CZ/CM control codes (implicitly consumed during conversion)
- Discrete tap step information (NTP, RMA, RMI)

**Pairwise to star-leg impedance conversion:** Before decomposition, all pairwise impedances must be converted to a common per-unit base. Then the star-leg formulas are applied (see "Pairwise to Star-Leg Impedance Conversion" above).

### Parser-Specific Behavior

**MATPOWER (Phase 1 D4):** The `psse2mpc` converter automatically decomposes all 3-winding transformers into three `mpc.branch` rows at phantom star buses. Star buses are numbered starting from `max_bus_number + 1`. Pairwise impedances are converted to star-leg impedances on the system base. Tap ratios and phase angles are preserved in the `TAP` and `SHIFT` columns. Control modes, ownership, name, and discrete tap data are lost. This is the default MATPOWER representation and cannot be overridden.

**GridCal (Phase 1 D5):** The GridCal PSS/E parser preserves the original 3-winding record structure as a `Transformer3W` object. All 83 fields are accessible through the object's attributes. Internally, GridCal computes the star-bus equivalent for power flow solution, but the user-facing data model retains the unified 3-winding parameterization. This provides maximum fidelity for round-trip data preservation.

## Tool Handling

### Summary Matrix

| Tool | Native 3W | Representation | Key Limitations |
|------|-----------|---------------|-----------------|
| PyPSA | No | Star-bus decomposition into three `Transformer` components | Loses unified 3W parameterization; no tap changer control fields |
| pandapower | Yes | `create_transformer3w()` with internal star bus | Full 3W support; parameter names differ from PSS/E |
| GridCal | Yes | `Transformer3W` object | Closest to PSS/E native representation; preserves all fields |
| PowerModels.jl | No | Star-bus decomposition into `branch` dict entries | Loses tap changer control modes and discrete tap data |
| PowerSimulations.jl | No | Per-winding `TapTransformer` or `Transformer2W` via PowerSystems.jl | No native `Transformer3W` type; requires decomposition |
| MATPOWER | No | `mpc.branch` rows at phantom star bus | Loses COD, CONT, NTP, TAB, CR, CX, ownership, NAME |

### PyPSA

PyPSA does not have a native 3-winding transformer object. The `Transformer` component is strictly 2-winding, defined by a from-bus (`bus0`) and to-bus (`bus1`) with tap ratio (`tap_ratio`) and phase shift (`phase_shift`).

To represent a 3-winding transformer in PyPSA:
1. Create a synthetic star `Bus` component with appropriate voltage level
2. Create three `Transformer` components connecting bus I to star bus, bus J to star bus, and bus K to star bus
3. Set `tap_ratio` and `phase_shift` on each component from the per-winding values
4. Compute star-leg impedances from pairwise impedances and assign to each component's `r` and `x` parameters

**Fields preserved:** Winding impedances (as star-leg values), tap ratios, phase angles, MVA ratings.

**Fields lost:** Unified 3-winding parameterization, tap changer control modes (COD), controlled bus (CONT), discrete tap positions (NTP), impedance correction tables (TAB), load drop compensation (CR, CX), ownership (O1-O4, F1-F4), name (NAME), vector group (VECGRP).

### pandapower

pandapower provides native 3-winding transformer support through `create_transformer3w()`. This function creates a single 3-winding transformer element with parameters mapped from the PSS/E fields:

| pandapower Parameter | PSS/E Source |
|---------------------|-------------|
| `hv_bus` | `I` (winding 1 bus) |
| `mv_bus` | `J` (winding 2 bus) |
| `lv_bus` | `K` (winding 3 bus) |
| `sn_hv_mva` | `RATA1` or `SBASE1-2` |
| `sn_mv_mva` | `RATA2` or `SBASE2-3` |
| `sn_lv_mva` | `RATA3` or `SBASE3-1` |
| `vn_hv_kv` | Bus I `BASKV` or `NOMV1` |
| `vn_mv_kv` | Bus J `BASKV` or `NOMV2` |
| `vn_lv_kv` | Bus K `BASKV` or `NOMV3` |
| `vk_hv_percent` | Derived from `X1-2` (% short-circuit voltage, HV-MV) |
| `vk_mv_percent` | Derived from `X2-3` (% short-circuit voltage, MV-LV) |
| `vk_lv_percent` | Derived from `X3-1` (% short-circuit voltage, LV-HV) |
| `vkr_hv_percent` | Derived from `R1-2` (% resistive component, HV-MV) |
| `vkr_mv_percent` | Derived from `R2-3` (% resistive component, MV-LV) |
| `vkr_lv_percent` | Derived from `R3-1` (% resistive component, LV-HV) |
| `tap_pos` | Derived from `WINDV1`/`WINDV2`/`WINDV3` |
| `tap_side` | Winding with active tap changer (from `COD1`/`COD2`/`COD3`) |
| `tap_step_percent` | Computed from tap range and NTP |

pandapower internally creates a star-bus decomposition for power flow computation, but this is transparent to the user. The 3-winding transformer data model preserves the unified parameterization.

**Fields that cannot be expressed:** Per-winding load drop compensation (CR, CX), impedance correction table references (TAB), vector group (VECGRP), detailed ownership fractions (O1-O4, F1-F4).

### GridCal

GridCal provides a native `Transformer3W` class that preserves all three windings as a single object. The GridCal PSS/E parser maps PSS/E 3-winding transformer records directly to `Transformer3W` instances, preserving the original record structure.

Key characteristics:
- All three winding impedances, tap ratios, and phase angles are stored as object attributes
- Internal star-bus computation is performed for power flow solution but is transparent
- The `Transformer3W` object is the closest representation to the PSS/E native format among all evaluated tools
- Tap changer control parameters are preserved at the object level

**Fields preserved:** All 83 fields are accessible through the object's attributes, including control modes, ownership, and vector group.

**Fields with limitations:** Some PSS/E-specific fields may be stored as generic metadata rather than typed attributes, depending on the GridCal version.

### PowerModels.jl

PowerModels.jl does not have a native 3-winding transformer object. The `parse_psse` function decomposes 3-winding transformers into three `branch` dictionary entries connected at a star bus:

- A star bus is added to the `bus` dictionary with bus type PQ and voltage initialized from `VMSTAR`/`ANSTAR`
- Three branch entries are created with per-winding impedances (star-leg values), tap ratios, and phase angles
- The `tap` field stores the off-nominal turns ratio (dimensionless)
- The `shift` field stores the phase angle in **radians** (note: PSS/E uses degrees)

**Fields preserved:** Winding impedances (as star-leg values), tap ratios (`tap`), phase angles (`shift`), MVA ratings (`rate_a`, `rate_b`, `rate_c`).

**Fields lost:** Tap changer control modes (COD, CONT), discrete tap positions (NTP), impedance correction tables (TAB), load drop compensation (CR, CX), ownership (O1-O4, F1-F4), name (NAME), vector group (VECGRP), original pairwise impedances.

### PowerSimulations.jl

PowerSimulations.jl delegates data modeling to PowerSystems.jl. As of the current version, PowerSystems.jl does not include a dedicated `Transformer3W` type. Three-winding transformers must be decomposed into per-winding representations:

- Each winding is represented as a `TapTransformer` (if it has a tap changer) or a `Transformer2W` equivalent
- A synthetic `ACBus` is created for the star bus
- Per-winding impedances, tap ratios, and phase angles are assigned to each component

**Fields preserved:** Winding impedances (as star-leg values), tap ratios, phase angles, MVA ratings.

**Fields lost:** Unified 3-winding parameterization, tap changer control modes beyond simple voltage regulation, discrete tap steps, impedance correction tables, load drop compensation, ownership, name, vector group.

### MATPOWER

MATPOWER's `psse2mpc` converter automatically decomposes 3-winding transformers into three `mpc.branch` matrix rows connected at a phantom star bus:

- **Phantom bus numbering:** Star buses are numbered starting from `max_bus_number + 1`. For example, if the largest bus number in the network is 50000, the first 3-winding transformer's star bus is 50001.
- **Branch columns:** Each of the three branch rows contains:
  - `F_BUS` / `T_BUS`: physical winding bus and star bus
  - `BR_R` / `BR_X`: star-leg resistance and reactance on system MVA base
  - `TAP`: per-winding tap ratio (off-nominal turns ratio)
  - `SHIFT`: per-winding phase shift angle in degrees
  - `RATE_A` / `RATE_B` / `RATE_C`: per-winding MVA ratings
  - `BR_STATUS`: branch status

**Fields lost in MATPOWER decomposition:**
- Tap changer control modes (`COD1`, `COD2`, `COD3`)
- Controlled bus references (`CONT1`, `CONT2`, `CONT3`)
- Number of tap positions (`NTP1`, `NTP2`, `NTP3`)
- Impedance correction table references (`TAB1`, `TAB2`, `TAB3`)
- Load drop compensation (`CR1`/`CX1`, `CR2`/`CX2`, `CR3`/`CX3`)
- Ownership fields (`O1`-`O4`, `F1`-`F4`)
- Transformer name (`NAME`)
- Vector group (`VECGRP`)
- Connection angles (`CNXA1`, `CNXA2`, `CNXA3`)
- Original pairwise impedances (replaced by star-leg values)

## Worked Example

### Source Parameters

A synthetic 500/230/115 kV autotransformer representative of bulk transmission infrastructure in the CAISO footprint:

- **Winding 1 (HV):** 500 kV nominal, 600 MVA rating
- **Winding 2 (MV):** 230 kV nominal, 300 MVA rating
- **Winding 3 (LV):** 115 kV nominal, 100 MVA rating
- **System base:** SBASE = 100 MVA

Pairwise impedances (CZ=1, on per-winding MVA base):
- Z1-2: R1-2 = 0.0012, X1-2 = 0.0856 pu on SBASE1-2 = 600 MVA
- Z2-3: R2-3 = 0.0028, X2-3 = 0.1245 pu on SBASE2-3 = 300 MVA
- Z3-1: R3-1 = 0.0019, X3-1 = 0.0934 pu on SBASE3-1 = 600 MVA

Tap ratios (CW=1): WINDV1 = 1.025, WINDV2 = 1.000, WINDV3 = 1.000

Control: COD1 = 1 (voltage control), CONT1 = 99999 (regulated bus)

Star bus initial voltage: VMSTAR = 1.0, ANSTAR = 0.0

### PSS/E Record Representation

**Data Line 1:**

```
99001, 99002, 99003, '1 ', 1, 1, 1, 0.00000, 0.00000, 2, '3W-EXAMPLE ', 1, 1, 1.0, 0, 1.0, 0, 1.0, 0, 1.0, 'YNyn0'
```

Fields: I=99001, J=99002, K=99003, CKT='1 ', CW=1, CZ=1, CM=1, MAG1=0.0, MAG2=0.0, NMETR=2, NAME='3W-EXAMPLE', STAT=1, O1=1, F1=1.0, O2=0, F2=1.0, O3=0, F3=1.0, O4=0, F4=1.0, VECGRP='YNyn0'

**Data Line 2:**

```
0.00120, 0.08560, 600.0, 0.00280, 0.12450, 300.0, 0.00190, 0.09340, 600.0, 1.00000, 0.00000
```

Fields: R1-2=0.0012, X1-2=0.0856, SBASE1-2=600.0, R2-3=0.0028, X2-3=0.1245, SBASE2-3=300.0, R3-1=0.0019, X3-1=0.0934, SBASE3-1=600.0, VMSTAR=1.0, ANSTAR=0.0

**Data Line 3 (Winding 1):**

```
1.02500, 500.000, 0.000, 600.00, 600.00, 600.00, 1, 99999, 1.10000, 0.90000, 1.10000, 0.90000, 33, 0, 0.00000, 0.00000, 0.00000
```

Fields: WINDV1=1.025, NOMV1=500.0, ANG1=0.0, RATA1=600.0, RATB1=600.0, RATC1=600.0, COD1=1, CONT1=99999, RMA1=1.1, RMI1=0.9, VMA1=1.1, VMI1=0.9, NTP1=33, TAB1=0, CR1=0.0, CX1=0.0, CNXA1=0.0

**Data Line 4 (Winding 2):**

```
1.00000, 230.000, 0.000, 300.00, 300.00, 300.00, 0, 0, 1.10000, 0.90000, 1.10000, 0.90000, 33, 0, 0.00000, 0.00000, 0.00000
```

Fields: WINDV2=1.0, NOMV2=230.0, ANG2=0.0, RATA2=300.0, RATB2=300.0, RATC2=300.0, COD2=0, CONT2=0, RMA2=1.1, RMI2=0.9, VMA2=1.1, VMI2=0.9, NTP2=33, TAB2=0, CR2=0.0, CX2=0.0, CNXA2=0.0

**Data Line 5 (Winding 3):**

```
1.00000, 115.000, 0.000, 100.00, 100.00, 100.00, 0, 0, 1.10000, 0.90000, 1.10000, 0.90000, 33, 0, 0.00000, 0.00000, 0.00000
```

Fields: WINDV3=1.0, NOMV3=115.0, ANG3=0.0, RATA3=100.0, RATB3=100.0, RATC3=100.0, COD3=0, CONT3=0, RMA3=1.1, RMI3=0.9, VMA3=1.1, VMI3=0.9, NTP3=33, TAB3=0, CR3=0.0, CX3=0.0, CNXA3=0.0

### Star-Bus Decomposition

Step 1 -- Convert pairwise impedances to system base (100 MVA):

Each pairwise impedance is on a different winding MVA base. Convert to system base using: Z_pu,system = Z_pu,winding \* (SBASE / SBASEn-m)

X1-2 on system base: X12_sys = 0.0856 \* (100 / 600) = 0.01427 pu

X2-3 on system base: X23_sys = 0.1245 \* (100 / 300) = 0.04150 pu

X3-1 on system base: X31_sys = 0.0934 \* (100 / 600) = 0.01557 pu

R1-2 on system base: R12_sys = 0.0012 \* (100 / 600) = 0.0002000 pu

R2-3 on system base: R23_sys = 0.0028 \* (100 / 300) = 0.0009333 pu

R3-1 on system base: R31_sys = 0.0019 \* (100 / 600) = 0.0003167 pu

Step 2 -- Apply star-leg impedance formulas:

X1 = (X12_sys + X31_sys - X23_sys) / 2 = (0.01427 + 0.01557 - 0.04150) / 2 = -0.005833 pu

X2 = (X12_sys + X23_sys - X31_sys) / 2 = (0.01427 + 0.04150 - 0.01557) / 2 = 0.02010 pu

X3 = (X23_sys + X31_sys - X12_sys) / 2 = (0.04150 + 0.01557 - 0.01427) / 2 = 0.02140 pu

R1 = (R12_sys + R31_sys - R23_sys) / 2 = (0.0002000 + 0.0003167 - 0.0009333) / 2 = -0.0002083 pu

R2 = (R12_sys + R23_sys - R31_sys) / 2 = (0.0002000 + 0.0009333 - 0.0003167) / 2 = 0.0004083 pu

R3 = (R23_sys + R31_sys - R12_sys) / 2 = (0.0009333 + 0.0003167 - 0.0002000) / 2 = 0.0005250 pu

Note: X1 and R1 are negative, which is typical for autotransformers where the primary and secondary windings are electrically connected (not magnetically isolated).

Step 3 -- Resulting 2-winding transformer records:

| Branch | From Bus | To Bus | R (pu) | X (pu) | TAP | SHIFT | RATA (MVA) |
|--------|----------|--------|--------|--------|-----|-------|------------|
| Winding 1 | 99001 (I) | 50001 (Star) | -0.0002083 | -0.005833 | 1.025 | 0.0 | 600.0 |
| Winding 2 | 99002 (J) | 50001 (Star) | 0.0004083 | 0.02010 | 1.000 | 0.0 | 300.0 |
| Winding 3 | 99003 (K) | 50001 (Star) | 0.0005250 | 0.02140 | 1.000 | 0.0 | 100.0 |

Step 4 -- Star bus parameters:

Star bus 50001: VM = 1.0 pu (VMSTAR), VA = 0.0 degrees (ANSTAR), type = PQ (1)

### Numeric Verification

Verify that pairwise impedances can be reconstructed from star-leg impedances (all on system base):

**Z1-2 verification:**

X1 + X2 = -0.005833 + 0.02010 = 0.01427 pu (matches X12_sys = 0.01427 pu)

R1 + R2 = -0.0002083 + 0.0004083 = 0.0002000 pu (matches R12_sys = 0.0002000 pu)

**Z2-3 verification:**

X2 + X3 = 0.02010 + 0.02140 = 0.04150 pu (matches X23_sys = 0.04150 pu)

R2 + R3 = 0.0004083 + 0.0005250 = 0.0009333 pu (matches R23_sys = 0.0009333 pu)

**Z3-1 verification:**

X3 + X1 = 0.02140 + (-0.005833) = 0.01557 pu (matches X31_sys = 0.01557 pu)

R3 + R1 = 0.0005250 + (-0.0002083) = 0.0003167 pu (matches R31_sys = 0.0003167 pu)

All six reconstructed values match the converted pairwise impedances to 4 significant digits, confirming the star-bus decomposition is consistent.

## Common Pitfalls

1. **Per-unit base mismatch:** Each winding pair has its own MVA base (SBASE1-2, SBASE2-3, SBASE3-1). All three pairwise impedances must be converted to a common base (typically system MVA base) before applying the star-leg decomposition formulas. Failing to do this produces incorrect star-leg impedances and wrong power flow results.

2. **Star bus voltage initialization:** Forgetting to set VMSTAR and ANSTAR initial values for the star bus can cause power flow convergence problems. The star bus voltage should be initialized to reasonable values (typically 1.0 pu and 0.0 degrees).

3. **Negative star-leg impedance:** One or more star-leg impedances (Z1, Z2, or Z3) can be negative, particularly for autotransformers. This is physically meaningful and must be preserved in the equivalent circuit. Tools that reject negative impedance values will fail to model these transformers correctly.

4. **Tap changer loss in decomposition:** Tools that decompose 3-winding transformers into star-bus equivalents lose the tap changer control mode fields (COD, CONT, NTP, TAB, CR, CX). This means automatic voltage regulation and power flow control by tap changers cannot be modeled at the individual winding level after decomposition.

5. **Rating interpretation:** RATA, RATB, and RATC are per-winding MVA ratings, not per-transformer totals. Each winding has its own thermal capacity. Using a single transformer-level rating would understate the capacity of smaller windings and overstate the capacity of the tertiary.

6. **Magnetizing admittance placement:** In the star-bus equivalent, the magnetizing admittance (MAG1, MAG2) must be placed on the correct branch (winding 1 / primary side). Placing it on the wrong branch or distributing it equally across all three branches produces incorrect no-load loss and magnetizing current representation.

7. **CW/CZ/CM mode inconsistency:** PSS/E enforces a single CW, CZ, and CM code per transformer record (applying to all windings uniformly). However, when constructing transformer data manually or converting between formats, it is possible to inadvertently apply different interpretation modes to different windings. The CW, CZ, and CM codes must be checked and applied consistently to all three windings.

## Cross-References

- **Phase 1 D6 -- Parser Fidelity Comparison:** Documents parser-specific 3-winding transformer handling, including star-bus decomposition details and field preservation differences between MATPOWER and GridCal parsers.
- **Phase 2 PRD 01 -- Intermediate Format Schema Reference:** Provides field definitions, data types, and nullable status for all transformer table columns. See `intermediate-schema.md`.
- **Phase 2 PRD 03 -- Per-Unit Convention Reference, Section 6:** Covers 3-winding transformer per-unit bases, per-winding MVA bases, and impedance base conversion formulas. See [per-unit-conventions.md](per-unit-conventions.md#three-winding-transformer-per-unit-bases).
- **Phase 2 PRD 05 -- Field Criticality Matrix:** Classifies each of the 83 3-winding transformer fields by criticality tier (DCPF-critical, ACPF-critical, informational, discardable). See `field-criticality-matrix.md`.
