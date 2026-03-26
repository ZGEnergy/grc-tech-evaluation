---
test_id: D-3
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: b9d3ff07
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T18:00:00Z
---

# D-3: Example Verification

## Result: QUALIFIED PASS

## Finding

8 of 10 quickstart examples from the official PowerModels documentation run successfully on
v0.21.5 (Julia 1.10.7). 1 example was skipped (missing test data file), and 1 example
triggers a PSS/E parser edge case on a non-standard test data file. All core MATPOWER-based
examples and the two-level API examples work correctly.

## Evidence

Source: `https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/`

Tested inside devcontainer on 2026-03-24 using PowerModels' bundled test data at
`test/data/matpower/` and `test/data/pti/`.

### Example Results

| # | Example | Status | Notes |
|---|---------|--------|-------|
| 1 | `solve_ac_opf(case3, Ipopt.Optimizer)` | PASS | Returns LOCALLY_SOLVED |
| 2 | `solve_dc_opf(case3, HiGHS.Optimizer)` | PASS | Returns OPTIMAL |
| 3 | PTI `.raw` file (`solve_ac_opf("case3.raw", ...)`) | PASS | `case3.raw` parses and solves correctly; `case0.raw` in test data has non-standard header that fails |
| 4 | Result inspection (solve_time, objective, bus angles) | PASS | All fields accessible as documented |
| 5 | Generic `solve_opf` with ACPPowerModel + SOCWRPowerModel | PASS | Both formulations return LOCALLY_SOLVED |
| 6 | Data modification (set load to zero, re-solve) | PASS | Objective changes correctly (5906.88 -> 2937.16) |
| 7 | PTI `import_all=true` | PASS | Works with standard v33 `.raw` files; `case0.raw` fails (same root cause as Example 3 edge case) |
| 8 | Branch flow/loss inspection on `case3_dc.m` | SKIP | `case3_dc.m` not found at expected location in test data |
| 9 | `instantiate_model` + `optimize_model!` (two-level API) | PASS | LOCALLY_SOLVED |
| 10 | Multi-step: parse + instantiate + optimize | PASS | LOCALLY_SOLVED |

**Totals: 8 pass, 0 fail, 1 skip, 1 edge-case (pass with non-standard file failure) out of 10.**

### PSS/E Parser Edge Case Detail

PowerModels ships 35 `.raw` files in `test/data/pti/`. `case0.raw` uses a non-standard header
(`Header 1` instead of the v33 numeric IC field), triggering:
```
Parsing failed at line 1: value 'Header 1' for IC in section CASE IDENTIFICATION is not of type Int64.
```
The docs example references `case3.raw`, which uses standard v33 format and parses correctly.
This is a test data consistency issue, not a documentation error -- the example as documented
works.

### File Path Friction

The quickstart shows `solve_ac_opf("matpower/case3.m", ...)` without explaining where to
obtain case files. Users must discover that MATPOWER case files ship in PowerModels' test data
or download from the MATPOWER project. This is the most significant accessibility friction for
new users.

## Implications

The core documentation examples are reliable. The MATPOWER-based workflow (examples 1, 2, 4-6)
and the two-level API (examples 9-10) work correctly. The PSS/E edge case affects only a
non-standard test file. The file path omission is a genuine accessibility gap but does not
prevent experienced Julia users from getting started. Status is qualified_pass because 8/10
examples work and the remaining issues are minor.
