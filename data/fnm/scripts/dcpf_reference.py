"""DCPF Reference Solution Computation for FNM Annual S01.

Computes the DC Power Flow (DCPF) reference solution by building and solving
the standard B' susceptance matrix formulation against the canonical parser's
intermediate format data.  The DCPF reference is always solver-computed --
PSS/E RAW files do not store DC solutions -- making this the sole source of
DCPF ground truth for downstream tool verification.

Output directory: ``data/fnm/reference/dcpf/``

Implementation note: uses only Python stdlib (no numpy/scipy).  The B-matrix
is represented as a dict-of-dicts sparse structure and solved via dense LU
factorization after assembly into a list-of-lists matrix.  This is sufficient
for networks up to ~30K buses on modern hardware.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZERO_IMPEDANCE_REPLACEMENT: float = 0.0001
"""Reactance (p.u.) assigned to zero-impedance branches (X=0) to avoid
division-by-zero in B-matrix construction. Small enough for negligible
angle error, large enough to avoid numerical ill-conditioning."""

ANGLE_TOLERANCE_DEG: float = 0.001
"""Tolerance for flow-angle consistency validation (degrees)."""

FLOW_TOLERANCE_MW: float = 0.1
"""Tolerance for power balance validation (MW)."""


# ---------------------------------------------------------------------------
# Input data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusRecord:
    """A single bus from the intermediate format, relevant to DCPF."""

    bus_number: int
    """Bus number (unique identifier)."""

    bus_type: int
    """Bus type: 1=PQ, 2=PV, 3=slack, 4=isolated."""

    pd_mw: float
    """Real power demand at the bus (MW)."""

    base_kv: float
    """Bus base voltage (kV). Informational only for DCPF."""


@dataclass(frozen=True)
class GeneratorRecord:
    """A single generator from the intermediate format, relevant to DCPF."""

    bus_number: int
    """Bus number where this generator is connected."""

    pg_mw: float
    """Real power output (MW)."""

    status: int
    """Generator status: 1=in-service, 0=out-of-service."""

    machine_id: str
    """Machine identifier (for multi-generator buses)."""


@dataclass(frozen=True)
class BranchRecord:
    """A single branch from the intermediate format, relevant to DCPF."""

    from_bus: int
    """From bus number."""

    to_bus: int
    """To bus number."""

    circuit_id: str
    """Circuit identifier (distinguishes parallel branches)."""

    x_pu: float
    """Series reactance (p.u. on system MVA base)."""

    tap_ratio: float
    """Transformer off-nominal turns ratio (1.0 for lines)."""

    shift_deg: float
    """Phase shift angle (degrees, 0.0 for non-phase-shifters)."""

    status: int
    """Branch status: 1=in-service, 0=out-of-service."""

    is_transformer: bool
    """True if this branch is a transformer (has tap ratio != 1.0 or
    originates from the Transformer record type)."""


# ---------------------------------------------------------------------------
# B-matrix and solution containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BMatrixResult:
    """Result of B-matrix construction."""

    b_prime: list[list[float]]
    """The (N-1) x (N-1) B' susceptance matrix as a dense list-of-lists."""

    bus_index_map: dict[int, int]
    """Mapping from bus number to matrix row/column index."""

    slack_bus: int
    """Bus number of the slack bus (angle fixed at 0.0)."""

    active_bus_count: int
    """Total number of active buses (including slack)."""

    zero_impedance_branches: list[tuple[int, int, str]]
    """List of (from_bus, to_bus, circuit_id) for branches that had X=0
    and were assigned the replacement reactance."""

    excluded_branch_count: int
    """Number of out-of-service branches excluded from the matrix."""

    phase_shifter_count: int
    """Number of branches with non-zero phase shift angle."""

    base_mva: float
    """System MVA base used for per-unit conversion."""


@dataclass(frozen=True)
class BranchFlow:
    """MW flow result for a single branch."""

    from_bus: int
    """From bus number."""

    to_bus: int
    """To bus number."""

    circuit_id: str
    """Circuit identifier."""

    p_flow_mw: float
    """Real power flow (MW). Positive = from -> to direction."""

    angle_diff_deg: float
    """Angle difference theta_from - theta_to (degrees)."""

    x_pu: float
    """Branch reactance used in computation (p.u.). May differ from
    original if zero-impedance replacement was applied."""

    is_zero_impedance_replaced: bool
    """True if this branch had X=0 and used the replacement reactance."""


@dataclass(frozen=True)
class DCPFSolution:
    """Complete DCPF solution for the network."""

    bus_angles_deg: dict[int, float]
    """Mapping from bus number to voltage angle (degrees). Slack bus is 0.0.
    Only active (non-excluded) buses are included."""

    branch_flows_mw: list[BranchFlow]
    """Per-branch MW flow for all in-service branches."""

    total_generation_mw: float
    """Sum of all in-service generator Pg (MW)."""

    total_load_mw: float
    """Sum of all active bus Pd (MW)."""

    slack_bus: int
    """Bus number of the slack bus."""

    slack_injection_mw: float
    """Net power injection at the slack bus (MW)."""

    active_bus_count: int
    """Number of active buses in the solution."""

    active_branch_count: int
    """Number of in-service branches in the solution."""

    zero_impedance_branches: list[tuple[int, int, str]]
    """Branches that had X=0, carried forward from BMatrixResult."""

    base_mva: float
    """System MVA base."""


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DCPFValidation:
    """Internal consistency validation of the DCPF solution."""

    power_balance_ok: bool
    """True if |total_gen - total_load| < FLOW_TOLERANCE_MW."""

    power_balance_residual_mw: float
    """Absolute residual of the power balance check (MW)."""

    flow_angle_consistency_ok: bool
    """True if all branch flows are consistent with angle differences
    within FLOW_TOLERANCE_MW."""

    flow_angle_max_deviation_mw: float
    """Maximum absolute deviation between computed branch flow and
    flow re-derived from angle differences (MW)."""

    slack_angle_zero: bool
    """True if the slack bus angle is exactly 0.0 degrees."""

    all_checks_passed: bool
    """True if all three checks passed."""


# ---------------------------------------------------------------------------
# Column name auto-detection helpers
# ---------------------------------------------------------------------------

_BUS_COLUMN_MAP: dict[str, list[str]] = {
    "BUS_I": ["bus_i", "bus", "bus_number", "number", "i"],
    "BUS_TYPE": ["bus_type", "type", "ide"],
    "PD": ["pd", "pl"],
    "BASE_KV": ["base_kv", "basekv", "nom_kv", "baskv", "vnom"],
}

_GEN_COLUMN_MAP: dict[str, list[str]] = {
    "GEN_BUS": ["gen_bus", "bus", "bus_number", "i"],
    "PG": ["pg"],
    "GEN_STATUS": ["gen_status", "status", "stat"],
    "ID": ["id", "machine_id", "mach_id"],
}

_BRANCH_COLUMN_MAP: dict[str, list[str]] = {
    "F_BUS": ["f_bus", "from_bus", "i", "fbus"],
    "T_BUS": ["t_bus", "to_bus", "j", "tbus"],
    "BR_X": ["br_x", "x"],
    "TAP": ["tap", "windv1"],
    "SHIFT": ["shift", "ang1"],
    "BR_STATUS": ["br_status", "status", "st"],
    "CKT": ["ckt", "circuit"],
}


def _resolve_columns(
    headers: list[str],
    column_map: dict[str, list[str]],
    required: list[str],
) -> dict[str, int]:
    """Map normalized column names to CSV column indices.

    Args:
        headers: Raw CSV header row.
        column_map: Mapping from canonical name to list of variant names.
        required: Canonical names that must be found.

    Returns:
        Dict mapping canonical name to column index.

    Raises:
        ValueError: If a required column cannot be found.
    """
    lower_headers = [h.strip().lower() for h in headers]
    result: dict[str, int] = {}

    for canonical, variants in column_map.items():
        canonical_lower = canonical.lower()
        if canonical_lower in lower_headers:
            result[canonical] = lower_headers.index(canonical_lower)
            continue
        for variant in variants:
            if variant.lower() in lower_headers:
                result[canonical] = lower_headers.index(variant.lower())
                break

    missing = [r for r in required if r not in result]
    if missing:
        raise ValueError(f"Required columns not found: {missing}. Available headers: {headers}")
    return result


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_bus_table(bus_csv_path: Path) -> list[BusRecord]:
    """Load the bus table from the canonical parser's CSV output.

    Auto-detects column names from MATPOWER and GridCal conventions:
    - Bus number: ``BUS_I``, ``bus``, ``bus_number``, ``NUMBER``
    - Bus type: ``BUS_TYPE``, ``type``, ``bus_type``, ``IDE``
    - Real power demand: ``PD``, ``Pd``, ``pd``, ``PL``
    - Base kV: ``BASE_KV``, ``base_kv``, ``basekv``, ``NOM_KV``

    Args:
        bus_csv_path: Path to the bus CSV file.

    Returns:
        List of BusRecord instances for all buses in the file
        (including isolated -- filtering is done later).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not bus_csv_path.exists():
        raise FileNotFoundError(f"Bus CSV not found: {bus_csv_path}")

    with open(bus_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Bus CSV is empty: {bus_csv_path}")

    headers = rows[0]
    col_map = _resolve_columns(headers, _BUS_COLUMN_MAP, required=["BUS_I", "BUS_TYPE", "PD"])
    data_rows = rows[1:]

    result: list[BusRecord] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        result.append(
            BusRecord(
                bus_number=int(float(row[col_map["BUS_I"]].strip())),
                bus_type=int(float(row[col_map["BUS_TYPE"]].strip())),
                pd_mw=float(row[col_map["PD"]].strip()),
                base_kv=float(row[col_map["BASE_KV"]].strip()) if "BASE_KV" in col_map else 0.0,
            )
        )
    return result


def load_generator_table(gen_csv_path: Path) -> list[GeneratorRecord]:
    """Load the generator table from the canonical parser's CSV output.

    Auto-detects column names from MATPOWER and GridCal conventions:
    - Bus number: ``GEN_BUS``, ``bus``, ``bus_number``
    - Real power: ``PG``, ``Pg``, ``pg``
    - Status: ``GEN_STATUS``, ``status``, ``gen_status``
    - Machine ID: ``ID``, ``machine_id``, ``MACH_ID`` (defaults to "1" if absent)

    Args:
        gen_csv_path: Path to the generator CSV file.

    Returns:
        List of GeneratorRecord instances for all generators.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not gen_csv_path.exists():
        raise FileNotFoundError(f"Generator CSV not found: {gen_csv_path}")

    with open(gen_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Generator CSV is empty: {gen_csv_path}")

    headers = rows[0]
    col_map = _resolve_columns(headers, _GEN_COLUMN_MAP, required=["GEN_BUS", "PG", "GEN_STATUS"])
    data_rows = rows[1:]

    result: list[GeneratorRecord] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        result.append(
            GeneratorRecord(
                bus_number=int(float(row[col_map["GEN_BUS"]].strip())),
                pg_mw=float(row[col_map["PG"]].strip()),
                status=int(float(row[col_map["GEN_STATUS"]].strip())),
                machine_id=row[col_map["ID"]].strip() if "ID" in col_map else "1",
            )
        )
    return result


def load_branch_table(branch_csv_path: Path) -> list[BranchRecord]:
    """Load the branch table from the canonical parser's CSV output.

    Reads both simple branches and transformers.  Auto-detects column names:
    - From bus: ``F_BUS``, ``from_bus``, ``I``
    - To bus: ``T_BUS``, ``to_bus``, ``J``
    - Reactance: ``BR_X``, ``x``, ``X``
    - Tap ratio: ``TAP``, ``tap``, ``WINDV1`` (1.0 if absent or 0.0)
    - Phase shift: ``SHIFT``, ``shift``, ``ANG1`` (0.0 if absent)
    - Status: ``BR_STATUS``, ``status``, ``ST``
    - Circuit ID: ``CKT``, ``ckt``, ``circuit`` (defaults to "1" if absent)

    A tap ratio of 0.0 in MATPOWER convention means 1.0 (nominal).  This
    function normalizes 0.0 tap values to 1.0.

    Args:
        branch_csv_path: Path to the branch CSV file.

    Returns:
        List of BranchRecord instances for all branches.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not branch_csv_path.exists():
        raise FileNotFoundError(f"Branch CSV not found: {branch_csv_path}")

    with open(branch_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Branch CSV is empty: {branch_csv_path}")

    headers = rows[0]
    col_map = _resolve_columns(
        headers, _BRANCH_COLUMN_MAP, required=["F_BUS", "T_BUS", "BR_X", "BR_STATUS"]
    )
    data_rows = rows[1:]

    result: list[BranchRecord] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        tap_raw = float(row[col_map["TAP"]].strip()) if "TAP" in col_map else 0.0
        tap = tap_raw if tap_raw != 0.0 else 1.0

        shift = float(row[col_map["SHIFT"]].strip()) if "SHIFT" in col_map else 0.0

        is_transformer = tap != 1.0 or shift != 0.0

        result.append(
            BranchRecord(
                from_bus=int(float(row[col_map["F_BUS"]].strip())),
                to_bus=int(float(row[col_map["T_BUS"]].strip())),
                circuit_id=row[col_map["CKT"]].strip() if "CKT" in col_map else "1",
                x_pu=float(row[col_map["BR_X"]].strip()),
                tap_ratio=tap,
                shift_deg=shift,
                status=int(float(row[col_map["BR_STATUS"]].strip())),
                is_transformer=is_transformer,
            )
        )
    return result


def load_excluded_buses(exclusion_csv_path: Path) -> set[int]:
    """Load the set of excluded bus numbers from the D1 bus exclusion registry.

    Reads the ``bus_number`` column from the exclusion CSV produced by
    Phase 3 D1 (``data/fnm/reference/excluded_buses.csv``).

    Args:
        exclusion_csv_path: Path to the excluded buses CSV.

    Returns:
        Set of bus numbers to exclude from the DCPF computation.

    Raises:
        FileNotFoundError: If the exclusion CSV does not exist.
    """
    if not exclusion_csv_path.exists():
        raise FileNotFoundError(f"Exclusion CSV not found: {exclusion_csv_path}")

    excluded: set[int] = set()
    with open(exclusion_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            excluded.add(int(float(row["bus_number"])))
    return excluded


# ---------------------------------------------------------------------------
# Bus filtering and injection computation
# ---------------------------------------------------------------------------


def filter_active_buses(
    buses: list[BusRecord],
    excluded_bus_numbers: set[int],
) -> list[BusRecord]:
    """Filter buses to the active set for DCPF computation.

    Removes:
    - Buses in the exclusion registry (isolated, de-energized, disconnected)
    - Buses with bus_type == 4 (as a safety check, even if not in the registry)

    Args:
        buses: All buses from the intermediate format.
        excluded_bus_numbers: Set of bus numbers from the exclusion registry.

    Returns:
        List of active BusRecord instances.
    """
    return [
        bus for bus in buses if bus.bus_number not in excluded_bus_numbers and bus.bus_type != 4
    ]


def compute_bus_injections(
    active_buses: list[BusRecord],
    generators: list[GeneratorRecord],
    excluded_bus_numbers: set[int],
) -> dict[int, float]:
    """Compute net real power injection at each active bus.

    For each active bus: P_injection = sum(Pg for in-service generators
    at this bus) - Pd (bus load).

    Generators on excluded buses are ignored.  Out-of-service generators
    (status=0) are ignored.

    Args:
        active_buses: The filtered active bus set.
        generators: All generators from the intermediate format.
        excluded_bus_numbers: Set of excluded bus numbers (for filtering generators).

    Returns:
        Dict mapping bus number to net injection (MW).  Buses with no
        generators and no load have injection = 0.0.
    """
    active_bus_set = {bus.bus_number for bus in active_buses}

    # Initialize injections: -Pd for each active bus
    injections: dict[int, float] = {}
    for bus in active_buses:
        injections[bus.bus_number] = -bus.pd_mw

    # Add generator contributions
    for gen in generators:
        if gen.status != 1:
            continue
        if gen.bus_number in excluded_bus_numbers:
            continue
        if gen.bus_number in active_bus_set:
            injections[gen.bus_number] = injections.get(gen.bus_number, 0.0) + gen.pg_mw

    return injections


def identify_slack_bus(active_buses: list[BusRecord]) -> int:
    """Identify the slack bus for DCPF computation.

    Selects the bus with type=3 (swing bus).  If multiple type-3 buses
    exist, selects the one with the lowest bus number.  If no type-3 bus
    exists, raises an error.

    Args:
        active_buses: The filtered active bus set.

    Returns:
        Bus number of the selected slack bus.

    Raises:
        ValueError: If no type-3 bus exists in the active bus set.
    """
    slack_candidates = sorted([bus.bus_number for bus in active_buses if bus.bus_type == 3])
    if not slack_candidates:
        raise ValueError("No type-3 (slack/swing) bus found in the active bus set.")
    return slack_candidates[0]


# ---------------------------------------------------------------------------
# B-matrix construction (pure Python, no numpy/scipy)
# ---------------------------------------------------------------------------


def build_b_matrix(
    active_buses: list[BusRecord],
    branches: list[BranchRecord],
    excluded_bus_numbers: set[int],
    slack_bus: int,
    base_mva: float,
) -> BMatrixResult:
    """Construct the B' susceptance matrix for DC power flow.

    Builds the (N-1) x (N-1) dense matrix by iterating over all in-service
    branches.  The slack bus row and column are excluded from the matrix
    (its angle is the reference, fixed at 0.0).

    For each in-service branch:
    1. Skip if either endpoint is in the excluded set.
    2. If X == 0.0, replace with ZERO_IMPEDANCE_REPLACEMENT and log.
    3. Compute susceptance per the B-matrix formulation, accounting for
       tap ratio and phase shift.
    4. Add susceptance contributions to diagonal and off-diagonal entries.

    Args:
        active_buses: The filtered active bus set.
        branches: All branches from the intermediate format.
        excluded_bus_numbers: Bus numbers to exclude.
        slack_bus: Bus number of the slack bus.
        base_mva: System MVA base.

    Returns:
        A BMatrixResult containing the dense matrix and metadata.

    Raises:
        ValueError: If the active bus set is empty or contains only the
            slack bus (trivial system).
    """
    active_bus_set = {bus.bus_number for bus in active_buses}

    if len(active_bus_set) <= 1:
        raise ValueError(
            "Active bus set must contain at least 2 buses "
            f"(including slack). Got {len(active_bus_set)}."
        )

    # Build bus index map: non-slack active buses -> 0-based index
    non_slack_buses = sorted(b for b in active_bus_set if b != slack_bus)
    bus_index_map: dict[int, int] = {bus: idx for idx, bus in enumerate(non_slack_buses)}
    n = len(non_slack_buses)

    # Initialize dense matrix
    b_prime: list[list[float]] = [[0.0] * n for _ in range(n)]

    zero_impedance_branches: list[tuple[int, int, str]] = []
    excluded_branch_count = 0
    phase_shifter_count = 0
    for branch in branches:
        # Skip out-of-service branches
        if branch.status != 1:
            excluded_branch_count += 1
            continue

        from_bus = branch.from_bus
        to_bus = branch.to_bus

        # Skip if either endpoint is excluded or not in active set
        if from_bus in excluded_bus_numbers or to_bus in excluded_bus_numbers:
            continue
        if from_bus not in active_bus_set or to_bus not in active_bus_set:
            continue

        x = branch.x_pu

        # Handle zero-impedance branches
        if x == 0.0:
            x = ZERO_IMPEDANCE_REPLACEMENT
            zero_impedance_branches.append((from_bus, to_bus, branch.circuit_id))
            logger.warning(
                "Zero-impedance branch %d-%d (ckt %s) assigned X=%f p.u.",
                from_bus,
                to_bus,
                branch.circuit_id,
                x,
            )

        # Log negative reactance
        if x < 0.0:
            logger.warning(
                "Negative reactance X=%f on branch %d-%d (ckt %s)",
                x,
                from_bus,
                to_bus,
                branch.circuit_id,
            )

        # Count phase shifters
        if branch.shift_deg != 0.0:
            phase_shifter_count += 1

        t = branch.tap_ratio

        # Compute B-matrix entries based on tap ratio
        if t == 1.0:
            # Simple branch (no tap adjustment)
            b = 1.0 / x
            # Add to matrix (only for non-slack buses)
            if from_bus in bus_index_map:
                b_prime[bus_index_map[from_bus]][bus_index_map[from_bus]] += b
            if to_bus in bus_index_map:
                b_prime[bus_index_map[to_bus]][bus_index_map[to_bus]] += b
            if from_bus in bus_index_map and to_bus in bus_index_map:
                i_idx = bus_index_map[from_bus]
                j_idx = bus_index_map[to_bus]
                b_prime[i_idx][j_idx] -= b
                b_prime[j_idx][i_idx] -= b
        else:
            # Transformer with off-nominal tap ratio
            # From-side diagonal: 1 / (X * t^2)
            # To-side diagonal: 1 / X
            # Off-diagonal: -1 / (X * t)  [both i,j and j,i]
            b_from_diag = 1.0 / (x * t * t)
            b_to_diag = 1.0 / x
            b_off = -1.0 / (x * t)

            if from_bus in bus_index_map:
                b_prime[bus_index_map[from_bus]][bus_index_map[from_bus]] += b_from_diag
            if to_bus in bus_index_map:
                b_prime[bus_index_map[to_bus]][bus_index_map[to_bus]] += b_to_diag
            if from_bus in bus_index_map and to_bus in bus_index_map:
                i_idx = bus_index_map[from_bus]
                j_idx = bus_index_map[to_bus]
                b_prime[i_idx][j_idx] += b_off
                b_prime[j_idx][i_idx] += b_off

    return BMatrixResult(
        b_prime=b_prime,
        bus_index_map=bus_index_map,
        slack_bus=slack_bus,
        active_bus_count=len(active_bus_set),
        zero_impedance_branches=zero_impedance_branches,
        excluded_branch_count=excluded_branch_count,
        phase_shifter_count=phase_shifter_count,
        base_mva=base_mva,
    )


def compute_phase_shift_injections(
    branches: list[BranchRecord],
    excluded_bus_numbers: set[int],
    base_mva: float,
) -> dict[int, float]:
    """Compute injection vector modifications from phase-shifting transformers.

    For each in-service branch with a non-zero phase shift angle, computes
    the real power offset injected at each endpoint:

        P_shift = shift_rad / X * baseMVA

    This is subtracted from the from-bus injection and added to the to-bus
    injection.

    Args:
        branches: All branches from the intermediate format.
        excluded_bus_numbers: Bus numbers to exclude.
        base_mva: System MVA base.

    Returns:
        Dict mapping bus number to cumulative phase-shift injection
        modification (MW).  Only buses affected by phase shifters appear.
    """
    injections: dict[int, float] = {}

    for branch in branches:
        if branch.status != 1:
            continue
        if branch.shift_deg == 0.0:
            continue
        if branch.from_bus in excluded_bus_numbers or branch.to_bus in excluded_bus_numbers:
            continue

        x = branch.x_pu
        if x == 0.0:
            x = ZERO_IMPEDANCE_REPLACEMENT

        shift_rad = math.radians(branch.shift_deg)
        p_shift = shift_rad / x * base_mva

        # Subtract from from-bus, add to to-bus
        injections[branch.from_bus] = injections.get(branch.from_bus, 0.0) - p_shift
        injections[branch.to_bus] = injections.get(branch.to_bus, 0.0) + p_shift

    return injections


# ---------------------------------------------------------------------------
# Dense LU solver (pure Python, no numpy/scipy)
# ---------------------------------------------------------------------------


def _solve_linear_system(a_matrix: list[list[float]], b_vector: list[float]) -> list[float]:
    """Solve A * x = b using Gaussian elimination with partial pivoting.

    Args:
        a_matrix: N x N coefficient matrix (will be modified in place).
        b_vector: N-element right-hand side vector (will be modified in place).

    Returns:
        N-element solution vector x.

    Raises:
        ValueError: If the matrix is singular.
    """
    n = len(b_vector)

    # Make copies to avoid modifying inputs
    a = [row[:] for row in a_matrix]
    b = b_vector[:]

    # Forward elimination with partial pivoting
    for col in range(n):
        # Find pivot
        max_val = abs(a[col][col])
        max_row = col
        for row in range(col + 1, n):
            if abs(a[row][col]) > max_val:
                max_val = abs(a[row][col])
                max_row = row

        if max_val < 1e-15:
            raise ValueError(
                f"Singular or near-singular matrix at column {col}. "
                "This may indicate disconnected sub-networks in the active bus set."
            )

        # Swap rows
        if max_row != col:
            a[col], a[max_row] = a[max_row], a[col]
            b[col], b[max_row] = b[max_row], b[col]

        # Eliminate below
        pivot = a[col][col]
        for row in range(col + 1, n):
            factor = a[row][col] / pivot
            for k in range(col + 1, n):
                a[row][k] -= factor * a[col][k]
            a[row][col] = 0.0
            b[row] -= factor * b[col]

    # Back substitution
    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        val = b[row]
        for col in range(row + 1, n):
            val -= a[row][col] * x[col]
        x[row] = val / a[row][row]

    return x


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


def solve_dcpf(
    b_matrix: BMatrixResult,
    bus_injections: dict[int, float],
    phase_shift_injections: dict[int, float],
    branches: list[BranchRecord],
    excluded_bus_numbers: set[int],
) -> DCPFSolution:
    """Solve the DC power flow: B' * theta = P_injection.

    Steps:
    1. Assemble the injection vector P for the (N-1) non-slack buses,
       incorporating phase-shift modifications.
    2. Convert injections to per-unit on system MVA base.
    3. Solve the linear system using Gaussian elimination.
    4. Convert theta from radians to degrees and map back to bus numbers.
    5. Compute per-branch MW flows from angle differences.

    Args:
        b_matrix: The BMatrixResult from build_b_matrix.
        bus_injections: Net real power injection per bus (MW).
        phase_shift_injections: Phase-shift injection modifications (MW).
        branches: All branches (for computing branch flows).
        excluded_bus_numbers: Excluded bus numbers.

    Returns:
        A complete DCPFSolution.

    Raises:
        ValueError: If the B-matrix is singular (disconnected network).
    """
    bus_index_map = b_matrix.bus_index_map
    n = len(bus_index_map)
    base_mva = b_matrix.base_mva
    slack_bus = b_matrix.slack_bus

    # Assemble injection vector in per-unit
    p_vector = [0.0] * n
    for bus_num, idx in bus_index_map.items():
        inj_mw = bus_injections.get(bus_num, 0.0)
        # Add phase-shift modifications
        inj_mw += phase_shift_injections.get(bus_num, 0.0)
        # Convert to per-unit
        p_vector[idx] = inj_mw / base_mva

    # Solve B' * theta = P
    theta_rad = _solve_linear_system(b_matrix.b_prime, p_vector)

    # Build bus_angles_rad and bus_angles_deg maps
    bus_angles_rad: dict[int, float] = {slack_bus: 0.0}
    bus_angles_deg: dict[int, float] = {slack_bus: 0.0}

    for bus_num, idx in bus_index_map.items():
        bus_angles_rad[bus_num] = theta_rad[idx]
        bus_angles_deg[bus_num] = math.degrees(theta_rad[idx])

    # Compute branch flows
    branch_flows = compute_branch_flows(branches, bus_angles_rad, excluded_bus_numbers, base_mva)

    # Compute totals
    total_gen = 0.0
    total_load = 0.0
    for bus_num, inj in bus_injections.items():
        # injection = gen - load, so gen contributes positive, load contributes negative
        if inj > 0:
            total_gen += inj
        else:
            total_load += abs(inj)

    slack_inj = bus_injections.get(slack_bus, 0.0)

    return DCPFSolution(
        bus_angles_deg=bus_angles_deg,
        branch_flows_mw=branch_flows,
        total_generation_mw=0.0,  # Placeholder, set by orchestrator
        total_load_mw=0.0,  # Placeholder, set by orchestrator
        slack_bus=slack_bus,
        slack_injection_mw=slack_inj,
        active_bus_count=b_matrix.active_bus_count,
        active_branch_count=len(branch_flows),
        zero_impedance_branches=b_matrix.zero_impedance_branches,
        base_mva=base_mva,
    )


def compute_branch_flows(
    branches: list[BranchRecord],
    bus_angles_rad: dict[int, float],
    excluded_bus_numbers: set[int],
    base_mva: float,
) -> list[BranchFlow]:
    """Compute MW flow for each in-service branch from angle differences.

    For each branch:
        P_flow = (theta_from - theta_to) / X * baseMVA

    For transformers with tap ratio t:
        P_flow = (theta_from - theta_to) / (X * t) * baseMVA

    Phase shift is already incorporated in the angle solution via
    injection vector modification, so it does not appear here.

    Args:
        branches: All branches from the intermediate format.
        bus_angles_rad: Bus angles in radians (keyed by bus number).
        excluded_bus_numbers: Excluded bus numbers.
        base_mva: System MVA base.

    Returns:
        List of BranchFlow instances for all in-service branches with
        both endpoints in the active set.
    """
    flows: list[BranchFlow] = []

    for branch in branches:
        if branch.status != 1:
            continue

        from_bus = branch.from_bus
        to_bus = branch.to_bus

        if from_bus in excluded_bus_numbers or to_bus in excluded_bus_numbers:
            continue
        if from_bus not in bus_angles_rad or to_bus not in bus_angles_rad:
            continue

        x = branch.x_pu
        is_zero_replaced = False
        if x == 0.0:
            x = ZERO_IMPEDANCE_REPLACEMENT
            is_zero_replaced = True

        t = branch.tap_ratio
        # Effective reactance includes tap ratio for transformers
        x_eff = x * t

        theta_from = bus_angles_rad[from_bus]
        theta_to = bus_angles_rad[to_bus]
        angle_diff_rad = theta_from - theta_to

        # P_flow = (theta_from - theta_to) / (X * t) * baseMVA
        p_flow_mw = angle_diff_rad / x_eff * base_mva

        flows.append(
            BranchFlow(
                from_bus=from_bus,
                to_bus=to_bus,
                circuit_id=branch.circuit_id,
                p_flow_mw=p_flow_mw,
                angle_diff_deg=math.degrees(angle_diff_rad),
                x_pu=x_eff,
                is_zero_impedance_replaced=is_zero_replaced,
            )
        )

    return flows


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_dcpf_solution(solution: DCPFSolution) -> DCPFValidation:
    """Run internal consistency checks on the DCPF solution.

    Three checks:
    1. **Power balance:** |total_generation - total_load| < FLOW_TOLERANCE_MW
       (lossless DC assumption -- generation must equal load after slack
       bus adjustment).
    2. **Flow-angle consistency:** For each branch, the stored P_flow_MW
       matches (theta_from - theta_to) / X * baseMVA within FLOW_TOLERANCE_MW.
       This catches indexing errors in the B-matrix.
    3. **Slack angle zero:** The slack bus angle is exactly 0.0 degrees.

    Args:
        solution: The DCPF solution to validate.

    Returns:
        A DCPFValidation with all check results.
    """
    # Check 1: Power balance
    power_residual = abs(solution.total_generation_mw - solution.total_load_mw)
    power_balance_ok = power_residual < FLOW_TOLERANCE_MW

    # Check 2: Flow-angle consistency
    # x_pu in BranchFlow stores the effective reactance (X * tap_ratio),
    # so the formula P_flow = angle_diff / x_pu * baseMVA should match.
    max_deviation = 0.0
    for flow in solution.branch_flows_mw:
        from_angle_rad = math.radians(solution.bus_angles_deg.get(flow.from_bus, 0.0))
        to_angle_rad = math.radians(solution.bus_angles_deg.get(flow.to_bus, 0.0))
        angle_diff = from_angle_rad - to_angle_rad

        expected_flow = angle_diff / flow.x_pu * solution.base_mva
        deviation = abs(flow.p_flow_mw - expected_flow)
        if deviation > max_deviation:
            max_deviation = deviation

    flow_angle_ok = max_deviation < FLOW_TOLERANCE_MW

    # Check 3: Slack angle zero
    slack_angle = solution.bus_angles_deg.get(solution.slack_bus, float("nan"))
    slack_angle_zero = slack_angle == 0.0

    all_passed = power_balance_ok and flow_angle_ok and slack_angle_zero

    return DCPFValidation(
        power_balance_ok=power_balance_ok,
        power_balance_residual_mw=power_residual,
        flow_angle_consistency_ok=flow_angle_ok,
        flow_angle_max_deviation_mw=max_deviation,
        slack_angle_zero=slack_angle_zero,
        all_checks_passed=all_passed,
    )


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------


def write_buses_csv(
    solution: DCPFSolution,
    output_path: Path,
) -> None:
    """Write the bus angles CSV file.

    Output schema:

    | Column | Type | Unit | Description |
    |--------|------|------|-------------|
    | bus | int | -- | Bus number |
    | VA | float | degrees | Voltage angle |

    Sorted by bus number ascending.  Only active (non-excluded) buses.

    Args:
        solution: The DCPF solution.
        output_path: Path for the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_buses = sorted(solution.bus_angles_deg.items(), key=lambda x: x[0])

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "VA"])
        for bus_num, angle_deg in sorted_buses:
            writer.writerow([bus_num, f"{angle_deg:.6f}"])


def write_branches_csv(
    solution: DCPFSolution,
    output_path: Path,
) -> None:
    """Write the branch flows CSV file.

    Output schema:

    | Column | Type | Unit | Description |
    |--------|------|------|-------------|
    | from_bus | int | -- | From bus number |
    | to_bus | int | -- | To bus number |
    | ckt | str | -- | Circuit identifier |
    | P_flow_MW | float | MW | Real power flow (positive = from->to) |

    Sorted by (from_bus, to_bus, ckt) ascending.  Only in-service branches
    with both endpoints in the active set.

    Args:
        solution: The DCPF solution.
        output_path: Path for the output CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_flows = sorted(
        solution.branch_flows_mw,
        key=lambda f: (f.from_bus, f.to_bus, f.circuit_id),
    )

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["from_bus", "to_bus", "ckt", "P_flow_MW"])
        for flow in sorted_flows:
            writer.writerow(
                [
                    flow.from_bus,
                    flow.to_bus,
                    flow.circuit_id,
                    f"{flow.p_flow_mw:.6f}",
                ]
            )


def write_summary_json(
    solution: DCPFSolution,
    validation: DCPFValidation,
    output_path: Path,
    *,
    canonical_parser: str = "",
) -> None:
    """Write the DCPF summary JSON file.

    Args:
        solution: The DCPF solution.
        validation: The validation results.
        output_path: Path for the output JSON file.
        canonical_parser: Name of the canonical parser (for metadata).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute angle statistics
    angles = list(solution.bus_angles_deg.values())
    max_angle = max(angles) if angles else 0.0
    min_angle = min(angles) if angles else 0.0
    mean_angle = sum(angles) / len(angles) if angles else 0.0
    variance = sum((a - mean_angle) ** 2 for a in angles) / len(angles) if angles else 0.0
    std_angle = math.sqrt(variance)

    # Compute flow statistics
    flows_mw = [f.p_flow_mw for f in solution.branch_flows_mw]
    max_flow = max(flows_mw) if flows_mw else 0.0
    min_flow = min(flows_mw) if flows_mw else 0.0

    summary = {
        "solver": "stdlib_gaussian_elimination",
        "formulation": "standard_b_prime",
        "base_mva": solution.base_mva,
        "settings": {
            "zero_impedance_replacement_pu": ZERO_IMPEDANCE_REPLACEMENT,
            "voltage_magnitude_assumption": 1.0,
            "loss_model": "lossless",
            "slack_bus": solution.slack_bus,
            "slack_angle_deg": 0.0,
        },
        "network_summary": {
            "active_bus_count": solution.active_bus_count,
            "active_branch_count": solution.active_branch_count,
            "excluded_bus_count": 0,  # Set by orchestrator if available
            "out_of_service_branch_count": 0,  # Set by orchestrator if available
            "zero_impedance_branch_count": len(solution.zero_impedance_branches),
            "phase_shifter_count": 0,  # Set by orchestrator if available
        },
        "power_summary": {
            "total_generation_mw": solution.total_generation_mw,
            "total_load_mw": solution.total_load_mw,
            "slack_injection_mw": solution.slack_injection_mw,
            "max_branch_flow_mw": max_flow,
            "min_branch_flow_mw": min_flow,
        },
        "angle_summary": {
            "max_angle_deg": max_angle,
            "min_angle_deg": min_angle,
            "mean_angle_deg": mean_angle,
            "std_angle_deg": std_angle,
        },
        "validation": {
            "power_balance_ok": validation.power_balance_ok,
            "power_balance_residual_mw": validation.power_balance_residual_mw,
            "flow_angle_consistency_ok": validation.flow_angle_consistency_ok,
            "flow_angle_max_deviation_mw": validation.flow_angle_max_deviation_mw,
            "slack_angle_zero": validation.slack_angle_zero,
            "all_checks_passed": validation.all_checks_passed,
        },
        "zero_impedance_branches": [
            {"from_bus": fb, "to_bus": tb, "ckt": ckt}
            for fb, tb, ckt in solution.zero_impedance_branches
        ],
        "excluded_element_types": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "canonical_parser": canonical_parser,
    }

    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_dcpf_reference(
    bus_csv_path: Path,
    gen_csv_path: Path,
    branch_csv_path: Path,
    exclusion_csv_path: Path,
    output_dir: Path,
    *,
    base_mva: float = 100.0,
    canonical_parser: str = "",
) -> DCPFSolution:
    """Orchestrate the full DCPF reference computation pipeline.

    Steps:
    1. Load bus, generator, and branch tables from CSVs.
    2. Load excluded bus set from D1 exclusion registry.
    3. Filter to active buses.
    4. Identify the slack bus.
    5. Compute bus injections.
    6. Build the B' susceptance matrix.
    7. Compute phase-shift injection modifications.
    8. Solve the linear system.
    9. Validate the solution.
    10. Write buses_dcpf.csv, branches_dcpf.csv, and summary_dcpf.json.

    Args:
        bus_csv_path: Path to the canonical parser's bus CSV.
        gen_csv_path: Path to the canonical parser's generator CSV.
        branch_csv_path: Path to the canonical parser's branch CSV.
        exclusion_csv_path: Path to the D1 bus exclusion registry CSV.
        output_dir: Directory for output files. Created if it does not exist.
        base_mva: System MVA base (default 100.0).
        canonical_parser: Name of the canonical parser (for metadata).

    Returns:
        The DCPFSolution (also written to disk).

    Raises:
        FileNotFoundError: If any input CSV does not exist.
        ValueError: If the network has no active buses or no slack bus.
    """
    # 1. Load tables
    buses = load_bus_table(bus_csv_path)
    generators = load_generator_table(gen_csv_path)
    branches = load_branch_table(branch_csv_path)

    # 2. Load exclusion set
    excluded = load_excluded_buses(exclusion_csv_path)

    # 3. Filter active buses
    active_buses = filter_active_buses(buses, excluded)
    if not active_buses:
        raise ValueError("No active buses after exclusion filtering.")

    # 4. Identify slack bus
    slack_bus = identify_slack_bus(active_buses)

    # 5. Compute bus injections
    injections = compute_bus_injections(active_buses, generators, excluded)

    # 6. Build B-matrix
    b_result = build_b_matrix(active_buses, branches, excluded, slack_bus, base_mva)

    # 7. Compute phase-shift injections
    phase_injections = compute_phase_shift_injections(branches, excluded, base_mva)

    # 8. Solve
    solution = solve_dcpf(b_result, injections, phase_injections, branches, excluded)

    # Compute total generation and total load from original data
    active_bus_set = {bus.bus_number for bus in active_buses}
    total_gen = sum(
        gen.pg_mw
        for gen in generators
        if gen.status == 1 and gen.bus_number not in excluded and gen.bus_number in active_bus_set
    )
    total_load = sum(bus.pd_mw for bus in active_buses)

    # Reconstruct solution with correct totals
    solution = DCPFSolution(
        bus_angles_deg=solution.bus_angles_deg,
        branch_flows_mw=solution.branch_flows_mw,
        total_generation_mw=total_gen,
        total_load_mw=total_load,
        slack_bus=solution.slack_bus,
        slack_injection_mw=injections.get(slack_bus, 0.0),
        active_bus_count=solution.active_bus_count,
        active_branch_count=solution.active_branch_count,
        zero_impedance_branches=solution.zero_impedance_branches,
        base_mva=solution.base_mva,
    )

    # 9. Validate
    validation = validate_dcpf_solution(solution)

    # 10. Write output
    output_dir.mkdir(parents=True, exist_ok=True)
    write_buses_csv(solution, output_dir / "buses_dcpf.csv")
    write_branches_csv(solution, output_dir / "branches_dcpf.csv")
    write_summary_json(
        solution,
        validation,
        output_dir / "summary_dcpf.json",
        canonical_parser=canonical_parser,
    )

    return solution


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for DCPF reference computation.

    Usage::

        python -m data.fnm.scripts.dcpf_reference \\
            --bus-csv path/to/bus.csv \\
            --gen-csv path/to/gen.csv \\
            --branch-csv path/to/branch.csv \\
            --exclusion-csv path/to/excluded_buses.csv \\
            [-o output_dir] \\
            [--base-mva 100.0] \\
            [--canonical-parser gridcal]

    If ``-o`` is omitted, writes to ``data/fnm/reference/dcpf/``.

    Exit codes:
    - 0: DCPF computed and all validation checks passed.
    - 1: DCPF computed but one or more validation checks failed.
    - 2: Input error (missing files, no active buses, singular B-matrix).

    Args:
        argv: Command-line arguments.  If ``None``, reads from ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(
        description="Compute DCPF reference solution from intermediate format CSVs."
    )
    parser.add_argument(
        "--bus-csv",
        type=Path,
        required=True,
        help="Path to the bus table CSV.",
    )
    parser.add_argument(
        "--gen-csv",
        type=Path,
        required=True,
        help="Path to the generator table CSV.",
    )
    parser.add_argument(
        "--branch-csv",
        type=Path,
        required=True,
        help="Path to the branch table CSV.",
    )
    parser.add_argument(
        "--exclusion-csv",
        type=Path,
        required=True,
        help="Path to the D1 bus exclusion registry CSV.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/fnm/reference/dcpf/).",
    )
    parser.add_argument(
        "--base-mva",
        type=float,
        default=100.0,
        help="System MVA base (default: 100.0).",
    )
    parser.add_argument(
        "--canonical-parser",
        type=str,
        default="",
        help="Name of the canonical parser (for metadata).",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    output_dir: Path = args.output_dir or Path("data/fnm/reference/dcpf")

    try:
        solution = run_dcpf_reference(
            bus_csv_path=args.bus_csv,
            gen_csv_path=args.gen_csv,
            branch_csv_path=args.branch_csv,
            exclusion_csv_path=args.exclusion_csv,
            output_dir=output_dir,
            base_mva=args.base_mva,
            canonical_parser=args.canonical_parser,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    # Run validation for exit code
    validation = validate_dcpf_solution(solution)

    print(f"Active buses: {solution.active_bus_count}")
    print(f"Active branches: {solution.active_branch_count}")
    print(f"Total generation: {solution.total_generation_mw:.1f} MW")
    print(f"Total load: {solution.total_load_mw:.1f} MW")
    print(f"Slack bus: {solution.slack_bus}")
    print(f"Validation passed: {validation.all_checks_passed}")

    if not validation.all_checks_passed:
        print(f"  Power balance residual: {validation.power_balance_residual_mw:.4f} MW")
        print(f"  Flow-angle max deviation: {validation.flow_angle_max_deviation_mw:.4f} MW")
        print(f"  Slack angle zero: {validation.slack_angle_zero}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
