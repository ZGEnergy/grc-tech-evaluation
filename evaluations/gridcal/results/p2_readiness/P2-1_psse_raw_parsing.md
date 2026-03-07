---
test_id: P2-1
tool: gridcal
dimension: p2_readiness
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# P2-1: PSS/E RAW Parsing

## Result: PASS

## Capability: Yes

GridCal has native PSS/E RAW and RAWX parsing built into the engine. No additional dependencies required.

## Supported Versions

RAW versions **29, 30, 32, 33, 34, 35** are explicitly supported. The parser source (`VeraGridEngine/IO/raw/raw_parser_writer.py`) contains a version list:

```python
versions = [35, 34, 33, 32, 30, 29]
```

If the RAW file's `REV` field is not in this list, the parser logs an error with:

```
The PSSe version is not compatible. Compatible versions are: 35, 34, 33, 32, 30, 29
```

## Implementation Details

- **Parser module:** `VeraGridEngine.IO.raw.raw_parser_writer` (read_raw function)
- **RAWX parser:** `VeraGridEngine.IO.raw.rawx_parser_writer` (parse_rawx function)
- **Converter:** `VeraGridEngine.IO.raw.raw_to_veragrid` (psse_to_veragrid function) converts `PsseCircuit` to `MultiCircuit`
- **File detection:** `vge.open_file()` auto-detects `.raw` and `.rawx` extensions
- **Export:** `write_raw()` can write RAW format (default v33)

## Usage

```python
import VeraGridEngine as vge
grid = vge.open_file("network.raw")  # auto-detects PSS/E RAW format
```

## Estimated Effort if Absent

N/A -- capability exists natively.

## Notes

- RAW v31 is notably absent from the supported version list. This may cause issues with some utility files.
- The parser handles impedance correction tables (v35+), multi-terminal DC, switched shunts, and other PSS/E-specific features via versioned parsing branches.
- Export to RAW format is also supported, enabling round-trip capability.
