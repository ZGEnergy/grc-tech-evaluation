"""Tests for Phase 3 DR Resource Placement & Parameter Definition.

All tests are self-contained with no external file dependencies or network calls.
Mock MATPOWER .m files are generated inline for load_bus_data tests.
"""

from __future__ import annotations

import csv
import io
import textwrap
from pathlib import Path

import numpy as np
import pytest

from scripts.phase3_dr_placement import (
    BusCandidate,
    DrBus,
    DrNetworkId,
    DrPlacementConfig,
    assign_dr_parameters,
    load_bus_data,
    select_dr_buses,
    validate_dr_placement,
    write_dr_buses_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_SEED = 42


def _make_rng(seed: int = _DEFAULT_SEED) -> np.random.Generator:
    return np.random.default_rng(seed)


def _make_config(**overrides: object) -> DrPlacementConfig:
    """Create a DrPlacementConfig with sensible test defaults."""
    defaults: dict[str, object] = {
        "min_buses": 3,
        "max_buses": 8,
        "max_buses_per_area": 3,
        "curtail_fraction_min": 0.10,
        "curtail_fraction_max": 0.15,
        "recovery_ratio": 0.75,
        "curtail_ramp_fraction": 0.50,
        "recover_ramp_fraction": 0.50,
        "max_curtail_hours": 4,
        "min_recovery_gap_hr": 2.0,
        "daily_energy_neutral": True,
        "notification_lead_hr": 1.0,
        "curtail_target_fraction": 0.12,
    }
    defaults.update(overrides)
    return DrPlacementConfig(**defaults)  # type: ignore[arg-type]


def _make_candidate(bus: int, pd_mw: float, area: int) -> BusCandidate:
    return BusCandidate(bus=bus, pd_mw=pd_mw, area=area)


def _write_mock_m_file(tmp_path: Path, buses: list[tuple[int, float, int]]) -> Path:
    """Write a minimal MATPOWER .m file with specified buses.

    Each bus tuple is (bus_id, pd_mw, area). Generators are not relevant
    for DR placement so a minimal gen block is included.

    The bus matrix columns are:
    bus_i type Pd Qd Gs Bs area Vm Va baseKV zone Vmax Vmin
    """
    network_dir = tmp_path / "ACTIVSg2000"
    network_dir.mkdir(parents=True, exist_ok=True)
    m_file = network_dir / "case_ACTIVSg2000.m"

    bus_lines = []
    for bus_id, pd, area in buses:
        # bus_i type Pd  Qd  Gs Bs area Vm  Va baseKV zone Vmax Vmin
        bus_lines.append(f"\t{bus_id}\t1\t{pd}\t0\t0\t0\t{area}\t1.0\t0\t230\t1\t1.05\t0.95")

    bus_block = ";\n".join(bus_lines)

    # Minimal gen block (one generator at bus 1)
    gen_line = "\t1\t0\t0\t100\t-100\t1.0\t100\t1\t500\t0"

    content = textwrap.dedent(f"""\
        function mpc = case_ACTIVSg2000
        mpc.version = '2';
        mpc.baseMVA = 100;
        mpc.bus = [
        {bus_block}
        ];
        mpc.gen = [
        {gen_line}
        ];
        mpc.branch = [
        \t1\t1\t0.01\t0.1\t0\t100\t100\t100\t0\t0\t1\t-360\t360
        ];
    """)

    m_file.write_text(content)
    return network_dir


# ---------------------------------------------------------------------------
# Test 1: load_bus_data returns only nonzero Pd
# ---------------------------------------------------------------------------


def test_load_bus_data_returns_only_nonzero_pd(tmp_path: Path) -> None:
    """Call load_bus_data on a mock .m file with 5 buses (3 with Pd > 0, 2 with Pd = 0).
    Verify the result contains exactly 3 BusCandidate records.
    """
    buses = [
        (1, 100.0, 1),
        (2, 0.0, 1),
        (3, 200.0, 2),
        (4, 0.0, 2),
        (5, 50.0, 3),
    ]
    network_dir = _write_mock_m_file(tmp_path, buses)

    candidates = load_bus_data(network_dir, DrNetworkId.SMALL)

    assert len(candidates) == 3
    for c in candidates:
        assert c.pd_mw > 0


# ---------------------------------------------------------------------------
# Test 2: load_bus_data sorted by Pd descending
# ---------------------------------------------------------------------------


def test_load_bus_data_sorted_by_pd_descending(tmp_path: Path) -> None:
    """Call load_bus_data on a mock .m file with buses having Pd values
    [100, 500, 300, 200]. Verify sorted by pd_mw descending.
    """
    buses = [
        (1, 100.0, 1),
        (2, 500.0, 1),
        (3, 300.0, 2),
        (4, 200.0, 2),
    ]
    network_dir = _write_mock_m_file(tmp_path, buses)

    candidates = load_bus_data(network_dir, DrNetworkId.SMALL)

    pd_values = [c.pd_mw for c in candidates]
    assert pd_values == [500.0, 300.0, 200.0, 100.0]


# ---------------------------------------------------------------------------
# Test 3: select_dr_buses respects area diversity cap
# ---------------------------------------------------------------------------


def test_select_dr_buses_respects_area_diversity_cap() -> None:
    """Create 10 BusCandidate records all in area 1, with max_buses_per_area=3
    and max_buses=8. Verify that select_dr_buses returns exactly 3 buses.
    """
    candidates = [_make_candidate(bus=i, pd_mw=1000 - i * 10, area=1) for i in range(1, 11)]
    config = _make_config(min_buses=1, max_buses=8, max_buses_per_area=3)
    rng = _make_rng()

    selected = select_dr_buses(candidates, config, rng)

    assert len(selected) == 3


# ---------------------------------------------------------------------------
# Test 4: select_dr_buses distributes across areas
# ---------------------------------------------------------------------------


def test_select_dr_buses_distributes_across_areas() -> None:
    """Create 12 BusCandidate records: 5 in area 1, 4 in area 2, 3 in area 3.
    Verify at most 3 per area and total between min_buses and max_buses.
    """
    candidates = []
    pd = 1000.0
    # Area 1: 5 buses
    for i in range(5):
        candidates.append(_make_candidate(bus=100 + i, pd_mw=pd, area=1))
        pd -= 10
    # Area 2: 4 buses
    for i in range(4):
        candidates.append(_make_candidate(bus=200 + i, pd_mw=pd, area=2))
        pd -= 10
    # Area 3: 3 buses
    for i in range(3):
        candidates.append(_make_candidate(bus=300 + i, pd_mw=pd, area=3))
        pd -= 10

    # Sort by Pd descending (already in order)
    candidates.sort(key=lambda c: -c.pd_mw)

    config = _make_config(min_buses=5, max_buses=8, max_buses_per_area=3)
    rng = _make_rng()

    selected = select_dr_buses(candidates, config, rng)

    # Count per area
    area_counts: dict[int, int] = {}
    for s in selected:
        area_counts[s.area] = area_counts.get(s.area, 0) + 1

    for area, count in area_counts.items():
        assert count <= 3, f"Area {area} has {count} buses, expected <= 3"

    assert config.min_buses <= len(selected) <= config.max_buses


# ---------------------------------------------------------------------------
# Test 5: select_dr_buses raises if too few eligible
# ---------------------------------------------------------------------------


def test_select_dr_buses_raises_if_too_few_eligible() -> None:
    """Create 3 BusCandidate records (all in area 1) with min_buses=5.
    Verify that select_dr_buses raises ValueError.
    """
    candidates = [_make_candidate(bus=i, pd_mw=500 - i * 50, area=1) for i in range(1, 4)]
    config = _make_config(min_buses=5, max_buses=8, max_buses_per_area=3)
    rng = _make_rng()

    with pytest.raises(ValueError, match="Could not select"):
        select_dr_buses(candidates, config, rng)


# ---------------------------------------------------------------------------
# Test 6: assign_dr_parameters curtailment within bounds
# ---------------------------------------------------------------------------


def test_assign_dr_parameters_curtailment_within_bounds() -> None:
    """Assign DR parameters to a bus with Pd=400 MW. Verify max_curtail_mw
    is in [40.0, 60.0] (10-15% of 400 MW).
    """
    selected = [_make_candidate(bus=1, pd_mw=400.0, area=1)]
    config = _make_config(
        min_buses=1,
        max_buses=1,
        curtail_fraction_min=0.10,
        curtail_fraction_max=0.15,
        curtail_target_fraction=0.12,
    )
    rng = _make_rng()

    dr_buses = assign_dr_parameters(selected, config, DrNetworkId.SMALL, rng)

    assert len(dr_buses) == 1
    dr = dr_buses[0]
    assert 40.0 <= dr.max_curtail_mw <= 60.0, (
        f"max_curtail_mw={dr.max_curtail_mw} outside [40.0, 60.0]"
    )
    # Should be close to 48.0 (12% of 400), within perturbation tolerance
    assert abs(dr.max_curtail_mw - 48.0) < 10.0


# ---------------------------------------------------------------------------
# Test 7: assign_dr_parameters recovery is asymmetric
# ---------------------------------------------------------------------------


def test_assign_dr_parameters_recovery_is_asymmetric() -> None:
    """Verify max_recover_mw equals 0.75 * max_curtail_mw within 0.2 MW."""
    selected = [_make_candidate(bus=i, pd_mw=300.0 + i * 50, area=i) for i in range(1, 5)]
    config = _make_config(min_buses=1, max_buses=4, recovery_ratio=0.75)
    rng = _make_rng()

    dr_buses = assign_dr_parameters(selected, config, DrNetworkId.SMALL, rng)

    for dr in dr_buses:
        expected_recover = 0.75 * dr.max_curtail_mw
        assert abs(dr.max_recover_mw - expected_recover) <= 0.2, (
            f"DR bus {dr.bus}: max_recover_mw={dr.max_recover_mw} != "
            f"0.75 * {dr.max_curtail_mw} = {expected_recover}"
        )


# ---------------------------------------------------------------------------
# Test 8: assign_dr_parameters ramp limits positive
# ---------------------------------------------------------------------------


def test_assign_dr_parameters_ramp_limits_positive() -> None:
    """Verify ramp limits are positive and curtail_ramp = 0.50 * max_curtail_mw."""
    selected = [_make_candidate(bus=i, pd_mw=400.0, area=i) for i in range(1, 4)]
    config = _make_config(
        min_buses=1,
        max_buses=3,
        curtail_ramp_fraction=0.50,
        recover_ramp_fraction=0.50,
    )
    rng = _make_rng()

    dr_buses = assign_dr_parameters(selected, config, DrNetworkId.SMALL, rng)

    for dr in dr_buses:
        assert dr.curtail_ramp_mw_per_hr > 0
        assert dr.recover_ramp_mw_per_hr > 0
        expected_curtail_ramp = 0.50 * dr.max_curtail_mw
        assert abs(dr.curtail_ramp_mw_per_hr - expected_curtail_ramp) <= 0.1


# ---------------------------------------------------------------------------
# Test 9: assign_dr_parameters dr_id format
# ---------------------------------------------------------------------------


def test_assign_dr_parameters_dr_id_format() -> None:
    """Verify dr_id values are DR_SMALL_001 through DR_SMALL_006."""
    selected = [
        _make_candidate(bus=i * 10, pd_mw=500 - i * 20, area=(i % 3) + 1) for i in range(1, 7)
    ]
    config = _make_config(min_buses=1, max_buses=6)
    rng = _make_rng()

    dr_buses = assign_dr_parameters(selected, config, DrNetworkId.SMALL, rng)

    assert len(dr_buses) == 6
    expected_ids = [f"DR_SMALL_{i:03d}" for i in range(1, 7)]
    actual_ids = [dr.dr_id for dr in dr_buses]
    assert actual_ids == expected_ids

    # All unique
    assert len(set(actual_ids)) == len(actual_ids)


# ---------------------------------------------------------------------------
# Test 10: assign_dr_parameters energy neutrality flag
# ---------------------------------------------------------------------------


def test_assign_dr_parameters_energy_neutrality_flag() -> None:
    """Verify every DrBus has daily_energy_neutral=True."""
    selected = [_make_candidate(bus=1, pd_mw=400.0, area=1)]
    config = _make_config(min_buses=1, max_buses=1, daily_energy_neutral=True)
    rng = _make_rng()

    dr_buses = assign_dr_parameters(selected, config, DrNetworkId.SMALL, rng)

    for dr in dr_buses:
        assert dr.daily_energy_neutral is True


# ---------------------------------------------------------------------------
# Test 11: validate_dr_placement rejects area violation
# ---------------------------------------------------------------------------


def test_validate_dr_placement_rejects_area_violation() -> None:
    """Construct DrBus records where 4 buses are in the same area with
    max_buses_per_area=3. Verify ValueError.
    """
    candidates = [_make_candidate(bus=i, pd_mw=400.0, area=1) for i in range(1, 5)]
    config = _make_config(
        min_buses=1,
        max_buses=4,
        max_buses_per_area=3,
    )

    dr_buses = [
        DrBus(
            dr_id=f"DR_SMALL_{i:03d}",
            bus=i,
            max_curtail_mw=48.0,
            max_recover_mw=36.0,
            curtail_ramp_mw_per_hr=24.0,
            recover_ramp_mw_per_hr=18.0,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        )
        for i in range(1, 5)
    ]

    with pytest.raises(ValueError, match="Area.*exceeding max_buses_per_area"):
        validate_dr_placement(dr_buses, candidates, config, DrNetworkId.SMALL)


# ---------------------------------------------------------------------------
# Test 12: validate_dr_placement rejects curtailment out of range
# ---------------------------------------------------------------------------


def test_validate_dr_placement_rejects_curtailment_out_of_range() -> None:
    """Construct a DrBus with max_curtail_mw=5.0 at bus with Pd=400 MW (1.25%).
    Verify ValueError.
    """
    candidates = [_make_candidate(bus=1, pd_mw=400.0, area=1)]
    config = _make_config(min_buses=1, max_buses=1)

    dr_buses = [
        DrBus(
            dr_id="DR_SMALL_001",
            bus=1,
            max_curtail_mw=5.0,  # 1.25% of 400, below 10% floor
            max_recover_mw=3.75,
            curtail_ramp_mw_per_hr=2.5,
            recover_ramp_mw_per_hr=1.875,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        )
    ]

    with pytest.raises(ValueError, match="max_curtail_mw.*outside"):
        validate_dr_placement(dr_buses, candidates, config, DrNetworkId.SMALL)


# ---------------------------------------------------------------------------
# Test 13: write_dr_buses_csv columns and values
# ---------------------------------------------------------------------------


def test_write_dr_buses_csv_columns_and_values(tmp_path: Path) -> None:
    """Write 2 DrBus records to CSV, read back and verify columns, row count,
    boolean formatting, and float precision.
    """
    dr_buses = [
        DrBus(
            dr_id="DR_SMALL_001",
            bus=10,
            max_curtail_mw=48.0,
            max_recover_mw=36.0,
            curtail_ramp_mw_per_hr=24.0,
            recover_ramp_mw_per_hr=18.0,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        ),
        DrBus(
            dr_id="DR_SMALL_002",
            bus=20,
            max_curtail_mw=52.5,
            max_recover_mw=39.4,
            curtail_ramp_mw_per_hr=26.3,
            recover_ramp_mw_per_hr=19.7,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        ),
    ]

    csv_path = tmp_path / "dr_buses.csv"
    write_dr_buses_csv(dr_buses, csv_path)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    # (a) Check header columns
    expected_columns = [
        "dr_id",
        "bus",
        "max_curtail_mw",
        "max_recover_mw",
        "curtail_ramp_mw_per_hr",
        "recover_ramp_mw_per_hr",
        "max_curtail_hours",
        "min_recovery_gap_hr",
        "daily_energy_neutral",
        "notification_lead_hr",
    ]
    assert list(reader.fieldnames or []) == expected_columns

    # (b) 2 data rows
    assert len(rows) == 2

    # (c) daily_energy_neutral is written as "true"
    for row in rows:
        assert row["daily_energy_neutral"] == "true"

    # (d) Float values have 1 decimal place
    assert rows[0]["max_curtail_mw"] == "48.0"
    assert rows[1]["max_curtail_mw"] == "52.5"
    assert rows[1]["max_recover_mw"] == "39.4"


# ---------------------------------------------------------------------------
# Test 14: write_dr_buses_csv ordered by dr_id
# ---------------------------------------------------------------------------


def test_write_dr_buses_csv_ordered_by_dr_id(tmp_path: Path) -> None:
    """Write 3 DrBus records with dr_ids in reverse order. Verify rows
    are ordered by dr_id ascending.
    """
    dr_buses = [
        DrBus(
            dr_id="DR_SMALL_003",
            bus=30,
            max_curtail_mw=40.0,
            max_recover_mw=30.0,
            curtail_ramp_mw_per_hr=20.0,
            recover_ramp_mw_per_hr=15.0,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        ),
        DrBus(
            dr_id="DR_SMALL_001",
            bus=10,
            max_curtail_mw=48.0,
            max_recover_mw=36.0,
            curtail_ramp_mw_per_hr=24.0,
            recover_ramp_mw_per_hr=18.0,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        ),
        DrBus(
            dr_id="DR_SMALL_002",
            bus=20,
            max_curtail_mw=50.0,
            max_recover_mw=37.5,
            curtail_ramp_mw_per_hr=25.0,
            recover_ramp_mw_per_hr=18.8,
            max_curtail_hours=4,
            min_recovery_gap_hr=2.0,
            daily_energy_neutral=True,
            notification_lead_hr=1.0,
        ),
    ]

    csv_path = tmp_path / "dr_buses.csv"
    write_dr_buses_csv(dr_buses, csv_path)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    dr_ids = [row["dr_id"] for row in rows]
    assert dr_ids == ["DR_SMALL_001", "DR_SMALL_002", "DR_SMALL_003"]
