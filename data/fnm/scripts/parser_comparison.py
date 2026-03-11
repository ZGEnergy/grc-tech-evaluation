"""Parser fidelity comparison and canonical parser selection.

Compares parser outputs from D3 (raw record counter), D4 (MATPOWER), and
D5 (GridCal) to assess which parser most faithfully preserves the original
PSS/E v31 data. Produces a structured comparison report with fidelity scores
and a selection recommendation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DiscrepancyType(str, Enum):
    """Classification of a record-count discrepancy between raw and parsed data."""

    MATCH = "MATCH"
    DATA_LOSS = "DATA_LOSS"
    PHANTOM_INSERTION = "PHANTOM_INSERTION"
    STRUCTURAL_TRANSFORM = "STRUCTURAL_TRANSFORM"
    COLLAPSED = "COLLAPSED"
    RECORD_TYPE_MISSING = "RECORD_TYPE_MISSING"


class ParserName(str, Enum):
    """Identifier for each parser under evaluation."""

    MATPOWER = "MATPOWER"
    GRIDCAL = "GRIDCAL"


class SelectionRationale(str, Enum):
    """Reason for the canonical parser selection decision."""

    CLEAR_WINNER = "CLEAR_WINNER"
    TIER1_TIEBREAK = "TIER1_TIEBREAK"
    PHANTOM_TIEBREAK = "PHANTOM_TIEBREAK"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecordCountComparison:
    """Per-record-type count comparison between raw and both parsers.

    Attributes:
        psse_section: PSS/E v31 section name (e.g. ``"Bus"``).
        raw_count: Record count from the raw record counter (D3).
        matpower_count: Record count from MATPOWER parser (D4), or None if missing.
        gridcal_count: Record count from GridCal parser (D5), or None if missing.
        matpower_discrepancy: Discrepancy classification for MATPOWER.
        gridcal_discrepancy: Discrepancy classification for GridCal.
    """

    psse_section: str
    raw_count: int
    matpower_count: int | None
    gridcal_count: int | None
    matpower_discrepancy: DiscrepancyType
    gridcal_discrepancy: DiscrepancyType


@dataclass(frozen=True)
class FieldCoverageEntry:
    """Per-record-type field coverage comparison between parsers.

    Attributes:
        psse_section: PSS/E v31 section name.
        psse_fields: Expected PSS/E v31 field names for this section.
        matpower_fields: Column names from MATPOWER CSV output.
        gridcal_fields: Column names from GridCal CSV output.
        common_fields: Fields present in both parser outputs (by mapping).
        matpower_only: Fields present only in MATPOWER output.
        gridcal_only: Fields present only in GridCal output.
        matpower_coverage: Fraction of PSS/E fields covered by MATPOWER.
        gridcal_coverage: Fraction of PSS/E fields covered by GridCal.
    """

    psse_section: str
    psse_fields: list[str]
    matpower_fields: list[str]
    gridcal_fields: list[str]
    common_fields: list[str]
    matpower_only: list[str]
    gridcal_only: list[str]
    matpower_coverage: float
    gridcal_coverage: float


@dataclass(frozen=True)
class DataLossEntry:
    """A single data loss instance identified during comparison.

    Attributes:
        psse_section: PSS/E v31 section name where the loss occurred.
        parser: Which parser exhibits the loss.
        loss_type: The type of discrepancy (DATA_LOSS, RECORD_TYPE_MISSING, etc.).
        raw_count: Expected count from the raw file.
        parser_count: Actual count from the parser, or None if the record type is missing.
        delta: Difference (parser_count - raw_count), or None.
        description: Human-readable explanation.
    """

    psse_section: str
    parser: ParserName
    loss_type: DiscrepancyType
    raw_count: int
    parser_count: int | None
    delta: int | None
    description: str


@dataclass(frozen=True)
class FidelityScore:
    """Per-parser fidelity score with component breakdown.

    Attributes:
        parser: Which parser this score belongs to.
        overall: Weighted composite fidelity score in [0, 1].
        field_coverage: Average field coverage across all record types.
        record_type_coverage: Fraction of PSS/E record types present in parser output.
        tier1_field_coverage: Coverage of tier-1 critical fields.
        record_count_accuracy: Fraction of record types with exact count match.
        phantom_count: Number of PHANTOM_INSERTION discrepancies.
    """

    parser: ParserName
    overall: float
    field_coverage: float
    record_type_coverage: float
    tier1_field_coverage: float
    record_count_accuracy: float
    phantom_count: int


@dataclass(frozen=True)
class CanonicalParserSelection:
    """Selection decision for the canonical parser.

    Attributes:
        selected: The chosen parser.
        rationale: The reason for the selection.
        matpower_score: Overall fidelity score for MATPOWER.
        gridcal_score: Overall fidelity score for GridCal.
        score_diff: Absolute difference between the two scores.
        explanation: Human-readable explanation of the decision.
    """

    selected: ParserName
    rationale: SelectionRationale
    matpower_score: float
    gridcal_score: float
    score_diff: float
    explanation: str


@dataclass(frozen=True)
class ComparisonMetadata:
    """Provenance information for the comparison report.

    Attributes:
        timestamp: ISO-8601 timestamp of the comparison run.
        raw_counts_path: Path to the D3 raw counts JSON.
        matpower_summary_path: Path to the D4 MATPOWER summary JSON.
        gridcal_summary_path: Path to the D5 GridCal summary JSON.
        matpower_csv_dir: Path to the MATPOWER CSV output directory.
        gridcal_csv_dir: Path to the GridCal CSV output directory.
    """

    timestamp: str
    raw_counts_path: str
    matpower_summary_path: str
    gridcal_summary_path: str
    matpower_csv_dir: str
    gridcal_csv_dir: str


@dataclass(frozen=True)
class ParserComparisonReport:
    """Complete parser fidelity comparison report.

    Attributes:
        metadata: Provenance information.
        record_counts: Per-record-type count comparisons.
        field_coverage: Per-record-type field coverage comparisons.
        data_loss_inventory: All identified data loss instances.
        matpower_fidelity: Fidelity score for MATPOWER.
        gridcal_fidelity: Fidelity score for GridCal.
        selection: Canonical parser selection decision.
    """

    metadata: ComparisonMetadata
    record_counts: list[RecordCountComparison]
    field_coverage: list[FieldCoverageEntry]
    data_loss_inventory: list[DataLossEntry]
    matpower_fidelity: FidelityScore
    gridcal_fidelity: FidelityScore
    selection: CanonicalParserSelection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIER1_CRITICAL_FIELDS: dict[str, list[str]] = {
    "Bus": ["I", "NAME", "BASKV", "IDE", "AREA", "ZONE", "VM", "VA"],
    "Load": ["I", "ID", "STATUS", "PL", "QL"],
    "Generator": ["I", "ID", "PG", "QG", "QT", "QB", "VS", "MBASE"],
    "Branch": ["I", "J", "CKT", "R", "X", "B", "RATEA", "RATEB", "RATEC"],
    "Transformer": ["I", "J", "K", "CKT", "CW", "CZ", "CM", "R1-2", "X1-2", "WINDV1", "WINDV2"],
    "Switched Shunt": ["I", "MODSW", "VSWHI", "VSWLO", "BINIT"],
    "Area": ["I", "ISW", "PDES", "PTOL", "ARNAM"],
    "Fixed Shunt": ["I", "ID", "STATUS", "GL", "BL"],
}


# ---------------------------------------------------------------------------
# PSS/E v31 Field Specification
# ---------------------------------------------------------------------------


def get_psse_v31_field_spec() -> dict[str, list[str]]:
    """Return PSS/E v31 field names per record type.

    Returns:
        Dict mapping PSS/E section name to list of field names.
    """
    return {
        "Bus": [
            "I",
            "NAME",
            "BASKV",
            "IDE",
            "AREA",
            "ZONE",
            "OWNER",
            "VM",
            "VA",
            "GL",
            "BL",
            "NVHI",
            "NVLO",
        ],
        "Load": [
            "I",
            "ID",
            "STATUS",
            "AREA",
            "ZONE",
            "PL",
            "QL",
            "IP",
            "IQ",
            "YP",
            "YQ",
            "OWNER",
            "SCALE",
        ],
        "Fixed Shunt": ["I", "ID", "STATUS", "GL", "BL"],
        "Generator": [
            "I",
            "ID",
            "PG",
            "QG",
            "QT",
            "QB",
            "VS",
            "IREG",
            "MBASE",
            "ZR",
            "ZX",
            "RT",
            "XT",
            "GTAP",
            "STAT",
            "RMPCT",
            "PT",
            "PB",
            "O1",
            "F1",
            "O2",
            "F2",
            "O3",
            "F3",
            "O4",
            "F4",
            "WMOD",
            "WPF",
        ],
        "Branch": [
            "I",
            "J",
            "CKT",
            "R",
            "X",
            "B",
            "RATEA",
            "RATEB",
            "RATEC",
            "GI",
            "BI",
            "GJ",
            "BJ",
            "ST",
            "LEN",
            "O1",
            "F1",
            "O2",
            "F2",
            "O3",
            "F3",
            "O4",
            "F4",
        ],
        "Transformer": [
            "I",
            "J",
            "K",
            "CKT",
            "CW",
            "CZ",
            "CM",
            "MAG1",
            "MAG2",
            "NMETR",
            "NAME",
            "STAT",
            "O1",
            "F1",
            "O2",
            "F2",
            "O3",
            "F3",
            "O4",
            "F4",
            "R1-2",
            "X1-2",
            "SBASE1-2",
            "WINDV1",
            "NOMV1",
            "ANG1",
            "RATA1",
            "RATB1",
            "RATC1",
            "COD1",
            "CONT1",
            "RMA1",
            "RMI1",
            "VMA1",
            "VMI1",
            "NTP1",
            "TAB1",
            "CR1",
            "CX1",
            "WINDV2",
            "NOMV2",
        ],
        "Area": ["I", "ISW", "PDES", "PTOL", "ARNAM"],
        "Two-Terminal DC": [
            "NAME",
            "MDC",
            "RDC",
            "SETEFX",
            "VSCHD",
            "VCMOD",
            "RCOMP",
            "DELTI",
            "METER",
            "DCVMIN",
            "CCCITMX",
            "CCCACC",
            "IPR",
            "NBR",
            "ANMXR",
            "ANMNR",
            "RCR",
            "XCR",
            "EBASR",
            "TRR",
            "TAPR",
            "TMXR",
            "TMNR",
            "STPR",
            "ICR",
            "IFR",
            "ITR",
            "IDR",
            "XCAPR",
            "IPI",
            "NBI",
            "ANMXI",
            "ANMNI",
            "RCI",
            "XCI",
            "EBASI",
            "TRI",
            "TAPI",
            "TMXI",
            "TMNI",
            "STPI",
            "ICI",
            "IFI",
            "ITI",
            "IDI",
            "XCAPI",
        ],
        "VSC DC": [
            "NAME",
            "MDC",
            "RDC",
            "O1",
            "F1",
            "O2",
            "F2",
            "O3",
            "F3",
            "O4",
            "F4",
            "IBUS1",
            "TYPE1",
            "MODE1",
            "DCSET1",
            "ACSET1",
            "ALOSS1",
            "BLOSS1",
            "MINLOSS1",
            "SMAX1",
            "IMAX1",
            "PWF1",
            "MAXQ1",
            "MINQ1",
            "REMOT1",
            "RMPCT1",
        ],
        "Impedance Correction": ["T1", "F1", "T2", "F2", "T3", "F3"],
        "Multi-Terminal DC": ["NAME", "NCONV", "NDCBS", "NDCLN"],
        "Multi-Section Line": ["I", "J", "ID", "MET", "DUM1"],
        "Zone": ["I", "ZONAME"],
        "Interarea Transfer": ["ARFROM", "ARTO", "TRID", "PTRAN"],
        "Owner": ["I", "OWNAME"],
        "FACTS": [
            "NAME",
            "I",
            "J",
            "MODE",
            "PDES",
            "QDES",
            "VSET",
            "SHMX",
            "TRMX",
            "VTMN",
            "VTMX",
            "VSMX",
            "IMX",
            "LINX",
            "RMPCT",
            "OWNER",
            "SET1",
            "SET2",
            "VSREF",
        ],
        "Switched Shunt": [
            "I",
            "MODSW",
            "ADJM",
            "STAT",
            "VSWHI",
            "VSWLO",
            "SWREM",
            "RMPCT",
            "RMIDNT",
            "BINIT",
            "N1",
            "B1",
            "N2",
            "B2",
            "N3",
            "B3",
            "N4",
            "B4",
            "N5",
            "B5",
            "N6",
            "B6",
            "N7",
            "B7",
            "N8",
            "B8",
        ],
    }


# ---------------------------------------------------------------------------
# Record-Type Mapping
# ---------------------------------------------------------------------------

# PSS/E section name -> (matpower table name or None, gridcal table name or None)
_PSSE_TO_PARSER_TABLE: dict[str, tuple[str | None, str | None]] = {
    "Bus": ("bus", "buses"),
    "Load": (None, "loads"),  # MATPOWER folds loads into bus
    "Fixed Shunt": (None, "shunts"),  # MATPOWER folds into bus
    "Generator": ("gen", "generators"),
    "Branch": ("branch", "lines"),
    "Transformer": ("branch", "transformers2w"),  # MATPOWER merges into branch
    "Area": ("areas", "areas"),
    "Two-Terminal DC": ("dcline", "hvdc_lines"),
    "VSC DC": (None, "vsc_devices"),
    "Impedance Correction": (None, None),
    "Multi-Terminal DC": (None, None),
    "Multi-Section Line": (None, None),
    "Zone": (None, "zones"),
    "Interarea Transfer": (None, None),
    "Owner": (None, None),
    "FACTS": (None, "facts_devices"),
    "Switched Shunt": (None, "controllable_shunts"),
}


def build_record_type_mapping() -> dict[str, tuple[str | None, str | None]]:
    """Return PSS/E section to parser table name mapping.

    Returns:
        Dict mapping PSS/E section name to a tuple of
        (matpower_table_name, gridcal_table_name). None means the parser
        does not produce a separate table for that record type.
    """
    return dict(_PSSE_TO_PARSER_TABLE)


def build_field_name_mapping() -> dict[str, dict[str, str]]:
    """Return PSS/E field to parser column name mapping.

    This is a best-effort mapping of canonical PSS/E field names to the
    column names used by each parser. Only covers commonly-mapped fields.

    Returns:
        Dict mapping PSS/E section name to a dict of
        {psse_field: parser_column_name} for each parser. The inner dict
        keys are PSS/E field names, values are lowercase parser column names.
    """
    # For the purpose of comparison, we map key PSS/E fields to lowercase
    # column names that the parsers tend to use. This mapping is approximate.
    return {
        "Bus": {
            "I": "bus_i",
            "NAME": "name",
            "BASKV": "base_kv",
            "IDE": "type",
            "AREA": "area",
            "ZONE": "zone",
            "VM": "vm",
            "VA": "va",
        },
        "Generator": {
            "I": "bus",
            "PG": "pg",
            "QG": "qg",
            "QT": "qmax",
            "QB": "qmin",
            "VS": "vs",
            "MBASE": "mbase",
        },
        "Branch": {
            "I": "fbus",
            "J": "tbus",
            "R": "r",
            "X": "x",
            "B": "b",
            "RATEA": "rate_a",
            "RATEB": "rate_b",
            "RATEC": "rate_c",
        },
    }


# ---------------------------------------------------------------------------
# Load Functions
# ---------------------------------------------------------------------------


def load_raw_counts(path: str | Path) -> dict[str, int]:
    """Load D3 raw record counter JSON and return section counts.

    Args:
        path: Path to the D3 JSON output file.

    Returns:
        Dict mapping PSS/E section name to record count.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("section_counts", {}))


def load_parser_summary(path: str | Path) -> dict[str, int]:
    """Load D4 (MATPOWER) or D5 (GridCal) summary JSON and return record counts.

    For MATPOWER, reads ``log.field_counts_csv``.
    For GridCal, reads ``multicircuit_counts``.

    Args:
        path: Path to the parser summary JSON file.

    Returns:
        Dict mapping table/collection name to record count.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    # Try MATPOWER format first
    if "log" in data and "field_counts_csv" in data.get("log", {}):
        return dict(data["log"]["field_counts_csv"])

    # Try GridCal format
    if "multicircuit_counts" in data:
        return {k: v for k, v in data["multicircuit_counts"].items() if v > 0}

    # Fallback: return top-level dict if it looks like counts
    return {k: v for k, v in data.items() if isinstance(v, int)}


def load_csv_columns(csv_dir: str | Path) -> dict[str, list[str]]:
    """Read CSV headers from a directory of parser output CSVs.

    Recognizes both ``mpc_*.csv`` (MATPOWER) and ``gridcal_*.csv`` (GridCal) naming.

    Args:
        csv_dir: Directory containing CSV files.

    Returns:
        Dict mapping table name to list of column header strings.
    """
    import csv
    import re

    csv_dir = Path(csv_dir)
    result: dict[str, list[str]] = {}

    if not csv_dir.is_dir():
        return result

    for csv_path in sorted(csv_dir.glob("*.csv")):
        # Extract table name from filename
        match = re.match(r"(?:mpc_|gridcal_)(.+)\.csv$", csv_path.name)
        if not match:
            # Try bare name
            table_name = csv_path.stem
        else:
            table_name = match.group(1)

        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    result[table_name] = [col.strip() for col in header]
        except (OSError, StopIteration):
            pass

    return result


# ---------------------------------------------------------------------------
# Comparison Functions
# ---------------------------------------------------------------------------


def compare_record_counts(
    raw: dict[str, int],
    matpower: dict[str, int],
    gridcal: dict[str, int],
    mapping: dict[str, tuple[str | None, str | None]],
) -> list[RecordCountComparison]:
    """Compare record counts from raw (D3) against both parsers.

    Args:
        raw: PSS/E section name to count from D3.
        matpower: MATPOWER table name to count from D4.
        gridcal: GridCal collection name to count from D5.
        mapping: PSS/E section to (matpower_table, gridcal_table) mapping.

    Returns:
        List of RecordCountComparison, one per PSS/E section in ``raw``.
    """
    comparisons: list[RecordCountComparison] = []

    for section, raw_count in raw.items():
        mp_table, gc_table = mapping.get(section, (None, None))

        # MATPOWER count
        mp_count: int | None = None
        if mp_table is not None and mp_table in matpower:
            mp_count = matpower[mp_table]

        # GridCal count
        gc_count: int | None = None
        if gc_table is not None and gc_table in gridcal:
            gc_count = gridcal[gc_table]

        mp_disc = _classify_count_discrepancy(raw_count, mp_count, mp_table)
        gc_disc = _classify_count_discrepancy(raw_count, gc_count, gc_table)

        comparisons.append(
            RecordCountComparison(
                psse_section=section,
                raw_count=raw_count,
                matpower_count=mp_count,
                gridcal_count=gc_count,
                matpower_discrepancy=mp_disc,
                gridcal_discrepancy=gc_disc,
            )
        )

    return comparisons


def _classify_count_discrepancy(
    raw_count: int,
    parser_count: int | None,
    table_name: str | None,
) -> DiscrepancyType:
    """Classify a single count discrepancy."""
    if table_name is None:
        # Parser has no table for this record type
        if raw_count > 0:
            return DiscrepancyType.RECORD_TYPE_MISSING
        return DiscrepancyType.MATCH

    if parser_count is None:
        if raw_count > 0:
            return DiscrepancyType.RECORD_TYPE_MISSING
        return DiscrepancyType.MATCH

    if parser_count == raw_count:
        return DiscrepancyType.MATCH
    elif parser_count < raw_count:
        return DiscrepancyType.DATA_LOSS
    else:
        return DiscrepancyType.PHANTOM_INSERTION


def compare_field_coverage(
    psse_spec: dict[str, list[str]],
    matpower_columns: dict[str, list[str]],
    gridcal_columns: dict[str, list[str]],
    mapping: dict[str, tuple[str | None, str | None]],
) -> list[FieldCoverageEntry]:
    """Compare field coverage of each parser against the PSS/E v31 specification.

    Args:
        psse_spec: PSS/E section to list of expected field names.
        matpower_columns: MATPOWER table to list of CSV column names.
        gridcal_columns: GridCal table to list of CSV column names.
        mapping: PSS/E section to (matpower_table, gridcal_table) mapping.

    Returns:
        List of FieldCoverageEntry, one per PSS/E section in ``psse_spec``.
    """
    entries: list[FieldCoverageEntry] = []

    for section, psse_fields in psse_spec.items():
        mp_table, gc_table = mapping.get(section, (None, None))

        mp_fields = matpower_columns.get(mp_table, []) if mp_table else []
        gc_fields = gridcal_columns.get(gc_table, []) if gc_table else []

        # Compute sets (case-insensitive)
        mp_set = {f.lower() for f in mp_fields}
        gc_set = {f.lower() for f in gc_fields}
        common = sorted(mp_set & gc_set)
        mp_only = sorted(mp_set - gc_set)
        gc_only = sorted(gc_set - mp_set)

        n_psse = len(psse_fields) if psse_fields else 1
        mp_coverage = len(mp_set) / n_psse if mp_set else 0.0
        gc_coverage = len(gc_set) / n_psse if gc_set else 0.0

        entries.append(
            FieldCoverageEntry(
                psse_section=section,
                psse_fields=list(psse_fields),
                matpower_fields=list(mp_fields),
                gridcal_fields=list(gc_fields),
                common_fields=common,
                matpower_only=mp_only,
                gridcal_only=gc_only,
                matpower_coverage=min(mp_coverage, 1.0),
                gridcal_coverage=min(gc_coverage, 1.0),
            )
        )

    return entries


def build_data_loss_inventory(
    counts: list[RecordCountComparison],
    fields: list[FieldCoverageEntry],
) -> list[DataLossEntry]:
    """Build an inventory of all data loss instances from count and field comparisons.

    Args:
        counts: Record count comparisons from ``compare_record_counts``.
        fields: Field coverage entries from ``compare_field_coverage``.

    Returns:
        List of DataLossEntry for every non-MATCH discrepancy.
    """
    inventory: list[DataLossEntry] = []

    for c in counts:
        for parser, disc, p_count in [
            (ParserName.MATPOWER, c.matpower_discrepancy, c.matpower_count),
            (ParserName.GRIDCAL, c.gridcal_discrepancy, c.gridcal_count),
        ]:
            if disc == DiscrepancyType.MATCH:
                continue

            delta = (p_count - c.raw_count) if p_count is not None else None
            desc = _describe_loss(c.psse_section, parser, disc, c.raw_count, p_count)
            inventory.append(
                DataLossEntry(
                    psse_section=c.psse_section,
                    parser=parser,
                    loss_type=disc,
                    raw_count=c.raw_count,
                    parser_count=p_count,
                    delta=delta,
                    description=desc,
                )
            )

    return inventory


def _describe_loss(
    section: str,
    parser: ParserName,
    disc: DiscrepancyType,
    raw_count: int,
    parser_count: int | None,
) -> str:
    """Generate a human-readable description for a data loss entry."""
    if disc == DiscrepancyType.RECORD_TYPE_MISSING:
        return f"{parser.value} has no table for {section} ({raw_count} raw records lost)."
    if disc == DiscrepancyType.DATA_LOSS:
        return (
            f"{parser.value} has {parser_count} records for {section} "
            f"vs {raw_count} raw (lost {raw_count - (parser_count or 0)})."
        )
    if disc == DiscrepancyType.PHANTOM_INSERTION:
        return (
            f"{parser.value} has {parser_count} records for {section} "
            f"vs {raw_count} raw (phantom +{(parser_count or 0) - raw_count})."
        )
    return f"{parser.value} {section}: {disc.value}"


# ---------------------------------------------------------------------------
# Fidelity Scoring
# ---------------------------------------------------------------------------

_W_FIELD_COVERAGE = 0.35
_W_RECORD_TYPE_COVERAGE = 0.30
_W_TIER1_FIELD_COVERAGE = 0.20
_W_RECORD_COUNT_ACCURACY = 0.15


def compute_fidelity_score(
    parser: ParserName,
    counts: list[RecordCountComparison],
    fields: list[FieldCoverageEntry],
    losses: list[DataLossEntry],
    psse_spec: dict[str, list[str]],
    tier1: dict[str, list[str]],
) -> FidelityScore:
    """Compute a composite fidelity score for a single parser.

    Weights: 0.35 field_coverage + 0.30 record_type_coverage
             + 0.20 tier1_field_coverage + 0.15 record_count_accuracy

    Args:
        parser: Which parser to score.
        counts: Record count comparisons.
        fields: Field coverage entries.
        losses: Data loss inventory.
        psse_spec: PSS/E v31 field specification.
        tier1: Tier-1 critical fields per section.

    Returns:
        FidelityScore with all component scores.
    """
    # 1. Field coverage: average coverage across sections that have parser fields
    if parser == ParserName.MATPOWER:
        cov_values = [f.matpower_coverage for f in fields]
    else:
        cov_values = [f.gridcal_coverage for f in fields]
    field_cov = sum(cov_values) / len(cov_values) if cov_values else 0.0

    # 2. Record type coverage: fraction of raw sections that have a parser table
    total_raw_sections = len([c for c in counts if c.raw_count > 0])
    if total_raw_sections > 0:
        if parser == ParserName.MATPOWER:
            present = len(
                [
                    c
                    for c in counts
                    if c.raw_count > 0
                    and c.matpower_discrepancy != DiscrepancyType.RECORD_TYPE_MISSING
                ]
            )
        else:
            present = len(
                [
                    c
                    for c in counts
                    if c.raw_count > 0
                    and c.gridcal_discrepancy != DiscrepancyType.RECORD_TYPE_MISSING
                ]
            )
        rt_cov = present / total_raw_sections
    else:
        rt_cov = 1.0

    # 3. Tier-1 field coverage: fraction of tier-1 fields covered
    tier1_total = 0
    tier1_covered = 0
    for section, t1_fields in tier1.items():
        tier1_total += len(t1_fields)
        # Find the matching field coverage entry
        for f in fields:
            if f.psse_section == section:
                if parser == ParserName.MATPOWER:
                    parser_fields_lower = {x.lower() for x in f.matpower_fields}
                else:
                    parser_fields_lower = {x.lower() for x in f.gridcal_fields}
                for t1f in t1_fields:
                    if t1f.lower() in parser_fields_lower:
                        tier1_covered += 1
                break
    tier1_cov = tier1_covered / tier1_total if tier1_total > 0 else 0.0

    # 4. Record count accuracy: fraction of sections with exact match
    if parser == ParserName.MATPOWER:
        matches = len([c for c in counts if c.matpower_discrepancy == DiscrepancyType.MATCH])
    else:
        matches = len([c for c in counts if c.gridcal_discrepancy == DiscrepancyType.MATCH])
    rc_acc = matches / len(counts) if counts else 1.0

    # Phantom count
    if parser == ParserName.MATPOWER:
        phantoms = len(
            [c for c in counts if c.matpower_discrepancy == DiscrepancyType.PHANTOM_INSERTION]
        )
    else:
        phantoms = len(
            [c for c in counts if c.gridcal_discrepancy == DiscrepancyType.PHANTOM_INSERTION]
        )

    overall = (
        _W_FIELD_COVERAGE * field_cov
        + _W_RECORD_TYPE_COVERAGE * rt_cov
        + _W_TIER1_FIELD_COVERAGE * tier1_cov
        + _W_RECORD_COUNT_ACCURACY * rc_acc
    )

    return FidelityScore(
        parser=parser,
        overall=round(overall, 6),
        field_coverage=round(field_cov, 6),
        record_type_coverage=round(rt_cov, 6),
        tier1_field_coverage=round(tier1_cov, 6),
        record_count_accuracy=round(rc_acc, 6),
        phantom_count=phantoms,
    )


# ---------------------------------------------------------------------------
# Selection Logic
# ---------------------------------------------------------------------------


def select_canonical_parser(
    mp_score: FidelityScore,
    gc_score: FidelityScore,
) -> CanonicalParserSelection:
    """Select the canonical parser based on fidelity scores.

    Decision tree:
    1. |diff| > 0.05 -> CLEAR_WINNER
    2. tier1 diff > 0.02 -> TIER1_TIEBREAK
    3. phantom count differs -> PHANTOM_TIEBREAK (fewer phantoms wins)
    4. else -> MANUAL_REQUIRED

    Args:
        mp_score: Fidelity score for MATPOWER.
        gc_score: Fidelity score for GridCal.

    Returns:
        CanonicalParserSelection with the decision.
    """
    diff = abs(mp_score.overall - gc_score.overall)

    # 1. Clear winner
    if diff > 0.05:
        winner = ParserName.MATPOWER if mp_score.overall > gc_score.overall else ParserName.GRIDCAL
        return CanonicalParserSelection(
            selected=winner,
            rationale=SelectionRationale.CLEAR_WINNER,
            matpower_score=mp_score.overall,
            gridcal_score=gc_score.overall,
            score_diff=round(diff, 6),
            explanation=(
                f"{winner.value} wins with overall score "
                f"{max(mp_score.overall, gc_score.overall):.4f} "
                f"vs {min(mp_score.overall, gc_score.overall):.4f} "
                f"(diff={diff:.4f} > 0.05)."
            ),
        )

    # 2. Tier-1 tiebreak
    tier1_diff = abs(mp_score.tier1_field_coverage - gc_score.tier1_field_coverage)
    if tier1_diff > 0.02:
        winner = (
            ParserName.MATPOWER
            if mp_score.tier1_field_coverage > gc_score.tier1_field_coverage
            else ParserName.GRIDCAL
        )
        return CanonicalParserSelection(
            selected=winner,
            rationale=SelectionRationale.TIER1_TIEBREAK,
            matpower_score=mp_score.overall,
            gridcal_score=gc_score.overall,
            score_diff=round(diff, 6),
            explanation=(
                f"Overall scores tied (diff={diff:.4f}). "
                f"{winner.value} wins on tier-1 field coverage "
                f"({max(mp_score.tier1_field_coverage, gc_score.tier1_field_coverage):.4f} "
                f"vs {min(mp_score.tier1_field_coverage, gc_score.tier1_field_coverage):.4f})."
            ),
        )

    # 3. Phantom tiebreak
    if mp_score.phantom_count != gc_score.phantom_count:
        winner = (
            ParserName.MATPOWER
            if mp_score.phantom_count < gc_score.phantom_count
            else ParserName.GRIDCAL
        )
        return CanonicalParserSelection(
            selected=winner,
            rationale=SelectionRationale.PHANTOM_TIEBREAK,
            matpower_score=mp_score.overall,
            gridcal_score=gc_score.overall,
            score_diff=round(diff, 6),
            explanation=(
                f"Overall and tier-1 scores tied. "
                f"{winner.value} wins with fewer phantom insertions "
                f"({min(mp_score.phantom_count, gc_score.phantom_count)} "
                f"vs {max(mp_score.phantom_count, gc_score.phantom_count)})."
            ),
        )

    # 4. Manual required
    return CanonicalParserSelection(
        selected=ParserName.GRIDCAL,  # Default to GridCal if truly tied
        rationale=SelectionRationale.MANUAL_REQUIRED,
        matpower_score=mp_score.overall,
        gridcal_score=gc_score.overall,
        score_diff=round(diff, 6),
        explanation=(
            "Scores, tier-1 coverage, and phantom counts are all tied. Manual review required."
        ),
    )


# ---------------------------------------------------------------------------
# Report Building
# ---------------------------------------------------------------------------


def build_comparison_report(
    raw_path: str | Path,
    mp_path: str | Path,
    gc_path: str | Path,
    mp_csvs: str | Path,
    gc_csvs: str | Path,
) -> ParserComparisonReport:
    """Build a complete comparison report from D3/D4/D5 output files.

    Args:
        raw_path: Path to D3 raw counts JSON.
        mp_path: Path to D4 MATPOWER summary JSON.
        gc_path: Path to D5 GridCal summary JSON.
        mp_csvs: Path to MATPOWER CSV output directory.
        gc_csvs: Path to GridCal CSV output directory.

    Returns:
        A fully populated ParserComparisonReport.
    """
    raw_counts = load_raw_counts(raw_path)
    mp_counts = load_parser_summary(mp_path)
    gc_counts = load_parser_summary(gc_path)

    mp_columns = load_csv_columns(mp_csvs)
    gc_columns = load_csv_columns(gc_csvs)

    mapping = build_record_type_mapping()
    psse_spec = get_psse_v31_field_spec()
    tier1 = TIER1_CRITICAL_FIELDS

    record_counts = compare_record_counts(raw_counts, mp_counts, gc_counts, mapping)
    field_coverage = compare_field_coverage(psse_spec, mp_columns, gc_columns, mapping)
    data_losses = build_data_loss_inventory(record_counts, field_coverage)

    mp_fidelity = compute_fidelity_score(
        ParserName.MATPOWER, record_counts, field_coverage, data_losses, psse_spec, tier1
    )
    gc_fidelity = compute_fidelity_score(
        ParserName.GRIDCAL, record_counts, field_coverage, data_losses, psse_spec, tier1
    )

    selection = select_canonical_parser(mp_fidelity, gc_fidelity)

    metadata = ComparisonMetadata(
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        raw_counts_path=str(raw_path),
        matpower_summary_path=str(mp_path),
        gridcal_summary_path=str(gc_path),
        matpower_csv_dir=str(mp_csvs),
        gridcal_csv_dir=str(gc_csvs),
    )

    return ParserComparisonReport(
        metadata=metadata,
        record_counts=record_counts,
        field_coverage=field_coverage,
        data_loss_inventory=data_losses,
        matpower_fidelity=mp_fidelity,
        gridcal_fidelity=gc_fidelity,
        selection=selection,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def report_to_dict(report: ParserComparisonReport) -> dict:
    """Convert a ParserComparisonReport to a JSON-serializable dict.

    Args:
        report: The comparison report.

    Returns:
        A dict suitable for ``json.dumps()``.
    """
    return {
        "metadata": {
            "timestamp": report.metadata.timestamp,
            "raw_counts_path": report.metadata.raw_counts_path,
            "matpower_summary_path": report.metadata.matpower_summary_path,
            "gridcal_summary_path": report.metadata.gridcal_summary_path,
            "matpower_csv_dir": report.metadata.matpower_csv_dir,
            "gridcal_csv_dir": report.metadata.gridcal_csv_dir,
        },
        "record_counts": [
            {
                "psse_section": c.psse_section,
                "raw_count": c.raw_count,
                "matpower_count": c.matpower_count,
                "gridcal_count": c.gridcal_count,
                "matpower_discrepancy": c.matpower_discrepancy.value,
                "gridcal_discrepancy": c.gridcal_discrepancy.value,
            }
            for c in report.record_counts
        ],
        "field_coverage": [
            {
                "psse_section": f.psse_section,
                "psse_fields": f.psse_fields,
                "matpower_fields": f.matpower_fields,
                "gridcal_fields": f.gridcal_fields,
                "common_fields": f.common_fields,
                "matpower_only": f.matpower_only,
                "gridcal_only": f.gridcal_only,
                "matpower_coverage": f.matpower_coverage,
                "gridcal_coverage": f.gridcal_coverage,
            }
            for f in report.field_coverage
        ],
        "data_loss_inventory": [
            {
                "psse_section": d.psse_section,
                "parser": d.parser.value,
                "loss_type": d.loss_type.value,
                "raw_count": d.raw_count,
                "parser_count": d.parser_count,
                "delta": d.delta,
                "description": d.description,
            }
            for d in report.data_loss_inventory
        ],
        "matpower_fidelity": _fidelity_to_dict(report.matpower_fidelity),
        "gridcal_fidelity": _fidelity_to_dict(report.gridcal_fidelity),
        "selection": {
            "selected": report.selection.selected.value,
            "rationale": report.selection.rationale.value,
            "matpower_score": report.selection.matpower_score,
            "gridcal_score": report.selection.gridcal_score,
            "score_diff": report.selection.score_diff,
            "explanation": report.selection.explanation,
        },
    }


def _fidelity_to_dict(score: FidelityScore) -> dict:
    """Convert a FidelityScore to a JSON-serializable dict."""
    return {
        "parser": score.parser.value,
        "overall": score.overall,
        "field_coverage": score.field_coverage,
        "record_type_coverage": score.record_type_coverage,
        "tier1_field_coverage": score.tier1_field_coverage,
        "record_count_accuracy": score.record_count_accuracy,
        "phantom_count": score.phantom_count,
    }


def report_to_markdown(report: ParserComparisonReport) -> str:
    """Render a ParserComparisonReport as a Markdown document.

    Args:
        report: The comparison report.

    Returns:
        A Markdown string.
    """
    lines: list[str] = []
    lines.append("# Parser Fidelity Comparison Report")
    lines.append("")
    lines.append(f"**Generated:** {report.metadata.timestamp}")
    lines.append("")

    # Selection summary
    sel = report.selection
    lines.append("## Canonical Parser Selection")
    lines.append("")
    lines.append(f"- **Selected:** {sel.selected.value}")
    lines.append(f"- **Rationale:** {sel.rationale.value}")
    lines.append(f"- **Score diff:** {sel.score_diff:.4f}")
    lines.append(f"- **Explanation:** {sel.explanation}")
    lines.append("")

    # Fidelity scores
    lines.append("## Fidelity Scores")
    lines.append("")
    lines.append("| Component | MATPOWER | GridCal |")
    lines.append("|-----------|----------|---------|")
    mp = report.matpower_fidelity
    gc = report.gridcal_fidelity
    lines.append(f"| Overall | {mp.overall:.4f} | {gc.overall:.4f} |")
    lines.append(f"| Field Coverage | {mp.field_coverage:.4f} | {gc.field_coverage:.4f} |")
    lines.append(
        f"| Record Type Coverage | {mp.record_type_coverage:.4f} | {gc.record_type_coverage:.4f} |"
    )
    lines.append(
        f"| Tier-1 Field Coverage | {mp.tier1_field_coverage:.4f} | {gc.tier1_field_coverage:.4f} |"
    )
    lines.append(
        f"| Record Count Accuracy | {mp.record_count_accuracy:.4f} "
        f"| {gc.record_count_accuracy:.4f} |"
    )
    lines.append(f"| Phantom Insertions | {mp.phantom_count} | {gc.phantom_count} |")
    lines.append("")

    # Record counts
    lines.append("## Record Count Comparison")
    lines.append("")
    lines.append("| Section | Raw | MATPOWER | GridCal | MP Status | GC Status |")
    lines.append("|---------|-----|----------|---------|-----------|-----------|")
    for c in report.record_counts:
        mp_val = str(c.matpower_count) if c.matpower_count is not None else "-"
        gc_val = str(c.gridcal_count) if c.gridcal_count is not None else "-"
        lines.append(
            f"| {c.psse_section} | {c.raw_count} | {mp_val} | {gc_val} "
            f"| {c.matpower_discrepancy.value} | {c.gridcal_discrepancy.value} |"
        )
    lines.append("")

    # Data loss inventory
    if report.data_loss_inventory:
        lines.append("## Data Loss Inventory")
        lines.append("")
        for d in report.data_loss_inventory:
            lines.append(f"- **{d.psse_section}** ({d.parser.value}): {d.description}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for parser comparison.

    Usage::

        python -m fnm.scripts.parser_comparison \\
            --raw-counts d3_counts.json \\
            --matpower-summary d4_summary.json \\
            --gridcal-summary d5_summary.json \\
            --matpower-csvs /path/to/matpower/csvs \\
            --gridcal-csvs /path/to/gridcal/csvs \\
            [-o output.json] [--markdown output.md]
    """
    parser = argparse.ArgumentParser(
        description="Compare MATPOWER and GridCal parser fidelity against raw PSS/E counts."
    )
    parser.add_argument("--raw-counts", required=True, help="Path to D3 raw counts JSON")
    parser.add_argument(
        "--matpower-summary", required=True, help="Path to D4 MATPOWER summary JSON"
    )
    parser.add_argument("--gridcal-summary", required=True, help="Path to D5 GridCal summary JSON")
    parser.add_argument(
        "--matpower-csvs", required=True, help="Path to MATPOWER CSV output directory"
    )
    parser.add_argument(
        "--gridcal-csvs", required=True, help="Path to GridCal CSV output directory"
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Output JSON file path (default: stdout)"
    )
    parser.add_argument("--markdown", default=None, help="Output Markdown file path")

    args = parser.parse_args(argv)

    report = build_comparison_report(
        raw_path=args.raw_counts,
        mp_path=args.matpower_summary,
        gc_path=args.gridcal_summary,
        mp_csvs=args.matpower_csvs,
        gc_csvs=args.gridcal_csvs,
    )

    result_dict = report_to_dict(report)
    json_text = json.dumps(result_dict, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(json_text, encoding="utf-8")
        print(f"JSON report written to {args.output}", file=sys.stderr)
    else:
        print(json_text)

    if args.markdown:
        md_text = report_to_markdown(report)
        Path(args.markdown).write_text(md_text, encoding="utf-8")
        print(f"Markdown report written to {args.markdown}", file=sys.stderr)
