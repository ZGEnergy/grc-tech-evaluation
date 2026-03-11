# Test Methodology Notes

This file provides agent-facing implementation guidance for evaluate-tool agents
executing Phase 1 tests. The authoritative source for test definitions, pass
conditions, and grading standards is `Phase1_Test_Protocol.md`. This file contains
implementation notes that were extracted during the v7-to-v8 protocol thinning pass
-- content that helps agents execute tests correctly but is not needed by human
evaluators reading the protocol. Agents should read the relevant suite section
below before executing tests in that suite.

---

## Suite A: Expressiveness

### Resource Type Classification `[A-8, B-4]`

For stochastic tests requiring independent perturbations by resource type,
generators are classified using cost curve slope as a proxy for fuel type:

- **Baseload:** Low marginal cost (bottom quartile of cost curve slopes)
- **Intermediate:** Mid-range marginal cost
- **Peaker:** High marginal cost (top quartile)
- **Wind/Solar:** Zero or near-zero marginal cost with capacity factor patterns. If
  the reference case does not include explicit renewable generators, this category
  may be empty -- document accordingly.

Classification procedure:
1. Extract the polynomial cost coefficients from the generator cost data (MATPOWER
   `gencost` matrix, column for the linear coefficient in a quadratic cost curve,
   or the slope of the first segment in a piecewise-linear cost curve).
2. Sort generators by marginal cost (cost curve slope at rated output).
3. Assign quartile labels: bottom quartile = Baseload, middle two quartiles =
   Intermediate, top quartile = Peaker.
4. Generators with zero or near-zero marginal cost and no minimum generation
   constraint are classified as Wind/Solar.

This classification is used in A-8 (native stochastic support) and B-4 (stochastic
scenario wrapping) to ensure perturbations are independent by resource type.

### A-7 Contingency Sweep Algorithm `[A-7]`

The contingency sweep is an escalating, pruned search -- not a flat N-1 loop. It
tests three things: graph-distance scoping (does the tool expose topology for
enumeration?), efficient contingency re-solve (can branches be removed and restored
without model reconstruction?), and programmability (can the pruning and escalation
logic be expressed cleanly in user code on top of the tool's API?).

Implementation steps:

1. **Scope by graph distance.** From the chosen bus, enumerate all branches within
   graph distance *x* (number of hops along the bus-branch topology). On TINY, use
   *x*=3 to keep the space trivial. On MEDIUM, use *x*=5.
2. **Sweep N-1.** For each scoped branch, remove it, solve DCPF, record load loss
   (total load shed or unserved energy). Restore the branch.
3. **Prune.** Any branch whose removal at order N-1 already produced total load
   loss is pruned from higher-order combinations -- it would dominate any
   combination it appears in.
4. **Sweep N-2.** Enumerate all 2-branch combinations from the unpruned set.
   Remove both, solve, record load loss, restore. Prune branches that caused total
   load loss at N-2 from N-3 combinations.
5. **Escalate.** Continue to N-*m* (on TINY *m*=3, on MEDIUM *m*=2 for grading).
   N-3 and N-4 results on MEDIUM are informational only and do not affect the
   pass/fail determination -- the combinatorial explosion at higher orders is
   infeasible for all tools at 10k-bus scale.

### A-5 Cycling Augmentation Recipes `[A-5]`

The IEEE 39-bus case has a capacity-to-load ratio (~7,367 MW capacity vs ~6,254 MW
peak load) that makes decommitment uneconomical with the default parameters. The
Modified Tiny augmented data (`gen_temporal_params.csv`, `load_24h.csv`,
`reserve_requirements_24h.csv`, `reserve_eligibility.csv`) provides differentiated
costs and temporal parameters that are the primary augmentation mechanism. When using
Modified Tiny data, load the differentiated costs and temporal parameters from
`gen_temporal_params.csv` and the 24-hour load profile from `load_24h.csv`.

The augmentation must produce at least 2 generators cycling (committing and
decommitting) during the 24-hour horizon. Document the augmentation applied.

If Modified Tiny data does not produce cycling, apply the following fallback
augmentation recipes (try in order until cycling is observed):

1. **Raise PMIN.** Set PMIN to 40-60% of PMAX for the largest 3-4 generators. This
   forces the UC to decommit expensive units during low-load hours because keeping
   them online wastes capacity on minimum generation.
2. **Create peakers.** Reclassify 2-3 mid-merit generators as peakers by
   multiplying their linear cost coefficient by 3-5x and setting high startup
   costs. The UC will cycle these on/off as load rises and falls.
3. **Widen load range.** Scale the 24-hour load profile so the trough is 40-50% of
   the peak (the default profile may have a narrow range). A wider load swing
   creates stronger economic incentive to decommit during off-peak hours.

### A-9 Feasibility Relaxation Recipe `[A-9]`

The IEEE 39-bus case has tight thermal limits that may make preventive SCOPF
infeasible on TINY. This is a data finding reflecting the test case's
characteristics, not a tool limitation.

If SCOPF is infeasible with original thermal limits:

1. Scale all `RATE_A` values to 150% of their original values. Re-solve.
2. If still infeasible, escalate to 200%. Re-solve.
3. If still infeasible at 200%, record as infeasible with a note that the network's
   thermal constraints are too tight for preventive SCOPF with the given contingency
   set. This is not a tool failure.

Document the relaxation level applied and whether the relaxation changed the
binding contingency set.

### A-12 Multi-Period DCOPF with Storage `[A-12]`

A-12 tests whether a tool can express a 24-hour multi-period DCOPF with
inter-temporal storage constraints and congestion. It uses the full Modified Tiny
7-step loading recipe (see protocol).

**Quadratic cost rationale:** Quadratic costs (c2 = c1 × 0.001) are mandatory
because purely linear DCOPF produces degenerate dual values — the LP has multiple
optimal vertices with different shadow price vectors. The small quadratic term
regularizes the problem into a strictly convex QP, producing unique dual values.
This makes the BESS arbitrage timing assertion (pass condition 2) reliable. The
c2 coefficient is intentionally small (0.1% of c1) so it does not materially
distort the economic dispatch ordering.

**Cyclic SoC rationale:** Cyclic SoC (SoC at t=0 equals SoC at t=24, value chosen
by optimizer) prevents end-of-horizon dump artifacts where the optimizer discharges
all stored energy in the final hours because there is no future value to conserve
it. Without cyclic SoC, the BESS arbitrage timing assertion would be confounded by
the dump effect. The `init_soc` value from `bess_units.csv` is not used as a
constraint — it is informational only.

**Energy balance tolerance derivation:** The 1.0 MWh tolerance on
`|SoC[t] − SoC[t−1] − η_ch·P_ch[t] + P_dis[t]/η_dis|` accommodates:
- Floating-point precision in the solver (~1e-6 MWh)
- Rounding in solver output extraction (~0.01 MWh)
- Different efficiency application methods between tools (some apply round-trip
  efficiency on charge side only, some split between charge and discharge)
The 1.0 MWh value is deliberately generous — it catches gross errors (wrong
efficiency, wrong sign convention, missing storage constraint) while allowing
legitimate cross-tool variation.

**Infeasibility escalation:** If 70% branch derating produces an infeasible
problem, try 80% derating and record which factor was used. An infeasible problem
at 80% derating indicates a data or formulation issue, not a tool limitation —
investigate before recording fail.

---

## Suite B: Extensibility

### B-4 Perturbation Calibration `[B-4]`

The stochastic scenario wrapping test (B-4) requires calibrated perturbations that
do not cause excessive infeasibility. Key implementation parameters:

- **Infeasibility threshold:** No more than 20% of scenarios (4 out of 20) should
  be infeasible. If more than 20% are infeasible, reduce perturbation magnitude.
- **Sigma reduction procedure:** Start with sigma = 0.15 (15% coefficient of
  variation). If infeasibility exceeds 20%, reduce sigma by half (0.075) and
  regenerate all scenarios. Repeat until the threshold is met.
- **Slack variable fallback:** If even sigma = 0.05 produces >20% infeasibility,
  add load-shedding slack variables with a high penalty cost (10x the most expensive
  generator) to ensure feasibility. Document the slack usage and total shed.

Perturbations must be temporally correlated (not i.i.d. noise per interval) and
independent by resource type (see Resource Type Classification under Suite A).

### Resource Type Classification (cross-reference) `[B-4]`

B-4 uses the same resource type classification as A-8. See the Resource Type
Classification note under Suite A for the full classification procedure.

---

## Suite C: Scalability

### Performance Loop Methodology `[C-1 through C-10]`

All Suite C tests measure wall-clock performance. The following methodology applies
to every C-test:

**Clone vs reload:** When a test requires multiple solves (e.g., contingency loop,
scenario sweep), the base model must be cloned or modified in-place -- not reloaded
from file each iteration. Reloading from file measures I/O performance, not solver
performance. If the tool does not support in-memory cloning, document this as a
finding and measure both the reload-based time and the per-solve time (excluding
I/O).

**Per-unit metrics:** Record both total wall-clock time and per-unit metrics:
- C-3 (DC OPF): time per solver
- C-5 (contingency sweep): time per contingency case, total cases evaluated
- C-6 (stochastic): time per scenario, total scenarios
- C-8 (SCOPF): time per iteration (if screening), total iterations

**Warm-up for Julia tools:** The first invocation of any Julia function triggers
JIT compilation. Run a warm-up solve on TINY and discard its timing before measuring
on the grade network. Use `@elapsed` or `@timed` for the measured run.

**Memory measurement:** Record peak resident set size (RSS) during the solve. On
Linux, use `/proc/self/status` (VmHWM field) or the `resource` module
(`getrusage`). For Julia, use `Base.summarysize` for object sizes and system tools
for process RSS.

**CPU utilization:** Note whether the tool uses multiple cores during the solve.
Single-threaded tools should be documented as such -- this is a finding, not a
failure.

---

## Suite G: FNM Ingestion

### Pass Conditions Runtime Application `[G-FNM-3, G-FNM-4]`

The pass conditions for G-FNM-3 and G-FNM-4 are parameterized in
`data/fnm/reference/pass_conditions.json`. At runtime:

1. Load `pass_conditions.json` from the path
   `data/fnm/reference/pass_conditions.json` relative to the repository root.
2. For G-FNM-3 (DCPF), read the `dcpf` key. It contains:
   - `bus_va_tolerance_deg`: per-bus voltage angle tolerance in degrees
   - `bus_va_pass_fraction`: fraction of buses that must be within tolerance
   - `branch_p_tolerance_mw`: per-branch active power flow tolerance in MW
   - `branch_p_pass_fraction`: fraction of branches that must be within tolerance
   - Hard-fail thresholds (excessive failing fraction, extreme deviation)
   - Outlier classification rules (switched_shunt, q_limit, slack_distribution,
     tap_position, island_boundary)
   - `formulation_difference_max_abs` thresholds
3. For G-FNM-4 (ACPF), read the `acpf` key. It contains cross-tool consistency
   thresholds (used only when two or more tools converge).
4. Apply aggregate thresholds first, then classify outliers using the rules, then
   recompute pass metrics with classified outliers excluded.
5. Check hard-fail conditions last -- these are never relaxed by outlier
   classification or formulation_difference tagging.

### Failure Attribution Procedure `[G-FNM-1 through G-FNM-5]`

When a Suite G test fails, attribute the failure to the correct rubric dimension
using this decision procedure:

1. **Is it a data loading failure?** If the tool cannot parse or load the
   intermediate format tables (G-FNM-1 fails), the failure is an Expressiveness
   finding (data model limitation). G-FNM-2 through G-FNM-5 are skipped.
2. **Is it a field coverage gap?** If G-FNM-2 reports missing DCPF-critical fields,
   the failure is an Expressiveness finding (the tool's data model cannot represent
   required network elements).
3. **Is it a scale failure?** If the tool loads the data (G-FNM-1 passes) and has
   adequate field coverage (G-FNM-2 passes) but fails G-FNM-3 or G-FNM-4 due to
   out-of-memory, timeout, or solver failure that does not occur on MEDIUM-scale
   networks, the failure is a Scalability finding.
4. **Is it a numerical accuracy failure?** If G-FNM-3 fails due to deviations
   exceeding tolerance (not due to solver failure or scale), the failure is an
   Expressiveness finding (incorrect formulation or parameter handling).
5. **Is it an extensibility finding?** If G-FNM-5 shows that critical supplemental
   data cannot be represented even via extension mechanisms, this is an
   Extensibility finding.
6. **Document the attribution** in the result file's `failure_attribution` field
   with the dimension name and a one-sentence justification.

### G-FNM-3/4 Input Routing `[G-FNM-3, G-FNM-4]`

G-FNM-3 and G-FNM-4 use the cleaned network data, not the raw intermediate format.
Two input paths are available:

- **Primary (CSV):** Load intermediate CSV tables from
  `data/fnm/reference/cleaned/intermediate/`. These contain the cleaned network in
  tabular form with all data fixes pre-applied (negative-X coercion, zero-impedance
  fixes, zero-RATE_A fixes, main island extraction, single-slack reduction) per
  `summary_cleaning.json`.
- **Fallback (MATPOWER):** If the tool lacks CSV ingestion capability, load the
  pre-cleaned MATPOWER case from
  `data/fnm/reference/cleaned/fnm_main_island.mat`.

Both paths represent the same cleaned network. Record which path was used via the
`input_path` frontmatter field (`"csv"` or `"matpower"`).

G-FNM-1 and G-FNM-2 still use the raw intermediate format (testing ingestion
fidelity). G-FNM-3 and G-FNM-4 use the cleaned data (testing solver accuracy on
known-good input).

### G-FNM-1 Record-Type Merge Verification `[G-FNM-1]`

The manifest file at `FNM_PATH` is the source of truth for record counts -- it is
not the PSS/E header record count (which may differ due to parser handling of
multi-section lines, 3-winding transformer expansion, or record type merging).

When verifying record counts after ingestion:

- If the tool's data model merges record types (e.g., branches and transformers
  into a single edge table), the merged count must equal the sum of the constituent
  intermediate format table counts.
- Enumerate the tool's merged tables and map each back to the intermediate format
  tables it absorbs.
- Compute: `merged_count == sum(manifest_count[t] for t in constituent_tables)`.
- If the equality does not hold, identify which constituent table's records are
  missing or duplicated.

### G-FNM-5 Classification Comparison `[G-FNM-5]`

This test bridges data model assessment and extensibility assessment. The 7
supplemental CSVs carry market-specific data (trading hub definitions, generator
distribution factors, contingency definitions, interface limits, thermal rating
tiers, outage schedules) that no tool natively ingests.

For each supplemental CSV field, compare the achieved representability (determined
empirically by attempting attachment) against the analytical classification in
`data/fnm/docs/supplemental-csvs.md`:

- **N (natively representable):** The tool's data model has a native attribute that
  directly maps to this field.
- **E (extension representable):** The field can be attached via the tool's
  documented extension mechanism (custom attributes, metadata dictionaries).
- **X (tool-external):** The field cannot be attached to the network model and must
  be carried in a separate data structure.

Discrepancies between analytical and empirical classifications are valuable
findings. Common discrepancy patterns:

- A field classified as E that turns out to be N (the tool has an undocumented
  native attribute) -- this is a positive finding.
- A field classified as E that turns out to be X (the extension mechanism does not
  work as documented) -- this is a negative finding.
- A field classified as N that turns out to be E or X (the native attribute exists
  but does not accept the field's data type or semantics) -- document the mismatch.

Report per-CSV totals: total fields, count by tier (N/E/X), and percentage. Flag
fields where achieved differs from analytical classification.
