"""Preprocess ACTIVSg companion time series from PowerWorld export format.

Reads raw PowerWorld-format CSVs (obtained from TAMU via their request form) and
converts them into the standardized schema expected by downstream scripts
(select_representative_day.py, estimate_correlation.py, reconcile_bus_gen.py).

Source data: https://electricgrids.engr.tamu.edu/activsg-time-series-data/

The TAMU companion download endpoint (electricgrids.engr.tamu.edu/companion/) now
returns HTTP 403. Data must be requested manually from TAMU and placed in a local
directory. Set the ACTIVGS_TS_PATH environment variable to that directory, or
pre-populate data/timeseries/ACTIVSg_raw/ with the raw CSVs.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import numpy as np

__version__ = "0.2.0"

TAMU_DATA_URL = "https://electricgrids.engr.tamu.edu/activsg-time-series-data/"

# Source file mapping (handles ACTIVISg typo in real filenames)
SOURCE_FILES: dict[str, dict[str, str]] = {
    "ACTIVSg2000": {
        "load": "ACTIVISg2000_load_time_series_MW.csv",
        "renewable": "ACTIVISg2000_renewable_time_series_MW.csv",
    },
    "ACTIVSg10k": {
        "load": "ACTIVSg10k_load_time_series_MW.csv",
        "renewable": "ACTIVISg10k_renewable_time_series_MW.csv",
    },
}

# Output file names per network (matches old download_activsg.py KNOWN_FILES)
OUTPUT_FILES: dict[str, list[str]] = {
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
# Data structures (compatible with old download_activsg.py manifest schema)
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    ACTIVSG2000 = "ACTIVSg2000"
    ACTIVSG10K = "ACTIVSg10k"


class TimeSeriesType(StrEnum):
    LOAD = "load"
    WIND = "wind"
    SOLAR = "solar"
    OTHER = "other"


@dataclass(frozen=True)
class ColumnSummary:
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None


@dataclass(frozen=True)
class FormattingQuirk:
    quirk_type: str
    description: str
    affected_rows: list[int] = field(default_factory=list)
    affected_columns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileInventoryEntry:
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
    network_id: NetworkId
    download_url: str
    download_timestamp: str
    raw_directory: str
    files: list[FileInventoryEntry]
    total_size_bytes: int
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DownloadManifest:
    networks: list[NetworkInventory]
    script_version: str
    python_version: str
    generated_at: str


# ---------------------------------------------------------------------------
# PowerWorld format conversion
# ---------------------------------------------------------------------------

# Matches "Bus 1001 #1 MW" or "Bus 1001 #2 MW" etc.
_BUS_COL_RE = re.compile(r"Bus\s+(\d+)\s+#\d+\s+(?:Max\s+)?MW", re.IGNORECASE)

# Matches "Gen 1011 #1 MW" or "Gen 10691 #1 Max MW" etc.
_GEN_COL_RE = re.compile(r"Gen\s+(\d+)\s+#\d+\s+(?:Max\s+)?MW", re.IGNORECASE)


def _parse_datetime(date_str: str, time_str: str) -> str:
    """Merge PowerWorld Date + Time columns into ISO format string.

    Input format: date='1/1/2016', time='12:00:00 AM'
    Output: '2016-01-01 00:00:00'
    """
    combined = f"{date_str.strip()} {time_str.strip()}"
    dt = datetime.strptime(combined, "%m/%d/%Y %I:%M:%S %p")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _is_feb29(iso_datetime: str) -> bool:
    """Check if an ISO datetime string falls on Feb 29."""
    return iso_datetime[5:10] == "02-29"


def convert_load_csv(source_path: Path) -> tuple[list[str], list[list[str]]]:
    """Convert a PowerWorld load time-series CSV to standard format.

    Returns:
        (headers, rows) where headers = ['Time', 'Bus_1001', ...] and
        rows = [['2016-01-01 00:00:00', '100.5', ...], ...]
    """
    with open(source_path, newline="") as fh:
        reader = csv.reader(fh)
        _category_row = next(reader)  # Row 1: PWOPFTimePoint,,,... (skip)
        header_row = next(reader)  # Row 2: Date,Time,Num Load,...,Bus 1001 #1 MW,...

        # Identify bus columns (skip Date, Time, Num Load, Total MW/Mvar Load)
        bus_col_indices: dict[int, int] = {}  # source_index -> bus_id
        for i, col in enumerate(header_row):
            m = _BUS_COL_RE.match(col.strip())
            if m:
                bus_col_indices[i] = int(m.group(1))

        # Group by bus_id to sum duplicates
        bus_ids_ordered: list[int] = []
        seen_bus: set[int] = set()
        for i in sorted(bus_col_indices.keys()):
            bid = bus_col_indices[i]
            if bid not in seen_bus:
                bus_ids_ordered.append(bid)
                seen_bus.add(bid)

        # Build output
        out_headers = ["Time"] + [f"Bus_{bid}" for bid in bus_ids_ordered]
        out_rows: list[list[str]] = []

        for row in reader:
            iso_time = _parse_datetime(row[0], row[1])
            if _is_feb29(iso_time):
                continue

            # Sum values per bus_id
            bus_sums: dict[int, float] = {bid: 0.0 for bid in bus_ids_ordered}
            for src_idx, bid in bus_col_indices.items():
                val = row[src_idx].strip()
                if val:
                    bus_sums[bid] += float(val)

            out_row = [iso_time] + [str(bus_sums[bid]) for bid in bus_ids_ordered]
            out_rows.append(out_row)

    return out_headers, out_rows


def convert_renewable_csv(
    source_path: Path,
) -> tuple[list[str], list[list[str]], list[str], list[list[str]]]:
    """Convert a PowerWorld renewable time-series CSV to wind + solar.

    Returns:
        (wind_headers, wind_rows, solar_headers, solar_rows)
    """
    with open(source_path, newline="") as fh:
        reader = csv.reader(fh)
        category_row = next(reader)  # Row 1: PWOPFTimePoint,,,Solar,...,Wind,...
        header_row = next(reader)  # Row 2: Date,Time,Num Renewable,...,Gen XXXX #N MW,...

        # Build category map: column index -> 'Solar' or 'Wind'
        # category_row may have fewer entries than header_row for some files
        cat_map: dict[int, str] = {}
        for i, cat in enumerate(category_row):
            cat_lower = cat.strip().lower()
            if cat_lower in ("solar", "wind"):
                cat_map[i] = cat_lower

        # Parse gen columns — handles both "Gen XXXX #N MW" and bare bus IDs
        wind_col_indices: dict[int, int] = {}  # source_index -> bus_id
        solar_col_indices: dict[int, int] = {}

        for i, col in enumerate(header_row):
            if i not in cat_map:
                continue
            col_stripped = col.strip()
            m = _GEN_COL_RE.match(col_stripped)
            if m:
                bus_id = int(m.group(1))
            elif col_stripped.isdigit():
                bus_id = int(col_stripped)
            else:
                continue
            if cat_map[i] == "wind":
                wind_col_indices[i] = bus_id
            else:
                solar_col_indices[i] = bus_id

        def _unique_ordered_ids(col_indices: dict[int, int]) -> list[int]:
            ids: list[int] = []
            seen: set[int] = set()
            for i in sorted(col_indices.keys()):
                bid = col_indices[i]
                if bid not in seen:
                    ids.append(bid)
                    seen.add(bid)
            return ids

        wind_bus_ids = _unique_ordered_ids(wind_col_indices)
        solar_bus_ids = _unique_ordered_ids(solar_col_indices)

        wind_headers = ["Time"] + [f"Bus_{bid}" for bid in wind_bus_ids]
        solar_headers = ["Time"] + [f"Bus_{bid}" for bid in solar_bus_ids]
        wind_rows: list[list[str]] = []
        solar_rows: list[list[str]] = []

        for row in reader:
            iso_time = _parse_datetime(row[0], row[1])
            if _is_feb29(iso_time):
                continue

            # Wind sums
            wind_sums: dict[int, float] = {bid: 0.0 for bid in wind_bus_ids}
            for src_idx, bid in wind_col_indices.items():
                val = row[src_idx].strip()
                if val:
                    wind_sums[bid] += float(val)

            # Solar sums
            solar_sums: dict[int, float] = {bid: 0.0 for bid in solar_bus_ids}
            for src_idx, bid in solar_col_indices.items():
                val = row[src_idx].strip()
                if val:
                    solar_sums[bid] += float(val)

            wind_rows.append([iso_time] + [str(wind_sums[bid]) for bid in wind_bus_ids])
            solar_rows.append([iso_time] + [str(solar_sums[bid]) for bid in solar_bus_ids])

    return wind_headers, wind_rows, solar_headers, solar_rows


def write_csv(headers: list[str], rows: list[list[str]], dest_path: Path) -> None:
    """Write headers + rows to a CSV file."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------


def _validate_output(headers: list[str], rows: list[list[str]], label: str) -> None:
    """Run sanity checks on converted output."""
    # 8760 rows
    if len(rows) != 8760:
        msg = f"{label}: expected 8760 rows, got {len(rows)}"
        raise ValueError(msg)

    # No duplicate column names
    if len(headers) != len(set(headers)):
        dupes = [h for h in headers if headers.count(h) > 1]
        msg = f"{label}: duplicate columns: {set(dupes)}"
        raise ValueError(msg)

    # No Feb 29 timestamps
    for row in rows:
        if _is_feb29(row[0]):
            msg = f"{label}: found Feb 29 timestamp: {row[0]}"
            raise ValueError(msg)

    # All numeric values finite; small negatives (<1 MW) tolerated (load data noise)
    for row_idx, row in enumerate(rows):
        for col_idx in range(1, len(row)):
            val = float(row[col_idx])
            if not np.isfinite(val):
                msg = f"{label}: non-finite value at row {row_idx}, col {headers[col_idx]}"
                raise ValueError(msg)
            if val < -1.0:
                msg = (
                    f"{label}: large negative value {val} at row {row_idx}, col {headers[col_idx]}"
                )
                raise ValueError(msg)


# ---------------------------------------------------------------------------
# Inventory / manifest generation (reused from download_activsg.py)
# ---------------------------------------------------------------------------


def classify_series_type(columns: list[str], file_name: str) -> TimeSeriesType:
    """Classify a CSV file as load, wind, solar, or other."""
    name_lower = file_name.lower()
    if "load" in name_lower:
        return TimeSeriesType.LOAD
    if "wind" in name_lower:
        return TimeSeriesType.WIND
    if "solar" in name_lower:
        return TimeSeriesType.SOLAR
    cols_lower = " ".join(c.lower() for c in columns)
    if "load" in cols_lower or "demand" in cols_lower:
        return TimeSeriesType.LOAD
    if "wind" in cols_lower:
        return TimeSeriesType.WIND
    if "solar" in cols_lower or "pv" in cols_lower:
        return TimeSeriesType.SOLAR
    return TimeSeriesType.OTHER


def _extract_bus_ids(columns: list[str]) -> list[int]:
    """Extract integer bus IDs from column headers."""
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
    """Identify the timestamp column by name heuristic."""
    candidates = {"time", "timestamp", "datetime", "date", "hour", "date_time"}
    for col in columns:
        if col.strip().lower() in candidates:
            return col
    return None


def detect_formatting_quirks(csv_path: Path) -> list[FormattingQuirk]:
    """Scan a CSV file for formatting anomalies."""
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
        for row_idx, row in enumerate(reader, start=2):
            for col_idx, val in enumerate(row):
                stripped = val.strip().lower()
                if stripped in ("", "nan", "na", "null", "none"):
                    missing_rows.append(row_idx)
                    if col_idx < num_cols:
                        missing_cols.add(headers[col_idx])
            if time_col_idx is not None and time_col_idx < len(row):
                timestamps.append(row[time_col_idx].strip())
    if missing_rows:
        quirks.append(
            FormattingQuirk(
                quirk_type="missing_values",
                description=f"Found missing/NaN values in {len(missing_rows)} row(s)",
                affected_rows=sorted(set(missing_rows)),
                affected_columns=sorted(missing_cols),
            )
        )
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
                    description=f"Found {len(dup_rows)} duplicate timestamp(s)",
                    affected_rows=dup_rows,
                    affected_columns=[time_col_name] if time_col_name else [],
                )
            )
    return quirks


def parse_csv_file(csv_path: Path, network_id: NetworkId) -> FileInventoryEntry:
    """Parse a single output CSV and produce an inventory entry."""
    file_size = csv_path.stat().st_size
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)
        rows = list(reader)

    num_rows = len(rows)
    num_columns = len(headers)
    series_type = classify_series_type(headers, csv_path.name)
    bus_ids = _extract_bus_ids(headers)

    col_summaries: list[ColumnSummary] = []
    for col_idx, col_name in enumerate(headers):
        values_raw = [row[col_idx] if col_idx < len(row) else "" for row in rows]
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
                pass
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
    source_url: str,
) -> NetworkInventory:
    """Build inventory for all CSV files in a network's raw directory."""
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
        download_url=source_url,
        download_timestamp=datetime.now(timezone.utc).isoformat(),
        raw_directory=str(raw_dir),
        files=entries,
        total_size_bytes=total_size,
    )


def build_download_manifest(
    inventories: list[NetworkInventory],
    script_version: str,
) -> DownloadManifest:
    """Assemble the top-level download manifest from per-network inventories."""
    return DownloadManifest(
        networks=inventories,
        script_version=script_version,
        python_version=(
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Serialization
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


def write_inventory_json(inventory: NetworkInventory, dest_path: Path) -> None:
    """Serialize a NetworkInventory to a JSON file."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(inventory)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize)
        fh.write("\n")


def write_download_manifest_json(manifest: DownloadManifest, dest_path: Path) -> None:
    """Serialize the full DownloadManifest to a JSON file."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(manifest)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Data acquisition
# ---------------------------------------------------------------------------


def _acquire_raw_data(raw_cache_dir: Path) -> None:
    """Ensure raw PowerWorld CSVs exist in raw_cache_dir.

    Copies from ACTIVGS_TS_PATH env var if the cache is empty.
    """
    needed_files = set()
    for network_files in SOURCE_FILES.values():
        for fname in network_files.values():
            needed_files.add(fname)

    existing = {f.name for f in raw_cache_dir.glob("*.csv")} if raw_cache_dir.exists() else set()

    if needed_files <= existing:
        return  # All files already cached

    source_dir_str = os.environ.get("ACTIVGS_TS_PATH", "")
    if not source_dir_str:
        msg = (
            "ACTIVSg raw time-series data not found.\n"
            f"Download from: {TAMU_DATA_URL}\n"
            "Then set ACTIVGS_TS_PATH to the download location and re-run."
        )
        raise FileNotFoundError(msg)

    source_dir = Path(source_dir_str)
    if not source_dir.is_dir():
        msg = f"ACTIVGS_TS_PATH={source_dir_str} is not a valid directory"
        raise FileNotFoundError(msg)

    raw_cache_dir.mkdir(parents=True, exist_ok=True)
    for fname in needed_files:
        src = source_dir / fname
        if not src.exists():
            msg = f"Expected source file not found: {src}"
            raise FileNotFoundError(msg)
        dest = raw_cache_dir / fname
        print(f"Copying {src} -> {dest}")
        shutil.copy2(src, dest)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    source_dir: Path | None = None,
    output_base_dir: Path | None = None,
) -> DownloadManifest:
    """Preprocess ACTIVSg companion data and produce inventory manifests.

    Args:
        source_dir: Directory containing raw PowerWorld CSVs. Defaults to
            data/timeseries/ACTIVSg_raw/ (populated from ACTIVGS_TS_PATH if empty).
        output_base_dir: Base directory for output CSVs and manifests.
            Defaults to data/timeseries/.
    """
    if output_base_dir is None:
        output_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    if source_dir is None:
        source_dir = output_base_dir / "ACTIVSg_raw"

    # Acquire raw data if needed
    _acquire_raw_data(source_dir)

    inventories: list[NetworkInventory] = []

    for nid in NetworkId:
        network = nid.value
        raw_dir = output_base_dir / network / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        src_files = SOURCE_FILES[network]

        # Convert load CSV
        print(f"Converting {network} load...")
        load_headers, load_rows = convert_load_csv(source_dir / src_files["load"])
        _validate_output(load_headers, load_rows, f"{network}_load")
        write_csv(load_headers, load_rows, raw_dir / f"{network}_load.csv")
        print(f"  {len(load_headers) - 1} buses, {len(load_rows)} hours")

        # Convert renewable CSV -> wind + solar
        print(f"Converting {network} renewables...")
        wind_h, wind_r, solar_h, solar_r = convert_renewable_csv(
            source_dir / src_files["renewable"]
        )
        _validate_output(wind_h, wind_r, f"{network}_wind")
        _validate_output(solar_h, solar_r, f"{network}_solar")
        write_csv(wind_h, wind_r, raw_dir / f"{network}_wind.csv")
        write_csv(solar_h, solar_r, raw_dir / f"{network}_solar.csv")
        print(f"  {len(wind_h) - 1} wind gens, {len(solar_h) - 1} solar gens")

        # Build inventory from output CSVs
        inventory = build_network_inventory(nid, raw_dir, TAMU_DATA_URL)
        inventories.append(inventory)

        inv_path = output_base_dir / network / "inventory.json"
        write_inventory_json(inventory, inv_path)
        print(f"  Wrote {inv_path}")

    manifest = build_download_manifest(inventories, __version__)
    manifest_path = output_base_dir / "download_manifest.json"
    write_download_manifest_json(manifest, manifest_path)
    print(f"Wrote manifest: {manifest_path}")

    return manifest


if __name__ == "__main__":
    main()
