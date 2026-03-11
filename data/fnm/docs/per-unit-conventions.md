# Per-Unit Convention Reference

## Purpose

This document provides the authoritative reference for every per-unit base and convention used in the FNM intermediate format. It covers nine convention domains -- from system MVA base through load representation -- documenting the base definitions, conversion formulas, worked examples with realistic transmission-scale values, and common pitfalls when ingesting PSS/E-derived network data into each of the six evaluated power-system modeling tools. This document complements the intermediate format schema reference (PRD 01) by specifying how per-unit quantities are normalized and converted, rather than what each field means semantically.

## Audience

This document is written for evaluate-tool agents assessing FNM ingestion fidelity across six power-system modeling tools (MATPOWER, pandapower, PyPSA, GridCal, PowerModels.jl, PowerSimulations.jl).

## Notation Conventions

The following mathematical notation is used throughout this document:

- `S_base`: system MVA base (PSS/E field `SBASE`), in MVA
- `V_base`: bus base voltage (PSS/E field `BASKV`), in kV
- `Z_base`: base impedance in ohms = V_base^2 / S_base
- `Y_base`: base admittance in siemens = S_base / V_base^2
- `I_base`: base current in amperes = S_base / (sqrt(3) \* V_base)
- Subscript notation for winding-specific bases: `S_base,w1` for winding-1 MVA base, `Z_base,w1` for winding-1 impedance base
- `RATA` or `RATAn`: winding MVA rating for winding n of a transformer
- All per-unit quantities are dimensionless ratios of actual value to base value

## 1. System MVA Base (SBASE)

### Definition

The system MVA base (`S_base`) is the power base used to normalize all per-unit quantities in the power system. It is a single scalar value that applies system-wide. In PSS/E v31, `SBASE` is specified in the case identification (header) record and defaults to 100.0 MVA. The FNM intermediate format uses the canonical value of **100 MVA**.

All per-unit impedances, admittances, and power quantities in the intermediate format are referenced to this base unless explicitly stated otherwise (e.g., transformer winding-base quantities).

### Source in Intermediate Format

The system MVA base is stored in the case header metadata. The intermediate format schema field `SBASE` (from the PSS/E header record) carries this value. Every record type that contains per-unit quantities implicitly references this base.

### Worked Example

Given `S_base` = 100 MVA:

**Per-unit to physical (MW):**
A generator producing P_pu = 3.50 per-unit active power corresponds to:

P_MW = P_pu \* S_base = 3.50 \* 100 = 350.0 MW

**Physical to per-unit:**
A load consuming 275.0 MW corresponds to:

P_pu = P_MW / S_base = 275.0 / 100 = 2.750 per-unit

Round-trip confirmation: 2.750 \* 100 = 275.0 MW (matches original).

### Common Pitfalls

1. **Base mismatch errors:** If a tool internally uses a different system MVA base (e.g., 1000 MVA), all imported per-unit impedances and admittances will be scaled incorrectly. The symptom is that all per-unit values are off by a factor of S_base_tool / S_base_FNM.

2. **Tool-specific conventions:**
   - **MATPOWER** stores the system base in `mpc.baseMVA`. If this field is not set to 100, all branch and generator per-unit values are misinterpreted. MATPOWER's internal convention matches the PSS/E convention (100 MVA default).
   - **pandapower** uses `net.sn_mva` as the system base. When creating a network from PSS/E data, pandapower sets `sn_mva` from the PSS/E header. If the user creates a network manually with a different `sn_mva`, impedance values will be inconsistent.
   - **PyPSA** uses `network.sn_mva` (default 1.0 MVA in older versions). If not explicitly set to 100, all per-unit quantities imported from the FNM will be scaled by a factor of 100. This is the most common PyPSA ingestion error.
   - **GridCal** stores the system base in `MultiCircuit.Sbase`. The default is 100 MVA, matching the FNM.
   - **PowerModels.jl** expects `baseMVA` in the network data dictionary. The PSS/E parser sets this automatically.
   - **PowerSimulations.jl** inherits the base from its PowerSystems.jl data model, which reads `baseMVA` from the source data.

3. **Diagnostic signature:** All per-unit impedances in the tool's output are consistently scaled by a constant factor relative to the FNM values. For example, if the tool uses S_base=1.0 instead of 100, all impedances will appear 100x larger.

4. **Correction formula:** Z_pu,new = Z_pu,old \* (S_base,old / S_base,new)

## 2. Bus Base Voltage (BASKV)

### Definition

The bus base voltage (`V_base`) is the nominal voltage at each bus, specified in kV. In PSS/E v31, this is the `BASKV` field in the Bus Data record. It defines the per-unit voltage reference for that bus: a per-unit voltage of 1.0 corresponds to exactly `BASKV` kV.

Each bus has its own `BASKV` value. Buses at the same nominal voltage level share the same `BASKV` (e.g., all 230 kV buses have BASKV = 230.0). The `BASKV` value also determines the impedance base for branches connected to that bus.

### Source in Intermediate Format

The intermediate format stores `BASKV` as a field in the Bus record table. It is a required, non-nullable field with unit kV and per-unit base classification `bus_kv`.

### Voltage Per-Unit Conversion

**Per-unit to physical:**

V_kV = V_pu \* BASKV

**Physical to per-unit:**

V_pu = V_kV / BASKV

### Worked Example

A 345 kV bus with `BASKV` = 345.0 kV and measured voltage `VM` = 1.035 per-unit:

**Per-unit to physical:**

V_kV = 1.035 \* 345.0 = 357.075 kV

**Physical to per-unit:**

V_pu = 357.075 / 345.0 = 1.0350 per-unit

Round-trip confirmation: 1.0350 \* 345.0 = 357.075 kV (matches original).

A 138 kV bus with `BASKV` = 138.0 kV and measured voltage `VM` = 0.982 per-unit:

V_kV = 0.982 \* 138.0 = 135.516 kV

### Common Pitfalls

1. **Base mismatch errors:** If a tool assigns an incorrect `BASKV` to a bus (e.g., confusing the bus nominal voltage with the winding nominal voltage NOMV of a connected transformer), all impedance calculations for branches at that bus will use the wrong Z_base. The symptom is impedances scaled by (BASKV_wrong / BASKV_correct)^2.

2. **Tool-specific conventions:**
   - **MATPOWER** stores bus base voltage in `mpc.bus(:, BASE_KV)`. If this column is zero or missing, MATPOWER may default to 1.0, causing catastrophic impedance base errors.
   - **pandapower** stores the bus voltage in `net.bus.vn_kv`. The field name differs from PSS/E's `BASKV` but the semantics are identical.
   - **PyPSA** stores bus voltage in `network.buses.v_nom` (in kV). This must match `BASKV` for correct per-unit interpretation.
   - **GridCal** stores bus nominal voltage in `Bus.Vnom` (in kV).
   - **PowerModels.jl** stores bus base voltage in `bus["base_kv"]`. The PSS/E parser maps `BASKV` directly.
   - **PowerSimulations.jl** stores it via PowerSystems.jl `Bus.base_voltage` (in kV).

3. **Diagnostic signature:** If `BASKV` is wrong for a subset of buses, only branches connected to those buses will show impedance errors. The error factor is (BASKV_actual / BASKV_assigned)^2.

4. **Correction formula:** Z_base_correct = BASKV_correct^2 / S_base; Z_pu_corrected = Z_pu_original \* (BASKV_wrong^2 / BASKV_correct^2)

## 3. Branch (AC Line) Impedance

### Base Impedance Formula

For AC branches (non-transformer lines), the impedance base is determined by the from-bus `BASKV` and the system `SBASE`:

Z_base = BASKV_from^2 / SBASE (ohms)

Y_base = SBASE / BASKV_from^2 (siemens)

For branches where both ends are at the same voltage level (the normal case for AC lines), it does not matter which bus is designated as "from" or "to."

### Per-Unit to Physical

R_ohm = R_pu \* Z_base

X_ohm = X_pu \* Z_base

B_siemens = B_pu \* Y_base

### Physical to Per-Unit

R_pu = R_ohm / Z_base

X_pu = X_ohm / Z_base

B_pu = B_siemens / Y_base

### Intermediate Format Fields

| Field Name | Unit in Intermediate Format | Per-Unit Base | Description |
|------------|---------------------------|---------------|-------------|
| `R` | per-unit | S_base, BASKV_from | Branch resistance |
| `X` | per-unit | S_base, BASKV_from | Branch reactance |
| `B` | per-unit | S_base, BASKV_from | Total line charging susceptance |
| `RATEA` | MVA | none (physical) | Rate A (normal) thermal rating |
| `RATEB` | MVA | none (physical) | Rate B (emergency) thermal rating |
| `RATEC` | MVA | none (physical) | Rate C (short-term) thermal rating |

### Worked Example

A 230 kV transmission line with `SBASE` = 100 MVA and `BASKV_from` = 230.0 kV:

Z_base = 230.0^2 / 100 = 52900 / 100 = 529.0 ohms

Y_base = 100 / 230.0^2 = 100 / 52900 = 0.001890 siemens

Given per-unit values: R_pu = 0.00450, X_pu = 0.03800, B_pu = 0.08400

**Per-unit to physical:**

R_ohm = 0.00450 \* 529.0 = 2.3805 ohms

X_ohm = 0.03800 \* 529.0 = 20.1020 ohms

B_siemens = 0.08400 \* 0.001890 = 0.00015876 siemens = 158.76 microsiemens

**Physical to per-unit:**

R_pu = 2.3805 / 529.0 = 0.004500 per-unit

X_pu = 20.1020 / 529.0 = 0.03800 per-unit

B_pu = 0.00015876 / 0.001890 = 0.08400 per-unit

Round-trip confirmation: all values match originals to 4 significant digits.

### Common Pitfalls

1. **Base mismatch errors:** Using the wrong bus `BASKV` in the impedance base formula produces impedances scaled by (BASKV_wrong / BASKV_correct)^2. For example, using 345 kV instead of 230 kV inflates the impedance base by (345/230)^2 = 2.25, making all per-unit values appear 2.25x smaller.

2. **Tool-specific conventions:**
   - **MATPOWER** stores branch impedance in `mpc.branch(:, [BR_R BR_X BR_B])` in per-unit on the system base, matching the intermediate format directly.
   - **pandapower** stores line parameters in physical units (ohms/km and nF/km in `net.line`) but uses per-unit on system base for the internal power flow model. The conversion happens internally during `runpp()`.
   - **PyPSA** stores line impedance in per-unit on the system base in `network.lines[["r", "x", "b"]]`, directly matching the intermediate format convention.
   - **GridCal** stores branch impedance in per-unit on the system base, matching the intermediate format.
   - **PowerModels.jl** stores branch impedance in per-unit on system base in `branch["br_r"]`, `branch["br_x"]`, `branch["br_b"]`, matching the intermediate format.
   - **PowerSimulations.jl** uses PowerSystems.jl `Line` objects with `r` and `x` in per-unit on system base.

3. **Diagnostic signature:** If line charging `B` is stored as total line charging but a tool expects half-line charging (B/2 per side in the pi-model), all `B` values will differ by a factor of 2. Check whether the tool's internal model uses total B or B/2.

4. **Correction formula:** If B_total vs B_half mismatch: B_tool = B_intermediate / 2 (for tools expecting per-side B).

## 4. Two-Winding Transformer Impedance

Transformer impedance in PSS/E v31 can be specified in three modes, controlled by the `CZ` code in the transformer data record. The intermediate format must handle all three modes and convert to a canonical representation.

### CZ=1: Per-Unit on Winding Base

When CZ=1, transformer impedance (R1-2, X1-2) is specified in per-unit on the winding MVA base and winding kV base:

Z_base,winding = BASKV_winding^2 / (RATA \* SBASE_winding) (ohms)

where `RATA` is the winding MVA rating (from the transformer record) and `SBASE_winding` is the winding-level MVA base. In PSS/E, when CZ=1, the impedance base MVA is `SBASE1-2` (from the transformer data record), not the system `SBASE`.

The per-unit impedance on winding base is:

Z_pu,winding = Z_ohm / Z_base,winding

### CZ=2: Per-Unit on System Base, Winding kV

When CZ=2, transformer impedance is specified in per-unit on the system MVA base (`SBASE`) and winding kV base:

Z_base = BASKV_winding^2 / SBASE (ohms)

This is the most straightforward representation and is directly comparable to branch impedance. The only difference from branch impedance is that the kV base may differ on each side of the transformer.

### CZ=3: Losses in Watts, Impedance in Per-Unit

When CZ=3, R1-2 is specified as load loss in watts (CU, copper loss), and X1-2 is specified in per-unit on the winding MVA base:

R_pu = CU / (1000 \* SBASE1-2) (converting watts to per-unit on winding base)

X_pu on winding base is given directly.

### Conversion Between CZ Modes

**CZ=1 to CZ=2:**

Z_pu,system = Z_pu,winding \* (SBASE / SBASE1-2)

This scales the per-unit value from winding base to system base.

**CZ=2 to CZ=1:**

Z_pu,winding = Z_pu,system \* (SBASE1-2 / SBASE)

**CZ=3 to CZ=1:**

R_pu,winding = CU_watts / (1000 \* SBASE1-2)

X_pu,winding is already on winding base (given directly in CZ=3).

**CZ=3 to CZ=2:**

R_pu,system = CU_watts / (1000 \* SBASE) = R_pu,winding \* (SBASE / SBASE1-2)

X_pu,system = X_pu,winding \* (SBASE / SBASE1-2)

### Intermediate Format Canonical Representation

The intermediate format stores transformer impedance as parsed from the PSS/E file with the original `CZ` code preserved. The `CZ` field in the Transformer record indicates which convention applies. Tools must check `CZ` and convert to their internal convention during ingestion. This approach preserves maximum fidelity and avoids premature conversion that could introduce rounding errors.

### Worked Example

A 230/115 kV, 200 MVA two-winding transformer with `SBASE` = 100 MVA and `SBASE1-2` = 200 MVA.

Parameters: R1-2 = 0.00350 pu, X1-2 = 0.12500 pu (on winding base, CZ=1).

**CZ=1 representation (winding base):**

Z_base,winding = 230.0^2 / 200 = 52900 / 200 = 264.5 ohms

R_ohm = 0.00350 \* 264.5 = 0.9258 ohms

X_ohm = 0.12500 \* 264.5 = 33.0625 ohms

**CZ=1 to CZ=2 conversion (pu to physical and back on system base):**

R_pu,system = 0.00350 \* (100 / 200) = 0.001750 pu on system base

X_pu,system = 0.12500 \* (100 / 200) = 0.06250 pu on system base

Verify via physical values:

Z_base,system = 230.0^2 / 100 = 529.0 ohms

R_pu,system = 0.9258 / 529.0 = 0.001750 pu (matches)

X_pu,system = 33.0625 / 529.0 = 0.06250 pu (matches)

**CZ=3 representation:**

CU (load loss) = R_pu,winding \* 1000 \* SBASE1-2 = 0.00350 \* 1000 \* 200 = 700.0 watts

X1-2 = 0.12500 pu on winding base (same as CZ=1)

**Physical to per-unit round-trip (CZ=2):**

R_pu = 0.9258 / 529.0 = 0.001750 pu on system base

R_ohm = 0.001750 \* 529.0 = 0.9258 ohms (matches original)

### Common Pitfalls

1. **Base mismatch errors:** The most common transformer ingestion error is applying system-base impedance formulas to winding-base values (or vice versa). If a tool assumes CZ=2 but the data is CZ=1, all transformer impedances will be off by a factor of SBASE / SBASE1-2. For a 200 MVA transformer on a 100 MVA system base, impedances will be scaled by 0.5.

2. **Tool-specific conventions:**
   - **MATPOWER** stores all transformer impedance on the system base (CZ=2 equivalent) in `mpc.branch(:, [BR_R BR_X])`. Its PSS/E importer converts from CZ=1 or CZ=3 to system base automatically. If using a custom importer, this conversion must be done explicitly.
   - **pandapower** stores transformer impedance as percentage short-circuit voltage (`vk_percent`) and percentage resistive component (`vkr_percent`) referenced to the rated MVA (`sn_mva`). Conversion: `vk_percent = Z_pu,winding \* 100`, `vkr_percent = R_pu,winding \* 100`, where the per-unit is on the transformer's rated MVA base.
   - **PyPSA** stores transformer impedance in per-unit on the system base (CZ=2 equivalent) in `network.transformers[["r", "x"]]`. The user must convert from CZ=1 before importing.
   - **GridCal** stores transformer impedance in per-unit on the system base, equivalent to CZ=2.
   - **PowerModels.jl** converts all transformer data to per-unit on system base during PSS/E parsing. Internally, transformers are stored in the branch data structure.
   - **PowerSimulations.jl** (via PowerSystems.jl) stores transformer impedance on system base.

3. **Diagnostic signature:** All transformer impedances are off by a consistent ratio equal to SBASE / SBASE1-2 (the ratio of system base to transformer rated MVA). If SBASE = 100 and the transformer is rated at 500 MVA, the factor is 0.2. This ratio varies per transformer (since each has a different rating), so the error pattern is a per-transformer scaling rather than a uniform scaling.

4. **Correction formula:**
   - CZ=1 to CZ=2: Z_pu,system = Z_pu,winding \* (SBASE / SBASE1-2)
   - CZ=2 to CZ=1: Z_pu,winding = Z_pu,system \* (SBASE1-2 / SBASE)
   - CZ=3 to CZ=2: R_pu,system = CU_watts / (1000 \* SBASE); X_pu,system = X_pu,winding \* (SBASE / SBASE1-2)

## 5. Two-Winding Transformer Tap Ratios

Transformer tap ratios in PSS/E v31 are specified in three modes, controlled by the `CW` code. The tap ratio determines the off-nominal turns ratio which affects voltage transformation and power flow through the transformer.

### CW=1: Per-Unit of Winding Bus BASKV

When CW=1, `WINDV1` and `WINDV2` are specified in per-unit of the winding bus `BASKV`:

WINDV = tap_kV / BASKV

A value of 1.0 means the tap is at the nominal position (tap voltage equals bus base voltage). Values above 1.0 indicate a tap position above nominal.

### CW=2: Tap in kV

When CW=2, `WINDV1` and `WINDV2` are specified directly in kV:

WINDV = tap_kV (actual winding voltage in kV)

To obtain the per-unit tap ratio: tap_pu = WINDV / BASKV

### CW=3: Per-Unit of Nominal Winding Voltage (NOMV)

When CW=3, `WINDV1` and `WINDV2` are specified in per-unit of the winding nominal voltage `NOMV`:

WINDV = tap_kV / NOMV

where `NOMV1` and `NOMV2` are the nominal winding voltages specified in the transformer data record. `NOMV` may differ from `BASKV` if the winding nominal voltage differs from the bus nominal voltage.

To convert to CW=1: tap_pu_BASKV = WINDV \* (NOMV / BASKV)

### Conversion Between CW Modes

**CW=2 to CW=1:**

WINDV_pu = WINDV_kV / BASKV

**CW=3 to CW=1:**

WINDV_pu = WINDV_NOMV \* (NOMV / BASKV)

**CW=1 to CW=2:**

WINDV_kV = WINDV_pu \* BASKV

**CW=1 to CW=3:**

WINDV_NOMV = WINDV_pu \* (BASKV / NOMV)

### Off-Nominal Tap Ratio

The off-nominal tap ratio `t` is the effective turns ratio seen by the power flow model. For a transformer from bus i to bus j:

t = WINDV1 / WINDV2 (when both are in per-unit of their respective BASKV, i.e., CW=1)

If WINDV2 = 1.0 (common convention), then t = WINDV1.

The off-nominal tap ratio modifies the transformer admittance model. In the pi-equivalent circuit, the series admittance is scaled by 1/t and the shunt admittances include t-dependent terms.

### Phase-Shifting Angle (ANG)

The phase-shifting angle `ANG` (in degrees) represents the phase shift introduced by the transformer. Convention:

- Positive `ANG` means the winding-1 (from-bus) voltage leads the winding-2 (to-bus) voltage by `ANG` degrees
- `ANG` = 0 for standard power transformers (no phase shift)
- Typical phase-shifter angles range from -60 to +60 degrees

The complex tap ratio is: t_complex = t \* exp(j \* ANG \* pi / 180)

### Intermediate Format Canonical Representation

The intermediate format stores `WINDV1`, `WINDV2`, `ANG1`, `NOMV1`, `NOMV2`, and `CW` as parsed from the PSS/E file. The `CW` code indicates which tap convention applies. Tools must convert to their internal tap representation during ingestion.

### Worked Example

A 230/115 kV transformer with tap at 1.05 per-unit on the high side:

`BASKV` (bus 1) = 230.0 kV, `BASKV` (bus 2) = 115.0 kV

**CW=1 representation:**

WINDV1 = 1.05 (pu of 230.0 kV), WINDV2 = 1.00 (pu of 115.0 kV)

tap_kV_1 = 1.05 \* 230.0 = 241.5 kV

tap_kV_2 = 1.00 \* 115.0 = 115.0 kV

Off-nominal tap ratio: t = 1.05 / 1.00 = 1.05

**CW=2 representation:**

WINDV1 = 241.5 kV, WINDV2 = 115.0 kV

Per-unit to physical and back: WINDV1_pu = 241.5 / 230.0 = 1.0500 (matches original CW=1)

**CW=3 representation (with NOMV1 = 230.0, NOMV2 = 115.0):**

WINDV1 = 241.5 / 230.0 = 1.05 (pu of NOMV1), WINDV2 = 115.0 / 115.0 = 1.00 (pu of NOMV2)

When NOMV = BASKV, CW=3 is identical to CW=1.

**Phase shifter example:**

A phase-shifting transformer with ANG = 5.0 degrees:

t_complex = 1.05 \* exp(j \* 5.0 \* pi / 180) = 1.05 \* (cos(5.0 deg) + j \* sin(5.0 deg))

t_complex = 1.05 \* (0.9962 + j \* 0.08716) = 1.0460 + j \* 0.09152

**Physical to per-unit round-trip:**

Starting from 241.5 kV: V_pu = 241.5 / 230.0 = 1.0500 pu

Back to physical: V_kV = 1.0500 \* 230.0 = 241.50 kV (matches original)

### Common Pitfalls

1. **Base mismatch errors:** Confusing NOMV (winding nominal voltage) with BASKV (bus base voltage) when CW=3. If NOMV differs from BASKV (e.g., a 230/115 kV bus with NOMV1=220 kV), the tap ratio will be scaled by NOMV/BASKV = 220/230 = 0.9565. The symptom is that all transformer tap ratios at that voltage level are off by a consistent factor.

2. **Tool-specific conventions:**
   - **MATPOWER** stores the tap ratio as the off-nominal turns ratio `t` in `mpc.branch(:, TAP)` on the from-side. A value of 0 means t=1 (no off-nominal tap). The phase shift angle is stored in `mpc.branch(:, SHIFT)` in degrees.
   - **pandapower** represents taps using `tap_pos` (integer tap position), `tap_step_percent` (voltage change per tap step), and `tap_neutral` (neutral tap position). The per-unit tap ratio is: t = 1 + (tap_pos - tap_neutral) \* tap_step_percent / 100. This is fundamentally different from the PSS/E WINDV representation.
   - **PyPSA** stores tap ratio as `tap_ratio` (dimensionless, equivalent to t) and phase shift as `phase_shift` (degrees) in the transformers table. `tap_ratio` = 1.0 means nominal.
   - **GridCal** stores the tap ratio as a per-unit value in the transformer model, similar to CW=1.
   - **PowerModels.jl** stores tap ratio in `branch["tap"]` as the off-nominal ratio on the from-side and shift angle in `branch["shift"]` in radians (not degrees). The radian/degree conversion is a common source of error.
   - **PowerSimulations.jl** (via PowerSystems.jl) stores tap as a per-unit ratio.

3. **Diagnostic signature:** If tap ratios are off by a factor, voltage profiles on the secondary side of all transformers will show a consistent bias. For example, if taps are interpreted as CW=2 (kV) when they are CW=1 (per-unit), a tap of 1.05 pu will be misread as 1.05 kV, producing nonsensical results.

4. **Correction formula:**
   - CW=2 to CW=1: WINDV_pu = WINDV_kV / BASKV
   - CW=3 to CW=1: WINDV_pu = WINDV_NOMV \* (NOMV / BASKV)
   - Degree to radian (for PowerModels.jl): shift_rad = ANG_deg \* pi / 180

## 6. Three-Winding Transformer Per-Unit Bases

Three-winding transformers have independent MVA and impedance bases for each winding. PSS/E v31 stores pairwise impedances (between winding pairs) which must be decomposed into per-winding (star-bus) impedances for most tool representations. Full topology and connection details are documented in Phase 2 PRD 04.

### Per-Winding MVA Base

Each winding has its own MVA rating:

- Winding 1: `RATA1` (or `SBASE` if RATA1 = 0)
- Winding 2: `RATA2` (or `SBASE` if RATA2 = 0)
- Winding 3: `RATA3` (or `SBASE` if RATA3 = 0)

The per-winding MVA base `S_base,wn` is used for winding-specific impedance normalization when CZ=1.

### Per-Winding Impedance Base

The impedance base for each winding pair depends on the CZ mode:

For CZ=1 (winding base):

Z_base,12 = BASKV_w1^2 / SBASE1-2 (for winding 1-2 impedance)

Z_base,23 = BASKV_w2^2 / SBASE2-3 (for winding 2-3 impedance)

Z_base,31 = BASKV_w3^2 / SBASE3-1 (for winding 3-1 impedance)

For CZ=2 (system base):

Z_base,12 = BASKV_w1^2 / SBASE

Z_base,23 = BASKV_w2^2 / SBASE

Z_base,31 = BASKV_w3^2 / SBASE

### Star-Bus Impedance Distribution

PSS/E stores pairwise impedances (Z12, Z23, Z31) which represent the impedance measured between two windings with the third open-circuited. To convert to per-winding (star-equivalent) impedances:

Z1 = (Z12 + Z31 - Z23) / 2

Z2 = (Z12 + Z23 - Z31) / 2

Z3 = (Z23 + Z31 - Z12) / 2

The star-bus impedances Z1, Z2, Z3 are the impedances from each winding to the virtual star point. This decomposition is used by tools that model three-winding transformers as three two-winding transformers connected at a star bus.

Inverse (star to pairwise):

Z12 = Z1 + Z2

Z23 = Z2 + Z3

Z31 = Z3 + Z1

### Worked Example

A 500/230/115 kV autotransformer with per-winding ratings:

- Winding 1: 500 kV, RATA1 = 600 MVA
- Winding 2: 230 kV, RATA2 = 300 MVA
- Winding 3: 115 kV, RATA3 = 100 MVA
- SBASE = 100 MVA

Pairwise impedances on winding base (CZ=1):

R12 = 0.00200, X12 = 0.08500 pu on SBASE1-2 = 600 MVA

R23 = 0.00350, X23 = 0.14000 pu on SBASE2-3 = 300 MVA

R31 = 0.00400, X31 = 0.11000 pu on SBASE3-1 = 100 MVA

**Convert pairwise to system base (CZ=2):**

X12_system = 0.08500 \* (100 / 600) = 0.01417 pu

X23_system = 0.14000 \* (100 / 300) = 0.04667 pu

X31_system = 0.11000 \* (100 / 100) = 0.11000 pu

**Star-bus decomposition (on system base):**

X1 = (0.01417 + 0.11000 - 0.04667) / 2 = 0.03875 pu

X2 = (0.01417 + 0.04667 - 0.11000) / 2 = -0.02458 pu

X3 = (0.04667 + 0.11000 - 0.01417) / 2 = 0.07125 pu

Note: X2 is negative, which is physically meaningful for autotransformers and indicates that winding 2 has a magnetizing effect.

**Physical impedance values (winding 1):**

Z_base,w1 = 500.0^2 / 100 = 2500.0 ohms

X1_ohm = 0.03875 \* 2500.0 = 96.875 ohms

**Per-unit to physical and back:**

X1_pu = 96.875 / 2500.0 = 0.03875 pu (matches original)

### Common Pitfalls

1. **Base mismatch errors:** Each winding pair has a different MVA base (SBASE1-2, SBASE2-3, SBASE3-1). If a tool converts all three pairwise impedances using the same MVA base, the star-bus decomposition will be incorrect. The symptom is that the star impedances Z1, Z2, Z3 have incorrect magnitudes and the power flow solution shows voltage errors at the three-winding transformer buses.

2. **Tool-specific conventions:**
   - **MATPOWER** does not natively support three-winding transformers. They must be decomposed into three two-winding transformers connected at a virtual star bus. The MATPOWER PSS/E importer performs this decomposition automatically.
   - **pandapower** supports three-winding transformers via `create_transformer3w()`. Parameters include per-winding short-circuit voltages (`vk_hv_percent`, `vk_mv_percent`, `vk_lv_percent`) referenced to each winding's rated MVA. The naming convention (HV/MV/LV) must be mapped correctly to PSS/E winding 1/2/3.
   - **PyPSA** does not have native three-winding transformer support. Three-winding transformers must be manually decomposed into three two-winding transformers with a virtual star bus.
   - **GridCal** supports three-winding transformers internally and can handle the star-bus decomposition.
   - **PowerModels.jl** decomposes three-winding transformers into three branches at a star bus during PSS/E import.
   - **PowerSimulations.jl** (via PowerSystems.jl) handles three-winding transformers through decomposition into two-winding equivalents.

3. **Diagnostic signature:** If pairwise impedances are not converted to a common base before star-bus decomposition, the resulting Z1, Z2, Z3 values will be inconsistent. The most visible symptom is that the sum Z12_reconstructed = Z1 + Z2 does not equal the original Z12 after base conversion. The error ratio differs by winding pair, scaled by the ratio of the winding MVA bases.

4. **Correction formula:** Always convert all pairwise impedances to the same MVA base (typically system base) before performing star-bus decomposition:
   Z_pu,system = Z_pu,winding \* (SBASE / SBASEn-m)

## 7. Shunt Admittance

Shunt elements in PSS/E v31 are specified in MW and MVAR at unity per-unit voltage (V = 1.0 pu), not in per-unit. Tools that use per-unit admittance must convert these values.

### Fixed Shunts (GL, BL)

PSS/E convention: `GL` is the shunt conductance in MW at V = 1.0 per-unit, and `BL` is the shunt susceptance in MVAR at V = 1.0 per-unit.

Per-unit conversion:

G_pu = GL / S_base (per-unit conductance)

B_pu = BL / S_base (per-unit susceptance)

Sign convention:

- Positive `BL` = capacitive (generating reactive power, lagging current)
- Negative `BL` = inductive (absorbing reactive power, leading current)
- Positive `GL` = real power absorption (resistive loss)

### Switched Shunts (BINIT, B1-B8)

Switched shunts follow the same convention as fixed shunts: MVAR at 1.0 per-unit voltage.

- `BINIT`: initial total susceptance in MVAR
- `B1` through `B8`: susceptance per step in each switching block, in MVAR
- `N1` through `N8`: number of steps in each block

Total susceptance range: sum of (Ni \* Bi) for all blocks.

Per-unit conversion: B_pu = B_MVAR / S_base

### Worked Example

**Fixed shunt: 200 MVAR capacitor bank** --
GL = 0.0 MW (no resistive losses), BL = 200.0 MVAR

With S_base = 100 MVA:

G_pu = 0.0 / 100 = 0.0000 pu

B_pu = 200.0 / 100 = 2.0000 pu

**Per-unit to physical:**

BL = B_pu \* S_base = 2.0000 \* 100 = 200.0 MVAR (matches original)

**Physical to per-unit:**

B_pu = 200.0 / 100 = 2.0000 pu (matches)

**Switched shunt: 4 steps of 50 MVAR** --
N1 = 4, B1 = 50.0 MVAR per step

BINIT = 150.0 MVAR (3 steps currently in service)

Total range: 0 to 4 \* 50.0 = 200.0 MVAR

BINIT_pu = 150.0 / 100 = 1.5000 pu

Per step: B1_pu = 50.0 / 100 = 0.5000 pu

### Common Pitfalls

1. **Base mismatch errors:** A common error is treating GL/BL as already in per-unit. Since GL and BL are in MW and MVAR (not per-unit), importing them without dividing by S_base produces values 100x too large in the tool's internal model. The symptom is unrealistically large reactive power injections.

2. **Tool-specific conventions:**
   - **MATPOWER** stores shunt admittance in `mpc.bus(:, [GS BS])` in MW and MVAR (same as PSS/E convention), so no conversion is needed when importing from the intermediate format.
   - **pandapower** stores shunts as separate elements (`net.shunt`) with `q_mvar` and `p_mw` at rated voltage. The sign convention for `q_mvar` may differ: pandapower uses positive for inductive, which is opposite to PSS/E's positive-capacitive BL convention.
   - **PyPSA** stores shunt impedance in per-unit in `network.shunt_impedances`. The conversion from MVAR to per-unit must be performed during import: B_pu = BL / S_base.
   - **GridCal** stores shunts in per-unit admittance, requiring the MVAR-to-per-unit conversion.
   - **PowerModels.jl** stores shunt data in `bus["gs"]` and `bus["bs"]` in per-unit (not MW/MVAR), so conversion from PSS/E values is required: gs = GL / baseMVA, bs = BL / baseMVA.
   - **PowerSimulations.jl** (via PowerSystems.jl) stores fixed shunts with admittance in per-unit.

3. **Diagnostic signature:** If GL/BL values are imported without dividing by S_base, reactive power injections at shunt buses will be off by a factor of S_base (typically 100). The voltage profile will show severe over-voltages at buses with large capacitor banks.

4. **Correction formula:** For tools requiring per-unit: G_pu = GL_MW / S_base; B_pu = BL_MVAR / S_base. Watch for sign convention differences (capacitive positive vs. inductive positive).

## 8. Generator Capability

Generator active and reactive power limits in PSS/E v31 are specified in physical units (MW and MVAR), not per-unit. The generator MVA base (`MBASE`) is distinct from the system MVA base (`SBASE`) and is relevant for machine impedance calculations.

### Active Power (PG, PMAX, PMIN)

Units: MW (not per-unit)

- `PG`: current active power output in MW
- `PMAX`: maximum active power output in MW
- `PMIN`: minimum active power output in MW

No per-unit conversion is needed for the intermediate format. Tools that require per-unit values must convert: P_pu = P_MW / S_base.

### Reactive Power (QG, QMAX, QMIN)

Units: MVAR (not per-unit)

- `QG`: current reactive power output in MVAR
- `QMAX`: maximum reactive power output in MVAR
- `QMIN`: minimum reactive power output in MVAR

No per-unit conversion is needed for the intermediate format. For tools requiring per-unit: Q_pu = Q_MVAR / S_base.

### Generator MVA Base (MBASE)

`MBASE` is the machine MVA base, used for machine impedance calculations (subtransient and transient reactances). It is distinct from `SBASE`:

- `SBASE`: system-wide power base for network impedance (typically 100 MVA)
- `MBASE`: per-machine base for machine parameters (typically the generator nameplate MVA)

Machine impedance on system base: X_pu,system = X_pu,machine \* (SBASE / MBASE)

The MBASE field is present in the intermediate format but is primarily relevant for dynamic studies and transient stability, not steady-state power flow.

### Voltage Setpoint (VS)

The generator voltage setpoint `VS` is in per-unit on the bus `BASKV`:

V_kV = VS \* BASKV

A typical setpoint is VS = 1.02 to 1.05 per-unit.

### Worked Example

A 500 MW gas turbine at a 230 kV bus:

- MBASE = 600 MVA
- PG = 450.0 MW, PMAX = 500.0 MW, PMIN = 100.0 MW
- QG = 120.0 MVAR, QMAX = 300.0 MVAR, QMIN = -150.0 MVAR
- VS = 1.035 per-unit, BASKV = 230.0 kV

**Per-unit to physical (voltage):**

V_kV = 1.035 \* 230.0 = 238.050 kV

**Physical to per-unit (power, for tools requiring it):**

With S_base = 100 MVA:

P_pu = 450.0 / 100 = 4.500 pu

Q_pu = 120.0 / 100 = 1.200 pu

PMAX_pu = 500.0 / 100 = 5.000 pu

**Physical to per-unit round-trip:**

P_MW = 4.500 \* 100 = 450.0 MW (matches original)

V_pu = 238.050 / 230.0 = 1.0350 pu (matches original)

**Machine impedance conversion example:**

Generator subtransient reactance X''d = 0.20 pu on MBASE = 600 MVA

On system base: X''d_system = 0.20 \* (100 / 600) = 0.03333 pu

### Common Pitfalls

1. **Base mismatch errors:** Confusing `MBASE` with `SBASE` when converting machine impedance. If a tool converts machine reactances using `SBASE` instead of `MBASE`, the impedances will be off by a factor of MBASE / SBASE. For a 600 MVA machine on a 100 MVA system, the error factor is 6.

2. **Tool-specific conventions:**
   - **MATPOWER** stores generator output in `mpc.gen(:, [PG QG QMAX QMIN PMAX PMIN])` in MW/MVAR. The MBASE is stored in `mpc.gen(:, MBASE)`. Conversion to per-unit happens internally.
   - **pandapower** stores generator data in `net.gen` with `p_mw`, `max_q_mvar`, `min_q_mvar` in physical units. Voltage setpoint is in per-unit (`vm_pu`).
   - **PyPSA** stores generator power in MW in `network.generators.p_nom` (nominal capacity) and dispatch in `network.generators_t.p`. Voltage setpoint is `v_set_pu`.
   - **GridCal** stores generator power in MW and voltage setpoint in per-unit.
   - **PowerModels.jl** stores generator data in per-unit on the system base: `gen["pg"]` = PG/baseMVA, `gen["qg"]` = QG/baseMVA.
   - **PowerSimulations.jl** stores generator data through PowerSystems.jl with `active_power` and `reactive_power` in per-unit on system base.

3. **Diagnostic signature:** If PG/PMAX are imported as per-unit when they are actually in MW, all generator outputs will appear 100x too large (with S_base = 100). The power flow solution will not converge or will show extreme power mismatches.

4. **Correction formula:**
   - MW to per-unit: P_pu = P_MW / S_base
   - Per-unit to MW: P_MW = P_pu \* S_base
   - Machine base to system base: X_system = X_machine \* (S_base / MBASE)

## 9. Load Representation

Load active and reactive power in PSS/E v31 are specified in physical units (MW and MVAR), not per-unit. The intermediate format preserves these physical units.

### Active/Reactive Load (PL, QL)

Units: MW and MVAR (not per-unit)

- `PL`: active power demand in MW (positive = load consuming power)
- `QL`: reactive power demand in MVAR (positive = load absorbing reactive power)

### Per-Unit Conversion (for tools requiring it)

P_pu = PL / S_base

Q_pu = QL / S_base

Inverse:

PL = P_pu \* S_base

QL = Q_pu \* S_base

### Worked Example

A 275.0 MW, 85.0 MVAR load with S_base = 100 MVA:

**Physical to per-unit:**

P_pu = 275.0 / 100 = 2.7500 pu

Q_pu = 85.0 / 100 = 0.8500 pu

**Per-unit to physical:**

PL = 2.7500 \* 100 = 275.0 MW (matches original)

QL = 0.8500 \* 100 = 85.0 MVAR (matches original)

Round-trip confirmation: both values match to 4 significant digits.

### Common Pitfalls

1. **Base mismatch errors:** If a tool imports PL/QL as per-unit values when they are actually in MW/MVAR, the load will be modeled as S_base times too large. With S_base = 100, a 275 MW load would become 27,500 MW, causing the power flow to diverge. The symptom is non-convergence or extreme voltage collapse.

2. **Tool-specific conventions:**
   - **MATPOWER** stores loads in `mpc.bus(:, [PD QD])` in MW and MVAR, matching the PSS/E convention. No conversion needed.
   - **pandapower** stores loads in `net.load` with `p_mw` and `q_mvar` in physical units. No conversion needed.
   - **PyPSA** stores loads in MW in `network.loads.p_set` and `network.loads.q_set`. No conversion needed when importing from the intermediate format.
   - **GridCal** stores loads in MW and MVAR, matching the intermediate format.
   - **PowerModels.jl** stores loads in per-unit on the system base: `load["pd"]` = PL/baseMVA, `load["qd"]` = QL/baseMVA. Conversion from MW to per-unit is required during import.
   - **PowerSimulations.jl** stores loads through PowerSystems.jl with `active_power` and `reactive_power` in per-unit on system base. Conversion required.

3. **Diagnostic signature:** If MW/MVAR loads are imported as per-unit without conversion, total system load will be off by a factor of S_base. A quick check: sum(PL) in the tool should equal the sum of MW loads from the FNM. If the tool's total is 100x smaller, the loads were correctly converted to per-unit; if 100x larger, they were treated as per-unit when they are MW.

4. **Correction formula:**
   - MW to per-unit: P_pu = PL / S_base
   - Per-unit to MW: PL = P_pu \* S_base

## Summary Table

| Domain | PSS/E Fields | Unit in Intermediate Format | Per-Unit Base | Conversion Formula (pu to physical) |
|--------|-------------|---------------------------|---------------|--------------------------------------|
| 1. System MVA Base | `SBASE` (header) | MVA | -- (this IS the base) | -- |
| 2. Bus Base Voltage | `BASKV` (Bus) | kV | -- (this IS the voltage base) | V_kV = V_pu \* BASKV |
| 3. Branch Impedance | `R`, `X`, `B` (Branch) | per-unit | S_base, BASKV_from | Z_ohm = Z_pu \* BASKV^2 / S_base |
| 4. 2W Transformer Impedance | `R1-2`, `X1-2`, `CZ` (Transformer) | per-unit (CZ-dependent) | Depends on CZ mode | Z_ohm = Z_pu \* BASKV^2 / S_base_effective |
| 5. 2W Transformer Taps | `WINDV1`, `WINDV2`, `CW` (Transformer) | CW-dependent | Depends on CW mode | tap_kV = WINDV \* BASKV (CW=1) |
| 6. 3W Transformer Bases | `R`, `X` per pair, `RATAn`, `CZ` (Transformer) | per-unit (CZ-dependent) | Per-winding MVA and kV | Z_ohm = Z_pu \* BASKV_wn^2 / S_base,wn |
| 7. Shunt Admittance | `GL`, `BL` (Fixed Shunt), `BINIT`, `Bi` (Switched Shunt) | MW / MVAR at V=1.0 pu | Not per-unit in PSS/E | G_pu = GL / S_base; B_pu = BL / S_base |
| 8. Generator Capability | `PG`, `PMAX`, `QG`, `QMAX`, `MBASE`, `VS` (Generator) | MW / MVAR (not pu); VS in pu | MW/MVAR: none; VS: BASKV | P_MW = P_pu \* S_base; V_kV = VS \* BASKV |
| 9. Load Representation | `PL`, `QL` (Load) | MW / MVAR (not pu) | none | PL = P_pu \* S_base |

## Cross-References

- **Phase 1 D7 — Intermediate Format Schema Specification:** Defines JSON Schema files with `perUnitBase` annotations for every field. The `PerUnitBase` enum (`system_mva`, `winding_mva`, `bus_kv`, `none`, `mixed`) classifies each field's per-unit base. This per-unit convention reference expands on that classification with formulas and worked examples.
- **Phase 2 PRD 01 — Intermediate Format Schema Reference:** Provides field semantic descriptions for every intermediate format field. This per-unit convention reference complements PRD 01 by covering the numerical conventions rather than the semantic definitions.
- **Phase 2 PRD 04 — Three-Winding Transformer Reference:** Documents full three-winding transformer topology, star-bus decomposition, and winding connection details. Section 6 of this document defers to PRD 04 for the complete three-winding treatment.
- **Phase 2 PRD 05 — Field Criticality Matrix:** Downstream consumer that uses per-unit base classification from this document to correctly classify per-unit-dependent fields by criticality level.
