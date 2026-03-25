"""Gate tests for PyPSA: network ingestion at TINY, SMALL, and MEDIUM tiers.

Protocol v11 / Skill v2.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

# Reference counts: (buses, branches, generators)
REFERENCE = {
    "TINY": {
        "file": "case39.m",
        "buses": 39,
        "branches": 46,
        "generators": 10,
    },
    "SMALL": {
        "file": "case_ACTIVSg2000.m",
        "buses": 2000,
        "branches": 3206,
        "generators": 544,
    },
    "MEDIUM": {
        "file": "case_ACTIVSg10k.m",
        "buses": 10000,
        "branches": 12706,
        "generators": 2485,
    },
}


def _load_network(data_dir: Path, tier: str):
    """Load a MATPOWER case file into a PyPSA Network and return (network, load_time)."""
    import pypsa
    from matpowercaseframes import CaseFrames

    ref = REFERENCE[tier]
    case_path = data_dir / ref["file"]
    assert case_path.exists(), f"Network file not found: {case_path}"

    cf = CaseFrames(str(case_path))

    # Build pypower ppc dict
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    t0 = time.perf_counter()
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    load_time = time.perf_counter() - t0

    return net, load_time, cf


def _count_branches(net) -> int:
    """Total branch count = lines + transformers."""
    return len(net.lines) + len(net.transformers)


class TestGateG1:
    """G-1: Ingest TINY network (IEEE 39-bus)."""

    def test_g1_bus_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "TINY")
        expected = REFERENCE["TINY"]["buses"]
        assert len(net.buses) == expected, f"Expected {expected} buses, got {len(net.buses)}"

    def test_g1_branch_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "TINY")
        expected = REFERENCE["TINY"]["branches"]
        actual = _count_branches(net)
        assert actual == expected, f"Expected {expected} branches, got {actual}"

    def test_g1_generator_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "TINY")
        expected = REFERENCE["TINY"]["generators"]
        assert len(net.generators) == expected, (
            f"Expected {expected} generators, got {len(net.generators)}"
        )

    def test_g1_data_quality(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "TINY")

        # No NaN/inf in bus voltages
        assert not net.buses.v_nom.isna().any(), "NaN in bus v_nom"
        assert np.isfinite(net.buses.v_nom).all(), "Inf in bus v_nom"

        # Branch flow limits present (s_nom)
        if len(net.lines) > 0:
            assert not net.lines.s_nom.isna().any(), "NaN in line s_nom"

        # Generator limits
        assert not net.generators.p_nom.isna().any(), "NaN in generator p_nom"
        assert np.isfinite(net.generators.p_nom).all(), "Inf in generator p_nom"

        # Slack bus
        slack_buses = net.buses[net.buses.control == "Slack"]
        assert len(slack_buses) > 0, "No slack bus identified"


class TestGateG2:
    """G-2: Ingest SMALL network (ACTIVSg 2k)."""

    def test_g2_bus_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "SMALL")
        expected = REFERENCE["SMALL"]["buses"]
        assert len(net.buses) == expected, f"Expected {expected} buses, got {len(net.buses)}"

    def test_g2_branch_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "SMALL")
        expected = REFERENCE["SMALL"]["branches"]
        actual = _count_branches(net)
        assert actual == expected, f"Expected {expected} branches, got {actual}"

    def test_g2_generator_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "SMALL")
        expected = REFERENCE["SMALL"]["generators"]
        assert len(net.generators) == expected, (
            f"Expected {expected} generators, got {len(net.generators)}"
        )

    def test_g2_data_quality(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "SMALL")

        assert not net.buses.v_nom.isna().any(), "NaN in bus v_nom"
        assert np.isfinite(net.buses.v_nom).all(), "Inf in bus v_nom"

        if len(net.lines) > 0:
            assert not net.lines.s_nom.isna().any(), "NaN in line s_nom"

        assert not net.generators.p_nom.isna().any(), "NaN in generator p_nom"
        assert np.isfinite(net.generators.p_nom).all(), "Inf in generator p_nom"

        slack_buses = net.buses[net.buses.control == "Slack"]
        assert len(slack_buses) > 0, "No slack bus identified"


class TestGateG3:
    """G-3: Ingest MEDIUM network (ACTIVSg 10k)."""

    def test_g3_bus_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "MEDIUM")
        expected = REFERENCE["MEDIUM"]["buses"]
        assert len(net.buses) == expected, f"Expected {expected} buses, got {len(net.buses)}"

    def test_g3_branch_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "MEDIUM")
        expected = REFERENCE["MEDIUM"]["branches"]
        actual = _count_branches(net)
        assert actual == expected, f"Expected {expected} branches, got {actual}"

    def test_g3_generator_count(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "MEDIUM")
        expected = REFERENCE["MEDIUM"]["generators"]
        assert len(net.generators) == expected, (
            f"Expected {expected} generators, got {len(net.generators)}"
        )

    def test_g3_data_quality(self, data_dir: Path) -> None:
        net, _, _ = _load_network(data_dir, "MEDIUM")

        assert not net.buses.v_nom.isna().any(), "NaN in bus v_nom"
        assert np.isfinite(net.buses.v_nom).all(), "Inf in bus v_nom"

        if len(net.lines) > 0:
            assert not net.lines.s_nom.isna().any(), "NaN in line s_nom"

        assert not net.generators.p_nom.isna().any(), "NaN in generator p_nom"
        assert np.isfinite(net.generators.p_nom).all(), "Inf in generator p_nom"

        slack_buses = net.buses[net.buses.control == "Slack"]
        assert len(slack_buses) > 0, "No slack bus identified"
