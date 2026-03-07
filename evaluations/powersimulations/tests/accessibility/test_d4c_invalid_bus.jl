#=
Test D-4c: Error quality — Invalid bus type

Dimension: accessibility
Network: TINY (case39.m — IEEE 39-bus)
Tool: PowerSimulations.jl v0.30.2

Tests whether the tool produces a meaningful diagnostic when a bus type
is set to an invalid value.
=#

using PowerSystems

println("=" ^ 60)
println("D-4c: Invalid bus type")
println("=" ^ 60)

# First, examine valid bus types
println("\n--- Valid ACBusTypes ---")
for bt in instances(ACBusTypes)
    println("  ", bt, " = ", Int(bt))
end

# Load system
sys = System("/workspace/data/networks/case39.m")

# Get a bus and try to set invalid type
target_bus = nothing
for bus in get_components(ACBus, sys)
    target_bus = bus
    break
end

if target_bus !== nothing
    println("\nTarget bus: ", get_name(target_bus))
    println("Original bustype: ", get_bustype(target_bus))

    # Test 1: Try setting bus type via the enum
    println("\n--- Test 1: Setting bus to ISOLATED type ---")
    try
        set_bustype!(target_bus, ACBusTypes.ISOLATED)
        println("Set bustype to ISOLATED: ", get_bustype(target_bus))
    catch e
        println("ERROR: ", typeof(e))
        println("  ", sprint(showerror, e))
    end

    # Test 2: Try creating a bus with an invalid integer type
    println("\n--- Test 2: Creating bus type from invalid integer ---")
    try
        invalid_type = ACBusTypes(999)
        println("Created invalid bus type: ", invalid_type)
    catch e
        println("ERROR: ", typeof(e))
        println("  ", sprint(showerror, e))
    end

    # Test 3: Try setting bus type to a string (wrong type entirely)
    println("\n--- Test 3: Passing wrong type to set_bustype! ---")
    try
        set_bustype!(target_bus, "INVALID")
        println("Set bustype to string: ", get_bustype(target_bus))
    catch e
        println("ERROR: ", typeof(e))
        println("  ", sprint(showerror, e))
    end

    # Test 4: Try a power flow with an ISOLATED bus
    println("\n--- Test 4: DCPF with ISOLATED bus ---")
    # Reload to get clean system
    sys2 = System("/workspace/data/networks/case39.m")

    # Set a generator bus to ISOLATED
    for bus in get_components(ACBus, sys2)
        if get_bustype(bus) == ACBusTypes.REF
            println("Setting REF bus '", get_name(bus), "' to ISOLATED")
            set_bustype!(bus, ACBusTypes.ISOLATED)
            break
        end
    end

    try
        using PowerFlows, PowerNetworkMatrices
        result = solve_powerflow(DCPowerFlow(), sys2)
        println("DCPF result type: ", typeof(result))
        println("DCPF completed (unexpected with ISOLATED ref bus)")
    catch e
        println("ERROR: ", typeof(e))
        println("  ", sprint(showerror, e))
        println("\nFull traceback:")
        println(sprint(showerror, e, catch_backtrace()))
    end
end

println("\n--- END D-4c ---")
