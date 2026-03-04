"""Tests for BESS & DR resource definitions (PRD 2b/06).

All tests are self-contained: minimal .m file fixtures are defined as string
constants and written to tmp_path. No network calls, no reading from data/networks/.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.tiny_bess_dr import (
    BESS_CSV_COLUMNS,
    DR_CSV_COLUMNS,
    BessDrDefinitionResult,
    BessUnit,
    DrBus,
    build_bess_unit,
    build_dr_bus,
    define_bess_and_dr,
    load_bus_data,
    validate_bess_placement,
    validate_dr_placement,
    write_bess_units_csv,
    write_dr_buses_csv,
)

# ---------------------------------------------------------------------------
# Minimal MATPOWER .m file fixtures
# ---------------------------------------------------------------------------

# case39-like snippet with buses 20 (Pd=680) and 25 (Pd=224), plus a few others
M_FILE_CASE39_SNIPPET = """\
function mpc = case39_snippet
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1   3  97.6   44.2  0  0  1  1.0  0.0  345  1  1.1  0.9;
   20   1  680.0  103.0 0  0  1  1.0  0.0  345  1  1.1  0.9;
   25   1  224.0   47.2 0  0  1  1.0  0.0  345  1  1.1  0.9;
   30   2  0.0     0.0  0  0  1  1.0  0.0  345  1  1.1  0.9;
   39   1  1104.0  250.0 0  0  1  1.0  0.0  345  1  1.1  0.9;
];

%% generator data
% bus Pg   Qg  Qmax Qmin Vg  mBase status Pmax Pmin
mpc.gen = [
    1   520.0  0.0  400  -400  1.0  100  1  1000  0;
   30   250.0  0.0  300  -300  1.0  100  1  1040  0;
];
"""

# Buses with zero-load bus (bus 99)
M_FILE_ZERO_LOAD = """\
function mpc = case_zero_load
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1   3  100.0  50.0  0  0  1  1.0  0.0  345  1  1.1  0.9;
   99   1  0.0    0.0   0  0  1  1.0  0.0  345  1  1.1  0.9;
];

mpc.gen = [
    1  50.0  0.0  30  -30  1.0  100  1  100  0;
];
"""


def _write_m_file(tmp_path: Path, content: str, name: str = "case39.m") -> Path:
    """Write a MATPOWER .m file and return its path."""
    p = tmp_path / name
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# Tests: BESS builder and properties
# ---------------------------------------------------------------------------


def test_bess_correct_type() -> None:
    """build_bess_unit returns a BessUnit instance with expected unit_id and bus."""
    bess = build_bess_unit()
    assert isinstance(bess, BessUnit)
    assert bess.unit_id == "BESS_1"
    assert bess.bus == 25


def test_bess_4_hour_duration() -> None:
    """BESS duration = energy_mwh / power_mw = 600 / 150 = 4 hours."""
    bess = build_bess_unit()
    assert bess.duration_hours == pytest.approx(4.0)


def test_bess_round_trip_efficiency() -> None:
    """Round-trip efficiency = charge_eff * discharge_eff = 0.92 * 0.95 = 0.874."""
    bess = build_bess_unit()
    assert bess.round_trip_efficiency == pytest.approx(0.92 * 0.95)


def test_bess_soc_bounds() -> None:
    """SoC bounds: min_soc < init_soc < max_soc, all in [0, 1]."""
    bess = build_bess_unit()
    assert 0.0 <= bess.min_soc < bess.init_soc < bess.max_soc <= 1.0
    assert bess.min_soc == pytest.approx(0.10)
    assert bess.max_soc == pytest.approx(0.90)
    assert bess.init_soc == pytest.approx(0.50)


def test_bess_reserve_eligibility() -> None:
    """BESS is eligible for both spinning and non-spinning reserves."""
    bess = build_bess_unit()
    assert bess.spinning_eligible is True
    assert bess.non_spinning_eligible is True


def test_bess_power_sizing_vs_system_peak() -> None:
    """BESS power (150 MW) should be meaningful relative to system peak load.

    case39 total load is ~6097 MW. 150 MW is ~2.5% of total, which is
    a reasonable BESS size for grid services.
    """
    bess = build_bess_unit()
    # The BESS should be between 1% and 10% of a ~6000 MW system
    system_peak_approx = 6097.0
    ratio = bess.power_mw / system_peak_approx
    assert 0.01 < ratio < 0.10


# ---------------------------------------------------------------------------
# Tests: DR builder and properties
# ---------------------------------------------------------------------------


def test_dr_correct_type() -> None:
    """build_dr_bus returns a DrBus instance at bus 20."""
    dr = build_dr_bus()
    assert isinstance(dr, DrBus)
    assert dr.bus == 20


def test_dr_curtailment_sizing() -> None:
    """DR max curtailment is 25 MW, which is ~3.7% of bus 20's 680 MW load."""
    dr = build_dr_bus()
    bus_20_load = 680.0
    ratio = dr.max_curtailment_mw / bus_20_load
    assert dr.max_curtailment_mw == pytest.approx(25.0)
    assert 0.03 < ratio < 0.04  # ~3.7%


def test_dr_energy_neutrality() -> None:
    """DR resource is energy-neutral: curtailment must be recovered."""
    dr = build_dr_bus()
    assert dr.energy_neutral is True


def test_dr_curtailment_gt_recovery_cost() -> None:
    """Curtailment cost ($200/MWh) must exceed recovery cost ($50/MWh)."""
    dr = build_dr_bus()
    assert dr.curtailment_cost > dr.recovery_cost
    assert dr.curtailment_cost == pytest.approx(200.0)
    assert dr.recovery_cost == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Tests: Validation
# ---------------------------------------------------------------------------


def test_validate_rejects_nonexistent_bus(tmp_path: Path) -> None:
    """validate_bess_placement raises ValueError for a bus not in the network."""
    m_path = _write_m_file(tmp_path, M_FILE_CASE39_SNIPPET)
    buses = load_bus_data(m_path)

    bad_bess = BessUnit(
        unit_id="BAD",
        bus=999,
        power_mw=100.0,
        energy_mwh=400.0,
        charge_eff=0.90,
        discharge_eff=0.90,
        min_soc=0.10,
        max_soc=0.90,
        init_soc=0.50,
        cyclic_soc=True,
        spinning_eligible=True,
        non_spinning_eligible=True,
    )
    with pytest.raises(ValueError, match="does not exist"):
        validate_bess_placement(bad_bess, buses)


def test_validate_rejects_zero_load_bus(tmp_path: Path) -> None:
    """validate_bess_placement raises ValueError for a bus with Pd=0."""
    m_path = _write_m_file(tmp_path, M_FILE_CASE39_SNIPPET)
    buses = load_bus_data(m_path)

    # Bus 30 has Pd=0.0
    bad_bess = BessUnit(
        unit_id="BAD",
        bus=30,
        power_mw=100.0,
        energy_mwh=400.0,
        charge_eff=0.90,
        discharge_eff=0.90,
        min_soc=0.10,
        max_soc=0.90,
        init_soc=0.50,
        cyclic_soc=True,
        spinning_eligible=True,
        non_spinning_eligible=True,
    )
    with pytest.raises(ValueError, match="zero or negative load"):
        validate_bess_placement(bad_bess, buses)


def test_validate_dr_rejects_low_curtailment(tmp_path: Path) -> None:
    """validate_dr_placement raises ValueError when curtailment fraction is too low."""
    m_path = _write_m_file(tmp_path, M_FILE_CASE39_SNIPPET)
    buses = load_bus_data(m_path)

    # Bus 39 has 1104 MW load; 0.5 MW curtailment is < 1%
    tiny_dr = DrBus(
        bus=39,
        max_curtailment_mw=0.5,
        max_recovery_mw=0.5,
        curtailment_cost=200.0,
        recovery_cost=50.0,
        max_hours=4.0,
        energy_neutral=True,
        notification_lead_time_hr=1.0,
    )
    with pytest.raises(ValueError, match="below minimum threshold"):
        validate_dr_placement(tiny_dr, buses)


# ---------------------------------------------------------------------------
# Tests: CSV output
# ---------------------------------------------------------------------------


def test_bess_csv_columns(tmp_path: Path) -> None:
    """bess_units.csv has the expected columns matching the D4 schema."""
    bess = build_bess_unit()
    csv_path = tmp_path / "bess_units.csv"
    write_bess_units_csv([bess], csv_path)

    with open(csv_path) as fh:
        reader = csv.reader(fh)
        header = next(reader)

    assert header == BESS_CSV_COLUMNS


def test_dr_csv_columns(tmp_path: Path) -> None:
    """dr_buses.csv has the expected columns matching the D4 schema."""
    dr = build_dr_bus()
    csv_path = tmp_path / "dr_buses.csv"
    write_dr_buses_csv([dr], csv_path)

    with open(csv_path) as fh:
        reader = csv.reader(fh)
        header = next(reader)

    assert header == DR_CSV_COLUMNS


# ---------------------------------------------------------------------------
# Tests: End-to-end
# ---------------------------------------------------------------------------


def test_end_to_end_output(tmp_path: Path) -> None:
    """define_bess_and_dr produces both CSVs with correct content."""
    m_path = _write_m_file(tmp_path, M_FILE_CASE39_SNIPPET)
    output_dir = tmp_path / "output"

    result = define_bess_and_dr(m_path, output_dir)

    assert isinstance(result, BessDrDefinitionResult)
    assert len(result.bess_units) == 1
    assert len(result.dr_buses) == 1

    # Verify BESS CSV content
    bess_path = Path(result.bess_csv_path)
    assert bess_path.exists()
    with open(bess_path) as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["unit_id"] == "BESS_1"
    assert rows[0]["bus_id"] == "25"
    assert float(rows[0]["power_mw"]) == pytest.approx(150.0)
    assert float(rows[0]["energy_mwh"]) == pytest.approx(600.0)
    assert float(rows[0]["efficiency"]) == pytest.approx(0.92 * 0.95, abs=1e-4)
    assert float(rows[0]["min_soc"]) == pytest.approx(0.10)
    assert float(rows[0]["max_soc"]) == pytest.approx(0.90)
    assert float(rows[0]["init_soc"]) == pytest.approx(0.50)

    # Verify DR CSV content
    dr_path = Path(result.dr_csv_path)
    assert dr_path.exists()
    with open(dr_path) as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["bus_id"] == "20"
    assert float(rows[0]["max_curtailment_mw"]) == pytest.approx(25.0)
    assert float(rows[0]["max_recovery_mw"]) == pytest.approx(25.0)
    assert float(rows[0]["curtailment_cost"]) == pytest.approx(200.0)
    assert float(rows[0]["recovery_cost"]) == pytest.approx(50.0)
    assert float(rows[0]["max_hours"]) == pytest.approx(4.0)
