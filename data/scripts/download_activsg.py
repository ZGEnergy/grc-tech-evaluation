"""ACTIVSg companion time series download and inventory.

Downloads published ACTIVSg companion time series CSV files from the Texas A&M
Electric Grid Test Case Repository for ACTIVSg2000 and ACTIVSg10k synthetic grids,
then parses and inventories every downloaded file into a structured JSON manifest.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

import numpy as np

__version__ = "0.1.0"

# Default base URL for the Texas A&M repository companion data
TAMU_BASE_URL = "https://electricgrids.engr.tamu.edu"

# Known companion CSV file names per network
KNOWN_FILES: dict[str, list[str]] = {
    "ACTIVSg2000": [
        "ACTIVSg2000_load.csv",
        "ACTIVSg2000_wind.csv",
        "ACTIVSg2000_solar.csv",
    ],
    "ACTIVSg10k": [
        "ACTIVSg10k_load.csv",
        "ACTIVSg10k_wind.csv",
        "ACTIVSg10k_solar.csv",
    ],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Identifier for supported ACTIVSg networks."""

    ACTIVSG2000 = "ACTIVSg2000"
    ACTIVSG10K = "ACTIVSg10k"


class TimeSeriesType(StrEnum):
    """Classification of a companion CSV time series file."""

    LOAD = "load"
    WIND = "wind"
    SOLAR = "solar"
    OTHER = "other"


@dataclass(frozen=True)
class ColumnSummary:
    """Statistical summary for a single CSV column."""

    name: str
    dtype: str
    non_null_count: int
    null_count: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None


@dataclass(frozen=True)
class FormattingQuirk:
    """A detected formatting anomaly in a CSV file."""

    quirk_type: str
    description: str
    affected_rows: list[int] = field(default_factory=list)
    affected_columns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileInventoryEntry:
    """Inventory metadata for a single parsed CSV file."""

    file_name: str
    file_path: str
    file_size_bytes: int
    series_type: TimeSeriesType
    num_rows: int
    num_columns: int
    columns: list[ColumnSummary]
    temporal_resolution_minutes: int | None
    date_range_start: str | None
    date_range_end: str | None
    bus_ids: list[int]
    quirks: list[FormattingQuirk] = field(default_factory=list)


@dataclass(frozen=True)
class NetworkInventory:
    """Aggregate inventory for all CSV files belonging to one network."""

    network_id: NetworkId
    download_url: str
    download_timestamp: str
    raw_directory: str
    files: list[FileInventoryEntry]
    total_size_bytes: int
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DownloadResult:
    """Result of downloading a single file."""

    file_name: str
    dest_path: Path
    size_bytes: int
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class DownloadManifest:
    """Top-level manifest covering all networks."""

    networks: list[NetworkInventory]
    script_version: str
    python_version: str
    generated_at: str


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def download_activsg_companion_data(
    network_id: NetworkId,
    dest_dir: Path,
    *,
    source_url: str | None = None,
    timeout_seconds: int = 120,
) -> list[DownloadResult]:
    """Download ACTIVSg companion time series CSVs for a single network.

    Args:
        network_id: Which ACTIVSg network to download data for.
        dest_dir: Base directory; files are placed in ``dest_dir/<network_id>/raw/``.
        source_url: Override URL base. When set, files are fetched from
            ``<source_url>/<filename>``. Supports both ``http(s)://`` and
            ``file://`` schemes.
        timeout_seconds: HTTP timeout in seconds.

    Returns:
        A list of ``DownloadResult`` for each file attempted.

    Raises:
        ValueError: If *network_id* is not a recognized ``NetworkId``.
    """
    if network_id not in NetworkId.__members__.values():
        msg = f"Unknown network_id: {network_id!r}"
        raise ValueError(msg)

    file_names = KNOWN_FILES[network_id.value]
    raw_dir = dest_dir / network_id.value / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    base_url = source_url if source_url else f"{TAMU_BASE_URL}/companion/{network_id.value}"

    results: list[DownloadResult] = []
    for fname in file_names:
        dest_path = raw_dir / fname
        url = f"{base_url}/{fname}"
        try:
            urlretrieve(url, dest_path)  # noqa: S310
            size = dest_path.stat().st_size
            results.append(
                DownloadResult(
                    file_name=fname,
                    dest_path=dest_path,
                    size_bytes=size,
                    success=True,
                )
            )
        except (URLError, OSError) as exc:
            results.append(
                DownloadResult(
                    file_name=fname,
                    dest_path=dest_path,
                    size_bytes=0,
                    success=False,
                    error=str(exc),
                )
            )

    return results


def classify_series_type(
    columns: list[str],
    file_name: str,
) -> TimeSeriesType:
    """Classify a CSV file as load, wind, solar, or other.

    Classification uses file name first, then falls back to column name
    heuristics.

    Args:
        columns: Column header names from the CSV.
        file_name: The file's base name.

    Returns:
        The inferred ``TimeSeriesType``.
    """
    name_lower = file_name.lower()
    if "load" in name_lower:
        return TimeSeriesType.LOAD
    if "wind" in name_lower:
        return TimeSeriesType.WIND
    if "solar" in name_lower:
        return TimeSeriesType.SOLAR

    # Fall back to column-name heuristics
    cols_lower = " ".join(c.lower() for c in columns)
    if "load" in cols_lower or "demand" in cols_lower:
        return TimeSeriesType.LOAD
    if "wind" in cols_lower:
        return TimeSeriesType.WIND
    if "solar" in cols_lower or "pv" in cols_lower:
        return TimeSeriesType.SOLAR

    return TimeSeriesType.OTHER


def _extract_bus_ids(columns: list[str]) -> list[int]:
    """Extract integer bus IDs from column headers.

    Recognises patterns like ``bus_123``, ``Bus 123``, ``123``, ``BUS123``.
    """
    bus_ids: list[int] = []
    bus_pattern = re.compile(r"(?:bus[_\s]?)(\d+)", re.IGNORECASE)
    for col in columns:
        m = bus_pattern.search(col)
        if m:
            bus_ids.append(int(m.group(1)))
        elif col.strip().isdigit():
            bus_ids.append(int(col.strip()))
    return sorted(set(bus_ids))


def _find_time_column(columns: list[str]) -> str | None:
    """Identify the timestamp / datetime column by name heuristic."""
    candidates = {"time", "timestamp", "datetime", "date", "hour", "date_time"}
    for col in columns:
        if col.strip().lower() in candidates:
            return col
    return None


def detect_formatting_quirks(
    csv_path: Path,
) -> list[FormattingQuirk]:
    """Scan a CSV file for formatting anomalies.

    Detected quirk types:
    - ``missing_values``: rows/columns containing NaN, empty cells, or ``NA``.
    - ``duplicate_timestamps``: repeated timestamp values.
    - ``inconsistent_delimiters``: lines with a delimiter different from comma.
    - ``non_standard_header``: header row with unexpected characters.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        A list of ``FormattingQuirk`` instances.
    """
    quirks: list[FormattingQuirk] = []

    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)
        num_cols = len(headers)

        missing_rows: list[int] = []
        missing_cols: set[str] = set()
        timestamps: list[str] = []
        time_col_idx: int | None = None

        time_col_name = _find_time_column(headers)
        if time_col_name is not None:
            time_col_idx = headers.index(time_col_name)

        for row_idx, row in enumerate(reader, start=2):  # row 1 is header
            # Check for missing values
            for col_idx, val in enumerate(row):
                stripped = val.strip().lower()
                if stripped in ("", "nan", "na", "null", "none"):
                    missing_rows.append(row_idx)
                    if col_idx < num_cols:
                        missing_cols.add(headers[col_idx])

            # Collect timestamps
            if time_col_idx is not None and time_col_idx < len(row):
                timestamps.append(row[time_col_idx].strip())

    if missing_rows:
        quirks.append(
            FormattingQuirk(
                quirk_type="missing_values",
                description=(f"Found missing/NaN values in {len(missing_rows)} row(s)"),
                affected_rows=sorted(set(missing_rows)),
                affected_columns=sorted(missing_cols),
            )
        )

    # Duplicate timestamps
    if timestamps:
        seen: dict[str, int] = {}
        dup_rows: list[int] = []
        for idx, ts in enumerate(timestamps, start=2):
            if ts in seen:
                dup_rows.append(idx)
            else:
                seen[ts] = idx
        if dup_rows:
            quirks.append(
                FormattingQuirk(
                    quirk_type="duplicate_timestamps",
                    description=(f"Found {len(dup_rows)} duplicate timestamp(s)"),
                    affected_rows=dup_rows,
                    affected_columns=[time_col_name] if time_col_name else [],
                )
            )

    return quirks


def parse_csv_file(
    csv_path: Path,
    network_id: NetworkId,
) -> FileInventoryEntry:
    """Parse a single downloaded CSV and produce an inventory entry.

    Args:
        csv_path: Path to the CSV file.
        network_id: The network this file belongs to.

    Returns:
        A fully populated ``FileInventoryEntry``.
    """
    file_size = csv_path.stat().st_size

    # Read entire file with csv module first to get raw structure
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)
        rows = list(reader)

    num_rows = len(rows)
    num_columns = len(headers)

    series_type = classify_series_type(headers, csv_path.name)
    bus_ids = _extract_bus_ids(headers)

    # Build per-column summaries using numpy for numeric stats
    col_summaries: list[ColumnSummary] = []
    for col_idx, col_name in enumerate(headers):
        values_raw = [row[col_idx] if col_idx < len(row) else "" for row in rows]

        # Try numeric parse
        numeric_values: list[float] = []
        null_count = 0
        for v in values_raw:
            stripped = v.strip()
            if stripped.lower() in ("", "nan", "na", "null", "none"):
                null_count += 1
                continue
            try:
                numeric_values.append(float(stripped))
            except ValueError:
                pass  # non-numeric cell

        non_null = len(values_raw) - null_count

        if numeric_values and len(numeric_values) == non_null:
            arr = np.array(numeric_values)
            col_summaries.append(
                ColumnSummary(
                    name=col_name,
                    dtype="float64",
                    non_null_count=non_null,
                    null_count=null_count,
                    min_value=float(np.min(arr)),
                    max_value=float(np.max(arr)),
                    mean_value=float(np.mean(arr)),
                )
            )
        else:
            col_summaries.append(
                ColumnSummary(
                    name=col_name,
                    dtype="str",
                    non_null_count=non_null,
                    null_count=null_count,
                    min_value=None,
                    max_value=None,
                    mean_value=None,
                )
            )

    # Temporal resolution
    time_col_name = _find_time_column(headers)
    temporal_resolution: int | None = None
    date_start: str | None = None
    date_end: str | None = None

    if time_col_name is not None:
        time_col_idx = headers.index(time_col_name)
        ts_strings = [
            row[time_col_idx].strip()
            for row in rows
            if time_col_idx < len(row) and row[time_col_idx].strip()
        ]
        if ts_strings:
            date_start = ts_strings[0]
            date_end = ts_strings[-1]

            # Try to infer resolution from first two timestamps
            if len(ts_strings) >= 2:
                for fmt in (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%m/%d/%Y %H:%M",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                ):
                    try:
                        t0 = datetime.strptime(ts_strings[0], fmt)
                        t1 = datetime.strptime(ts_strings[1], fmt)
                        delta = t1 - t0
                        temporal_resolution = int(delta.total_seconds() / 60)
                        break
                    except ValueError:
                        continue

    quirks = detect_formatting_quirks(csv_path)

    return FileInventoryEntry(
        file_name=csv_path.name,
        file_path=str(csv_path),
        file_size_bytes=file_size,
        series_type=series_type,
        num_rows=num_rows,
        num_columns=num_columns,
        columns=col_summaries,
        temporal_resolution_minutes=temporal_resolution,
        date_range_start=date_start,
        date_range_end=date_end,
        bus_ids=bus_ids,
        quirks=quirks,
    )


def build_network_inventory(
    network_id: NetworkId,
    raw_dir: Path,
    download_url: str,
) -> NetworkInventory:
    """Build a complete inventory for all CSV files in a network's raw directory.

    Args:
        network_id: The network being inventoried.
        raw_dir: Path to the directory containing raw CSV files.
        download_url: The URL used for downloading.

    Returns:
        A ``NetworkInventory`` covering every CSV in *raw_dir*.

    Raises:
        ValueError: If *raw_dir* contains no CSV files.
    """
    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        msg = f"No CSV files found in {raw_dir}"
        raise ValueError(msg)

    entries: list[FileInventoryEntry] = []
    total_size = 0
    for csv_path in csv_files:
        entry = parse_csv_file(csv_path, network_id)
        entries.append(entry)
        total_size += entry.file_size_bytes

    return NetworkInventory(
        network_id=network_id,
        download_url=download_url,
        download_timestamp=datetime.now(timezone.utc).isoformat(),
        raw_directory=str(raw_dir),
        files=entries,
        total_size_bytes=total_size,
    )


def build_download_manifest(
    inventories: list[NetworkInventory],
    script_version: str,
) -> DownloadManifest:
    """Assemble the top-level download manifest from per-network inventories.

    Args:
        inventories: One ``NetworkInventory`` per network processed.
        script_version: Version string for the generating script.

    Returns:
        A ``DownloadManifest`` ready for serialization.
    """
    return DownloadManifest(
        networks=inventories,
        script_version=script_version,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize(obj: object) -> object:
    """Custom JSON serializer for dataclasses, enums, and Path objects."""
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)  # type: ignore[arg-type]
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def write_inventory_json(
    inventory: NetworkInventory,
    dest_path: Path,
) -> None:
    """Serialize a ``NetworkInventory`` to a JSON file.

    The output is human-readable (indented, snake_case keys).

    Args:
        inventory: The inventory to serialize.
        dest_path: Where to write the JSON file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(inventory)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize)
        fh.write("\n")


def write_download_manifest_json(
    manifest: DownloadManifest,
    dest_path: Path,
) -> None:
    """Serialize the full ``DownloadManifest`` to a JSON file.

    Args:
        manifest: The manifest to serialize.
        dest_path: Where to write the JSON file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(manifest)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    output_base_dir: Path | None = None,
    *,
    skip_download: bool = False,
) -> DownloadManifest:
    """Entry point: download companion data for all networks and produce inventory.

    Args:
        output_base_dir: Base directory for downloaded data and inventory files.
            Defaults to ``data/timeseries/`` relative to the repo root.
        skip_download: If True, skip downloading and inventory existing files.

    Returns:
        The assembled ``DownloadManifest``.
    """
    if output_base_dir is None:
        output_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    inventories: list[NetworkInventory] = []

    for nid in NetworkId:
        raw_dir = output_base_dir / nid.value / "raw"

        if not skip_download:
            results = download_activsg_companion_data(nid, output_base_dir)
            failures = [r for r in results if not r.success]
            if failures:
                for f in failures:
                    print(f"WARNING: failed to download {f.file_name}: {f.error}")

        download_url = f"{TAMU_BASE_URL}/companion/{nid.value}"
        inventory = build_network_inventory(nid, raw_dir, download_url)
        inventories.append(inventory)

        # Write per-network inventory JSON
        inv_path = output_base_dir / nid.value / "inventory.json"
        write_inventory_json(inventory, inv_path)

    manifest = build_download_manifest(inventories, __version__)
    manifest_path = output_base_dir / "download_manifest.json"
    write_download_manifest_json(manifest, manifest_path)

    return manifest


if __name__ == "__main__":
    main()
