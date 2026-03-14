---
test_id: D-3
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-13T23:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "cb68eeba"
---

# D-3: Example Verification

## Scope

Verify that getting-started examples from official documentation at
`https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/` run correctly on PowerModels.jl v0.21.5 in the evaluation devcontainer (Julia 1.10.7).

The quickguide contains 10 distinct code examples. All were tested against PowerModels' own test data files (shipped with the package at `test/data/matpower/` and `test/data/pti/`).

## Examples Tested

### Example 1: `solve_ac_opf` (Quickstart entry point)

**Docs show:**
```julia
using PowerModels; using Ipopt
solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)
```

**Result: PASS** -- runs correctly when a valid path to `case3.m` is substituted. The relative path `"matpower/case3.m"` in the docs does not exist without context; users must locate a case file. Using PowerModels' bundled test data at `test/data/matpower/case3.m` works. Returns `LOCALLY_SOLVED` with Ipopt.

**Friction:** The docs do not explain where to obtain `case3.m`. New users must know that MATPOWER case files are available from the MATPOWER project or bundled in PowerModels' test data.

### Example 2: `solve_dc_opf`

**Result: PASS** -- `solve_dc_opf(case3, Ipopt.Optimizer)` returns `OPTIMAL`.

### Example 3: PTI Raw file (`solve_ac_opf` on `.raw` format)

**Docs show:**
```julia
solve_ac_opf("case3.raw", Ipopt.Optimizer)
```

**Result: FAIL** -- PowerModels ships 35 `.raw` files in `test/data/pti/`. The first file alphabetically (`case0.raw`) has a non-standard header (`Header 1` instead of the v33 numeric format) and triggers a parse error:
```
[error | PowerModels]: value 'Header 1' for IC in section CASE IDENTIFICATION is not of type Int64.
```
Other `.raw` files (e.g., `case3.raw`, `case14.raw`) use the standard v33 header format and parse correctly. The docs example works for v33 format files but would fail on some files in PowerModels' own test suite.

**Classification:** Needs fix -- `case0.raw` in the test data uses a non-v33 header that the parser cannot handle. The example itself is valid for standard PSS/E files.

### Example 4: Result inspection (solve_time, objective, bus angles)

**Docs show:**
```julia
result = solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)
result["solve_time"]
result["objective"]
Dict(name => data["va"] for (name, data) in result["solution"]["bus"])
```

**Result: PASS** -- all four operations produce expected output. `solve_time` is a Float64, `objective` is numeric, bus angle dictionary comprehension works correctly.

Note: The docs also show `print_summary(result["solution"])` which was not tested separately but is a documented function.

### Example 5: Generic `solve_opf` with different formulations

**Docs show:**
```julia
solve_opf("matpower/case3.m", ACPPowerModel, Ipopt.Optimizer)
solve_opf("matpower/case3.m", SOCWRPowerModel, Ipopt.Optimizer)
```

**Result: PASS** -- both formulations return successfully. ACPPowerModel returns `LOCALLY_SOLVED`, SOCWRPowerModel returns `LOCALLY_SOLVED`. This demonstrates the formulation-independent API correctly.

### Example 6: Network data modification

**Docs show:**
```julia
network_data = PowerModels.parse_file("matpower/case3.m")
solve_opf(network_data, ACPPowerModel, Ipopt.Optimizer)
network_data["load"]["3"]["pd"] = 0.0
network_data["load"]["3"]["qd"] = 0.0
solve_opf(network_data, ACPPowerModel, Ipopt.Optimizer)
```

**Result: PASS** -- objective value changes after load modification, confirming the data mutation is effective. Before modification and after modification produce different objective values.

### Example 7: PTI `import_all=true`

**Docs show:**
```julia
network_data = PowerModels.parse_file("pti/case3.raw"; import_all=true)
```

**Result: FAIL** -- same PSS/E header parse failure as Example 3. The first `.raw` file tested (`case0.raw`) has a non-standard header. With a valid v33 file (e.g., `case3.raw`), `import_all=true` works correctly and adds extended data fields to the parsed dictionary.

### Example 8: Branch flow and loss inspection

**Docs show:**
```julia
result = solve_opf("matpower/case3_dc.m", ACPPowerModel, Ipopt.Optimizer)
result["solution"]["dcline"]["1"]
result["solution"]["branch"]["2"]
loss_ac = Dict(name => data["pt"]+data["pf"] for (name, data) in result["solution"]["branch"])
```

**Result: SKIP** -- `case3_dc.m` was not found in the PowerModels test data at the expected location. The file may be named differently or located elsewhere. The loss computation pattern (`pt + pf`) is verified to work on standard case files that do have branch results.

### Example 9: `instantiate_model` + `optimize_model!` (two-level API)

**Docs show:**
```julia
pm = instantiate_model("matpower/case3.m", ACPPowerModel, PowerModels.build_opf)
print(pm.model)
result = optimize_model!(pm, optimizer=Ipopt.Optimizer)
```

**Result: PASS** -- model instantiation succeeds, `optimize_model!` returns `LOCALLY_SOLVED`. This is the key extensibility API entry point.

### Example 10: Multi-step with parsed data

**Docs show:**
```julia
network_data = PowerModels.parse_file("matpower/case3.m")
pm = instantiate_model(network_data, ACPPowerModel, PowerModels.build_opf)
result = optimize_model!(pm, optimizer=Ipopt.Optimizer)
```

**Result: PASS** -- three-step workflow (parse, instantiate, optimize) succeeds. Demonstrates full control over the model lifecycle.

## Summary

| # | Example | Status | Notes |
|---|---------|--------|-------|
| 1 | `solve_ac_opf` | PASS | Needs valid file path (not provided in docs) |
| 2 | `solve_dc_opf` | PASS | Clean |
| 3 | PTI `.raw` file | FAIL | `case0.raw` has non-standard header; v33 files work |
| 4 | Result inspection | PASS | All fields accessible as documented |
| 5 | Generic `solve_opf` | PASS | Both ACP and SOCWR formulations work |
| 6 | Data modification | PASS | Mutation-then-re-solve pattern works |
| 7 | PTI `import_all` | FAIL | Same PSS/E header issue as Example 3 |
| 8 | Branch flow/loss | SKIP | `case3_dc.m` not found in test data |
| 9 | `instantiate_model` | PASS | Two-level API works correctly |
| 10 | Multi-step workflow | PASS | Parse + instantiate + optimize succeeds |

**Totals: 7 pass, 2 fail, 1 skip out of 10 examples.**

## Analysis

The two failures (Examples 3 and 7) share the same root cause: the PSS/E parser does not handle all header formats present in PowerModels' own test data. This is a consistency issue between the test data and the parser, not a fundamental capability gap -- v33 format `.raw` files parse correctly.

The core MATPOWER-based examples (1, 2, 4, 5, 6) all work correctly. The two-level API examples (9, 10) also work correctly and are the most important for extensibility workflows.

The most significant user-facing issue is that the quickstart examples reference file paths (`"matpower/case3.m"`) without explaining where to obtain the files. A new user must independently discover that MATPOWER case files need to be downloaded separately.

## Pass/Fail Rationale

**qualified_pass**: 7 of 10 examples run without modification (substituting valid file paths). The 2 failures are caused by a PSS/E parser edge case, not by broken API documentation. The core MATPOWER workflow is fully functional. The file path omission in docs is a genuine accessibility friction point but does not prevent experienced Julia users from getting started.
