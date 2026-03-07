---
test_id: P2-1
tool: matpower
dimension: p2_readiness
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 0
solver: null
timestamp: "2026-03-06T00:00:00Z"
---

# P2-1: PSS/E RAW Parsing Capability

## Result: INFORMATIONAL -- Capability Present

## Capability: YES (Native, Built-in)

MATPOWER 8.1 includes built-in PSS/E RAW file import and export functions.
No external dependencies or plugins required.

## Functions

| Function | Purpose | Notes |
|----------|---------|-------|
| `psse2mpc(rawfile)` | Import PSS/E RAW -> MATPOWER case struct | Primary import function |
| `save2psse(fname, mpc)` | Export MATPOWER case -> PSS/E RAW | Exports as Rev 33 |
| `save2psse_rop(fname, mpc)` | Export to PSS/E ROP format | Generator dispatch + cost tables |
| `psse_read(rawfile)` | Low-level RAW file reader | Returns raw records + section indices |
| `psse_parse(records, sections)` | Parse raw records into structured data | Version-aware parsing |
| `psse_convert(data)` | Convert parsed PSS/E data to MATPOWER | Handles version differences |
| `psse_convert_xfmr(data)` | Transformer-specific conversion | Multi-winding support |
| `psse_convert_hvdc(data)` | HVDC line conversion | Two-terminal DC lines |

## Supported PSS/E RAW Versions

### Import (psse2mpc)
- **Auto-detection:** Attempts to detect PSS/E revision from file header (regex: `PSS/E-<rev>`)
- **Default:** Falls back to Rev 23 if version cannot be detected
- **Override:** Optional `REV` parameter to force a specific revision
- **Version-specific parsing:** Code branches for revisions <24, 24-27, 28-29, 30, 31, 32, >32
- **Effective range:** Rev 23 through Rev 33+ (based on code branch analysis)

### Export (save2psse)
- **Output format:** Rev 33 (fixed, no version selection currently)
- **Planned:** Version parameter exists in signature but is noted as "not yet implemented"

### Data Sections Parsed (Import)
- Identification data (case name, SBASE, revision)
- Bus data (with version-dependent load/shunt handling)
- Load data (separate section for Rev >= 24)
- Fixed shunt data (separate section for Rev > 30)
- Generator data
- Branch data
- Transformer data (version-dependent ratio/angle handling)
- Switched shunt data
- Area data
- HVDC line data (two-terminal)
- **Ignored:** Other sections (e.g., facts, multi-section lines, impedance corrections)

## Round-Trip Verification

Tested on case9 (9-bus system):

```
mpc = loadcase('case9');
fname = save2psse('/tmp/test_case9', mpc);    % Export to RAW
mpc2 = psse2mpc(fname, '', 0);                % Re-import
% Result: 9 buses, 3 gens, 9 branches -- matches original
```

Round-trip preserves bus, generator, and branch counts. Numerical fidelity
depends on the precision of the RAW text format.

## Effort Assessment

| Task | Effort | Notes |
|------|--------|-------|
| Import existing RAW file | **Trivial** | Single function call `psse2mpc(file)` |
| Export to RAW format | **Trivial** | Single function call `save2psse(file, mpc)` |
| Handle specific RAW version | **Low** | Pass `REV` parameter to override auto-detect |
| Parse unsupported sections | **Medium** | Would require extending `psse_parse` |
| Support newer RAW versions (>33) | **Medium** | Code is version-branched; adding new version requires new branches |

## Limitations

1. **Export fixed at Rev 33:** Cannot currently export to older RAW versions
2. **Section coverage:** Several PSS/E data sections are ignored (FACTS, multi-section lines, impedance correction tables, multi-terminal DC, etc.)
3. **No EPC format:** Only RAW format supported, not the newer EPC (Siemens PTI Engineering data) format
4. **No incremental/change file support:** Only full RAW files
5. **Gencost not preserved:** PSS/E RAW doesn't carry cost data; `save2psse_rop` handles cost export separately

## Test Coverage

MATPOWER includes 143 unit tests for PSS/E parsing in `matpower8.1/lib/t/t_psse.m`, with test RAW files:
- `t_psse_case.raw` -- general parsing test
- `t_psse_case2.raw` -- additional format variant
- `t_case9_save2psse.raw` -- round-trip export test

## Assessment for P2 Readiness

PSS/E RAW parsing is a mature, built-in capability in MATPOWER. The import function
has been maintained since MATPOWER 5.x (2014) with continuous fixes through 8.1. For
standard power flow cases with buses, generators, branches, and transformers, the
import/export works reliably. The main gaps are in advanced PSS/E features (FACTS,
multi-terminal DC, newer section types) which would require custom extensions.
