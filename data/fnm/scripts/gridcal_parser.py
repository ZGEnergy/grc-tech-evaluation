"""GridCal v31 RAW file parser with structured logging and CSV export.

Loads a PSS/E v31 RAW file through GridCal (VeraGridEngine), captures parser
logs, counts intermediate and final element counts, and exports GridCal
collections to CSV files for downstream validation.

Data classes and constants are importable without GridCal installed. Functions
that require GridCal perform lazy imports and raise ImportError with a helpful
message if VeraGridEngine is not available.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fnm.scripts.raw_record_counter import PSSE_V31_SECTION_NAMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PSSE_TO_GRIDCAL_MAPPING: dict[str, str | None] = {
    "Bus": "buses",
    "Load": "loads",
    "Fixed Shunt": "shunts",
    "Generator": "generators",
    "Branch": "lines",
    "Transformer": "transformers2w",
    "Area": "areas",
    "Two-Terminal DC": "hvdc_lines",
    "VSC DC": "vsc_devices",
    "Impedance Correction": None,  # merged into transformer tap tables
    "Multi-Terminal DC": None,  # dropped — not supported
    "Multi-Section Line": None,  # dropped — not supported
    "Zone": "zones",
    "Interarea Transfer": None,  # dropped — no GridCal equivalent
    "Owner": None,  # dropped — metadata only
    "FACTS": "facts_devices",
    "Switched Shunt": "controllable_shunts",
}

GRIDCAL_ELEMENT_COLLECTIONS: tuple[str, ...] = (
    "buses",
    "loads",
    "shunts",
    "generators",
    "lines",
    "transformers2w",
    "transformers3w",
    "areas",
    "zones",
    "hvdc_lines",
    "vsc_devices",
    "facts_devices",
    "controllable_shunts",
    "batteries",
    "static_generators",
    "substations",
    "voltage_levels",
    "connectivity_nodes",
    "fluid_nodes",
    "fluid_paths",
)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParserLogEntry:
    """A single log entry emitted during GridCal parsing.

    Attributes:
        time: ISO-8601 timestamp of the log entry.
        severity: Log level (e.g. 'INFO', 'WARNING', 'ERROR').
        message: Human-readable log message.
        device: Device identifier, if applicable.
        device_class: Device class/type name, if applicable.
        value: Actual value that triggered the log entry, if applicable.
        expected_value: Expected value for comparison, if applicable.
    """

    time: str
    severity: str
    message: str
    device: str = ""
    device_class: str = ""
    value: str = ""
    expected_value: str = ""


@dataclass
class ParserLog:
    """Aggregate parser log with individual entries and summary counts.

    Attributes:
        entries: List of individual log entries.
        info_count: Number of INFO-level entries.
        warning_count: Number of WARNING-level entries.
        error_count: Number of ERROR-level entries.
    """

    entries: list[ParserLogEntry] = field(default_factory=list)
    info_count: int = 0
    warning_count: int = 0
    error_count: int = 0


@dataclass(frozen=True)
class PsseIntermediateCounts:
    """Record counts from the PsseCircuit intermediate representation.

    Each field corresponds to one of the 17 PSS/E v31 data sections.
    """

    bus: int = 0
    load: int = 0
    fixed_shunt: int = 0
    generator: int = 0
    branch: int = 0
    transformer: int = 0
    area: int = 0
    two_terminal_dc: int = 0
    vsc_dc: int = 0
    impedance_correction: int = 0
    multi_terminal_dc: int = 0
    multi_section_line: int = 0
    zone: int = 0
    interarea_transfer: int = 0
    owner: int = 0
    facts: int = 0
    switched_shunt: int = 0


@dataclass(frozen=True)
class MultiCircuitCounts:
    """Element counts from the final GridCal MultiCircuit.

    Each field corresponds to a named element collection on the MultiCircuit.
    """

    buses: int = 0
    loads: int = 0
    shunts: int = 0
    generators: int = 0
    lines: int = 0
    transformers2w: int = 0
    transformers3w: int = 0
    areas: int = 0
    zones: int = 0
    hvdc_lines: int = 0
    vsc_devices: int = 0
    facts_devices: int = 0
    controllable_shunts: int = 0
    batteries: int = 0
    static_generators: int = 0
    substations: int = 0
    voltage_levels: int = 0
    connectivity_nodes: int = 0
    fluid_nodes: int = 0
    fluid_paths: int = 0


@dataclass(frozen=True)
class RecordTypeMapping:
    """Documents how one PSS/E section maps to a GridCal collection.

    Attributes:
        psse_section: PSS/E v31 section name.
        gridcal_collection: GridCal MultiCircuit property name, or None.
        status: Mapping status — 'mapped', 'dropped', or 'merged'.
        notes: Explanation of the mapping or reason for dropping/merging.
    """

    psse_section: str
    gridcal_collection: str | None
    status: str
    notes: str


@dataclass(frozen=True)
class GridCalParserSummary:
    """Complete output of a GridCal parse operation.

    Attributes:
        raw_path: Path to the source RAW file.
        psse_intermediate_counts: Counts from PsseCircuit.
        multicircuit_counts: Counts from MultiCircuit.
        parser_log: Structured parser log.
        record_type_mapping: Mapping documentation for all 17 sections.
        csv_files: List of exported CSV file paths.
        log_file: Path to the exported log file, or None.
        timestamp: ISO-8601 timestamp of the parse run.
    """

    raw_path: str
    psse_intermediate_counts: PsseIntermediateCounts
    multicircuit_counts: MultiCircuitCounts
    parser_log: ParserLog
    record_type_mapping: list[RecordTypeMapping]
    csv_files: list[str]
    log_file: str | None
    timestamp: str


# ---------------------------------------------------------------------------
# Lazy GridCal Import Helper
# ---------------------------------------------------------------------------


def _require_gridcal():  # noqa: ANN202
    """Import and return VeraGridEngine, raising ImportError if unavailable."""
    try:
        import VeraGridEngine as vge

        return vge
    except ImportError:
        raise ImportError(
            "VeraGridEngine (GridCal) is not installed. "
            "Install it with: pip install GridCal  or  uv add GridCal"
        ) from None


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_raw_with_logging(raw_path: str | Path) -> tuple:
    """Load a PSS/E RAW file via GridCal and return the parsed objects.

    Args:
        raw_path: Path to the PSS/E v31 RAW file.

    Returns:
        A tuple of (MultiCircuit, psse_circuit_or_None, Logger).
        psse_circuit may be None if the GridCal API does not expose
        the intermediate PsseCircuit object.

    Raises:
        ImportError: If VeraGridEngine is not installed.
        FileNotFoundError: If raw_path does not exist.
    """
    _require_gridcal()
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"RAW file not found: {raw_path}")

    # Use the FileOpen API for access to the logger
    from VeraGridEngine.IO.file_handler import FileOpen

    fo = FileOpen(str(raw_path))
    fo.open()
    grid = fo.circuit
    logger = fo.logger

    # Try to get the psse_circuit intermediate, if available
    psse_circuit = getattr(fo, "psse_circuit", None)

    return (grid, psse_circuit, logger)


def extract_logger_entries(logger: object) -> ParserLog:
    """Convert a GridCal Logger object to a structured ParserLog.

    Args:
        logger: A GridCal Logger instance with messages.

    Returns:
        A ParserLog with entries and aggregate counts.
    """
    entries: list[ParserLogEntry] = []
    info_count = 0
    warning_count = 0
    error_count = 0

    # GridCal Logger stores messages as lists of strings
    # Try common attribute patterns
    messages: list[str] = []
    if hasattr(logger, "messages"):
        messages = list(logger.messages) if logger.messages else []
    elif hasattr(logger, "entries"):
        messages = list(logger.entries) if logger.entries else []

    now = datetime.now(tz=timezone.utc).isoformat()

    for msg in messages:
        msg_str = str(msg)
        severity = "INFO"
        if "error" in msg_str.lower():
            severity = "ERROR"
            error_count += 1
        elif "warn" in msg_str.lower():
            severity = "WARNING"
            warning_count += 1
        else:
            info_count += 1

        entries.append(
            ParserLogEntry(
                time=now,
                severity=severity,
                message=msg_str,
            )
        )

    return ParserLog(
        entries=entries,
        info_count=info_count,
        warning_count=warning_count,
        error_count=error_count,
    )


def count_psse_intermediate(psse_circuit: object | None) -> PsseIntermediateCounts:
    """Extract record counts from a PsseCircuit intermediate object.

    Args:
        psse_circuit: The GridCal PsseCircuit object, or None.

    Returns:
        PsseIntermediateCounts with counts for each PSS/E section.
        All zeros if psse_circuit is None.
    """
    if psse_circuit is None:
        return PsseIntermediateCounts()

    # Map PSS/E section names to PsseCircuit attribute names
    attr_map = {
        "bus": ("buses",),
        "load": ("loads",),
        "fixed_shunt": ("fixed_shunts",),
        "generator": ("generators",),
        "branch": ("branches",),
        "transformer": ("transformers",),
        "area": ("areas",),
        "two_terminal_dc": ("two_terminal_dc",),
        "vsc_dc": ("vsc_dc",),
        "impedance_correction": ("impedance_corrections",),
        "multi_terminal_dc": ("multi_terminal_dc",),
        "multi_section_line": ("multi_section_lines",),
        "zone": ("zones",),
        "interarea_transfer": ("interarea_transfers",),
        "owner": ("owners",),
        "facts": ("facts",),
        "switched_shunt": ("switched_shunts",),
    }

    counts: dict[str, int] = {}
    for field_name, attr_names in attr_map.items():
        count = 0
        for attr_name in attr_names:
            val = getattr(psse_circuit, attr_name, None)
            if val is not None:
                try:
                    count = len(val)
                except TypeError:
                    count = 0
                break
        counts[field_name] = count

    return PsseIntermediateCounts(**counts)


def count_multicircuit(grid: object) -> MultiCircuitCounts:
    """Extract element counts from a GridCal MultiCircuit.

    Args:
        grid: A GridCal MultiCircuit instance.

    Returns:
        MultiCircuitCounts with counts for each element collection.
    """
    counts: dict[str, int] = {}
    for collection_name in GRIDCAL_ELEMENT_COLLECTIONS:
        val = getattr(grid, collection_name, None)
        if val is not None:
            try:
                counts[collection_name] = len(val)
            except TypeError:
                counts[collection_name] = 0
        else:
            counts[collection_name] = 0

    return MultiCircuitCounts(**counts)


def export_collection_to_csv(grid: object, collection_name: str, output_dir: Path) -> Path | None:
    """Export one GridCal element collection as a CSV file.

    Args:
        grid: A GridCal MultiCircuit instance.
        collection_name: Name of the collection property on the grid.
        output_dir: Directory where the CSV file will be written.

    Returns:
        Path to the created CSV file, or None if the collection is empty.
    """
    elements = getattr(grid, collection_name, None)
    if elements is None or len(elements) == 0:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"gridcal_{collection_name}.csv"

    # Attempt to extract properties from registered_properties or __dict__
    rows: list[dict[str, object]] = []
    for elem in elements:
        row: dict[str, object] = {}
        if hasattr(elem, "registered_properties"):
            for prop in elem.registered_properties:
                prop_name = getattr(prop, "name", str(prop))
                try:
                    row[prop_name] = getattr(elem, prop_name, None)
                except Exception:
                    row[prop_name] = None
        else:
            # Fallback: use public attributes
            for attr in dir(elem):
                if not attr.startswith("_") and not callable(getattr(elem, attr, None)):
                    try:
                        row[attr] = getattr(elem, attr, None)
                    except Exception:
                        pass
        rows.append(row)

    if not rows:
        return None

    # Gather all column names preserving order
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Convert non-serializable values to strings
            safe_row = {k: str(v) if v is not None else "" for k, v in row.items()}
            writer.writerow(safe_row)

    return csv_path


def export_all_collections(grid: object, output_dir: Path) -> list[Path]:
    """Export all non-empty GridCal element collections to CSV files.

    Args:
        grid: A GridCal MultiCircuit instance.
        output_dir: Directory where CSV files will be written.

    Returns:
        List of paths to the created CSV files.
    """
    csv_files: list[Path] = []
    for collection_name in GRIDCAL_ELEMENT_COLLECTIONS:
        result = export_collection_to_csv(grid, collection_name, output_dir)
        if result is not None:
            csv_files.append(result)
    return csv_files


# Mapping notes for each PSS/E section
_MAPPING_NOTES: dict[str, str] = {
    "Bus": "Direct 1:1 mapping to GridCal Bus objects.",
    "Load": "Direct 1:1 mapping to GridCal Load objects.",
    "Fixed Shunt": "Mapped to GridCal Shunt objects (fixed admittance).",
    "Generator": "Direct 1:1 mapping to GridCal Generator objects.",
    "Branch": "Mapped to GridCal Line objects (pi-model branches).",
    "Transformer": "Mapped to GridCal 2-winding transformer objects.",
    "Area": "Direct 1:1 mapping to GridCal Area objects.",
    "Two-Terminal DC": "Mapped to GridCal HVDC Line objects.",
    "VSC DC": "Mapped to GridCal VSC device objects.",
    "Impedance Correction": (
        "Merged into transformer tap-changer tables; no standalone GridCal collection."
    ),
    "Multi-Terminal DC": "Dropped — GridCal does not support multi-terminal DC.",
    "Multi-Section Line": "Dropped — GridCal does not support multi-section lines.",
    "Zone": "Direct 1:1 mapping to GridCal Zone objects.",
    "Interarea Transfer": "Dropped — no GridCal equivalent for interarea transfer schedules.",
    "Owner": "Dropped — ownership metadata not modeled in GridCal.",
    "FACTS": "Mapped to GridCal FACTS device objects.",
    "Switched Shunt": "Mapped to GridCal controllable shunt objects.",
}


def build_record_type_mapping() -> list[RecordTypeMapping]:
    """Build 17 RecordTypeMapping entries documenting PSS/E-to-GridCal mapping.

    Returns:
        List of 17 RecordTypeMapping entries, one per PSS/E v31 section.
    """
    mappings: list[RecordTypeMapping] = []
    for section_name in PSSE_V31_SECTION_NAMES:
        gridcal_collection = PSSE_TO_GRIDCAL_MAPPING[section_name]

        if gridcal_collection is not None:
            status = "mapped"
        elif section_name == "Impedance Correction":
            status = "merged"
        else:
            status = "dropped"

        notes = _MAPPING_NOTES.get(section_name, "")

        mappings.append(
            RecordTypeMapping(
                psse_section=section_name,
                gridcal_collection=gridcal_collection,
                status=status,
                notes=notes,
            )
        )

    return mappings


def build_summary(
    raw_path: str | Path,
    grid: object,
    psse_circuit: object | None,
    csv_files: list[str],
    log_file: str | None,
) -> GridCalParserSummary:
    """Assemble a complete GridCalParserSummary.

    Args:
        raw_path: Path to the source RAW file.
        grid: GridCal MultiCircuit instance.
        psse_circuit: GridCal PsseCircuit instance, or None.
        csv_files: List of exported CSV file paths (as strings).
        log_file: Path to the exported log file, or None.

    Returns:
        A fully populated GridCalParserSummary.
    """
    return GridCalParserSummary(
        raw_path=str(raw_path),
        psse_intermediate_counts=count_psse_intermediate(psse_circuit),
        multicircuit_counts=count_multicircuit(grid),
        parser_log=ParserLog(),
        record_type_mapping=build_record_type_mapping(),
        csv_files=csv_files,
        log_file=log_file,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )


def summary_to_dict(summary: GridCalParserSummary) -> dict:
    """Convert a GridCalParserSummary to a JSON-serializable dict.

    Args:
        summary: The summary to convert.

    Returns:
        A dict suitable for ``json.dumps()``.
    """
    return {
        "raw_path": summary.raw_path,
        "timestamp": summary.timestamp,
        "psse_intermediate_counts": {
            "bus": summary.psse_intermediate_counts.bus,
            "load": summary.psse_intermediate_counts.load,
            "fixed_shunt": summary.psse_intermediate_counts.fixed_shunt,
            "generator": summary.psse_intermediate_counts.generator,
            "branch": summary.psse_intermediate_counts.branch,
            "transformer": summary.psse_intermediate_counts.transformer,
            "area": summary.psse_intermediate_counts.area,
            "two_terminal_dc": summary.psse_intermediate_counts.two_terminal_dc,
            "vsc_dc": summary.psse_intermediate_counts.vsc_dc,
            "impedance_correction": summary.psse_intermediate_counts.impedance_correction,
            "multi_terminal_dc": summary.psse_intermediate_counts.multi_terminal_dc,
            "multi_section_line": summary.psse_intermediate_counts.multi_section_line,
            "zone": summary.psse_intermediate_counts.zone,
            "interarea_transfer": summary.psse_intermediate_counts.interarea_transfer,
            "owner": summary.psse_intermediate_counts.owner,
            "facts": summary.psse_intermediate_counts.facts,
            "switched_shunt": summary.psse_intermediate_counts.switched_shunt,
        },
        "multicircuit_counts": {
            name: getattr(summary.multicircuit_counts, name) for name in GRIDCAL_ELEMENT_COLLECTIONS
        },
        "parser_log": parser_log_to_dict(summary.parser_log),
        "record_type_mapping": [
            {
                "psse_section": m.psse_section,
                "gridcal_collection": m.gridcal_collection,
                "status": m.status,
                "notes": m.notes,
            }
            for m in summary.record_type_mapping
        ],
        "csv_files": summary.csv_files,
        "log_file": summary.log_file,
    }


def parser_log_to_dict(log: ParserLog) -> dict:
    """Convert a ParserLog to a JSON-serializable dict.

    Args:
        log: The parser log to convert.

    Returns:
        A dict suitable for ``json.dumps()``.
    """
    return {
        "entries": [
            {
                "time": e.time,
                "severity": e.severity,
                "message": e.message,
                "device": e.device,
                "device_class": e.device_class,
                "value": e.value,
                "expected_value": e.expected_value,
            }
            for e in log.entries
        ],
        "info_count": log.info_count,
        "warning_count": log.warning_count,
        "error_count": log.error_count,
    }


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for GridCal parser execution.

    Usage:
        python -m fnm.scripts.gridcal_parser /path/to/file.raw [-o output_dir]
    """
    _require_gridcal()

    parser = argparse.ArgumentParser(
        description="Parse a PSS/E v31 RAW file via GridCal and export results."
    )
    parser.add_argument("raw_file", type=str, help="Path to the PSS/E v31 RAW file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for CSV exports and summary JSON",
    )
    args = parser.parse_args(argv)

    raw_path = Path(args.raw_file)
    output_dir = Path(args.output_dir) if args.output_dir else raw_path.parent / "gridcal_output"

    # Load and parse
    grid, psse_circuit, logger = load_raw_with_logging(raw_path)

    # Extract log
    parser_log = extract_logger_entries(logger)

    # Export CSVs
    csv_paths = export_all_collections(grid, output_dir)
    csv_files = [str(p) for p in csv_paths]

    # Write log file
    log_file_path = output_dir / "parser_log.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dict = parser_log_to_dict(parser_log)
    log_file_path.write_text(json.dumps(log_dict, indent=2) + "\n", encoding="utf-8")

    # Build and write summary
    summary = GridCalParserSummary(
        raw_path=str(raw_path),
        psse_intermediate_counts=count_psse_intermediate(psse_circuit),
        multicircuit_counts=count_multicircuit(grid),
        parser_log=parser_log,
        record_type_mapping=build_record_type_mapping(),
        csv_files=csv_files,
        log_file=str(log_file_path),
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )

    summary_path = output_dir / "gridcal_summary.json"
    summary_dict = summary_to_dict(summary)
    summary_path.write_text(json.dumps(summary_dict, indent=2) + "\n", encoding="utf-8")

    print(f"Summary written to {summary_path}", file=sys.stderr)
    print(f"Exported {len(csv_files)} CSV file(s) to {output_dir}", file=sys.stderr)
    print(json.dumps(summary_dict, indent=2))
