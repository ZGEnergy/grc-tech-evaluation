---
test_id: G-FNM-2
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v9
skill_version: v1
test_hash: 1dd6a61c
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 0.5
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 333
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# G-FNM-2: Field Coverage Audit

## Result: FAIL

## Finding

PyPSA achieves **73.1% DCPF-critical field coverage** (19 of 26 fields) when ingesting
the FNM via the MATPOWER PPC pathway. The pass condition requires 100%. Seven
DCPF-critical fields are structurally absent because the MATPOWER PPC format does not
carry PSS/E identifier fields (ID, CKT) or 3-winding transformer topology (K, X2_3,
X3_1). ACPF-critical coverage is 34.7% (17 of 49 fields).

## Evidence

### Tier Summary (Core Tables Only)

| Tier | Total Fields | Present | Missing | Coverage |
|------|-------------|---------|---------|----------|
| DCPF-critical | 26 | 19 | 7 | 73.1% |
| ACPF-critical | 49 | 17 | 32 | 34.7% |
| Informational | 37 | 12 | 25 | 32.4% |

### Missing DCPF-Critical Fields

| Table | Field | Reason |
|-------|-------|--------|
| load | ID | PPC aggregates multiple loads per bus into single Pd/Qd values; load-level IDs lost |
| generator | ID | PPC uses row indices, not 2-character machine IDs; generators distinguished by position |
| branch | CKT | PPC uses row indices for parallel branches; circuit identifiers lost |
| transformer | CKT | Same as branch — no circuit identifier in PPC format |
| transformer | K | 3-winding bus number; PPC converts 3W transformers to star-equivalent 2W pairs |
| transformer | X2_3 | Winding 2-3 reactance; 3W transformer data lost in PPC conversion |
| transformer | X3_1 | Winding 3-1 reactance; 3W transformer data lost in PPC conversion |

### Per-Table Coverage Breakdown

#### Bus (13 fields)

| Field | Tier | PyPSA Attribute | Present |
|-------|------|-----------------|---------|
| I | DCPF-critical | index | Yes |
| IDE | DCPF-critical | control | Yes |
| VA | DCPF-critical | v_ang_set | Yes |
| BASKV | ACPF-critical | v_nom | Yes |
| VM | ACPF-critical | v_mag_pu_set | Yes |
| NAME | Informational | — | No |
| AREA | Informational | area | Yes |
| ZONE | Informational | zone | Yes |
| OWNER | Informational | — | No |
| NVHI | Informational | v_mag_pu_max | Yes |
| NVLO | Informational | v_mag_pu_min | Yes |
| EVHI | Informational | — | No |
| EVLO | Informational | — | No |

DCPF-critical: 3/3 = 100%. ACPF-critical: 2/2 = 100%.

#### Load (13 fields, 8 tested)

| Field | Tier | PyPSA Attribute | Present |
|-------|------|-----------------|---------|
| I | DCPF-critical | bus | Yes |
| ID | DCPF-critical | — | No (PPC aggregates loads per bus) |
| STATUS | DCPF-critical | active | Yes |
| PL | DCPF-critical | p_set | Yes |
| QL | ACPF-critical | q_set | Yes |
| IP | ACPF-critical | — | No |
| IQ | ACPF-critical | — | No |
| YP | ACPF-critical | — | No |
| YQ | ACPF-critical | — | No |

DCPF-critical: 3/4 = 75%. Missing: ID.

#### Generator (28 fields, 22 tested)

| Field | Tier | PyPSA Attribute | Present |
|-------|------|-----------------|---------|
| I | DCPF-critical | bus | Yes |
| ID | DCPF-critical | — | No (PPC uses row index) |
| PG | DCPF-critical | p_set | Yes |
| STAT | DCPF-critical | active | Yes |
| QG | ACPF-critical | q_set | Yes |
| QT | ACPF-critical | q_max | Yes |
| QB | ACPF-critical | q_min | Yes |
| VS | ACPF-critical | v_set_pu | Yes |
| IREG | ACPF-critical | — | No |
| MBASE | Informational | mva_base | Yes |
| PT | Informational | p_nom | Yes |
| PB | Informational | p_min_pu | Yes |

DCPF-critical: 3/4 = 75%. Missing: ID.

#### Branch (24 fields, 18 tested)

| Field | Tier | PyPSA Attribute | Present |
|-------|------|-----------------|---------|
| I | DCPF-critical | bus0 | Yes |
| J | DCPF-critical | bus1 | Yes |
| CKT | DCPF-critical | — | No (PPC uses row index) |
| X | DCPF-critical | x | Yes |
| ST | DCPF-critical | active/status | Yes |
| R | ACPF-critical | r | Yes |
| B | ACPF-critical | b | Yes |
| GI | ACPF-critical | — | No |
| BI | ACPF-critical | — | No |
| GJ | ACPF-critical | — | No |
| BJ | ACPF-critical | — | No |
| RATEA | Informational | s_nom | Yes |
| RATEB | Informational | rateB | Yes |
| RATEC | Informational | rateC | Yes |
| LEN | Informational | length | Yes |

DCPF-critical: 4/5 = 80%. Missing: CKT.

#### Transformer (83 fields, 31 tested)

| Field | Tier | PyPSA Attribute | Present |
|-------|------|-----------------|---------|
| I | DCPF-critical | bus0 | Yes |
| J | DCPF-critical | bus1 | Yes |
| K | DCPF-critical | — | No (PPC is 2W only) |
| CKT | DCPF-critical | — | No (PPC uses row index) |
| STAT | DCPF-critical | active/status | Yes |
| X1_2 | DCPF-critical | x | Yes |
| WINDV1 | DCPF-critical | tap_ratio | Yes |
| ANG1 | DCPF-critical | phase_shift | Yes |
| X2_3 | DCPF-critical | — | No (3W not in PPC) |
| X3_1 | DCPF-critical | — | No (3W not in PPC) |
| R1_2 | ACPF-critical | r | Yes |
| RATA1 | ACPF-critical | s_nom | Yes |
| CW/CZ/CM | ACPF-critical | — | No (PPC pre-converts) |
| MAG1/MAG2 | ACPF-critical | — | No |
| RATB1 | Informational | rateB | Yes |
| RATC1 | Informational | rateC | Yes |

DCPF-critical: 6/10 = 60%. Missing: K, CKT, X2_3, X3_1.

#### Fixed Shunt (5 fields)

All ACPF-critical. PPC carries bus-level Gs/Bs columns (aggregated). Present:
I (via bus index), GL (Gs), BL (Bs). Missing: per-shunt ID, STATUS.

ACPF-critical: 3/5 = 60%.

#### Switched Shunt (26 fields, 9 tested)

All ACPF-critical. PPC import does not carry switched shunt discrete steps.
Present: I (bus), BINIT (b), STAT (active). Missing: MODSW, VSWHI, VSWLO,
SWREM, N1, B1, and remaining block fields.

ACPF-critical: 3/9 tested = 33.3%.

#### Area (5 fields)

0 DCPF-critical, 3 ACPF-critical (ISW, PDES, PTOL), 2 Informational.
PyPSA PPC import does not create an area table. Only bus-level area number is
preserved (Informational). All ACPF-critical area fields are missing.

ACPF-critical: 0/3 = 0%.

### Tables Not Representable via PPC (0% coverage)

The following intermediate format tables have no representation in MATPOWER PPC
and are therefore entirely absent from PyPSA after PPC import:

| Table | Fields | DCPF-critical | ACPF-critical |
|-------|--------|---------------|---------------|
| two_terminal_dc | 46 | 0 | 46 |
| vsc_dc | 41 | 0 | 41 |
| impedance_correction | 23 | 0 | 23 |
| multi_terminal_dc | 8 | 0 | 8 |
| multi_section_line | 13 | 0 | 12 |
| zone | 2 | 0 | 0 |
| interarea_transfer | 4 | 0 | 0 |
| owner | 2 | 0 | 0 |
| facts | 14 | 0 | 14 |

None of these tables contain DCPF-critical fields, so their absence does not
affect the DCPF-critical pass condition. They contribute 144 ACPF-critical
fields that are entirely missing.

## Implications

**The DCPF-critical coverage failure is a structural limitation of the PPC
import pathway, not a PyPSA software deficiency.** The MATPOWER PPC format is
a simplified representation that:

1. **Drops identifier fields** (ID, CKT) — uses positional indexing instead
2. **Flattens 3-winding transformers** — MATPOWER converts to star-equivalent
   2-winding pairs during `.m` file creation, losing K, X2_3, X3_1
3. **Aggregates loads** — multiple PSS/E loads at one bus become a single Pd/Qd
4. **Omits entire record types** — no HVDC, FACTS, switched shunt details,
   areas, impedance corrections

For the 7 missing DCPF-critical fields:
- **ID/CKT (4 fields)**: The underlying electrical data is structurally preserved
  (separate rows in PPC arrays). Only the original PSS/E identifiers are lost.
  Power flow results are unaffected because the B-matrix is constructed from
  per-element reactance values, not from identifiers.
- **K/X2_3/X3_1 (3 fields)**: 3-winding transformer data is lost in MATPOWER
  conversion. The star-equivalent 2W pairs preserve the electrical behavior but
  lose the 3W topology. This is a MATPOWER limitation, not PyPSA.

**To achieve 100% DCPF-critical coverage, PyPSA would need a native PSS/E RAW
parser or a richer import format (e.g., CIM/CGMES, pandapower JSON) that
preserves these fields.** PyPSA does not have a native PSS/E RAW reader.

## Workarounds

- **What:** MATPOWER PPC format used as intermediate between PSS/E RAW and PyPSA
- **Why:** PyPSA has no native PSS/E RAW parser; PPC is the closest available format
- **Durability:** blocking — the PPC format fundamentally cannot carry ID/CKT fields
  or 3-winding transformer topology; no workaround within the PPC pathway
- **Grade impact:** DCPF-critical field coverage < 100% means the PPC import pathway
  cannot fully represent the FNM's identifier structure and 3W transformer topology
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 0.5 s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_2_field_coverage.py`
