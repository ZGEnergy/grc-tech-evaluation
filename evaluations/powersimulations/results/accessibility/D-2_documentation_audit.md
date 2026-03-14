---
test_id: D-2
tool: powersimulations
dimension: accessibility
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "d1e20188"
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
timestamp: "2026-03-14T00:00:00Z"
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Finding

Of 10 Suite A tests, **3 are achievable from official documentation alone**, **3 are partially
documented** (requiring source code or issue tracker for key details), and **4 require
significant source reading, trial-and-error, or workarounds not covered in any documentation**.
Critical gaps include: dual/LMP unit conversion, time series boilerplate requirements,
`initialize_model=false` workaround, and storage device formulations.

## Evidence

### Documentation Sources Audited

| Source | URL | Access Date |
|--------|-----|-------------|
| PowerSimulations.jl stable docs | https://nrel-sienna.github.io/PowerSimulations.jl/stable/ | 2026-03-14 |
| PowerSystems.jl stable docs | https://nrel-sienna.github.io/PowerSystems.jl/stable/ | 2026-03-14 |
| PowerFlows.jl dev docs | https://nrel-sienna.github.io/PowerFlows.jl/dev/ | 2026-03-14 |
| PSI formulation library | .../stable/formulation_library/ | 2026-03-14 |
| PSI how-to guides | .../stable/how_to/ | 2026-03-14 |

### Per-Test Documentation Assessment

#### A-1: DCPF — PARTIALLY DOCUMENTED

| Aspect | Documented? | Source |
|--------|------------|--------|
| `solve_powerflow(DCPowerFlow(), sys)` | Yes | PowerFlows.jl tutorial |
| Return type `Dict{String, Dict{String, DataFrame}}` | Yes (dev docs) | PowerFlows.jl tutorial |
| `System(path)` accepts MATPOWER `.m` files | Mentioned in PSY how-to | PowerSystems.jl |
| Column names in bus_results / flow_results | No | Discovered empirically |

**Verdict:** Doable from docs with minor exploration of DataFrame columns.

#### A-2: ACPF — PARTIALLY DOCUMENTED

| Aspect | Documented? | Source |
|--------|------------|--------|
| `solve_powerflow(ACPowerFlow(), sys)` | Yes | PowerFlows.jl tutorial |
| Return type differs from DC (flat Dict) | Yes (dev docs) | PowerFlows.jl tutorial |
| NR iteration count / convergence residual | **Not exposed** | Discovered from return type inspection |
| `TrustRegionACPowerFlow` fallback | Mentioned | PowerFlows.jl tutorial |

**Verdict:** Doable from docs, but convergence diagnostics gap is undocumented.

#### A-3: DCOPF — REQUIRES SOURCE READING

| Aspect | Documented? | Source |
|--------|------------|--------|
| `DecisionModel` + `ProblemTemplate` pattern | Yes | PSI tutorial (single-step) |
| `DCPPowerModel` network formulation | Listed | Formulation library (Network) |
| `ThermalDispatchNoMin` formulation | Listed | Formulation library (ThermalGen) |
| Time series requirement for single-snapshot | **No** | Error message discovery |
| `SingleTimeSeries` + `transform_single_time_series!` | Partial (PSY tutorial) | PowerSystems.jl |
| Time series value is multiplier on `max_active_power` | **No** | Discovered empirically |
| Dual extraction via `read_dual` | Yes (name only) | How-to: read_results |
| **Dual unit conversion (divide by base_power, negate)** | **No** | Discovered empirically |
| `CostCurve(QuadraticCurve(...))` API | Partial | PSY cost types page |
| Branch derating via `set_rating!` | **No** | Discovered from API exploration |

**Verdict:** Core pattern documented, but 3 critical details (time series requirement,
time series semantics as multiplier, dual unit conversion) require trial-and-error or
source reading. A user following only official docs would not produce correct LMP values.

#### A-4: AC Feasibility — DOABLE FROM DOCS

| Aspect | Documented? | Source |
|--------|------------|--------|
| Fix dispatch on System + run ACPF | Inferable | Combination of PSI + PowerFlows docs |
| `set_active_power!` to fix dispatch | Yes | PowerSystems.jl API |

**Verdict:** Doable by combining A-3 and A-2 knowledge, no new undocumented API needed.

#### A-5: SCUC — REQUIRES SOURCE READING

| Aspect | Documented? | Source |
|--------|------------|--------|
| `ThermalStandardUnitCommitment` formulation | Listed with constraints | Formulation library |
| Min up/down time, startup costs, ramp rates | Listed as constraint types | Formulation library |
| `initialize_model=false` bypass | **No** | Discovered when HiGHS initialization fails |
| Direct `JuMP.optimize!` instead of `solve!` | **No** | Workaround for initialization failure |
| Extracting results via `PSI.get_variables()` | **No** (internal API) | Source code reading |
| 24-hour time series setup | Partial | PSY time series tutorial |

**Verdict:** The formulation exists and is documented, but the initialization failure with
HiGHS and the required workaround (`initialize_model=false` + direct JuMP access) are
completely undocumented. A user who follows the official tutorial pattern will hit an
opaque initialization error with no documented resolution.

#### A-6: SCED — REQUIRES SOURCE READING

| Aspect | Documented? | Source |
|--------|------------|--------|
| Two-stage UC+ED pattern | Conceptually described | PSI multi-stage tutorial |
| Fixing commitment variables for ED stage | **No** | Custom JuMP constraint injection |
| Separating UC and ED as distinct models | **No** | Not a supported workflow |

**Verdict:** The multi-stage simulation tutorial shows DA/RT coupling, but fixing commitment
from one model and injecting into another is not documented as a workflow.

#### A-9: SCOPF — REQUIRES SOURCE READING

| Aspect | Documented? | Source |
|--------|------------|--------|
| Built-in SCOPF formulation | **Does not exist** | GitHub issue #944 |
| Custom constraint injection via JuMP | Partial | How-to: register_variable |
| PTDF-based contingency constraint assembly | **No** | Manually assembled |

**Verdict:** No built-in SCOPF. The how-to on custom variables/constraints provides a
starting point, but assembling N-1 contingency constraints from PTDF matrices is entirely
user-developed code.

#### A-10: Lossy DCOPF — NOT ACHIEVABLE

| Aspect | Documented? | Source |
|--------|------------|--------|
| Loss-approximation DC formulation | Not available | `DCPLLPowerModel` listed but non-functional in PSI |

**Verdict:** Failed test. No documentation path exists because the capability does not exist.

#### A-11: Distributed Slack — NOT ACHIEVABLE

| Aspect | Documented? | Source |
|--------|------------|--------|
| Distributed slack formulation | Not available | No formulation in PSI or PM supports this |

**Verdict:** Failed test. No documentation path exists because the capability does not exist.

#### A-12: Multi-Period DCOPF with Storage — REQUIRES SOURCE READING

| Aspect | Documented? | Source |
|--------|------------|--------|
| Multi-period DCOPF | Yes | PSI tutorial + formulation library |
| Storage device model (`EnergyReservoirStorage`) | **Listed in PSY but no PSI formulation** | Source code inspection |
| Manual BESS via JuMP variables/constraints | **No** | Custom assembly |
| `set_normalized_coefficient` for nodal injection | **No** (JuMP internal) | JuMP docs, not PSI docs |
| Quadratic costs fail with HiGHS on multi-period | **No** | Discovered empirically |

**Verdict:** Multi-period DCOPF is documented, but storage requires entirely manual
JuMP model construction. The storage data type exists in PowerSystems.jl but PSI v0.30.2
has no formulation for it — this gap is not documented anywhere.

### Summary Table

| Test | From Docs Alone? | Key Gap |
|------|-----------------|---------|
| A-1 | Partially | Column names undocumented |
| A-2 | Partially | Convergence diagnostics not exposed |
| A-3 | No | Dual unit conversion, TS multiplier semantics |
| A-4 | Yes | None |
| A-5 | No | `initialize_model=false` workaround |
| A-6 | No | UC→ED commitment transfer |
| A-9 | No | No built-in SCOPF |
| A-10 | N/A | Capability absent |
| A-11 | N/A | Capability absent |
| A-12 | No | Storage formulation missing from PSI |

**Score: 3/10 tests doable from docs alone** (A-1 partially, A-2 partially, A-4 yes).
Excluding the 2 tests that failed due to missing capabilities, **3/8 implementable tests
are doc-supported**, and 5/8 require source reading or undocumented workarounds.

### Documentation Quality Notes

**Strengths:**
- Formulation library clearly lists available device models and their constraint sets
- The single-step tutorial demonstrates the full `ProblemTemplate` → `DecisionModel` →
  `build!` → `solve!` workflow
- `read_results` how-to documents variable/dual/parameter extraction function names
- Debugging infeasible models how-to covers slack variables and IIS computation

**Weaknesses:**
- No documentation of dual value units or conversion to $/MWh
- No minimal example loading a MATPOWER file (tutorials use PowerSystemCaseBuilder)
- Time series requirement for single-snapshot OPF is not explained
- Time series multiplier semantics (value * max_active_power) not documented
- `initialize_model=false` workaround not mentioned despite being necessary for HiGHS
- Storage formulation gap (PSY has the type, PSI has no formulation) is silent
- PowerFlows.jl DC vs AC return type difference is documented in dev docs but not stable

## Implications

The documentation gap is a significant accessibility concern. A power systems engineer
with Julia experience could implement A-1 through A-4 from docs, but anything involving
unit commitment (A-5, A-6), advanced OPF formulations (A-9, A-10, A-11), or storage (A-12)
requires reading PSI source code or GitHub issues. The most impactful single gap is the
undocumented dual unit conversion — without it, LMP values are wrong by a factor of 100x
and have the wrong sign, with no warning or documentation to guide correction.
