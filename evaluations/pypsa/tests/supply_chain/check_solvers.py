"""Check available solvers for F-8."""

import sys

# Check linopy solvers
try:
    import linopy

    print(f"linopy version: {linopy.__version__}")
    print(f"Available solvers: {linopy.available_solvers}")
except Exception as e:
    print(f"linopy error: {e}")

# Test HiGHS
try:
    import highspy

    print(f"highspy version: {highspy.__version__}")
    print("HiGHS: AVAILABLE")
except Exception as e:
    print(f"HiGHS: NOT AVAILABLE ({e})")

# Test GLPK
try:
    import subprocess

    result = subprocess.run(["glpsol", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"GLPK: AVAILABLE ({result.stdout.splitlines()[0]})")
    else:
        print("GLPK: NOT AVAILABLE (glpsol not found)")
except Exception as e:
    print(f"GLPK: NOT AVAILABLE ({e})")

# Test SCIP
try:
    import pyscipopt

    print(f"SCIP: AVAILABLE (pyscipopt {pyscipopt.__version__})")
except ImportError:
    print("SCIP: NOT AVAILABLE (pyscipopt not installed)")

# Test Ipopt
try:
    import pyomo.environ as pyo

    solver = pyo.SolverFactory("ipopt")
    print(f"Ipopt via pyomo: available={solver.available()}")
except Exception as e:
    print(f"Ipopt: NOT AVAILABLE ({e})")

sys.stdout.flush()
