"""Load Profile Synthesis for TINY (case39).

Synthesizes a 24-hour bus-level load profile for case39 by extracting the
system-level hourly load shape from RTS-GMLC, normalizing to fraction-of-peak,
and distributing across case39 load buses proportionally to each bus's base-case
Pd. The system peak hour equals total base-case Pd (6,254.23 MW). Buses with
zero Pd are excluded (21 buses with nonzero Pd included).

Output artifacts:
  - data/timeseries/case39/load_24h.csv   (bus-level 24h load profile)
  - data/timeseries/case39/load_metadata.json (synthesis metadata)
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.reconcile_bus_gen import MatpowerBusRecord, parse_matpower_case

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# RTS-GMLC default hourly load shape (system-level MW for a representative day)
# ---------------------------------------------------------------------------

# These 24 values represent the system-level hourly load from a typical
# RTS-GMLC winter weekday, in MW, for hours ending 1 through 24.
# Source: RTS-GMLC timeseries_data_files/Load/DAY_AHEAD_Regional_Load.csv
# If actual RTS-GMLC data is unavailable, this serves as a synthetic default.
RTS_GMLC_DEFAULT_HOURLY_LOAD: list[float] = [
    4135.0,  # HR_1
    3940.0,  # HR_2
    3829.0,  # HR_3
    3775.0,  # HR_4
    3810.0,  # HR_5
    3986.0,  # HR_6
    4340.0,  # HR_7
    4563.0,  # HR_8
    4716.0,  # HR_9
    4860.0,  # HR_10
    4945.0,  # HR_11
    5010.0,  # HR_12
    5060.0,  # HR_13
    5100.0,  # HR_14
    5120.0,  # HR_15
    5078.0,  # HR_16
    5243.0,  # HR_17
    5572.0,  # HR_18
    5510.0,  # HR_19
    5280.0,  # HR_20
    5008.0,  # HR_21
    4690.0,  # HR_22
    4370.0,  # HR_23
    4090.0,  # HR_24
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RtsGmlcLoadDay:
    """System-level hourly load values for one representative day.

    Attributes:
        hourly_mw: 24 values of system-level load in MW, one per hour-ending
            (HR_1 through HR_24).
    """

    hourly_mw: list[float]

    def __post_init__(self) -> None:
        if len(self.hourly_mw) != 24:
            msg = f"Expected 24 hourly values, got {len(self.hourly_mw)}"
            raise ValueError(msg)


@dataclass(frozen=True)
class NormalizedLoadShape:
    """Fraction-of-peak load shape for 24 hours.

    Each value is in the range (0, 1], with at least one value equal to 1.0
    (the peak hour).

    Attributes:
        fractions: 24 values of load as a fraction of the daily peak.
    """

    fractions: list[float]


@dataclass(frozen=True)
class BusLoad:
    """Base-case real power demand for a single bus.

    Attributes:
        bus_id: MATPOWER bus identifier.
        pd_mw: Base-case real power demand (MW) from the .m file (Pd > 0).
    """

    bus_id: int
    pd_mw: float


@dataclass(frozen=True)
class LoadProfileRow:
    """One row of the load_24h.csv file: a bus's 24-hour load profile.

    Attributes:
        bus_id: MATPOWER bus identifier.
        hourly_mw: 24 values of load in MW for HR_1 through HR_24.
    """

    bus_id: int
    hourly_mw: list[float]


@dataclass(frozen=True)
class LoadProfileResult:
    """Complete result of load profile synthesis.

    Attributes:
        rows: List of LoadProfileRow, one per load bus, sorted by bus_id.
        metadata: Synthesis metadata.
    """

    rows: list[LoadProfileRow]
    metadata: LoadMetadata


@dataclass(frozen=True)
class LoadMetadata:
    """Metadata for the load profile synthesis process.

    Attributes:
        network_id: Network identifier (e.g. "case39").
        script_version: Version of this script.
        total_buses: Total number of buses in the network.
        load_buses: Number of buses with nonzero Pd (included in output).
        excluded_buses: Number of buses with zero Pd (excluded).
        system_peak_mw: Total system Pd at peak hour (sum of all bus Pd values).
        rts_gmlc_source: Description of the load shape source.
        hourly_system_mw: 24 system-level MW totals (sum across all buses per hour).
    """

    network_id: str
    script_version: str
    total_buses: int
    load_buses: int
    excluded_buses: int
    system_peak_mw: float
    rts_gmlc_source: str
    hourly_system_mw: list[float]


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------


def extract_rts_gmlc_load_day(
    hourly_mw: list[float] | None = None,
) -> RtsGmlcLoadDay:
    """Extract or provide the system-level hourly load for one day.

    If hourly_mw is provided, uses those values directly. Otherwise falls back
    to the built-in RTS_GMLC_DEFAULT_HOURLY_LOAD synthetic shape.

    Args:
        hourly_mw: Optional list of 24 hourly MW values. If None, uses the
            built-in default.

    Returns:
        An RtsGmlcLoadDay with 24 hourly MW values.

    Raises:
        ValueError: If the provided list does not have exactly 24 elements.
    """
    if hourly_mw is None:
        hourly_mw = list(RTS_GMLC_DEFAULT_HOURLY_LOAD)
    return RtsGmlcLoadDay(hourly_mw=hourly_mw)


def normalize_load_shape(load_day: RtsGmlcLoadDay) -> NormalizedLoadShape:
    """Normalize hourly MW values to fraction-of-peak.

    Divides each hourly value by the maximum value in the day, producing a
    shape where the peak hour has value 1.0 and all other hours are in (0, 1].

    Args:
        load_day: System-level hourly load values.

    Returns:
        A NormalizedLoadShape with 24 fraction values.

    Raises:
        ValueError: If the peak value is zero (cannot normalize).
        ValueError: If any hourly value is negative.
    """
    peak = max(load_day.hourly_mw)
    if peak <= 0.0:
        msg = "Cannot normalize: peak load is zero or negative"
        raise ValueError(msg)
    if any(v < 0.0 for v in load_day.hourly_mw):
        msg = "Cannot normalize: negative hourly values found"
        raise ValueError(msg)
    fractions = [v / peak for v in load_day.hourly_mw]
    return NormalizedLoadShape(fractions=fractions)


def extract_bus_loads(m_file_path: Path) -> list[BusLoad]:
    """Extract bus loads from a cleaned MATPOWER .m file.

    Parses the .m file using parse_matpower_case and returns a BusLoad for
    each bus with Pd > 0, sorted by bus_id.

    Args:
        m_file_path: Path to the cleaned MATPOWER .m file.

    Returns:
        List of BusLoad for buses with nonzero Pd, sorted by bus_id.
    """
    case_data = parse_matpower_case(m_file_path)
    return extract_bus_loads_from_records(case_data.buses)


def extract_bus_loads_from_records(buses: list[MatpowerBusRecord]) -> list[BusLoad]:
    """Extract bus loads from pre-parsed bus records.

    Returns a BusLoad for each bus with Pd > 0, sorted by bus_id.

    Args:
        buses: List of MatpowerBusRecord from a parsed MATPOWER case.

    Returns:
        List of BusLoad for buses with nonzero Pd, sorted by bus_id.
    """
    loads = [BusLoad(bus_id=b.bus_id, pd_mw=b.pd) for b in buses if b.pd > 0.0]
    return sorted(loads, key=lambda bl: bl.bus_id)


def distribute_load_profile(
    shape: NormalizedLoadShape,
    bus_loads: list[BusLoad],
) -> list[LoadProfileRow]:
    """Distribute the normalized load shape across buses proportionally to Pd.

    For each bus, the load at hour h = shape.fractions[h] * bus.pd_mw.
    This ensures the system peak hour equals the total base-case Pd.

    Args:
        shape: Normalized 24-hour load shape (fraction of peak).
        bus_loads: Bus loads with nonzero Pd, sorted by bus_id.

    Returns:
        List of LoadProfileRow, one per bus, sorted by bus_id.
    """
    rows: list[LoadProfileRow] = []
    for bl in bus_loads:
        hourly = [bl.pd_mw * f for f in shape.fractions]
        rows.append(LoadProfileRow(bus_id=bl.bus_id, hourly_mw=hourly))
    return rows


def write_load_csv(rows: list[LoadProfileRow], dest_path: Path) -> None:
    """Write load profile rows to a CSV file in canonical schema format.

    Produces a CSV with columns: bus_id, HR_1, HR_2, ..., HR_24.
    One row per bus, sorted by bus_id. Uses csv.writer with float formatting
    to 4 decimal places.

    Args:
        rows: Load profile rows to write.
        dest_path: File path for the output CSV. Parent directory is created
            if it does not exist.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["bus_id"] + [f"HR_{h}" for h in range(1, 25)]

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            csv_row: list[str | int] = [row.bus_id]
            csv_row.extend(f"{v:.4f}" for v in row.hourly_mw)
            writer.writerow(csv_row)


def build_load_metadata(
    rows: list[LoadProfileRow],
    bus_loads: list[BusLoad],
    total_bus_count: int,
    rts_gmlc_source: str = "synthetic_default",
) -> LoadMetadata:
    """Build metadata for the load profile synthesis.

    Args:
        rows: The generated load profile rows.
        bus_loads: Bus loads used in the synthesis.
        total_bus_count: Total number of buses in the network (including zero-Pd).
        rts_gmlc_source: Description of the load shape source.

    Returns:
        A LoadMetadata dataclass.
    """
    system_peak = sum(bl.pd_mw for bl in bus_loads)
    hourly_system_mw = [sum(r.hourly_mw[h] for r in rows) for h in range(24)]

    return LoadMetadata(
        network_id="case39",
        script_version=__version__,
        total_buses=total_bus_count,
        load_buses=len(bus_loads),
        excluded_buses=total_bus_count - len(bus_loads),
        system_peak_mw=system_peak,
        rts_gmlc_source=rts_gmlc_source,
        hourly_system_mw=hourly_system_mw,
    )


def write_load_metadata(metadata: LoadMetadata, dest_path: Path) -> None:
    """Write load metadata to a JSON file.

    Args:
        metadata: The metadata to write.
        dest_path: File path for the output JSON. Parent directory is created
            if it does not exist.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(asdict(metadata), fh, indent=2)
        fh.write("\n")


def synthesize_load_profile(
    m_file_path: Path,
    hourly_mw: list[float] | None = None,
    rts_gmlc_source: str = "synthetic_default",
) -> LoadProfileResult:
    """Run the complete load profile synthesis pipeline.

    Orchestrates: extract RTS-GMLC load day -> normalize -> extract bus loads
    -> distribute -> assemble result with metadata.

    Args:
        m_file_path: Path to the cleaned MATPOWER .m file.
        hourly_mw: Optional 24-hour system load shape in MW. If None, uses
            the built-in default.
        rts_gmlc_source: Description of the load shape source.

    Returns:
        A LoadProfileResult with rows and metadata.
    """
    case_data = parse_matpower_case(m_file_path)
    total_bus_count = len(case_data.buses)

    load_day = extract_rts_gmlc_load_day(hourly_mw)
    shape = normalize_load_shape(load_day)
    bus_loads = extract_bus_loads_from_records(case_data.buses)
    rows = distribute_load_profile(shape, bus_loads)
    metadata = build_load_metadata(rows, bus_loads, total_bus_count, rts_gmlc_source)

    return LoadProfileResult(rows=rows, metadata=metadata)


def main(
    m_file_path: Path | None = None,
    output_dir: Path | None = None,
    hourly_mw: list[float] | None = None,
) -> LoadProfileResult:
    """Entry point: synthesize load profile and write output artifacts.

    Args:
        m_file_path: Path to the cleaned case39.m file. Defaults to
            <repo_root>/data/timeseries/case39/case39.m.
        output_dir: Directory for output files. Defaults to
            <repo_root>/data/timeseries/case39/.
        hourly_mw: Optional 24-hour system load shape in MW.

    Returns:
        A LoadProfileResult with rows and metadata.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if m_file_path is None:
        m_file_path = repo_root / "timeseries" / "case39" / "case39.m"
    if output_dir is None:
        output_dir = repo_root / "timeseries" / "case39"

    rts_gmlc_source = "synthetic_default" if hourly_mw is None else "user_provided"
    result = synthesize_load_profile(m_file_path, hourly_mw, rts_gmlc_source)

    write_load_csv(result.rows, output_dir / "load_24h.csv")
    write_load_metadata(result.metadata, output_dir / "load_metadata.json")

    return result


if __name__ == "__main__":
    main()
