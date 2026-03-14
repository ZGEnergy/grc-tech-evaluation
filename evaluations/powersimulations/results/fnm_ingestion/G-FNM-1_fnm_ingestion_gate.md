---
test_id: G-FNM-1
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
status: fail
workaround_class: blocking
blocked_by: null
timestamp: "2026-03-14T13:15:56Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "7827a912"
wall_clock_seconds: 18.23
timing_source: measured
peak_memory_mb: 838.3
convergence_residual: null
convergence_iterations: null
loc: 147
solver: null
input_path: matpower
---

# G-FNM-1: Intermediate format ingestion — two-check gate

## Result: FAIL

## Approach

G-FNM-1 is a two-check gate test:

**(a) PSS/E RAW compatibility:** Attempted to load the FNM Annual S01 RAW file
(`AUC_AN_2026_2026_S01_ON_NETWORK_MODEL.RAW`, 17.8 MB, PSS/E v31 format) directly
via `PowerSystems.System(raw_file; runchecks=false)`. PowerSystems.jl v4.6.2 includes
a built-in PSS/E RAW parser (via the PowerModels-derived `pti.jl` parser).

**(b) Record count fidelity:** Not evaluated because sub-check (a) failed.

After PSS/E failure, loaded the pre-cleaned MATPOWER fallback
(`fnm_main_island.m`, 27,862-bus main island) to verify the MATPOWER ingestion path
works for downstream G-FNM-3/4/5 tests.

## Output

### Sub-check (a): PSS/E RAW parsing — FAIL

The parser failed at line 1 of the RAW file with:

```
Parsing failed at line 1: value '0    100.00 31  0  0    0.0' for IC in section
CASE IDENTIFICATION is not of type Int64.
```

The RAW file's first line is a fixed-width record:
```
 0    100.00 31  0  0    0.0
```

The PowerSystems.jl PSS/E parser (inherited from PowerModels.jl) attempts to parse
the `IC` field as `Int64` from the entire whitespace-separated token but fails because
it cannot correctly tokenize the fixed-width v31 CASE IDENTIFICATION header. The parser
expects a strict column-delimited format that this RAW file does not match.

**Root cause:** The PSS/E parser in PowerSystems.jl v4.6.2 has incomplete support for
PSS/E RAW v31 format fixed-width field layouts in the CASE IDENTIFICATION section.

### Sub-check (b): Record count fidelity — SKIPPED

Not evaluated because PSS/E parsing did not succeed.

### MATPOWER fallback — verified

The MATPOWER fallback file loaded successfully in 9.3 seconds. Note: this is the
pre-cleaned main island (27,862 buses), not the full 30,307-bus FNM, so direct
comparison against the intermediate manifest is not applicable.

| Component Type | MATPOWER Fallback Count | Manifest (full FNM) | Notes |
|---|---|---|---|
| ACBus | 27,862 | 30,307 | Main island only (2,445 isolated buses removed) |
| Generator (all) | 5,741 | 5,768 | 27 generators on removed islands |
| Line | 23,058 | 24,117 | Lines on removed islands excluded |
| Transformer2W | 7,190 | — | MATPOWER merges branch types |
| TapTransformer | 2,358 | — | MATPOWER merges branch types |
| PhaseShiftingTransformer | 0 | — | None in this network |
| Line + all transformers | 32,606 | 33,840 (merged) | Consistent with island removal |
| ElectricLoad | 11,734 | 15,062 | Loads mapped to PowerLoad + StandardLoad |
| PowerLoad | 8,624 | — | Subset of ElectricLoad |
| FixedAdmittance | 3,110 | 3,114 | Switched shunts mapped to fixed admittance |
| Area | 44 | 49 | 5 areas only on removed islands |
| LoadZone | 74 | 90 | Zones on removed islands excluded |

**Component type mapping notes:**
- PowerSystems.jl splits MATPOWER `branch` rows into `Line`, `Transformer2W`, and
  `TapTransformer` based on tap ratio and transformer flags
- All generators are imported as `ThermalStandard` (no fuel-type differentiation from MATPOWER)
- `ElectricLoad` is the abstract supertype; concrete types are `PowerLoad` (8,624) plus others
- `FixedAdmittance` captures switched shunts (discrete steps lost in MATPOWER conversion)

## Workarounds

- **What:** MATPOWER fallback path (`fnm_main_island.m`) used instead of direct PSS/E RAW ingestion
- **Why:** PowerSystems.jl v4.6.2's PSS/E parser cannot parse the v31 RAW CASE IDENTIFICATION header
- **Durability:** blocking — the PSS/E parser bug is in the upstream PowerModels.jl-derived code within PowerSystems.jl. Fixing requires either (1) upstream patch to the PTI parser's fixed-width tokenizer, or (2) pre-converting RAW to MATPOWER format externally
- **Grade impact:** G-FNM-1 fails. G-FNM-2 (field coverage) is blocked. G-FNM-3/4/5 proceed via MATPOWER fallback path with reduced bus count (27,862 vs 30,307)

## Timing

- **Wall-clock:** 18.23s total (7.86s PSS/E attempt + 9.3s MATPOWER fallback load)
- **Timing source:** measured
- **Peak memory:** 838.3 MB (includes Julia runtime + MATPOWER load)
- **Solver iterations:** N/A
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Observations

### `api-friction` — PSS/E RAW v31 parsing failure (blocking)

PowerSystems.jl v4.6.2 cannot parse PSS/E RAW v31 files from the reference ISO FNM. The
parser fails at the very first line (CASE IDENTIFICATION section). This is a blocking
limitation for any workflow that requires direct PSS/E RAW ingestion without
pre-conversion to MATPOWER format.

Severity: **blocking** — there is no API-level workaround within PowerSystems.jl.
The only path is external format conversion (RAW to MATPOWER `.m`).

### `fnm-data-model` — MATPOWER fallback component mapping

When loading via MATPOWER format, PowerSystems.jl provides reasonable component
type differentiation (Line vs Transformer2W vs TapTransformer) from the merged
MATPOWER branch table. However, all generators become `ThermalStandard` and
switched shunts become `FixedAdmittance` (losing discrete step information).

## Test Script

**Path:** `evaluations/powersimulations/tests/fnm_ingestion/test_g_fnm_1_fnm_ingestion_gate.jl`

Key API calls:
```julia
# PSS/E attempt (fails)
sys = PowerSystems.System("/path/to/file.RAW"; runchecks=false)

# MATPOWER fallback (succeeds)
sys = PowerSystems.System("/path/to/file.m"; runchecks=false)

# Component counting
collect(PowerSystems.get_components(PowerSystems.ACBus, sys))
collect(PowerSystems.get_components(PowerSystems.Generator, sys))  # all subtypes
```
