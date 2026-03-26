---
test_id: D-5
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "e3ef643e"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-5: Code Volume

## Result: INFORMATIONAL

## Finding

MATPOWER Suite A test scripts range from 125 to 479 lines, with a median of 265 lines. Code volume is higher than typical Python tools due to Octave's lack of DataFrame abstractions, verbose CSV parsing, and the need for manual boilerplate (path setup, define_constants, memory measurement).

## Evidence

### LOC per Suite A Test

| Test | Description | LOC | Notes |
|------|-------------|-----|-------|
| A-1 | DCPF | 125 | Minimal -- core solve is 3 lines |
| A-2 | ACPF | 170 | Includes flat-start and DC warm-start fallback |
| A-3 | DCOPF | 221 | CSV parsing for gen costs adds ~30 lines |
| A-4 | AC Feasibility | 242 | DC OPF + AC PF pipeline, violation detection |
| A-5 | SCUC | 283 | MOST setup with xgd_table, load profiles, 2-part test |
| A-6 | SCED | 307 | Per-period dispatch loop, ramp verification |
| A-9 | SCOPF | 288 | LODF computation, constraint injection, fallback logic |
| A-10 | Lossy DCOPF + LMP | 350 | Iterative loss injection, manual PTDF decomposition |
| A-11 | Distributed Slack | 287 | PTDF-based LMP recomputation, 3 weight schemes |
| A-12 | Multi-period + Storage | 479 | Full MOST setup with storage, renewables, profiles |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total LOC (all 10 tests) | 2,752 |
| Mean LOC | 275.2 |
| Median LOC | 265 |
| Min LOC | 125 (A-1) |
| Max LOC | 479 (A-12) |

### LOC Breakdown by Category

Each test script contains:
- **Path setup boilerplate:** 6 lines (identical across all tests -- `addpath` calls)
- **Define constants:** 1-8 lines (range from `define_constants;` to full `idx_ct` load for MOST)
- **CSV parsing:** 10-20 lines per CSV file (Octave has no `csvread` with headers, requires `fopen`/`fgetl`/`strsplit` loop)
- **Core solve:** 1-5 lines (the actual MATPOWER function call)
- **Result extraction:** 5-20 lines (indexed column access via named constants)
- **Output formatting:** 15-40 lines (fprintf loops for tables)
- **Memory measurement:** 5 lines (reading `/proc/self/status`)

### Code Volume Drivers

1. **No DataFrame abstraction.** Octave/MATPOWER uses positional numeric matrices. Result extraction requires knowing column indices (e.g., `results.bus(:, LAM_P)`) and manual formatting. Python tools can do `results.buses_t.p.to_csv()` in one line.

2. **Manual CSV parsing.** Octave's `csvread` cannot handle headers or mixed types. Reading the `gen_temporal_params.csv` file requires a 12-line `fopen/fgetl/strsplit` loop that would be `pd.read_csv()` in Python.

3. **Path setup overhead.** Every test file starts with 6 identical `addpath` lines. Python tools use virtual environments; Julia tools use `Project.toml`. MATPOWER has no equivalent mechanism.

4. **MOST boilerplate.** Tests A-5, A-6, and A-12 require extensive MOST data structure setup (`xgd_table`, `sd_table`, `profiles`). The MOST API requires building specific struct formats with column name strings that must match exactly. This adds 30-60 lines per test.

5. **Verbose error handling.** Octave's `try/catch` blocks with error collection add ~10 lines per test. MATPOWER does not throw exceptions for some failure modes (e.g., `results.success == 0`), requiring explicit checking.

### Core Solve LOC (Excluding Boilerplate)

Stripping path setup, output formatting, error handling, and memory measurement:

| Test | Core LOC | Notes |
|------|----------|-------|
| A-1 | ~5 | `loadcase` + `rundcpf` + result access |
| A-2 | ~10 | `loadcase` + flat start + `runpf` + convergence check |
| A-3 | ~15 | Cost setup + derating + `rundcopf` + LMP access |
| A-4 | ~20 | DC OPF + AC PF pipeline + violation detection |
| A-5 | ~80 | MOST data structure assembly is the dominant cost |
| A-6 | ~60 | Per-period dispatch loop with ramp constraints |
| A-9 | ~80 | LODF + constraint matrix assembly |
| A-10 | ~100 | Iterative loss injection + PTDF decomposition |
| A-11 | ~50 | PTDF computation + LMP recomputation |
| A-12 | ~150 | Full MOST setup with storage + renewables |

## Implications

MATPOWER's code volume is driven by the Octave platform (no DataFrames, verbose CSV I/O) and the MOST API's data structure requirements. Core power flow and OPF operations (A-1 through A-4) are concise -- the `runpf`/`rundcopf` API is among the most compact in the evaluation. Advanced multi-period operations (A-5, A-6, A-12) require significantly more code due to MOST's structured input format. Operations requiring custom formulations (A-9 SCOPF, A-10 lossy OPF) add substantial code because MATPOWER lacks native support, requiring manual matrix construction.
