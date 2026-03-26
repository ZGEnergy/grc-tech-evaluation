---
test_id: P2-1
tool: matpower
dimension: p2_readiness
network: N/A
protocol_version: v11
skill_version: v2
test_hash: "e1aebe67"
status: informational
workaround_class: null
timestamp: 2026-03-24T12:00:00Z
---

# P2-1: PSS/E RAW Parsing Capability

## Capability: YES -- native support via `psse2mpc()`

## Supported RAW Versions

MATPOWER 8.1 ships `psse2mpc()` which converts PSS/E RAW data files to MATPOWER `mpc` case
structs. The underlying parser (`psse_parse.m`) contains explicit revision-dependent branching
for PSS/E RAW revisions 24 through 33+, with a default fallback to revision 23 when the
revision cannot be auto-detected from the file header.

Revision-specific code paths handle structural differences across versions:

| RAW Revision Range | Key Structural Difference Handled |
|--------------------|-----------------------------------|
| rev <= 23 | Load data embedded in bus records |
| rev 24-30 | Load data separate; fixed shunt data in bus records |
| rev >= 31 | Fixed shunt data in separate section |
| rev <= 27 | Transformer ratio/angle in branch records |
| rev 28-30 | Expanded transformer data format |
| rev >= 31 | Further transformer data expansion |
| rev >= 32 | Additional data sections |
| rev >= 33 | Latest supported format extensions |

The parser auto-detects the revision from the file's identification record (looking for
`PSS/E-XX` or `PSS(tm)E-XX` patterns in the header comment). Users can also force a
specific revision via the `REV` argument: `psse2mpc(rawfile, verbose, rev)`.

**Data sections parsed:** identification, bus, load, branch, fixed shunt, generator,
transformer, switched shunt, area, and HVDC line data. Other PSS/E data sections (e.g.,
multi-terminal DC, impedance correction, multi-section line, zone, interarea transfer,
owner, FACTS) are present in the file but currently ignored by the parser.

**Export:** `save2psse(file, mpc)` exports to PSS/E RAW Rev 33 format. MATPOWER 8.1 also
added `save2psse_rop()` for PSS/E ROP (remedial action plan) file export.

## Effort to Add if Absent

Not applicable -- capability is native.

## Sources

- `/workspace/evaluations/matpower/matpower8.1/lib/psse2mpc.m` -- entry point
- `/workspace/evaluations/matpower/matpower8.1/lib/psse_parse.m` -- revision-dependent parser (lines 156-450 contain rev-specific branching)
- `/workspace/evaluations/matpower/matpower8.1/lib/psse_convert.m` -- conversion from parsed data to mpc struct
- `/workspace/evaluations/matpower/matpower8.1/lib/save2psse.m` -- export to RAW Rev 33
