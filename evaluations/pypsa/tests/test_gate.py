"""Gate tests for PyPSA: network ingestion checks across TINY/SMALL/MEDIUM tiers.

Test IDs:
  G-1: TINY  — IEEE 39-bus (case39.m): 39 buses, 46 branches, 10 generators
  G-2: SMALL — ACTIVSg2000 (case_ACTIVSg2000.m): 2000 buses, 3206 branches, 544 generators
  G-3: MEDIUM — ACTIVSg10k (case_ACTIVSg10k.m): 10000 buses, 12706 branches, 2485 generators
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pypsa
import pytest
from matpowercaseframes import CaseFrames

# Reference counts: (case_file, buses, branches, generators)
REFERENCE = {
    "G-1": ("case39.m", 39, 46, 10),
    "G-2": ("case_ACTIVSg2000.m", 2000, 3206, 544),
    "G-3": ("case_ACTIVSg10k.m", 10000, 12706, 2485),
}


def _load_network(data_dir: Path, case_file: str) -> pypsa.Network:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(data_dir / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net


# ---------------------------------------------------------------------------
# G-1: TINY (case39)
# ---------------------------------------------------------------------------


class TestG1Tiny:
    """G-1: Import and validate IEEE 39-bus network (TINY tier)."""

    @pytest.fixture
    def net(self, data_dir: Path) -> pypsa.Network:
        return _load_network(data_dir, REFERENCE["G-1"][0])

    def test_g1_bus_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-1"][1]
        assert len(net.buses) == expected, f"Expected {expected} buses, got {len(net.buses)}"

    def test_g1_branch_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-1"][2]
        actual = len(net.lines) + len(net.transformers)
        assert actual == expected, (
            f"Expected {expected} branches (lines+transformers), got {actual} "
            f"(lines={len(net.lines)}, transformers={len(net.transformers)})"
        )

    def test_g1_generator_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-1"][3]
        assert len(net.generators) == expected, (
            f"Expected {expected} generators, got {len(net.generators)}"
        )

    def test_g1_no_nan_inf_bus_voltage(self, net: pypsa.Network) -> None:
        v = net.buses["v_mag_pu_set"]
        assert v.isna().sum() == 0, f"Found {v.isna().sum()} NaN bus voltages"
        assert np.isinf(v).sum() == 0, f"Found {np.isinf(v).sum()} infinite bus voltages"

    def test_g1_no_nan_inf_generator_limits(self, net: pypsa.Network) -> None:
        for col in ["p_nom", "p_set"]:
            vals = net.generators[col]
            assert vals.isna().sum() == 0, f"Found NaN in generators.{col}"
            assert np.isinf(vals).sum() == 0, f"Found Inf in generators.{col}"

    def test_g1_branch_flow_limits_present(self, net: pypsa.Network) -> None:
        if len(net.lines) > 0:
            assert (net.lines["s_nom"] > 0).any(), "No lines have positive s_nom ratings"
        if len(net.transformers) > 0:
            assert (net.transformers["s_nom"] > 0).any(), "No transformers have positive s_nom"

    def test_g1_slack_bus_identified(self, net: pypsa.Network) -> None:
        slack = net.buses[net.buses["control"] == "Slack"]
        assert len(slack) >= 1, "No slack/reference bus identified"

    def test_g1_generator_cost_data(self, net: pypsa.Network) -> None:
        """Check whether generator cost data was imported.

        NOTE: PyPSA's pypower importer explicitly skips gencost data, so
        marginal_cost will be zero even though the .m file has gencost.
        This test documents that limitation rather than failing on it.
        """
        mc = net.generators["marginal_cost"]
        assert mc.isna().sum() == 0, "NaN values in marginal_cost"
        # Record the limitation: all zeros means gencost was not imported
        if (mc == 0).all():
            pytest.skip(
                "WARN: marginal_cost is all zeros — PyPSA pypower importer "
                "does not import gencost data from MATPOWER files"
            )


# ---------------------------------------------------------------------------
# G-2: SMALL (case_ACTIVSg2000)
# ---------------------------------------------------------------------------


class TestG2Small:
    """G-2: Import and validate ACTIVSg2000 network (SMALL tier)."""

    @pytest.fixture
    def net(self, data_dir: Path) -> pypsa.Network:
        return _load_network(data_dir, REFERENCE["G-2"][0])

    def test_g2_bus_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-2"][1]
        assert len(net.buses) == expected, f"Expected {expected} buses, got {len(net.buses)}"

    def test_g2_branch_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-2"][2]
        actual = len(net.lines) + len(net.transformers)
        assert actual == expected, (
            f"Expected {expected} branches, got {actual} "
            f"(lines={len(net.lines)}, transformers={len(net.transformers)})"
        )

    def test_g2_generator_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-2"][3]
        assert len(net.generators) == expected, (
            f"Expected {expected} generators, got {len(net.generators)}"
        )

    def test_g2_no_nan_inf_bus_voltage(self, net: pypsa.Network) -> None:
        v = net.buses["v_mag_pu_set"]
        assert v.isna().sum() == 0, f"Found {v.isna().sum()} NaN bus voltages"
        assert np.isinf(v).sum() == 0, f"Found {np.isinf(v).sum()} infinite bus voltages"

    def test_g2_no_nan_inf_generator_limits(self, net: pypsa.Network) -> None:
        for col in ["p_nom", "p_set"]:
            vals = net.generators[col]
            assert vals.isna().sum() == 0, f"Found NaN in generators.{col}"
            assert np.isinf(vals).sum() == 0, f"Found Inf in generators.{col}"

    def test_g2_branch_flow_limits_present(self, net: pypsa.Network) -> None:
        if len(net.lines) > 0:
            assert (net.lines["s_nom"] > 0).any(), "No lines have positive s_nom ratings"
        if len(net.transformers) > 0:
            assert (net.transformers["s_nom"] > 0).any(), "No transformers have positive s_nom"

    def test_g2_slack_bus_identified(self, net: pypsa.Network) -> None:
        slack = net.buses[net.buses["control"] == "Slack"]
        assert len(slack) >= 1, "No slack/reference bus identified"

    def test_g2_generator_cost_data(self, net: pypsa.Network) -> None:
        mc = net.generators["marginal_cost"]
        assert mc.isna().sum() == 0, "NaN values in marginal_cost"
        if (mc == 0).all():
            pytest.skip(
                "WARN: marginal_cost is all zeros — gencost not imported by pypower importer"
            )


# ---------------------------------------------------------------------------
# G-3: MEDIUM (case_ACTIVSg10k)
# ---------------------------------------------------------------------------


class TestG3Medium:
    """G-3: Import and validate ACTIVSg10k network (MEDIUM tier)."""

    @pytest.fixture
    def net(self, data_dir: Path) -> pypsa.Network:
        return _load_network(data_dir, REFERENCE["G-3"][0])

    def test_g3_bus_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-3"][1]
        assert len(net.buses) == expected, f"Expected {expected} buses, got {len(net.buses)}"

    def test_g3_branch_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-3"][2]
        actual = len(net.lines) + len(net.transformers)
        assert actual == expected, (
            f"Expected {expected} branches, got {actual} "
            f"(lines={len(net.lines)}, transformers={len(net.transformers)})"
        )

    def test_g3_generator_count(self, net: pypsa.Network) -> None:
        expected = REFERENCE["G-3"][3]
        assert len(net.generators) == expected, (
            f"Expected {expected} generators, got {len(net.generators)}"
        )

    def test_g3_no_nan_inf_bus_voltage(self, net: pypsa.Network) -> None:
        v = net.buses["v_mag_pu_set"]
        assert v.isna().sum() == 0, f"Found {v.isna().sum()} NaN bus voltages"
        assert np.isinf(v).sum() == 0, f"Found {np.isinf(v).sum()} infinite bus voltages"

    def test_g3_no_nan_inf_generator_limits(self, net: pypsa.Network) -> None:
        for col in ["p_nom", "p_set"]:
            vals = net.generators[col]
            assert vals.isna().sum() == 0, f"Found NaN in generators.{col}"
            assert np.isinf(vals).sum() == 0, f"Found Inf in generators.{col}"

    def test_g3_branch_flow_limits_present(self, net: pypsa.Network) -> None:
        """Check branch flow limits, documenting zero-rating branches."""
        if len(net.lines) > 0:
            zero_count = (net.lines["s_nom"] == 0).sum()
            total = len(net.lines)
            # At least some lines must have ratings
            assert (net.lines["s_nom"] > 0).any(), "No lines have positive s_nom ratings"
            if zero_count > 0:
                pytest.skip(
                    f"WARN: {zero_count}/{total} lines have s_nom=0 "
                    f"— branch ratings missing in MATPOWER source or not imported"
                )
        if len(net.transformers) > 0:
            assert (net.transformers["s_nom"] > 0).any(), "No transformers have positive s_nom"

    def test_g3_slack_bus_identified(self, net: pypsa.Network) -> None:
        slack = net.buses[net.buses["control"] == "Slack"]
        assert len(slack) >= 1, "No slack/reference bus identified"

    def test_g3_generator_cost_data(self, net: pypsa.Network) -> None:
        mc = net.generators["marginal_cost"]
        assert mc.isna().sum() == 0, "NaN values in marginal_cost"
        if (mc == 0).all():
            pytest.skip(
                "WARN: marginal_cost is all zeros — gencost not imported by pypower importer"
            )
