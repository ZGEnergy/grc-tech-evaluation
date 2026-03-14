"""Gate tests for GridCal (VeraGridEngine): network ingestion and data quality checks.

Tests G-1 (TINY), G-2 (SMALL), G-3 (MEDIUM) per protocol v10.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

# Reference counts (verified from MATPOWER files and prior evaluations)
REFERENCE = {
    "TINY": {"file": "case39.m", "buses": 39, "branches": 46, "generators": 10},
    "SMALL": {"file": "case_ACTIVSg2000.m", "buses": 2000, "branches": 3206, "generators": 544},
    "MEDIUM": {"file": "case_ACTIVSg10k.m", "buses": 10000, "branches": 12706, "generators": 2485},
}


def _load_and_validate(data_dir: Path, tier: str) -> dict:
    """Load a MATPOWER file and return validation results."""
    import time

    import VeraGridEngine as vge

    ref = REFERENCE[tier]
    path = data_dir / ref["file"]
    assert path.exists(), f"Network file not found: {path}"

    t0 = time.perf_counter()
    grid = vge.open_file(str(path))
    load_time = time.perf_counter() - t0

    buses = grid.get_buses()
    branches = grid.get_branches()
    gens = grid.get_generators()

    branch_types = Counter(type(b).__name__ for b in branches)

    result = {
        "load_time": load_time,
        "bus_count": len(buses),
        "branch_count": len(branches),
        "gen_count": len(gens),
        "branch_types": dict(branch_types),
        "bus_vnom_nan": sum(1 for b in buses if np.isnan(b.Vnom)),
        "bus_vnom_inf": sum(1 for b in buses if np.isinf(b.Vnom)),
        "branch_rate_nan": sum(1 for b in branches if np.isnan(b.rate)),
        "branch_rate_inf": sum(1 for b in branches if np.isinf(b.rate)),
        "branch_rate_zero": sum(1 for b in branches if b.rate == 0),
        "branch_rate_positive": sum(1 for b in branches if b.rate > 0),
        "gen_pmax_nan": sum(1 for g in gens if np.isnan(g.Pmax)),
        "gen_pmax_inf": sum(1 for g in gens if np.isinf(g.Pmax)),
        "gen_cost_present": sum(1 for g in gens if g.Cost != 0 or g.Cost2 != 0),
        "slack_buses": [(b.name, b.code) for b in buses if b.is_slack],
    }

    return result


class TestGateG1:
    """G-1: Ingest TINY network (IEEE 39-bus)."""

    def test_bus_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "TINY")
        assert r["bus_count"] == 39

    def test_branch_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "TINY")
        assert r["branch_count"] == 46

    def test_generator_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "TINY")
        assert r["gen_count"] == 10

    def test_data_quality(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "TINY")
        assert r["bus_vnom_nan"] == 0
        assert r["bus_vnom_inf"] == 0
        assert r["branch_rate_nan"] == 0
        assert r["branch_rate_inf"] == 0
        assert r["gen_pmax_nan"] == 0
        assert r["gen_pmax_inf"] == 0
        assert r["branch_rate_positive"] == 46
        assert len(r["slack_buses"]) >= 1


class TestGateG2:
    """G-2: Ingest SMALL network (ACTIVSg 2k)."""

    def test_bus_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "SMALL")
        assert r["bus_count"] == 2000

    def test_branch_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "SMALL")
        assert r["branch_count"] == 3206

    def test_generator_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "SMALL")
        assert r["gen_count"] == 544

    def test_data_quality(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "SMALL")
        assert r["bus_vnom_nan"] == 0
        assert r["bus_vnom_inf"] == 0
        assert r["branch_rate_nan"] == 0
        assert r["branch_rate_inf"] == 0
        assert r["gen_pmax_nan"] == 0
        assert r["gen_pmax_inf"] == 0
        assert r["branch_rate_positive"] == 3206
        assert len(r["slack_buses"]) >= 1


class TestGateG3:
    """G-3: Ingest MEDIUM network (ACTIVSg 10k)."""

    def test_bus_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "MEDIUM")
        assert r["bus_count"] == 10000

    def test_branch_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "MEDIUM")
        assert r["branch_count"] == 12706

    def test_generator_count(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "MEDIUM")
        assert r["gen_count"] == 2485

    def test_data_quality(self, data_dir: Path) -> None:
        r = _load_and_validate(data_dir, "MEDIUM")
        assert r["bus_vnom_nan"] == 0
        assert r["bus_vnom_inf"] == 0
        assert r["branch_rate_nan"] == 0
        assert r["branch_rate_inf"] == 0
        assert r["gen_pmax_nan"] == 0
        assert r["gen_pmax_inf"] == 0
        assert r["branch_rate_positive"] == 12706
        assert len(r["slack_buses"]) >= 1
