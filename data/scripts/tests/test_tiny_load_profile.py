"""Tests for tiny_load_profile.py — Load Profile Synthesis for case39.

18 unit tests covering:
  - normalize peak=1.0, all values in (0,1], 24 elements, reject zero peak, reject negative
  - extract 21 buses, exclude zero Pd, total Pd=6254.23, sorted by bus_id
  - system peak matches total, proportionality preserved, off-peak less than peak
  - CSV columns, CSV row count, CSV roundtrip, CSV bus ordering
  - metadata fields, metadata system hourly sums
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from scripts.reconcile_bus_gen import BusType, MatpowerBusRecord
from scripts.tiny_load_profile import (
    BusLoad,
    LoadProfileRow,
    NormalizedLoadShape,
    RtsGmlcLoadDay,
    build_load_metadata,
    distribute_load_profile,
    extract_bus_loads_from_records,
    normalize_load_shape,
    write_load_csv,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic bus records matching case39 structure
# ---------------------------------------------------------------------------

# (bus_id, bus_type, pd, qd, base_kv) — all 39 buses from case39.m
_CASE39_BUS_DATA: list[tuple[int, int, float, float, float]] = [
    (1, 1, 97.6, 44.2, 345),
    (2, 1, 0, 0, 345),
    (3, 1, 322, 2.4, 345),
    (4, 1, 500, 184, 345),
    (5, 1, 0, 0, 345),
    (6, 1, 0, 0, 345),
    (7, 1, 233.8, 84, 345),
    (8, 1, 522, 176.6, 345),
    (9, 1, 6.5, -66.6, 345),
    (10, 1, 0, 0, 345),
    (11, 1, 0, 0, 345),
    (12, 1, 8.53, 88, 345),
    (13, 1, 0, 0, 345),
    (14, 1, 0, 0, 345),
    (15, 1, 320, 153, 345),
    (16, 1, 329, 32.3, 345),
    (17, 1, 0, 0, 345),
    (18, 1, 158, 30, 345),
    (19, 1, 0, 0, 345),
    (20, 1, 680, 103, 345),
    (21, 1, 274, 115, 345),
    (22, 1, 0, 0, 345),
    (23, 1, 247.5, 84.6, 345),
    (24, 1, 308.6, -92.2, 345),
    (25, 1, 224, 47.2, 345),
    (26, 1, 139, 17, 345),
    (27, 1, 281, 75.5, 345),
    (28, 1, 206, 27.6, 345),
    (29, 1, 283.5, 26.9, 345),
    (30, 2, 0, 0, 345),
    (31, 3, 9.2, 4.6, 345),
    (32, 2, 0, 0, 345),
    (33, 2, 0, 0, 345),
    (34, 2, 0, 0, 345),
    (35, 2, 0, 0, 345),
    (36, 2, 0, 0, 345),
    (37, 2, 0, 0, 345),
    (38, 2, 0, 0, 345),
    (39, 2, 1104, 250, 345),
]


@pytest.fixture()
def case39_buses() -> list[MatpowerBusRecord]:
    """All 39 bus records from case39.m."""
    return [
        MatpowerBusRecord(
            bus_id=bus_id,
            bus_type=BusType(bus_type),
            pd=pd,
            qd=qd,
            base_kv=base_kv,
        )
        for bus_id, bus_type, pd, qd, base_kv in _CASE39_BUS_DATA
    ]


@pytest.fixture()
def simple_load_day() -> RtsGmlcLoadDay:
    """A simple synthetic 24-hour load shape for testing."""
    # Values from 50 to 100, with hour 18 as peak
    values = [
        60,
        55,
        50,
        50,
        52,
        58,
        70,
        78,
        82,
        85,
        88,
        90,
        91,
        92,
        93,
        90,
        95,
        100,
        98,
        94,
        88,
        80,
        72,
        62,
    ]
    return RtsGmlcLoadDay(hourly_mw=[float(v) for v in values])


@pytest.fixture()
def simple_shape(simple_load_day: RtsGmlcLoadDay) -> NormalizedLoadShape:
    """Normalized shape from the simple load day."""
    return normalize_load_shape(simple_load_day)


@pytest.fixture()
def case39_bus_loads(case39_buses: list[MatpowerBusRecord]) -> list[BusLoad]:
    """Bus loads extracted from case39 bus records."""
    return extract_bus_loads_from_records(case39_buses)


# ---------------------------------------------------------------------------
# Tests: normalize_load_shape
# ---------------------------------------------------------------------------


class TestNormalizeLoadShape:
    """Tests for the normalize_load_shape function."""

    def test_peak_equals_one(self, simple_load_day: RtsGmlcLoadDay) -> None:
        """The peak hour in the normalized shape must equal exactly 1.0."""
        shape = normalize_load_shape(simple_load_day)
        assert max(shape.fractions) == 1.0

    def test_all_values_in_zero_one(self, simple_load_day: RtsGmlcLoadDay) -> None:
        """All normalized values must be in the range (0, 1]."""
        shape = normalize_load_shape(simple_load_day)
        for f in shape.fractions:
            assert 0.0 < f <= 1.0

    def test_24_elements(self, simple_load_day: RtsGmlcLoadDay) -> None:
        """The normalized shape must have exactly 24 elements."""
        shape = normalize_load_shape(simple_load_day)
        assert len(shape.fractions) == 24

    def test_reject_zero_peak(self) -> None:
        """normalize_load_shape must reject a load day with all zeros."""
        load_day = RtsGmlcLoadDay(hourly_mw=[0.0] * 24)
        with pytest.raises(ValueError, match="zero or negative"):
            normalize_load_shape(load_day)

    def test_reject_negative(self) -> None:
        """normalize_load_shape must reject a load day with negative values."""
        values = [100.0] * 24
        values[5] = -10.0
        load_day = RtsGmlcLoadDay(hourly_mw=values)
        with pytest.raises(ValueError, match="negative"):
            normalize_load_shape(load_day)


# ---------------------------------------------------------------------------
# Tests: extract_bus_loads_from_records
# ---------------------------------------------------------------------------


class TestExtractBusLoads:
    """Tests for bus load extraction from case39 records."""

    def test_extract_21_buses(self, case39_buses: list[MatpowerBusRecord]) -> None:
        """case39 has exactly 21 buses with nonzero Pd."""
        loads = extract_bus_loads_from_records(case39_buses)
        assert len(loads) == 21

    def test_exclude_zero_pd(self, case39_buses: list[MatpowerBusRecord]) -> None:
        """Buses with Pd == 0 must be excluded."""
        loads = extract_bus_loads_from_records(case39_buses)
        for bl in loads:
            assert bl.pd_mw > 0.0

    def test_total_pd(self, case39_buses: list[MatpowerBusRecord]) -> None:
        """Total Pd across load buses must equal 6254.23 MW."""
        loads = extract_bus_loads_from_records(case39_buses)
        total = sum(bl.pd_mw for bl in loads)
        assert math.isclose(total, 6254.23, rel_tol=1e-6)

    def test_sorted_by_bus_id(self, case39_buses: list[MatpowerBusRecord]) -> None:
        """Bus loads must be sorted by bus_id."""
        loads = extract_bus_loads_from_records(case39_buses)
        bus_ids = [bl.bus_id for bl in loads]
        assert bus_ids == sorted(bus_ids)


# ---------------------------------------------------------------------------
# Tests: distribute_load_profile
# ---------------------------------------------------------------------------


class TestDistributeLoadProfile:
    """Tests for load profile distribution across buses."""

    def test_system_peak_matches_total(
        self,
        simple_shape: NormalizedLoadShape,
        case39_bus_loads: list[BusLoad],
    ) -> None:
        """At the peak hour (fraction=1.0), system total must equal total Pd."""
        rows = distribute_load_profile(simple_shape, case39_bus_loads)
        total_pd = sum(bl.pd_mw for bl in case39_bus_loads)
        # Find the peak hour index
        peak_idx = simple_shape.fractions.index(1.0)
        system_at_peak = sum(r.hourly_mw[peak_idx] for r in rows)
        assert math.isclose(system_at_peak, total_pd, rel_tol=1e-9)

    def test_proportionality_preserved(
        self,
        simple_shape: NormalizedLoadShape,
        case39_bus_loads: list[BusLoad],
    ) -> None:
        """The ratio between any two buses' load must equal the ratio of their Pd."""
        rows = distribute_load_profile(simple_shape, case39_bus_loads)
        # Compare first two buses at an arbitrary non-peak hour
        if len(rows) >= 2 and rows[1].hourly_mw[0] > 0:
            ratio_profile = rows[0].hourly_mw[0] / rows[1].hourly_mw[0]
            ratio_pd = case39_bus_loads[0].pd_mw / case39_bus_loads[1].pd_mw
            assert math.isclose(ratio_profile, ratio_pd, rel_tol=1e-9)

    def test_off_peak_less_than_peak(
        self,
        simple_shape: NormalizedLoadShape,
        case39_bus_loads: list[BusLoad],
    ) -> None:
        """Every off-peak hour's system total must be less than the peak hour total."""
        rows = distribute_load_profile(simple_shape, case39_bus_loads)
        peak_idx = simple_shape.fractions.index(1.0)
        system_at_peak = sum(r.hourly_mw[peak_idx] for r in rows)
        for h in range(24):
            if h == peak_idx:
                continue
            system_at_h = sum(r.hourly_mw[h] for r in rows)
            assert system_at_h < system_at_peak


# ---------------------------------------------------------------------------
# Tests: write_load_csv
# ---------------------------------------------------------------------------


class TestWriteLoadCsv:
    """Tests for CSV output."""

    @pytest.fixture()
    def sample_rows(self, simple_shape: NormalizedLoadShape) -> list[LoadProfileRow]:
        """A small set of load profile rows for CSV testing."""
        bus_loads = [
            BusLoad(bus_id=3, pd_mw=100.0),
            BusLoad(bus_id=1, pd_mw=50.0),
            BusLoad(bus_id=7, pd_mw=200.0),
        ]
        # Sort by bus_id to match expected behavior
        bus_loads_sorted = sorted(bus_loads, key=lambda bl: bl.bus_id)
        return distribute_load_profile(simple_shape, bus_loads_sorted)

    def test_csv_columns(
        self,
        sample_rows: list[LoadProfileRow],
        tmp_path: Path,
    ) -> None:
        """CSV must have columns: bus_id, HR_1, HR_2, ..., HR_24."""
        csv_path = tmp_path / "load_24h.csv"
        write_load_csv(sample_rows, csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)

        expected = ["bus_id"] + [f"HR_{h}" for h in range(1, 25)]
        assert header == expected

    def test_csv_row_count(
        self,
        sample_rows: list[LoadProfileRow],
        tmp_path: Path,
    ) -> None:
        """CSV must have one data row per bus (3 in this case)."""
        csv_path = tmp_path / "load_24h.csv"
        write_load_csv(sample_rows, csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.reader(fh)
            next(reader)  # skip header
            data_rows = list(reader)

        assert len(data_rows) == 3

    def test_csv_roundtrip(
        self,
        sample_rows: list[LoadProfileRow],
        tmp_path: Path,
    ) -> None:
        """Values written to CSV must be recoverable with reasonable precision."""
        csv_path = tmp_path / "load_24h.csv"
        write_load_csv(sample_rows, csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for i, row_dict in enumerate(reader):
                bus_id = int(row_dict["bus_id"])
                assert bus_id == sample_rows[i].bus_id
                for h in range(24):
                    col = f"HR_{h + 1}"
                    parsed = float(row_dict[col])
                    assert math.isclose(parsed, sample_rows[i].hourly_mw[h], abs_tol=0.0002)

    def test_csv_bus_ordering(
        self,
        sample_rows: list[LoadProfileRow],
        tmp_path: Path,
    ) -> None:
        """Bus IDs in CSV must be in sorted ascending order."""
        csv_path = tmp_path / "load_24h.csv"
        write_load_csv(sample_rows, csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            bus_ids = [int(row["bus_id"]) for row in reader]

        assert bus_ids == sorted(bus_ids)


# ---------------------------------------------------------------------------
# Tests: build_load_metadata
# ---------------------------------------------------------------------------


class TestLoadMetadata:
    """Tests for metadata construction."""

    def test_metadata_fields(
        self,
        simple_shape: NormalizedLoadShape,
        case39_buses: list[MatpowerBusRecord],
        case39_bus_loads: list[BusLoad],
    ) -> None:
        """Metadata must contain all required fields with correct values."""
        rows = distribute_load_profile(simple_shape, case39_bus_loads)
        meta = build_load_metadata(rows, case39_bus_loads, len(case39_buses))

        assert meta.network_id == "case39"
        assert meta.total_buses == 39
        assert meta.load_buses == 21
        assert meta.excluded_buses == 18
        assert math.isclose(meta.system_peak_mw, 6254.23, rel_tol=1e-6)
        assert meta.rts_gmlc_source == "synthetic_default"
        assert len(meta.hourly_system_mw) == 24

    def test_metadata_system_hourly_sums(
        self,
        simple_shape: NormalizedLoadShape,
        case39_bus_loads: list[BusLoad],
    ) -> None:
        """Each hourly system MW in metadata must equal the sum across all bus rows."""
        rows = distribute_load_profile(simple_shape, case39_bus_loads)
        meta = build_load_metadata(rows, case39_bus_loads, 39)

        for h in range(24):
            expected = sum(r.hourly_mw[h] for r in rows)
            assert math.isclose(meta.hourly_system_mw[h], expected, rel_tol=1e-9)
