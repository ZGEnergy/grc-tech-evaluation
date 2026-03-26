---
test_id: F-4
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: 32355ea8
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# F-4: Compiled Extension Audit

## Result: PASS

## Finding

MATPOWER 8.1 is 100% pure MATLAB/Octave code with zero compiled extensions (.mex, .so, .dll, .oct files) in the distribution. All source code is human-readable .m files. External solvers (IPOPT, GLPK) do contain compiled C/C++ components, but these are separate installations outside the MATPOWER distribution.

## Evidence

**Compiled file search:**
```bash
find /workspace/evaluations/matpower/matpower8.1/ -name '*.mex*' -o -name '*.so' -o -name '*.dll' -o -name '*.oct' | wc -l
# Result: 0
```

Zero compiled binary files found in the entire MATPOWER 8.1 distribution.

**Key execution path files (all .m text files):**

| File | Lines | Role |
|------|-------|------|
| `lib/rundcopf.m` | 75 | DC OPF entry point |
| `lib/opf.m` | 305 | OPF dispatcher |
| `lib/opf_setup.m` | 574 | Problem formulation |
| `lib/opf_execute.m` | 296 | Solve execution |
| `lib/dcopf_solver.m` | 154 | DC OPF solver interface |
| `lib/dcpf.m` | 46 | DC power flow core |
| `lib/makeBdc.m` | 86 | B-matrix construction |

**External solver compiled components (outside MATPOWER distribution):**

| Solver | Compiled? | Source Available? | Buildable? |
|--------|-----------|-------------------|------------|
| IPOPT | Yes (C++) | Yes (EPL-2.0, coin-or/Ipopt on GitHub) | Yes |
| GLPK | Yes (C) | Yes (GPL-3.0, gnu.org) | Yes |
| HiGHS | Yes (C++) | Yes (MIT, ERGO-Code/HiGHS on GitHub) | Yes |

All external solvers with compiled components have publicly available source code and are buildable from source.

## Implications

The core MATPOWER distribution achieves the highest possible inspectability score: every line of code in the execution path is readable .m source. No opaque binary blobs exist anywhere in the distribution. External solver binaries are the only compiled components in the full execution stack, and all have open-source code available for audit.
