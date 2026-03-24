---
probe_id: probe-007
tool: gridcal
source_test: G-FNM-3
probe_type: formulation_audit
classification: classification_plausible_with_caveats
reason: >
  The 326 outlier branches are 88.7% transformer-adjacent (289/326), meeting
  the 80% structural-pattern threshold used to invoke the formulation_difference
  classification. The deviation pattern is consistent with GridCal's B-matrix
  construction omitting or mis-applying transformer tap ratios in the DCPF.
  However, three caveats limit full confidence: (1) the top deviating branches
  are typed as "Line" not "Xfmr", meaning the adjacency criterion is proximate
  rather than direct; (2) the pass_conditions threshold_deg for
  formulation_difference is null (no magnitude cap), allowing arbitrarily large
  deviations to be excused; (3) the 37 non-transformer-adjacent failing branches
  (11.3%) have no structural explanation and could indicate secondary issues.
  The classification is defensible but the qualified_pass verdict should be
  treated as a significant limitation flag, not a routine annotation.
solver: N/A
solver_version: N/A
solver_version_match: true
tool_version: "VeraGridEngine 5.6.28"
timeout_seconds: 120
wall_clock_seconds: 8
timestamp: "2026-03-14T00:00:00Z"
---

# Probe 007: G-FNM-3 Branch Deviation Pattern Analysis

## Claim Under Investigation

G-FNM-3 DCPF has 326 branches with deviations up to 562,955%, classified as
`formulation_difference`. The concern is whether this classification is
justified or whether the deviations indicate a data ingestion bug or solver error.

## Network Context

The FNM used is the real grid Full Network Model (NDA-restricted), not the
ACTIVSg70k synthetic case. The test uses a 27,862-bus main island extracted from
the FNM PSS/E RAW file, loaded via the MATPOWER fallback path
(`fnm_main_island.m`). The direct CSV ingestion path (G-FNM-1) failed, so all
conclusions are conditional on the MATPOWER conversion being accurate.

Network scale: 27,862 buses, 32,532 matched branches. The ACTIVSg10k available
in `data/networks/` is a different, synthetic network not used here.

## Structural Pattern Analysis

### Failing branch count and adjacency

| Category | Count | Fraction |
|----------|-------|----------|
| Total failing branches | 326 | 1.00% of 32,532 |
| Transformer-adjacent | 289 | 88.7% |
| Non-transformer-adjacent | 37 | 11.3% |
| Threshold to qualify | 80% | **Met** |

### Top 5 deviating branches

| From | To | Object Type | GridCal (MW) | Reference (MW) | Dev % |
|------|-----|-------------|-------------|----------------|-------|
| 1668 | 88630 | Line | 111,582 | -19.82 | 562,955% |
| 21476 | 84022 | Line | -68,017 | 12.57 | 541,075% |
| 72100 | 73053 | Line | -13,365 | 3.23 | 413,787% |
| 180421 | 36990 | Xfmr | 5,234 | -1.61 | 325,193% |
| 1635 | 92191 | Line | -352,878 | 109.50 | 322,365% |

Key observation: 4 of the top 5 are classified as "Line" objects in GridCal's
data model. The `transformer_adjacent` flag means at least one endpoint bus
appears in the set of transformer terminal buses — these are not transformers
themselves but lines immediately connected to transformers.

### Deviation magnitude and sign pattern

- Flow magnitudes are 3–5 orders of magnitude above reference values
- Example: bus 1635→92191: GridCal 352,878 MW vs reference 109.5 MW
- Signs are not universally flipped — both positive and negative deviations occur
- This rules out a simple sign convention difference

The magnitude (×3000 errors) is far beyond tap ratio mishandling alone (which
would produce errors proportional to `(tap - 1)^2 / X_pu`, typically 10–100%
for realistic off-nominal taps). This magnitude is more consistent with
near-zero branch reactance in the B-matrix — i.e., transformers with off-nominal
tap ratios causing the effective per-unit reactance seen by the DCPF to be
computed incorrectly (possibly near-zero or negative), producing numerical
instability in the B-matrix solution for adjacent branches.

## Assessment of the formulation_difference Classification

### Evidence supporting the classification

1. **88.7% transformer-adjacency** exceeds the 80% structural pattern threshold
2. **Bus angles match perfectly** (100% within 1.0 deg, 0.0 deg max deviation)
   — the B-matrix is correct for angle computation but incorrect for branch
   flow extraction for transformer-adjacent branches. This is consistent with
   a known GridCal issue where `Sf` is computed using an incomplete branch
   admittance matrix that does not account for tap ratios in transformer
   branches, while the voltage solution correctly uses the full admittance
   in the nodal equations.
3. **99% of branches pass** — the failure is isolated to transformer-adjacent
   branches, not distributed randomly

### Evidence raising concern about the classification

1. **Deviation magnitude is disproportionate.** Tap-ratio formulation
   differences in standard DCPF implementations produce deviations of
   10–200%, not 100,000–560,000%. The extreme magnitudes suggest something
   more severe than a convention difference (e.g., per-unit base mismatch,
   branch admittance sign error for transformers, or transformer branches
   being excluded from the `Sf` computation entirely with residual injections
   flowing through adjacent lines).

2. **"Line" objects at the top of the deviation list.** The highest-deviation
   branches are `Line` objects, not transformers. This means the error is
   propagating from transformers into the adjacent lines — the transformer
   itself may have near-zero or zero `Sf` (its flow allocated elsewhere),
   with the adjacent line receiving a massive compensation flow. This is
   internally inconsistent with a simple tap-ratio convention difference.

3. **No magnitude cap in pass_conditions.** The `formulation_difference_max_abs`
   `threshold_deg` is set to `null` in `pass_conditions.json`, meaning there
   is no upper bound on how extreme a deviation can be while still being
   classified as a formulation difference. This creates a loophole where
   arbitrarily large errors can be excused if 80%+ of failing branches happen
   to be transformer-adjacent.

4. **37 non-transformer-adjacent failures (11.3%) are unaccounted for.**
   The test code classifies the overall pattern as `formulation_difference`
   if the aggregate threshold is met, but does not separately classify or
   bound the 37 branches that have no structural proximity to transformers.
   These could indicate a second, independent issue.

## Classification Decision

The `formulation_difference` classification is **plausible but overstated**.

The structural evidence (transformer-adjacency, perfect angle match, localized
failures) is consistent with GridCal's DCPF Sf computation having a known
limitation with transformer branches. This is a documented behavior in
VeraGridEngine's linear power flow — branch flows for transformer elements use
a simplified model.

However, the classification mechanism has two design flaws that allow it to
over-excuse results:

1. No magnitude cap — the protocol should impose a maximum permissible
   deviation even under `formulation_difference` (e.g., 1000%). At 562,955%,
   the GridCal result for those branches is effectively useless for any
   operational purpose.
2. Adjacency proxy — the test correctly identifies that transformers cause
   the problem, but classifying adjacent lines as "transformer-adjacent" blurs
   whether the root cause is a transformer modeling issue or a broader
   B-matrix sparsity/index error.

## Impact on G-FNM-3 Verdict

The `qualified_pass` verdict is defensible as a protocol outcome (the 80%
threshold is met, aggregate metrics pass), but the result should carry a
stronger warning:

- GridCal DCPF branch flows for transformer-adjacent branches in real grid
  models are unreliable at the magnitude level (errors up to ~3000×)
- Any application requiring correct branch flows near transformers (N-1
  contingency, thermal limit checking, loss allocation) will produce wrong
  results
- The "qualification" annotation understates the severity — this is a
  material limitation, not a minor formulation nuance

## Note on "ACTIVSg70k"

The probe description references "ACTIVSg70k" but the actual test uses the FNM
main island (27,862 buses, NDA-restricted). The `data/networks/` directory
contains case_ACTIVSg10k.m (10,000 buses) and case_ACTIVSg2000.m but no
ACTIVSg70k file. No execution was needed to verify this finding.
