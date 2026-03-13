---
test_id: G-1
tool: powermodels
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-11T21:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "0a74adbf"
---

# G-1: Ingest IEEE 39-bus reference network

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.33s
- **Data quality notes:** No issues. All bus voltage bounds finite, slack bus present (bus_type=3), all branch rate_a finite, all generator cost and limit data present.
- **Errors/warnings:** None

## Test Script

```julia

#!/usr/bin/env julia
# test_gate.jl — Gate tests G-1, G-2, G-3 for PowerModels

using PowerModels
using Dates

PowerModels.silence()

function audit_network(data::Dict)
    issues = String[]

    for (id, bus) in data["bus"]
        if !isfinite(get(bus, "vmin", NaN)) || !isfinite(get(bus, "vmax", NaN))
            push!(issues, "Bus $id has non-finite voltage bounds")
        end
    end

    has_slack = any(bus["bus_type"] == 3 for (_, bus) in data["bus"])
    if !has_slack
        push!(issues, "No slack/reference bus (bus_type=3) found")
    end

    zero_rate_a = 0
    for (id, br) in data["branch"]
        ra = get(br, "rate_a", NaN)
        if !isfinite(ra)
            push!(issues, "Branch $id has non-finite rate_a")
        end
        if isfinite(ra) && ra == 0.0
            zero_rate_a += 1
        end
    end
    if zero_rate_a > 0
        push!(issues, "$(zero_rate_a) branches have rate_a = 0 (unconstrained flow limit)")
    end

    zero_x = 0
    for (id, br) in data["branch"]
        xval = get(br, "br_x", NaN)
        if isfinite(xval) && xval == 0.0
            zero_x += 1
        end
    end
    if zero_x > 0
        push!(issues, "$(zero_x) branches have br_x = 0 (may cause singularity in AC)")
    end

    gen_no_cost = 0
    for (id, gen) in data["gen"]
        if !haskey(data, "gencost") && !haskey(gen, "cost")
            gen_no_cost += 1
        end
    end
    if gen_no_cost > 0
        push!(issues, "$(gen_no_cost) generators missing cost data")
    end

    for (id, gen) in data["gen"]
        for field in ["pmin", "pmax", "qmin", "qmax"]
            val = get(gen, field, NaN)
            if !isfinite(val)
                push!(issues, "Gen $id has non-finite $field")
            end
        end
    end

    return issues
end

r1 = run_gate_test("G-1", "TINY (IEEE 39-bus)",
    "/workspace/data/networks/case39.m", 39, 46, 10)

```
