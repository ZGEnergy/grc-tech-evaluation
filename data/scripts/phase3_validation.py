"""Cross-Deliverable Validation & Consistency Checks (PRD 03/07).

Runs cross-deliverable validation checks on all Phase 3 outputs (BESS placement,
BESS reserve eligibility, DR placement, DC OPF congestion analysis, flowgate
definitions) for the SMALL (ACTIVSg2000) and MEDIUM (ACTIVSg10k) networks, and
verifies methodology alignment with the Phase 2b TINY (case39) outputs.

Validation checks span ten categories organized into four groups:
  1. Topological integrity (a, b, c)
  2. Fleet sizing reasonableness (d, e, f)
  3. Reserve integration & resource stacking (g, h, i)
  4. Cross-phase consistency (j)
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.reconcile_bus_gen import parse_matpower_case

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BESS_FLEET_FRACTION_MIN: float = 0.03
"""Minimum acceptable BESS fleet power as fraction of system peak load."""

BESS_FLEET_FRACTION_MAX: float = 0.05
"""Maximum acceptable BESS fleet power as fraction of system peak load."""

DR_CURTAIL_FRACTION_MIN: float = 0.02
"""Minimum acceptable total DR curtailment as fraction of system peak load."""

DR_CURTAIL_FRACTION_MAX: float = 0.08
"""Maximum acceptable total DR curtailment as fraction of system peak load."""

VALID_BESS_BUS_TYPES: frozenset[int] = frozenset({1, 2})
"""Bus types acceptable for BESS placement (PQ=1, PV=2). Reference bus (3) excluded."""

PRIMARY_NETWORK_IDS: tuple[str, ...] = ("ACTIVSg2000", "ACTIVSg10k")
"""Networks receiving full Phase 3 validation (checks a-i)."""

TINY_NETWORK_ID: str = "case39"
"""TINY network identifier used for cross-phase consistency check (j)."""

# Phase 2b TINY BESS base columns (from Phase 2b PRD-06 schema)
TINY_BESS_BASE_COLUMNS: frozenset[str] = frozenset(
    {
        "unit_id",
        "bus_id",
        "power_mw",
        "energy_mwh",
        "charge_efficiency",
        "discharge_efficiency",
        "min_soc",
        "max_soc",
        "init_soc",
        "cyclic_soc",
        "spinning_eligible",
        "non_spinning_eligible",
    }
)

# Phase 3 BESS base columns (from Phase 3 PRD-02 schema)
PHASE3_BESS_BASE_COLUMNS: frozenset[str] = frozenset(
    {
        "unit_id",
        "bus",
        "power_mw",
        "energy_mwh",
        "duration_hr",
        "charge_eff",
        "discharge_eff",
        "roundtrip_eff",
        "min_soc_pct",
        "max_soc_pct",
        "initial_soc_pct",
        "ramp_rate_mw_per_min",
        "cyclic_soc",
    }
)

# Base flowgate columns shared across TINY and Phase 3
FLOWGATE_BASE_COLUMNS: frozenset[str] = frozenset(
    {
        "flowgate_id",
        "flowgate_name",
        "branch_id_list",
        "weight_list",
        "limit_mw",
        "direction",
    }
)

NETWORK_M_FILE_NAMES: dict[str, str] = {
    "case39": "case39.m",
    "ACTIVSg2000": "case_ACTIVSg2000.m",
    "ACTIVSg10k": "case_ACTIVSg10k.m",
}

MAX_DETAILS_JSON: int = 20
"""Maximum number of detail entries per check in JSON output."""

MAX_DETAILS_MD: int = 10
"""Maximum number of detail entries per check in markdown output."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ValidationNetworkId(StrEnum):
    """Network identifiers for Phase 3 validation.

    SMALL and MEDIUM are the primary validation targets.
    TINY is loaded for cross-phase consistency check (j) only.
    """

    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"
    TINY = "case39"


class CheckStatus(StrEnum):
    """Outcome of a single validation check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class CheckCategory(StrEnum):
    """Grouping of validation checks by type."""

    TOPOLOGICAL_INTEGRITY = "topological_integrity"
    FLEET_SIZING = "fleet_sizing"
    RESERVE_INTEGRATION = "reserve_integration"
    RESOURCE_STACKING = "resource_stacking"
    FLOWGATE_OVERLAP = "flowgate_overlap"
    CROSS_PHASE_CONSISTENCY = "cross_phase_consistency"


# --- Per-check result ---


@dataclass(frozen=True)
class CheckResult:
    """Result of a single validation check for one network.

    Each check produces exactly one CheckResult. The check_id uses the
    letter labels from the phase plan (a through j) for traceability.
    """

    check_id: str  # e.g., "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"
    check_name: str  # human-readable name, e.g., "BESS bus existence"
    category: CheckCategory
    status: CheckStatus
    message: str  # summary message (e.g., "All 5 BESS buses exist in .m file")
    details: list[str]  # per-item failure details (empty if PASS)
    items_checked: int  # number of items examined
    items_passed: int  # number of items that passed
    items_failed: int  # number of items that failed


# --- Network topology reference ---


@dataclass(frozen=True)
class BusRecord:
    """Minimal bus record extracted from the cleaned .m file for validation."""

    bus: int  # bus number (column 1)
    bus_type: int  # 1=PQ, 2=PV, 3=ref (column 2)
    pd_mw: float  # real power demand (column 3)
    area: int  # electrical area (column 7)


@dataclass(frozen=True)
class BranchRecord:
    """Minimal branch record extracted from the cleaned .m file for validation."""

    branch_idx: int  # 1-based index into the branch table
    from_bus: int  # from bus number (column 1)
    to_bus: int  # to bus number (column 2)
    rate_a_mw: float  # long-term thermal rating (column 6)


@dataclass(frozen=True)
class NetworkTopology:
    """Extracted topology from the cleaned .m file for validation reference."""

    network_id: str
    buses: list[BusRecord]
    branches: list[BranchRecord]
    bus_set: frozenset[int]  # set of valid bus numbers
    bus_pd_map: dict[int, float]  # bus number -> Pd
    bus_type_map: dict[int, int]  # bus number -> bus_type
    branch_idx_set: frozenset[int]  # set of valid 1-based branch indices
    branch_rate_map: dict[int, float]  # branch_idx -> rate_a_mw
    system_peak_mw: float  # sum of all bus Pd values


# --- Loaded Phase 3 output records (minimal for validation) ---


@dataclass(frozen=True)
class BessUnitRecord:
    """Minimal BESS unit record loaded from bess_units.csv for validation."""

    unit_id: str
    bus: int
    power_mw: float
    cyclic_soc: bool


@dataclass(frozen=True)
class DrBusRecord:
    """Minimal DR bus record loaded from dr_buses.csv for validation."""

    dr_id: str
    bus: int
    max_curtail_mw: float


@dataclass(frozen=True)
class FlowgateRecord:
    """Minimal flowgate record loaded from flowgates.csv for validation."""

    flowgate_id: str
    branch_ids: list[int]  # parsed from semicolon-separated branch_id_list
    weights: list[float]  # parsed from semicolon-separated weight_list
    limit_mw: float
    direction: str


@dataclass(frozen=True)
class ReserveEligibilityRecord:
    """Minimal reserve eligibility record for BESS validation check (g)."""

    gen_uid: str
    tech_class: str
    spinning_eligible: bool
    non_spinning_eligible: bool


# --- Network validation result ---


@dataclass(frozen=True)
class NetworkValidationResult:
    """Complete validation result for a single network."""

    network_id: str
    checks: list[CheckResult]
    total_checks: int
    passed: int
    warned: int
    failed: int
    overall_pass: bool  # True if no check has status FAIL


# --- Cross-phase consistency result ---


@dataclass(frozen=True)
class CrossPhaseConsistencyResult:
    """Result of the cross-phase consistency check (j)."""

    tiny_bess_columns: list[str]
    phase3_bess_columns: list[str]
    bess_column_match: bool
    tiny_flowgate_columns: list[str]
    phase3_flowgate_columns: list[str]
    flowgate_column_match: bool
    all_flowgate_limits_positive: bool
    all_bess_cyclic_soc_true: bool
    details: list[str]


# --- Top-level validation report ---


@dataclass(frozen=True)
class ValidationReport:
    """Complete Phase 3 validation report across all networks."""

    network_results: list[NetworkValidationResult]
    cross_phase: CrossPhaseConsistencyResult
    total_checks: int
    total_passed: int
    total_warned: int
    total_failed: int
    overall_pass: bool
    script_version: str


# ---------------------------------------------------------------------------
# Topology loading
# ---------------------------------------------------------------------------


def load_network_topology(
    network_dir: Path,
    network_id: str,
) -> NetworkTopology:
    """Load bus and branch data from the cleaned .m file for validation.

    Uses the Phase 1 D2 MATPOWER parser (parse_matpower_case).

    Args:
        network_dir: Path to the directory containing the cleaned .m file.
        network_id: Network identifier used to locate the .m file.

    Returns:
        A NetworkTopology with bus/branch data and lookup structures.

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
    """
    m_file_name = NETWORK_M_FILE_NAMES[network_id]
    m_file_path = network_dir / m_file_name

    if not m_file_path.exists():
        msg = f"Cleaned .m file not found: {m_file_path}"
        raise FileNotFoundError(msg)

    case_data = parse_matpower_case(m_file_path)

    # Extract area from raw .m text (not available via MatpowerBusRecord)
    m_text = m_file_path.read_text()
    area_map = _extract_bus_areas(m_text)

    buses: list[BusRecord] = []
    for b in case_data.buses:
        buses.append(
            BusRecord(
                bus=b.bus_id,
                bus_type=int(b.bus_type),
                pd_mw=b.pd,
                area=area_map.get(b.bus_id, 1),
            )
        )

    # Parse branches from raw .m file
    branches = _parse_branches_from_text(m_text)

    bus_set = frozenset(b.bus for b in buses)
    bus_pd_map = {b.bus: b.pd_mw for b in buses}
    bus_type_map = {b.bus: b.bus_type for b in buses}
    branch_idx_set = frozenset(br.branch_idx for br in branches)
    branch_rate_map = {br.branch_idx: br.rate_a_mw for br in branches}
    system_peak_mw = sum(b.pd_mw for b in buses if b.pd_mw > 0)

    return NetworkTopology(
        network_id=network_id,
        buses=buses,
        branches=branches,
        bus_set=bus_set,
        bus_pd_map=bus_pd_map,
        bus_type_map=bus_type_map,
        branch_idx_set=branch_idx_set,
        branch_rate_map=branch_rate_map,
        system_peak_mw=system_peak_mw,
    )


def _extract_bus_areas(m_text: str) -> dict[int, int]:
    """Extract bus ID to area mapping from raw .m file text."""
    import re

    pattern = re.compile(r"mpc\.bus\s*=\s*\[([^\]]*)\]", re.DOTALL)
    match = pattern.search(m_text)
    if match is None:
        return {}

    block = match.group(1)
    area_map: dict[int, int] = {}
    for line in block.split(";"):
        line = line.strip()
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        values = line.split()
        try:
            float_vals = [float(v) for v in values]
        except ValueError:
            continue
        if len(float_vals) > 6:
            bus_id = int(float_vals[0])
            area = int(float_vals[6])
            area_map[bus_id] = area
    return area_map


def _parse_branches_from_text(m_text: str) -> list[BranchRecord]:
    """Parse branch data from raw .m file text."""
    import re

    pattern = re.compile(r"mpc\.branch\s*=\s*\[([^\]]*)\]", re.DOTALL)
    match = pattern.search(m_text)
    if match is None:
        return []

    block = match.group(1)
    branches: list[BranchRecord] = []
    idx = 1
    for line in block.split(";"):
        line = line.strip()
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        values = line.split()
        try:
            float_vals = [float(v) for v in values]
        except ValueError:
            continue
        if len(float_vals) >= 6:
            branches.append(
                BranchRecord(
                    branch_idx=idx,
                    from_bus=int(float_vals[0]),
                    to_bus=int(float_vals[1]),
                    rate_a_mw=float_vals[5],
                )
            )
            idx += 1
    return branches


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------


def load_bess_units(
    csv_path: Path,
) -> list[BessUnitRecord]:
    """Load BESS unit records from bess_units.csv for validation.

    Handles both Phase 2b column naming (bus_id) and Phase 3 column
    naming (bus).

    Args:
        csv_path: Path to bess_units.csv.

    Returns:
        A list of BessUnitRecord, one per BESS unit.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing.
    """
    if not csv_path.exists():
        msg = f"BESS units file not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        msg = f"BESS units file has no header: {csv_path}"
        raise ValueError(msg)

    cols = set(reader.fieldnames)

    # Determine bus column name
    if "bus" in cols:
        bus_col = "bus"
    elif "bus_id" in cols:
        bus_col = "bus_id"
    else:
        msg = f"BESS units file missing bus/bus_id column: {csv_path}"
        raise ValueError(msg)

    if "unit_id" not in cols:
        msg = f"BESS units file missing unit_id column: {csv_path}"
        raise ValueError(msg)

    records: list[BessUnitRecord] = []
    for row in reader:
        cyclic_str = row.get("cyclic_soc", "true").strip().lower()
        records.append(
            BessUnitRecord(
                unit_id=row["unit_id"].strip(),
                bus=int(row[bus_col]),
                power_mw=float(row.get("power_mw", "0")),
                cyclic_soc=cyclic_str == "true",
            )
        )
    return records


def load_dr_buses(
    csv_path: Path,
) -> list[DrBusRecord]:
    """Load DR bus records from dr_buses.csv for validation.

    Handles both Phase 2b column naming (bus_id, max_curtailment_mw)
    and Phase 3 column naming (bus, max_curtail_mw).

    Args:
        csv_path: Path to dr_buses.csv.

    Returns:
        A list of DrBusRecord, one per DR bus.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing.
    """
    if not csv_path.exists():
        msg = f"DR buses file not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        msg = f"DR buses file has no header: {csv_path}"
        raise ValueError(msg)

    cols = set(reader.fieldnames)

    # Determine bus column name
    if "bus" in cols:
        bus_col = "bus"
    elif "bus_id" in cols:
        bus_col = "bus_id"
    else:
        msg = f"DR buses file missing bus/bus_id column: {csv_path}"
        raise ValueError(msg)

    # Determine curtailment column name
    if "max_curtail_mw" in cols:
        curtail_col = "max_curtail_mw"
    elif "max_curtailment_mw" in cols:
        curtail_col = "max_curtailment_mw"
    else:
        msg = f"DR buses file missing max_curtail_mw/max_curtailment_mw column: {csv_path}"
        raise ValueError(msg)

    # Determine DR ID column name
    if "dr_id" in cols:
        id_col = "dr_id"
    elif "dr_bus_id" in cols:
        id_col = "dr_bus_id"
    else:
        msg = f"DR buses file missing dr_id/dr_bus_id column: {csv_path}"
        raise ValueError(msg)

    records: list[DrBusRecord] = []
    for row in reader:
        records.append(
            DrBusRecord(
                dr_id=row[id_col].strip(),
                bus=int(row[bus_col]),
                max_curtail_mw=float(row[curtail_col]),
            )
        )
    return records


def load_flowgates(
    csv_path: Path,
) -> list[FlowgateRecord]:
    """Load flowgate records from flowgates.csv for validation.

    Parses branch_id_list and weight_list from semicolon-separated strings.

    Args:
        csv_path: Path to flowgates.csv.

    Returns:
        A list of FlowgateRecord, one per flowgate.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing.
    """
    if not csv_path.exists():
        msg = f"Flowgates file not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        msg = f"Flowgates file has no header: {csv_path}"
        raise ValueError(msg)

    cols = set(reader.fieldnames)
    required = {"flowgate_id", "branch_id_list", "weight_list", "limit_mw", "direction"}
    missing = required - cols
    if missing:
        msg = f"Flowgates file missing columns: {sorted(missing)}"
        raise ValueError(msg)

    records: list[FlowgateRecord] = []
    for row in reader:
        branch_id_str = row["branch_id_list"].strip()
        weight_str = row["weight_list"].strip()

        branch_ids = [int(x.strip()) for x in branch_id_str.split(";") if x.strip()]
        weights = [float(x.strip()) for x in weight_str.split(";") if x.strip()]

        records.append(
            FlowgateRecord(
                flowgate_id=row["flowgate_id"].strip(),
                branch_ids=branch_ids,
                weights=weights,
                limit_mw=float(row["limit_mw"]),
                direction=row["direction"].strip(),
            )
        )
    return records


def load_reserve_eligibility(
    csv_path: Path,
) -> list[ReserveEligibilityRecord]:
    """Load reserve eligibility records for BESS check (g).

    Filters to rows with tech_class == "bess" for efficient lookup.

    Args:
        csv_path: Path to reserve_eligibility.csv.

    Returns:
        A list of ReserveEligibilityRecord for BESS rows only.

    Raises:
        FileNotFoundError: If csv_path does not exist.
    """
    if not csv_path.exists():
        msg = f"Reserve eligibility file not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    records: list[ReserveEligibilityRecord] = []
    for row in reader:
        records.append(
            ReserveEligibilityRecord(
                gen_uid=row["gen_uid"].strip(),
                tech_class=row["tech_class"].strip(),
                spinning_eligible=row["spinning_eligible"].strip().lower() == "true",
                non_spinning_eligible=(row["non_spinning_eligible"].strip().lower() == "true"),
            )
        )
    return records


def load_csv_columns(
    csv_path: Path,
) -> list[str]:
    """Read just the header row from a CSV to get column names.

    Args:
        csv_path: Path to any CSV file.

    Returns:
        A list of column name strings from the header row.

    Raises:
        FileNotFoundError: If csv_path does not exist.
    """
    if not csv_path.exists():
        msg = f"CSV file not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    return [col.strip() for col in header] if header else []


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_bess_bus_existence(
    bess_units: list[BessUnitRecord],
    topology: NetworkTopology,
) -> CheckResult:
    """Check (a): every BESS unit bus exists in cleaned .m file with valid bus type.

    Args:
        bess_units: BESS unit records from D2 output.
        topology: Network topology from the cleaned .m file.

    Returns:
        A CheckResult with check_id="a" and per-unit failure details.
    """
    details: list[str] = []
    failed = 0
    for unit in bess_units:
        if unit.bus not in topology.bus_set:
            details.append(f"{unit.unit_id}: bus {unit.bus} not found in .m file")
            failed += 1
        elif topology.bus_type_map[unit.bus] not in VALID_BESS_BUS_TYPES:
            bt = topology.bus_type_map[unit.bus]
            details.append(
                f"{unit.unit_id}: bus {unit.bus} has invalid bus type {bt} "
                f"(expected one of {sorted(VALID_BESS_BUS_TYPES)})"
            )
            failed += 1

    passed = len(bess_units) - failed
    status = CheckStatus.PASS if failed == 0 else CheckStatus.FAIL
    message = (
        f"All {len(bess_units)} BESS buses exist in .m file with valid bus type"
        if failed == 0
        else f"{failed} of {len(bess_units)} BESS unit(s) have invalid bus assignments"
    )

    return CheckResult(
        check_id="a",
        check_name="BESS bus existence",
        category=CheckCategory.TOPOLOGICAL_INTEGRITY,
        status=status,
        message=message,
        details=details,
        items_checked=len(bess_units),
        items_passed=passed,
        items_failed=failed,
    )


def check_dr_bus_existence(
    dr_buses: list[DrBusRecord],
    topology: NetworkTopology,
) -> CheckResult:
    """Check (b): every DR bus exists in cleaned .m file with nonzero Pd.

    Args:
        dr_buses: DR bus records from D4 output.
        topology: Network topology from the cleaned .m file.

    Returns:
        A CheckResult with check_id="b" and per-bus failure details.
    """
    details: list[str] = []
    failed = 0
    for dr in dr_buses:
        if dr.bus not in topology.bus_set:
            details.append(f"{dr.dr_id}: bus {dr.bus} not found in .m file")
            failed += 1
        elif topology.bus_pd_map.get(dr.bus, 0.0) <= 0:
            details.append(
                f"{dr.dr_id}: bus {dr.bus} has zero or negative Pd "
                f"({topology.bus_pd_map.get(dr.bus, 0.0):.1f} MW)"
            )
            failed += 1

    passed = len(dr_buses) - failed
    status = CheckStatus.PASS if failed == 0 else CheckStatus.FAIL
    message = (
        f"All {len(dr_buses)} DR buses exist in .m file with nonzero Pd"
        if failed == 0
        else f"{failed} of {len(dr_buses)} DR bus(es) have invalid bus assignments"
    )

    return CheckResult(
        check_id="b",
        check_name="DR bus existence",
        category=CheckCategory.TOPOLOGICAL_INTEGRITY,
        status=status,
        message=message,
        details=details,
        items_checked=len(dr_buses),
        items_passed=passed,
        items_failed=failed,
    )


def check_flowgate_branch_existence(
    flowgates: list[FlowgateRecord],
    topology: NetworkTopology,
) -> CheckResult:
    """Check (c): every flowgate branch ID exists in cleaned .m file branch table.

    Args:
        flowgates: Flowgate records from D6 output.
        topology: Network topology from the cleaned .m file.

    Returns:
        A CheckResult with check_id="c" and per-branch failure details.
    """
    details: list[str] = []
    failed_flowgates = 0
    for fg in flowgates:
        fg_has_error = False
        for bid in fg.branch_ids:
            if bid not in topology.branch_idx_set:
                details.append(f"{fg.flowgate_id}: branch index {bid} not found in .m file")
                fg_has_error = True
        if fg_has_error:
            failed_flowgates += 1

    passed = len(flowgates) - failed_flowgates
    status = CheckStatus.PASS if failed_flowgates == 0 else CheckStatus.FAIL
    message = (
        f"All branch IDs in {len(flowgates)} flowgate(s) exist in .m file"
        if failed_flowgates == 0
        else (
            f"{failed_flowgates} of {len(flowgates)} flowgate(s) reference nonexistent branch IDs"
        )
    )

    return CheckResult(
        check_id="c",
        check_name="Flowgate branch existence",
        category=CheckCategory.TOPOLOGICAL_INTEGRITY,
        status=status,
        message=message,
        details=details,
        items_checked=len(flowgates),
        items_passed=passed,
        items_failed=failed_flowgates,
    )


def check_bess_fleet_fraction(
    bess_units: list[BessUnitRecord],
    topology: NetworkTopology,
) -> CheckResult:
    """Check (d): BESS fleet power within 3-5% of system peak load.

    Args:
        bess_units: BESS unit records from D2 output.
        topology: Network topology for system peak MW.

    Returns:
        A CheckResult with check_id="d" and the computed fraction in message.
    """
    total_power = sum(u.power_mw for u in bess_units)
    peak = topology.system_peak_mw
    fraction = total_power / peak if peak > 0 else 0.0

    in_range = BESS_FLEET_FRACTION_MIN <= fraction <= BESS_FLEET_FRACTION_MAX
    status = CheckStatus.PASS if in_range else CheckStatus.FAIL
    details: list[str] = []
    if not in_range:
        details.append(
            f"BESS fleet fraction {fraction:.4f} ({fraction * 100:.2f}%) "
            f"outside [{BESS_FLEET_FRACTION_MIN:.0%}, {BESS_FLEET_FRACTION_MAX:.0%}]"
        )

    message = (
        f"BESS fleet: {total_power:.1f} MW = {fraction:.2%} of "
        f"{peak:.1f} MW system peak "
        f"(range: [{BESS_FLEET_FRACTION_MIN:.0%}, {BESS_FLEET_FRACTION_MAX:.0%}])"
    )

    return CheckResult(
        check_id="d",
        check_name="BESS fleet sizing",
        category=CheckCategory.FLEET_SIZING,
        status=status,
        message=message,
        details=details,
        items_checked=1,
        items_passed=1 if in_range else 0,
        items_failed=0 if in_range else 1,
    )


def check_dr_curtailment_fraction(
    dr_buses: list[DrBusRecord],
    topology: NetworkTopology,
) -> CheckResult:
    """Check (e): DR curtailment capacity within 2-8% of system peak load.

    Args:
        dr_buses: DR bus records from D4 output.
        topology: Network topology for system peak MW.

    Returns:
        A CheckResult with check_id="e" and the computed fraction in message.
    """
    total_curtail = sum(dr.max_curtail_mw for dr in dr_buses)
    peak = topology.system_peak_mw
    fraction = total_curtail / peak if peak > 0 else 0.0

    in_range = DR_CURTAIL_FRACTION_MIN <= fraction <= DR_CURTAIL_FRACTION_MAX
    status = CheckStatus.PASS if in_range else CheckStatus.FAIL
    details: list[str] = []
    if not in_range:
        details.append(
            f"DR curtailment fraction {fraction:.4f} ({fraction * 100:.2f}%) "
            f"outside [{DR_CURTAIL_FRACTION_MIN:.0%}, {DR_CURTAIL_FRACTION_MAX:.0%}]"
        )

    message = (
        f"DR curtailment: {total_curtail:.1f} MW = {fraction:.2%} of "
        f"{peak:.1f} MW system peak "
        f"(range: [{DR_CURTAIL_FRACTION_MIN:.0%}, {DR_CURTAIL_FRACTION_MAX:.0%}])"
    )

    return CheckResult(
        check_id="e",
        check_name="DR curtailment sizing",
        category=CheckCategory.FLEET_SIZING,
        status=status,
        message=message,
        details=details,
        items_checked=1,
        items_passed=1 if in_range else 0,
        items_failed=0 if in_range else 1,
    )


def check_flowgate_limits(
    flowgates: list[FlowgateRecord],
    topology: NetworkTopology,
) -> CheckResult:
    """Check (f): flowgate limits are positive and bounded by branch capacity.

    Args:
        flowgates: Flowgate records from D6 output.
        topology: Network topology for branch rate_a lookup.

    Returns:
        A CheckResult with check_id="f" and per-flowgate failure details.
    """
    details: list[str] = []
    failed = 0
    for fg in flowgates:
        if fg.limit_mw <= 0:
            details.append(f"{fg.flowgate_id}: limit_mw={fg.limit_mw} is not positive")
            failed += 1
            continue

        branch_capacity_sum = sum(topology.branch_rate_map.get(bid, 0.0) for bid in fg.branch_ids)
        if fg.limit_mw >= branch_capacity_sum:
            details.append(
                f"{fg.flowgate_id}: limit_mw={fg.limit_mw:.1f} >= "
                f"sum of branch rate_a={branch_capacity_sum:.1f}"
            )
            failed += 1

    passed = len(flowgates) - failed
    status = CheckStatus.PASS if failed == 0 else CheckStatus.FAIL
    message = (
        f"All {len(flowgates)} flowgate limits are positive and bounded"
        if failed == 0
        else f"{failed} of {len(flowgates)} flowgate(s) have invalid limits"
    )

    return CheckResult(
        check_id="f",
        check_name="Flowgate limit bounds",
        category=CheckCategory.FLEET_SIZING,
        status=status,
        message=message,
        details=details,
        items_checked=len(flowgates),
        items_passed=passed,
        items_failed=failed,
    )


def check_bess_reserve_eligibility(
    bess_units: list[BessUnitRecord],
    reserve_rows: list[ReserveEligibilityRecord],
) -> CheckResult:
    """Check (g): every BESS unit has a matching reserve eligibility entry.

    Args:
        bess_units: BESS unit records from D2 output.
        reserve_rows: BESS reserve eligibility records from D3 output.

    Returns:
        A CheckResult with check_id="g" and per-unit failure details.
    """
    # Build lookup by gen_uid for BESS rows
    bess_reserve_map: dict[str, ReserveEligibilityRecord] = {}
    for r in reserve_rows:
        if r.tech_class == "bess":
            bess_reserve_map[r.gen_uid] = r

    details: list[str] = []
    failed = 0
    for unit in bess_units:
        if unit.unit_id not in bess_reserve_map:
            details.append(
                f"{unit.unit_id}: not found in reserve eligibility with tech_class='bess'"
            )
            failed += 1
            continue

        entry = bess_reserve_map[unit.unit_id]
        if not entry.spinning_eligible:
            details.append(f"{unit.unit_id}: spinning_eligible is false")
            failed += 1
        elif not entry.non_spinning_eligible:
            details.append(f"{unit.unit_id}: non_spinning_eligible is false")
            failed += 1

    passed = len(bess_units) - failed
    status = CheckStatus.PASS if failed == 0 else CheckStatus.FAIL
    message = (
        f"All {len(bess_units)} BESS units have valid reserve eligibility entries"
        if failed == 0
        else (
            f"{failed} of {len(bess_units)} BESS unit(s) have "
            f"missing or invalid reserve eligibility"
        )
    )

    return CheckResult(
        check_id="g",
        check_name="BESS reserve eligibility",
        category=CheckCategory.RESERVE_INTEGRATION,
        status=status,
        message=message,
        details=details,
        items_checked=len(bess_units),
        items_passed=passed,
        items_failed=failed,
    )


def check_no_bess_dr_overlap(
    bess_units: list[BessUnitRecord],
    dr_buses: list[DrBusRecord],
) -> CheckResult:
    """Check (h): no bus hosts both BESS and DR resources.

    Args:
        bess_units: BESS unit records from D2 output.
        dr_buses: DR bus records from D4 output.

    Returns:
        A CheckResult with check_id="h" and overlapping buses in details.
    """
    bess_bus_set = {u.bus for u in bess_units}
    dr_bus_set = {d.bus for d in dr_buses}
    overlap = bess_bus_set & dr_bus_set

    total_unique = len(bess_bus_set | dr_bus_set)
    details: list[str] = []
    if overlap:
        details.append(f"Buses hosting both BESS and DR: {sorted(overlap)}")

    failed = len(overlap)
    status = CheckStatus.PASS if not overlap else CheckStatus.FAIL
    message = (
        f"BESS buses ({len(bess_bus_set)}) and DR buses ({len(dr_bus_set)}) are disjoint"
        if not overlap
        else (f"{len(overlap)} bus(es) host both BESS and DR resources: {sorted(overlap)}")
    )

    return CheckResult(
        check_id="h",
        check_name="BESS/DR overlap",
        category=CheckCategory.RESOURCE_STACKING,
        status=status,
        message=message,
        details=details,
        items_checked=total_unique,
        items_passed=total_unique - failed,
        items_failed=failed,
    )


def check_flowgate_branch_disjoint(
    flowgates: list[FlowgateRecord],
) -> CheckResult:
    """Check (i): flowgate branch sets are pairwise disjoint.

    Args:
        flowgates: Flowgate records from D6 output.

    Returns:
        A CheckResult with check_id="i" and overlapping branch details.
    """
    details: list[str] = []
    failed_pairs = 0
    n = len(flowgates)
    for i in range(n):
        for j in range(i + 1, n):
            set_i = set(flowgates[i].branch_ids)
            set_j = set(flowgates[j].branch_ids)
            overlap = set_i & set_j
            if overlap:
                details.append(
                    f"{flowgates[i].flowgate_id} and {flowgates[j].flowgate_id} "
                    f"share branch(es): {sorted(overlap)}"
                )
                failed_pairs += 1

    status = CheckStatus.PASS if failed_pairs == 0 else CheckStatus.FAIL
    message = (
        f"All {n} flowgate branch sets are pairwise disjoint"
        if failed_pairs == 0
        else f"{failed_pairs} pair(s) of flowgates share branch(es)"
    )

    return CheckResult(
        check_id="i",
        check_name="Flowgate branch disjointness",
        category=CheckCategory.FLOWGATE_OVERLAP,
        status=status,
        message=message,
        details=details,
        items_checked=n,
        items_passed=n if failed_pairs == 0 else n - failed_pairs,
        items_failed=failed_pairs,
    )


def check_cross_phase_consistency(
    tiny_dir: Path,
    phase3_dirs: dict[str, Path],
) -> CrossPhaseConsistencyResult:
    """Check (j): Phase 3 methodology aligns with Phase 2b TINY outputs.

    Args:
        tiny_dir: Path to data/timeseries/case39/.
        phase3_dirs: Dict mapping network_id to data/timeseries/<network>/.

    Returns:
        A CrossPhaseConsistencyResult with comparison details.
    """
    details: list[str] = []

    # --- j-1: BESS column comparison ---
    tiny_bess_cols: list[str] = []
    phase3_bess_cols: list[str] = []
    bess_column_match = False

    tiny_bess_path = tiny_dir / "bess_units.csv"
    if tiny_bess_path.exists():
        tiny_bess_cols = load_csv_columns(tiny_bess_path)
    else:
        details.append("TINY bess_units.csv not found; skipping BESS column check")

    # Use first available Phase 3 network for column comparison
    for nid, ndir in phase3_dirs.items():
        p3_bess_path = ndir / "bess_units.csv"
        if p3_bess_path.exists():
            phase3_bess_cols = load_csv_columns(p3_bess_path)
            break

    if tiny_bess_cols and phase3_bess_cols:
        tiny_set = set(tiny_bess_cols)
        p3_set = set(phase3_bess_cols)
        # Check semantic overlap: shared column names
        shared = tiny_set & p3_set
        # Known shared columns (at minimum unit_id, power_mw, energy_mwh, cyclic_soc)
        bess_column_match = len(shared) >= 3
        if not bess_column_match:
            details.append(
                f"BESS column overlap insufficient: shared={sorted(shared)}, "
                f"TINY={sorted(tiny_set)}, Phase3={sorted(p3_set)}"
            )
    elif not tiny_bess_cols and not phase3_bess_cols:
        details.append("No BESS CSV files found for column comparison")

    # --- j-2: Flowgate column comparison ---
    tiny_fg_cols: list[str] = []
    phase3_fg_cols: list[str] = []
    flowgate_column_match = False

    tiny_fg_path = tiny_dir / "flowgates.csv"
    if tiny_fg_path.exists():
        tiny_fg_cols = load_csv_columns(tiny_fg_path)
    else:
        details.append("TINY flowgates.csv not found; skipping flowgate column check")

    for nid, ndir in phase3_dirs.items():
        p3_fg_path = ndir / "flowgates.csv"
        if p3_fg_path.exists():
            phase3_fg_cols = load_csv_columns(p3_fg_path)
            break

    if tiny_fg_cols and phase3_fg_cols:
        tiny_fg_set = set(tiny_fg_cols)
        p3_fg_set = set(phase3_fg_cols)
        base_in_tiny = FLOWGATE_BASE_COLUMNS <= tiny_fg_set
        base_in_p3 = FLOWGATE_BASE_COLUMNS <= p3_fg_set
        flowgate_column_match = base_in_tiny and base_in_p3
        if not flowgate_column_match:
            missing_tiny = FLOWGATE_BASE_COLUMNS - tiny_fg_set
            missing_p3 = FLOWGATE_BASE_COLUMNS - p3_fg_set
            if missing_tiny:
                details.append(f"TINY flowgates missing base columns: {sorted(missing_tiny)}")
            if missing_p3:
                details.append(f"Phase3 flowgates missing base columns: {sorted(missing_p3)}")

    # --- j-3: All flowgate limits positive ---
    all_fg_limits_positive = True
    all_dirs = {TINY_NETWORK_ID: tiny_dir, **phase3_dirs}
    for nid, ndir in all_dirs.items():
        fg_path = ndir / "flowgates.csv"
        if not fg_path.exists():
            continue
        try:
            fgs = load_flowgates(fg_path)
            for fg in fgs:
                if fg.limit_mw <= 0:
                    all_fg_limits_positive = False
                    details.append(
                        f"[{nid}] {fg.flowgate_id}: limit_mw={fg.limit_mw} is not positive"
                    )
        except (ValueError, FileNotFoundError):
            pass

    # --- j-4: All BESS cyclic_soc true ---
    all_bess_cyclic = True
    for nid, ndir in all_dirs.items():
        bess_path = ndir / "bess_units.csv"
        if not bess_path.exists():
            continue
        try:
            bess = load_bess_units(bess_path)
            for unit in bess:
                if not unit.cyclic_soc:
                    all_bess_cyclic = False
                    details.append(f"[{nid}] {unit.unit_id}: cyclic_soc is false")
        except (ValueError, FileNotFoundError):
            pass

    return CrossPhaseConsistencyResult(
        tiny_bess_columns=tiny_bess_cols,
        phase3_bess_columns=phase3_bess_cols,
        bess_column_match=bess_column_match,
        tiny_flowgate_columns=tiny_fg_cols,
        phase3_flowgate_columns=phase3_fg_cols,
        flowgate_column_match=flowgate_column_match,
        all_flowgate_limits_positive=all_fg_limits_positive,
        all_bess_cyclic_soc_true=all_bess_cyclic,
        details=details,
    )


# ---------------------------------------------------------------------------
# Network-level orchestration
# ---------------------------------------------------------------------------


def validate_network(
    network_id: str,
    timeseries_dir: Path,
) -> NetworkValidationResult:
    """Run all Phase 3 validation checks (a-i) for a single network.

    If a required input file is missing, the corresponding checks
    receive FAIL status with a "file not found" message.

    Args:
        network_id: Network identifier ("ACTIVSg2000" or "ACTIVSg10k").
        timeseries_dir: Base timeseries directory (data/timeseries/).

    Returns:
        A NetworkValidationResult for the network.
    """
    network_dir = timeseries_dir / network_id
    checks: list[CheckResult] = []

    # 1. Load topology
    try:
        topology = load_network_topology(network_dir, network_id)
    except FileNotFoundError as e:
        # All checks fail if topology can't be loaded
        fail_msg = f"Cannot load topology: {e}"
        for cid, cname, cat in [
            ("a", "BESS bus existence", CheckCategory.TOPOLOGICAL_INTEGRITY),
            ("b", "DR bus existence", CheckCategory.TOPOLOGICAL_INTEGRITY),
            ("c", "Flowgate branch existence", CheckCategory.TOPOLOGICAL_INTEGRITY),
            ("d", "BESS fleet sizing", CheckCategory.FLEET_SIZING),
            ("e", "DR curtailment sizing", CheckCategory.FLEET_SIZING),
            ("f", "Flowgate limit bounds", CheckCategory.FLEET_SIZING),
            ("g", "BESS reserve eligibility", CheckCategory.RESERVE_INTEGRATION),
            ("h", "BESS/DR overlap", CheckCategory.RESOURCE_STACKING),
            ("i", "Flowgate branch disjointness", CheckCategory.FLOWGATE_OVERLAP),
        ]:
            checks.append(
                CheckResult(
                    check_id=cid,
                    check_name=cname,
                    category=cat,
                    status=CheckStatus.FAIL,
                    message=fail_msg,
                    details=[fail_msg],
                    items_checked=0,
                    items_passed=0,
                    items_failed=0,
                )
            )
        return _build_network_result(network_id, checks)

    # 2. Load input files
    bess_path = network_dir / "bess_units.csv"
    dr_path = network_dir / "dr_buses.csv"
    fg_path = network_dir / "flowgates.csv"
    reserve_path = network_dir / "reserve_eligibility.csv"

    bess_units: list[BessUnitRecord] | None = None
    dr_buses_list: list[DrBusRecord] | None = None
    flowgates_list: list[FlowgateRecord] | None = None
    reserve_rows: list[ReserveEligibilityRecord] | None = None

    try:
        bess_units = load_bess_units(bess_path)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Could not load bess_units.csv for %s: %s", network_id, e)

    try:
        dr_buses_list = load_dr_buses(dr_path)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Could not load dr_buses.csv for %s: %s", network_id, e)

    try:
        flowgates_list = load_flowgates(fg_path)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Could not load flowgates.csv for %s: %s", network_id, e)

    try:
        reserve_rows = load_reserve_eligibility(reserve_path)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Could not load reserve_eligibility.csv for %s: %s", network_id, e)

    # 3. Run checks (a) through (i)
    # Check (a): BESS bus existence
    if bess_units is not None:
        checks.append(check_bess_bus_existence(bess_units, topology))
    else:
        checks.append(
            _file_not_found_check(
                "a", "BESS bus existence", CheckCategory.TOPOLOGICAL_INTEGRITY, "bess_units.csv"
            )
        )

    # Check (b): DR bus existence
    if dr_buses_list is not None:
        checks.append(check_dr_bus_existence(dr_buses_list, topology))
    else:
        checks.append(
            _file_not_found_check(
                "b", "DR bus existence", CheckCategory.TOPOLOGICAL_INTEGRITY, "dr_buses.csv"
            )
        )

    # Check (c): Flowgate branch existence
    if flowgates_list is not None:
        checks.append(check_flowgate_branch_existence(flowgates_list, topology))
    else:
        checks.append(
            _file_not_found_check(
                "c",
                "Flowgate branch existence",
                CheckCategory.TOPOLOGICAL_INTEGRITY,
                "flowgates.csv",
            )
        )

    # Check (d): BESS fleet fraction
    if bess_units is not None:
        checks.append(check_bess_fleet_fraction(bess_units, topology))
    else:
        checks.append(
            _file_not_found_check(
                "d", "BESS fleet sizing", CheckCategory.FLEET_SIZING, "bess_units.csv"
            )
        )

    # Check (e): DR curtailment fraction
    if dr_buses_list is not None:
        checks.append(check_dr_curtailment_fraction(dr_buses_list, topology))
    else:
        checks.append(
            _file_not_found_check(
                "e", "DR curtailment sizing", CheckCategory.FLEET_SIZING, "dr_buses.csv"
            )
        )

    # Check (f): Flowgate limits
    if flowgates_list is not None:
        checks.append(check_flowgate_limits(flowgates_list, topology))
    else:
        checks.append(
            _file_not_found_check(
                "f", "Flowgate limit bounds", CheckCategory.FLEET_SIZING, "flowgates.csv"
            )
        )

    # Check (g): BESS reserve eligibility
    if bess_units is not None and reserve_rows is not None:
        checks.append(check_bess_reserve_eligibility(bess_units, reserve_rows))
    else:
        missing_file = "bess_units.csv" if bess_units is None else "reserve_eligibility.csv"
        checks.append(
            _file_not_found_check(
                "g", "BESS reserve eligibility", CheckCategory.RESERVE_INTEGRATION, missing_file
            )
        )

    # Check (h): BESS/DR overlap
    if bess_units is not None and dr_buses_list is not None:
        checks.append(check_no_bess_dr_overlap(bess_units, dr_buses_list))
    else:
        missing_file = "bess_units.csv" if bess_units is None else "dr_buses.csv"
        checks.append(
            _file_not_found_check(
                "h", "BESS/DR overlap", CheckCategory.RESOURCE_STACKING, missing_file
            )
        )

    # Check (i): Flowgate branch disjointness
    if flowgates_list is not None:
        checks.append(check_flowgate_branch_disjoint(flowgates_list))
    else:
        checks.append(
            _file_not_found_check(
                "i", "Flowgate branch disjointness", CheckCategory.FLOWGATE_OVERLAP, "flowgates.csv"
            )
        )

    return _build_network_result(network_id, checks)


def _file_not_found_check(
    check_id: str,
    check_name: str,
    category: CheckCategory,
    file_name: str,
) -> CheckResult:
    """Create a FAIL CheckResult for a missing input file."""
    msg = f"Input file not found: {file_name}"
    return CheckResult(
        check_id=check_id,
        check_name=check_name,
        category=category,
        status=CheckStatus.FAIL,
        message=msg,
        details=[msg],
        items_checked=0,
        items_passed=0,
        items_failed=0,
    )


def _build_network_result(
    network_id: str,
    checks: list[CheckResult],
) -> NetworkValidationResult:
    """Build a NetworkValidationResult from a list of check results."""
    passed = sum(1 for c in checks if c.status == CheckStatus.PASS)
    warned = sum(1 for c in checks if c.status == CheckStatus.WARN)
    failed = sum(1 for c in checks if c.status == CheckStatus.FAIL)
    return NetworkValidationResult(
        network_id=network_id,
        checks=checks,
        total_checks=len(checks),
        passed=passed,
        warned=warned,
        failed=failed,
        overall_pass=failed == 0,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_validation_report(
    network_results: list[NetworkValidationResult],
    cross_phase: CrossPhaseConsistencyResult,
) -> ValidationReport:
    """Aggregate per-network results and cross-phase checks into a report.

    Args:
        network_results: Validation results for SMALL and MEDIUM.
        cross_phase: Cross-phase consistency result.

    Returns:
        A ValidationReport with aggregated statistics.
    """
    total_passed = sum(nr.passed for nr in network_results)
    total_warned = sum(nr.warned for nr in network_results)
    total_failed = sum(nr.failed for nr in network_results)

    # Count cross-phase sub-checks
    cross_phase_checks = 4  # j-1 through j-4
    cross_phase_passed = sum(
        [
            cross_phase.bess_column_match,
            cross_phase.flowgate_column_match,
            cross_phase.all_flowgate_limits_positive,
            cross_phase.all_bess_cyclic_soc_true,
        ]
    )
    cross_phase_failed = cross_phase_checks - cross_phase_passed

    total_checks = sum(nr.total_checks for nr in network_results) + cross_phase_checks
    total_passed += cross_phase_passed
    total_failed += cross_phase_failed

    overall_pass = total_failed == 0

    return ValidationReport(
        network_results=network_results,
        cross_phase=cross_phase,
        total_checks=total_checks,
        total_passed=total_passed,
        total_warned=total_warned,
        total_failed=total_failed,
        overall_pass=overall_pass,
        script_version=__version__,
    )


def write_validation_json(
    report: ValidationReport,
    dest_path: Path,
) -> None:
    """Write the validation report to JSON for CI consumption.

    Details lists are capped at 20 entries per check.

    Args:
        report: The complete validation report.
        dest_path: File path for the output JSON.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, object] = {
        "overall_pass": report.overall_pass,
        "total_checks": report.total_checks,
        "total_passed": report.total_passed,
        "total_warned": report.total_warned,
        "total_failed": report.total_failed,
        "networks": {},
        "cross_phase": {
            "bess_column_match": report.cross_phase.bess_column_match,
            "flowgate_column_match": report.cross_phase.flowgate_column_match,
            "all_flowgate_limits_positive": (report.cross_phase.all_flowgate_limits_positive),
            "all_bess_cyclic_soc_true": report.cross_phase.all_bess_cyclic_soc_true,
            "details": report.cross_phase.details[:MAX_DETAILS_JSON],
        },
        "script_version": report.script_version,
    }

    networks_dict: dict[str, object] = {}
    for nr in report.network_results:
        networks_dict[nr.network_id] = {
            "overall_pass": nr.overall_pass,
            "checks": [
                {
                    "check_id": c.check_id,
                    "check_name": c.check_name,
                    "category": c.category.value,
                    "status": c.status.value,
                    "message": c.message,
                    "items_checked": c.items_checked,
                    "items_passed": c.items_passed,
                    "items_failed": c.items_failed,
                    "details": c.details[:MAX_DETAILS_JSON],
                }
                for c in nr.checks
            ],
        }
    data["networks"] = networks_dict

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def write_validation_markdown(
    report: ValidationReport,
    dest_path: Path,
) -> None:
    """Write a human-readable markdown summary of the validation report.

    Args:
        report: The complete validation report.
        dest_path: File path for the output markdown.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    verdict = "PASS" if report.overall_pass else "FAIL"
    lines.append("# Phase 3 Cross-Deliverable Validation Report")
    lines.append("")
    lines.append(f"- **Overall verdict:** {verdict}")
    lines.append(f"- **Script version:** {report.script_version}")
    lines.append(
        f"- **Total checks:** {report.total_checks} "
        f"(PASS: {report.total_passed}, WARN: {report.total_warned}, "
        f"FAIL: {report.total_failed})"
    )
    lines.append("")

    # Summary table
    lines.append("## Network Summary")
    lines.append("")
    lines.append("| Network | Checks | PASS | WARN | FAIL | Overall |")
    lines.append("|---------|--------|------|------|------|---------|")
    for nr in report.network_results:
        status = "PASS" if nr.overall_pass else "FAIL"
        lines.append(
            f"| {nr.network_id} | {nr.total_checks} | {nr.passed} "
            f"| {nr.warned} | {nr.failed} | {status} |"
        )
    lines.append("")

    # Per-network details
    for nr in report.network_results:
        lines.append(f"## {nr.network_id}")
        lines.append("")
        lines.append("| ID | Check | Status | Checked | Failed |")
        lines.append("|------|-------|--------|---------|--------|")
        for c in nr.checks:
            lines.append(
                f"| {c.check_id} | {c.check_name} | {c.status.value} "
                f"| {c.items_checked} | {c.items_failed} |"
            )
        lines.append("")

        # Failure details
        fail_checks = [c for c in nr.checks if c.status == CheckStatus.FAIL]
        if fail_checks:
            lines.append("### Failure Details")
            lines.append("")
            for c in fail_checks:
                lines.append(f"**{c.check_id} ({c.check_name}):** {c.message}")
                lines.append("")
                for d in c.details[:MAX_DETAILS_MD]:
                    lines.append(f"- {d}")
                if len(c.details) > MAX_DETAILS_MD:
                    lines.append(f"- ... and {len(c.details) - MAX_DETAILS_MD} more")
                lines.append("")

    # Cross-phase section
    lines.append("## Cross-Phase Consistency (Check j)")
    lines.append("")
    cp = report.cross_phase
    lines.append(f"- **j-1 BESS column match:** {cp.bess_column_match}")
    lines.append(f"- **j-2 Flowgate column match:** {cp.flowgate_column_match}")
    lines.append(f"- **j-3 All flowgate limits positive:** {cp.all_flowgate_limits_positive}")
    lines.append(f"- **j-4 All BESS cyclic_soc true:** {cp.all_bess_cyclic_soc_true}")
    lines.append("")

    if cp.details:
        lines.append("### Details")
        lines.append("")
        for d in cp.details[:MAX_DETAILS_MD]:
            lines.append(f"- {d}")
        lines.append("")

    dest_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
) -> ValidationReport:
    """Entry point: run Phase 3 cross-deliverable validation for all networks.

    Args:
        timeseries_base_dir: Base directory for input CSVs. Defaults
            to <repo_root>/data/timeseries/.

    Returns:
        A ValidationReport with results for all networks.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_root / "timeseries"

    # Run checks (a-i) for SMALL and MEDIUM
    network_results: list[NetworkValidationResult] = []
    for network_id in PRIMARY_NETWORK_IDS:
        result = validate_network(network_id, timeseries_base_dir)
        network_results.append(result)

    # Run cross-phase consistency check (j)
    tiny_dir = timeseries_base_dir / TINY_NETWORK_ID
    phase3_dirs = {nid: timeseries_base_dir / nid for nid in PRIMARY_NETWORK_IDS}
    cross_phase = check_cross_phase_consistency(tiny_dir, phase3_dirs)

    # Build report
    report = build_validation_report(network_results, cross_phase)

    # Write outputs
    output_dir = repo_root / "validation"
    write_validation_json(report, output_dir / "phase3_validation_results.json")
    write_validation_markdown(report, output_dir / "phase3_validation_report.md")

    # Print summary
    _print_summary(report)

    return report


def _print_summary(report: ValidationReport) -> None:
    """Print a human-readable summary to stdout."""
    print("=" * 72)
    print("Phase 3 Cross-Deliverable Validation Summary")
    print("=" * 72)
    print(f"Script version: {report.script_version}")
    print(f"Overall pass: {report.overall_pass}")
    print(
        f"Total checks: {report.total_checks} "
        f"(PASS: {report.total_passed}, WARN: {report.total_warned}, "
        f"FAIL: {report.total_failed})"
    )
    print()

    for nr in report.network_results:
        status = "ALL PASSED" if nr.overall_pass else "HAS FAILURES"
        print(f"  {nr.network_id}: {status}")
        print(f"    PASS: {nr.passed}, WARN: {nr.warned}, FAIL: {nr.failed}")
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
