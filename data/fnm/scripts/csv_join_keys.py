"""Supplemental CSV Join-Key Mapping.

Analyzes supplemental CSVs accompanying the CAISO FNM Annual S01 variant,
identifies columns that serve as join keys to PSS/E network elements in the
intermediate format tables, validates those joins against actual data, and
produces a structured mapping report (JSON + markdown).

This resolves OQ-E03 (join keys between supplemental CSVs and PSS/E network
elements).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Join key pattern registry
# ---------------------------------------------------------------------------


class JoinCardinality(Enum):
    """Cardinality of a join between a supplemental CSV and an intermediate format table."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "M:N"


class KeyType(Enum):
    """Classification of a join key column's semantic type."""

    BUS_NUMBER = "bus_number"
    GENERATOR_ID = "generator_id"
    GENERATOR_NAME = "generator_name"
    BRANCH_COMPOSITE = "branch_composite"
    TRANSFORMER_COMPOSITE = "transformer_composite"
    AREA_NUMBER = "area_number"
    ZONE_NUMBER = "zone_number"
    ELEMENT_NAME = "element_name"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Column name patterns for key discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyColumnPattern:
    """A pattern for discovering candidate join-key columns in supplemental CSVs.

    The discovery engine matches CSV column names against these patterns
    (case-insensitive substring or regex match) to identify candidate keys.
    """

    key_type: KeyType
    column_patterns: list[str]
    target_table: str
    target_columns: list[str]
    is_composite: bool = False


# ---------------------------------------------------------------------------
# Key discovery and validation results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateKey:
    """A candidate join key discovered in a supplemental CSV."""

    csv_file: str
    csv_columns: list[str]
    key_type: KeyType
    confidence: float


@dataclass(frozen=True)
class JoinValidationResult:
    """Result of validating a candidate key against an intermediate format table."""

    candidate: CandidateKey
    target_table: str
    target_columns: list[str]
    csv_row_count: int
    matched_row_count: int
    unmatched_row_count: int
    match_rate: float
    cardinality: JoinCardinality
    is_valid: bool
    unmatched_sample: list[dict[str, str]]
    notes: str = ""


# ---------------------------------------------------------------------------
# Per-CSV mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CsvJoinMapping:
    """Complete join-key mapping for a single supplemental CSV."""

    csv_file: str
    csv_columns: list[str]
    csv_row_count: int
    candidate_keys: list[CandidateKey]
    validated_joins: list[JoinValidationResult]
    primary_join: JoinValidationResult | None
    secondary_joins: list[JoinValidationResult]
    sample_rows: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Top-level mapping report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReportSummary:
    """Aggregate statistics for the join-key report."""

    total_csvs_analyzed: int
    total_valid_joins: int
    total_csvs_with_valid_join: int
    total_csvs_without_valid_join: int
    average_match_rate: float
    csvs_needing_review: list[str]


@dataclass(frozen=True)
class ReportMetadata:
    """Provenance metadata for the join-key report."""

    fnm_path: str = ""
    intermediate_dir: str = ""
    match_rate_threshold: float = 0.80
    report_timestamp: str = ""


@dataclass(frozen=True)
class JoinKeyReport:
    """Complete join-key mapping report for all supplemental CSVs."""

    csv_mappings: list[CsvJoinMapping]
    csvs_found: list[str]
    csvs_missing: list[str]
    intermediate_tables_used: list[str]
    overall_summary: ReportSummary
    metadata: ReportMetadata


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAISO_FNM_CSV_NAMES: list[str] = [
    "LINE_AND_TRANSFORMER.csv",
    "TRADING_HUB.csv",
    "GEN_DISTRIBUTION_FACTOR.csv",
    "CONTINGENCY.csv",
    "INTERFACE.csv",
    "INTERFACE_ELEMENT.csv",
    "OUTAGE.csv",
]


# ---------------------------------------------------------------------------
# Key pattern registry
# ---------------------------------------------------------------------------


def get_default_key_patterns() -> list[KeyColumnPattern]:
    """Return the default registry of join-key column patterns.

    Returns:
        List of KeyColumnPattern entries sorted by specificity (composite
        patterns first, then by number of column_patterns descending).
    """
    patterns = [
        KeyColumnPattern(
            key_type=KeyType.BRANCH_COMPOSITE,
            column_patterns=["from_bus", "to_bus", "ckt"],
            target_table="branch",
            target_columns=["I", "J", "CKT"],
            is_composite=True,
        ),
        KeyColumnPattern(
            key_type=KeyType.TRANSFORMER_COMPOSITE,
            column_patterns=["from_bus", "to_bus", "ckt"],
            target_table="transformer",
            target_columns=["I", "J", "K", "CKT"],
            is_composite=True,
        ),
        KeyColumnPattern(
            key_type=KeyType.GENERATOR_ID,
            column_patterns=["gen_bus", "machine_id", "gen_id", "generator_id"],
            target_table="generator",
            target_columns=["I", "ID"],
            is_composite=False,
        ),
        KeyColumnPattern(
            key_type=KeyType.GENERATOR_NAME,
            column_patterns=["gen_name", "generator_name", "unit_name"],
            target_table="generator",
            target_columns=["NAME"],
            is_composite=False,
        ),
        KeyColumnPattern(
            key_type=KeyType.BUS_NUMBER,
            column_patterns=[
                "bus_num",
                "bus_no",
                "busnum",
                "bus_number",
                "bus_i",
                "bus",
            ],
            target_table="bus",
            target_columns=["I"],
            is_composite=False,
        ),
        KeyColumnPattern(
            key_type=KeyType.AREA_NUMBER,
            column_patterns=["area_num", "area_number", "area_no", "area"],
            target_table="area",
            target_columns=["I"],
            is_composite=False,
        ),
        KeyColumnPattern(
            key_type=KeyType.ZONE_NUMBER,
            column_patterns=["zone_num", "zone_number", "zone_no", "zone"],
            target_table="zone",
            target_columns=["I"],
            is_composite=False,
        ),
    ]
    # Sort: composites first, then by number of column_patterns descending
    patterns.sort(key=lambda p: (not p.is_composite, -len(p.column_patterns)))
    return patterns


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------


def read_csv_header(csv_path: Path) -> list[str]:
    """Read the header row of a CSV file and return column names.

    Strips whitespace from column names. Handles BOM-prefixed files.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of column names in order.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty (no header row).
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"CSV file is empty (no header row): {csv_path}")

    return [col.strip() for col in header]


def read_csv_sample(csv_path: Path, n_rows: int = 100) -> list[dict[str, str]]:
    """Read up to n_rows of data from a CSV file.

    Returns rows as dicts mapping column name to string value. Does not
    attempt type conversion. Strips whitespace from both column names
    and values.

    Args:
        csv_path: Path to the CSV file.
        n_rows: Maximum number of data rows to read.

    Returns:
        List of row dicts, up to n_rows.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file has no data rows (header only).
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: list[dict[str, str]] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file is empty (no header row): {csv_path}")
        for i, row in enumerate(reader):
            if i >= n_rows:
                break
            rows.append({k.strip(): v.strip() if v else "" for k, v in row.items()})

    if not rows:
        raise ValueError(f"CSV file has no data rows (header only): {csv_path}")

    return rows


def read_csv_key_values(
    csv_path: Path,
    key_columns: list[str],
) -> list[tuple[str, ...]]:
    """Read all values for the specified key columns from a CSV file.

    Returns a list of tuples, one per data row, containing the string values
    of the specified columns in order.

    Args:
        csv_path: Path to the CSV file.
        key_columns: Column names to extract.

    Returns:
        List of key value tuples.

    Raises:
        FileNotFoundError: If the file does not exist.
        KeyError: If any specified column is not in the CSV header.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    result: list[tuple[str, ...]] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return result

        # Normalize fieldnames for matching
        raw_fields = [fn.strip() for fn in reader.fieldnames]
        for kc in key_columns:
            if kc not in raw_fields:
                raise KeyError(f"Column '{kc}' not found in CSV header: {raw_fields}")

        for row in reader:
            # Build normalized row
            norm_row = {k.strip(): v.strip() if v else "" for k, v in row.items()}
            result.append(tuple(norm_row[kc] for kc in key_columns))

    return result


# ---------------------------------------------------------------------------
# Intermediate format table reading
# ---------------------------------------------------------------------------


def load_intermediate_key_values(
    intermediate_dir: Path,
    table_name: str,
    key_columns: list[str],
) -> set[tuple[str, ...]]:
    """Load the set of valid key values from an intermediate format table.

    Reads the specified columns from the intermediate format CSV table
    (file named ``<table_name>.csv`` in ``intermediate_dir``) and returns
    a set of tuples representing the unique key values.

    Args:
        intermediate_dir: Path to the directory containing D7 intermediate
            format CSV tables.
        table_name: Table name (file stem, e.g., 'bus', 'generator', 'branch').
        key_columns: Column names to extract as the key.

    Returns:
        Set of key value tuples present in the intermediate table.

    Raises:
        FileNotFoundError: If the table file does not exist.
        KeyError: If any specified column is not in the table header.
    """
    table_path = intermediate_dir / f"{table_name}.csv"
    if not table_path.exists():
        raise FileNotFoundError(f"Intermediate table not found: {table_path}")

    result: set[tuple[str, ...]] = set()
    with open(table_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return result

        raw_fields = [fn.strip() for fn in reader.fieldnames]
        for kc in key_columns:
            if kc not in raw_fields:
                raise KeyError(
                    f"Column '{kc}' not found in intermediate table '{table_name}': {raw_fields}"
                )

        for row in reader:
            norm_row = {k.strip(): v.strip() if v else "" for k, v in row.items()}
            result.add(tuple(norm_row[kc] for kc in key_columns))

    return result


# ---------------------------------------------------------------------------
# Key discovery
# ---------------------------------------------------------------------------


def _match_column(csv_col: str, pattern: str) -> bool:
    """Check if a CSV column name matches a pattern (case-insensitive).

    Uses exact match after normalizing: lowercased, underscores/spaces/hyphens
    collapsed. Also matches if the pattern is a substring of the column name.
    """
    col_lower = csv_col.lower().replace("-", "_").replace(" ", "_")
    pat_lower = pattern.lower().replace("-", "_").replace(" ", "_")
    return pat_lower == col_lower or pat_lower in col_lower


def _find_matching_columns(
    csv_columns: list[str],
    pattern: str,
) -> list[str]:
    """Find CSV columns matching a pattern."""
    return [c for c in csv_columns if _match_column(c, pattern)]


def _values_look_numeric(sample: list[dict[str, str]], column: str) -> bool:
    """Check if sample values for a column look like integers."""
    for row in sample:
        val = row.get(column, "").strip()
        if val and not val.lstrip("-").isdigit():
            return False
    return True


def discover_candidate_keys(
    csv_file: str,
    csv_columns: list[str],
    csv_sample: list[dict[str, str]],
    key_patterns: list[KeyColumnPattern],
) -> list[CandidateKey]:
    """Discover candidate join keys in a supplemental CSV.

    For each key pattern in the registry:
    1. Check whether the CSV contains columns matching the pattern's
       ``column_patterns`` (case-insensitive substring match).
    2. For composite keys, all component columns must be present.
    3. Optionally inspect sample data values to boost confidence.
    4. Assign a confidence score based on match quality.

    Returns all candidate keys with confidence > 0.0, sorted by
    confidence descending.

    Args:
        csv_file: Name of the CSV file (for labeling).
        csv_columns: Column names from the CSV header.
        csv_sample: Sample data rows for value-based heuristics.
        key_patterns: Registry of key column patterns to match against.

    Returns:
        List of CandidateKey entries, sorted by confidence descending.
    """
    candidates: list[CandidateKey] = []

    for pattern in key_patterns:
        if pattern.is_composite:
            # All component patterns must match at least one column
            matched_cols: list[str] = []
            all_found = True
            for col_pat in pattern.column_patterns:
                matches = _find_matching_columns(csv_columns, col_pat)
                if matches:
                    matched_cols.append(matches[0])
                else:
                    all_found = False
                    break

            if not all_found:
                continue

            # Compute confidence
            confidence = 0.7  # base for composite match
            # Boost if numeric values where expected
            for col in matched_cols:
                if col != matched_cols[-1]:  # skip CKT (may be string)
                    if _values_look_numeric(csv_sample, col):
                        confidence = min(1.0, confidence + 0.1)

            candidates.append(
                CandidateKey(
                    csv_file=csv_file,
                    csv_columns=matched_cols,
                    key_type=pattern.key_type,
                    confidence=confidence,
                )
            )
        else:
            # Simple key: find any column matching any pattern
            for col_pat in pattern.column_patterns:
                matches = _find_matching_columns(csv_columns, col_pat)
                for matched_col in matches:
                    # Avoid matching a column already part of a composite
                    confidence = 0.6  # base for simple match
                    # Exact match gets higher confidence
                    if matched_col.lower() == col_pat.lower():
                        confidence = 0.8

                    # Boost for numeric values if bus/area/zone
                    if pattern.key_type in (
                        KeyType.BUS_NUMBER,
                        KeyType.AREA_NUMBER,
                        KeyType.ZONE_NUMBER,
                    ):
                        if _values_look_numeric(csv_sample, matched_col):
                            confidence = min(1.0, confidence + 0.15)

                    candidates.append(
                        CandidateKey(
                            csv_file=csv_file,
                            csv_columns=[matched_col],
                            key_type=pattern.key_type,
                            confidence=confidence,
                        )
                    )
                    break  # One match per pattern is enough

    # Deduplicate by csv_columns + key_type
    seen: set[tuple[tuple[str, ...], str]] = set()
    unique: list[CandidateKey] = []
    for c in candidates:
        key = (tuple(c.csv_columns), c.key_type.value)
        if key not in seen:
            seen.add(key)
            unique.append(c)

    unique.sort(key=lambda c: -c.confidence)
    return unique


# ---------------------------------------------------------------------------
# Join validation
# ---------------------------------------------------------------------------


def _determine_cardinality(
    csv_key_values: list[tuple[str, ...]],
    target_key_set: set[tuple[str, ...]],
) -> JoinCardinality:
    """Determine the join cardinality from key value distributions.

    Args:
        csv_key_values: All key value tuples from the CSV (with duplicates).
        target_key_set: Set of valid key value tuples from the target table.

    Returns:
        The inferred JoinCardinality.
    """
    csv_distinct = set(csv_key_values)
    matched_csv_distinct = csv_distinct & target_key_set

    if not matched_csv_distinct:
        return JoinCardinality.ONE_TO_ONE

    total_rows = len(csv_key_values)
    distinct_count = len(csv_distinct)

    # Multiple CSV rows per distinct key => many CSV rows map to one target
    has_csv_duplicates = total_rows > distinct_count

    # Check if distinct CSV keys map to more target keys than CSV keys
    # (not really possible with set intersection, so we focus on CSV side)
    matched_target_count = len(matched_csv_distinct)

    if has_csv_duplicates:
        if matched_target_count < distinct_count:
            return JoinCardinality.MANY_TO_MANY
        return JoinCardinality.MANY_TO_ONE
    else:
        if matched_target_count == distinct_count:
            return JoinCardinality.ONE_TO_ONE
        return JoinCardinality.ONE_TO_MANY


def validate_join(
    csv_path: Path,
    candidate: CandidateKey,
    intermediate_dir: Path,
    target_table: str,
    target_columns: list[str],
    match_threshold: float = 0.80,
) -> JoinValidationResult:
    """Validate a candidate join key against an intermediate format table.

    Args:
        csv_path: Path to the supplemental CSV file.
        candidate: The candidate key to validate.
        intermediate_dir: Path to D7 intermediate format tables.
        target_table: Intermediate table to join against.
        target_columns: Key columns in the target table.
        match_threshold: Minimum match_rate for the join to be valid.

    Returns:
        A JoinValidationResult with match statistics and cardinality.
    """
    csv_key_values = read_csv_key_values(csv_path, candidate.csv_columns)
    target_key_set = load_intermediate_key_values(intermediate_dir, target_table, target_columns)

    csv_row_count = len(csv_key_values)
    if csv_row_count == 0:
        return JoinValidationResult(
            candidate=candidate,
            target_table=target_table,
            target_columns=target_columns,
            csv_row_count=0,
            matched_row_count=0,
            unmatched_row_count=0,
            match_rate=0.0,
            cardinality=JoinCardinality.ONE_TO_ONE,
            is_valid=False,
            unmatched_sample=[],
            notes="CSV has no data rows.",
        )

    matched = 0
    unmatched_samples: list[dict[str, str]] = []

    for key_tuple in csv_key_values:
        if key_tuple in target_key_set:
            matched += 1
        else:
            if len(unmatched_samples) < 10:
                sample_dict = {col: val for col, val in zip(candidate.csv_columns, key_tuple)}
                unmatched_samples.append(sample_dict)

    unmatched = csv_row_count - matched
    match_rate = matched / csv_row_count

    cardinality = _determine_cardinality(csv_key_values, target_key_set)

    return JoinValidationResult(
        candidate=candidate,
        target_table=target_table,
        target_columns=target_columns,
        csv_row_count=csv_row_count,
        matched_row_count=matched,
        unmatched_row_count=unmatched,
        match_rate=match_rate,
        cardinality=cardinality,
        is_valid=match_rate >= match_threshold,
        unmatched_sample=unmatched_samples,
    )


# ---------------------------------------------------------------------------
# Per-CSV analysis
# ---------------------------------------------------------------------------


def analyze_csv(
    csv_path: Path,
    intermediate_dir: Path,
    key_patterns: list[KeyColumnPattern] | None = None,
    match_threshold: float = 0.80,
) -> CsvJoinMapping:
    """Analyze a single supplemental CSV for join keys.

    Orchestrates the full discovery-and-validation pipeline for one CSV:
    1. Read header and sample rows.
    2. Discover candidate keys using the pattern registry.
    3. Validate each candidate against the appropriate intermediate table.
    4. Select the primary join (highest match_rate among valid joins).
    5. Collect secondary valid joins.
    6. Return the complete CsvJoinMapping.

    Args:
        csv_path: Path to the supplemental CSV file.
        intermediate_dir: Path to D7 intermediate format tables.
        key_patterns: Optional custom key pattern registry.
        match_threshold: Minimum match_rate for join validity.

    Returns:
        A CsvJoinMapping with all discovery and validation results.
    """
    if key_patterns is None:
        key_patterns = get_default_key_patterns()

    csv_file = csv_path.name
    columns = read_csv_header(csv_path)

    try:
        sample = read_csv_sample(csv_path, n_rows=100)
    except ValueError:
        sample = []

    candidates = discover_candidate_keys(csv_file, columns, sample, key_patterns)

    # Validate each candidate
    validated: list[JoinValidationResult] = []
    for candidate in candidates:
        # Find the matching pattern to get target table/columns
        target_table = None
        target_columns = None
        for pat in key_patterns:
            if pat.key_type == candidate.key_type:
                target_table = pat.target_table
                target_columns = pat.target_columns
                break

        if target_table is None or target_columns is None:
            continue

        # Check if the intermediate table exists
        table_path = intermediate_dir / f"{target_table}.csv"
        if not table_path.exists():
            continue

        try:
            result = validate_join(
                csv_path,
                candidate,
                intermediate_dir,
                target_table,
                target_columns,
                match_threshold,
            )
            validated.append(result)
        except (FileNotFoundError, KeyError):
            continue

    # Select primary and secondary joins
    valid_joins = [v for v in validated if v.is_valid]
    valid_joins.sort(key=lambda v: -v.match_rate)

    primary = valid_joins[0] if valid_joins else None
    secondary = valid_joins[1:] if len(valid_joins) > 1 else []

    # Sample rows for documentation
    sample_rows = sample[:5] if sample else []

    # Count rows
    csv_row_count = len(sample)
    if sample:
        # Read actual row count
        try:
            all_keys = read_csv_key_values(csv_path, [columns[0]])
            csv_row_count = len(all_keys)
        except (KeyError, IndexError):
            pass

    return CsvJoinMapping(
        csv_file=csv_file,
        csv_columns=columns,
        csv_row_count=csv_row_count,
        candidate_keys=candidates,
        validated_joins=validated,
        primary_join=primary,
        secondary_joins=secondary,
        sample_rows=sample_rows,
    )


# ---------------------------------------------------------------------------
# Full report generation
# ---------------------------------------------------------------------------


def build_join_key_report(
    fnm_path: Path,
    intermediate_dir: Path,
    manifest_csv_names: list[str] | None = None,
    key_patterns: list[KeyColumnPattern] | None = None,
    match_threshold: float = 0.80,
) -> JoinKeyReport:
    """Build the complete join-key mapping report for all supplemental CSVs.

    Args:
        fnm_path: Resolved FNM_PATH directory containing supplemental CSVs.
        intermediate_dir: Path to D7 intermediate format tables.
        manifest_csv_names: Expected CSV file names (from D1 manifest).
        key_patterns: Optional custom key pattern registry.
        match_threshold: Minimum match_rate for join validity.

    Returns:
        A complete JoinKeyReport.
    """
    if manifest_csv_names is None:
        manifest_csv_names = CAISO_FNM_CSV_NAMES

    csvs_found: list[str] = []
    csvs_missing: list[str] = []

    for name in manifest_csv_names:
        if (fnm_path / name).exists():
            csvs_found.append(name)
        else:
            csvs_missing.append(name)

    # Analyze each found CSV
    mappings: list[CsvJoinMapping] = []
    tables_used: set[str] = set()

    for csv_name in csvs_found:
        csv_path = fnm_path / csv_name
        mapping = analyze_csv(csv_path, intermediate_dir, key_patterns, match_threshold)
        mappings.append(mapping)

        for vj in mapping.validated_joins:
            tables_used.add(vj.target_table)

    # Compute summary
    total_valid = sum(len([v for v in m.validated_joins if v.is_valid]) for m in mappings)
    csvs_with_valid = sum(1 for m in mappings if m.primary_join is not None)
    csvs_without_valid = len(mappings) - csvs_with_valid

    primary_rates = [m.primary_join.match_rate for m in mappings if m.primary_join is not None]
    avg_rate = sum(primary_rates) / len(primary_rates) if primary_rates else 0.0

    needing_review = [
        m.csv_file for m in mappings if m.primary_join is None or m.primary_join.match_rate < 0.90
    ]

    summary = ReportSummary(
        total_csvs_analyzed=len(mappings),
        total_valid_joins=total_valid,
        total_csvs_with_valid_join=csvs_with_valid,
        total_csvs_without_valid_join=csvs_without_valid,
        average_match_rate=avg_rate,
        csvs_needing_review=needing_review,
    )

    metadata = ReportMetadata(
        fnm_path=str(fnm_path),
        intermediate_dir=str(intermediate_dir),
        match_rate_threshold=match_threshold,
        report_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return JoinKeyReport(
        csv_mappings=mappings,
        csvs_found=csvs_found,
        csvs_missing=csvs_missing,
        intermediate_tables_used=sorted(tables_used),
        overall_summary=summary,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _serialize(obj: Any) -> Any:
    """Recursively serialize dataclasses, enums, and other types to JSON-safe values."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_serialize(item) for item in obj]
    if isinstance(obj, set):
        return sorted(_serialize(item) for item in obj)
    return obj


def report_to_dict(report: JoinKeyReport) -> dict:
    """Convert a JoinKeyReport to a JSON-serializable dict.

    All enum values are serialized as their string values. All dataclass
    fields are recursively converted.

    Args:
        report: The join-key report to serialize.

    Returns:
        A dict safe for JSON serialization.
    """
    return _serialize(report)


def report_to_markdown(report: JoinKeyReport) -> str:
    """Render a JoinKeyReport as a markdown document.

    Args:
        report: The join-key report to render.

    Returns:
        A complete markdown string.
    """
    lines: list[str] = []
    s = report.overall_summary

    lines.append("# Supplemental CSV Join-Key Mapping Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **CSVs analyzed:** {s.total_csvs_analyzed}")
    lines.append(f"- **Valid joins found:** {s.total_valid_joins}")
    lines.append(f"- **CSVs with valid join:** {s.total_csvs_with_valid_join}")
    lines.append(f"- **CSVs without valid join:** {s.total_csvs_without_valid_join}")
    lines.append(f"- **Average match rate:** {s.average_match_rate:.1%}")
    if s.csvs_needing_review:
        lines.append(f"- **CSVs needing review:** {', '.join(s.csvs_needing_review)}")
    lines.append("")

    # Per-CSV sections
    for mapping in report.csv_mappings:
        lines.append(f"## {mapping.csv_file}")
        lines.append("")
        lines.append(f"- **Row count:** {mapping.csv_row_count}")
        lines.append(f"- **Columns:** {', '.join(mapping.csv_columns)}")
        lines.append("")

        if mapping.primary_join:
            pj = mapping.primary_join
            lines.append("### Primary Join")
            lines.append("")
            lines.append(f"- **Target table:** {pj.target_table}")
            lines.append(
                f"- **Key columns:** {', '.join(pj.candidate.csv_columns)} "
                f"-> {', '.join(pj.target_columns)}"
            )
            lines.append(f"- **Cardinality:** {pj.cardinality.value}")
            lines.append(f"- **Match rate:** {pj.match_rate:.1%}")
            lines.append(f"- **Matched/Total:** {pj.matched_row_count}/{pj.csv_row_count}")
            lines.append("")

            if pj.unmatched_sample:
                lines.append("#### Unmatched Samples")
                lines.append("")
                for sample in pj.unmatched_sample[:5]:
                    lines.append(f"  - {sample}")
                lines.append("")

        if mapping.secondary_joins:
            lines.append("### Secondary Joins")
            lines.append("")
            for sj in mapping.secondary_joins:
                lines.append(
                    f"- **{sj.target_table}** via "
                    f"{', '.join(sj.candidate.csv_columns)}: "
                    f"{sj.match_rate:.1%} match rate, "
                    f"{sj.cardinality.value}"
                )
            lines.append("")

        if not mapping.primary_join and not mapping.secondary_joins:
            lines.append("*No valid join keys identified.*")
            lines.append("")

    # Aggregate table
    lines.append("## Join Summary Table")
    lines.append("")
    lines.append("| CSV File | Primary Join Target | Key Columns | Cardinality | Match Rate |")
    lines.append("|----------|-------------------|-------------|-------------|------------|")
    for mapping in report.csv_mappings:
        if mapping.primary_join:
            pj = mapping.primary_join
            lines.append(
                f"| {mapping.csv_file} | {pj.target_table} | "
                f"{', '.join(pj.candidate.csv_columns)} | "
                f"{pj.cardinality.value} | {pj.match_rate:.1%} |"
            )
        else:
            lines.append(f"| {mapping.csv_file} | — | — | — | — |")
    lines.append("")

    # Missing CSVs
    if report.csvs_missing:
        lines.append("## Missing CSVs")
        lines.append("")
        for name in report.csvs_missing:
            lines.append(f"- {name}")
        lines.append("")

    # Methodology
    lines.append("## Methodology")
    lines.append("")
    lines.append(f"- **Match rate threshold:** {report.metadata.match_rate_threshold:.0%}")
    lines.append("- **Discovery:** Column name pattern matching (case-insensitive)")
    lines.append("- **Cardinality:** Inferred from CSV key value distribution vs target table")
    lines.append(f"- **Report generated:** {report.metadata.report_timestamp}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the supplemental CSV join-key mapping.

    Args:
        argv: Command-line arguments. If ``None``, reads from ``sys.argv[1:]``.
    """
    import sys

    parser = argparse.ArgumentParser(
        description="Analyze supplemental CSV join keys against intermediate format tables."
    )
    parser.add_argument(
        "--fnm-path",
        type=Path,
        default=None,
        help="Path to FNM data directory. Falls back to FNM_PATH env var.",
    )
    parser.add_argument(
        "--intermediate-dir",
        type=Path,
        default=Path("data/fnm/intermediate/canonical"),
        help="Path to intermediate format tables directory.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/fnm/intermediate/csv_join_keys"),
        help="Output directory for report files.",
    )
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=0.80,
        help="Minimum match rate for a join to be valid (default: 0.80).",
    )

    args = parser.parse_args(argv)

    fnm_path = args.fnm_path
    if fnm_path is None:
        env_val = os.environ.get("FNM_PATH")
        if env_val is None:
            print("Error: --fnm-path not provided and FNM_PATH env var not set.", file=sys.stderr)
            sys.exit(2)
        fnm_path = Path(env_val)

    fnm_path = fnm_path.expanduser().resolve()
    if not fnm_path.is_dir():
        print(f"Error: FNM path is not a directory: {fnm_path}", file=sys.stderr)
        sys.exit(2)

    intermediate_dir = args.intermediate_dir.resolve()
    if not intermediate_dir.is_dir():
        print(
            f"Error: Intermediate directory not found: {intermediate_dir}",
            file=sys.stderr,
        )
        sys.exit(2)

    report = build_join_key_report(
        fnm_path=fnm_path,
        intermediate_dir=intermediate_dir,
        match_threshold=args.match_threshold,
    )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_path = output_dir / "join_key_report.json"
    json_path.write_text(json.dumps(report_to_dict(report), indent=2) + "\n", encoding="utf-8")

    # Write markdown
    md_path = output_dir / "join_key_report.md"
    md_path.write_text(report_to_markdown(report), encoding="utf-8")

    print(f"Report written to {output_dir}")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")

    # Exit code 1 if any CSV has no valid join
    has_failures = any(m.primary_join is None for m in report.csv_mappings)
    if has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
