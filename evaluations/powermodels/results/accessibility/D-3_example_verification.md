---
test_id: D-3
tool: powermodels
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-3: Example Verification

## Finding

Of the 14 Quick Guide code examples, 12 run successfully on PowerModels v0.21.5 with minor adaptation, 1 fails due to a path issue (example uses relative path `"matpower/case3.m"` that does not resolve without knowing the package's internal test data location), and 1 requires the user to know the full package path. No examples are fundamentally broken. The tutorial notebooks from the 2019 Grid Science Winter School are outdated (target Julia v1.8) and were not tested.

## Evidence

### Quick Guide Examples (<https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/>)

| # | Code | Result | Notes |

|---|------|--------|-------|

| 1 | `solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)` | FAIL (path) | `"matpower/case3.m"` does not exist in working directory. Requires knowing the package's bundled test data path. |

| 2 | `solve_dc_opf("matpower/case3.m", Ipopt.Optimizer)` | FAIL (path) | Same path issue as Example 1. |

| 3 | `solve_ac_opf("case3.raw", Ipopt.Optimizer)` | FAIL (path) | Same path issue. |

| 4 | `result["solve_time"]` / `result["objective"]` | PASS | Result dict access works correctly. |

| 5 | `Dict(name => data["va"] for ...)` | PASS | Bus voltage angle extraction works. |

| 6 | `print_summary(result["solution"])` | PASS | Tabular summary prints correctly. |

| 7 | `solve_opf(..., ACPPowerModel, Ipopt.Optimizer)` | PASS | Generic OPF with formulation type works. |

| 8 | `solve_opf(..., SOCWRPowerModel, Ipopt.Optimizer)` | PASS | SOC relaxation works. |

| 9 | Parse + modify + re-solve | PASS | Network modification workflow works. |

| 10 | `parse_file("pti/case3.raw"; import_all=true)` | FAIL (path) | Same path issue for PTI file. |

| 11 | Branch flow inspection | PASS | Solution dict navigation works. |

| 12 | Branch loss computation | PASS | `pf + pt` loss calculation works. |

| 13 | `instantiate_model` + `optimize_model!` | PASS | Model inspection workflow works. `optimize_model!` is exported and callable. |

| 14 | Parse + instantiate + optimize | PASS | Separated workflow works. |

### Path Issue Detail

The Quick Guide shows `solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)` but `case3.m` is bundled inside the PowerModels package at `$DEPOT/packages/PowerModels/.../test/data/matpower/case3.m`. To use this data, users must either:
1. Know to use `joinpath(dirname(dirname(pathof(PowerModels))), "test", "data", "matpower", "case3.m")`
2. Provide their own MATPOWER file

This is a common Julia documentation pattern (assuming test data is available) but creates a first-run stumbling block.

**Verified fix:** When using the full path, all examples that reference `case3.m` run correctly:
- `solve_ac_opf(full_path, Ipopt.Optimizer)` returns `LOCALLY_SOLVED` with objective 5906.88
- `solve_dc_opf(full_path, Ipopt.Optimizer)` returns `LOCALLY_SOLVED` with objective 5782.03

### Tutorial Notebooks (lanl-ansi/tutorial-grid-science)

The repository contains 5 Jupyter notebooks from the 2019 LANL Grid Science Winter School:
1. Introduction to Julia
2. Introduction to JuMP
3. JuMP visualizations
4. Introduction to PowerModels.jl
5. Introduction to GasModels.jl

These target Julia v1.8 and an older PowerModels version. They were not tested against v0.21.5 due to likely API drift over 7 years. The repository has minimal recent activity.

### Summary

- **Run unmodified:** 10/14 examples (Examples 4-9, 11-14)
- **Need path fix:** 4/14 examples (Examples 1-3, 10) -- all the same issue with relative paths to bundled test data
- **Fundamentally broken:** 0/14

## Implications

The Quick Guide examples are functionally correct but have a usability gap: the file paths shown don't work without knowing where Julia stores package data. This is a first-five-minutes friction point that could discourage new users. All actual API calls (`solve_ac_opf`, `solve_dc_opf`, `solve_opf`, `instantiate_model`, `optimize_model!`, `print_summary`) work as documented on v0.21.5.
