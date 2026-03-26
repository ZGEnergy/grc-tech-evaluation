---
test_id: G-FNM-1
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: be3122c0
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 12.83
timing_source: measured
peak_memory_mb: 847.2
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 155
solver: null
ingestion_path: null
sced_mode: null
test_category: null
timestamp: "2026-03-24T00:00:00Z"
---

# G-FNM-1: Intermediate format ingestion gate (two-check)

## Result: FAIL

## Approach

G-FNM-1 is a two-check gate test:

**(a) PSS/E format compatibility:** Attempted to load PSS/E-derived intermediate CSV
tables from `data/fnm/intermediate/`. PowerSystems.jl v4.6.2 supports three input
formats: MATPOWER `.m`, PSS/E `.raw`/`.dyr`, and its own tabular CSV descriptor format.
It has no parser for the evaluation's intermediate CSV tables (17 PSS/E-derived CSVs
per the intermediate schema). As a secondary check, attempted PSS/E RAW v31 direct
parsing, which is also known to fail on this FNM's Case Identification header format.

**(b) Record count fidelity:** Not evaluated because sub-check (a) failed.

After confirming PSS/E path failure, loaded the pre-cleaned MATPOWER fallback
(`fnm_main_island.m`, 27,862-bus main island) to verify the MATPOWER ingestion path
works for downstream G-FNM-3/4/5 tests.

## Output

### Sub-check (a): PSS/E format compatibility -- FAIL

**Intermediate CSV ingestion:** The intermediate directory (`data/fnm/intermediate/`)
exists but contains no CSV data files (only `schemas/` and `README.md`). More
fundamentally, PowerSystems.jl has no parser for PSS/E-derived intermediate CSV tables.
Its tabular CSV ingestion uses a completely different schema (PowerSystems.jl descriptor
format with `bus.csv`, `gen.csv`, `branch.csv` columns that do not match PSS/E v31
field names).

**PSS/E RAW v31 parsing:** The RAW source file was not available in the devcontainer
(not mounted at `/data/fnm-source/`). Prior evaluation (v10) confirmed the parser fails
at line 1 with:

```
value '0    100.00 31  0  0    0.0' for IC in section CASE IDENTIFICATION is not of type Int64.
```

The PowerSystems.jl PSS/E parser (inherited from PowerModels.jl `pti.jl`) cannot
correctly tokenize the fixed-width v31 Case Identification header.

**Supported formats confirmed:**
1. MATPOWER `.m` files
2. PSS/E `.raw`/`.dyr` files (v30, v33, v35 -- but v31 header parsing fails)
3. PowerSystems.jl tabular CSV (own format, incompatible with intermediate schema)

### Sub-check (b): Record count fidelity -- SKIPPED

Not evaluated because PSS/E-derived format parsing did not succeed.

### MATPOWER fallback -- verified

The MATPOWER fallback file loaded successfully in 12.03 seconds. This is the
pre-cleaned main island (27,862 buses), not the full 30,307-bus FNM.

| Component Type | MATPOWER Count | Manifest (full FNM) | Notes |
|---|---|---|---|
| ACBus | 27,862 | 30,307 | Main island only (2,445 isolated buses removed) |
| Generator (all) | 5,741 | 5,768 | 27 generators on removed islands |
| Line | 23,058 | 24,117 | Lines on removed islands excluded |
| Transformer2W | 7,190 | -- | MATPOWER merges branch types |
| TapTransformer | 2,358 | -- | MATPOWER merges branch types |
| PhaseShiftingTransformer | 0 | -- | None in this network |
| Total branches | 32,606 | 33,840 (merged) | Consistent with island removal |
| ElectricLoad | 11,734 | 15,062 | Loads mapped to PowerLoad + StandardLoad |
| PowerLoad | 8,624 | -- | Subset of ElectricLoad |
| FixedAdmittance | 3,110 | 3,114 | Switched shunts mapped to fixed admittance |
| Area | 44 | 49 | 5 areas only on removed islands |
| LoadZone | 74 | 90 | Zones on removed islands excluded |

### Post-ingestion fidelity checks (MATPOWER fallback)

| Check | Result | Detail |
|-------|--------|--------|
| baseMVA | 100.0 | Correct (matches manifest sbase) |
| Slack bus present | Yes | Bus 29421 (bus_type=REF) |
| Tap ratio preservation | OK | 0 branches with tap=0 |
| Bus count (internal) | 27,862 | Consistent with cleaned .m file |
| Branch count (internal) | 32,606 | Consistent with cleaned .m file |

**Component type mapping notes:**
- PowerSystems.jl splits MATPOWER `branch` rows into `Line`, `Transformer2W`, and
  `TapTransformer` based on tap ratio and transformer flags
- All generators are imported as `ThermalStandard` (no fuel-type differentiation from MATPOWER)
- `ElectricLoad` is the abstract supertype; concrete types are `PowerLoad` (8,624) plus others
- `FixedAdmittance` captures switched shunts (discrete steps lost in MATPOWER conversion)

## Workarounds

- **What:** MATPOWER fallback path (`fnm_main_island.m`) used instead of PSS/E-derived
  intermediate CSV ingestion or direct PSS/E RAW parsing
- **Why:** PowerSystems.jl v4.6.2 has no parser for the evaluation's intermediate CSV
  format. Its PSS/E RAW parser also fails on v31 Case Identification header. The only
  viable ingestion path is MATPOWER `.m`.
- **Durability:** blocking -- there is no API-level workaround within PowerSystems.jl
  to parse PSS/E-derived intermediate CSVs. Fixing requires either (1) building a
  custom CSV-to-PowerSystems.jl converter, (2) upstream patch to the PTI parser's
  fixed-width tokenizer, or (3) external pre-conversion to MATPOWER format.
- **Grade impact:** G-FNM-1 fails. G-FNM-2 (field coverage) is blocked. G-FNM-3/4/5
  proceed via MATPOWER fallback path with reduced bus count (27,862 vs 30,307).

## Timing

- **Wall-clock:** 12.83s total (12.03s MATPOWER fallback load)
- **Timing source:** measured
- **Peak memory:** 847.2 MB (includes Julia runtime + MATPOWER load)
- **Solver iterations:** N/A
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/fnm_ingestion/test_g_fnm_1_fnm_ingestion_gate.jl`

Key findings:
```julia
# PowerSystems.jl supported formats (none match intermediate CSV)
# 1. MATPOWER .m: System("case.m") -- works
# 2. PSS/E .raw: System("file.raw") -- v31 header parse fails
# 3. Tabular CSV: own schema, not PSS/E-derived

# MATPOWER fallback succeeds
sys = PowerSystems.System("/workspace/data/fnm/reference/cleaned/fnm_main_island.m"; runchecks=false)
# => 27,862 buses, 5,741 generators, 32,606 branches
```
