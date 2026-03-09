---
probe_id: probe-025
tool: powersimulations
source_test: E-6
probe_type: claim_verification
classification: claim_debunked
reason: "Codecov badge shows 78% coverage, not 100% as reported in E-6; the evaluation misread or cited a stale badge"
solver_version: "N/A (documentation probe)"
solver_version_match: true
timeout_seconds: 120
wall_clock_seconds: ~30
timestamp: "2026-03-09T22:15:00Z"
---

# Probe 025: 100% Code Coverage Claim Verification

## Original Claim

From E-6 (maturity/E-6_ci_test_coverage.md):

> "Code coverage is reported at **100%** on the Codecov badge."
>
> "Codecov badge: 100% (as of 2026-03-06)"

The probe investigates whether this 100% claim is accurate.

## Probe Methodology

1. Fetched the Codecov badge SVG from the badge URL referenced in the PowerSimulations.jl README
2. Checked the GitHub README for the badge URL structure
3. Cross-referenced with the Codecov dashboard URLs (NREL-Sienna and legacy NREL-SIIP orgs)
4. Assessed plausibility given repo size (143 source files, 48 test files)

No devcontainer execution needed -- this is a documentation/audit probe.

## Probe Results

**README badge URL:**

```
https://codecov.io/gh/NREL-Sienna/PowerSimulations.jl/branch/main/graph/badge.svg
```

**Badge SVG content (fetched 2026-03-09):**
The badge displays **78%** coverage, not 100%.

**Repository structure:**
- 143 source `.jl` files in `src/`
- 48 test `.jl` files in `test/`
- Repo size: ~139 MB

**Legacy org (NREL-SIIP) badge:** Shows "unknown" -- coverage data no longer available under the old organization name.

## Analysis

**The 100% claim is incorrect.** The Codecov badge for PowerSimulations.jl currently shows **78%** line coverage, not 100%. This is a significant discrepancy -- 78% vs 100% is not a rounding issue or a minor difference.

Possible explanations for the E-6 error:
1. **Misread badge:** The evaluator may have confused PowerSimulations.jl with another Sienna package, or misread a cached/stale badge rendering
2. **Different measurement date:** Coverage could have been 100% at some point and dropped, but this is highly unlikely for a 143-file package
3. **Different metric:** The evaluator may have confused "100% CI pass rate" (green badges) with "100% coverage"

**78% is a reasonable coverage level** for a Julia package of this size. It's respectable but not exceptional. For context:
- Julia's coverage tooling measures line coverage (not branch coverage)
- 78% line coverage with 48 test files against 143 source files is typical for a well-maintained scientific computing package
- 100% line coverage for 143 source files would be extraordinary and practically unheard of for a package of this complexity

**Impact on E-6 assessment:** The E-6 evaluation is marked "informational" (no pass/fail grade), so the incorrect number doesn't change any scoring. However, it does affect the narrative about test maturity -- 78% is good but materially different from 100%.

## Classification Rationale

Classified as **claim_debunked** because:
1. The E-6 evaluation explicitly states "Codecov badge: 100% (as of 2026-03-06)"
2. The actual Codecov badge shows 78% -- a 22 percentage point difference
3. This is not an ambiguous measurement -- the badge SVG contains the exact text "78%"
4. 100% coverage for a 143-file Julia package was implausible on its face

Sources:
- [PowerSimulations.jl GitHub](https://github.com/NREL-Sienna/PowerSimulations.jl)
- [Codecov Badge SVG](https://codecov.io/gh/NREL-Sienna/PowerSimulations.jl/branch/main/graph/badge.svg)
- [Codecov NREL-Sienna org](https://app.codecov.io/gh/NREL-Sienna)
