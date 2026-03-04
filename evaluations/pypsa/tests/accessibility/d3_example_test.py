"""D-3: Example verification — run pypsa.examples and quickstart code."""

from __future__ import annotations

import json
import traceback

results = {}

# --- Example 1: pypsa.examples.ac_dc_meshed() ---
print("=" * 60)
print("Example 1: pypsa.examples.ac_dc_meshed()")
print("=" * 60)
try:
    import pypsa

    n = pypsa.examples.ac_dc_meshed()
    print(f"Network loaded: {n.name}")
    print(f"Buses: {len(n.buses)}, Generators: {len(n.generators)}")
    # Try a basic solve
    n.lpf()
    print("LPF solved successfully")
    results["ac_dc_meshed"] = {"status": "pass", "error": None}
except Exception as e:
    tb = traceback.format_exc()
    print(f"FAILED: {e}")
    print(tb)
    results["ac_dc_meshed"] = {"status": "fail", "error": str(e)}

# --- Example 2: pypsa.examples.storage_hvdc() ---
print("\n" + "=" * 60)
print("Example 2: pypsa.examples.storage_hvdc()")
print("=" * 60)
try:
    n = pypsa.examples.storage_hvdc()
    print(f"Network loaded: {n.name}")
    print(f"Buses: {len(n.buses)}, Generators: {len(n.generators)}")
    n.lpf()
    print("LPF solved successfully")
    results["storage_hvdc"] = {"status": "pass", "error": None}
except Exception as e:
    tb = traceback.format_exc()
    print(f"FAILED: {e}")
    print(tb)
    results["storage_hvdc"] = {"status": "fail", "error": str(e)}

# --- Example 3: pypsa.examples.scigrid_de() ---
print("\n" + "=" * 60)
print("Example 3: pypsa.examples.scigrid_de()")
print("=" * 60)
try:
    n = pypsa.examples.scigrid_de()
    print(f"Network loaded: {n.name}")
    print(f"Buses: {len(n.buses)}, Generators: {len(n.generators)}")
    n.lpf()
    print("LPF solved successfully")
    results["scigrid_de"] = {"status": "pass", "error": None}
except Exception as e:
    tb = traceback.format_exc()
    print(f"FAILED: {e}")
    print(tb)
    results["scigrid_de"] = {"status": "fail", "error": str(e)}

# --- Example 4: Quickstart from docs (v0.33.2 style) ---
print("\n" + "=" * 60)
print("Example 4: Quickstart from docs — build network manually")
print("=" * 60)
try:
    network = pypsa.Network()
    n_buses = 3
    for i in range(n_buses):
        network.add("Bus", f"My bus {i}", v_nom=20.0)
    for i in range(n_buses):
        network.add(
            "Line",
            f"My line {i}",
            bus0=f"My bus {i}",
            bus1=f"My bus {(i + 1) % 3}",
            x=0.1,
            r=0.01,
        )
    network.add("Generator", "My gen", bus="My bus 0", p_set=100, control="PQ")
    network.add("Load", "My load", bus="My bus 1", p_set=100, q_set=100)
    print(f"Network built: {len(network.buses)} buses, {len(network.lines)} lines")
    network.pf()
    print("PF solved successfully")
    results["quickstart_manual"] = {"status": "pass", "error": None}
except Exception as e:
    tb = traceback.format_exc()
    print(f"FAILED: {e}")
    print(tb)
    results["quickstart_manual"] = {"status": "fail", "error": str(e)}

# --- Example 5: pypsa.examples.model_energy() ---
print("\n" + "=" * 60)
print("Example 5: pypsa.examples.model_energy()")
print("=" * 60)
try:
    n = pypsa.examples.model_energy()
    print(f"Network loaded: {n.name}")
    print(f"Buses: {len(n.buses)}, Generators: {len(n.generators)}")
    print(f"Snapshots: {len(n.snapshots)}")
    results["model_energy"] = {"status": "pass", "error": None}
except Exception as e:
    tb = traceback.format_exc()
    print(f"FAILED: {e}")
    print(tb)
    results["model_energy"] = {"status": "fail", "error": str(e)}

# --- Example 6: pypsa.examples.stochastic_network() ---
print("\n" + "=" * 60)
print("Example 6: pypsa.examples.stochastic_network()")
print("=" * 60)
try:
    n = pypsa.examples.stochastic_network()
    print(f"Network loaded: {n.name}")
    print(f"Buses: {len(n.buses)}, Generators: {len(n.generators)}")
    print(f"Snapshots: {len(n.snapshots)}")
    results["stochastic_network"] = {"status": "pass", "error": None}
except Exception as e:
    tb = traceback.format_exc()
    print(f"FAILED: {e}")
    print(tb)
    results["stochastic_network"] = {"status": "fail", "error": str(e)}

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(json.dumps(results, indent=2))
