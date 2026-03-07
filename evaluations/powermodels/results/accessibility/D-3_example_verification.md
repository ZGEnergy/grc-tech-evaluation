---
test_id: D-3
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# D-3: Find and run all getting-started examples from official docs

## Result: QUALIFIED PASS

## Finding

PowerModels provides two sources of getting-started examples: the official docs Quick Guide (5 code snippets) and the Grid Science tutorial notebook (29 code cells). The Quick Guide examples all use correct, current API and would run unmodified with appropriate solver and data file. The tutorial notebook is from January 2019 and references a local `data/` directory with pglib case files not bundled with PowerModels, but the API calls themselves remain valid against PowerModels v0.21.5. No examples are broken due to API changes; the only friction is data file paths.

## Evidence

### Source 1: Official Docs Quick Guide

The Quick Guide at `<https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/`> provides 5 code examples:

| # | Example | Runs Unmodified? | Notes |
|---|---------|-----------------|-------|
| 1 | `solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)` | YES (with Ipopt) | Uses PowerModels bundled test case path. Works. |
| 2 | `solve_dc_opf("matpower/case3.m", Ipopt.Optimizer)` | YES (with Ipopt) | Same as above. |
| 3 | Result dict access (`result["solve_time"]`, etc.) | YES | Standard Dict operations. |
| 4 | `solve_opf` with formulation argument | YES (with Ipopt) | Demonstrates `ACPPowerModel`, `SOCWRPowerModel`. |
| 5 | `instantiate_model` + `optimize_model!` | YES (with Ipopt) | JuMP model inspection workflow. |

All Quick Guide examples use valid, current API. The path `"matpower/case3.m"` resolves via PowerModels' internal data lookup. Solver requirement (Ipopt) is explicitly stated.

### Source 2: Grid Science Tutorial Notebook

Repository: `<https://github.com/lanl-ansi/tutorial-grid-science`>
File: `Class III - An introduction to PowerModels.jl.ipynb`
Date: January 2019

The notebook contains 29 code cells covering:
- Package setup and data loading
- Network data inspection (bus, load, branch, gen dictionaries)
- `print_summary()` utility
- DC OPF with HiGHS
- AC OPF with Ipopt
- Formulation comparison (ACP vs SOC relaxation gap)
- N-1 generator contingency analysis
- Optimal Transmission Switching (OTS)

| Category | Count | Status |
|----------|-------|--------|
| Run unmodified | 0 | All cells reference `data/pglib_opf_case5_pjm.m` which is not bundled |
| Run with path fix only | 27 | Replacing `"data/pglib_opf_case5_pjm.m"` with a valid MATPOWER file makes all API calls work |
| Broken API | 0 | All function signatures remain valid in v0.21.5 |
| Setup/import cells | 2 | `Pkg.activate(@__DIR__)` is environment-specific |

**Key finding**: The tutorial's API calls (`solve_dc_opf`, `solve_ac_opf`, `solve_opf`, `solve_ots`, `PowerModels.parse_file`, `PowerModels.print_summary`) are all still valid. The only barrier is data file availability, not API staleness.

### Source 3: In-Docs Examples (Other Pages)

The Power Flow documentation page includes additional examples:
- `compute_dc_pf` / `compute_ac_pf` usage
- `calc_branch_flow_ac` / `calc_branch_flow_dc` post-processing
- `update_data!` for merging solutions back into network data

These are code fragments rather than runnable scripts but demonstrate correct API usage.

### Overall Assessment

| Metric | Value |
|--------|-------|
| Total distinct examples found | ~34 (5 Quick Guide + 29 tutorial) |
| Run unmodified | 5 (Quick Guide only) |
| Need minor fix (data path) | 27 (tutorial notebook) |
| Broken / outdated API | 0 |
| Tutorial age | 7 years (Jan 2019) |

## Implications

PowerModels examples are API-stable -- no code has broken over the 7 years since the tutorial was written. However, the example surface area is small (one tutorial notebook, one Quick Guide page) and concentrated on basic PF/OPF workflows. There are no examples for multi-network problems, custom formulations, or advanced workflows like contingency analysis beyond the tutorial's simple gen-outage loop. The Quick Guide examples work out of the box; the tutorial requires only a data path substitution.
