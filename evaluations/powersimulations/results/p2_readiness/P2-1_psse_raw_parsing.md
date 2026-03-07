---
test_id: P2-1
tool: powersimulations
dimension: p2_readiness
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:30:00Z"
---

# P2-1: PSS/E RAW Format Parsing

## Result: INFORMATIONAL

## Finding

PowerSystems.jl **natively supports PSS/E RAW format** parsing via its data ingestion layer.
The `System()` constructor accepts `.raw` files directly:

```julia
sys = System("network.raw")
```

### Supported Versions

PowerSystems.jl supports PSS/E RAW versions 30, 32, and 33 through its parser. The parser
handles bus, load, generator, branch, transformer, and area interchange records. Dynamic
data (`.dyr` files) is also supported for transient stability studies.

### Capabilities

| Feature | Supported |
|---------|-----------|
| Static network data (.raw) | Yes |
| Dynamic data (.dyr) | Yes |
| RAW v30 | Yes |
| RAW v32 | Yes |
| RAW v33 | Yes |
| CIM format | No |
| CGMES format | No |

### Effort to Add (if absent)

Not applicable — capability exists natively. No additional development effort required
for Phase 2 PSS/E data ingestion.

### Limitations

- RAW v35+ (newer PSS/E versions) may not be fully supported
- Some vendor-specific extensions to the RAW format may not parse correctly
- Validation of parsed data against PSS/E reference solutions has not been performed
  in this evaluation
