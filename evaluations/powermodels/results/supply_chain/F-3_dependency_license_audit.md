---
test_id: F-3
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-3: Dependency License Audit

## Result: QUALIFIED PASS

## Finding

Of 114 manifest packages, 110 are MIT or BSD licensed (permissive). Two packages (JuMP, MutableArithmetics) are MPL-2.0 (weak copyleft, file-level only). One package (GLPK.jl) is GPL-3.0 (strong copyleft). The underlying GLPK binary library (GLPK_jll) is also GPL-3.0. SCIP's binary is under ZIB Academic License (non-commercial only). GLPK and SCIP are optional solver dependencies, not required by PowerModels core. Ipopt's binary is EPL-2.0 (weak copyleft, permissive for linking).

## Evidence

**License audit of all 114 manifest packages**(automated scan of LICENSE files in installed packages):

| License | Count | Packages |
|---------|-------|----------|
| MIT | ~107 | PowerModels, InfrastructureModels, JSON, Memento, NLsolve, HiGHS, MathOptInterface, all JLL wrappers, all stdlib, etc. |
| MPL-2.0 | 2 | JuMP v1.29.4, MutableArithmetics v1.6.7 |
| BSD-3-Clause | 1 | PowerModels (core) |
| GPL-3.0 | 1 | GLPK v1.2.1 (Julia wrapper) |

**Copyleft flags:**

1. **GLPK.jl (GPL-3.0)**: The Julia wrapper package `GLPK` v1.2.1 is explicitly GPL-3.0 per its LICENSE.md. The underlying C library (`libglpk.so` via GLPK_jll) is also GPL-3.0. However, GLPK is an optional solver -- PowerModels does not depend on it. It is listed as a direct dependency in the evaluation project only. PowerModels can run with HiGHS (MIT), Ipopt (EPL-2.0), or other solvers without GLPK.

2. **JuMP (MPL-2.0)**: Core dependency. MPL-2.0 is weak copyleft at the file level only. Section 3.3 explicitly allows creating "Larger Works" under different terms. Using JuMP as a library does not impose MPL on the consuming codebase.

3. **MutableArithmetics (MPL-2.0)**: Transitive dep via JuMP. Same MPL-2.0 terms.

4. **Ipopt binary (EPL-2.0)**: The Ipopt_jll binary is under Eclipse Public License 2.0. EPL-2.0 is a weak copyleft license. Linking against Ipopt does not impose EPL on the consuming application.

5. **SCIP binary (ZIB Academic License)**: SCIP_jll's binary is under ZIB Academic License, which restricts use to non-commercial academic institutions. This is a significant licensing concern for commercial deployment. However, SCIP is an optional solver dependency.

**Binary library licenses verified:**
- HiGHS binary: MIT (confirmed via `share/licenses/HiGHS`)
- Ipopt binary: EPL-2.0 (confirmed via `share/licenses/Ipopt`)
- GLPK binary: GPL-3.0 (confirmed via `share/licenses/GLPK`)
- SCIP binary: ZIB Academic (confirmed via `share/licenses/SCIP`)

## Implications

PowerModels core + HiGHS solver pathway is fully permissive (BSD + MIT). The mandatory JuMP dependency is MPL-2.0, which is compatible with commercial use when used as a library. GLPK (GPL-3.0) and SCIP (ZIB Academic) must be excluded from any commercial deployment. This is achievable since they are optional solver packages -- simply omit them from Project.toml. Qualified pass because the default evaluation environment includes GPL-3.0 (GLPK) and non-commercial (SCIP) dependencies, but these are removable without loss of functionality.
