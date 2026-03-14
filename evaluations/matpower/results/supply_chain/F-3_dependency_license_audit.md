---
test_id: F-3
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: v10
skill_version: v1
test_hash: eace1faa
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

# F-3: Dependency License Audit

## Result: PASS

## Finding

All bundled dependencies use the BSD 3-Clause license, matching the core package license. External optional solvers have varied licenses, with GLPK's GPL-3.0 being the only potentially concerning copyleft license, but it is optional and not required for any core functionality.

## Evidence

**Bundled package licenses (all verified via LICENSE files in distribution):**

| Package | License | License File Path | Copyleft |
|---------|---------|-------------------|----------|
| MATPOWER core | BSD 3-Clause | `matpower8.1/LICENSE` | No |
| MIPS | BSD 3-Clause | `matpower8.1/mips/LICENSE` | No |
| MP-Opt-Model | BSD 3-Clause | `matpower8.1/mp-opt-model/LICENSE` | No |
| MP-Test | BSD 3-Clause | `matpower8.1/mptest/LICENSE` | No |
| MOST | BSD 3-Clause | `matpower8.1/most/LICENSE` | No |
| SDP_PF (extra) | BSD 3-Clause | `matpower8.1/extras/sdp_pf/LICENSE` | No |
| SynGrid (extra) | BSD 3-Clause | `matpower8.1/extras/syngrid/LICENSE` | No |
| simulink_matpower (extra) | BSD 3-Clause | `matpower8.1/extras/simulink_matpower/LICENSE` | No |

**External optional solver licenses:**

| Solver | License | Required? | Copyleft Risk |
|--------|---------|-----------|---------------|
| MIPS (built-in) | BSD 3-Clause | Built-in | None |
| GLPK | GPL-3.0 | Optional (LP/MILP) | Yes -- copyleft |
| IPOPT | EPL-2.0 | Optional (NLP) | Weak copyleft |
| HiGHS | MIT | Optional (LP/MILP/QP) | None |
| Gurobi | Commercial | Optional | N/A (not OSS) |
| CPLEX | Commercial | Optional | N/A (not OSS) |

**GLPK copyleft note:** GLPK is GPL-3.0, which is a strong copyleft license. However, GLPK is:
1. An external, optional solver -- not bundled with MATPOWER
2. Linked at runtime via Octave's built-in GLPK bindings (Octave itself is GPL)
3. Not required for any core functionality (MIPS handles all PF/OPF natively)

**IPOPT EPL-2.0 note:** EPL-2.0 is a weak copyleft license. Modifications to IPOPT itself must be shared, but using IPOPT as a solver does not impose copyleft obligations on MATPOWER code or user code.

**Problematic licenses:** 0 (among bundled dependencies)
**Unknown licenses:** 0

## Implications

The supply chain is clean. All bundled code is BSD 3-Clause. The only copyleft exposure is through optional external solvers (GLPK GPL-3.0), which can be avoided by using MIPS (built-in) or HiGHS (MIT) instead. No license flags need to be raised for the core distribution.
