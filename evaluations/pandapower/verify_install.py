"""Verify pandapower installation by running DC power flow on IEEE 39-bus case."""

from __future__ import annotations

import sys
from pathlib import Path

import pandapower as pp

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "networks"

# Load case39.m directly
net = pp.converter.from_mpc(str(DATA_DIR / "case39.m"))

# Run DC power flow
pp.rundcpp(net)

print(f"pandapower version: {pp.__version__}")
print(f"Buses: {len(net.bus)}")
print(f"Lines: {len(net.line)}")
print(f"Converged: {net.converged}")
sys.exit(0 if net.converged else 1)
