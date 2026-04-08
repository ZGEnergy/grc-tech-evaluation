---
test_id: P2-1
tool: gridcal
dimension: p2_readiness
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "11e6e5b8"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# P2-1: PSS/E RAW parsing capability

## Finding

GridCal/VeraGrid has a built-in PSS/E RAW parser that declares support for versions 29, 30, 32, 33, 34, and 35, but field-count expectations are hardcoded to v35 layout, causing parse failures on older versions such as v31 (as demonstrated in G-FNM-1).

## Evidence

**Declared version support.** The `read_raw()` function in `VeraGridEngine/IO/raw/raw_parser_writer.py` defines a supported versions list:

```python
versions = [35, 34, 33, 32, 30, 29]
```

If the file's `REV` field is not in this list, the parser logs an error and returns an empty `PsseCircuit`. Version 31 is notably absent from the list.

**Actual v31 failure (G-FNM-1).** When the FNM RAW file (`<FNM_SOURCE>.RAW`, PSS/e v31) was parsed, the parser failed with:

```
Exception: PSSe 35 load data came with 1 elements and 18 or 17 were expected :/
```

This error reveals that even for nominally "supported" versions, the per-record parsers (`RawLoad`, `RawBranch`, etc.) use field-count expectations keyed to v35 layout. The `version` parameter is passed to individual device parsers, but the v31 record format has fewer fields per record than v35, and the parser does not degrade gracefully.

**Version-aware parsing is partial.** The `version` integer is threaded through to device-level `parse()` methods (e.g., `obj.parse(data2, version, logger)`), and some version-conditional logic exists (e.g., `if version >= 35` for impedance correction tables). However, field-count validation within device parsers appears to assume v35 field counts as the baseline, causing failures when older formats have fewer columns.

**Export.** RAW export (`write_raw()`) supports v33 and v35 output. GitHub Issue #414 reports PSS/E exporting is broken.

## Implications

- **Phase 2 FNM ingestion** requires PSS/e v31 parsing. GridCal cannot parse v31 RAW files without parser modifications to handle the shorter record formats.
- **Estimated effort to fix:** Medium. The parser architecture already threads a `version` parameter to device-level parsers. The fix requires auditing each device parser (bus, load, branch, generator, transformer, etc.) to accept the correct field counts for v29-v34 formats. The PSS/e RAW specification defines field layouts per version, so this is mechanical but tedious work across ~15 device types.
- **Alternative path:** The MATPOWER `.m` fallback (demonstrated in G-FNM-1) successfully loads the FNM main island with ~28,000 of ~30,000 buses. This loses area/zone metadata but provides a workable network for power flow and OPF studies.
- **v35 files parse correctly.** Standard test cases distributed in v35 format (the current PSS/e version) should work without issues.
