---
test_id: F-3
tool: powermodels
dimension: supply_chain
network: N/A
status: qualified_pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "15e985d9"
---

# F-3: Check license of every direct and transitive runtime dependency

## Finding

The dependency stack is predominantly MIT/BSD-licensed with two flagged items: (1) **GLPK.jl wrapper** is GNU GPL v3, which is copyleft and incompatible with proprietary code if GLPK is used; (2) **SCIP binary** (via SCIP_jll) uses the ZIB Academic License, which explicitly restricts use to non-commercial academic institutions. All other packages are MIT, BSD-3, MPL 2.0, EPL 2.0, or CeCILL-C (MUMPS), which are permissive or weakly copyleft with no commercial restrictions.

## Evidence

Licenses audited from `/opt/julia-depot/packages/` and `/opt/julia-depot/artifacts/`:

### PowerModels direct dependencies:

| Package | License | Notes |
|---------|---------|-------|
| PowerModels | BSD-3 (LANL) | Main package — permissive |
| InfrastructureModels | BSD-3 (Triad/LANL) | Permissive |
| JuMP | MPL 2.0 | Weak copyleft — file-level, not project-level |
| MathOptInterface | MIT | Permissive |
| JSON.jl | MIT | Permissive |
| NLsolve.jl | MIT | Permissive |
| Memento.jl | MIT | Permissive |
| PrecompileTools | MIT | Permissive |

#### Solver wrappers (Julia layer):

| Package | Julia wrapper license | Binary license |
|---------|----------------------|----------------|
| Ipopt.jl | MIT | EPL 2.0 (Eclipse) — copyleft but weak; OSS-compatible |
| HiGHS.jl | MIT | MIT |
| GLPK.jl | **GNU GPL v3** | GPL v3 (same) |
| SCIP.jl | MIT | **ZIB Academic License** |

#### Native binaries (JLL artifacts):

| JLL Package | Binary license | Notes |
|-------------|---------------|-------|
| Ipopt_jll | EPL 2.0 | Ipopt source; MUMPS sub-dependency is CeCILL-C |
| MUMPS_seq_jll | CeCILL-C | French free software license; compatible with commercial use |
| HiGHS_jll | MIT | Fully permissive |
| GLPK_jll | GPL v3 | GPL applies to derived works |
| SCIP_jll | **ZIB Academic** | **Non-commercial only** |
| SCIP_PaPILO_jll | **ZIB Academic** (SCIP) + LGPL v3 (GCG/PaPILO) | Mixed; SCIP component restricts commercial use |
| bliss_jll | MIT | Permissive |
| boost_jll | BSL-1.0 | Permissive |
| SPRAL_jll | BSD-like | OSS |

#### Other transitive pure-Julia deps:
All remaining packages (ADTypes, Adapt, ArrayInterface, BenchmarkTools, CodecBzip2/Zlib, Compat, ConstructionBase, DiffResults, DiffRules, DifferentiationInterface, Distances, DocStringExtensions, FiniteDiff, ForwardDiff, IrrationalConstants, JLLWrappers, LineSearches, LogExpFunctions, MacroTools, MathOptIIS, MutableArithmetics, NaNMath, NLSolversBase, OrderedCollections, Parsers, Reexport, Requires, Setfield, SpecialFunctions, StaticArraysCore, StatsAPI, TranscodingStreams) — all MIT or BSD licensed.

#### Flagged items:

1. **GLPK.jl (GPL v3):** The GLPK Julia wrapper is licensed under GNU GPL v3. Using GLPK in a commercial application may require open-sourcing any derivative software under GPL. The GLPK solver is an optional dependency — commercial deployments that avoid GLPK are not affected.

2. **SCIP / SCIP_jll (ZIB Academic License):** The SCIP binary (via SCIP_jll 0.2.1) is licensed under the ZIB Academic License, which explicitly states: "This license applies to you only if you are a member of a noncommercial and academic institution." Commercial use is prohibited. SCIP is an optional dependency; commercial deployments must not use SCIP.

Note: SCIP 9.x was released under Apache 2.0 in 2024, but the version in this manifest (SCIP_jll 0.2.1 / SCIP binary ~8.x) predates that change. The ZIB Academic restriction applies to this specific pinned version.

**MPL 2.0 (JuMP):** Mozilla Public License 2.0 is a weak, file-scoped copyleft. Modifications to JuMP source files must be shared, but JuMP can be used as a library without open-sourcing the calling code. This is an acceptable commercial risk.

**EPL 2.0 (Ipopt):** Eclipse Public License 2.0 is similarly file-scoped. Ipopt can be used in commercial applications without triggering copyleft obligations on calling code.

## Implications

**For commercial deployments:** SCIP must be excluded (ZIB Academic License prohibits commercial use). GLPK carries GPL v3 obligations if used. Excluding both SCIP and GLPK from the deployment scope removes all problematic licenses. HiGHS (MIT) and Ipopt (EPL 2.0) are safe for commercial use without restriction.

This test receives `qualified_pass` because the problematic licenses attach to optional solver dependencies (SCIP, GLPK) that can be excluded from commercial deployments. The core PowerModels + JuMP + Ipopt + HiGHS stack is clean for commercial use.
