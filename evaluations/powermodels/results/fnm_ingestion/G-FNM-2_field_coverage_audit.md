---
test_id: G-FNM-2
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: 2b7a381c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.0
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 43
solver: null
timestamp: "2026-03-13T23:15:00Z"
---

# G-FNM-2: Field Coverage Audit

## Result: PASS

All 19 DCPF-critical fields are present in the PowerModels data model after loading the
MATPOWER fallback case. ACPF-critical coverage is 19/237 (8.0%) and Informational coverage
is 11/87 (12.6%). The low ACPF/Informational rates are structural consequences of the
MATPOWER PPC format, which flattens transformer data into the branch table and does not
carry record types outside the core five (bus, load, generator, branch, shunt).

## Approach

PowerModels.parse_file loaded the MATPOWER fallback at
`data/fnm/reference/cleaned/fnm_main_island.m` (as established by G-FNM-1). After loading,
each top-level data table's field keys were enumerated and mapped to the corresponding
intermediate schema fields using the field criticality matrix.

The PowerModels internal data model after MATPOWER ingestion contains these tables:
- `bus` (27,862 entries, 12 fields per entry)
- `load` (8,624 entries, 6 fields)
- `gen` (5,741 entries, 23 fields)
- `branch` (32,606 entries, 19 fields -- includes both lines and transformers)
- `shunt` (3,110 entries, 6 fields)
- `dcline` (empty), `storage` (empty), `switch` (empty)

## Output

### PowerModels Field Inventory

**Bus fields (12):** area, base_kv, bus_i, bus_type, index, name, source_id, va, vm, vmax, vmin, zone

**Load fields (6):** index, load_bus, pd, qd, source_id, status

**Generator fields (23):** apf, gen_bus, gen_status, index, mbase, pc1, pc2, pg, pmax, pmin, qc1max, qc1min, qc2max, qc2min, qg, qmax, qmin, ramp_10, ramp_30, ramp_agc, ramp_q, source_id, vg

**Branch fields (19):** angmax, angmin, b_fr, b_to, br_r, br_status, br_x, f_bus, g_fr, g_to, index, rate_a, rate_b, rate_c, shift, source_id, t_bus, tap, transformer

**Shunt fields (6):** bs, gs, index, shunt_bus, source_id, status

### DCPF-Critical Coverage: 19/19 (100.0%)

All DCPF-critical fields from the five relevant record types are present in the PowerModels
data model. The MATPOWER PPC format preserves all fields needed for DC power flow.

| Record Type | Schema Field | PM Field | Present |
|-------------|-------------|----------|---------|
| **Bus** | I | bus_i | Yes |
| | IDE | bus_type | Yes |
| | VA | va | Yes |
| **Load** | I | load_bus | Yes |
| | STATUS | status | Yes |
| | PL | pd | Yes |
| **Generator** | I | gen_bus | Yes |
| | PG | pg | Yes |
| | STAT | gen_status | Yes |
| **Branch** | I | f_bus | Yes |
| | J | t_bus | Yes |
| | X | br_x | Yes |
| | ST | br_status | Yes |
| **Transformer** | I | f_bus | Yes |
| | J | t_bus | Yes |
| | STAT | br_status | Yes |
| | X1_2 | br_x | Yes |
| | WINDV1 | tap | Yes |
| | ANG1 | shift | Yes |

Note: Transformer fields map to the branch table in MATPOWER PPC format. The MATPOWER
converter pre-computes tap ratios and phase shift angles into the branch's `tap` and `shift`
fields, and transformer reactance into `br_x`. Three-winding transformers are pre-expanded
into star-equivalent two-winding pairs, preserving the B-matrix structure.

### ACPF-Critical Coverage: 19/237 (8.0%)

| Record Type | Total ACPF Fields | Present | Missing | Notes |
|-------------|------------------:|--------:|--------:|-------|
| Bus | 2 | 2 | 0 | BASKV->base_kv, VM->vm |
| Load | 5 | 1 | 4 | QL->qd present; IP, IQ, YP, YQ absent (ZIP load components lost) |
| Fixed Shunt | 5 | 4 | 1 | I->shunt_bus, STATUS, GL->gs, BL->bs present; ID absent |
| Generator | 5 | 4 | 1 | QG->qg, QT->qmax, QB->qmin, VS->vg present; IREG absent |
| Branch | 6 | 6 | 0 | R->br_r, B->b_fr/b_to, GI->g_fr, BI->b_fr, GJ->g_to, BJ->b_to |
| Transformer | 44 | 2 | 42 | R1_2->br_r, RATA1->rate_a present; CW/CZ/CM, MAG1/2, SBASE, COD, CONT, tap limits, NTP, NOMV, winding 2/3 details all lost |
| Area | 3 | 0 | 3 | ISW, PDES, PTOL absent (no area interchange table) |
| Two-Terminal DC | 46 | 0 | 46 | No HVDC lines in MATPOWER fallback |
| VSC DC | 41 | 0 | 41 | Not representable in MATPOWER PPC |
| Impedance Correction | 23 | 0 | 23 | Not representable in MATPOWER PPC |
| Multi-Terminal DC | 8 | 0 | 8 | Not representable in MATPOWER PPC |
| Multi-Section Line | 12 | 0 | 12 | Not representable in MATPOWER PPC |
| FACTS | 14 | 0 | 14 | Not representable in MATPOWER PPC |
| Switched Shunt | 23 | 0 | 23 | Converted to fixed shunts in MATPOWER; discrete step data lost |
| **Total** | **237** | **19** | **218** | **8.0%** |

Key ACPF-critical gaps:

1. **ZIP load components (IP, IQ, YP, YQ):** MATPOWER PPC carries only constant-power (PL/QL)
   load. Voltage-dependent load models are not preserved.
2. **Generator IREG (remote regulated bus):** Lost in MATPOWER conversion. All generators
   appear to regulate locally. This affects voltage regulation topology.
3. **Transformer detailed fields (42 of 44):** MATPOWER flattens transformer data into the
   branch table, preserving only impedance and tap/shift but losing control mode (COD),
   controlled bus (CONT), tap limits (RMA/RMI), voltage targets (VMA/VMI), tap positions (NTP),
   nominal voltages (NOMV), magnetizing admittance (MAG1/MAG2), winding I/O codes (CW/CZ/CM),
   MVA base (SBASE), and all winding 2/3 details except those embedded in star-equivalent.
4. **Entire record types absent:** Area interchange, HVDC, VSC DC, impedance correction,
   multi-terminal DC, multi-section line, FACTS, and switched shunt record types have no
   representation in the MATPOWER PPC format and are therefore completely absent from
   PowerModels after loading.

### Informational Coverage: 11/87 (12.6%)

| Record Type | Total Info Fields | Present | Notes |
|-------------|------------------:|--------:|-------|
| Bus | 8 | 5 | NAME, AREA, ZONE, NVHI->vmax, NVLO->vmin present; OWNER, EVHI, EVLO absent |
| Load | 5 | 0 | ID, AREA, ZONE, OWNER, SCALE all absent |
| Generator | 19 | 3 | MBASE->mbase, PT->pmax, PB->pmin present; ID, impedance, ownership fields absent |
| Branch | 13 | 3 | RATEA->rate_a, RATEB->rate_b, RATEC->rate_c present; CKT, MET, LEN, ownership absent |
| Transformer | 29 | 0 | K, CKT, NMETR, NAME, VECGRP, emergency/short-term ratings, TAB, CR, CX, CNXA, ownership all absent |
| Zone | 2 | 0 | Not in MATPOWER PPC |
| Interarea Transfer | 4 | 0 | Not in MATPOWER PPC |
| Owner | 2 | 0 | Not in MATPOWER PPC |
| Switched Shunt | 3 | 0 | Discrete step info lost |
| Multi-Section Line | 1 | 0 | Not in MATPOWER PPC |
| **Total** | **87** | **11** | **12.6%** |

### Coverage Summary

| Tier | Present | Total | Coverage |
|------|--------:|------:|---------:|
| DCPF-critical | 19 | 19 | **100.0%** |
| ACPF-critical | 19 | 237 | 8.0% |
| Informational | 11 | 87 | 12.6% |
| Discardable | 0 | 0 | N/A |
| **All fields** | **49** | **343** | **14.3%** |

## Workarounds

None required for the DCPF-critical pass condition. The MATPOWER fallback path (documented
in G-FNM-1) is an inherent limitation for ACPF-critical and Informational coverage, but the
pass condition requires only DCPF-critical completeness.

## Timing

- **Wall-clock:** ~3.0 s (MATPOWER parse time, reused from G-FNM-1)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powermodels/tests/fnm_ingestion/test_g_fnm_2_field_coverage_audit.jl`

Key inspection code:

```julia
data = PowerModels.parse_file("/workspace/data/fnm/reference/cleaned/fnm_main_island.m")

# Enumerate fields per table
bus_keys = sort(collect(keys(data["bus"][first(keys(data["bus"]))])))
# => ["area", "base_kv", "bus_i", "bus_type", "index", "name", "source_id",
#     "va", "vm", "vmax", "vmin", "zone"]

branch_keys = sort(collect(keys(data["branch"][first(keys(data["branch"]))])))
# => ["angmax", "angmin", "b_fr", "b_to", "br_r", "br_status", "br_x",
#     "f_bus", "g_fr", "g_to", "index", "rate_a", "rate_b", "rate_c",
#     "shift", "source_id", "t_bus", "tap", "transformer"]
```
