---
test_id: F-3
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "15e985d9"
status: informational
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

# F-3: Dependency License Audit

## Result: INFORMATIONAL — Two copyleft flags (GLPK GPL-3.0, JuMP MPL-2.0)

## Finding

The vast majority of PowerSimulations.jl's dependency tree is permissively licensed (MIT, BSD, Apache-2.0). Two notable exceptions require attention:

1. **GLPK / GLPK.jl** — GPL-3.0 (strong copyleft). The Julia wrapper and the native GLPK library are both GPL-3.0.
2. **JuMP.jl** — MPL-2.0 (weak copyleft). JuMP is a core dependency that cannot be removed.

Neither is a blocker for use, but the GLPK dependency should be evaluated for removal if GPL obligations are a concern.

## Evidence

### Direct Dependencies — License Summary

| Package | Version | License | Category |
|---------|---------|---------|----------|
| PowerSimulations.jl | v0.30.2 | BSD-3-Clause | Permissive |
| PowerSystems.jl | v4.6.2 | BSD-3-Clause | Permissive |
| PowerFlows.jl | v0.9.0 | BSD-3-Clause | Permissive |
| PowerNetworkMatrices.jl | v0.12.1 | BSD-3-Clause | Permissive |
| InfrastructureSystems.jl | v2.6.0 | BSD-3-Clause | Permissive |
| JuMP.jl | v1.29.4 | **MPL-2.0** | **Weak copyleft** |
| HiGHS.jl | v1.21.1 | MIT | Permissive |
| Ipopt.jl | v1.14.1 | MIT | Permissive |
| GLPK.jl | v1.2.1 | **GPL-3.0** | **Strong copyleft** |
| SCIP.jl | v0.12.8 | MIT | Permissive |
| DataFrames.jl | v1.8.1 | MIT | Permissive |
| CSV.jl | v0.10.16 | MIT | Permissive |
| JSON.jl | v0.21.4 | MIT | Permissive |
| TimeSeries.jl | v0.24.2 | MIT | Permissive |
| Combinatorics.jl | v1.1.0 | MIT | Permissive |

### Key Transitive Dependencies — License Summary

| Package | License | Notes |
|---------|---------|-------|
| MathOptInterface.jl | MIT | JuMP's solver abstraction layer |
| InfrastructureModels.jl | BSD-3-Clause (LANL) | Los Alamos National Lab |
| PowerModels.jl | BSD-3-Clause (LANL) | Los Alamos National Lab |
| ForwardDiff.jl | MIT | Automatic differentiation |
| Memento.jl | MIT | Logging framework |
| NLsolve.jl | MIT | Nonlinear solver |
| HDF5.jl | MIT | File I/O |
| SQLite.jl | MIT | Database |
| Tables.jl | MIT | Table interface |

### Native Solver Libraries (JLL-wrapped binaries)

| Library | License | Julia Wrapper License |
|---------|---------|----------------------|
| HiGHS | MIT | MIT |
| Ipopt | EPL-2.0 | MIT |
| GLPK | **GPL-3.0** | **GPL-3.0** |
| SCIP | Apache-2.0 | MIT |
| MKL (optional) | Intel Proprietary (redistribution allowed via JLL) | MIT wrapper |

### Detailed Assessment of Flagged Licenses

#### GLPK — GPL-3.0 (Strong Copyleft)

- **Scope:** Both the native GLPK library (`GLPK_jll`) and the Julia wrapper (`GLPK.jl`) are GPL-3.0.
- **Impact:** GPL-3.0 requires that derivative works be distributed under GPL-3.0. When GLPK is used as a solver backend, the GPL may apply to the combined work depending on how "derivative work" is interpreted for dynamically linked solver backends.
- **Mitigation:** GLPK is a direct dependency of our evaluation project, not of PowerSimulations.jl itself. It can be replaced with HiGHS (MIT) or another solver without any code changes to PowerSimulations.jl. **Removing GLPK from the project eliminates the GPL obligation entirely.**

#### JuMP — MPL-2.0 (Weak Copyleft)

- **Scope:** JuMP.jl is licensed under Mozilla Public License 2.0.
- **Impact:** MPL-2.0 is a weak copyleft (file-level). Modifications to JuMP source files must be shared under MPL-2.0, but code in other files that merely uses JuMP is not affected. MPL-2.0 is explicitly compatible with Apache-2.0 and is generally considered business-friendly.
- **Mitigation:** No action needed. Using JuMP as a library (without modifying its source) imposes no copyleft obligations on the calling code.

#### Ipopt — EPL-2.0 (Weak Copyleft on native library)

- **Scope:** The native Ipopt library is EPL-2.0; the Julia wrapper is MIT.
- **Impact:** EPL-2.0 is similar to MPL-2.0 in scope. It requires source disclosure only for modifications to the EPL-licensed code itself. Using Ipopt as a solver backend does not create a derivative work.
- **Mitigation:** No action needed for standard use.

#### Intel MKL (Proprietary)

- **Scope:** MKL is an optional linear algebra backend distributed as a JLL binary artifact.
- **Impact:** Intel's license allows redistribution of the runtime binaries. It does not impose source code obligations.
- **Mitigation:** MKL is optional; OpenBLAS (BSD-3-Clause) is the default. MKL can be excluded entirely.

### License Distribution

| License | Count (direct) | Count (transitive, sampled) |
|---------|---------------|---------------------------|
| MIT | 10 | Majority |
| BSD-3-Clause | 5 | Several (NREL + LANL packages) |
| MPL-2.0 | 1 (JuMP) | 0 |
| GPL-3.0 | 1 (GLPK) | 0 |
| EPL-2.0 | 0 | 1 (Ipopt native) |
| Apache-2.0 | 0 | 1 (SCIP native) |
| Proprietary (redistributable) | 0 | 1 (MKL, optional) |

### Data Source

- LICENSE files checked via `gh api repos/<org>/<repo>/contents/LICENSE` and `LICENSE.md` (accessed 2026-03-14)
- GitHub API `license.spdx_id` field for all packages (accessed 2026-03-14)

## Implications

1. **GLPK is the only strong copyleft dependency and it is removable.** GLPK is not required by PowerSimulations.jl. It is one of several interchangeable solver backends. Dropping it from the project's `Project.toml` and using HiGHS (MIT) instead eliminates all GPL exposure.

2. **JuMP's MPL-2.0 is non-concerning for library use.** MPL-2.0 is file-scoped copyleft. Using JuMP as a dependency (without modifying JuMP source files) does not trigger any copyleft obligations. This is the standard use case.

3. **No proprietary or unknown licenses in the critical path.** Every package between PowerSimulations.jl and the solver interface is MIT or BSD-3-Clause.

4. **Recommended configuration for license-clean deployment:**
   - Use HiGHS (MIT/MIT) as the primary LP/MIP solver
   - Use Ipopt (MIT wrapper / EPL-2.0 native) for nonlinear problems
   - Exclude GLPK and MKL from the project
   - This yields a dependency tree that is entirely MIT/BSD/MPL/EPL/Apache — all permissive or weak-copyleft with no source disclosure obligations for users.
