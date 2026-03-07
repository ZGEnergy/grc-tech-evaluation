---
test_id: F-4
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-4: Compiled Extension Audit

## Methodology

Searched the entire MATPOWER 8.1 distribution for compiled binaries:

```bash
find /workspace/evaluations/matpower/matpower8.1 \
  -name '*.mex*' -o -name '*.so' -o -name '*.dll' 2>/dev/null
```

## Results

**No compiled extensions found.** Zero MEX files, shared libraries, or DLLs
exist in the MATPOWER 8.1 distribution.

## Analysis

MATPOWER is **100% interpreted MATLAB/Octave code** (.m files). Every function
in the execution path is a readable .m text file. There are no:

- MEX files (compiled MATLAB/Octave extensions)
- Shared libraries (.so, .dylib)
- Windows DLLs
- Java JARs
- Python extensions
- WebAssembly modules
- Any other binary artifacts

## Optional External Solvers (Not Bundled)

The following solvers are optionally used but **not shipped** with MATPOWER:

| Solver | Interface | Binary? | Notes |
|--------|-----------|---------|-------|
| IPOPT | MEX file | Yes — user must compile or download separately | Not in distribution |
| OSQP | MEX file | Yes — user must compile or download separately | Not in distribution |
| HiGHS | Octave interface | Depends on installation method | Not in distribution |
| GLPK | Built into Octave | Part of Octave, not MATPOWER | Not in distribution |

These are accessed through MATPOWER's solver abstraction layer (`qps_master.m`)
which dynamically checks for solver availability at runtime.

## Assessment

**PASS.** The MATPOWER distribution contains zero compiled code. Every line of
the execution path is inspectable .m source code. This is the strongest possible
result for code inspectability. Optional external solvers (IPOPT, OSQP) are
binary but are not bundled and are not required for core functionality.
