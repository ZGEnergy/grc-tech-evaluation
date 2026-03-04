"""Tests for download_activsg module."""

from __future__ import annotations

import json
import textwrap
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

import pytest

from scripts.download_activsg import (
    DownloadManifest,
    NetworkId,
    TimeSeriesType,
    build_network_inventory,
    classify_series_type,
    detect_formatting_quirks,
    download_activsg_companion_data,
    main,
    parse_csv_file,
    write_inventory_json,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LOAD_CSV = textwrap.dedent("""\
    Time,Bus_1,Bus_2,Bus_3
    2019-01-01 00:00:00,100.5,200.3,150.0
    2019-01-01 01:00:00,105.2,198.7,148.5
    2019-01-01 02:00:00,102.1,201.0,151.2
    2019-01-01 03:00:00,99.8,195.4,147.3
""")

SAMPLE_WIND_CSV = textwrap.dedent("""\
    Time,Bus_10,Bus_20
    2019-01-01 00:00:00,50.0,80.0
    2019-01-01 01:00:00,55.0,75.0
    2019-01-01 02:00:00,60.0,70.0
""")

SAMPLE_SOLAR_CSV = textwrap.dedent("""\
    Time,Bus_100,Bus_200
    2019-01-01 00:00:00,0.0,0.0
    2019-01-01 01:00:00,0.0,0.0
    2019-01-01 02:00:00,10.5,5.3
""")

SAMPLE_CSV_WITH_MISSING = textwrap.dedent("""\
    Time,Bus_1,Bus_2
    2019-01-01 00:00:00,100.5,200.3
    2019-01-01 01:00:00,,198.7
    2019-01-01 02:00:00,102.1,NaN
""")

SAMPLE_CSV_WITH_DUP_TIMESTAMPS = textwrap.dedent("""\
    Time,Bus_1,Bus_2
    2019-01-01 00:00:00,100.5,200.3
    2019-01-01 01:00:00,105.2,198.7
    2019-01-01 01:00:00,102.1,201.0
""")


@pytest.fixture()
def load_csv_path(tmp_path: Path) -> Path:
    """Write a sample load CSV to a temp directory and return its path."""
    p = tmp_path / "ACTIVSg2000_load.csv"
    p.write_text(SAMPLE_LOAD_CSV)
    return p


@pytest.fixture()
def wind_csv_path(tmp_path: Path) -> Path:
    p = tmp_path / "ACTIVSg2000_wind.csv"
    p.write_text(SAMPLE_WIND_CSV)
    return p


@pytest.fixture()
def solar_csv_path(tmp_path: Path) -> Path:
    p = tmp_path / "ACTIVSg2000_solar.csv"
    p.write_text(SAMPLE_SOLAR_CSV)
    return p


@pytest.fixture()
def raw_dir_with_csvs(tmp_path: Path) -> Path:
    """Create a raw directory with all three CSV types."""
    raw = tmp_path / "ACTIVSg2000" / "raw"
    raw.mkdir(parents=True)
    (raw / "ACTIVSg2000_load.csv").write_text(SAMPLE_LOAD_CSV)
    (raw / "ACTIVSg2000_wind.csv").write_text(SAMPLE_WIND_CSV)
    (raw / "ACTIVSg2000_solar.csv").write_text(SAMPLE_SOLAR_CSV)
    return raw


@pytest.fixture()
def csv_with_missing(tmp_path: Path) -> Path:
    p = tmp_path / "missing.csv"
    p.write_text(SAMPLE_CSV_WITH_MISSING)
    return p


@pytest.fixture()
def csv_with_dup_ts(tmp_path: Path) -> Path:
    p = tmp_path / "dup_ts.csv"
    p.write_text(SAMPLE_CSV_WITH_DUP_TIMESTAMPS)
    return p


@pytest.fixture()
def file_server(tmp_path: Path) -> str:
    """Start a local HTTP server serving CSV files from tmp_path, return base URL."""
    # Write known files for ACTIVSg2000
    (tmp_path / "ACTIVSg2000_load.csv").write_text(SAMPLE_LOAD_CSV)
    (tmp_path / "ACTIVSg2000_wind.csv").write_text(SAMPLE_WIND_CSV)
    (tmp_path / "ACTIVSg2000_solar.csv").write_text(SAMPLE_SOLAR_CSV)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(tmp_path), **kwargs)

        def log_message(self, format, *args):  # noqa: A002
            pass  # suppress server logs during tests

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------


class TestDownload:
    def test_download_creates_raw_directories(self, tmp_path: Path, file_server: str) -> None:
        """Verify that download creates raw directories if they do not exist."""
        raw_dir = tmp_path / "output" / "ACTIVSg2000" / "raw"
        assert not raw_dir.exists()

        download_activsg_companion_data(
            NetworkId.ACTIVSG2000,
            tmp_path / "output",
            source_url=file_server,
        )

        assert raw_dir.is_dir()

    def test_download_writes_files_to_correct_paths(self, tmp_path: Path, file_server: str) -> None:
        """Verify files land in the correct directory with success=True."""
        results = download_activsg_companion_data(
            NetworkId.ACTIVSG2000,
            tmp_path / "output",
            source_url=file_server,
        )

        assert len(results) == 3
        for r in results:
            assert r.success is True
            assert r.size_bytes > 0
            assert r.dest_path.exists()
            assert r.dest_path.parent.name == "raw"
            assert "ACTIVSg2000" in str(r.dest_path)

    def test_download_invalid_network_raises(self, tmp_path: Path) -> None:
        """Verify that an invalid network_id raises ValueError."""
        with pytest.raises(ValueError, match="Unknown network_id"):
            download_activsg_companion_data(
                "InvalidNetwork",  # type: ignore[arg-type]
                tmp_path,
            )


# ---------------------------------------------------------------------------
# Parse tests
# ---------------------------------------------------------------------------


class TestParseCsv:
    def test_parse_csv_extracts_column_summaries(self, load_csv_path: Path) -> None:
        """Verify correct num_rows, num_columns, and per-column summaries."""
        entry = parse_csv_file(load_csv_path, NetworkId.ACTIVSG2000)

        assert entry.num_rows == 4
        assert entry.num_columns == 4

        # Time column is string type
        time_col = entry.columns[0]
        assert time_col.name == "Time"
        assert time_col.dtype == "str"

        # Bus_1 column is numeric
        bus1_col = entry.columns[1]
        assert bus1_col.name == "Bus_1"
        assert bus1_col.dtype == "float64"
        assert bus1_col.non_null_count == 4
        assert bus1_col.null_count == 0
        assert bus1_col.min_value == pytest.approx(99.8)
        assert bus1_col.max_value == pytest.approx(105.2)

    def test_parse_csv_detects_bus_ids(self, load_csv_path: Path) -> None:
        """Verify bus IDs extracted from column headers."""
        entry = parse_csv_file(load_csv_path, NetworkId.ACTIVSG2000)
        assert entry.bus_ids == [1, 2, 3]

    def test_parse_csv_determines_temporal_resolution(self, load_csv_path: Path) -> None:
        """Verify correct identification of hourly resolution (60 minutes)."""
        entry = parse_csv_file(load_csv_path, NetworkId.ACTIVSG2000)
        assert entry.temporal_resolution_minutes == 60

    def test_parse_csv_date_range(self, load_csv_path: Path) -> None:
        """Verify date range extraction."""
        entry = parse_csv_file(load_csv_path, NetworkId.ACTIVSG2000)
        assert entry.date_range_start == "2019-01-01 00:00:00"
        assert entry.date_range_end == "2019-01-01 03:00:00"


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------


class TestClassifySeriesType:
    def test_classify_series_type_load(self) -> None:
        """Verify LOAD classification for load file patterns."""
        result = classify_series_type(["Time", "Bus_1", "Bus_2"], "ACTIVSg2000_load.csv")
        assert result == TimeSeriesType.LOAD

    def test_classify_series_type_wind_and_solar(self) -> None:
        """Verify WIND and SOLAR classification."""
        assert classify_series_type(["Time", "Bus_10"], "network_wind.csv") == TimeSeriesType.WIND
        assert (
            classify_series_type(["Time", "Bus_100"], "network_solar.csv") == TimeSeriesType.SOLAR
        )

    def test_classify_series_type_other(self) -> None:
        """Verify OTHER when no pattern matches."""
        assert classify_series_type(["col_a", "col_b"], "mystery.csv") == TimeSeriesType.OTHER


# ---------------------------------------------------------------------------
# Quirk detection tests
# ---------------------------------------------------------------------------


class TestDetectQuirks:
    def test_detect_quirks_missing_values(self, csv_with_missing: Path) -> None:
        """Given a CSV with NaN values, verify missing_values quirk detected."""
        quirks = detect_formatting_quirks(csv_with_missing)

        missing_quirks = [q for q in quirks if q.quirk_type == "missing_values"]
        assert len(missing_quirks) == 1
        assert missing_quirks[0].affected_rows  # non-empty

    def test_detect_quirks_duplicate_timestamps(self, csv_with_dup_ts: Path) -> None:
        """Given a CSV with duplicate timestamp, verify quirk detected."""
        quirks = detect_formatting_quirks(csv_with_dup_ts)

        dup_quirks = [q for q in quirks if q.quirk_type == "duplicate_timestamps"]
        assert len(dup_quirks) == 1
        assert dup_quirks[0].affected_rows  # non-empty

    def test_no_quirks_on_clean_csv(self, load_csv_path: Path) -> None:
        """A clean CSV should produce no quirks."""
        quirks = detect_formatting_quirks(load_csv_path)
        assert quirks == []


# ---------------------------------------------------------------------------
# Network inventory tests
# ---------------------------------------------------------------------------


class TestBuildNetworkInventory:
    def test_build_network_inventory_aggregates_all_files(self, raw_dir_with_csvs: Path) -> None:
        """Verify all .csv files inventoried and total_size_bytes correct."""
        inv = build_network_inventory(
            NetworkId.ACTIVSG2000,
            raw_dir_with_csvs,
            "http://example.com",
        )

        assert len(inv.files) == 3
        expected_total = sum(f.file_size_bytes for f in inv.files)
        assert inv.total_size_bytes == expected_total
        assert inv.total_size_bytes > 0

    def test_build_network_inventory_empty_dir_raises(self, tmp_path: Path) -> None:
        """Verify ValueError when no .csv files found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(ValueError, match="No CSV files found"):
            build_network_inventory(
                NetworkId.ACTIVSG2000,
                empty_dir,
                "http://example.com",
            )


# ---------------------------------------------------------------------------
# JSON serialization tests
# ---------------------------------------------------------------------------


class TestJsonSerialization:
    def test_write_inventory_json_roundtrip(self, raw_dir_with_csvs: Path, tmp_path: Path) -> None:
        """Write and read back, verify all fields survive."""
        inv = build_network_inventory(
            NetworkId.ACTIVSG2000,
            raw_dir_with_csvs,
            "http://example.com",
        )

        json_path = tmp_path / "inventory.json"
        write_inventory_json(inv, json_path)

        data = json.loads(json_path.read_text())
        assert data["network_id"] == "ACTIVSg2000"
        assert len(data["files"]) == 3
        assert data["total_size_bytes"] == inv.total_size_bytes
        assert "download_timestamp" in data
        assert "raw_directory" in data

        # Verify column summaries survive
        first_file = data["files"][0]
        assert "columns" in first_file
        assert len(first_file["columns"]) > 0
        col = first_file["columns"][0]
        assert "name" in col
        assert "dtype" in col

    def test_inventory_json_is_human_readable(
        self, raw_dir_with_csvs: Path, tmp_path: Path
    ) -> None:
        """Verify JSON is indented with snake_case keys."""
        inv = build_network_inventory(
            NetworkId.ACTIVSG2000,
            raw_dir_with_csvs,
            "http://example.com",
        )

        json_path = tmp_path / "inventory.json"
        write_inventory_json(inv, json_path)

        raw_text = json_path.read_text()
        # Indented means multi-line
        assert raw_text.count("\n") > 5

        # All keys should be snake_case (no camelCase)
        data = json.loads(raw_text)

        def check_keys(obj: object) -> None:
            if isinstance(obj, dict):
                for key in obj:
                    # snake_case: lowercase with underscores, no uppercase
                    assert key == key.lower(), f"Key {key!r} is not snake_case"
                    check_keys(obj[key])
            elif isinstance(obj, list):
                for item in obj:
                    check_keys(item)

        check_keys(data)


# ---------------------------------------------------------------------------
# Main / manifest tests
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_skip_download_inventories_existing_files(self, tmp_path: Path) -> None:
        """Place fixture CSVs, call main(skip_download=True), verify valid manifest."""
        # Set up both networks
        for nid in ("ACTIVSg2000", "ACTIVSg10k"):
            raw = tmp_path / nid / "raw"
            raw.mkdir(parents=True)
            (raw / f"{nid}_load.csv").write_text(SAMPLE_LOAD_CSV)
            (raw / f"{nid}_wind.csv").write_text(SAMPLE_WIND_CSV)
            (raw / f"{nid}_solar.csv").write_text(SAMPLE_SOLAR_CSV)

        manifest = main(output_base_dir=tmp_path, skip_download=True)

        assert isinstance(manifest, DownloadManifest)
        assert len(manifest.networks) == 2
        assert manifest.script_version
        assert manifest.python_version
        assert manifest.generated_at

    def test_download_manifest_contains_both_networks(self, tmp_path: Path) -> None:
        """Verify manifest has exactly two NetworkInventory entries."""
        for nid in ("ACTIVSg2000", "ACTIVSg10k"):
            raw = tmp_path / nid / "raw"
            raw.mkdir(parents=True)
            (raw / f"{nid}_load.csv").write_text(SAMPLE_LOAD_CSV)
            (raw / f"{nid}_wind.csv").write_text(SAMPLE_WIND_CSV)
            (raw / f"{nid}_solar.csv").write_text(SAMPLE_SOLAR_CSV)

        manifest = main(output_base_dir=tmp_path, skip_download=True)

        network_ids = {inv.network_id for inv in manifest.networks}
        assert network_ids == {NetworkId.ACTIVSG2000, NetworkId.ACTIVSG10K}
        assert len(manifest.networks) == 2
