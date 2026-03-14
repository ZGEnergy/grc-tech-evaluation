---
test_id: P2-1
tool: powersimulations
dimension: p2_readiness
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "9f8ed88f"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# P2-1: PSS/E RAW Format Parsing

## Result: INFORMATIONAL

## Capability Assessment

| Question | Answer |
|----------|--------|
| Can PowerSystems.jl parse PSS/E RAW files? | Yes, via built-in PTI parser |
| Supported RAW versions | v33, v35 (comma-delimited) |
| RAW v31 support | No -- parser fails on CASE IDENTIFICATION header |
| RAW v30 support | No -- same issue (pre-v33 uses fixed-width format) |
| Estimated effort to add v31 | Medium (weeks, not days) |

## Parser Architecture

PowerSystems.jl includes a PSS/E RAW parser derived from PowerModels.jl, located in
`src/parsers/pm_io/pti.jl`. The parser handles the PTI (Power Technologies International)
raw data format.

### Tokenization Strategy

The parser uses **comma-delimited splitting** exclusively:
```julia
const _split_string = r",(?=(?:[^']*'[^']*')*[^']*$)"
```

This regex splits on commas while preserving quoted strings. The `_parse_line_element!()`
function then parses each comma-separated token according to declared field types.

**No fixed-width parsing logic exists in the codebase.**

### Version Detection and Handling

- **v35 files:** Identified by `@!` comment markers; header starts at line 2
- **v33 files:** Header starts at line 1; six comma-separated fields expected
- **v30-v32 files:** Trigger a warning (`"Version X of PTI format is unsupported"`) but
  the parser continues -- and then fails on the first line because pre-v33 RAW files use
  **fixed-width column format** rather than comma-delimited format

### CASE IDENTIFICATION Field Layout

The parser expects six comma-delimited fields on the header line:
```
IC, SBASE, REV, XFRRAT, NXFRAT, BASFRQ
```
Declared types: `(Int64, Float64, Int64, Float64, Float64, Float64)`

### v31 RAW Header (Fixed-Width)

The reference ISO FNM v31 file's first line:
```
 0    100.00 31  0  0    0.0
```

This is a **fixed-width format** where fields are separated by whitespace, not commas.
The parser attempts to parse the entire string `'0    100.00 31  0  0    0.0'` as a
single `Int64` for the `IC` field, which fails.

## Failure Evidence (from G-FNM-1)

```
Parsing failed at line 1: value '0    100.00 31  0  0    0.0' for IC
in section CASE IDENTIFICATION is not of type Int64.
```

This error occurs in `_parse_line_element!()` when `parse(Int64, "0    100.00 31  0  0    0.0")`
is called on the unsplit line.

## Effort Estimate to Fix v31 Support

### What Would Be Required

1. **Fixed-width tokenizer for CASE IDENTIFICATION (small):** Add a fallback that
   detects the absence of commas and splits on whitespace columns per the PSS/E v31
   specification. The CASE IDENTIFICATION section is only 3 lines and has a well-defined
   column layout.

2. **Fixed-width tokenizer for all data sections (medium-large):** PSS/E v30-v32 use
   fixed-width format for **all** data sections (BUS, LOAD, GENERATOR, BRANCH, etc.),
   not just the header. Each section has a different column layout defined in the PSS/E
   Program Operation Manual. Adding full v31 support requires:
   - Column-width definitions for every data section in v31
   - A parallel parsing path that uses column slicing instead of comma splitting
   - Handling of blank fields (common in fixed-width format)
   - Testing against real v31 files from multiple ISOs

3. **Version-specific field differences (small-medium):** v31 has fewer fields per
   section than v33/v35. Some sections added in v33 (e.g., FACTS DEVICE CONTROL MODE
   DATA) do not exist in v31.

### Effort Classification

| Component | Effort | Risk |
|-----------|--------|------|
| Header-only fix (parse first 3 lines) | 1-2 days | Low |
| Full v31 data section parsing | 2-4 weeks | Medium |
| Testing with real ISO RAW files | 1 week | Medium |
| Upstream PR acceptance | Uncertain | High |

**Overall: Medium effort (3-6 weeks including testing and review)**

The header-only fix would allow version detection but not actual data loading. Full v31
support requires a parallel fixed-width parsing path for all ~15 data sections.

### Alternative Approaches

1. **External conversion (RAW to MATPOWER):** Use MATPOWER's `loadcase()` in Octave or
   PSS/E's own export to convert v31 RAW files to MATPOWER `.m` format before loading
   into PowerSystems.jl. This is the approach used in the evaluation (G-FNM-1).

2. **Request v33+ RAW files:** Ask the data provider (the ISO) for comma-delimited
   RAW exports. Many ISOs now provide v33 or v35 format files.

3. **Use a Python bridge:** `grg-psse` or `andes` Python packages can parse v31 RAW
   files. The parsed data could be converted to PowerSystems.jl's tabular CSV format.

## Implications for Phase 2

PSS/E RAW v31 parsing is **not available** in the current Sienna stack. For a production
workflow that ingests ISO FNM RAW files, one of the alternative approaches (external
conversion or upstream fix) would be required. The MATPOWER fallback path works but loses
some PSS/E-specific data (switched shunt steps, owner/zone assignments, multi-section
line groupings).
