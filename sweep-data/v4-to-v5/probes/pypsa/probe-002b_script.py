"""Probe 002b: Functional test of PyPSA stochastic optimization.

Try to actually use set_scenarios + optimize to see if it works end-to-end.
"""

import pypsa
import pandas as pd

print(f"PyPSA version: {pypsa.__version__}")

# Build a minimal 2-bus network
n = pypsa.Network()
n.set_snapshots(range(3))

n.add("Bus", "bus0")
n.add("Bus", "bus1")
n.add("Line", "line", bus0="bus0", bus1="bus1", s_nom=100, x=0.1)
n.add("Generator", "gen_cheap", bus="bus0", p_nom=100, marginal_cost=10)
n.add("Generator", "gen_expensive", bus="bus1", p_nom=100, marginal_cost=50)
n.add("Load", "load", bus="bus1", p_set=50)

# Set up scenarios
print("\n=== SETTING UP SCENARIOS ===")
try:
    n.set_scenarios(low=0.5, high=0.5)
    print(f"Scenarios set: {n.scenarios}")
    print(f"Scenario weightings: {n.scenario_weightings}")
    print(f"has_scenarios: {n.has_scenarios}")
except Exception as e:
    print(f"set_scenarios failed: {type(e).__name__}: {e}")

# Try to set different load profiles per scenario
print("\n=== SETTING SCENARIO-SPECIFIC DATA ===")
try:
    # Check if we can set scenario-indexed data
    print(
        f"loads_t.p_set shape before: {n.loads_t.p_set.shape if not n.loads_t.p_set.empty else 'empty'}"
    )

    # Try setting scenario-indexed load
    if n.has_scenarios:
        # Create scenario-indexed load data
        idx = pd.MultiIndex.from_product(
            [range(3), n.scenarios], names=["snapshot", "scenario"]
        )
        load_data = pd.DataFrame({"load": [40, 60, 45, 55, 50, 50]}, index=idx)
        print(f"Created scenario-indexed load data with shape {load_data.shape}")

        # Try assigning via different methods
        try:
            n.loads_t.p_set = load_data
            print("Direct assignment succeeded")
        except Exception as e:
            print(f"Direct assignment failed: {e}")

        # Check the loads_t structure
        print(f"loads_t.p_set: {n.loads_t.p_set}")
except Exception as e:
    print(f"Scenario data setup failed: {type(e).__name__}: {e}")

# Try to optimize with scenarios
print("\n=== RUNNING OPTIMIZE WITH SCENARIOS ===")
try:
    status, condition = n.optimize(solver_name="highs")
    print(f"Status: {status}, Condition: {condition}")
    print(f"Objective: {n.objective}")
    print(f"Generator dispatch:\n{n.generators_t.p}")
    print(f"Bus marginal prices:\n{n.buses_t.marginal_price}")
except Exception as e:
    print(f"Optimize failed: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

# Try the risk preference
print("\n=== RISK PREFERENCE ===")
try:
    n2 = pypsa.Network()
    n2.set_snapshots(range(3))
    n2.add("Bus", "bus0")
    n2.add("Generator", "gen", bus="bus0", p_nom=100, marginal_cost=10)
    n2.add("Load", "load", bus="bus0", p_set=50)

    n2.set_scenarios(low=0.5, high=0.5)
    n2.set_risk_preference(alpha=0.5, omega=0.5)
    print(f"Risk preference set: {n2.risk_preference}")
    print(f"has_risk_preference: {n2.has_risk_preference}")

    status, condition = n2.optimize(solver_name="highs")
    print(f"Status: {status}, Condition: {condition}")
    print(f"Objective: {n2.objective}")
except Exception as e:
    print(f"Risk preference test failed: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

# Check documentation references
print("\n=== DOCSTRING CHECK ===")
print(f"set_scenarios docstring:\n{n.set_scenarios.__doc__}")
print(f"\nset_risk_preference docstring:\n{n.set_risk_preference.__doc__}")
