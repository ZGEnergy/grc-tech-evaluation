"""Verify GridCal (VeraGrid) installation by running DC power flow on IEEE 39-bus case."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

import VeraGridEngine as vge
from VeraGridEngine.enumerations import SolverType

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "networks"

# Load case39.m
grid = vge.open_file(str(DATA_DIR / "case39.m"))

# Run DC power flow (Linear solver = DC approximation)
opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
results = vge.power_flow(grid, options=opts)

version = importlib.metadata.version("veragridengine")
print(f"VeraGridEngine version: {version}")
print(f"Buses: {grid.get_bus_number()}")
print(f"Branches: {grid.get_branch_number()}")
print(f"Converged: {bool(results.converged)}")
sys.exit(0 if results.converged else 1)
