---
test_id: P2-1
tool: pandapower
dimension: p2_readiness
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# P2-1: PSS/E RAW format parsing capability

## Result: INFORMATIONAL

## Finding

pandapower does NOT support PSS/E RAW format import or export. No parser, converter, or bridge for any RAW version (v26, v29, v30, v33, v35) exists in the codebase.

## Evidence

### Supported Import Formats

pandapower's `converter` subpackage provides converters for:

| Format | Module | Direction |
|--------|--------|-----------|
| MATPOWER (.m, .mat) | `converter.matpower` | Import + Export |
| PYPOWER (ppc dict) | `converter.pypower` | Import + Export |
| CIM/CGMES (XML) | `converter.cim` | Import |
| PowerFactory (DGS) | `converter.powerfactory` | Import |
| UCTE-DEF | `converter.ucte` | Import |
| JAO | `converter.jao` | Import |

### Search for PSS/E References

A search of the pandapower v3.4.0 codebase (361 `.py` files, ~89K LOC) for keywords `psse`, `pss/e`, `raw`, `rawd`, `PTI` found no relevant matches. There is no import function, no parser, and no documentation referencing PSS/E RAW format support.

### Effort Estimate to Add PSS/E RAW Support

| Aspect | Assessment |
|--------|------------|
| Parser complexity | High -- RAW format has 20+ record types with version-specific fields |
| Data model gap | Medium -- pandapower's element types cover most PSS/E concepts but some (switched shunts, multi-terminal DC, facts) have partial or no equivalents |
| Existing alternatives | [andes](https://docs.andes.app/) and [GridCal](https://gridcal.org/) have PSS/E parsers; code could be referenced |
| Estimated effort | 3-6 person-weeks for v30/v33 support with basic element coverage |
| Community interest | Multiple GitHub issues requesting PSS/E support; no implementation to date |

### Alternative Paths

1. **MATPOWER bridge:** Convert RAW to MATPOWER format using an external tool (e.g., MATPOWER's `psse2mpc` in MATLAB/Octave), then import via `from_mpc()`.
2. **CIM bridge:** If the source system can export CIM/CGMES, pandapower can import directly.
3. **External parser:** Use a Python PSS/E parser (e.g., `grg-psse` or GridCal's parser) to extract data, then construct a pandapower network programmatically.

## Implications

The absence of PSS/E RAW support is a significant gap for P2 readiness, as many North American utilities and ISOs use PSS/E as their primary planning tool. Network models are commonly distributed in RAW format. An integration pipeline would require either adding a native parser or maintaining an external conversion step.
