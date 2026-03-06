"""Tests for preprocess_activsg module."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.preprocess_activsg import (
    DownloadManifest,
    NetworkId,
    TimeSeriesType,
    _is_feb29,
    _parse_datetime,
    build_network_inventory,
    classify_series_type,
    convert_load_csv,
    convert_renewable_csv,
    main,
    write_inventory_json,
)

# ---------------------------------------------------------------------------
# Fixtures — small synthetic CSVs mimicking PowerWorld format
# ---------------------------------------------------------------------------

# 5 data rows (3 normal + 2 on Feb 29 to test filtering)
SAMPLE_LOAD_POWERWORLD = textwrap.dedent("""\
    PWOPFTimePoint,,,,,,,
    Date,Time,Num Load,Total MW Load,Bus 1001 #1 MW,Bus 1002 #1 MW,Bus 1013 #1 MW,Bus 1013 #2 MW
    1/1/2016,12:00:00 AM,4,500.0,100.5,200.3,75.0,75.0
    1/1/2016,1:00:00 AM,4,510.0,105.2,198.7,74.0,74.5
    1/1/2016,2:00:00 AM,4,505.0,102.1,201.0,76.0,75.2
    2/29/2016,12:00:00 AM,4,500.0,99.0,195.0,73.0,74.0
    2/29/2016,1:00:00 AM,4,510.0,101.0,197.0,72.0,73.0
""")

_RENEW_CAT = "PWOPFTimePoint,,,,,Solar,Solar,Wind,Wind,Wind"
_RENEW_HDR = (
    "Date,Time,Num Renewable,Total solar Gen,Total wind Gen,"
    "Gen 1011 #1 MW,Gen 1062 #1 MW,Gen 1004 #1 MW,Gen 1090 #1 MW,Gen 1090 #2 MW"
)
SAMPLE_RENEWABLE_POWERWORLD = "\n".join(
    [
        _RENEW_CAT,
        _RENEW_HDR,
        "1/1/2016,12:00:00 AM,5,10.0,300.0,5.0,5.0,100.0,100.0,100.0",
        "1/1/2016,1:00:00 AM,5,12.0,310.0,6.0,6.0,105.0,102.5,102.5",
        "1/1/2016,2:00:00 AM,5,15.0,305.0,8.0,7.0,110.0,97.5,97.5",
        "2/29/2016,12:00:00 AM,5,10.0,300.0,5.0,5.0,100.0,100.0,100.0",
        "2/29/2016,1:00:00 AM,5,12.0,310.0,6.0,6.0,105.0,102.5,102.5",
        "",
    ]
)

# Standard output format CSV (as written by the preprocess script)
SAMPLE_OUTPUT_CSV = textwrap.dedent("""\
    Time,Bus_1,Bus_2,Bus_3
    2016-01-01 00:00:00,100.5,200.3,150.0
    2016-01-01 01:00:00,105.2,198.7,148.5
    2016-01-01 02:00:00,102.1,201.0,151.2
""")


@pytest.fixture()
def load_powerworld_csv(tmp_path: Path) -> Path:
    p = tmp_path / "ACTIVISg2000_load_time_series_MW.csv"
    p.write_text(SAMPLE_LOAD_POWERWORLD)
    return p


@pytest.fixture()
def renewable_powerworld_csv(tmp_path: Path) -> Path:
    p = tmp_path / "ACTIVISg2000_renewable_time_series_MW.csv"
    p.write_text(SAMPLE_RENEWABLE_POWERWORLD)
    return p


@pytest.fixture()
def output_csv_path(tmp_path: Path) -> Path:
    p = tmp_path / "ACTIVSg2000_load.csv"
    p.write_text(SAMPLE_OUTPUT_CSV)
    return p


@pytest.fixture()
def raw_dir_with_output_csvs(tmp_path: Path) -> Path:
    """Create a raw directory with standard-format output CSVs."""
    raw = tmp_path / "ACTIVSg2000" / "raw"
    raw.mkdir(parents=True)
    for suffix in ("load", "wind", "solar"):
        (raw / f"ACTIVSg2000_{suffix}.csv").write_text(SAMPLE_OUTPUT_CSV)
    return raw


# ---------------------------------------------------------------------------
# DateTime parsing tests
# ---------------------------------------------------------------------------


class TestMergeDateTimeColumns:
    def test_midnight(self) -> None:
        assert _parse_datetime("1/1/2016", "12:00:00 AM") == "2016-01-01 00:00:00"

    def test_noon(self) -> None:
        assert _parse_datetime("1/1/2016", "12:00:00 PM") == "2016-01-01 12:00:00"

    def test_am_hour(self) -> None:
        assert _parse_datetime("3/15/2016", "9:00:00 AM") == "2016-03-15 09:00:00"

    def test_pm_hour(self) -> None:
        assert _parse_datetime("12/31/2016", "11:00:00 PM") == "2016-12-31 23:00:00"

    def test_1am(self) -> None:
        assert _parse_datetime("1/1/2016", "1:00:00 AM") == "2016-01-01 01:00:00"


# ---------------------------------------------------------------------------
# Load CSV conversion tests
# ---------------------------------------------------------------------------


class TestConvertLoadCsv:
    def test_rename_bus_columns(self, load_powerworld_csv: Path) -> None:
        """Bus 1001 #1 MW -> Bus_1001."""
        headers, _rows = convert_load_csv(load_powerworld_csv)
        assert "Bus_1001" in headers
        assert "Bus_1002" in headers
        assert "Bus_1013" in headers

    def test_sum_duplicate_buses(self, load_powerworld_csv: Path) -> None:
        """Bus 1013 #1 MW + Bus 1013 #2 MW should be summed."""
        headers, rows = convert_load_csv(load_powerworld_csv)
        bus_1013_idx = headers.index("Bus_1013")
        # Row 0: 75.0 + 75.0 = 150.0
        assert float(rows[0][bus_1013_idx]) == pytest.approx(150.0)
        # Row 1: 74.0 + 74.5 = 148.5
        assert float(rows[1][bus_1013_idx]) == pytest.approx(148.5)

    def test_drop_metadata_columns(self, load_powerworld_csv: Path) -> None:
        """Num Load, Total MW Load, Total Mvar Load should not appear."""
        headers, _rows = convert_load_csv(load_powerworld_csv)
        assert "Num Load" not in headers
        assert "Total MW Load" not in headers
        assert "Total Mvar Load" not in headers
        assert "Date" not in headers

    def test_drop_feb29(self, load_powerworld_csv: Path) -> None:
        """5 source rows -> 3 output rows (2 Feb 29 rows dropped)."""
        _headers, rows = convert_load_csv(load_powerworld_csv)
        assert len(rows) == 3
        for row in rows:
            assert not _is_feb29(row[0])

    def test_time_column_iso_format(self, load_powerworld_csv: Path) -> None:
        headers, rows = convert_load_csv(load_powerworld_csv)
        assert headers[0] == "Time"
        assert rows[0][0] == "2016-01-01 00:00:00"
        assert rows[1][0] == "2016-01-01 01:00:00"


# ---------------------------------------------------------------------------
# Renewable CSV conversion tests
# ---------------------------------------------------------------------------


class TestConvertRenewableCsv:
    def test_split_renewable_by_category(self, renewable_powerworld_csv: Path) -> None:
        """Solar and Wind columns split correctly."""
        wind_h, _wr, solar_h, _sr = convert_renewable_csv(renewable_powerworld_csv)
        # Wind should have Bus_1004 and Bus_1090
        assert "Bus_1004" in wind_h
        assert "Bus_1090" in wind_h
        # Solar should have Bus_1011 and Bus_1062
        assert "Bus_1011" in solar_h
        assert "Bus_1062" in solar_h

    def test_rename_gen_to_bus(self, renewable_powerworld_csv: Path) -> None:
        """Gen 1011 #1 MW -> Bus_1011."""
        _wh, _wr, solar_h, _sr = convert_renewable_csv(renewable_powerworld_csv)
        assert "Bus_1011" in solar_h
        assert "Gen 1011 #1 MW" not in solar_h

    def test_sum_duplicate_wind_gens(self, renewable_powerworld_csv: Path) -> None:
        """Gen 1090 #1 MW + Gen 1090 #2 MW should sum."""
        wind_h, wind_r, _sh, _sr = convert_renewable_csv(renewable_powerworld_csv)
        bus_1090_idx = wind_h.index("Bus_1090")
        # Row 0: 100.0 + 100.0 = 200.0
        assert float(wind_r[0][bus_1090_idx]) == pytest.approx(200.0)

    def test_drop_feb29_renewable(self, renewable_powerworld_csv: Path) -> None:
        """5 source rows -> 3 output rows."""
        _wh, wind_r, _sh, solar_r = convert_renewable_csv(renewable_powerworld_csv)
        assert len(wind_r) == 3
        assert len(solar_r) == 3

    def test_drop_metadata_columns_renewable(self, renewable_powerworld_csv: Path) -> None:
        wind_h, _wr, solar_h, _sr = convert_renewable_csv(renewable_powerworld_csv)
        for h in (wind_h, solar_h):
            assert "Num Renewable" not in h
            assert "Total solar Gen" not in h
            assert "Total wind Gen" not in h


# ---------------------------------------------------------------------------
# Manifest schema tests
# ---------------------------------------------------------------------------


class TestManifestSchema:
    def test_manifest_schema_matches(self, raw_dir_with_output_csvs: Path, tmp_path: Path) -> None:
        """Output manifest has all fields reconcile_bus_gen.py expects."""
        inv = build_network_inventory(
            NetworkId.ACTIVSG2000,
            raw_dir_with_output_csvs,
            "https://example.com",
        )
        json_path = tmp_path / "inventory.json"
        write_inventory_json(inv, json_path)
        data = json.loads(json_path.read_text())

        # Top-level fields
        assert "network_id" in data
        assert "files" in data
        assert data["network_id"] == "ACTIVSg2000"

        # File-level fields
        f = data["files"][0]
        assert "file_name" in f
        assert "file_path" in f
        assert "file_size_bytes" in f
        assert "series_type" in f
        assert "num_rows" in f
        assert "num_columns" in f
        assert "columns" in f
        assert "temporal_resolution_minutes" in f
        assert "date_range_start" in f
        assert "date_range_end" in f
        assert "bus_ids" in f
        assert "quirks" in f

        # bus_ids must be list of ints
        assert isinstance(f["bus_ids"], list)
        for bid in f["bus_ids"]:
            assert isinstance(bid, int)

    def test_classify_series_type(self) -> None:
        assert classify_series_type(["Time", "Bus_1"], "ACTIVSg2000_load.csv") == (
            TimeSeriesType.LOAD
        )
        assert classify_series_type(["Time", "Bus_1"], "ACTIVSg2000_wind.csv") == (
            TimeSeriesType.WIND
        )
        assert classify_series_type(["Time", "Bus_1"], "ACTIVSg2000_solar.csv") == (
            TimeSeriesType.SOLAR
        )


# ---------------------------------------------------------------------------
# End-to-end test
# ---------------------------------------------------------------------------


def _make_8760_load_csv(path: Path) -> None:
    """Create a minimal 8784-row PowerWorld load CSV (leap year, 3 buses)."""
    lines = ["PWOPFTimePoint,,,,,,\n"]
    lines.append("Date,Time,Num Load,Total MW Load,Total Mvar Load,Bus 1 #1 MW,Bus 2 #1 MW\n")
    start = datetime(2016, 1, 1, 0, 0, 0)
    for i in range(8784):
        dt = start + timedelta(hours=i)
        date_str = dt.strftime("%-m/%-d/%Y")
        hour = dt.hour
        if hour == 0:
            time_str = "12:00:00 AM"
        elif hour < 12:
            time_str = f"{hour}:00:00 AM"
        elif hour == 12:
            time_str = "12:00:00 PM"
        else:
            time_str = f"{hour - 12}:00:00 PM"
        lines.append(f"{date_str},{time_str},2,200.0,50.0,100.0,100.0\n")
    path.write_text("".join(lines))


def _make_8760_renewable_csv(path: Path) -> None:
    """Create a minimal 8784-row PowerWorld renewable CSV (1 wind, 1 solar)."""
    lines = ["PWOPFTimePoint,,,,Solar,Wind\n"]
    lines.append(
        "Date,Time,Num Renewable,Total solar Gen,Total wind Gen,Gen 10 #1 MW,Gen 20 #1 MW\n"
    )
    start = datetime(2016, 1, 1, 0, 0, 0)
    for i in range(8784):
        dt = start + timedelta(hours=i)
        date_str = dt.strftime("%-m/%-d/%Y")
        hour = dt.hour
        if hour == 0:
            time_str = "12:00:00 AM"
        elif hour < 12:
            time_str = f"{hour}:00:00 AM"
        elif hour == 12:
            time_str = "12:00:00 PM"
        else:
            time_str = f"{hour - 12}:00:00 PM"
        lines.append(f"{date_str},{time_str},2,50.0,150.0,50.0,150.0\n")
    path.write_text("".join(lines))


class TestEndToEnd:
    def test_main_end_to_end(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Full pipeline with synthetic 8784-row fixture CSVs."""
        raw_dir = tmp_path / "ACTIVSg_raw"
        raw_dir.mkdir()

        # Create all 4 source files with correct names
        _make_8760_load_csv(raw_dir / "ACTIVISg2000_load_time_series_MW.csv")
        _make_8760_renewable_csv(raw_dir / "ACTIVISg2000_renewable_time_series_MW.csv")
        _make_8760_load_csv(raw_dir / "ACTIVSg10k_load_time_series_MW.csv")
        _make_8760_renewable_csv(raw_dir / "ACTIVISg10k_renewable_time_series_MW.csv")

        output_dir = tmp_path / "timeseries"
        manifest = main(source_dir=raw_dir, output_base_dir=output_dir)

        # Manifest structure
        assert isinstance(manifest, DownloadManifest)
        assert len(manifest.networks) == 2
        network_ids = {inv.network_id for inv in manifest.networks}
        assert network_ids == {NetworkId.ACTIVSG2000, NetworkId.ACTIVSG10K}

        # Check output files exist with correct row counts
        for network in ("ACTIVSg2000", "ACTIVSg10k"):
            for suffix in ("load", "wind", "solar"):
                csv_path = output_dir / network / "raw" / f"{network}_{suffix}.csv"
                assert csv_path.exists(), f"Missing: {csv_path}"
                lines = csv_path.read_text().strip().split("\n")
                assert len(lines) == 8761, f"{csv_path.name}: {len(lines)} lines (expected 8761)"

            # Inventory JSON exists
            inv_path = output_dir / network / "inventory.json"
            assert inv_path.exists()
            inv_data = json.loads(inv_path.read_text())
            assert inv_data["network_id"] == network
            assert len(inv_data["files"]) == 3

        # Top-level manifest JSON exists
        manifest_path = output_dir / "download_manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text())
        assert len(manifest_data["networks"]) == 2

    def test_acquire_from_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When ACTIVSg_raw is empty, data is copied from ACTIVGS_TS_PATH."""
        # Set up a fake NAS source directory
        nas_dir = tmp_path / "nas_source"
        nas_dir.mkdir()
        _make_8760_load_csv(nas_dir / "ACTIVISg2000_load_time_series_MW.csv")
        _make_8760_renewable_csv(nas_dir / "ACTIVISg2000_renewable_time_series_MW.csv")
        _make_8760_load_csv(nas_dir / "ACTIVSg10k_load_time_series_MW.csv")
        _make_8760_renewable_csv(nas_dir / "ACTIVISg10k_renewable_time_series_MW.csv")

        monkeypatch.setenv("ACTIVGS_TS_PATH", str(nas_dir))

        output_dir = tmp_path / "timeseries"
        raw_cache = output_dir / "ACTIVSg_raw"
        # raw_cache doesn't exist yet — main should create it via env var
        manifest = main(source_dir=raw_cache, output_base_dir=output_dir)

        assert isinstance(manifest, DownloadManifest)
        assert len(manifest.networks) == 2
        # raw cache should now have the files
        assert (raw_cache / "ACTIVISg2000_load_time_series_MW.csv").exists()
