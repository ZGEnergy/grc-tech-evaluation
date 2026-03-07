using PowerSystems, PowerFlows

sys = System("/workspace/data/networks/case39.m")
result = solve_powerflow(ACPowerFlow(), sys)
println("Type: ", typeof(result))

if isa(result, Dict)
    println("Keys: ", keys(result))
    for (k, v) in result
        println("  $k: ", typeof(v), " size=", size(v))
        println("  columns: ", names(v))
        println("  first 3 rows:")
        for i in 1:min(3, nrow(v))
            println("    ", [v[i, c] for c in names(v)])
        end
    end
elseif ismissing(result)
    println("Result is missing (ACPF did not converge with non-mutating version)")
    println()
    println("Trying mutating version solve_powerflow!...")
    converged = solve_powerflow!(ACPowerFlow(), sys)
    println("Converged: ", converged)
    if converged
        for bus in collect(get_components(ACBus, sys))[1:3]
            println("Bus $(get_name(bus)): Vm=$(get_magnitude(bus)), Va=$(get_angle(bus))")
        end
    end
else
    println("Result is: ", result)
end
