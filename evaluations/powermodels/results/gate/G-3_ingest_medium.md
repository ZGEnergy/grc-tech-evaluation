---
test_id: G-3
tool: powermodels
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-11T21:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "2da513c6"
---

# G-3: Ingest ACTIVSg 10k reference network

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** ~10000 buses / verify branches / verify generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 1.2s
- **Data quality notes:** 2462 of 12706 branches (19.4%) have non-finite (Inf) rate_a values, indicating unconstrained thermal limits. These are present in the raw .m file; they are not introduced by PowerModels. The eval-config notes that the MEDIUM dataset requires a zero-RATE_A fix and congestion induction as preprocessing — those preprocessing steps have not yet been applied to the file used here. All bus voltage bounds are finite, a slack bus (bus_type=3) is present, all generator cost and limit data is finite, and zero-reactance branches were not detected. The network loaded without error, so the gate test passes; the non-finite rate_a values are recorded as a data quality warning for downstream OPF tests.
- **Errors/warnings:** 2462 branches with non-finite rate_a (Inf) in raw case_ACTIVSg10k.m

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

r3 = run_gate_test("G-3", "MEDIUM (ACTIVSg 10k)",
    "/workspace/data/networks/case_ACTIVSg10k.m", nothing, nothing, nothing)

```
