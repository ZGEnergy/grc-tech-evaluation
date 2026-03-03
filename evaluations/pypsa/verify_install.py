"""Verify PyPSA installation by running DC power flow on IEEE 39-bus case."""

from __future__ import annotations

import sys
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "networks"

# Load case39.m via matpowercaseframes → pypower ppc dict
cf = CaseFrames(str(DATA_DIR / "case39.m"))
ppc = {
    "version": "2",
    "baseMVA": cf.baseMVA,
    "bus": cf.bus.values,
    "gen": cf.gen.values,
    "branch": cf.branch.values,
}

# Import into PyPSA and run DC power flow
net = pypsa.Network()
net.import_from_pypower_ppc(ppc)
net.lpf()

print(f"PyPSA version: {pypsa.__version__}")
print(f"Buses: {len(net.buses)}")
print(f"Lines: {len(net.lines)}")
print("DC power flow completed successfully")
sys.exit(0)
