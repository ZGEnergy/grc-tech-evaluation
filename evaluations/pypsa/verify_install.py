"""Verify PyPSA installation by running DC power flow on IEEE 39-bus case."""

from __future__ import annotations

import sys
from pathlib import Path

import pandapower as pp
import pandapower.converter as pc
import pypsa

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "networks"

# Load case39.m via pandapower, then convert to PyPSA
net_pp = pp.converter.from_mpc(str(DATA_DIR / "case39.m"))
net = pc.to_pypsa(net_pp)

# Run DC power flow
net.lpf()

print(f"PyPSA version: {pypsa.__version__}")
print(f"Buses: {len(net.buses)}")
print(f"Lines: {len(net.lines)}")
print("DC power flow completed successfully")
sys.exit(0)
