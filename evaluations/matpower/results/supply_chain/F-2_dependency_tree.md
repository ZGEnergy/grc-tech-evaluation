---
test_id: F-2
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-2: Dependency Tree

## Architecture

MATPOWER is **self-contained** — it ships all sub-packages in a single distribution
zip file. It requires only a MATLAB or GNU Octave runtime.

## Sub-Packages (All Bundled)

| Package | Version | Purpose | Author |
|---------|---------|---------|--------|
| MATPOWER (core) | 8.1 | Power flow, OPF, sensitivity | Ray Zimmerman |
| MIPS | 1.5.2 | Interior point solver | Ray Zimmerman |
| MP-Opt-Model | 5.0 | Optimization model abstraction layer | Ray Zimmerman |
| MPTEST | 8.1 | Testing framework | Ray Zimmerman |
| MOST | 1.3 | Multi-period optimal scheduling | Ray Zimmerman |

## Extras (Optional, Bundled)

| Package | Purpose | License |
|---------|---------|---------|
| SynGrid | Synthetic grid generation | BSD-3 |
| SDP_PF | Semidefinite programming power flow | BSD-3 (PSERC) |
| Simulink MATPOWER | Simulink interface | ETH Zurich (BSD-3-like) |

## External Runtime Dependencies

| Dependency | Required | Notes |
|------------|----------|-------|
| GNU Octave 6+ or MATLAB R2020b+ | YES | Runtime environment |
| GLPK | NO (bundled with Octave) | LP/MILP solver |
| HiGHS | NO (optional) | LP/MIP solver (new in v8.1) |
| IPOPT | NO (optional) | Nonlinear solver (MEX binary) |
| OSQP | NO (optional) | QP solver (MEX binary) |

## Octave Package Check

```
octave --eval "pkg list"
=> no packages installed.
```

MATPOWER does not use Octave's package manager. It is installed by adding
directories to the MATLAB/Octave path.

## Dependency Graph

```
MATPOWER 8.1
  |-- MIPS 1.5.2 (bundled, no external deps)
  |-- MP-Opt-Model 5.0 (bundled, depends on MIPS)
  |-- MPTEST (bundled, no external deps)
  |-- MOST 1.3 (bundled, depends on MATPOWER + MP-Opt-Model)
  |-- [optional] IPOPT MEX (external binary)
  |-- [optional] OSQP MEX (external binary)
  |-- [optional] HiGHS (external, if installed)
  \-- GNU Octave 6+ or MATLAB R2020b+ (runtime)
       \-- GLPK (bundled with Octave)
```

## Assessment

**PASS.** MATPOWER has the simplest dependency tree of any tool evaluated.
All core functionality runs with zero external dependencies beyond the Octave/MATLAB
runtime. No pip/npm/cargo install, no transitive dependency resolution, no version
conflicts possible. The self-contained zip distribution is the gold standard for
supply chain simplicity.
