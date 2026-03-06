"""Tests for reserve product definition & sizing (PRD 02/04).

All tests are self-contained: minimal .m file fixtures are defined as string
constants and written to tmp_path. No network calls, no reading from data/timeseries/.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.define_reserves import (
    SIZING_BASIS_DESCRIPTION,
    LargestGenerator,
    ReserveNetworkId,
    ReserveProduct,
    ReserveRequirement,
    compute_reserve_requirements,
    find_largest_generator,
    load_generator_pmax_values,
    validate_reserve_feasibility,
    write_reserve_requirements_csv,
)

# ---------------------------------------------------------------------------
# Minimal MATPOWER .m file fixtures
# ---------------------------------------------------------------------------

# 5-generator case with known Pmax values: 100, 200, 300, 400, 500 MW
M_FILE_5_GENS = """\
function mpc = case5gen
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1  3  0.0   0.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    2  2  20.0  10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
    3  2  45.0  15.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
    4  2  40.0  5.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    5  2  60.0  10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
];

%% generator data
% bus Pg   Qg  Qmax Qmin Vg  mBase status Pmax Pmin
mpc.gen = [
    1  50.0  0.0  30   -30  1.0  100  1  100  0;
    2  80.0  0.0  60   -60  1.0  100  1  200  0;
    3  120.0 0.0  90   -90  1.0  100  1  300  0;
    4  160.0 0.0  120  -120 1.0  100  1  400  0;
    5  200.0 0.0  150  -150 1.0  100  1  500  0;
];
"""

# Valid bus section but NO generators
M_FILE_NO_GENS = """\
function mpc = case_nogen
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1  3  0.0  0.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    2  1  20.0 10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
];

mpc.gen = [
];
"""


# ---------------------------------------------------------------------------
# Tests: load_generator_pmax_values
# ---------------------------------------------------------------------------


def test_load_generator_pmax_values_count(tmp_path: Path) -> None:
    """Verify that 5 generators are returned with correct index, bus, and Pmax."""
    m_path = tmp_path / "case5gen.m"
    m_path.write_text(M_FILE_5_GENS)

    result = load_generator_pmax_values(m_path)

    assert len(result) == 5
    expected = [
        (0, 1, 100.0),
        (1, 2, 200.0),
        (2, 3, 300.0),
        (3, 4, 400.0),
        (4, 5, 500.0),
    ]
    for (idx, bus, pmax), (exp_idx, exp_bus, exp_pmax) in zip(result, expected, strict=True):
        assert idx == exp_idx
        assert bus == exp_bus
        assert pmax == pytest.approx(exp_pmax)


def test_load_generator_pmax_values_empty_file(tmp_path: Path) -> None:
    """Verify ValueError is raised when .m file has no generators."""
    m_path = tmp_path / "case_nogen.m"
    m_path.write_text(M_FILE_NO_GENS)

    with pytest.raises(ValueError, match="No generators found"):
        load_generator_pmax_values(m_path)


# ---------------------------------------------------------------------------
# Tests: find_largest_generator
# ---------------------------------------------------------------------------


def test_find_largest_generator_single_max() -> None:
    """Verify the generator with the highest Pmax is selected."""
    gen_data: list[tuple[int, int, float]] = [
        (0, 10, 100.0),
        (1, 20, 500.0),
        (2, 30, 200.0),
        (3, 40, 300.0),
    ]

    result = find_largest_generator(gen_data)

    assert isinstance(result, LargestGenerator)
    assert result.gen_index == 1
    assert result.gen_bus == 20
    assert result.pmax_mw == pytest.approx(500.0)
    assert result.gen_uid == "bus_20_gen_1"


def test_find_largest_generator_tiebreaker() -> None:
    """Verify lowest gen_index wins when multiple generators share max Pmax."""
    gen_data: list[tuple[int, int, float]] = [
        (0, 10, 100.0),
        (1, 20, 300.0),
        (2, 30, 500.0),  # tied max, lower index
        (3, 40, 200.0),
        (4, 50, 500.0),  # tied max, higher index
    ]

    result = find_largest_generator(gen_data)

    assert result.gen_index == 2
    assert result.pmax_mw == pytest.approx(500.0)
    assert result.gen_uid == "bus_30_gen_2"


def test_find_largest_generator_empty() -> None:
    """Verify ValueError is raised for empty gen_data."""
    with pytest.raises(ValueError, match="empty fleet"):
        find_largest_generator([])


# ---------------------------------------------------------------------------
# Tests: compute_reserve_requirements
# ---------------------------------------------------------------------------


def test_compute_reserve_requirements_values() -> None:
    """Verify both products have requirement_mw equal to largest generator Pmax."""
    largest = LargestGenerator(
        gen_index=3,
        gen_bus=42,
        gen_uid="bus_42_gen_3",
        pmax_mw=600.0,
    )

    spinning, non_spinning = compute_reserve_requirements(largest)

    assert spinning.product == ReserveProduct.SPINNING
    assert spinning.requirement_mw == pytest.approx(600.0)
    assert non_spinning.product == ReserveProduct.NON_SPINNING
    assert non_spinning.requirement_mw == pytest.approx(600.0)


def test_compute_reserve_requirements_sizing_basis() -> None:
    """Verify sizing_basis and largest generator fields are propagated correctly."""
    largest = LargestGenerator(
        gen_index=7,
        gen_bus=99,
        gen_uid="bus_99_gen_7",
        pmax_mw=450.0,
    )

    spinning, non_spinning = compute_reserve_requirements(largest)

    for req in (spinning, non_spinning):
        assert req.sizing_basis == SIZING_BASIS_DESCRIPTION
        assert req.largest_gen_uid == "bus_99_gen_7"
        assert req.largest_gen_pmax == pytest.approx(450.0)


# ---------------------------------------------------------------------------
# Tests: validate_reserve_feasibility
# ---------------------------------------------------------------------------


def test_validate_reserve_feasibility_passes() -> None:
    """Verify no exception when requirement < total capacity."""
    # Should not raise
    validate_reserve_feasibility(500.0, 5000.0, ReserveNetworkId.TINY)


def test_validate_reserve_feasibility_fails() -> None:
    """Verify ValueError when requirement >= total capacity."""
    # Equal case
    with pytest.raises(ValueError, match="not strictly less than"):
        validate_reserve_feasibility(5000.0, 5000.0, ReserveNetworkId.TINY)

    # Exceeding case
    with pytest.raises(ValueError, match="not strictly less than"):
        validate_reserve_feasibility(6000.0, 5000.0, ReserveNetworkId.SMALL)


# ---------------------------------------------------------------------------
# Tests: write_reserve_requirements_csv
# ---------------------------------------------------------------------------


def test_write_reserve_requirements_csv_format(tmp_path: Path) -> None:
    """Verify CSV structure, column count, product names, and hourly values."""
    spinning = ReserveRequirement(
        product=ReserveProduct.SPINNING,
        requirement_mw=350.0,
        sizing_basis=SIZING_BASIS_DESCRIPTION,
        largest_gen_uid="bus_42_gen_3",
        largest_gen_pmax=350.0,
    )
    non_spinning = ReserveRequirement(
        product=ReserveProduct.NON_SPINNING,
        requirement_mw=350.0,
        sizing_basis=SIZING_BASIS_DESCRIPTION,
        largest_gen_uid="bus_42_gen_3",
        largest_gen_pmax=350.0,
    )

    csv_path = tmp_path / "reserve_requirements_24h.csv"
    write_reserve_requirements_csv(spinning, non_spinning, csv_path)

    # Read back the file
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        rows = list(reader)

    # (a) Header: Product + HR_1..HR_24 + sizing_basis + largest_gen_uid + largest_gen_pmax
    #     = 1 + 24 + 1 + 1 + 1 = 28 columns
    header = rows[0]
    assert len(header) == 28
    assert header[0] == "Product"
    for h in range(1, 25):
        assert header[h] == f"HR_{h}"
    assert header[25] == "sizing_basis"
    assert header[26] == "largest_gen_uid"
    assert header[27] == "largest_gen_pmax"

    # (b) Exactly 2 data rows
    assert len(rows) == 3  # header + 2 data rows

    # (c) First row is spinning, second is non_spinning
    assert rows[1][0] == "spinning"
    assert rows[2][0] == "non_spinning"

    # (d) All HR_1 through HR_24 values equal "350.00"
    for data_row in rows[1:]:
        for col_idx in range(1, 25):
            assert data_row[col_idx] == "350.00"

    # (e) Metadata columns
    for data_row in rows[1:]:
        assert data_row[25] == SIZING_BASIS_DESCRIPTION
        assert data_row[26] == "bus_42_gen_3"
        assert data_row[27] == "350.00"
