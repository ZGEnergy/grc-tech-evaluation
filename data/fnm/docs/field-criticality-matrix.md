# Field Criticality Matrix

**Version:** 1.0
**Audience:** evaluate-tool agents, human reviewers
**Primary use:** Fidelity scoring weight assignment for FNM ingestion evaluation
**Dependencies:** Intermediate Schema Reference (`intermediate-schema.md`),
  Record-Type Mapping Guide (`mapping-guide.md`),
  Per-Unit Convention Reference (`per-unit-conventions.md`)

## Tier Definitions

| Tier | Label | Scope | Description |
|------|-------|-------|-------------|
| 1 | DCPF-critical | DC Power Flow | Field is required for correct DC power flow results. Loss or corruption of this field causes incorrect real power flows, generation dispatch, or topology. Includes: bus type codes, branch topology (from/to bus), branch reactance, generator active power output, load active power, transformer tap magnitude, phase shifter angle. |
| 2 | ACPF-critical | AC Power Flow | Field is additionally required for correct AC power flow convergence and accuracy. Not needed for DCPF but essential for ACPF. Includes: branch resistance and charging susceptance, bus voltage magnitude and angle (solved state), generator reactive power limits and voltage setpoint, transformer tap limits and control mode, switched shunt discrete steps, area interchange targets, shunt admittance values. |
| 3 | Informational | Context / Metadata | Field provides organizational, descriptive, or operational context but does not enter the power flow Jacobian or affect the power flow solution. Loss of this field reduces data completeness but does not degrade power flow accuracy. Includes: bus names, area/zone/owner numbers and names, generator MVA base, line thermal ratings, equipment identifiers. |
| 4 | Discardable | Always-Default / Padding | Field is confirmed by Phase 1 D7's `x-psse-present-but-inactive` annotation to be uniformly at the PSS/E default value across all FNM records. It carries no information for this specific network model. Tools that omit or zero this field lose nothing. Evaluate-tool must not penalize omission. |

The tiers are strictly ordered: DCPF-critical is the highest priority, Discardable is the lowest.
A field is assigned to the highest applicable tier (e.g., a field needed for both DCPF and ACPF is DCPF-critical, not ACPF-critical).
The Discardable tier is not a judgment about the field's general importance -- it only reflects that the field is at its default value in *this specific FNM file*.

## Summary

| Record Type | Total | DCPF-Critical | ACPF-Critical | Informational | Discardable |
|-------------|-------|---------------|---------------|---------------|-------------|
| Bus | 13 | 3 | 2 | 8 | 0 |
| Load | 13 | 4 | 5 | 4 | 0 |
| Fixed Shunt | 5 | 0 | 5 | 0 | 0 |
| Generator | 28 | 4 | 5 | 19 | 0 |
| Branch | 24 | 5 | 6 | 13 | 0 |
| Transformer | 83 | 10 | 44 | 29 | 0 |
| Area | 5 | 0 | 3 | 2 | 0 |
| Two-Terminal DC | 46 | 0 | 46 | 0 | 0 |
| VSC DC | 41 | 0 | 41 | 0 | 0 |
| Impedance Correction | 23 | 0 | 23 | 0 | 0 |
| Multi-Terminal DC | 8 | 0 | 8 | 0 | 0 |
| Multi-Section Line | 13 | 0 | 12 | 1 | 0 |
| Zone | 2 | 0 | 0 | 2 | 0 |
| Interarea Transfer | 4 | 0 | 0 | 4 | 0 |
| Owner | 2 | 0 | 0 | 2 | 0 |
| FACTS | 14 | 0 | 14 | 0 | 0 |
| Switched Shunt | 26 | 0 | 23 | 3 | 0 |
| **Total** | **350** | **26** | **237** | **87** | **0** |

## Bus

**Intermediate format table:** `bus`
**Record-type tier (from mapping guide):** Tier 1 -- Essential for any power flow
**Total fields:** 13
**Tier breakdown:** 3 DCPF-critical, 2 ACPF-critical, 8 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | DCPF-critical | Bus number is the primary key for all topology references; every branch, generator, and load references a bus by this number, making it essential for constructing the B-matrix and adjacency structure |
| `NAME` | string | Informational | Human-readable bus name used for identification in reports and diagrams; does not enter the power flow equations or affect any computed result |
| `BASKV` | number | ACPF-critical | Base voltage in kV defines the per-unit voltage base for this bus; does not enter the DCPF B-matrix directly but is essential for converting per-unit impedances to physical units and for correct impedance base calculation in ACPF |
| `IDE` | integer | DCPF-critical | Bus type code (1=PQ, 2=PV, 3=swing, 4=isolated) determines which variables are fixed versus solved in the power flow formulation, controlling topology and solution structure in both DCPF and ACPF |
| `AREA` | integer | Informational | Area number for organizational grouping; the bus-level area assignment is a grouping key used for interchange accounting, not a direct variable in the power flow equations |
| `ZONE` | integer | Informational | Zone number for geographic or administrative grouping used in reporting and load allocation; no direct impact on power flow equations |
| `OWNER` | integer | Informational | Ownership tracking number; administrative metadata for cost allocation with no electrical effect on the power flow solution |
| `VM` | number | ACPF-critical | Bus voltage magnitude in per-unit serves as the initial condition for ACPF iteration and the solved-state verification target; not used in DCPF which solves only for voltage angles |
| `VA` | number | DCPF-critical | Bus voltage angle in degrees is the primary DCPF solution variable; the swing bus angle serves as the reference and all branch power flows are computed from angle differences |
| `NVHI` | number | Informational | Normal operating voltage high limit in per-unit; used for post-solution voltage violation monitoring and OPF constraints, does not enter the power flow Jacobian |
| `NVLO` | number | Informational | Normal operating voltage low limit in per-unit; post-solution monitoring parameter for voltage violation flagging, not a power flow variable |
| `EVHI` | number | Informational | Emergency voltage high limit in per-unit; applied during contingency analysis for wider voltage tolerance, not a variable in the power flow equations |
| `EVLO` | number | Informational | Emergency voltage low limit in per-unit; contingency analysis parameter with no effect on the power flow solution |

Voltage limit fields (NVHI, NVLO, EVHI, EVLO) are classified as Informational rather than ACPF-critical because they are post-solution constraint checks used in OPF and contingency analysis, not variables in the power flow equations.

## Load

**Intermediate format table:** `load`
**Record-type tier (from mapping guide):** Tier 1 -- Essential for any power flow
**Total fields:** 13
**Tier breakdown:** 3 DCPF-critical, 5 ACPF-critical, 5 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | DCPF-critical | Bus number where load withdraws power; determines which bus in the network topology receives the power withdrawal, essential for the DCPF power injection vector |
| `ID` | string | Informational | Two-character load identifier distinguishing multiple loads at the same bus. Traceability label only — tools that aggregate multiple loads to bus-level active power (e.g., via PPC import) produce identical bus injections and identical DCPF results. Absence does not affect bus angles or branch flows. |
| `STATUS` | integer | DCPF-critical | Load status (1=in-service, 0=out-of-service) determines whether this load's power withdrawal is included in the power flow solution, directly affecting the power injection vector |
| `AREA` | integer | Informational | Area assignment for this load used for area interchange calculations; organizational grouping that does not directly enter the power flow equations |
| `ZONE` | integer | Informational | Zone assignment for this load; administrative grouping for reporting with no power flow impact |
| `PL` | number | DCPF-critical | Constant-power active load demand in MW; direct real power withdrawal at the bus entering the DCPF power injection vector and the ACPF power balance equations |
| `QL` | number | ACPF-critical | Constant-power reactive load demand in MVAR; enters the ACPF reactive power balance equations but is ignored in DCPF which does not model reactive power |
| `IP` | number | ACPF-critical | Constant-current active power component in MW at 1.0 pu voltage; voltage-dependent load model that scales linearly with bus voltage magnitude in ACPF |
| `IQ` | number | ACPF-critical | Constant-current reactive power component in MVAR at 1.0 pu voltage; voltage-dependent reactive load entering the ACPF reactive balance equations |
| `YP` | number | ACPF-critical | Constant-admittance active power component in MW at 1.0 pu voltage; scales with the square of bus voltage magnitude in the ACPF load model |
| `YQ` | number | ACPF-critical | Constant-admittance reactive power component in MVAR at 1.0 pu voltage; voltage-squared-dependent reactive load in the ACPF formulation |
| `OWNER` | integer | Informational | Owner number for this load; administrative metadata for cost allocation with no effect on power flow computation |
| `SCALE` | integer | Informational | Load scaling flag (1=participates in scaling, 0=fixed); operational parameter controlling whether the load is adjusted during area interchange scaling, not a direct power flow variable |

## Fixed Shunt

**Intermediate format table:** `fixed_shunt`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 5
**Tier breakdown:** 0 DCPF-critical, 5 ACPF-critical, 0 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | ACPF-critical | Bus number where the fixed shunt is connected; determines placement of the shunt admittance in the Y-bus matrix for ACPF, not needed for DCPF which ignores reactive compensation |
| `ID` | string | ACPF-critical | Shunt identifier forming part of the composite primary key; required to distinguish multiple shunts at the same bus and correctly aggregate their admittance contributions in ACPF |
| `STATUS` | integer | ACPF-critical | Shunt status (1=in-service, 0=out-of-service) determines whether this shunt's admittance is included in the Y-bus matrix for ACPF computation |
| `GL` | number | ACPF-critical | Active component of shunt admittance to ground in MW at 1.0 pu voltage; contributes real power loss to the Y-bus diagonal element in ACPF |
| `BL` | number | ACPF-critical | Reactive component of shunt admittance to ground in MVAR at 1.0 pu voltage; provides reactive power compensation in the Y-bus diagonal for ACPF voltage regulation |

All fixed shunt fields are ACPF-critical because fixed shunts provide reactive compensation that enters the Y-bus admittance matrix in ACPF but is ignored in DCPF's lossless real-power-only formulation.

## Generator

**Intermediate format table:** `generator`
**Record-type tier (from mapping guide):** Tier 1 -- Essential for any power flow
**Total fields:** 28
**Tier breakdown:** 3 DCPF-critical, 5 ACPF-critical, 20 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | DCPF-critical | Bus number where generator injects power; determines the bus in the network topology that receives the generation injection, essential for the DCPF power injection vector |
| `ID` | string | Informational | Two-character machine identifier distinguishing multiple generators at the same bus. Traceability label only — tools that enumerate generators by bus-row index rather than ID produce identical bus injection sums and identical DCPF results. Absence does not affect bus angles or branch flows. |
| `PG` | number | DCPF-critical | Active power output in MW; direct real power injection at the bus entering the DCPF power injection vector and ACPF active power balance equations |
| `QG` | number | ACPF-critical | Reactive power output in MVAR; enters the ACPF reactive power balance equations as a solved variable at PV buses, not used in DCPF |
| `QT` | number | ACPF-critical | Maximum reactive power limit in MVAR; determines the upper bound for PV-to-PQ bus conversion when the generator reaches its reactive capability limit in ACPF |
| `QB` | number | ACPF-critical | Minimum reactive power limit in MVAR; determines the lower bound for PV-to-PQ bus conversion in ACPF reactive capability enforcement |
| `VS` | number | ACPF-critical | Voltage setpoint in per-unit for PV bus regulation; the target voltage that the generator maintains by adjusting reactive output in ACPF iteration |
| `IREG` | integer | ACPF-critical | Remote regulated bus number (0=local regulation); determines which bus voltage is controlled by this generator in ACPF, critical for correct voltage regulation topology |
| `MBASE` | number | Informational | Machine MVA base for per-unit impedance conversion; relevant for generator internal impedance in dynamic and short-circuit studies, not for steady-state power flow |
| `ZR` | number | Informational | Machine resistance in per-unit on MBASE; part of the generator internal impedance model for short-circuit studies, not used in steady-state power flow computation |
| `ZX` | number | Informational | Machine reactance in per-unit on MBASE; sub-transient or transient reactance for dynamic studies, not a steady-state power flow parameter |
| `RT` | number | Informational | Step-up transformer resistance in per-unit on MBASE; generator-side transformer impedance for short-circuit analysis, not used in steady-state power flow |
| `XT` | number | Informational | Step-up transformer reactance in per-unit on MBASE; generator-side transformer impedance for dynamic studies, not a power flow variable |
| `GTAP` | number | Informational | Step-up transformer off-nominal turns ratio in per-unit; relates to the generator-side transformer model for dynamic studies, not used in steady-state power flow |
| `STAT` | integer | DCPF-critical | Generator status (1=in-service, 0=out-of-service); determines whether this generator's power injection is included in the power flow solution, directly affecting topology and power balance |
| `RMPCT` | number | Informational | Percent of total MVAR range allocated to remote voltage regulation; operational parameter for distributed slack reactive control, not a direct power flow equation variable |
| `PT` | number | Informational | Maximum active power output in MW (turbine limit); operational context for generator remote regulation calculations, not a constraint in basic DCPF or ACPF |
| `PB` | number | Informational | Minimum active power output in MW (turbine limit); operational context for generator remote regulation calculations, not a constraint in basic power flow |
| `O1` | integer | Informational | Owner number 1; administrative ownership tracking with no electrical effect on the power flow solution |
| `F1` | number | Informational | Fraction of generator owned by owner 1; ownership cost allocation metadata with no power flow impact |
| `O2` | integer | Informational | Owner number 2; secondary ownership tracking with no electrical effect on the power flow solution |
| `F2` | number | Informational | Fraction owned by owner 2; ownership metadata with no power flow impact |
| `O3` | integer | Informational | Owner number 3; tertiary ownership tracking with no electrical effect on the power flow solution |
| `F3` | number | Informational | Fraction owned by owner 3; ownership metadata with no power flow impact |
| `O4` | integer | Informational | Owner number 4; quaternary ownership tracking with no electrical effect on the power flow solution |
| `F4` | number | Informational | Fraction owned by owner 4; ownership metadata with no power flow impact |
| `WMOD` | integer | Informational | Wind machine reactive power control mode (0=standard); operational mode flag for wind-specific generator models, does not affect the steady-state power flow equations |
| `WPF` | number | Informational | Wind machine power factor for WMOD=1 mode; wind-specific operational parameter, not a direct power flow variable in steady-state analysis |

## Branch

**Intermediate format table:** `branch`
**Record-type tier (from mapping guide):** Tier 1 -- Essential for any power flow
**Total fields:** 24
**Tier breakdown:** 4 DCPF-critical, 6 ACPF-critical, 14 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | DCPF-critical | From-bus number defining one endpoint of the branch in the network topology; essential for constructing the B-matrix adjacency structure in DCPF |
| `J` | integer | DCPF-critical | To-bus number defining the other endpoint of the branch; together with I, establishes the branch connectivity required for DCPF and ACPF admittance matrices |
| `CKT` | string | Informational | Circuit identifier distinguishing parallel branches between the same bus pair. Traceability label only — tools that enumerate parallel branches by row index rather than CKT enumerate all branch impedances correctly and produce identical B-matrix construction and DCPF results. Absence does not affect bus angles or branch flows. |
| `R` | number | ACPF-critical | Series resistance in per-unit on system MVA base; enters the Y-bus for ACPF real power loss computation but is ignored in DCPF which assumes lossless branches |
| `X` | number | DCPF-critical | Series reactance in per-unit on system MVA base; enters the B-matrix for DCPF (as 1/X) and the Y-bus for ACPF, the dominant impedance component for power transfer |
| `B` | number | ACPF-critical | Total line charging susceptance in per-unit; provides reactive power injection at both branch endpoints in ACPF, ignored in DCPF's lossless model |
| `RATEA` | number | Informational | Normal thermal rating in MVA (Rate A); post-solution constraint check for continuous loading monitoring, does not enter the power flow equations |
| `RATEB` | number | Informational | Emergency thermal rating in MVA (Rate B); post-solution overload limit, not a power flow variable |
| `RATEC` | number | Informational | Short-term thermal rating in MVA (Rate C); post-solution constraint for emergency loading, not a power flow variable |
| `GI` | number | ACPF-critical | From-bus end shunt conductance in per-unit; contributes to the Y-bus diagonal element at the from-bus in ACPF, representing distributed line losses |
| `BI` | number | ACPF-critical | From-bus end shunt susceptance in per-unit; contributes to the Y-bus diagonal at the from-bus in ACPF, representing asymmetric line charging |
| `GJ` | number | ACPF-critical | To-bus end shunt conductance in per-unit; contributes to the Y-bus diagonal at the to-bus in ACPF, representing distributed line losses |
| `BJ` | number | ACPF-critical | To-bus end shunt susceptance in per-unit; contributes to the Y-bus diagonal at the to-bus in ACPF, representing asymmetric line charging |
| `ST` | integer | DCPF-critical | Branch status (1=in-service, 0=out-of-service); determines whether this branch exists in the network topology for both DCPF and ACPF admittance matrix construction |
| `MET` | integer | Informational | Metered end flag (1=from-bus, 2=to-bus); determines which end is used for loss allocation in accounting, does not affect the power flow solution |
| `LEN` | number | Informational | Line length in user-selected units; informational field for documentation and distance-based calculations, not used in power flow computation |
| `O1` | integer | Informational | Owner number 1; administrative ownership tracking with no electrical effect on the power flow solution |
| `F1` | number | Informational | Fraction owned by owner 1; ownership cost allocation metadata with no power flow impact |
| `O2` | integer | Informational | Owner number 2; secondary ownership tracking with no electrical effect on the power flow solution |
| `F2` | number | Informational | Fraction owned by owner 2; ownership metadata with no power flow impact |
| `O3` | integer | Informational | Owner number 3; tertiary ownership tracking with no electrical effect on the power flow solution |
| `F3` | number | Informational | Fraction owned by owner 3; ownership metadata with no power flow impact |
| `O4` | integer | Informational | Owner number 4; quaternary ownership tracking with no electrical effect on the power flow solution |
| `F4` | number | Informational | Fraction owned by owner 4; ownership metadata with no power flow impact |

Line ratings (RATEA, RATEB, RATEC) are classified as Informational rather than ACPF-critical because thermal limits do not affect the power flow solution -- they are post-solution constraint checks used in contingency analysis and OPF.

## Transformer

**Intermediate format table:** `transformer`
**Record-type tier (from mapping guide):** Tier 1 -- Essential for any power flow
**Total fields:** 83
**Tier breakdown:** 6 DCPF-critical, 44 ACPF-critical, 33 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | DCPF-critical | Winding 1 (primary) bus number; defines one endpoint of the transformer in the network topology, essential for the B-matrix adjacency structure |
| `J` | integer | DCPF-critical | Winding 2 (secondary) bus number; defines the other endpoint, establishing the transformer branch connectivity |
| `K` | integer | Informational | Winding 3 (tertiary) bus number; K=0 for 2-winding, K!=0 for 3-winding. Tools loading from MATPOWER PPC format receive pre-expanded star-equivalent 2-winding pairs — the original K value is not present but the star-equivalent topology preserves identical B-matrix structure and DCPF results. Tools using native PSS/E 3-winding support carry this field natively. |
| `CKT` | string | Informational | Circuit identifier for parallel transformers between the same bus pair. Traceability label only — same rationale as Branch.CKT; enumeration by row index produces identical admittance matrix construction. |
| `CW` | integer | ACPF-critical | Winding data I/O code determining how WINDV tap ratios are interpreted (1=pu on bus base kV, 2=kV, 3=pu on nominal kV); controls impedance parameter interpretation for ACPF |
| `CZ` | integer | ACPF-critical | Impedance data I/O code determining the per-unit base for R and X values (1=pu on system base, 2=pu on winding base, 3=losses in W); essential for correct impedance conversion in ACPF |
| `CM` | integer | ACPF-critical | Magnetizing admittance I/O code determining how MAG1/MAG2 are interpreted (1=pu on system base, 2=exciting current/losses); controls magnetizing branch parameter interpretation |
| `MAG1` | number | ACPF-critical | Magnetizing conductance or no-load losses (depending on CM); contributes to the Y-bus shunt admittance at the transformer primary in ACPF |
| `MAG2` | number | ACPF-critical | Magnetizing susceptance or exciting current (depending on CM); contributes to the Y-bus shunt admittance representing core losses and magnetizing current in ACPF |
| `NMETR` | integer | Informational | Non-metered end code (1, 2, or 3); determines which winding is used for loss allocation accounting, does not affect the power flow solution |
| `NAME` | string | Informational | Transformer name up to 12 characters; human-readable identification with no effect on power flow computation |
| `STAT` | integer | DCPF-critical | Transformer status (0=all out, 1=in-service, 2-4=partial winding status); determines whether and how the transformer exists in the network topology for admittance matrix construction |
| `O1` | integer | Informational | Owner number 1; administrative ownership tracking with no electrical effect on the power flow solution |
| `F1` | number | Informational | Fraction owned by owner 1; ownership cost allocation metadata with no power flow impact |
| `O2` | integer | Informational | Owner number 2; secondary ownership tracking with no electrical effect on the power flow solution |
| `F2` | number | Informational | Fraction owned by owner 2; ownership metadata with no power flow impact |
| `O3` | integer | Informational | Owner number 3; tertiary ownership tracking with no electrical effect on the power flow solution |
| `F3` | number | Informational | Fraction owned by owner 3; ownership metadata with no power flow impact |
| `O4` | integer | Informational | Owner number 4; quaternary ownership tracking with no electrical effect on the power flow solution |
| `F4` | number | Informational | Fraction owned by owner 4; ownership metadata with no power flow impact |
| `VECGRP` | string | Informational | Vector group designation (e.g., YNyn0); describes the winding connection configuration for reference, does not directly enter the power flow equations |
| `R1_2` | number | ACPF-critical | Resistance of winding 1-2 pair; enters the Y-bus for ACPF real power loss computation through the transformer, ignored in DCPF's lossless assumption |
| `X1_2` | number | DCPF-critical | Reactance of winding 1-2 pair; enters the B-matrix for DCPF (as 1/X) and the Y-bus for ACPF, the dominant impedance parameter for transformer power transfer |
| `SBASE1_2` | number | ACPF-critical | MVA base for winding 1-2 impedance; determines the per-unit base for R1_2 and X1_2 when CZ=1, essential for correct impedance conversion in ACPF |
| `R2_3` | number | ACPF-critical | Resistance of winding 2-3 pair (3-winding only); enters the Y-bus for the star-bus equivalent 2-3 leg in ACPF |
| `X2_3` | number | Informational | Reactance of winding 2-3 pair (3-winding only). Tools loading from MATPOWER PPC receive pre-computed star-equivalent branch impedances that embed X2_3's contribution — the raw PSS/E field is absent but DCPF accuracy is preserved via the star-equivalent. Tools with native 3-winding support carry X2_3 directly. |
| `SBASE2_3` | number | ACPF-critical | MVA base for winding 2-3 impedance; determines per-unit base for R2_3/X2_3 when CZ=1, required for correct impedance conversion |
| `R3_1` | number | ACPF-critical | Resistance of winding 3-1 pair (3-winding only); enters the Y-bus for the star-bus equivalent 3-1 leg in ACPF |
| `X3_1` | number | Informational | Reactance of winding 3-1 pair (3-winding only). Same rationale as X2_3: star-equivalent conversion preserves DCPF accuracy; raw field absent only in MATPOWER PPC pathway. |
| `SBASE3_1` | number | ACPF-critical | MVA base for winding 3-1 impedance; determines per-unit base for R3_1/X3_1 when CZ=1, required for correct impedance conversion |
| `VMSTAR` | number | ACPF-critical | Star-bus voltage magnitude initial value for 3-winding transformers; provides the initial voltage guess for the synthetic star bus in ACPF iteration |
| `ANSTAR` | number | ACPF-critical | Star-bus voltage angle initial value for 3-winding transformers; provides the initial angle guess for the synthetic star bus in ACPF iteration |
| `WINDV1` | number | DCPF-critical | Winding 1 off-nominal turns ratio or voltage; scales effective reactance in DCPF and affects voltage transformation ratio in ACPF |
| `NOMV1` | number | ACPF-critical | Winding 1 nominal voltage in kV; needed with CW modes for tap ratio interpretation, affects how WINDV1 is converted to per-unit in ACPF |
| `ANG1` | number | DCPF-critical | Winding 1 phase shift angle in degrees; directly enters the DCPF formulation for phase-shifting transformers, controlling real power flow direction |
| `RATA1` | number | ACPF-critical | Winding 1 normal rating in MVA; preservation-critical field used for transformer capacity assessment and OPF thermal constraints, required for complete transformer model specification in ACPF |
| `RATB1` | number | Informational | Winding 1 emergency rating in MVA; post-solution thermal constraint, not a power flow variable |
| `RATC1` | number | Informational | Winding 1 short-term rating in MVA; post-solution thermal constraint, not a power flow variable |
| `COD1` | integer | ACPF-critical | Winding 1 tap changer control mode code; determines whether and how the tap ratio is adjusted during ACPF solution for voltage or flow regulation |
| `CONT1` | integer | ACPF-critical | Winding 1 controlled bus number; identifies the target bus for voltage regulation by the tap changer in ACPF |
| `RMA1` | number | ACPF-critical | Maximum tap ratio or angle limit for winding 1; upper bound on tap changer adjustment range in ACPF |
| `RMI1` | number | ACPF-critical | Minimum tap ratio or angle limit for winding 1; lower bound on tap changer adjustment range in ACPF |
| `VMA1` | number | ACPF-critical | Maximum voltage or flow target for winding 1 control; upper control target for tap changer regulation in ACPF |
| `VMI1` | number | ACPF-critical | Minimum voltage or flow target for winding 1 control; lower control target for tap changer regulation in ACPF |
| `NTP1` | integer | ACPF-critical | Number of tap positions for winding 1; defines the discrete tap step resolution for the tap changer in ACPF |
| `TAB1` | integer | Informational | Impedance correction table number for winding 1; references a piecewise-linear correction curve, secondary adjustment that is often unused |
| `CR1` | number | Informational | Load drop compensation resistance for winding 1; secondary voltage regulation refinement typically at default values, not a primary power flow parameter |
| `CX1` | number | Informational | Load drop compensation reactance for winding 1; secondary voltage regulation refinement typically at default values, not a primary power flow parameter |
| `CNXA1` | integer | Informational | Connection angle for winding 1 wye-delta transformers; advanced winding connection parameter, does not enter the standard power flow equations |
| `WINDV2` | number | ACPF-critical | Winding 2 off-nominal turns ratio or voltage; affects voltage transformation in ACPF (usually 1.0 for standard 2-winding transformers) |
| `NOMV2` | number | ACPF-critical | Winding 2 nominal voltage in kV; needed with CW modes for winding 2 tap ratio interpretation in ACPF |
| `ANG2` | number | ACPF-critical | Winding 2 phase shift angle in degrees; affects phase shifting on the secondary winding in ACPF |
| `RATA2` | number | ACPF-critical | Winding 2 normal rating in MVA; preservation-critical field used for transformer capacity assessment and OPF thermal constraints, required for complete transformer model specification in ACPF |
| `RATB2` | number | Informational | Winding 2 emergency rating in MVA; post-solution thermal constraint, not a power flow variable |
| `RATC2` | number | Informational | Winding 2 short-term rating in MVA; post-solution thermal constraint, not a power flow variable |
| `COD2` | integer | ACPF-critical | Winding 2 tap changer control mode code; determines how the winding 2 tap ratio is adjusted in ACPF |
| `CONT2` | integer | ACPF-critical | Winding 2 controlled bus number; identifies the target bus for winding 2 voltage regulation in ACPF |
| `RMA2` | number | ACPF-critical | Maximum tap ratio or angle limit for winding 2; upper bound on winding 2 tap changer range in ACPF |
| `RMI2` | number | ACPF-critical | Minimum tap ratio or angle limit for winding 2; lower bound on winding 2 tap changer range in ACPF |
| `VMA2` | number | ACPF-critical | Maximum voltage or flow target for winding 2 control; upper control target for winding 2 regulation in ACPF |
| `VMI2` | number | ACPF-critical | Minimum voltage or flow target for winding 2 control; lower control target for winding 2 regulation in ACPF |
| `NTP2` | integer | ACPF-critical | Number of tap positions for winding 2; defines the discrete tap step resolution for winding 2 in ACPF |
| `TAB2` | integer | Informational | Impedance correction table number for winding 2; references a piecewise-linear correction curve, secondary parameter |
| `CR2` | number | Informational | Load drop compensation resistance for winding 2; secondary voltage regulation refinement, not a primary power flow parameter |
| `CX2` | number | Informational | Load drop compensation reactance for winding 2; secondary voltage regulation refinement, not a primary power flow parameter |
| `CNXA2` | integer | Informational | Connection angle for winding 2; advanced winding connection parameter, does not enter the standard power flow equations |
| `WINDV3` | number | ACPF-critical | Winding 3 off-nominal turns ratio or voltage; affects voltage transformation for the tertiary winding in 3-winding transformers in ACPF |
| `NOMV3` | number | ACPF-critical | Winding 3 nominal voltage in kV; needed with CW modes for winding 3 tap ratio interpretation in ACPF |
| `ANG3` | number | ACPF-critical | Winding 3 phase shift angle in degrees; affects phase shifting on the tertiary winding in ACPF |
| `RATA3` | number | ACPF-critical | Winding 3 normal rating in MVA; preservation-critical field used for transformer capacity assessment and OPF thermal constraints, required for complete transformer model specification in ACPF |
| `RATB3` | number | Informational | Winding 3 emergency rating in MVA; post-solution thermal constraint, not a power flow variable |
| `RATC3` | number | Informational | Winding 3 short-term rating in MVA; post-solution thermal constraint, not a power flow variable |
| `COD3` | integer | ACPF-critical | Winding 3 tap changer control mode code; determines how the winding 3 tap ratio is adjusted in ACPF |
| `CONT3` | integer | ACPF-critical | Winding 3 controlled bus number; identifies the target bus for winding 3 voltage regulation in ACPF |
| `RMA3` | number | ACPF-critical | Maximum tap ratio or angle limit for winding 3; upper bound on winding 3 tap changer range in ACPF |
| `RMI3` | number | ACPF-critical | Minimum tap ratio or angle limit for winding 3; lower bound on winding 3 tap changer range in ACPF |
| `VMA3` | number | ACPF-critical | Maximum voltage or flow target for winding 3 control; upper control target for winding 3 regulation in ACPF |
| `VMI3` | number | ACPF-critical | Minimum voltage or flow target for winding 3 control; lower control target for winding 3 regulation in ACPF |
| `NTP3` | integer | ACPF-critical | Number of tap positions for winding 3; defines the discrete tap step resolution for winding 3 in ACPF |
| `TAB3` | integer | Informational | Impedance correction table number for winding 3; references a piecewise-linear correction curve, secondary parameter |
| `CR3` | number | Informational | Load drop compensation resistance for winding 3; secondary voltage regulation refinement, not a primary power flow parameter |
| `CX3` | number | Informational | Load drop compensation reactance for winding 3; secondary voltage regulation refinement, not a primary power flow parameter |
| `CNXA3` | integer | Informational | Connection angle for winding 3; advanced winding connection parameter, does not enter the standard power flow equations |

CW, CZ, and CM codes are classified as ACPF-critical because they determine how transformer impedance and tap ratio values are interpreted, even though the codes themselves are not numerical parameters in the power flow equations. Normal winding ratings (RATA1, RATA2, RATA3) are ACPF-critical because they are preservation-critical fields required for complete transformer model specification; emergency and short-term ratings (RATB1-3, RATC1-3) are Informational as they are secondary thermal limits not flagged as preservation-critical.

## Area

**Intermediate format table:** `area`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 5
**Tier breakdown:** 0 DCPF-critical, 3 ACPF-critical, 2 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | Informational | Area number serves as the primary key for organizational grouping; the area ID itself is a lookup key for interchange data, not a direct variable in the power flow equations |
| `ISW` | integer | ACPF-critical | Area slack bus number determining which generator absorbs area interchange mismatch; controls generation redispatch in area interchange control during ACPF solution |
| `PDES` | number | ACPF-critical | Desired net area interchange in MW; the target power export/import for area interchange control in ACPF, directly affecting generation redispatch |
| `PTOL` | number | ACPF-critical | Area interchange tolerance in MW; convergence criterion for area interchange control determining when the ACPF solution has satisfied the interchange target |
| `ARNAME` | string | Informational | Area name for human-readable identification; descriptive label with no effect on power flow computation |

## Two-Terminal DC

**Intermediate format table:** `two_terminal_dc`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 46
**Tier breakdown:** 0 DCPF-critical, 46 ACPF-critical, 0 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `NAME` | string | ACPF-critical | HVDC line name serving as the primary key; required to identify and instantiate this DC link in the power flow model |
| `MDC` | integer | ACPF-critical | Control mode (0=blocked, 1=current, 2=power) determining how the DC line controls are modeled in ACPF; affects converter firing angle and power flow interaction |
| `RDC` | number | ACPF-critical | DC line resistance in ohms; determines DC power losses between rectifier and inverter, affecting the AC-DC power balance in ACPF |
| `SETVL` | number | ACPF-critical | Current or power demand setpoint; the operating target for the DC line control system, directly affecting AC-side power injections in ACPF |
| `VSCHD` | number | ACPF-critical | Scheduled DC voltage in kV; determines the operating voltage of the DC line, affecting converter reactive power consumption in ACPF |
| `VCMOD` | number | ACPF-critical | Mode switch DC voltage; threshold for control mode switching in the DC line control logic during ACPF solution |
| `RCOMP` | number | ACPF-critical | Compounding resistance; adjusts the voltage regulation reference point for the DC line controller in ACPF |
| `DELTI` | number | ACPF-critical | Inverter firing angle margin in degrees; safety margin for commutation failure prevention, affecting inverter reactive power in ACPF |
| `METER` | string | ACPF-critical | Metered end indicator (R=rectifier, I=inverter); determines which converter's power is controlled to the setpoint in the ACPF DC line model |
| `DCVMIN` | number | ACPF-critical | Minimum DC voltage in per-unit; lower limit on DC voltage for converter control logic in ACPF |
| `CCCITMX` | integer | ACPF-critical | Maximum converter control iterations; convergence parameter for the DC converter control loop within ACPF |
| `CCCACC` | number | ACPF-critical | Converter control acceleration factor; convergence tuning parameter for the DC converter control loop in ACPF |
| `IPR` | integer | ACPF-critical | Rectifier AC bus number; identifies the AC bus where the rectifier injects/absorbs power, essential for ACPF network connectivity |
| `NBR` | integer | ACPF-critical | Number of rectifier bridges; determines the rectifier transformer configuration and commutation voltage in the ACPF converter model |
| `ANMXR` | number | ACPF-critical | Maximum rectifier firing angle in degrees; upper limit on rectifier control range affecting reactive power consumption in ACPF |
| `ANMNR` | number | ACPF-critical | Minimum rectifier firing angle in degrees; lower limit on rectifier control range for the ACPF converter model |
| `RCR` | number | ACPF-critical | Rectifier commutating resistance; part of the rectifier transformer impedance model affecting commutation overlap in ACPF |
| `XCR` | number | ACPF-critical | Rectifier commutating reactance; dominant commutation impedance determining overlap angle and reactive power in the ACPF converter model |
| `EBASR` | number | ACPF-critical | Rectifier primary-side base voltage in kV; voltage base for the rectifier converter transformer, needed for correct per-unit conversion in ACPF |
| `TRR` | number | ACPF-critical | Rectifier transformer ratio; off-nominal turns ratio for the rectifier converter transformer in ACPF |
| `TAPR` | number | ACPF-critical | Rectifier tap setting; current tap position of the rectifier converter transformer, affecting DC voltage in ACPF |
| `TMXR` | number | ACPF-critical | Maximum rectifier tap; upper limit on rectifier transformer tap adjustment range in ACPF |
| `TMNR` | number | ACPF-critical | Minimum rectifier tap; lower limit on rectifier transformer tap adjustment range in ACPF |
| `STPR` | number | ACPF-critical | Rectifier tap step size; discrete step increment for rectifier transformer tap changes in ACPF |
| `ICR` | integer | ACPF-critical | Rectifier firing angle control bus; AC bus used for converter control feedback in the ACPF DC line model |
| `IFR` | integer | ACPF-critical | Rectifier commutating bus (from-side); defines the from-bus of the rectifier commutating branch in ACPF |
| `ITR` | integer | ACPF-critical | Rectifier commutating bus (to-side); defines the to-bus of the rectifier commutating branch in ACPF |
| `IDR` | string | ACPF-critical | Rectifier circuit identifier; distinguishes parallel converter transformer circuits in the ACPF model |
| `XCAPR` | number | ACPF-critical | Rectifier capacitor reactance; capacitive compensation reactance at the rectifier terminal in ACPF |
| `IPI` | integer | ACPF-critical | Inverter AC bus number; identifies the AC bus where the inverter injects/absorbs power, essential for ACPF network connectivity |
| `NBI` | integer | ACPF-critical | Number of inverter bridges; determines the inverter transformer configuration and commutation voltage in ACPF |
| `ANMXI` | number | ACPF-critical | Maximum inverter firing angle in degrees; upper limit on inverter control range in the ACPF converter model |
| `ANMNI` | number | ACPF-critical | Minimum inverter firing angle in degrees; lower limit on inverter extinction angle for commutation safety in ACPF |
| `RCI` | number | ACPF-critical | Inverter commutating resistance; part of the inverter transformer impedance model in ACPF |
| `XCI` | number | ACPF-critical | Inverter commutating reactance; dominant commutation impedance for the inverter side in ACPF |
| `EBASI` | number | ACPF-critical | Inverter primary-side base voltage in kV; voltage base for the inverter converter transformer in ACPF |
| `TRI` | number | ACPF-critical | Inverter transformer ratio; off-nominal turns ratio for the inverter converter transformer in ACPF |
| `TAPI` | number | ACPF-critical | Inverter tap setting; current tap position of the inverter converter transformer in ACPF |
| `TMXI` | number | ACPF-critical | Maximum inverter tap; upper limit on inverter transformer tap range in ACPF |
| `TMNI` | number | ACPF-critical | Minimum inverter tap; lower limit on inverter transformer tap range in ACPF |
| `STPI` | number | ACPF-critical | Inverter tap step size; discrete step increment for inverter transformer tap changes in ACPF |
| `ICI` | integer | ACPF-critical | Inverter firing angle control bus; AC bus used for inverter control feedback in ACPF |
| `IFI` | integer | ACPF-critical | Inverter commutating bus (from-side); defines the from-bus of the inverter commutating branch in ACPF |
| `ITI` | integer | ACPF-critical | Inverter commutating bus (to-side); defines the to-bus of the inverter commutating branch in ACPF |
| `IDI` | string | ACPF-critical | Inverter circuit identifier; distinguishes parallel inverter transformer circuits in the ACPF model |
| `XCAPI` | number | ACPF-critical | Inverter capacitor reactance; capacitive compensation reactance at the inverter terminal in ACPF |

All two-terminal DC fields are classified as ACPF-critical because HVDC converters interact with the AC system through reactive power consumption and active power injection, affecting ACPF convergence but not the DCPF formulation which does not model DC links.

## VSC DC

**Intermediate format table:** `vsc_dc`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 41
**Tier breakdown:** 0 DCPF-critical, 41 ACPF-critical, 0 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `NAME` | string | ACPF-critical | VSC DC line name serving as the primary key; required to identify and instantiate this VSC link in the ACPF power flow model |
| `MDC` | integer | ACPF-critical | Control mode determining how the VSC link operates in ACPF; affects active and reactive power control at both converter terminals |
| `RDC` | number | ACPF-critical | DC line resistance in ohms; determines DC power losses between converters, affecting the AC-side power balance in ACPF |
| `O1` | integer | ACPF-critical | Owner number 1 for the VSC link; in context of a Tier 2 ACPF device record, ownership is part of the complete device specification needed for model instantiation |
| `F1` | number | ACPF-critical | Ownership fraction for owner 1; part of the complete VSC device record needed for ACPF model instantiation |
| `O2` | integer | ACPF-critical | Owner number 2; part of the complete VSC device record specification |
| `F2` | number | ACPF-critical | Ownership fraction for owner 2; part of the complete VSC device record specification |
| `O3` | integer | ACPF-critical | Owner number 3; part of the complete VSC device record specification |
| `F3` | number | ACPF-critical | Ownership fraction for owner 3; part of the complete VSC device record specification |
| `O4` | integer | ACPF-critical | Owner number 4; part of the complete VSC device record specification |
| `F4` | number | ACPF-critical | Ownership fraction for owner 4; part of the complete VSC device record specification |
| `IBUS1` | integer | ACPF-critical | Converter 1 AC bus number; identifies the AC bus where converter 1 connects, essential for ACPF network topology |
| `TYPE1` | integer | ACPF-critical | Converter 1 type code; determines the converter operating characteristics in the ACPF model |
| `MODE1` | integer | ACPF-critical | Converter 1 control mode; specifies whether converter 1 controls active power, DC voltage, or other quantities in ACPF |
| `DCSET1` | number | ACPF-critical | Converter 1 DC setpoint; operating target value for the controlled quantity at converter 1 in ACPF |
| `ACSET1` | number | ACPF-critical | Converter 1 AC setpoint; AC-side voltage or reactive power target for converter 1 in ACPF |
| `ALOSS1` | number | ACPF-critical | Converter 1 loss coefficient A; constant term in the converter loss model affecting AC-side power balance in ACPF |
| `BLOSS1` | number | ACPF-critical | Converter 1 loss coefficient B; current-proportional loss term in the converter loss model for ACPF |
| `MINLOSS1` | number | ACPF-critical | Converter 1 minimum loss; floor on converter losses in the ACPF loss model |
| `SMAX1` | number | ACPF-critical | Converter 1 MVA rating; maximum apparent power capacity limiting converter operation in ACPF |
| `IMAX1` | number | ACPF-critical | Converter 1 current rating in amperes; maximum current capacity limiting converter operation in ACPF |
| `PWF1` | number | ACPF-critical | Converter 1 power weighting factor; determines power sharing between converters in the ACPF DC link model |
| `MAXQ1` | number | ACPF-critical | Converter 1 maximum reactive power in MVAR; upper Q limit for converter 1 affecting ACPF reactive power balance |
| `MINQ1` | number | ACPF-critical | Converter 1 minimum reactive power in MVAR; lower Q limit for converter 1 in ACPF |
| `REMOT1` | integer | ACPF-critical | Converter 1 remote bus for voltage control; identifies the bus whose voltage converter 1 regulates in ACPF |
| `RMPCT1` | number | ACPF-critical | Converter 1 MVAR percent for remote regulation; fraction of reactive range used for remote voltage control in ACPF |
| `IBUS2` | integer | ACPF-critical | Converter 2 AC bus number; identifies the AC bus where converter 2 connects, essential for ACPF network topology |
| `TYPE2` | integer | ACPF-critical | Converter 2 type code; determines converter 2 operating characteristics in the ACPF model |
| `MODE2` | integer | ACPF-critical | Converter 2 control mode; specifies whether converter 2 controls active power, DC voltage, or other quantities in ACPF |
| `DCSET2` | number | ACPF-critical | Converter 2 DC setpoint; operating target for the controlled quantity at converter 2 in ACPF |
| `ACSET2` | number | ACPF-critical | Converter 2 AC setpoint; AC-side voltage or reactive power target for converter 2 in ACPF |
| `ALOSS2` | number | ACPF-critical | Converter 2 loss coefficient A; constant term in converter 2 loss model for ACPF |
| `BLOSS2` | number | ACPF-critical | Converter 2 loss coefficient B; current-proportional loss term in converter 2 loss model for ACPF |
| `MINLOSS2` | number | ACPF-critical | Converter 2 minimum loss; floor on converter 2 losses in ACPF |
| `SMAX2` | number | ACPF-critical | Converter 2 MVA rating; maximum apparent power capacity for converter 2 in ACPF |
| `IMAX2` | number | ACPF-critical | Converter 2 current rating in amperes; maximum current capacity for converter 2 in ACPF |
| `PWF2` | number | ACPF-critical | Converter 2 power weighting factor; determines power sharing in the ACPF DC link model |
| `MAXQ2` | number | ACPF-critical | Converter 2 maximum reactive power in MVAR; upper Q limit for converter 2 in ACPF |
| `MINQ2` | number | ACPF-critical | Converter 2 minimum reactive power in MVAR; lower Q limit for converter 2 in ACPF |
| `REMOT2` | integer | ACPF-critical | Converter 2 remote bus for voltage control; identifies the bus whose voltage converter 2 regulates in ACPF |
| `RMPCT2` | number | ACPF-critical | Converter 2 MVAR percent for remote regulation; fraction of reactive range used for remote voltage control in ACPF |

## Impedance Correction

**Intermediate format table:** `impedance_correction`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 23
**Tier breakdown:** 0 DCPF-critical, 23 ACPF-critical, 0 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `T` | integer | ACPF-critical | Correction table number serving as the primary key; referenced by transformer TAB fields to apply piecewise-linear impedance corrections in ACPF |
| `T1` | number | ACPF-critical | Tap ratio or angle breakpoint 1 in the piecewise-linear impedance correction curve; defines where the correction factor changes in ACPF |
| `F1` | number | ACPF-critical | Impedance correction factor at breakpoint 1; multiplier applied to transformer impedance at this tap position in ACPF |
| `T2` | number | ACPF-critical | Tap ratio or angle breakpoint 2; second point in the piecewise-linear impedance correction curve for ACPF |
| `F2` | number | ACPF-critical | Impedance correction factor at breakpoint 2; multiplier for transformer impedance in ACPF |
| `T3` | number | ACPF-critical | Tap ratio or angle breakpoint 3; third point in the piecewise-linear correction curve for ACPF |
| `F3` | number | ACPF-critical | Impedance correction factor at breakpoint 3; multiplier for transformer impedance in ACPF |
| `T4` | number | ACPF-critical | Tap ratio or angle breakpoint 4; fourth point in the correction curve for ACPF |
| `F4` | number | ACPF-critical | Impedance correction factor at breakpoint 4; multiplier for transformer impedance in ACPF |
| `T5` | number | ACPF-critical | Tap ratio or angle breakpoint 5; fifth point in the correction curve for ACPF |
| `F5` | number | ACPF-critical | Impedance correction factor at breakpoint 5; multiplier for transformer impedance in ACPF |
| `T6` | number | ACPF-critical | Tap ratio or angle breakpoint 6; sixth point in the correction curve for ACPF |
| `F6` | number | ACPF-critical | Impedance correction factor at breakpoint 6; multiplier for transformer impedance in ACPF |
| `T7` | number | ACPF-critical | Tap ratio or angle breakpoint 7; seventh point in the correction curve for ACPF |
| `F7` | number | ACPF-critical | Impedance correction factor at breakpoint 7; multiplier for transformer impedance in ACPF |
| `T8` | number | ACPF-critical | Tap ratio or angle breakpoint 8; eighth point in the correction curve for ACPF |
| `F8` | number | ACPF-critical | Impedance correction factor at breakpoint 8; multiplier for transformer impedance in ACPF |
| `T9` | number | ACPF-critical | Tap ratio or angle breakpoint 9; ninth point in the correction curve for ACPF |
| `F9` | number | ACPF-critical | Impedance correction factor at breakpoint 9; multiplier for transformer impedance in ACPF |
| `T10` | number | ACPF-critical | Tap ratio or angle breakpoint 10; tenth point in the correction curve for ACPF |
| `F10` | number | ACPF-critical | Impedance correction factor at breakpoint 10; multiplier for transformer impedance in ACPF |
| `T11` | number | ACPF-critical | Tap ratio or angle breakpoint 11; eleventh point in the correction curve for ACPF |
| `F11` | number | ACPF-critical | Impedance correction factor at breakpoint 11; multiplier for transformer impedance in ACPF |

## Multi-Terminal DC

**Intermediate format table:** `multi_terminal_dc`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 8
**Tier breakdown:** 0 DCPF-critical, 8 ACPF-critical, 0 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `NAME` | string | ACPF-critical | Multi-terminal DC system name serving as the primary key; required to identify and instantiate this MTDC system in the ACPF model |
| `NCONV` | integer | ACPF-critical | Number of AC converters in the MTDC system; defines the system topology and determines how many converter models are created in ACPF |
| `NDCBS` | integer | ACPF-critical | Number of DC buses in the MTDC system; defines the DC-side network topology for the ACPF MTDC model |
| `NDCLN` | integer | ACPF-critical | Number of DC links in the MTDC system; defines the DC-side branch connectivity for ACPF |
| `MDC` | integer | ACPF-critical | Control mode for the MTDC system; determines the overall operating strategy affecting AC-side power injections in ACPF |
| `VCONV` | integer | ACPF-critical | DC voltage controlling converter number; identifies which converter maintains the DC voltage reference in the ACPF MTDC model |
| `VCMOD` | number | ACPF-critical | Mode switch DC voltage threshold; voltage level at which the MTDC control mode transitions during ACPF solution |
| `VCONVN` | integer | ACPF-critical | New voltage controlling converter after mode switch; backup converter for DC voltage control in the ACPF model |

## Multi-Section Line

**Intermediate format table:** `multi_section_line`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 13
**Tier breakdown:** 0 DCPF-critical, 12 ACPF-critical, 1 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | ACPF-critical | From-bus number of the multi-section line; identifies one endpoint of the grouped transmission corridor, essential for matching branches to multi-section groupings in ACPF |
| `J` | integer | ACPF-critical | To-bus number of the multi-section line; identifies the other endpoint of the grouped corridor for branch aggregation in ACPF |
| `ID` | string | ACPF-critical | Line identifier distinguishing parallel multi-section groupings; required to correctly associate branch sections with the correct multi-section line in ACPF |
| `MET` | integer | Informational | Metered end flag (1=from-bus, 2=to-bus); determines which end is used for loss allocation accounting, does not affect the power flow solution |
| `DUM1` | integer | ACPF-critical | Intermediate bus 1 along the multi-section line; defines the internal topology of the multi-section corridor by specifying section boundaries in ACPF |
| `DUM2` | integer | ACPF-critical | Intermediate bus 2; second section boundary bus in the multi-section line topology for ACPF |
| `DUM3` | integer | ACPF-critical | Intermediate bus 3; third section boundary bus in the multi-section line for ACPF |
| `DUM4` | integer | ACPF-critical | Intermediate bus 4; fourth section boundary in the multi-section line topology for ACPF |
| `DUM5` | integer | ACPF-critical | Intermediate bus 5; fifth section boundary in the multi-section line for ACPF |
| `DUM6` | integer | ACPF-critical | Intermediate bus 6; sixth section boundary in the multi-section line for ACPF |
| `DUM7` | integer | ACPF-critical | Intermediate bus 7; seventh section boundary in the multi-section line for ACPF |
| `DUM8` | integer | ACPF-critical | Intermediate bus 8; eighth section boundary in the multi-section line for ACPF |
| `DUM9` | integer | ACPF-critical | Intermediate bus 9; ninth section boundary in the multi-section line for ACPF |

## Zone

**Intermediate format table:** `zone`
**Record-type tier (from mapping guide):** Tier 3 -- Organizational / metadata
**Total fields:** 2
**Tier breakdown:** 0 DCPF-critical, 0 ACPF-critical, 2 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | Informational | Zone number serving as the primary key for geographic or administrative grouping; organizational identifier with no electrical effect on power flow computation |
| `ZONAME` | string | Informational | Zone name for human-readable identification; descriptive label for reporting purposes with no impact on power flow equations |

All Zone fields are Informational because Zone is a Tier 3 record type containing organizational metadata with no direct electrical effect on power flow.

## Interarea Transfer

**Intermediate format table:** `interarea_transfer`
**Record-type tier (from mapping guide):** Tier 3 -- Organizational / metadata
**Total fields:** 4
**Tier breakdown:** 0 DCPF-critical, 0 ACPF-critical, 4 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `ARFROM` | integer | Informational | From-area number for the scheduled transfer; administrative reference for interchange tracking with no direct effect on the power flow equations |
| `ARTO` | integer | Informational | To-area number for the scheduled transfer; administrative reference for interchange accounting, not a power flow variable |
| `TRID` | string | Informational | Transfer identifier distinguishing multiple transfers between the same area pair; administrative key with no electrical significance |
| `PTRAN` | number | Informational | Scheduled transfer amount in MW; reporting value for interchange accounting that does not directly enter the power flow solution as a variable or constraint |

All Interarea Transfer fields are Informational because Interarea Transfer is a Tier 3 record type. Interchange scheduling data is used for monitoring and reporting, not as a direct input to the power flow equations.

## Owner

**Intermediate format table:** `owner`
**Record-type tier (from mapping guide):** Tier 3 -- Organizational / metadata
**Total fields:** 2
**Tier breakdown:** 0 DCPF-critical, 0 ACPF-critical, 2 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | Informational | Owner number serving as the primary key for ownership entities; administrative identifier for cost allocation with no electrical effect on power flow |
| `OWNAME` | string | Informational | Owner name for human-readable identification; descriptive label for ownership tracking with no impact on power flow computation |

All Owner fields are Informational because Owner is a Tier 3 record type containing administrative metadata with no direct electrical effect on power flow.

## FACTS

**Intermediate format table:** `facts`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 14
**Tier breakdown:** 0 DCPF-critical, 14 ACPF-critical, 0 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `NAME` | string | ACPF-critical | FACTS device name serving as the primary key; required to identify and instantiate this device in the ACPF power flow model |
| `I` | integer | ACPF-critical | Sending end bus number; identifies the AC bus where the FACTS device connects, essential for ACPF network topology |
| `J` | integer | ACPF-critical | Terminal bus number (0=shunt device); determines whether the FACTS device operates as a shunt or series element in the ACPF Y-bus |
| `MODE` | integer | ACPF-critical | FACTS control mode determining the device operating behavior (e.g., voltage regulation, power flow control) in ACPF |
| `SET1` | number | ACPF-critical | Control setpoint 1; primary operating target for the FACTS device control logic in ACPF, interpretation depends on MODE |
| `SET2` | number | ACPF-critical | Control setpoint 2; secondary operating target for the FACTS device in ACPF, interpretation depends on MODE |
| `VSREF` | number | ACPF-critical | Series voltage reference in per-unit; reference voltage for the series element of the FACTS device in ACPF |
| `REMOT` | integer | ACPF-critical | Remote bus for voltage control; identifies the bus whose voltage the FACTS device regulates in ACPF |
| `MESSION` | number | ACPF-critical | Sending end impedance; impedance parameter of the FACTS device at the sending end, entering the ACPF Y-bus model |
| `LINX` | number | ACPF-critical | Series reactance in per-unit; the series reactive impedance of the FACTS device entering the ACPF Y-bus |
| `RMPCT` | number | ACPF-critical | MVAR percent for remote regulation; fraction of reactive capability allocated to remote bus voltage control in ACPF |
| `OWNER` | integer | ACPF-critical | Owner number for the FACTS device; in context of a Tier 2 ACPF device record, part of the complete device specification |
| `SET3` | number | ACPF-critical | Control setpoint 3; tertiary operating parameter for advanced FACTS control modes in ACPF |
| `SET4` | number | ACPF-critical | Control setpoint 4; quaternary operating parameter for advanced FACTS control modes in ACPF |

All FACTS fields are ACPF-critical because FACTS devices (SVCs, STATCOMs, TCSCs, UPFCs) provide dynamic reactive compensation and power flow control that directly affects ACPF convergence and voltage profiles but is not modeled in DCPF.

## Switched Shunt

**Intermediate format table:** `switched_shunt`
**Record-type tier (from mapping guide):** Tier 2 -- Required for ACPF accuracy
**Total fields:** 26
**Tier breakdown:** 0 DCPF-critical, 23 ACPF-critical, 3 Informational, 0 Discardable

| Field | Type | Tier | Rationale |
|-------|------|------|-----------|
| `I` | integer | ACPF-critical | Bus number where the switched shunt is connected; determines placement of the switched admittance in the Y-bus for ACPF voltage regulation |
| `MODSW` | integer | ACPF-critical | Control mode (0=fixed, 1=discrete, 2=continuous) determining how the switched shunt adjusts its susceptance during ACPF solution for voltage control |
| `ADJM` | integer | Informational | Adjustment method flag (0=steps, 1=direct); secondary control parameter indicating how shunt blocks are selected, typically at default |
| `STAT` | integer | ACPF-critical | Switched shunt status (1=in-service, 0=out-of-service); determines whether this device's susceptance is included in the ACPF Y-bus |
| `VSWHI` | number | ACPF-critical | Upper voltage control limit in per-unit; the voltage threshold above which the switched shunt reduces capacitive output in ACPF |
| `VSWLO` | number | ACPF-critical | Lower voltage control limit in per-unit; the voltage threshold below which the switched shunt increases capacitive output in ACPF |
| `SWREM` | integer | ACPF-critical | Remote bus for voltage control (0=local); identifies the bus whose voltage triggers switching actions in ACPF |
| `RMPCT` | number | Informational | MVAR percent for remote voltage regulation; fraction of reactive range allocated to remote voltage control, secondary tuning parameter |
| `RMIDNT` | string | Informational | Shunt identifier name; human-readable label for the switched shunt device with no effect on power flow computation |
| `BINIT` | number | ACPF-critical | Initial susceptance in MVAR; the starting reactive compensation value for the switched shunt at the beginning of ACPF iteration |
| `N1` | integer | ACPF-critical | Number of steps in shunt block 1; defines the discrete switching capacity of the first compensation block in ACPF |
| `B1` | number | ACPF-critical | Susceptance per step in block 1 in MVAR; the reactive power increment for each switching step of block 1 in ACPF |
| `N2` | integer | ACPF-critical | Number of steps in block 2; second discrete compensation block capacity for ACPF |
| `B2` | number | ACPF-critical | Susceptance per step in block 2 in MVAR; reactive increment for block 2 in ACPF |
| `N3` | integer | ACPF-critical | Number of steps in block 3; third discrete compensation block for ACPF |
| `B3` | number | ACPF-critical | Susceptance per step in block 3 in MVAR; reactive increment for block 3 in ACPF |
| `N4` | integer | ACPF-critical | Number of steps in block 4; fourth discrete compensation block for ACPF |
| `B4` | number | ACPF-critical | Susceptance per step in block 4 in MVAR; reactive increment for block 4 in ACPF |
| `N5` | integer | ACPF-critical | Number of steps in block 5; fifth discrete compensation block for ACPF |
| `B5` | number | ACPF-critical | Susceptance per step in block 5 in MVAR; reactive increment for block 5 in ACPF |
| `N6` | integer | ACPF-critical | Number of steps in block 6; sixth discrete compensation block for ACPF |
| `B6` | number | ACPF-critical | Susceptance per step in block 6 in MVAR; reactive increment for block 6 in ACPF |
| `N7` | integer | ACPF-critical | Number of steps in block 7; seventh discrete compensation block for ACPF |
| `B7` | number | ACPF-critical | Susceptance per step in block 7 in MVAR; reactive increment for block 7 in ACPF |
| `N8` | integer | ACPF-critical | Number of steps in block 8; eighth discrete compensation block for ACPF |
| `B8` | number | ACPF-critical | Susceptance per step in block 8 in MVAR; reactive increment for block 8 in ACPF |

ADJM, RMPCT, and RMIDNT are classified as Informational because ADJM is a secondary control method flag that does not affect the power flow equations, RMPCT is a tuning parameter for reactive allocation, and RMIDNT is a descriptive label.

## Tier Assignment Rules

**DCPF-critical assignment criteria (all must apply):**
- Field directly enters the DC power flow B-matrix, power injection vector, or topology adjacency structure.
- OR field determines whether a component is in-service (status fields that control topology).
- OR field is a transformer tap magnitude or phase-shifting angle (these scale effective reactance in DCPF).
- AND the record type is Tier 1 or Tier 2 (Tier 3 record types cannot contribute DCPF-critical fields).

**ACPF-critical assignment criteria (all must apply):**
- Field enters the AC power flow Y-bus matrix, voltage/reactive power constraints, or control mode logic, BUT is not needed for DCPF.
- OR field provides reactive power limits, voltage setpoints, tap ratio limits, or switching control parameters needed for ACPF convergence.
- OR field determines the per-unit base or convention mode (CW, CZ, CM) that affects interpretation of ACPF parameters.
- AND the record type is Tier 1 or Tier 2.

**Informational assignment criteria:**
- Field provides context, identification, or operational metadata that does not enter any power flow equation or control logic.
- OR field is in a Tier 3 record type (all fields in Tier 3 record types are Informational by definition, unless Discardable).
- AND the field is NOT flagged as `x-psse-present-but-inactive` in Phase 1 D7.

**Discardable assignment criteria:**
- Field IS flagged as `x-psse-present-but-inactive: true` in Phase 1 D7.
- This is the sole criterion -- no field may be Discardable without this flag.

## v10 Reclassification Note

Seven fields were reclassified from DCPF-critical to Informational in protocol v10 (2026-03-13):

| Table | Field | Previous Tier | New Tier | Rationale |
|-------|-------|--------------|----------|-----------|
| load | ID | DCPF-critical | Informational | Identifier-only; bus injection sum is unaffected by its absence |
| generator | ID | DCPF-critical | Informational | Identifier-only; bus injection sum is unaffected by its absence |
| branch | CKT | DCPF-critical | Informational | Identifier-only; branch enumeration by index preserves B-matrix |
| transformer | CKT | DCPF-critical | Informational | Identifier-only; same rationale as branch.CKT |
| transformer | K | DCPF-critical | Informational | Star-equivalent conversion preserves DCPF topology |
| transformer | X2_3 | DCPF-critical | Informational | Star-equivalent impedances embed X2_3; DCPF accuracy preserved |
| transformer | X3_1 | DCPF-critical | Informational | Same rationale as X2_3 |

**Impact:** DCPF-critical field count reduced from 26 to 19. G-FNM-2 pass condition
(100% DCPF-critical coverage) evaluated against 19 fields from v10 onward. Existing
G-FNM-2 results produced under v9 remain valid for their protocol version.

## Cross-References

- [Intermediate Schema Reference](intermediate-schema.md) -- field definitions and semantics (PRD 01)
- [Record-Type Mapping Guide](mapping-guide.md) -- record-type tier classification (PRD 02)
- [Per-Unit Convention Reference](per-unit-conventions.md) -- per-unit base assignments (PRD 03)
- [3-Winding Transformer Reference](three-winding-transformers.md) -- transformer field semantics (PRD 04)
- Phase 1 D7 JSON Schema files (`../intermediate/schemas/`) -- normative field inventories and `x-psse-*` annotations
