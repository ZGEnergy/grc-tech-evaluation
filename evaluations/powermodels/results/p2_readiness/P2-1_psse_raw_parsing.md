---
test_id: P2-1
tool: powermodels
dimension: p2_readiness
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
---

# P2-1: PSS/E RAW Format Parsing Capability

## Result: INFORMATIONAL

## Finding

PowerModels.jl has **built-in PSS/E RAW v33 parsing**. The parser is fully integrated and functional via `parse_psse(path)` / `parse_pti(path)` / `parse_file(path)` (auto-detects `.raw` extension). PSS/E RAW **v34 and later are not supported** -- the parser is hardcoded for v33 and will emit a warning for earlier versions but has no handling for v34+ structural changes.

## Evidence

### Capability: YES

**Exported functions:**
- `parse_psse(filename::String; kwargs...)` -- parses PSS/E `.raw` files (defined in `src/io/psse.jl`, 933 lines)
- `parse_pti(filename::String; kwargs...)` -- lower-level PTI format parser (defined in `src/io/pti.jl`, 1756 lines)
- `export_pti(data, filename)` -- exports PowerModels data back to PSS/E format
- `parse_file(path)` -- auto-detects `.m` (MATPOWER) or `.raw` (PSS/E) by extension

**Supported RAW version: v33 only.**

The PTI parser explicitly targets v33:
- Line 9 of `pti.jl`: "A list of data file sections in the order that they appear in a PTI v33 file"
- Line 231: Default `REV` value is 33
- Line 694: Warning for versions below 33: `"Version $(section_data["REV"]) of PTI format is unsupported, parser may not function correctly."`
- Lines 962, 1014, 1040, 1288, 1532: Multiple references to "PSSE 33" / "RAW V33" / "POM 5-20"

**No v34 support.** The parser does not warn or error on v34+ files; it silently attempts to parse them with v33 field definitions. GitHub issue #921 tracks v34 support as a feature request (unresolved).

### Parsed PSS/E elements:
The `_pti_to_powermodels!` function (line 851 of `psse.jl`) converts the following record types:
- CASE IDENTIFICATION (header)
- BUS DATA
- LOAD DATA
- FIXED SHUNT DATA
- GENERATOR DATA
- BRANCH DATA
- TRANSFORMER DATA (2- and 3-winding)
- AREA INTERCHANGE DATA
- TWO-TERMINAL DC LINE DATA
- SWITCHED SHUNT DATA

### `import_all` flag:
Setting `import_all=true` preserves all raw PTI fields that PowerModels does not natively use, stored in the data dict for downstream access.

## Implications

- **Phase 2 readiness: HIGH for v33 networks.** If ZGE's PSS/E models are v33, PowerModels can parse them directly with no additional effort.
- **Phase 2 risk: MODERATE for v34+ networks.** PSS/E v34 introduced structural changes (e.g., new record types, modified field definitions). Parsing v34 files with the v33 parser may silently produce incorrect data. Estimated effort to add v34 support: **significant**(requires modifying `_pti_dtypes`, adding new record type handlers, and updating field default values in ~1000+ lines of parser code). This would likely require a contribution to upstream PowerModels.jl or a fork.
- The bidirectional capability (`export_pti`) is a positive signal for round-trip workflows.
