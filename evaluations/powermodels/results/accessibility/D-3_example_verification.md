---
test_id: D-3
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "e9f1c2db"
---

# D-3: Example Verification

## Scope

Verify that getting-started examples from official documentation at
`https://lanl-ansi.github.io/PowerModels.jl/stable/` run correctly on PowerModels.jl v0.21.5.

## Examples Tested

### Example 1: solve_ac_opf from Quickstart

The official quickstart example shows:

```julia

using PowerModels
using Ipopt

result = solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)

```

**Status: Would not run as-written** — the path `"matpower/case3.m"` is a relative path that does not exist in the evaluation environment. The example assumes a MATPOWER case file in a local `matpower/` subdirectory without documenting where to get it. A new user must know to download case files separately or substitute their own path.

Functionally, substituting a valid case file path works correctly. The API call itself is valid.

### Example 2: solve_dc_opf from Quickstart

The quickstart shows `solve_dc_opf` with LMPs:

```julia

result = solve_dc_opf("case39.m", optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false))
println(result["termination_status"])
println(result["objective"])

```

**Verified: Runs correctly** on PowerModels.jl v0.21.5 with the case39.m file at
`../../data/networks/case39.m`.

Output:

```

OPTIMAL
41263.940785...

```

### Example 3: API Signature Discoverability

During D-1 testing, the most common variant seen in documentation examples is:

```julia

solve_dc_opf(data, DCPPowerModel, optimizer_with_attributes(...))

```

This 3-argument form does **not** work on v0.21.5. The error is:

```

ERROR: MethodError: no method matching solve_dc_opf(::Dict{String, Any},
::Type{DCPPowerModel}, ::MathOptInterface.OptimizerWithAttributes)

Closest candidates are:
  solve_dc_opf(::Any, ::Any; kwargs...)

```

The correct 2-argument form works:

```julia

solve_dc_opf(data, optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false))

```

The `solve_opf` generic function takes 3 arguments: `(data, FormulationType, optimizer)`.
`solve_dc_opf` and `solve_ac_opf` are 2-argument shortcuts that hardcode the formulation.

### Example 4: LMP Extraction

From the docs section on solution output:

```julia

result = solve_dc_opf(data, optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false);
    setting=Dict("output" => Dict("duals" => true)))
lmp = -result["solution"]["bus"]["1"]["lam_kcl_r"] / data["baseMVA"]

```

**Verified: Runs correctly**. LMPs are available as documented after enabling duals.

### Example 5: parse_file

```julia

data = parse_file("../../data/networks/case39.m")
println(data["baseMVA"])  # 100.0
println(length(data["bus"]))  # 39

```

**Verified: Runs correctly**. Parser warnings about angmin/angmax values on case39.m (±360 deg tightened to ±60 deg) are expected and documented behavior.

## Summary

| Example | Status | Notes |
|---------|--------|-------|
| solve_ac_opf quickstart | Would not run as-written | Relative path to case file not provided |
| solve_dc_opf basic | Verified OK | Correct 2-arg form |
| 3-arg API form | Fails with MethodError | Incorrect — common but wrong |
| LMP extraction | Verified OK | setting kwarg required |
| parse_file | Verified OK | Warnings expected |

## Pass/Fail Rationale

**qualified_pass**: The core examples work once the user substitutes a valid file path and uses the correct 2-argument API form. The path omission in the quickstart is a genuine friction point for new users. The 3-argument API form appearing in some documentation contexts (and in online examples) adds confusion but is not a docs-only issue — the correct form is documented.
