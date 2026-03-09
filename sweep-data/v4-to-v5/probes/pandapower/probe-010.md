---
probe_id: probe-010
tool: pandapower
source_test: B-9
probe_type: formulation_audit
classification: claim_supported
reason: 7.43 pu error reproduced; caused by missing Pbusinj/Pfinj correction terms from tap ratios and phase shifters, not a PTDF matrix error. Applying correction eliminates ALL error to machine precision.
solver_version: pandapower 3.4.0 (PYPOWER DCPF)
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 7.49
timestamp: 2026-03-09T00:00:00Z
---

# Probe 010: PTDF error attribution -- transformer tap ratios vs other factors

## Original Claim

From `evaluations/pandapower/results/extensibility/B-9_ptdf_extraction.md`:

> Max flow difference: 7.43 pu
> Mean flow difference: 0.027 pu
> flow predictions diverge from DCPF results on the 10k-bus network (max diff 7.43 pu), likely due to shunt elements and tap-ratio effects in transformers not fully captured by the basic PTDF formulation.

From probe-008: shunts are confirmed to be 0.0 MW (not the cause). This probe investigates whether transformer tap ratios explain the error and how.

## Probe Methodology

1. Loaded ACTIVSg10k and solved DCPF
2. Identified transformer branches (970 with tap != 1.0) vs line branches (11,736)
3. Computed PTDF flow errors, separated by branch type
4. Checked error propagation: do lines adjacent to transformer buses have higher error?
5. Examined `makeBdc()` return values to find correction terms (Pbusinj, Pfinj)
6. Applied correction: `corrected_flow = PTDF @ (Pinj - Pbusinj) + Pfinj`

Scripts: `probe-010_script.py`, `probe-010_bdc.py`, `probe-010_correction.py`

## Probe Results

### Branch Type Classification

| Type | Count | Fraction |
|------|-------|----------|
| Transformer (tap != 1.0) | 970 | 7.6% |
| Line (tap = 1.0) | 11,736 | 92.4% |

Transformer tap ratio range: 0.956 to 1.100 (mean 1.027).

### Error Distribution by Branch Type

| Metric | Transformer (970) | Line (11,736) |
|--------|-------------------|---------------|
| Max error | 2.22 pu | 7.43 pu |
| Mean error | 0.021 pu | 0.027 pu |
| Branches > 1.0 pu error | 4 | 49 |
| Share of total error | 6.1% | 93.9% |

The worst 20 branches are overwhelmingly lines (18 of 20). The error does NOT concentrate on transformer branches.

### Error Propagation

| Line category | Count | Mean error | Max error |
|---------------|-------|------------|-----------|
| Adjacent to transformer bus | 2,499 | 0.064 pu | 7.43 pu |
| Not adjacent to transformer bus | 9,237 | 0.017 pu | 5.63 pu |

Lines adjacent to transformer buses have 3.6x higher mean error, confirming the error propagates through network topology.

### Root Cause: Missing Correction Terms
The DC power flow equation with transformers is:

```
Bbus @ theta = Pinj - Pbusinj       (bus balance)
flow = Bf @ theta + Pfinj            (branch flow)
```

`makePTDF` computes `H = Bf @ inv(Bbus)`, giving `flow = H @ Pinj`. But the full equation requires:

```
flow = H @ Pinj - H @ Pbusinj + Pfinj
```

The correction terms from `makeBdc()`:
- **Pbusinj**: 10,000-element vector with 8 nonzero entries, max magnitude 733.7 pu. These are bus injection corrections from tap ratios.
- **Pfinj**: 12,706-element vector with 5 nonzero entries, max magnitude 366.8 pu. These are branch flow corrections from phase shifters (5 branches have nonzero shift angles).

### Correction Result

| Metric | Uncorrected PTDF | Corrected PTDF |
|--------|-----------------|----------------|
| Max error | 7.4346 pu | 0.000000 pu |
| Mean error | 0.0268 pu | 0.000000 pu |

Applying `PTDF @ (Pinj - Pbusinj) + Pfinj` eliminates ALL error to machine precision (~1e-12). The PTDF matrix itself is mathematically correct.

### Error Source Breakdown
The 5 branches with nonzero phase shift angles (max 0.454 rad = 26 degrees) produce Pfinj corrections up to 366.8 pu (36,684 MW). These are phase-shifting transformers whose angle shifts create fixed flow injections that the PTDF sensitivity matrix cannot capture because they are independent of bus injections.

The 8 buses with nonzero Pbusinj (max 733.7 pu) are the buses connected to these phase-shifting transformers.

## Analysis

The original claim that "flow predictions diverge from DCPF results [...] likely due to shunt elements and tap-ratio effects" is partially correct:

1. **Shunt attribution: WRONG.** Total shunt MW is 0.0 (confirmed by probe-008).
2. **Tap-ratio attribution: CORRECT but imprecise.** The error is specifically from 5 phase-shifting transformers with nonzero SHIFT angles, not from the 970 transformers with non-unity tap ratios in general.
3. **PTDF matrix correctness: The matrix IS correct.** The error is not in the PTDF computation but in how it's used -- the full flow equation requires additive Pbusinj/Pfinj corrections that are available from `makeBdc()` but not applied in the original test.
4. **Error propagation is real.** Although the root cause is 5 phase shifters, the error propagates through the network admittance matrix, affecting flows on 2,815+ lines (24% of all lines show error > 0.01 pu).

The original test's `qualified_pass` classification remains appropriate: PTDF computation works and produces a correct sensitivity matrix, but naive use without correction terms gives significant errors on networks with phase-shifting transformers.

## Classification Rationale

Classified as `claim_supported` because:
1. The 7.43 pu error is reproduced exactly and is a real phenomenon
2. The attribution to transformer effects is confirmed (specifically phase-shifting transformers)
3. The PTDF matrix is correct -- only the usage is incomplete (missing Pbusinj/Pfinj)
4. The `qualified_pass` grade is appropriate: the tool provides all necessary data to compute correct results, but the naive approach gives large errors
5. The probe provides additional insight (5 phase shifters, not general taps; shunts not involved) that refines rather than contradicts the original claim
