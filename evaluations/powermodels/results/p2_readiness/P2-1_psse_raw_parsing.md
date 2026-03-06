---
test_id: P2-1
tool: powermodels
dimension: p2_readiness
status: qualified_pass
timestamp: 2026-03-05
---

# P2-1: PSS(R)E .raw File Parsing

## Finding

PowerModels.jl supports parsing PSS(R)E v33 .raw files with coverage of major network components. Version 34 is not supported (open issue #921). The parser handles buses, loads, generators, branches, two- and three-winding transformers (including magnetizing admittance), shunts, two-terminal DC lines, and VSC HVDC lines.

## Evidence

**Supported PSS/E version**: v33 (PTI format)

**Supported components** (from documentation at <https://lanl-ansi.github.io/PowerModels.jl/stable/parser>/):
- Buses
- Loads
- Fixed shunts and approximation of switched shunts
- Branches
- Two-winding transformers (including magnetizing admittance)
- Three-winding transformers (via synthetic star-bus decomposition)
- Generators
- Two-terminal DC lines
- Voltage source converter (VSC) HVDC lines

**Usage**:

```julia
data = PowerModels.parse_file("network.raw")
data = PowerModels.parse_file("network.raw"; import_all=true)  # import all PTI fields

```

**Known limitations**:
- Only PSS/E v33 supported; v34 requested in issue #921 (opened 2024-07-01, open)
- DC line export is incomplete (issue #754, marked "future work")
- Generation cost data cannot be exported (costs are not in .raw format; they come from MATPOWER .m files or separate sources)
- FACTS devices, GNE data, and Inter-Area Transfer data not exportable
- Switched shunt support is approximate
- PSS/E parser is noted to be slower than the alternative PowerFlowData.jl parser (~100x difference reported)
- Issue #932: "Incorrect behaviour for PSSE active generators at load buses" (open)
- Issue #918: "PSS/E parser support transformer angle offset of more than 60 degrees" (open)

**Alternative in Julia ecosystem**: PowerFlowData.jl is a dedicated PSS/E parser that is reportedly faster and may support additional versions.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/parser/,> GitHub issues #921, #918, #932, #893

## Implications

PSS/E v33 .raw parsing is functional and covers the major component types needed for power flow and OPF analysis. The v33 limitation means files from newer PSS/E versions (v34+) may not parse correctly. For Phase 2 use with real utility data, the PSS/E version compatibility should be verified against the target network model. The open parser issues (#932, #918) suggest edge cases in transformer and generator handling that could affect accuracy with production network models.
