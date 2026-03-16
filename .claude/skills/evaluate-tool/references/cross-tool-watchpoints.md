# Cross-Tool Watchpoints

Generic cross-tool guidance for evaluators. No test-specific details — those come from
the protocol and eval-config.

## Solver Compatibility Matrix

| Solver | LP | MILP | QP | NLP | Notes |
|--------|:--:|:----:|:--:|:---:|-------|
| HiGHS | Y | Y | Y | N | Primary for LP/MILP/QP. QP support varies by tool binding. |
| SCIP | Y | Y | N | N | Secondary MILP. Some tools lack SCIP bindings. |
| Ipopt | Y | N | Y | Y | Primary for NLP (AC PF/OPF). Requires MUMPS linear solver. |
| GLPK | Y | Y | N | N | Lightweight baseline. Slower than HiGHS on large problems. |

Known ecosystem limitations (solver facts, not test-specific):
- **QP support:** HiGHS supports QP but some tool bindings may not expose it. If quadratic
  cost curves are present and the tool passes them to the solver, verify the solver handles
  them correctly. If the solver rejects them, document the limitation.
- **MILP performance:** HiGHS and SCIP have different branching heuristics. Large MILPs
  (SCUC at scale) may converge faster on one than the other. Test both where the protocol
  specifies it.
- **NLP convergence:** Ipopt convergence depends heavily on the initial point. See
  `convergence-protocol.md` for the flat-start → DC-warm-start fallback sequence.

## Timing Methodology

- **Python:** Use `time.perf_counter()` for wall-clock timing. Wrap only the solve call,
  not the model construction or result extraction.
- **Julia:** Use `@elapsed` or `@timed` macros. First invocation includes JIT compilation
  time — always run a warm-up solve and discard its timing. Record the second invocation.
- **Octave:** Use `tic`/`toc` around the solve call.

Exclude network loading from solve time. Record per-unit metrics for repeated solves
(time per scenario, time per contingency) alongside totals.

For Julia tools: first invocation of any function triggers JIT compilation. Stay in the
REPL and `include()` scripts to avoid restart overhead. The first solve of any problem
type will be slower; use the second invocation for timing.

## Known Pitfalls by Tool

Brief, factual observations to help evaluators avoid common mistakes:

- **PyPSA:** `n.lpf()` is linear power flow (DCPF), `n.optimize()` is OPF — they are
  different operations. `n.pf()` is AC power flow. Shadow prices require
  `n.optimize()` with appropriate solver settings.
- **pandapower:** Uses internal Newton-Raphson for AC PF, not an external solver. OPF
  uses either internal or PowerModels.jl backend. Check which backend is active.
- **PowerModels.jl:** First Julia invocation includes compilation time; use REPL for
  accurate timing. The `result` dict structure varies by formulation type.
- **PowerSimulations.jl:** Uses PowerSystems.jl for data model, JuMP for optimization.
  System construction from raw data requires significant boilerplate.
- **GridCal:** API surface has changed significantly across versions. Verify examples
  against the installed version.
- **MATPOWER (Octave):** `rundcpf` vs `rundcopf` vs `runopf` — each is a distinct
  function with different formulations. Octave is slower than MATLAB; do not compare
  Octave timings directly against MATLAB benchmarks in literature.

## Resource Type Classification

For stochastic tests requiring independent perturbations by resource type, generators
are classified using cost curve slope as a proxy for fuel type:

- **Baseload:** Low marginal cost (bottom quartile of cost curve slopes)
- **Intermediate:** Mid-range marginal cost
- **Peaker:** High marginal cost (top quartile)
- **Wind/Solar:** Zero or near-zero marginal cost with capacity factor patterns. If the
  reference case does not include explicit renewable generators, this category may be
  empty — document accordingly.

This classification method is documented in the protocol and referenced here for
convenience.

## PTDF Phase-Shifter Correction

Networks containing phase-shifting transformers (nonzero SHIFT column in branch data)
require bus injection and branch flow correction terms when validating PTDF-based flow
predictions. The standard formula `flow = PTDF @ Pinj` omits these corrections.

The full equation is: `flow = PTDF @ (Pinj - Pbusinj) + Pfinj`

where `Pbusinj` and `Pfinj` are correction terms derived from the admittance matrix
construction for branches with nonzero shift angles. Without these corrections, errors
can reach hundreds of MW on networks like ACTIVSg10k (which has 5 phase-shifting
transformers).

When evaluating B-9/C-9 (PTDF extraction/validation):
- Check whether the network has phase-shifting transformers
- If present, either apply Pbusinj/Pfinj corrections or exclude phase-shifting
  branches from the accuracy comparison
- The PTDF matrix itself is typically correct; the error is in the flow reconstruction

## ACTIVSg10k Congestion Characteristics

The ACTIVSg10k network has no binding branch constraints in base-case DCOPF (maximum
loading ~84-85%). This means:
- LMPs are uniform across all buses (no congestion component)
- Tests targeting congestion-driven capabilities (LMP decomposition, SCOPF cost premium,
  distributed slack LMP differences) produce no discriminative signal at MEDIUM scale
- If the protocol specifies preprocessing to tighten branch limits, apply it uniformly

When evaluating tests that depend on congestion signal (A-3, A-9, A-11, B-8, C-3, C-10
at MEDIUM scale), verify that branch constraints are actually binding before interpreting
LMP results. Uniform LMPs may indicate an uncongested network rather than a tool limitation.

## SCUC Generator Cycling

The case39 network has a high capacity-to-load ratio (~7,367 MW vs ~6,254 MW peak) with
uniform generator costs. All tools capable of SCUC report all generators committed for
all 24 hours with zero startups. This makes A-5 a formulation existence test rather than
a UC correctness test.

Modified Tiny's differentiated costs (from `gen_temporal_params.csv`) address the
"all generators on" problem by assigning distinct marginal costs to each generator
class (hydro $5, nuclear $10, coal $25, gas $40). With differentiated costs, the UC
optimizer has an economic incentive to decommit expensive generators during low-load
hours. The 24-hour load profile from `load_24h.csv` provides sufficient load variation
to drive cycling.

When evaluating A-5 (SCUC) on case39:
- Use Modified Tiny data (differentiated costs + temporal params) as the primary
  augmentation
- Do not interpret "all generators on for all hours" as a test failure if using
  vanilla case39 — it is the economically optimal solution for uniform costs
- With Modified Tiny data, at least 2 generators should cycle — if they don't,
  apply fallback augmentation recipes from test-methodology-notes.md
- Verify that the tool can express UC binary variables, min up/down times, and startup
  costs even if they are not exercised

## Convergence Verification

For AC power flow tests (A-2), verify convergence quality beyond the solver's
reported status:
- **Convergence residual** must be reported and below the tool's stated tolerance
- **Iteration count** must be reported (0 iterations indicates the solver did not
  actually run Newton-Raphson)
- **Voltage profile** must differ from flat-start defaults (1.0 pu) on >95% of buses
- If the tool cannot report iteration count or residual, document this as a diagnostic
  quality finding

A tool that reports "converged" but shows 0 NR iterations and flat-start voltages has
not actually solved the AC power flow.

## Measured vs Estimated Timing

All scalability grades must be based on measured wall-clock times, not estimates or
projections:
- Timings must come from actual execution (via `time.perf_counter()`, `@elapsed`,
  `tic`/`toc`)
- Estimated or projected timings must be clearly labeled as "estimated" and cannot
  support pass or qualified_pass on scalability tests
- If a test cannot be executed within the time budget, record fail with the projected
  timing as supplementary context
- JIT compilation overhead (Julia) must be excluded by using warm-up runs

## Unit Consistency (MW vs Per-Unit)

When transferring results between analyses (e.g., DC OPF dispatch to AC feasibility
check), verify unit consistency:
- Print and log `base_power` (base MVA) at each transfer point
- Log dispatch units and limit units before transfer
- Verify that the sending and receiving analyses use the same unit convention
- A mismatch between MW and per-unit values can produce apparent errors of 100x that
  are actually labeling errors, not solver failures

## Suite G Format Context

Suite G (FNM ingestion) tests use an intermediate CSV format rather than MATPOWER .m
case files. The intermediate format comprises 17 CSV tables — one per PSS/E v31 record
type — accompanied by a `manifest.json` sidecar file. The 17 tables are: bus, load,
fixed_shunt, generator, branch, transformer, area, two_terminal_dc, vsc_dc,
impedance_correction, multi_terminal_dc, multi_section_line, zone, interarea_transfer,
owner, facts, and switched_shunt.

The `manifest.json` file carries system-level metadata including `sbase` (baseMVA),
`basfrq` (base frequency), and a `tables` array with each table's `record_count` and
`column_count`. This allows ingestion tests to verify completeness without parsing
every CSV upfront.

A key design choice is the separation of `branch.csv` (transmission lines) from
`transformer.csv` (two- and three-winding transformers). In the MATPOWER .m format,
both are flattened into a single `branch` matrix, losing transformer-specific fields
such as tap ratio (WINDV1/WINDV2), phase shift angle, tap control mode, and winding
impedance detail. The intermediate format preserves all 83 transformer columns from
PSS/E v31, enabling tests that verify tap ratio and phase shift fidelity.

CSV is preferred over MATPOWER .m for G-FNM tests because:
- **Format neutrality:** CSV does not privilege any particular tool's native format,
  so ingestion tests measure the tool's general data-loading capability rather than
  its MATPOWER compatibility
- **Field coverage:** MATPOWER .m cannot represent all PSS/E v31 record types (e.g.,
  FACTS, switched shunts, multi-terminal DC), while the CSV format preserves the full
  field set
- **Schema validation:** JSON Schema files define column types, ranges, and
  required/optional status for each CSV, enabling automated validation

When evaluating G-FNM-1 through G-FNM-5:
- Verify the tool reads from the intermediate CSV directory, not from a MATPOWER .m
  case file
- Use `manifest.json` as the ground-truth source for expected record counts and
  baseMVA
- Transformer data comes from `transformer.csv`, not from the branch table

## Formulation Sophistication Catalog

Different tools use different levels of sophistication in their DC power flow B-matrix
construction. This produces small but systematic differences in DCPF and DCOPF results
across tools, even when all tools ingest identical network data.

**Simplified B-matrix** ignores transformer tap ratios and phase shift angles,
treating all branches as simple impedances. The susceptance of each branch is computed
as `b = -1/x` where `x` is the branch reactance. This approach is computationally
simpler and sufficient for networks with few off-nominal-tap transformers.

**Full B-matrix** incorporates tap ratios and phase shift angles into the admittance
matrix construction. Branches with tap ratios different from 1.0 receive modified
susceptance entries that account for the turns ratio. This produces more accurate
results on networks with many transformers operating at non-unity tap settings.

| Tool | B-Matrix Approach | Notes |
|------|-------------------|-------|
| MATPOWER | Full | Incorporates taps and shifts in `makeBdc()` |
| pandapower | Full | Uses MATPOWER-equivalent admittance construction |
| PyPSA | Full | Incorporates tap ratios in B-matrix via `lpf()` |
| PowerModels.jl | Depends on formulation | `DCPPowerModel` uses simplified; `DCMPPowerModel` uses full |
| GridCal | Version-dependent | Recent versions incorporate taps; older versions may not |
| PowerSimulations.jl | Inherits from PowerModels | Formulation choice determines B-matrix approach |

**Expected deviation magnitudes:** Differences between simplified and full B-matrix
results are concentrated on branches connected to transformers with tap ratios != 1.0.
Absolute flow deviations are typically small (< 5 MW on most branches) but can be
larger on heavily loaded transformer branches in large networks. Voltage angle
deviations are generally < 0.5 degrees.

**Interpreting deviations:**
- **Systematic deviations** correlated with transformer tap ratios indicate a
  formulation sophistication difference, not a bug. Branches connected to
  off-nominal-tap transformers show consistent signed errors.
- **Scattered deviations** with no correlation to transformer locations indicate data
  ingestion errors, incorrect impedance handling, or solver issues. These should be
  investigated as potential bugs.

When evaluating G-FNM-3 and G-FNM-4:
- Before attributing flow differences to bugs, check whether the deviating branches
  are connected to transformers with tap != 1.0
- If deviations are systematic and correlated with tap ratios, classify as
  formulation difference, not error
- If deviations are scattered across non-transformer branches, investigate data
  ingestion fidelity

## Post-Ingestion Fidelity Checks

After a tool ingests the intermediate CSV data, six verification checks confirm that
the network model was loaded correctly. These checks catch silent data-dropping,
type coercion errors, and off-by-one issues before running any power flow analysis.

The six checks are:

1. **Bus count** — total number of buses in the tool's internal model must match
   `manifest.json` bus table `record_count`
2. **Branch count** — total number of non-transformer branches must match
   `manifest.json` branch table `record_count`
3. **Transformer count** — total number of transformers must match `manifest.json`
   transformer table `record_count`. Tools that merge transformers into a unified
   branch table must still report the correct count when filtered by branch type.
4. **baseMVA** — the system base power must match `manifest.json` `sbase` field
   (100.0 MVA for the FNM). A mismatch here causes 100x scaling errors in all
   per-unit calculations.
5. **Slack bus** — at least one bus must be designated as the reference/swing bus
   (IDE=3 in the bus CSV). Verify the tool identifies the correct bus number.
6. **Tap ratio preservation** — transformers with tap ratio = 0.0 in the source data
   use the PSS/E convention where 0.0 means "unity tap" (equivalent to 1.0). Verify
   the tool maps tap=0 to tap=1.0 rather than treating it as a literal zero, which
   would produce division-by-zero or infinite impedance errors.

When evaluating G-FNM-1:
- Compare all six counts against `manifest.json` expected values
- A bus count mismatch may indicate the tool filtered out isolated buses (IDE=4) —
  document whether this is intentional or erroneous
- A branch/transformer count mismatch may indicate the tool merged or split records
  during ingestion

## baseMVA and Q-Limit Pitfalls

The intermediate CSV format uses baseMVA = 100 MVA, recorded in `manifest.json` as
`"sbase": 100.0`. All per-unit quantities in the CSV files are on this base. Tools
that assume a different baseMVA or fail to read it from the manifest will produce
systematically wrong results.

**100x unit mismatch symptom:** If a tool interprets MW values as per-unit (or vice
versa), all power quantities will be off by a factor of 100. This manifests as:
- Generator dispatch values 100x too large or too small
- Branch flows that violate thermal limits by orders of magnitude
- Load values that sum to an implausible system total
- OPF solutions with nonsensical objective function values

**Q-limit encoding:** Generator reactive power limits (QT and QB in the generator CSV)
use the convention where 0.0 may represent either "no reactive capability" or "use
default / unlimited." The interpretation is tool-dependent:
- Some tools treat QT=0 and QB=0 as zero reactive capability, effectively making the
  generator a pure real-power source
- Other tools treat zero Q-limits as "no constraint" and allow unlimited reactive
  dispatch

**False ACPF convergence failure:** If a tool interprets QT=0/QB=0 as zero reactive
capability on generators that should have reactive support, the AC power flow may fail
to converge. The solver cannot find a voltage solution because generators at PV buses
cannot provide the reactive power needed to maintain voltage setpoints. This failure
is a data interpretation issue, not a solver limitation. Symptoms include:
- ACPF divergence on networks that converge in MATPOWER
- Voltage collapse at buses with generators showing Q-limits of zero
- Convergence that succeeds only after manually widening Q-limits

When evaluating G-FNM-1 and G-FNM-4:
- Verify the tool reads baseMVA from `manifest.json` or the data header, not from a
  hardcoded default
- Check that total system load sums to a physically plausible value (tens of GW for
  the reference FNM)
- If ACPF fails to converge, check Q-limit interpretation before concluding the
  solver is inadequate

## PowerModels solve_dc_pf Pitfall

PowerModels.jl's `solve_dc_pf` function can return a trivial solution (all-zero bus
voltage angles and all-zero branch flows) without reporting an error or infeasibility.
This is a silent failure mode that produces results that pass basic structural checks
(correct dimensions, valid numeric types) but contain no useful information.

**Triggering conditions:**
- Incorrect network data that makes the DC power flow system singular or trivially
  satisfiable (e.g., all loads and generators set to zero due to a unit mismatch)
- Solver early exit when the problem is diagnosed as trivially feasible at the
  initial point (all zeros)
- Missing or incorrect bus type assignments that leave no injection imbalance for
  the solver to resolve

**Validation checks:**
- After calling `solve_dc_pf`, verify that at least some non-slack buses have
  nonzero voltage angles. In any network with nonzero load, the DC power flow must
  produce nonzero angles at buses away from the slack bus.
- Verify that at least some branches with nonzero endpoint injections carry nonzero
  flow. A network with load and generation should have nonzero flows on branches
  connecting generation to load.
- Check the `result["termination_status"]` field — but note that a status of
  `LOCALLY_SOLVED` does not guarantee a nontrivial solution.

When evaluating G-FNM-3:
- After every `solve_dc_pf` call, check for the trivial-solution condition before
  accepting results
- If all angles are zero, investigate whether the network data was ingested correctly
  (check baseMVA, bus types, and generator/load status flags)
- A trivial solution combined with correct ingestion counts (G-FNM-1 passing) points
  to a formulation or solver configuration issue rather than a data problem

## DCOPF Soft Constraints (Hard Limit Enforcement)

Standard DC OPF must enforce branch thermal limits as hard constraints — the LP
formulation must forbid branch flows from exceeding their derated ratings in the optimal
solution. Some tools use soft branch flow constraints (LP slack variables) that allow
branches to exceed thermal limits by absorbing the violation into a penalty term in the
objective function.

**Why this matters:** Soft constraints produce LMPs that reflect penalty costs, not true
congestion relief costs. This affects market clearing validity and congestion revenue
adequacy. A tool with soft-constraint DCOPF will pass basic LMP extraction tests but may
award incorrect credit for hard-constraint enforcement.

**Detection method:** After solving DCOPF, check `max(loading_percent)` across all
branches. If any branch exceeds 100% (allowing a numerical tolerance of 1e-4 p.u. =
0.01% for solver precision), the tool uses soft constraints. Source code inspection may
reveal explicit slack variables (`flow_slacks_pos`, `flow_slacks_neg`). A confirming
test: set all branch ratings to zero — a hard-constraint DCOPF must report infeasibility;
a soft-constraint solver will return a "feasible" solution where all limits are violated.

**Classification for A-3:** If max_loading > 1.0 + 1e-4 p.u. in the DCOPF solution,
classify A-3 as `partial_pass` (not `pass`) and document the penalty coefficient. Soft-
constraint DCOPF is a legitimate numerical stabilization technique but must be labeled.

**Confirmed instance:** GridCal `linear_opf` uses soft constraints (probe-005, v10-to-v11 sweep).

## Display Rounding vs Full Precision

Do not use `round(..., N)` or equivalent fixed-point formatting when storing deviation
metrics in result files. Six-decimal-place rounding causes sub-1e-6 deviations to
display as 0.000000, making non-zero floating-point noise indistinguishable from
true machine-zero agreement.

**Required format for deviation metrics (G-FNM-3 and any test reporting numerical deviations):**
- Python: `f'{value:.6e}'` (scientific notation)
- Julia: `@sprintf("%.6e", value)`
- Octave: `sprintf("%.6e", value)`

This applies to `max_deviation_deg`, `max_deviation_mw`, and any other deviation field.
Pass/fail thresholds are unchanged — only the storage format changes.

**Evidence:** Probe-001 (pypsa G-FNM-3, v10-to-v11 sweep) confirmed that a reported
0.0 deviation is actually 1.07e-8 degrees of float64 noise.

## SCIP_jll License — Binary vs Wrapper

In the Julia JLL ecosystem, binary artifact licenses frequently differ from the Julia
wrapper package license. For SCIP specifically:

| SCIP_jll version | SCIP binary version | License |
|-----------------|---------------------|---------|
| v0.2.1+0 | 8.0.0 | ZIB Academic (non-commercial) |
| v800.0.300+0 | 8.0.3 | Apache 2.0 (commercial ok) |

The Apache 2.0 switch happened at SCIP 8.0.3, not 8.0.0. The Julia wrapper package
itself uses MIT, but the binary artifact license governs actual deployments.

**When auditing JLL packages (F-3, F-8):**
1. Record the Julia wrapper package license from `Pkg.status()` metadata.
2. Record the bundled binary artifact license from the JuliaBinaryWrappers release README
   and the upstream source tarball.
3. If they differ, the **binary license governs** the supply chain classification.
4. Use `SCIPversion()` or equivalent to determine the actual binary version at runtime
   — do not rely solely on the Julia package version number.

**Evidence:** Probe-010 (powermodels SCIP, v10-to-v11 sweep) confirmed F-3 correct
(ZIB Academic at v0.2.1=8.0.0). The Apache 2.0 assumption in F-8 was incorrect.

## Convergence Diagnostics — Julia Logging API

Several Julia power system tools emit convergence diagnostics at `@info` log level that
are suppressed by default when the global logger is set to `Logging.Error` or higher.
Before concluding that a tool "provides no convergence diagnostics," enable info logging:

```julia
using Logging
with_logger(ConsoleLogger(stderr, Logging.Info)) do
    result = solve_powerflow(sys, method)
end
```

Or capture to a string buffer:
```julia
log_buffer = IOBuffer()
with_logger(ConsoleLogger(log_buffer, Logging.Info)) do
    result = solve_powerflow(sys, method)
end
log_output = String(take!(log_buffer))
```

**Convergence evidence quality tiers (highest to lowest):**
1. `residual_reported` — solver API exposes final Newton-Raphson residual value
2. `iteration_count_reported` — iteration count available via API or log capture
3. `binary_convergence_api` — return type structurally indicates convergence (e.g., `missing` on failure vs `Dict` on success)
4. `proxy_voltage` — inferred from voltage profile diverging from flat-start defaults

Attempt all tiers. Document which tier was achieved in `convergence_evidence_quality`
frontmatter. See `result-template.md` for the frontmatter field definition.

**Evidence:** Probe-013 (powersimulations A-2, v10-to-v11 sweep) confirmed that
PowerFlows.jl emits `[ Info: The NewtonRaphsonACPowerFlow solver converged after N iterations. ]`
when `@info` logging is enabled — the original evaluation suppressed this.

## C-SMALL Gate Scope (v11 Change)

As of protocol v11, the C-SMALL gate no longer blocks all MEDIUM-tier scalability tests:

- **LP and power-flow MEDIUM tests** (C-1 DCPF, C-2 ACPF, C-3 DCOPF, C-9 PTDF, C-10
  distributed slack) **run unconditionally** — they are not gated by C-4 (SCUC SMALL).
- **MILP MEDIUM tests** remain gated by C-4. A tool that fails C-4 should not receive
  credit for MILP capability at MEDIUM scale.
- **C-8 SCOPF** is gated only by C-3 (DCOPF MEDIUM), not by C-4.

The config-generator will enforce this in the DAG. When reviewing skip results, verify
that LP/PF MEDIUM tests are not recorded as `blocked_by: C-SMALL-gate` — that would
indicate stale results from a v10 evaluation.

## A-12 Multi-Period DCOPF with Storage

A-12 exercises multi-period DCOPF with inter-temporal storage constraints. Key
cross-tool watchpoints:

**Quadratic cost support:** HiGHS supports QP natively, but some tool bindings may
not expose QP to the solver. If the tool's DCOPF formulation silently drops quadratic
cost terms and solves a pure LP, shadow prices will be non-unique and the BESS
arbitrage timing assertion may produce misleading results. Verify that the solver
reports a QP (not LP) solution when quadratic costs are specified.

**MATPOWER (Octave):** MATPOWER lacks native multi-period optimization and storage
modeling. A-12 is expected to fail for MATPOWER with `failure_reason: no_multi_period`.
This is an expressiveness finding, not a bug.

**Julia tools (PowerModels, PowerSimulations):**
- PowerModels.jl does not natively support multi-period OPF or storage. A-12 will
  likely fail unless the evaluator builds a custom JuMP model.
- PowerSimulations.jl has native multi-period support via `DecisionModel` and storage
  via `GenericBattery` / `BatteryEMS`. It is the Julia tool most likely to pass A-12.
  However, Julia startup overhead means the first A-12 run may be slow — use the REPL
  for accurate timing.

**Storage sign conventions:** Tools differ on whether positive P means charge or
discharge. PyPSA uses positive = discharge. pandapower uses positive = generation
(discharge). PowerSimulations uses separate charge/discharge variables. The energy
balance check in pass condition 3 must account for the tool's sign convention.

**Cyclic SoC implementation:** Some tools support cyclic SoC natively (e.g., PyPSA's
`cyclic_state_of_charge=True`). Others require manual constraint addition (e.g.,
`SoC[0] == SoC[T]`). If the tool requires manual constraint addition, this is a
workaround to document, not a failure.
