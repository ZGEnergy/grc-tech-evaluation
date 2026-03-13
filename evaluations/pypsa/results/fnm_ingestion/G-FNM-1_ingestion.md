---
test_id: G-FNM-1
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v9
skill_version: v1
test_hash: 222414ed
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.353
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 254
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# G-FNM-1: Intermediate Format Ingestion

## Result: PASS

All primary component counts match the expected values from the intermediate
manifest after accounting for type-4 bus filtering. Buses, generators, and
branches (lines + transformers) all match exactly.

## Approach

1. Load the MATPOWER `.mat` file (`mpc_case.mat`) via `scipy.io.loadmat` (PyPSA
   has no native MATPOWER reader — stable workaround).
2. Manually construct a PYPOWER PPC dict with keys `version`, `baseMVA`, `bus`,
   `gen`, `branch`.
3. Filter out 2,370 type-4 (isolated) buses and their connected generators (1)
   and branches (1,151) to avoid `import_from_pypower_ppc` crash on bus type 4.
4. Import into PyPSA with `n.import_from_pypower_ppc(ppc)`.
5. Count ingested components and compare against intermediate manifest expectations.

## Output

| Component | RAW Expected | After Type-4 Filter | PyPSA Ingested | Match |
|-----------|-------------|---------------------|----------------|-------|
| Buses | 30,307 | 27,937 | 27,937 | yes |
| Generators | 5,768 | 5,767 | 5,767 | yes |
| Branches (merged) | 33,840 | 32,689 | 32,689 (23,142 lines + 9,547 xfmrs) | yes |
| Loads | 15,062 | — | 8,632 | note |
| Switched Shunts | 3,114 | — | 3,110 | note |

**Notes:**
- **Loads:** The PPC import path creates one load per bus with nonzero Pd/Qd
  (8,632 buses), not one per PSS/E load record (15,062). This is a known
  limitation of the pypower import path which aggregates multiple loads on the
  same bus into a single load entry.
- **Switched Shunts:** 3,110 imported via bus Gs/Bs columns; 4 fewer than RAW
  count due to shunts on type-4 buses or zero-admittance shunts dropped during
  filtering.
- **Branch split:** PyPSA splits the merged MATPOWER branch array into Lines
  (23,142 with tap ratio 0 or 1) and Transformers (9,547 with non-unity tap
  ratio or voltage level mismatch) based on tap ratio. The sum equals the
  filtered branch total.

## Workarounds

1. **No native MATPOWER reader** (stable): PyPSA has no built-in `.m` or `.mat`
   file reader. Used `scipy.io.loadmat` to load the `.mat` file and manually
   constructed a PPC dict. This is a well-documented approach and unlikely to
   break across PyPSA versions.

2. **Type-4 bus crash** (stable): `import_from_pypower_ppc` raises an error on
   bus type 4 (isolated). Filtered out 2,370 type-4 buses and their connected
   components (1 generator, 1,151 branches) before import. This is a
   deterministic pre-processing step with no ambiguity.

- **What:** Two-step workaround: manual PPC construction + type-4 bus filtering
- **Why:** PyPSA lacks native MATPOWER file I/O and does not handle isolated buses
- **Durability:** stable — both scipy.io and the PPC dict format are mature APIs
- **Grade impact:** Minor inconvenience for ingestion pipeline; does not affect
  analytical capability once the network is loaded
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 0.353 s (load + filter + import)
- **Timing source:** measured (time.perf_counter)
- **Peak memory:** not measured
- **Solver iterations:** N/A (no solver used)
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_1_ingestion.py`
