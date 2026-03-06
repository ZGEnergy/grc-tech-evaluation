"""Tests for renewable_profiles.py -- Renewable Profile Synthesis & Placement."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.reconcile_bus_gen import parse_matpower_case
from scripts.renewable_profiles import (
    GENERATOR_BUSES,
    SOLAR_NIGHTTIME_HOURS,
    SYSTEM_PEAK_LOAD_MW,
    TARGET_PENETRATION_MAX,
    TARGET_PENETRATION_MIN,
    WIND_CAPACITY_SHARE,
    BusHeadroomScore,
    RenewableType,
    compute_branch_loading,
    compute_unit_capacities,
    load_rts_gmlc_solar_profile,
    load_rts_gmlc_wind_profile,
    scale_profiles,
    select_renewable_buses,
    write_renewable_units_csv,
    write_solar_24h_csv,
    write_wind_24h_csv,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CASE39_PATH = Path(__file__).resolve().parent.parent.parent / "networks" / "case39.m"


@pytest.fixture
def case_data():
    """Parse the actual case39.m file."""
    return parse_matpower_case(CASE39_PATH)


@pytest.fixture
def headroom_scores(case_data):
    """Compute headroom scores from the actual case39 data."""
    return compute_branch_loading(case_data)


@pytest.fixture
def placement(headroom_scores):
    """Select renewable buses from actual headroom scores."""
    return select_renewable_buses(headroom_scores)


@pytest.fixture
def units(placement):
    """Compute unit capacities at 20% penetration."""
    return compute_unit_capacities(
        wind_buses=placement.wind_buses,
        solar_buses=placement.solar_buses,
        penetration=0.20,
    )


@pytest.fixture
def wind_cf():
    """Default wind capacity factor profile."""
    return load_rts_gmlc_wind_profile()


@pytest.fixture
def solar_cf():
    """Default solar capacity factor profile."""
    return load_rts_gmlc_solar_profile()


# ---------------------------------------------------------------------------
# Test 1: Headroom scores cover all 39 buses
# ---------------------------------------------------------------------------


def test_headroom_scores_cover_all_buses(headroom_scores):
    """Headroom scores should include exactly one entry per bus (39 total)."""
    bus_ids = {s.bus_id for s in headroom_scores}
    assert len(bus_ids) == 39
    assert bus_ids == set(range(1, 40))


# ---------------------------------------------------------------------------
# Test 2: Headroom scores sorted descending
# ---------------------------------------------------------------------------


def test_headroom_scores_sorted_descending(headroom_scores):
    """Headroom scores should be sorted by headroom_mw in descending order."""
    headroom_values = [s.headroom_mw for s in headroom_scores]
    for i in range(len(headroom_values) - 1):
        assert headroom_values[i] >= headroom_values[i + 1], (
            f"Score at index {i} ({headroom_values[i]}) < score at index {i + 1} "
            f"({headroom_values[i + 1]})"
        )


# ---------------------------------------------------------------------------
# Test 3: Generator buses flagged correctly
# ---------------------------------------------------------------------------


def test_generator_buses_flagged(headroom_scores):
    """Buses 30-39 should be flagged as generator buses."""
    for score in headroom_scores:
        if score.bus_id in GENERATOR_BUSES:
            assert score.is_generator_bus, f"Bus {score.bus_id} should be a generator bus"
        else:
            assert not score.is_generator_bus, f"Bus {score.bus_id} should not be a generator bus"


# ---------------------------------------------------------------------------
# Test 4: No wind/solar bus overlap
# ---------------------------------------------------------------------------


def test_no_wind_solar_overlap(placement):
    """Wind and solar bus sets must not overlap."""
    wind_set = set(placement.wind_buses)
    solar_set = set(placement.solar_buses)
    assert wind_set.isdisjoint(solar_set), (
        f"Wind buses {wind_set} and solar buses {solar_set} overlap: {wind_set & solar_set}"
    )


# ---------------------------------------------------------------------------
# Test 5: Correct bus counts
# ---------------------------------------------------------------------------


def test_correct_bus_counts(placement):
    """Should select 3 wind buses and 2 solar buses."""
    assert len(placement.wind_buses) == 3
    assert len(placement.solar_buses) == 2


# ---------------------------------------------------------------------------
# Test 6: Area diversity
# ---------------------------------------------------------------------------


def test_area_diversity(headroom_scores, placement):
    """Selected buses should span multiple areas where possible."""
    area_map = {s.bus_id: s.area for s in headroom_scores}

    wind_areas = {area_map[b] for b in placement.wind_buses}
    solar_areas = {area_map[b] for b in placement.solar_buses}

    # With 3 wind buses from case39 (which has 3 areas), we expect
    # diversity -- at least 2 areas represented for wind.
    assert len(wind_areas) >= 2, f"Wind buses only span {len(wind_areas)} area(s)"
    # Solar with 2 buses -- at least 1 area (trivially true, but check > 0)
    assert len(solar_areas) >= 1


# ---------------------------------------------------------------------------
# Test 7: Reject insufficient candidates
# ---------------------------------------------------------------------------


def test_reject_insufficient_candidates():
    """Should raise ValueError when not enough non-generator candidates."""
    # Create scores where all buses are generator buses
    scores = [
        BusHeadroomScore(bus_id=i, area=1, headroom_mw=100.0, is_generator_bus=True, branch_count=2)
        for i in range(1, 6)
    ]
    with pytest.raises(ValueError, match="non-generator buses"):
        select_renewable_buses(scores)


# ---------------------------------------------------------------------------
# Test 8: Aggregate capacity in range
# ---------------------------------------------------------------------------


def test_aggregate_capacity_in_range(units):
    """Total renewable capacity should be 15-25% of system peak."""
    total_mw = sum(u.pmax_mw for u in units)
    min_mw = TARGET_PENETRATION_MIN * SYSTEM_PEAK_LOAD_MW
    max_mw = TARGET_PENETRATION_MAX * SYSTEM_PEAK_LOAD_MW
    assert min_mw <= total_mw <= max_mw, (
        f"Total {total_mw:.1f} MW outside [{min_mw:.1f}, {max_mw:.1f}]"
    )


# ---------------------------------------------------------------------------
# Test 9: Wind/solar split 60/40
# ---------------------------------------------------------------------------


def test_wind_solar_split(units):
    """Wind should get 60% and solar 40% of total capacity."""
    wind_mw = sum(u.pmax_mw for u in units if u.renewable_type == RenewableType.WIND)
    solar_mw = sum(u.pmax_mw for u in units if u.renewable_type == RenewableType.SOLAR)
    total_mw = wind_mw + solar_mw

    assert total_mw > 0
    wind_share = wind_mw / total_mw
    solar_share = solar_mw / total_mw

    assert abs(wind_share - WIND_CAPACITY_SHARE) < 0.01, (
        f"Wind share {wind_share:.2%} != expected {WIND_CAPACITY_SHARE:.0%}"
    )
    assert abs(solar_share - (1.0 - WIND_CAPACITY_SHARE)) < 0.01, (
        f"Solar share {solar_share:.2%} != expected {1.0 - WIND_CAPACITY_SHARE:.0%}"
    )


# ---------------------------------------------------------------------------
# Test 10: Reject out-of-range penetration
# ---------------------------------------------------------------------------


def test_reject_out_of_range_penetration(placement):
    """Should raise ValueError for penetration outside [15%, 25%]."""
    with pytest.raises(ValueError, match="outside allowed range"):
        compute_unit_capacities(
            wind_buses=placement.wind_buses,
            solar_buses=placement.solar_buses,
            penetration=0.05,
        )

    with pytest.raises(ValueError, match="outside allowed range"):
        compute_unit_capacities(
            wind_buses=placement.wind_buses,
            solar_buses=placement.solar_buses,
            penetration=0.50,
        )


# ---------------------------------------------------------------------------
# Test 11: gen_uid format
# ---------------------------------------------------------------------------


def test_gen_uid_format(units):
    """gen_uid should follow WIND_N or SOLAR_N format."""
    for unit in units:
        if unit.renewable_type == RenewableType.WIND:
            assert unit.gen_uid.startswith("WIND_"), f"Bad wind gen_uid: {unit.gen_uid}"
            suffix = unit.gen_uid.removeprefix("WIND_")
            assert suffix.isdigit(), f"Wind gen_uid suffix not numeric: {unit.gen_uid}"
        else:
            assert unit.gen_uid.startswith("SOLAR_"), f"Bad solar gen_uid: {unit.gen_uid}"
            suffix = unit.gen_uid.removeprefix("SOLAR_")
            assert suffix.isdigit(), f"Solar gen_uid suffix not numeric: {unit.gen_uid}"


# ---------------------------------------------------------------------------
# Test 12: Wind CF has 24 values
# ---------------------------------------------------------------------------


def test_wind_cf_24_values(wind_cf):
    """Wind capacity factor profile should have exactly 24 values."""
    assert len(wind_cf.values) == 24
    assert wind_cf.renewable_type == RenewableType.WIND
    for v in wind_cf.values:
        assert 0.0 <= v <= 1.0, f"Wind CF {v} outside [0, 1]"


# ---------------------------------------------------------------------------
# Test 13: Solar nighttime zeros
# ---------------------------------------------------------------------------


def test_solar_nighttime_zeros(solar_cf):
    """Solar CF should be zero during nighttime hours (HE 1-6, 21-24)."""
    for h in SOLAR_NIGHTTIME_HOURS:
        idx = h - 1  # convert hour-ending to 0-based index
        assert solar_cf.values[idx] == 0.0, (
            f"Solar CF at HE{h} (index {idx}) should be 0, got {solar_cf.values[idx]}"
        )


# ---------------------------------------------------------------------------
# Test 14: MW within Pmax
# ---------------------------------------------------------------------------


def test_mw_within_pmax(units, wind_cf, solar_cf):
    """Scaled MW profiles should never exceed Pmax for any hour."""
    wind_profiles, solar_profiles = scale_profiles(units, wind_cf, solar_cf)

    for prof in wind_profiles + solar_profiles:
        for h_idx, mw in enumerate(prof.values_mw):
            assert mw <= prof.pmax_mw + 0.01, (
                f"{prof.gen_uid} HE{h_idx + 1}: {mw:.2f} MW > Pmax {prof.pmax_mw:.2f} MW"
            )
            assert mw >= 0.0, f"{prof.gen_uid} HE{h_idx + 1}: negative MW {mw:.2f}"


# ---------------------------------------------------------------------------
# Test 15: Renewable units CSV columns
# ---------------------------------------------------------------------------


def test_renewable_units_csv_columns(units, tmp_path):
    """Renewable units CSV should have correct columns."""
    csv_path = tmp_path / "renewable_units.csv"
    write_renewable_units_csv(units, csv_path)

    with open(csv_path) as fh:
        reader = csv.reader(fh)
        header = next(reader)

    expected = ["gen_uid", "bus_id", "type", "pmax_mw", "area"]
    assert header == expected, f"Expected columns {expected}, got {header}"

    # Verify row count matches unit count
    with open(csv_path) as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        rows = list(reader)
    assert len(rows) == len(units)


# ---------------------------------------------------------------------------
# Test 16: Wind/solar CSV HR columns
# ---------------------------------------------------------------------------


def test_wind_solar_csv_hr_columns(units, wind_cf, solar_cf, tmp_path):
    """Wind and solar CSVs should have gen_uid + HR_1..HR_24 columns."""
    wind_profiles, solar_profiles = scale_profiles(units, wind_cf, solar_cf)

    wind_csv = tmp_path / "wind_actual_24h.csv"
    solar_csv = tmp_path / "solar_actual_24h.csv"

    write_wind_24h_csv(wind_profiles, wind_csv)
    write_solar_24h_csv(solar_profiles, solar_csv)

    expected_header = ["gen_uid"] + [f"HR_{h}" for h in range(1, 25)]

    for csv_path, profiles in [(wind_csv, wind_profiles), (solar_csv, solar_profiles)]:
        with open(csv_path) as fh:
            reader = csv.reader(fh)
            header = next(reader)
        assert header == expected_header, (
            f"Expected {expected_header[:3]}... got {header[:3]}... in {csv_path.name}"
        )

        with open(csv_path) as fh:
            reader = csv.reader(fh)
            next(reader)
            rows = list(reader)
        assert len(rows) == len(profiles), (
            f"Expected {len(profiles)} rows in {csv_path.name}, got {len(rows)}"
        )
