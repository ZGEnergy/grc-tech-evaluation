---
test_id: F-3
tool: powermodels
dimension: supply_chain
network: N/A
status: qualified_pass
workaround_class: null
timestamp: "2026-03-13T23:01:54Z"
protocol_version: v10
skill_version: v1
test_hash: "ac2a9361"
---

# F-3: License audit of all direct and transitive dependencies

## Finding

The dependency stack is predominantly MIT/BSD-licensed with two flagged items requiring attention: (1) **GLPK.jl wrapper** is GNU GPL v3, which is copyleft; (2) **SCIP binary** (SCIP 8.0.0 via SCIP_jll v0.2.1) uses the ZIB Academic License, which restricts use to non-commercial academic institutions. Both are optional solver dependencies that can be excluded from commercial deployments. The core PowerModels + JuMP + Ipopt + HiGHS stack is clean for commercial use.

## Evidence

Licenses audited from package source trees under `/opt/julia-depot/packages/`. Julia wrapper license files were read directly; underlying binary licenses verified from JLL LICENSE files and known upstream project licenses.

### PowerModels core dependencies:

| Package | License | Classification |
|---------|---------|---------------|
| PowerModels 0.21.5 | BSD-3 (LANL) | Permissive |
| InfrastructureModels 0.7.8 | BSD-3 (LANL) | Permissive |
| JuMP 1.29.4 | MPL-2.0 | Weak copyleft (file-scoped) |
| MathOptInterface 1.49.0 | MIT | Permissive |
| MutableArithmetics 1.6.7 | MPL-2.0 | Weak copyleft (file-scoped) |
| MathOptIIS 0.1.2 | MIT | Permissive |
| JSON 0.21.4 | MIT | Permissive |
| NLsolve 4.5.1 | MIT | Permissive |
| Memento 1.4.1 | MIT | Permissive |
| ForwardDiff 1.3.2 | MIT | Permissive |

### Solver wrappers and binaries:

| Package | Julia Wrapper License | Binary License | Flag |
|---------|----------------------|----------------|------|
| Ipopt.jl 1.14.1 | MIT | EPL 2.0 (Eclipse) | OK — weak copyleft |
| HiGHS.jl 1.21.1 | MIT | MIT | Clean |
| GLPK.jl 1.2.1 | **GNU GPL v3** | GPL v3 | **Copyleft** |
| SCIP.jl 0.11.6 | MIT | **ZIB Academic** (SCIP 8.0.0) | **Non-commercial only** |

### Native binary dependencies (JLL artifacts):

| JLL Package | Upstream License | Notes |
|-------------|-----------------|-------|
| Ipopt_jll | EPL 2.0 | COIN-OR; weak copyleft, commercial OK |
| MUMPS_seq_jll | CeCILL-C | French free software; LGPL-compatible, commercial OK |
| HiGHS_jll | MIT | Fully permissive |
| GLPK_jll | GPL v3 | Copyleft applies to derived works |
| SCIP_jll v0.2.1 (SCIP 8.0.0) | ZIB Academic | Non-commercial only |
| SCIP_PaPILO_jll | ZIB Academic (SCIP) + LGPL v3 (PaPILO) | Mixed; SCIP component restricts |
| SPRAL_jll | BSD-3 | Permissive |
| bliss_jll | MIT | Permissive |
| boost_jll | BSL-1.0 | Permissive |
| ASL_jll | MIT | Permissive |
| OpenBLAS_jll / OpenBLAS32_jll | BSD-3 | Permissive |
| GMP_jll | LGPL v3 / GPL v2 | Dynamic linking OK under LGPL |
| METIS_jll | Apache-2.0 | Permissive |
| SuiteSparse_jll | BSD/LGPL (mixed per component) | Dynamic linking OK |

### Remaining pure-Julia transitive dependencies:

All other packages (ADTypes, Adapt, ArrayInterface, BenchmarkTools, CodecBzip2, CodecZlib, Compat, ConstructionBase, DiffResults, DiffRules, DifferentiationInterface, Distances, DocStringExtensions, FiniteDiff, IrrationalConstants, JLLWrappers, LineSearches, LogExpFunctions, MacroTools, NaNMath, NLSolversBase, OrderedCollections, Parsers, PrecompileTools, Preferences, Reexport, Requires, Setfield, SpecialFunctions, StaticArraysCore, StatsAPI, TranscodingStreams) are MIT licensed.

Julia stdlib packages (Base64, Dates, LinearAlgebra, Random, SparseArrays, etc.) are covered by Julia's MIT license.

### Flagged items:

1. **GLPK.jl (GPL v3):** The GLPK Julia wrapper is explicitly GNU GPL v3. Using GLPK in a commercial application may trigger copyleft obligations. GLPK is an optional solver dependency — commercial deployments that exclude GLPK are unaffected.

2. **SCIP / SCIP_jll (ZIB Academic License):** The SCIP binary (SCIP 8.0.0 via SCIP_jll v0.2.1) is licensed under the ZIB Academic License, which explicitly restricts use to non-commercial academic institutions. Note: SCIP 9.x (released 2024) moved to Apache 2.0, but the version pinned in this manifest is SCIP 8.0.0 and remains under ZIB Academic. SCIP is an optional solver dependency.

3. **MPL-2.0 (JuMP, MutableArithmetics):** Mozilla Public License 2.0 is a weak, file-scoped copyleft. Modifications to JuMP source files must be shared under MPL-2.0, but using JuMP as a library does not trigger copyleft on calling code. Acceptable for commercial use.

4. **EPL 2.0 (Ipopt):** Eclipse Public License 2.0 is similarly file-scoped. Ipopt can be used commercially without copyleft obligations on calling code.

5. **GMP_jll (LGPL v3):** GNU Lesser GPL — dynamic linking is permitted without copyleft trigger. Standard practice.

## Implications

For commercial deployment: SCIP must be excluded (ZIB Academic License prohibits commercial use at the pinned v8.0.0). GLPK carries GPL v3 obligations if used. Excluding both SCIP and GLPK removes all problematic licenses. The core stack of PowerModels (BSD-3) + JuMP (MPL-2.0) + Ipopt (EPL 2.0) + HiGHS (MIT) is clean for commercial use.

Status is `qualified_pass` because the problematic licenses attach to optional solver dependencies that can be excluded. No proprietary or unknown licenses were found.
