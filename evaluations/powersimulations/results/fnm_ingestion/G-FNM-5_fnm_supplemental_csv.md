---
test_id: G-FNM-5
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: a735a0e7
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.47
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 234
solver: null
ingestion_path: matpower_raw
sced_mode: null
test_category: null
timestamp: "2026-03-24T22:10:00Z"
---

# G-FNM-5: Supplemental CSV Representability Assessment

## Result: INFORMATIONAL

PowerSimulations.jl (via PowerSystems.jl v4.6.2) achieves the highest native field
coverage among all six evaluated tools: **50% native, 30% extension, 20% external**
across 44 fields in 7 supplemental CSVs. This lead is driven by first-class support
for contingency definitions (83% native) and transmission interfaces (60%/67% native).

## Approach

1. Read supplemental CSV field definitions from `data/fnm/docs/supplemental-csvs.md`.
2. Read analytical classifications from `data/fnm/docs/supplemental-csv-representability.md`.
3. Verified PowerSystems.jl type structure via Julia introspection in the devcontainer:
   - Confirmed `ext::Dict{String,Any}` field on all component types (ACBus, ThermalStandard,
     Line, TapTransformer, Transformer2W, Area).
   - Confirmed `Contingency` abstract type exists with concrete subtypes (`PlannedOutage`,
     `GeometricDistributionForcedOutage`, `TimeSeriesForcedOutage`) under the intermediate
     `Outage` abstract type.
   - Confirmed `TransmissionInterface` concrete type with fields: `name`, `available`,
     `active_power_flow_limits`, `violation_penalty`, `direction_mapping`, `internal`.
4. Classified each field as N (native), E (extension via `ext` dict), or X (external).

## Per-CSV Representability

### LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| FROM_BUS | N | `Arc.from` (bus reference on Line/TapTransformer) |
| TO_BUS | N | `Arc.to` (bus reference on Line/TapTransformer) |
| CKT | E | `component.ext["CKT"]` -- circuit identifier stored in ext dict |
| ELEMENT_TYPE | E | `component.ext["ELEMENT_TYPE"]` -- derivable from Julia type (Line vs TapTransformer) but not a native field; type dispatch is the idiomatic way |
| RATE_A | N | `Line.rating` / `TapTransformer.rating` -- single native rating field |
| RATE_B | E | `component.ext["RATE_B"]` -- no native multi-tier rating |
| RATE_C | E | `component.ext["RATE_C"]` |
| RATE_D | E | `component.ext["RATE_D"]` |
| STATUS | N | `available` field on all branch types |
| EFFECTIVE_DATE | E | `component.ext["EFFECTIVE_DATE"]` -- no native temporal validity |

**Summary:** 4 N (40%), 6 E (60%), 0 X (0%)

PowerSystems.jl has a single `rating` field per branch, supporting only RATE_A natively.
Multi-tier ratings (B/C/D) require the `ext` dictionary. The EFFECTIVE_DATE concept has
no temporal analog in the data model.

**Extension approach for E fields:** All extension fields use the documented
`ext::Dict{String,Any}` field present on every PowerSystems.jl component. Usage:
`line.ext["RATE_B"] = 890.0`. The `ext` dict is preserved through serialization and
accessible from any code with a component reference, but is not semantically interpreted
by PowerSimulations.jl solvers. Enforcing multi-tier rating limits in OPF requires
custom constraint formulation via `get_jump_model()`.

### TRADING_HUB.csv (4 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| HUB_NAME | X | No hub/zone aggregation concept in PowerSystems.jl |
| BUS_NUMBER | N | `ACBus.number` |
| DISTRIBUTION_FACTOR | X | No distribution factor attribute on buses or generators |
| HUB_TYPE | X | No trading hub type concept |

**Summary:** 1 N (25%), 0 E (0%), 3 X (75%)

**X justification:** Trading hubs are a market-layer concept entirely outside
PowerSystems.jl's domain model. The `LoadZone` and `Area` types exist but represent
ISO operational zones, not market trading hubs with weighted bus compositions. A trading
hub maps a named aggregate to a set of buses with distribution factors -- this is a
settlement-layer concept that no power flow tool models natively. An analyst must maintain
hub definitions in an external DataFrame or dictionary and compute hub-level LMPs as a
weighted sum of nodal LMPs post-solve.

### GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| GEN_BUS | N | `ThermalStandard.bus` |
| GEN_ID | E | `generator.ext["GEN_ID"]` |
| HUB_NAME | X | No hub model |
| PARTICIPATION_FACTOR | X | No market participation factor attribute |
| GEN_NAME | N | `ThermalStandard.name` |

**Summary:** 2 N (40%), 1 E (20%), 2 X (40%)

**Extension approach for GEN_ID:** `generator.ext["GEN_ID"] = "G1"`. The ext dict
stores the PSS/E machine identifier alongside the PowerSystems.jl component name.

**X justification:** PARTICIPATION_FACTOR is a market allocation weight determining
how a generator's output is credited across trading hubs. This is a settlement
calculation parameter, not a generator electrical characteristic. HUB_NAME references
the trading hub (itself external), making this field necessarily external as well.

### CONTINGENCY.csv (6 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| CONTINGENCY_NAME | N | `Contingency` type hierarchy (abstract) with named subtypes |
| ELEMENT_TYPE | N | Derivable from contingency element type (branch vs generator) |
| ELEMENT_FROM_BUS | N | `Arc.from` on tripped branch |
| ELEMENT_TO_BUS | N | `Arc.to` on tripped branch |
| ELEMENT_CKT | E | `component.ext["CKT"]` |
| ELEMENT_BUS | N | Generator bus reference |

**Summary:** 5 N (83%), 1 E (17%), 0 X (0%)

PowerSystems.jl has first-class contingency support via the `Contingency` abstract type
hierarchy: `Contingency` > `Outage` > {`PlannedOutage`, `GeometricDistributionForcedOutage`,
`TimeSeriesForcedOutage`}. This is the joint-highest contingency coverage alongside
GridCal (83% native). The single extension field (CKT) is the circuit identifier needed
to disambiguate parallel branches between the same bus pair.

**Extension approach for ELEMENT_CKT:** `component.ext["CKT"] = "1"`. The circuit
identifier is stored in the ext dict of the contingency's associated component.

### INTERFACE.csv (5 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| INTERFACE_ID | N | `TransmissionInterface.name` (string identifier) |
| INTERFACE_NAME | N | `TransmissionInterface.name` |
| NORMAL_LIMIT_MW | N | `TransmissionInterface.active_power_flow_limits` |
| EMERGENCY_LIMIT_MW | E | `interface.ext["EMERGENCY_LIMIT_MW"]` -- only one limit pair native |
| DIRECTION | E | `interface.ext["DIRECTION"]` -- direction_mapping covers element directions, not interface-level flow direction convention |

**Summary:** 3 N (60%), 2 E (40%), 0 X (0%)

PowerSystems.jl is the only tool with a native `TransmissionInterface` type. The type
includes `active_power_flow_limits` (a `MinMax` named tuple) for normal limits and
`direction_mapping` (a `Dict{String,Int}` mapping branch names to direction coefficients)
for element directions. Emergency limits and the interface-level flow direction convention
require extension.

**Extension approach for E fields:**
- `interface.ext["EMERGENCY_LIMIT_MW"] = 1200.0` stores the emergency rating.
- `interface.ext["DIRECTION"] = "A_TO_B"` stores the flow direction convention.
The `violation_penalty` field on `TransmissionInterface` could be repurposed to encode
emergency limit enforcement, but this would be semantically incorrect.

### INTERFACE_ELEMENT.csv (6 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| INTERFACE_ID | N | Reference to parent `TransmissionInterface` |
| FROM_BUS | N | `Arc.from` on member branch |
| TO_BUS | N | `Arc.to` on member branch |
| CKT | E | `component.ext["CKT"]` |
| DIRECTION_COEFF | N | `TransmissionInterface.direction_mapping` |
| WEIGHT_FACTOR | E | `component.ext["WEIGHT_FACTOR"]` |

**Summary:** 4 N (67%), 2 E (33%), 0 X (0%)

**Extension approach for E fields:**
- `component.ext["CKT"] = "1"` for circuit identifier.
- `component.ext["WEIGHT_FACTOR"] = 1.0` for the weight factor in interface flow
  calculation. The `direction_mapping` Dict natively carries direction coefficients
  (+1/-1) but not arbitrary weight factors.

### OUTAGE.csv (8 fields)

| Field | Tier | Mechanism |
|-------|------|-----------|
| ELEMENT_TYPE | X | No outage schedule model with element type classification |
| ELEMENT_FROM_BUS | N | `Arc.from` |
| ELEMENT_TO_BUS | N | `Arc.to` |
| ELEMENT_CKT | E | `component.ext["CKT"]` |
| ELEMENT_BUS | N | Generator bus reference |
| OUTAGE_START | X | No temporal outage schedule (only `available` flag) |
| OUTAGE_END | X | No temporal outage schedule |
| OUTAGE_TYPE | X | No outage classification concept |

**Summary:** 3 N (38%), 1 E (12%), 4 X (50%)

**X justification:** PowerSystems.jl has `available` and `must_run` flags on components,
and the `Contingency` type hierarchy includes `PlannedOutage` with an `outage_schedule`
field. However, `PlannedOutage.outage_schedule` is designed for probabilistic outage
modeling (generation reliability studies), not deterministic temporal scheduling with
calendar start/end dates. The OUTAGE.csv fields represent deterministic maintenance
scheduling -- a calendar-based concept where specific equipment is taken out of service
during defined time windows. This requires a temporal event model (start date, end date,
outage category) that has no structural analog in any power flow tool's domain model.
An analyst must maintain outage schedules in an external data structure and modify
component `available` flags per simulation period.

## Aggregate Summary

| CSV | Fields | N | E | X | N% | E% | X% |
|-----|--------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER | 10 | 4 | 6 | 0 | 40% | 60% | 0% |
| TRADING_HUB | 4 | 1 | 0 | 3 | 25% | 0% | 75% |
| GEN_DISTRIBUTION_FACTOR | 5 | 2 | 1 | 2 | 40% | 20% | 40% |
| CONTINGENCY | 6 | 5 | 1 | 0 | 83% | 17% | 0% |
| INTERFACE | 5 | 3 | 2 | 0 | 60% | 40% | 0% |
| INTERFACE_ELEMENT | 6 | 4 | 2 | 0 | 67% | 33% | 0% |
| OUTAGE | 8 | 3 | 1 | 4 | 38% | 12% | 50% |
| **Total** | **44** | **22** | **13** | **9** | **50%** | **30%** | **20%** |

## Market Solution Fidelity Summary

| Data Concept | Representability | Phase 2 Impact |
|--------------|-----------------|----------------|
| Thermal ratings (4-tier) | Extension | Requires custom constraint formulation via `get_jump_model()` to enforce multi-tier limits in OPF |
| Seasonal rating variations | Extension | Temporal rating changes need manual ext dict management per simulation period |
| Trading hub definitions | External | Hub-level LMP aggregation fully external; weighted sum of nodal LMPs computed post-solve |
| Generator distribution factors | External | Hub allocation requires post-solve external computation using distribution factor weights |
| Contingency definitions | **Native** | N-1/N-2 analysis directly consumable; `Contingency` type hierarchy provides first-class support |
| Interface flow limits | **Native** (normal) / Extension (emergency) | Normal limits natively enforced via `TransmissionInterface.active_power_flow_limits`; emergency requires ext |
| Interface element composition | **Native** | Branch-to-interface mapping stored in `TransmissionInterface.direction_mapping` Dict |
| Outage schedules | External | Temporal outage application requires external scripting to toggle `available` flags per period |

### Key Strengths

PowerSimulations.jl's native coverage is driven by two differentiating capabilities:

1. **Contingency support** (83% native in CONTINGENCY.csv): The `Contingency` abstract type
   hierarchy (`Contingency` > `Outage` > `PlannedOutage` / `GeometricDistributionForcedOutage` /
   `TimeSeriesForcedOutage`) provides first-class contingency definitions. Only GridCal matches
   this coverage among the six tools.

2. **Interface support** (60% native in INTERFACE.csv, 67% in INTERFACE_ELEMENT.csv): The
   `TransmissionInterface` type with `direction_mapping` and `active_power_flow_limits` is
   unique among the evaluated tools. MATPOWER is the only other tool with any native
   interface representation (40% native via `mpc.if`/`mpc.iflim`).

### Key Gaps

1. **Trading hubs** (75% external): Universal gap across all tools. No power flow tool
   models trading hubs natively. This is inherent to the domain separation between power
   system modeling and market settlement.

2. **Outage schedules** (50% external): PowerSystems.jl's `PlannedOutage` type handles
   probabilistic outage modeling, not deterministic temporal scheduling. An analyst must
   maintain outage schedules externally and modify component `available` flags per period.

3. **Multi-tier thermal ratings** (RATE_B/C/D as extension): Only one native rating per
   branch. This is shared with PyPSA, pandapower, and GridCal. PowerModels.jl and MATPOWER
   have 3 native tiers (RATE_A/B/C).

### Extension Mechanism

All extension-tier fields use the `ext::Dict{String,Any}` field present on every
PowerSystems.jl component type. Usage:

```julia
# Store extension data
line = get_component(Line, sys, "line_name")
line.ext["RATE_B"] = 890.0
line.ext["RATE_C"] = 1050.0
line.ext["EFFECTIVE_DATE"] = "2024-06-01"

# Retrieve extension data
rate_b = line.ext["RATE_B"]
```

The `ext` dict is preserved through serialization/deserialization and is accessible from
any code that has a reference to the component. It is not semantically interpreted by
PowerSimulations.jl solvers -- enforcement of extension-tier data (e.g., multi-tier
rating limits) requires custom constraint formulation via `get_jump_model()`.

## Timing

- **Wall-clock:** 1.47s (type introspection and classification only)
- **Timing source:** measured
- **Peak memory:** not measured (analytical assessment with minimal data loading)

## Test Script

**Path:** `evaluations/powersimulations/tests/fnm_ingestion/test_g_fnm_5_fnm_supplemental_csv.jl`

Key verification code:
```julia
# Confirm ext field on all component types
for T in [PS.ACBus, PS.ThermalStandard, PS.Line, PS.TapTransformer]
    has_ext = :ext in fieldnames(T)
end

# Confirm TransmissionInterface type
PS.TransmissionInterface  # concrete type
fieldnames(PS.TransmissionInterface)
# => (:name, :available, :active_power_flow_limits, :violation_penalty,
#     :direction_mapping, :internal)

# Confirm Contingency type hierarchy
isabstracttype(PS.Contingency)  # true
# Subtypes: Outage > {PlannedOutage, GeometricDistributionForcedOutage,
#                      TimeSeriesForcedOutage}
```
