# ruff: noqa: E402
"""Probe 002: Verify PyPSA stochastic optimization capabilities.

The D-2 documentation audit claims PyPSA has a dedicated stochastic optimization
page and example notebook. The A-8 test says the feature doesn't actually work.
This probe checks what stochastic capabilities actually exist in the installed version.
"""

import pypsa
import inspect

print(f"PyPSA version: {pypsa.__version__}")

# 1. Check n.scenarios attribute
print("\n=== SCENARIOS ATTRIBUTE ===")
n = pypsa.Network()
if hasattr(n, "scenarios"):
    print(f"n.scenarios exists: {n.scenarios}")
    print(f"n.scenarios type: {type(n.scenarios)}")
else:
    print("n.scenarios does NOT exist")

# 2. Check for set_scenarios method
print("\n=== SET_SCENARIOS METHOD ===")
if hasattr(n, "set_scenarios"):
    print("n.set_scenarios exists")
    print(f"  signature: {inspect.signature(n.set_scenarios)}")
    print(f"  docstring: {n.set_scenarios.__doc__}")
else:
    print("n.set_scenarios does NOT exist")

# 3. Check for set_risk_preference method
print("\n=== SET_RISK_PREFERENCE METHOD ===")
if hasattr(n, "set_risk_preference"):
    print("n.set_risk_preference exists")
    print(f"  signature: {inspect.signature(n.set_risk_preference)}")
else:
    print("n.set_risk_preference does NOT exist")

# 4. Check n.optimize() parameters
print("\n=== OPTIMIZE METHOD PARAMETERS ===")
sig = inspect.signature(n.optimize)
print(f"n.optimize signature: {sig}")
for param_name, param in sig.parameters.items():
    print(f"  {param_name}: default={param.default}")

# 5. Check optimize sub-methods
print("\n=== OPTIMIZE SUB-METHODS ===")
for attr in dir(n.optimize):
    if not attr.startswith("_"):
        obj = getattr(n.optimize, attr)
        if callable(obj):
            try:
                s = inspect.signature(obj)
                print(f"  n.optimize.{attr}{s}")
            except (ValueError, TypeError):
                print(f"  n.optimize.{attr}() [signature unavailable]")

# 6. Check for stochastic-related modules
print("\n=== STOCHASTIC MODULES ===")
import pypsa.optimization as opt

for attr in dir(opt):
    if "stoch" in attr.lower() or "scenario" in attr.lower() or "risk" in attr.lower():
        print(f"  pypsa.optimization.{attr}")

# Check in main pypsa namespace
for attr in dir(pypsa):
    if "stoch" in attr.lower() or "scenario" in attr.lower():
        print(f"  pypsa.{attr}")

# 7. Check Network class for scenario-related attributes
print("\n=== NETWORK SCENARIO ATTRIBUTES ===")
for attr in dir(n):
    if "scenario" in attr.lower() or "stoch" in attr.lower() or "risk" in attr.lower():
        obj = getattr(n, attr)
        print(f"  n.{attr} = {obj} (type: {type(obj).__name__})")

# 8. Check if there's a scenario dimension in the component data
print("\n=== COMPONENT DIMENSIONS ===")
try:
    # Check if generators_t or buses_t have scenario dimensions
    print(f"  generators_t columns type: {type(n.generators_t)}")
    for comp_name in ["generators_t", "loads_t", "buses_t"]:
        comp = getattr(n, comp_name)
        for attr_name in dir(comp):
            if not attr_name.startswith("_"):
                obj = getattr(comp, attr_name)
                if hasattr(obj, "dims"):
                    print(f"  {comp_name}.{attr_name}.dims = {obj.dims}")
except Exception as e:
    print(f"  Error checking dimensions: {e}")

# 9. Check installed package files for stochastic content
print("\n=== PYPSA PACKAGE FILES ===")
import importlib.util

spec = importlib.util.find_spec("pypsa")
if spec and spec.submodule_search_locations:
    import os

    pypsa_path = spec.submodule_search_locations[0]
    print(f"PyPSA installed at: {pypsa_path}")
    for root, dirs, files in os.walk(pypsa_path):
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                rel = os.path.relpath(fpath, pypsa_path)
                if "stoch" in rel.lower() or "scenario" in rel.lower():
                    print(f"  Found file: {rel}")

# Also grep for 'stochastic' or 'scenario' in key files
print("\n=== STOCHASTIC REFERENCES IN PYPSA SOURCE ===")
import os

pypsa_path = spec.submodule_search_locations[0]
count = 0
for root, dirs, files in os.walk(pypsa_path):
    for f in files:
        if f.endswith(".py"):
            fpath = os.path.join(root, f)
            try:
                with open(fpath) as fh:
                    content = fh.read()
                    if "stochastic" in content.lower() or "scenario" in content.lower():
                        rel = os.path.relpath(fpath, pypsa_path)
                        # Count occurrences
                        s_count = content.lower().count(
                            "stochastic"
                        ) + content.lower().count("scenario")
                        print(f"  {rel}: {s_count} mentions")
                        count += 1
            except Exception:
                pass
if count == 0:
    print("  No references found")

print("\n=== SUMMARY ===")
print("Checking if PyPSA has native stochastic optimization support:")
has_set_scenarios = hasattr(n, "set_scenarios")
has_scenarios = hasattr(n, "scenarios")
has_risk = hasattr(n, "set_risk_preference")
print(f"  n.set_scenarios: {has_set_scenarios}")
print(f"  n.scenarios attribute: {has_scenarios}")
print(f"  n.set_risk_preference: {has_risk}")
print(f"  'scenarios' in optimize params: {'scenarios' in sig.parameters}")
