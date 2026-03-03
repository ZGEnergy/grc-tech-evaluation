"""Verify GridCal installation by running DC power flow on IEEE 39-bus case."""

from __future__ import annotations

import sys
from pathlib import Path

import GridCalEngine as gce

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "networks"

# Load case39.m
grid = gce.open_file(str(DATA_DIR / "case39.m"))

# Run DC power flow
results = gce.power_flow(grid, engine=gce.EngineType.DC)

print(f"GridCalEngine version: {gce.__version__}")
print(f"Buses: {grid.get_bus_number()}")
print(f"Branches: {grid.get_branch_number()}")
print(f"Converged: {results.converged}")
sys.exit(0 if results.converged else 1)
