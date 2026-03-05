"""Referential Integrity Checks across augmented dataset files (PRD 05/02).

Validates cross-file ID consistency for all three networks (TINY, SMALL, MEDIUM).
Each check loads pairs of files, extracts ID columns, and computes set differences
to identify orphaned references (IDs in the referencing file that do not appear in
the target file). Pure check functions accept parsed data; a thin orchestration layer
handles file I/O and MATPOWER .m parsing.

Checks cover seven cross-file reference paths:
  1. Bus references (load, wind, solar, BESS, DR CSVs -> .m bus table)
  2. Generator references (temporal params, eligibility, scenarios -> .m gen table)
  3. Branch references (flowgates -> .m branch table)
  4. Reserve-to-temporal-params linkage
  5. BESS reserve-to-definition linkage
  6. DR bus load validation (nonzero Pd)
  7. Scenario-to-forecast generator alignment
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NETWORK_M_FILE_NAMES: dict[str, str] = {
    "case39": "case39.m",
    "ACTIVSg2000": "case_ACTIVSg2000.m",
    "ACTIVSg10k": "case_ACTIVSg10k.m",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers for the three tiers under validation."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class CheckStatus(StrEnum):
    """Outcome of a single referential integrity check."""

    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class ReferenceDirection(StrEnum):
    """Which file is the source and which is the target of the reference."""

    FORWARD = "forward"
    REVERSE = "reverse"


@dataclass(frozen=True)
class OrphanedReference:
    """A single ID that failed referential integrity."""

    id_value: int | str
    source_file: str
    target_file: str
    context: str


@dataclass(frozen=True)
class IntegrityCheckResult:
    """Result of a single referential integrity check."""

    check_name: str
    description: str
    status: CheckStatus
    source_file: str
    target_file: str
    total_ids_checked: int
    orphaned_ids: list[OrphanedReference]
    skip_reason: str | None = None


@dataclass(frozen=True)
class NetworkIntegrityReport:
    """Aggregated referential integrity results for one network."""

    network_id: NetworkId
    checks: list[IntegrityCheckResult]
    total_checks: int
    passed: int
    failed: int
    skipped: int


@dataclass(frozen=True)
class ReferentialIntegrityReport:
    """Top-level report across all three networks."""

    networks: list[NetworkIntegrityReport]
    total_checks: int
    total_passed: int
    total_failed: int
    total_skipped: int
    all_passed: bool


@dataclass(frozen=True)
class MFileIdSets:
    """Extracted ID sets from a cleaned MATPOWER .m file."""

    bus_ids: set[int]
    gen_indices: set[int]
    gen_bus_ids: list[int]
    branch_indices: set[int]
    branch_from_bus: list[int]
    branch_to_bus: list[int]
    bus_pd: dict[int, float]


@dataclass(frozen=True)
class CsvIdSet:
    """ID column values extracted from a single CSV file."""

    file_path: str
    id_column_name: str
    ids: set[int | str]


# ---------------------------------------------------------------------------
# MATPOWER .m file parsing
# ---------------------------------------------------------------------------

_BLOCK_RE = re.compile(
    r"mpc\.(\w+)\s*=\s*\[([^\]]*)\]",
    re.DOTALL,
)


def _extract_matrix_block(text: str, field_name: str) -> str:
    """Extract the content between [ ] for mpc.<field_name>."""
    pattern = re.compile(
        rf"mpc\.{re.escape(field_name)}\s*=\s*\[([^\]]*)\]",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        msg = f"Could not locate mpc.{field_name} block"
        raise ValueError(msg)
    return match.group(1)


def _parse_numeric_rows(block_text: str) -> list[list[float]]:
    """Parse semicolon-delimited rows of numeric values from a MATPOWER matrix block."""
    rows: list[list[float]] = []
    for line in block_text.split(";"):
        line = line.strip()
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        values = line.split()
        try:
            rows.append([float(v) for v in values])
        except ValueError:
            continue
    return rows


def parse_m_file_ids(m_file_path: Path) -> MFileIdSets:
    """Extract bus, generator, and branch ID sets from a cleaned MATPOWER .m file.

    Parses the .m file to extract the bus data matrix (mpc.bus), generator
    data matrix (mpc.gen), and branch data matrix (mpc.branch). From these,
    extracts:
    - bus_ids: set of integer bus IDs (column 0 of mpc.bus)
    - gen_indices: set of 0-based integer row indices into mpc.gen
    - gen_bus_ids: list mapping gen index to bus ID (column 0 of mpc.gen)
    - branch_indices: set of 0-based integer row indices into mpc.branch
    - branch endpoint bus IDs: columns 0 and 1 of mpc.branch
    - bus_pd: dict mapping bus_id to Pd value (column 2 of mpc.bus)

    Args:
        m_file_path: Path to the cleaned .m file.

    Returns:
        MFileIdSets containing all extracted ID sets.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If the .m file cannot be parsed.
    """
    text = m_file_path.read_text()

    # Parse bus matrix
    bus_block = _extract_matrix_block(text, "bus")
    bus_rows = _parse_numeric_rows(bus_block)

    bus_ids: set[int] = set()
    bus_pd: dict[int, float] = {}
    for row in bus_rows:
        if len(row) < 3:
            msg = f"Bus row has {len(row)} columns, expected at least 3"
            raise ValueError(msg)
        bid = int(row[0])
        bus_ids.add(bid)
        bus_pd[bid] = row[2]

    # Parse gen matrix
    gen_block = _extract_matrix_block(text, "gen")
    gen_rows = _parse_numeric_rows(gen_block)

    gen_indices: set[int] = set()
    gen_bus_ids: list[int] = []
    for i, row in enumerate(gen_rows):
        if len(row) < 1:
            msg = f"Gen row {i} has no columns"
            raise ValueError(msg)
        gen_indices.add(i)
        gen_bus_ids.append(int(row[0]))

    # Parse branch matrix
    branch_block = _extract_matrix_block(text, "branch")
    branch_rows = _parse_numeric_rows(branch_block)

    branch_indices: set[int] = set()
    branch_from_bus: list[int] = []
    branch_to_bus: list[int] = []
    for i, row in enumerate(branch_rows):
        if len(row) < 2:
            msg = f"Branch row {i} has {len(row)} columns, expected at least 2"
            raise ValueError(msg)
        branch_indices.add(i)
        branch_from_bus.append(int(row[0]))
        branch_to_bus.append(int(row[1]))

    return MFileIdSets(
        bus_ids=bus_ids,
        gen_indices=gen_indices,
        gen_bus_ids=gen_bus_ids,
        branch_indices=branch_indices,
        branch_from_bus=branch_from_bus,
        branch_to_bus=branch_to_bus,
        bus_pd=bus_pd,
    )


# ---------------------------------------------------------------------------
# CSV ID extraction
# ---------------------------------------------------------------------------


def extract_csv_ids(
    csv_path: Path,
    id_column: str,
    *,
    cast_to_int: bool = True,
) -> CsvIdSet:
    """Extract the set of unique IDs from a single column of a CSV file.

    Args:
        csv_path: Path to the CSV file.
        id_column: Name of the column to extract IDs from.
        cast_to_int: If True, cast ID values to int. If False, keep as str.

    Returns:
        CsvIdSet with the extracted unique IDs.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        KeyError: If id_column is not present in the CSV header.
        ValueError: If cast_to_int is True but values cannot be parsed as int.
    """
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or id_column not in reader.fieldnames:
        msg = f"Column '{id_column}' not found in {csv_path}"
        raise KeyError(msg)

    ids: set[int | str] = set()
    for row in reader:
        val = row[id_column].strip()
        if cast_to_int:
            ids.add(int(float(val)))
        else:
            ids.add(val)

    return CsvIdSet(
        file_path=str(csv_path),
        id_column_name=id_column,
        ids=ids,
    )


# ---------------------------------------------------------------------------
# Core check primitive
# ---------------------------------------------------------------------------


def check_ids_exist(
    source: CsvIdSet,
    target_ids: AbstractSet[int | str],
    target_file: str,
    *,
    check_name: str,
    description: str,
) -> IntegrityCheckResult:
    """Check that every ID in source exists in target_ids.

    Args:
        source: The CsvIdSet containing IDs to validate.
        target_ids: The set of valid IDs from the target file.
        target_file: Human-readable name of the target file (for reporting).
        check_name: Machine-readable check name for the result.
        description: Human-readable description for the result.

    Returns:
        IntegrityCheckResult with PASS if set difference is empty, FAIL otherwise.
    """
    orphaned = source.ids - target_ids
    orphaned_refs = [
        OrphanedReference(
            id_value=oid,
            source_file=source.file_path,
            target_file=target_file,
            context=f"column={source.id_column_name}",
        )
        for oid in sorted(orphaned, key=str)
    ]

    status = CheckStatus.PASS if not orphaned_refs else CheckStatus.FAIL
    return IntegrityCheckResult(
        check_name=check_name,
        description=description,
        status=status,
        source_file=source.file_path,
        target_file=target_file,
        total_ids_checked=len(source.ids),
        orphaned_ids=orphaned_refs,
    )


# ---------------------------------------------------------------------------
# Bus reference checks
# ---------------------------------------------------------------------------


def check_bus_references(
    m_ids: MFileIdSets,
    csv_files: list[tuple[Path, str]],
    network_id: NetworkId,
) -> list[IntegrityCheckResult]:
    """Check that bus IDs in all bus-referencing CSV files exist in the .m bus table.

    Args:
        m_ids: Extracted ID sets from the cleaned .m file.
        csv_files: List of (csv_path, id_column_name) pairs to check.
        network_id: Network being validated (for reporting).

    Returns:
        List of IntegrityCheckResult, one per CSV file.
    """
    results: list[IntegrityCheckResult] = []
    for csv_path, id_col in csv_files:
        fname = csv_path.name
        check_name = f"bus_ids_in_{fname.replace('.csv', '')}"

        if not csv_path.exists():
            results.append(
                IntegrityCheckResult(
                    check_name=check_name,
                    description=f"Bus IDs in {fname} exist in .m bus table",
                    status=CheckStatus.SKIPPED,
                    source_file=str(csv_path),
                    target_file=f"{network_id.value}.m",
                    total_ids_checked=0,
                    orphaned_ids=[],
                    skip_reason=f"File not found: {csv_path}",
                )
            )
            continue

        try:
            csv_ids = extract_csv_ids(csv_path, id_col, cast_to_int=True)
        except (KeyError, ValueError) as exc:
            results.append(
                IntegrityCheckResult(
                    check_name=check_name,
                    description=f"Bus IDs in {fname} exist in .m bus table",
                    status=CheckStatus.SKIPPED,
                    source_file=str(csv_path),
                    target_file=f"{network_id.value}.m",
                    total_ids_checked=0,
                    orphaned_ids=[],
                    skip_reason=f"Error reading {csv_path}: {exc}",
                )
            )
            continue

        result = check_ids_exist(
            source=csv_ids,
            target_ids=m_ids.bus_ids,
            target_file=f"{network_id.value}.m (bus table)",
            check_name=check_name,
            description=f"Bus IDs in {fname} exist in .m bus table",
        )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Generator reference checks
# ---------------------------------------------------------------------------


def _build_gen_uid_set(m_ids: MFileIdSets, network_id: NetworkId) -> set[int | str]:
    """Build the set of valid gen_uid strings from the .m file gen table.

    Generator UIDs follow the convention bus_{bus}_gen_{idx} where idx is
    the 0-based row index.

    Args:
        m_ids: Extracted ID sets from the .m file.
        network_id: Network identifier.

    Returns:
        Set of valid gen_uid strings.
    """
    uids: set[int | str] = set()
    for idx in sorted(m_ids.gen_indices):
        bus_id = m_ids.gen_bus_ids[idx]
        uid = f"bus_{bus_id}_gen_{idx}"
        uids.add(uid)
    return uids


def check_generator_references(
    m_ids: MFileIdSets,
    csv_files: list[tuple[Path, str]],
    network_id: NetworkId,
) -> list[IntegrityCheckResult]:
    """Check that generator IDs in gen-referencing CSV files exist in the .m gen table.

    Args:
        m_ids: Extracted ID sets from the cleaned .m file.
        csv_files: List of (csv_path, id_column_name) pairs to check.
        network_id: Network being validated (for reporting).

    Returns:
        List of IntegrityCheckResult, one per CSV file.
    """
    valid_gen_uids = _build_gen_uid_set(m_ids, network_id)

    results: list[IntegrityCheckResult] = []
    for csv_path, id_col in csv_files:
        fname = csv_path.name
        check_name = f"gen_ids_in_{fname.replace('.csv', '')}"

        if not csv_path.exists():
            results.append(
                IntegrityCheckResult(
                    check_name=check_name,
                    description=f"Generator IDs in {fname} exist in .m gen table",
                    status=CheckStatus.SKIPPED,
                    source_file=str(csv_path),
                    target_file=f"{network_id.value}.m",
                    total_ids_checked=0,
                    orphaned_ids=[],
                    skip_reason=f"File not found: {csv_path}",
                )
            )
            continue

        try:
            csv_ids = extract_csv_ids(csv_path, id_col, cast_to_int=False)
        except (KeyError, ValueError) as exc:
            results.append(
                IntegrityCheckResult(
                    check_name=check_name,
                    description=f"Generator IDs in {fname} exist in .m gen table",
                    status=CheckStatus.SKIPPED,
                    source_file=str(csv_path),
                    target_file=f"{network_id.value}.m",
                    total_ids_checked=0,
                    orphaned_ids=[],
                    skip_reason=f"Error reading {csv_path}: {exc}",
                )
            )
            continue

        result = check_ids_exist(
            source=csv_ids,
            target_ids=valid_gen_uids,
            target_file=f"{network_id.value}.m (gen table)",
            check_name=check_name,
            description=f"Generator IDs in {fname} exist in .m gen table",
        )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Branch reference checks
# ---------------------------------------------------------------------------


def check_branch_references(
    m_ids: MFileIdSets,
    flowgates_path: Path,
    branch_id_column: str,
    network_id: NetworkId,
) -> IntegrityCheckResult:
    """Check that branch IDs in flowgates.csv exist in the .m branch table.

    Flowgates store branch indices as semicolon-delimited lists in the line_ids
    column. This function parses those lists and checks each index against
    m_ids.branch_indices.

    Args:
        m_ids: Extracted ID sets from the cleaned .m file.
        flowgates_path: Path to flowgates.csv.
        branch_id_column: Column name containing branch indices in flowgates.csv.
        network_id: Network being validated (for reporting).

    Returns:
        IntegrityCheckResult. SKIPPED if flowgates.csv does not exist.
    """
    check_name = "branch_ids_in_flowgates"
    fname = flowgates_path.name

    if not flowgates_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description=f"Branch IDs in {fname} exist in .m branch table",
            status=CheckStatus.SKIPPED,
            source_file=str(flowgates_path),
            target_file=f"{network_id.value}.m",
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {flowgates_path}",
        )

    text = flowgates_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    all_branch_ids: set[int] = set()
    orphaned_refs: list[OrphanedReference] = []

    for row in reader:
        flowgate_id = row.get("flowgate_id", "unknown")
        line_ids_str = row[branch_id_column].strip()
        if not line_ids_str:
            continue

        for bid_str in line_ids_str.split(";"):
            bid_str = bid_str.strip()
            if not bid_str:
                continue
            bid = int(float(bid_str))
            all_branch_ids.add(bid)
            if bid not in m_ids.branch_indices:
                orphaned_refs.append(
                    OrphanedReference(
                        id_value=bid,
                        source_file=str(flowgates_path),
                        target_file=f"{network_id.value}.m (branch table)",
                        context=f"flowgate_id={flowgate_id}",
                    )
                )

    status = CheckStatus.PASS if not orphaned_refs else CheckStatus.FAIL
    return IntegrityCheckResult(
        check_name=check_name,
        description=f"Branch IDs in {fname} exist in .m branch table",
        status=status,
        source_file=str(flowgates_path),
        target_file=f"{network_id.value}.m (branch table)",
        total_ids_checked=len(all_branch_ids),
        orphaned_ids=orphaned_refs,
    )


# ---------------------------------------------------------------------------
# Reserve-to-temporal-params linkage
# ---------------------------------------------------------------------------


def check_reserve_temporal_linkage(
    reserve_path: Path,
    temporal_path: Path,
    gen_id_column: str,
    network_id: NetworkId,
) -> IntegrityCheckResult:
    """Check that every reserve-eligible generator has a gen_temporal_params entry.

    Extracts generator IDs from reserve_eligibility.csv (filtering to rows
    where spinning_eligible or non_spinning_eligible is True) and verifies
    each appears in gen_temporal_params.csv.

    Args:
        reserve_path: Path to reserve_eligibility.csv.
        temporal_path: Path to gen_temporal_params.csv.
        gen_id_column: Column name for generator ID in both files.
        network_id: Network being validated (for reporting).

    Returns:
        IntegrityCheckResult. SKIPPED if either file does not exist.
    """
    check_name = "reserve_temporal_linkage"

    if not reserve_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description="Reserve-eligible generators have temporal params entries",
            status=CheckStatus.SKIPPED,
            source_file=str(reserve_path),
            target_file=str(temporal_path),
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {reserve_path}",
        )

    if not temporal_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description="Reserve-eligible generators have temporal params entries",
            status=CheckStatus.SKIPPED,
            source_file=str(reserve_path),
            target_file=str(temporal_path),
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {temporal_path}",
        )

    # Extract reserve-eligible gen IDs
    reserve_text = reserve_path.read_text(encoding="utf-8")
    reserve_reader = csv.DictReader(io.StringIO(reserve_text))

    eligible_ids: set[str] = set()
    for row in reserve_reader:
        spin = row.get("spinning_eligible", "").strip().lower()
        nonspin = row.get("non_spinning_eligible", "").strip().lower()
        if spin in ("true", "1") or nonspin in ("true", "1"):
            eligible_ids.add(row[gen_id_column].strip())

    # Extract temporal params gen IDs
    temporal_text = temporal_path.read_text(encoding="utf-8")
    temporal_reader = csv.DictReader(io.StringIO(temporal_text))
    temporal_ids: set[str] = set()
    for row in temporal_reader:
        temporal_ids.add(row[gen_id_column].strip())

    # Check eligible IDs against temporal params
    orphaned = eligible_ids - temporal_ids
    orphaned_refs = [
        OrphanedReference(
            id_value=oid,
            source_file=str(reserve_path),
            target_file=str(temporal_path),
            context="reserve-eligible but missing temporal params",
        )
        for oid in sorted(orphaned)
    ]

    status = CheckStatus.PASS if not orphaned_refs else CheckStatus.FAIL
    return IntegrityCheckResult(
        check_name=check_name,
        description="Reserve-eligible generators have temporal params entries",
        status=status,
        source_file=str(reserve_path),
        target_file=str(temporal_path),
        total_ids_checked=len(eligible_ids),
        orphaned_ids=orphaned_refs,
    )


# ---------------------------------------------------------------------------
# BESS reserve-to-definition linkage
# ---------------------------------------------------------------------------


def check_bess_reserve_linkage(
    reserve_path: Path,
    bess_path: Path,
    network_id: NetworkId,
) -> IntegrityCheckResult:
    """Check that BESS unit IDs in reserve_eligibility.csv match bess_units.csv.

    Extracts BESS-related entries from reserve_eligibility.csv (identified
    by gen_uid prefix "BESS_") and verifies each unit_id exists in bess_units.csv.

    Args:
        reserve_path: Path to reserve_eligibility.csv.
        bess_path: Path to bess_units.csv.
        network_id: Network being validated (for reporting).

    Returns:
        IntegrityCheckResult. SKIPPED if either file does not exist.
    """
    check_name = "bess_reserve_linkage"

    if not reserve_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description="BESS unit IDs in reserve eligibility match bess_units.csv",
            status=CheckStatus.SKIPPED,
            source_file=str(reserve_path),
            target_file=str(bess_path),
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {reserve_path}",
        )

    if not bess_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description="BESS unit IDs in reserve eligibility match bess_units.csv",
            status=CheckStatus.SKIPPED,
            source_file=str(reserve_path),
            target_file=str(bess_path),
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {bess_path}",
        )

    # Extract BESS gen_uids from reserve eligibility
    reserve_text = reserve_path.read_text(encoding="utf-8")
    reserve_reader = csv.DictReader(io.StringIO(reserve_text))

    bess_reserve_ids: set[str] = set()
    for row in reserve_reader:
        gen_uid = row["gen_uid"].strip()
        if gen_uid.startswith("BESS_"):
            bess_reserve_ids.add(gen_uid)

    # Extract BESS unit_ids from bess_units.csv
    bess_text = bess_path.read_text(encoding="utf-8")
    bess_reader = csv.DictReader(io.StringIO(bess_text))
    bess_unit_ids: set[str] = set()
    for row in bess_reader:
        bess_unit_ids.add(row["unit_id"].strip())

    # Check
    orphaned = bess_reserve_ids - bess_unit_ids
    orphaned_refs = [
        OrphanedReference(
            id_value=oid,
            source_file=str(reserve_path),
            target_file=str(bess_path),
            context="BESS unit in reserve eligibility but not in bess_units.csv",
        )
        for oid in sorted(orphaned)
    ]

    status = CheckStatus.PASS if not orphaned_refs else CheckStatus.FAIL
    return IntegrityCheckResult(
        check_name=check_name,
        description="BESS unit IDs in reserve eligibility match bess_units.csv",
        status=status,
        source_file=str(reserve_path),
        target_file=str(bess_path),
        total_ids_checked=len(bess_reserve_ids),
        orphaned_ids=orphaned_refs,
    )


# ---------------------------------------------------------------------------
# DR bus load validation
# ---------------------------------------------------------------------------


def check_dr_bus_load(
    m_ids: MFileIdSets,
    dr_path: Path,
    network_id: NetworkId,
) -> IntegrityCheckResult:
    """Check that DR bus IDs reference buses with nonzero load (Pd > 0).

    Args:
        m_ids: Extracted ID sets with bus_pd mapping.
        dr_path: Path to dr_buses.csv.
        network_id: Network being validated (for reporting).

    Returns:
        IntegrityCheckResult. SKIPPED if dr_buses.csv does not exist.
    """
    check_name = "dr_bus_load"

    if not dr_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description="DR bus IDs reference buses with nonzero load",
            status=CheckStatus.SKIPPED,
            source_file=str(dr_path),
            target_file=f"{network_id.value}.m",
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {dr_path}",
        )

    try:
        csv_ids = extract_csv_ids(dr_path, "bus_id", cast_to_int=True)
    except (KeyError, ValueError) as exc:
        return IntegrityCheckResult(
            check_name=check_name,
            description="DR bus IDs reference buses with nonzero load",
            status=CheckStatus.SKIPPED,
            source_file=str(dr_path),
            target_file=f"{network_id.value}.m",
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"Error reading {dr_path}: {exc}",
        )

    orphaned_refs: list[OrphanedReference] = []
    for bid in sorted(csv_ids.ids, key=lambda x: int(x)):
        int_bid = int(bid)
        if int_bid not in m_ids.bus_ids:
            orphaned_refs.append(
                OrphanedReference(
                    id_value=int_bid,
                    source_file=str(dr_path),
                    target_file=f"{network_id.value}.m (bus table)",
                    context="bus_id not found in .m file",
                )
            )
        elif m_ids.bus_pd.get(int_bid, 0.0) <= 0.0:
            orphaned_refs.append(
                OrphanedReference(
                    id_value=int_bid,
                    source_file=str(dr_path),
                    target_file=f"{network_id.value}.m (bus table)",
                    context=f"bus has Pd={m_ids.bus_pd.get(int_bid, 0.0)} MW (zero load)",
                )
            )

    status = CheckStatus.PASS if not orphaned_refs else CheckStatus.FAIL
    return IntegrityCheckResult(
        check_name=check_name,
        description="DR bus IDs reference buses with nonzero load",
        status=status,
        source_file=str(dr_path),
        target_file=f"{network_id.value}.m (bus table)",
        total_ids_checked=len(csv_ids.ids),
        orphaned_ids=orphaned_refs,
    )


# ---------------------------------------------------------------------------
# Scenario-to-forecast alignment
# ---------------------------------------------------------------------------


def check_scenario_forecast_alignment(
    scenario_path: Path,
    forecast_path: Path,
    gen_id_column: str,
    resource_type: str,
    network_id: NetworkId,
) -> IntegrityCheckResult:
    """Check that scenario multiplier generator IDs match forecast generator IDs.

    Args:
        scenario_path: Path to scenario_multipliers_<type>_50x24.csv.
        forecast_path: Path to <type>_forecast_24h.csv.
        gen_id_column: Column name for generator ID in both files.
        resource_type: "wind" or "solar" (for reporting).
        network_id: Network being validated (for reporting).

    Returns:
        IntegrityCheckResult. SKIPPED if either file does not exist.
    """
    check_name = f"scenario_forecast_alignment_{resource_type}"

    if not scenario_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description=(
                f"{resource_type.title()} scenario generator IDs match forecast generator IDs"
            ),
            status=CheckStatus.SKIPPED,
            source_file=str(scenario_path),
            target_file=str(forecast_path),
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {scenario_path}",
        )

    if not forecast_path.exists():
        return IntegrityCheckResult(
            check_name=check_name,
            description=(
                f"{resource_type.title()} scenario generator IDs match forecast generator IDs"
            ),
            status=CheckStatus.SKIPPED,
            source_file=str(scenario_path),
            target_file=str(forecast_path),
            total_ids_checked=0,
            orphaned_ids=[],
            skip_reason=f"File not found: {forecast_path}",
        )

    # Extract gen IDs from scenario file
    scenario_text = scenario_path.read_text(encoding="utf-8")
    scenario_reader = csv.DictReader(io.StringIO(scenario_text))
    scenario_gen_ids: set[str] = set()
    for row in scenario_reader:
        scenario_gen_ids.add(row[gen_id_column].strip())

    # Extract gen IDs from forecast file
    forecast_text = forecast_path.read_text(encoding="utf-8")
    forecast_reader = csv.DictReader(io.StringIO(forecast_text))
    forecast_gen_ids: set[str] = set()
    for row in forecast_reader:
        forecast_gen_ids.add(row[gen_id_column].strip())

    # Find mismatches in both directions
    in_scenario_not_forecast = scenario_gen_ids - forecast_gen_ids
    in_forecast_not_scenario = forecast_gen_ids - scenario_gen_ids

    orphaned_refs: list[OrphanedReference] = []
    for gid in sorted(in_scenario_not_forecast):
        orphaned_refs.append(
            OrphanedReference(
                id_value=gid,
                source_file=str(scenario_path),
                target_file=str(forecast_path),
                context="in scenarios but not in forecast",
            )
        )
    for gid in sorted(in_forecast_not_scenario):
        orphaned_refs.append(
            OrphanedReference(
                id_value=gid,
                source_file=str(forecast_path),
                target_file=str(scenario_path),
                context="in forecast but not in scenarios",
            )
        )

    status = CheckStatus.PASS if not orphaned_refs else CheckStatus.FAIL
    return IntegrityCheckResult(
        check_name=check_name,
        description=(
            f"{resource_type.title()} scenario generator IDs match forecast generator IDs"
        ),
        status=status,
        source_file=str(scenario_path),
        target_file=str(forecast_path),
        total_ids_checked=len(scenario_gen_ids | forecast_gen_ids),
        orphaned_ids=orphaned_refs,
    )


# ---------------------------------------------------------------------------
# Network-level orchestration
# ---------------------------------------------------------------------------


def validate_network_integrity(
    network_dir: Path,
    m_file_path: Path,
    network_id: NetworkId,
) -> NetworkIntegrityReport:
    """Run all referential integrity checks for a single network.

    Args:
        network_dir: Directory containing the network's CSV files.
        m_file_path: Path to the cleaned .m file for this network.
        network_id: Which network is being validated.

    Returns:
        NetworkIntegrityReport with per-check results and summary counts.

    Raises:
        FileNotFoundError: If the .m file does not exist.
    """
    m_ids = parse_m_file_ids(m_file_path)

    all_checks: list[IntegrityCheckResult] = []

    # 1. Bus reference checks
    bus_csv_files: list[tuple[Path, str]] = [
        (network_dir / "load_24h.csv", "bus_id"),
        (network_dir / "bess_units.csv", "bus_id"),
        (network_dir / "dr_buses.csv", "bus_id"),
    ]
    all_checks.extend(check_bus_references(m_ids, bus_csv_files, network_id))

    # 2. Generator reference checks (gen_uid-based CSVs)
    gen_csv_files: list[tuple[Path, str]] = [
        (network_dir / "gen_temporal_params.csv", "gen_uid"),
        (network_dir / "reserve_eligibility.csv", "gen_uid"),
        (network_dir / "wind_forecast_24h.csv", "gen_uid"),
        (network_dir / "wind_actual_24h.csv", "gen_uid"),
        (network_dir / "solar_forecast_24h.csv", "gen_uid"),
        (network_dir / "solar_actual_24h.csv", "gen_uid"),
    ]
    all_checks.extend(check_generator_references(m_ids, gen_csv_files, network_id))

    # 3. Branch reference checks
    all_checks.append(
        check_branch_references(
            m_ids,
            network_dir / "flowgates.csv",
            "line_ids",
            network_id,
        )
    )

    # 4. Reserve-to-temporal-params linkage
    all_checks.append(
        check_reserve_temporal_linkage(
            network_dir / "reserve_eligibility.csv",
            network_dir / "gen_temporal_params.csv",
            "gen_uid",
            network_id,
        )
    )

    # 5. BESS reserve-to-definition linkage
    all_checks.append(
        check_bess_reserve_linkage(
            network_dir / "reserve_eligibility.csv",
            network_dir / "bess_units.csv",
            network_id,
        )
    )

    # 6. DR bus load validation
    all_checks.append(check_dr_bus_load(m_ids, network_dir / "dr_buses.csv", network_id))

    # 7. Scenario-to-forecast alignment
    scenarios_dir = network_dir / "scenarios"
    all_checks.append(
        check_scenario_forecast_alignment(
            scenarios_dir / "scenario_multipliers_wind_50x24.csv",
            network_dir / "wind_forecast_24h.csv",
            "gen_uid",
            "wind",
            network_id,
        )
    )
    all_checks.append(
        check_scenario_forecast_alignment(
            scenarios_dir / "scenario_multipliers_solar_50x24.csv",
            network_dir / "solar_forecast_24h.csv",
            "gen_uid",
            "solar",
            network_id,
        )
    )

    passed = sum(1 for c in all_checks if c.status == CheckStatus.PASS)
    failed = sum(1 for c in all_checks if c.status == CheckStatus.FAIL)
    skipped = sum(1 for c in all_checks if c.status == CheckStatus.SKIPPED)

    return NetworkIntegrityReport(
        network_id=network_id,
        checks=all_checks,
        total_checks=len(all_checks),
        passed=passed,
        failed=failed,
        skipped=skipped,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def validate_all_networks(
    timeseries_base_dir: Path | None = None,
) -> ReferentialIntegrityReport:
    """Run referential integrity checks across all three networks.

    Args:
        timeseries_base_dir: Base directory containing per-network
            subdirectories. Defaults to <repo_root>/data/timeseries/.

    Returns:
        ReferentialIntegrityReport with results for all networks.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "timeseries"

    network_reports: list[NetworkIntegrityReport] = []

    for network_id in NetworkId:
        network_dir = timeseries_base_dir / network_id.value
        m_file_name = NETWORK_M_FILE_NAMES[network_id.value]
        m_file_path = network_dir / m_file_name

        if not m_file_path.exists():
            logger.warning(
                "Skipping network %s: .m file not found at %s",
                network_id.value,
                m_file_path,
            )
            continue

        report = validate_network_integrity(network_dir, m_file_path, network_id)
        network_reports.append(report)

    total_checks = sum(r.total_checks for r in network_reports)
    total_passed = sum(r.passed for r in network_reports)
    total_failed = sum(r.failed for r in network_reports)
    total_skipped = sum(r.skipped for r in network_reports)

    return ReferentialIntegrityReport(
        networks=network_reports,
        total_checks=total_checks,
        total_passed=total_passed,
        total_failed=total_failed,
        total_skipped=total_skipped,
        all_passed=total_failed == 0,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _report_to_dict(report: ReferentialIntegrityReport) -> dict:
    """Convert a ReferentialIntegrityReport to a JSON-serializable dict."""
    return {
        "all_passed": report.all_passed,
        "total_checks": report.total_checks,
        "total_passed": report.total_passed,
        "total_failed": report.total_failed,
        "total_skipped": report.total_skipped,
        "networks": [
            {
                "network_id": nr.network_id.value,
                "total_checks": nr.total_checks,
                "passed": nr.passed,
                "failed": nr.failed,
                "skipped": nr.skipped,
                "checks": [
                    {
                        "check_name": c.check_name,
                        "description": c.description,
                        "status": c.status.value,
                        "source_file": c.source_file,
                        "target_file": c.target_file,
                        "total_ids_checked": c.total_ids_checked,
                        "orphaned_ids": [
                            {
                                "id_value": o.id_value,
                                "source_file": o.source_file,
                                "target_file": o.target_file,
                                "context": o.context,
                            }
                            for o in c.orphaned_ids
                        ],
                        "skip_reason": c.skip_reason,
                    }
                    for c in nr.checks
                ],
            }
            for nr in report.networks
        ],
    }


def write_json_report(report: ReferentialIntegrityReport, dest_path: Path) -> None:
    """Write the referential integrity report as JSON.

    Args:
        report: The report to serialize.
        dest_path: File path to write the JSON output.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _report_to_dict(report)
    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
    output_path: Path | None = None,
) -> ReferentialIntegrityReport:
    """Entry point: validate referential integrity across all networks.

    Args:
        timeseries_base_dir: Base directory for timeseries data.
        output_path: Path for JSON report output.

    Returns:
        The complete ReferentialIntegrityReport.
    """
    report = validate_all_networks(timeseries_base_dir)

    if output_path is None:
        if timeseries_base_dir is None:
            repo_root = Path(__file__).resolve().parent.parent
            output_path = repo_root / "timeseries" / "referential_integrity_report.json"
        else:
            output_path = timeseries_base_dir / "referential_integrity_report.json"

    write_json_report(report, output_path)

    # Summary
    logger.info(
        "Referential integrity: %d checks, %d passed, %d failed, %d skipped, all_passed=%s",
        report.total_checks,
        report.total_passed,
        report.total_failed,
        report.total_skipped,
        report.all_passed,
    )

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
