"""BESS Unit Placement & Sizing for SMALL and MEDIUM networks.

Selects battery energy storage system (BESS) placement buses using a composite
score combining normalized bus load and inverse peak branch utilization, then
sizes a heterogeneous fleet targeting 3-5% of system peak load. Intensive
parameters (efficiency, SoC bounds) come from the Phase 3 D1 storage reference;
extensive parameters (power, energy, ramp) are scaled proportionally.

Output: bess_units.csv and bess_placement_rationale.csv per network.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class BessNetworkId(StrEnum):
    """Network identifiers in scope for Phase 3 BESS placement."""

    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


@dataclass(frozen=True)
class BranchRecord:
    """A single branch from the cleaned .m file, used for utilization scoring.

    Branch flow_mw may be from a solved power flow snapshot or from a DC OPF
    result. If no solved flow is available, flow_mw is set to 0.0 and the
    utilization score defaults to a neutral value.
    """

    branch_idx: int  # 1-based index in the MATPOWER branch table
    from_bus: int
    to_bus: int
    rate_a_mw: float  # long-term thermal rating (MVA, treated as MW for DC)
    flow_mw: float  # absolute branch flow from snapshot or OPF (MW)


@dataclass(frozen=True)
class BusCandidate:
    """Intermediate record for a bus under consideration for BESS placement.

    Carries the raw data needed to compute the composite placement score.
    """

    bus: int  # bus number from the cleaned .m file
    pd_mw: float  # base-case real power demand (MW)
    area: int  # electrical area from MATPOWER bus data (column 7)
    max_branch_utilization: float  # max(flow_mw / rate_a_mw) among connected branches
    connected_branch_count: int  # number of branches incident on this bus


@dataclass(frozen=True)
class ScoredBus:
    """A candidate bus with its computed composite placement score.

    score = normalized_pd * (1 / max_branch_utilization), where:
    - normalized_pd = bus pd_mw / max(all bus pd_mw)
    - max_branch_utilization is clamped to [0.01, 1.0] to avoid division by zero
      and to cap the inverse at 100

    Higher score means the bus is a better BESS candidate (high load,
    low congestion on connected branches).
    """

    bus: int
    pd_mw: float
    area: int
    max_branch_utilization: float
    normalized_pd: float
    inverse_utilization: float
    score: float


@dataclass(frozen=True)
class BessUnit:
    """Parameter record for a single BESS unit in SMALL or MEDIUM networks.

    Field names match the output CSV column names exactly.
    """

    unit_id: str  # unique identifier, e.g. "BESS_SMALL_001"
    bus: int  # bus number in the network
    power_mw: float  # charge and discharge power rating (symmetric)
    energy_mwh: float  # usable energy capacity (power_mw * duration_hr)
    duration_hr: float  # energy_mwh / power_mw, always 4.0
    charge_eff: float  # one-way charging efficiency [0, 1]
    discharge_eff: float  # one-way discharging efficiency [0, 1]
    roundtrip_eff: float  # charge_eff * discharge_eff [0, 1]
    min_soc_pct: float  # minimum SoC as percentage of energy_mwh [0, 100]
    max_soc_pct: float  # maximum SoC as percentage of energy_mwh [0, 100]
    initial_soc_pct: float  # initial SoC as percentage of energy_mwh [0, 100]
    ramp_rate_mw_per_min: float  # maximum ramp rate for charge/discharge
    cyclic_soc: bool  # if True, SoC at hour 24 must equal SoC at hour 1


@dataclass(frozen=True)
class BessFleetConfig:
    """Configuration parameters controlling BESS fleet sizing and placement.

    All sizing parameters have defaults matching the phase plan specification.
    """

    min_units: int  # minimum BESS units to place (3 for SMALL, 5 for MEDIUM)
    max_units: int  # maximum BESS units to place (5 for SMALL, 8 for MEDIUM)
    fleet_fraction_min: float = 0.03  # min aggregate power as fraction of peak load
    fleet_fraction_max: float = 0.05  # max aggregate power as fraction of peak load
    fleet_fraction_target: float = 0.04  # target aggregate power fraction
    min_distinct_sizes: int = 2  # minimum number of distinct power ratings
    duration_hr: float = 4.0  # energy duration for all units (hours)
    utilization_clamp_min: float = 0.01  # lower clamp for branch utilization
    utilization_clamp_max: float = 1.0  # upper clamp for branch utilization
    min_pd_mw: float = 10.0  # minimum bus Pd to be considered a candidate


@dataclass(frozen=True)
class StorageRefParams:
    """Intensive parameters read from the Phase 3 D1 storage reference table.

    These are copied unchanged to every BESS unit regardless of power rating.
    Extensive parameters (power, energy, ramp) are scaled per-unit.
    """

    charge_eff: float  # one-way charging efficiency [0, 1]
    discharge_eff: float  # one-way discharging efficiency [0, 1]
    roundtrip_eff: float  # charge_eff * discharge_eff [0, 1]
    min_soc_pct: float  # minimum SoC as percentage [0, 100]
    max_soc_pct: float  # maximum SoC as percentage [0, 100]
    initial_soc_pct: float  # initial SoC as percentage [0, 100]
    cyclic_soc: bool  # cyclic SoC boundary condition
    template_power_mw: float  # template unit power (for ramp scaling)
    template_ramp_rate_mw_per_min: float  # template ramp rate


@dataclass(frozen=True)
class PlacementRationaleEntry:
    """One row of the placement rationale log, documenting why a bus was
    selected or rejected.
    """

    bus: int
    pd_mw: float
    area: int
    max_branch_utilization: float
    normalized_pd: float
    inverse_utilization: float
    score: float
    rank: int  # 1-based rank by score descending
    selected: bool  # True if this bus was chosen for BESS placement
    rejection_reason: str  # empty if selected


@dataclass(frozen=True)
class BessPlacementResult:
    """Complete result of BESS placement and sizing for a single network."""

    network_id: BessNetworkId
    bess_units_csv: str  # relative path to output bess_units.csv
    bess_units: list[BessUnit]  # in-memory BESS definitions
    rationale: list[PlacementRationaleEntry]  # full candidate ranking log
    total_power_mw: float  # sum of power_mw across fleet
    system_peak_mw: float  # sum of all bus Pd from cleaned .m file
    fleet_fraction: float  # total_power_mw / system_peak_mw
    distinct_sizes: int  # number of unique power_mw values in fleet


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NETWORK_M_FILES: dict[BessNetworkId, str] = {
    BessNetworkId.SMALL: "case_ACTIVSg2000.m",
    BessNetworkId.MEDIUM: "case_ACTIVSg10k.m",
}

SMALL_BESS_CONFIG: BessFleetConfig = BessFleetConfig(min_units=3, max_units=5)
"""Default BESS fleet configuration for the SMALL (ACTIVSg2000) network."""

MEDIUM_BESS_CONFIG: BessFleetConfig = BessFleetConfig(min_units=5, max_units=8)
"""Default BESS fleet configuration for the MEDIUM (ACTIVSg10k) network."""

BESS_CONFIG_MAP: dict[BessNetworkId, BessFleetConfig] = {
    BessNetworkId.SMALL: SMALL_BESS_CONFIG,
    BessNetworkId.MEDIUM: MEDIUM_BESS_CONFIG,
}

BESS_ID_PREFIX_MAP: dict[BessNetworkId, str] = {
    BessNetworkId.SMALL: "BESS_SMALL",
    BessNetworkId.MEDIUM: "BESS_MEDIUM",
}

# BESS output CSV column order
BESS_CSV_COLUMNS: list[str] = [
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
]

RATIONALE_CSV_COLUMNS: list[str] = [
    "rank",
    "bus",
    "pd_mw",
    "area",
    "max_branch_utilization",
    "normalized_pd",
    "inverse_utilization",
    "score",
    "selected",
    "rejection_reason",
]


# ---------------------------------------------------------------------------
# MATPOWER .m file parsing helpers
# ---------------------------------------------------------------------------

_MATRIX_BLOCK_RE_TEMPLATE = r"mpc\.{field}\s*=\s*\[([^\]]*)\]"


def _extract_matrix_block(text: str, field_name: str) -> str:
    """Extract the content between [ ] for mpc.<field_name>."""
    pattern = re.compile(
        _MATRIX_BLOCK_RE_TEMPLATE.format(field=re.escape(field_name)),
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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _parse_bus_area_pd(m_file_path: Path) -> list[tuple[int, float, int]]:
    """Parse bus number, Pd, and area from a MATPOWER .m file.

    Returns a list of (bus_id, pd_mw, area) tuples for every bus.
    MATPOWER bus columns: bus_i(0), type(1), Pd(2), Qd(3), Gs(4), Bs(5), area(6).
    """
    text = m_file_path.read_text()
    block = _extract_matrix_block(text, "bus")
    rows = _parse_numeric_rows(block)

    result: list[tuple[int, float, int]] = []
    for row in rows:
        if len(row) < 7:
            msg = f"Bus row has {len(row)} columns, expected at least 7"
            raise ValueError(msg)
        bus_id = int(row[0])
        pd_mw = row[2]
        area = int(row[6])
        result.append((bus_id, pd_mw, area))
    return result


def _parse_branches(m_file_path: Path) -> list[tuple[int, int, float]]:
    """Parse branch from_bus, to_bus, and rate_a from a MATPOWER .m file.

    MATPOWER branch columns: fbus(0), tbus(1), r(2), x(3), b(4), rateA(5).
    Returns list of (from_bus, to_bus, rate_a_mw).
    """
    text = m_file_path.read_text()
    block = _extract_matrix_block(text, "branch")
    rows = _parse_numeric_rows(block)

    result: list[tuple[int, int, float]] = []
    for row in rows:
        if len(row) < 6:
            msg = f"Branch row has {len(row)} columns, expected at least 6"
            raise ValueError(msg)
        from_bus = int(row[0])
        to_bus = int(row[1])
        rate_a = row[5]
        result.append((from_bus, to_bus, rate_a))
    return result


def load_branch_data(
    network_dir: Path,
    network_id: BessNetworkId,
) -> list[BranchRecord]:
    """Load branch data from the cleaned .m file for utilization scoring.

    If DC OPF branch loading results exist at
    data/timeseries/<network>/flowgate_calibration/branch_loading_peak.csv,
    those are loaded for more accurate peak-load utilization data. Otherwise,
    flow_mw defaults to 0.0.

    Args:
        network_dir: Path to the directory containing the cleaned .m file.
        network_id: Network identifier for locating the .m and OPF files.

    Returns:
        List of BranchRecord entries for all branches in the network.

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
    """
    m_file = network_dir / NETWORK_M_FILES[network_id]
    if not m_file.exists():
        msg = f"Cleaned .m file not found: {m_file}"
        raise FileNotFoundError(msg)

    raw_branches = _parse_branches(m_file)

    # Try to load DC OPF peak branch loading results
    opf_csv = network_dir / "flowgate_calibration" / "branch_loading_peak.csv"
    opf_flows: dict[int, float] = {}
    if opf_csv.exists():
        text = opf_csv.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            idx = int(row["branch_idx"])
            flow = abs(float(row["flow_mw"]))
            opf_flows[idx] = flow

    records: list[BranchRecord] = []
    for i, (from_bus, to_bus, rate_a) in enumerate(raw_branches):
        branch_idx = i + 1  # 1-based
        flow = opf_flows.get(branch_idx, 0.0)
        records.append(
            BranchRecord(
                branch_idx=branch_idx,
                from_bus=from_bus,
                to_bus=to_bus,
                rate_a_mw=rate_a,
                flow_mw=flow,
            )
        )
    return records


def load_bus_data(
    network_dir: Path,
    network_id: BessNetworkId,
    config: BessFleetConfig | None = None,
) -> list[BusCandidate]:
    """Load bus-level Pd, area, and branch connectivity from the cleaned .m file.

    Only buses with Pd >= config.min_pd_mw are returned as candidates.

    Args:
        network_dir: Path to the directory containing the cleaned .m file.
        network_id: Network identifier used to locate the correct .m file.
        config: Fleet configuration (for min_pd_mw threshold).

    Returns:
        List of BusCandidate records for buses meeting the minimum Pd threshold.

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
    """
    if config is None:
        config = BESS_CONFIG_MAP[network_id]

    m_file = network_dir / NETWORK_M_FILES[network_id]
    if not m_file.exists():
        msg = f"Cleaned .m file not found: {m_file}"
        raise FileNotFoundError(msg)

    bus_data = _parse_bus_area_pd(m_file)
    branches = load_branch_data(network_dir, network_id)

    # Compute per-bus max branch utilization
    bus_max_util: dict[int, float] = {}
    bus_branch_count: dict[int, int] = {}

    for br in branches:
        rate_a = br.rate_a_mw if br.rate_a_mw > 0 else 9999.0
        util = br.flow_mw / rate_a if rate_a > 0 else 0.0

        for bus in (br.from_bus, br.to_bus):
            bus_max_util[bus] = max(bus_max_util.get(bus, 0.0), util)
            bus_branch_count[bus] = bus_branch_count.get(bus, 0) + 1

    candidates: list[BusCandidate] = []
    for bus_id, pd_mw, area in bus_data:
        if pd_mw < config.min_pd_mw:
            continue
        candidates.append(
            BusCandidate(
                bus=bus_id,
                pd_mw=pd_mw,
                area=area,
                max_branch_utilization=bus_max_util.get(bus_id, 0.0),
                connected_branch_count=bus_branch_count.get(bus_id, 0),
            )
        )
    return candidates


def load_storage_reference(
    reference_path: Path,
) -> StorageRefParams:
    """Load intensive BESS parameters from the Phase 3 D1 reference table.

    Reads data/reference/rts_gmlc_storage_params.csv and extracts the
    intensive parameters and the template's extensive parameters.

    Efficiency values in the reference CSV are stored as fractions [0, 1].
    SoC values in the reference CSV are fractions [0, 1] and are converted
    to percentages [0, 100] for the _pct output fields.

    Args:
        reference_path: Path to the rts_gmlc_storage_params.csv file.

    Returns:
        A StorageRefParams with all intensive parameters and template values.

    Raises:
        FileNotFoundError: If the reference CSV does not exist.
        ValueError: If the CSV does not contain exactly one storage row,
            or if required columns are missing.
    """
    if not reference_path.exists():
        msg = f"Storage reference CSV not found: {reference_path}"
        raise FileNotFoundError(msg)

    text = reference_path.read_text(encoding="utf-8")

    # Filter out comment lines (starting with #)
    non_comment_lines = [line for line in text.splitlines() if not line.startswith("#")]
    filtered_text = "\n".join(non_comment_lines)

    reader = csv.DictReader(io.StringIO(filtered_text))
    rows = list(reader)

    if len(rows) == 0:
        msg = "Storage reference CSV contains no data rows"
        raise ValueError(msg)
    if len(rows) > 1:
        msg = f"Storage reference CSV contains {len(rows)} rows, expected exactly 1"
        raise ValueError(msg)

    row = rows[0]

    charge_eff = float(row["charge_efficiency"])
    discharge_eff = float(row["discharge_efficiency"])
    roundtrip_eff = float(row["roundtrip_efficiency"])

    # SoC values in D1 are fractions [0, 1]; convert to percentages [0, 100]
    min_soc_pct = float(row["min_soc"]) * 100.0
    max_soc_pct = float(row["max_soc"]) * 100.0
    initial_soc_pct = float(row["init_soc"]) * 100.0

    cyclic_soc_str = row["cyclic_soc"].strip().lower()
    cyclic_soc = cyclic_soc_str == "true"

    return StorageRefParams(
        charge_eff=charge_eff,
        discharge_eff=discharge_eff,
        roundtrip_eff=roundtrip_eff,
        min_soc_pct=min_soc_pct,
        max_soc_pct=max_soc_pct,
        initial_soc_pct=initial_soc_pct,
        cyclic_soc=cyclic_soc,
        template_power_mw=float(row["power_mw"]),
        template_ramp_rate_mw_per_min=float(row["ramp_rate_mw_per_min"]),
    )


# ---------------------------------------------------------------------------
# Scoring and selection
# ---------------------------------------------------------------------------


def score_candidates(
    candidates: list[BusCandidate],
) -> list[ScoredBus]:
    """Compute the composite placement score for each candidate bus.

    For each candidate:
    1. normalized_pd = candidate.pd_mw / max_pd across all candidates.
    2. clamped_utilization = clamp(candidate.max_branch_utilization, 0.01, 1.0).
    3. inverse_utilization = 1.0 / clamped_utilization.
    4. score = normalized_pd * inverse_utilization.

    Args:
        candidates: Bus candidates with Pd and branch utilization data.

    Returns:
        List of ScoredBus records, sorted by score descending. Ties are
        broken by bus number ascending for deterministic ordering.
    """
    if not candidates:
        return []

    max_pd = max(c.pd_mw for c in candidates)
    if max_pd <= 0:
        max_pd = 1.0  # Avoid division by zero

    scored: list[ScoredBus] = []
    for c in candidates:
        if c.pd_mw <= 0:
            normalized_pd = 0.0
            inverse_util = 0.0
            score = 0.0
        else:
            normalized_pd = c.pd_mw / max_pd
            clamped = max(0.01, min(1.0, c.max_branch_utilization))
            inverse_util = 1.0 / clamped
            score = normalized_pd * inverse_util

        scored.append(
            ScoredBus(
                bus=c.bus,
                pd_mw=c.pd_mw,
                area=c.area,
                max_branch_utilization=c.max_branch_utilization,
                normalized_pd=normalized_pd,
                inverse_utilization=inverse_util,
                score=score,
            )
        )

    # Sort by score descending, then bus number ascending for tiebreaking
    scored.sort(key=lambda s: (-s.score, s.bus))
    return scored


def select_bess_buses(
    scored: list[ScoredBus],
    config: BessFleetConfig,
) -> list[ScoredBus]:
    """Select the top-ranked buses for BESS placement.

    Takes the top config.max_units buses from the scored list. If the
    scored list has fewer than config.min_units entries, raises ValueError.

    Args:
        scored: Scored candidates sorted by score descending.
        config: Fleet configuration with unit count limits.

    Returns:
        List of selected ScoredBus records, in score order.

    Raises:
        ValueError: If fewer than config.min_units candidates are available.
    """
    if len(scored) < config.min_units:
        msg = f"Only {len(scored)} candidate buses available, but {config.min_units} are required"
        raise ValueError(msg)

    return scored[: config.max_units]


# ---------------------------------------------------------------------------
# Fleet sizing
# ---------------------------------------------------------------------------


def compute_unit_ratings(
    selected_buses: list[ScoredBus],
    system_peak_mw: float,
    config: BessFleetConfig,
    rng: np.random.Generator,
) -> list[float]:
    """Compute individual unit power ratings for the BESS fleet.

    Algorithm:
    1. Compute target_fleet_mw = config.fleet_fraction_target * system_peak_mw.
    2. Divide target_fleet_mw across units proportional to each bus's Pd.
    3. Perturb to ensure at least config.min_distinct_sizes unique ratings.
    4. Clamp total fleet capacity to valid range and round to 1 decimal.

    Args:
        selected_buses: Buses selected for BESS placement, in score order.
        system_peak_mw: Total system peak load (sum of all bus Pd).
        config: Fleet configuration with sizing parameters.
        rng: Seeded numpy random generator for deterministic sizing.

    Returns:
        List of power ratings in MW, one per selected bus.

    Raises:
        ValueError: If selected_buses is empty or system_peak_mw <= 0.
    """
    if not selected_buses:
        msg = "selected_buses must not be empty"
        raise ValueError(msg)
    if system_peak_mw <= 0:
        msg = f"system_peak_mw must be positive, got {system_peak_mw}"
        raise ValueError(msg)

    n = len(selected_buses)
    target_fleet_mw = config.fleet_fraction_target * system_peak_mw

    # Proportional split by Pd
    pd_values = np.array([b.pd_mw for b in selected_buses])
    pd_sum = pd_values.sum()
    if pd_sum <= 0:
        # Equal split if all Pd are zero
        weights = np.ones(n) / n
    else:
        weights = pd_values / pd_sum

    ratings = weights * target_fleet_mw

    # Round to 1 decimal place
    ratings = np.round(ratings, 1)

    # Ensure at least min_distinct_sizes unique values
    unique_count = len(set(ratings.tolist()))
    if unique_count < config.min_distinct_sizes and n >= config.min_distinct_sizes:
        # Perturb the largest and smallest to create diversity
        sorted_indices = np.argsort(ratings)
        # Increase the largest by ~10%
        largest_idx = sorted_indices[-1]
        ratings[largest_idx] = round(ratings[largest_idx] * 1.10, 1)
        # Decrease the smallest by ~10%
        smallest_idx = sorted_indices[0]
        ratings[smallest_idx] = round(ratings[smallest_idx] * 0.90, 1)

    # Ensure all ratings are positive
    ratings = np.maximum(ratings, 0.1)

    # Clamp total fleet capacity to valid range
    total = float(ratings.sum())
    fleet_min = config.fleet_fraction_min * system_peak_mw
    fleet_max = config.fleet_fraction_max * system_peak_mw

    if total < fleet_min:
        scale = fleet_min / total
        ratings = np.round(ratings * scale, 1)
    elif total > fleet_max:
        scale = fleet_max / total
        ratings = np.round(ratings * scale, 1)

    return [float(r) for r in ratings]


def build_bess_units(
    selected_buses: list[ScoredBus],
    power_ratings: list[float],
    ref_params: StorageRefParams,
    config: BessFleetConfig,
    network_id: BessNetworkId,
) -> list[BessUnit]:
    """Construct BessUnit records from selected buses and computed ratings.

    Args:
        selected_buses: Buses selected for BESS placement, in score order.
        power_ratings: Power ratings in MW from compute_unit_ratings.
        ref_params: Intensive parameters from the D1 reference table.
        config: Fleet configuration (for duration_hr).
        network_id: Network identifier for unit ID prefix.

    Returns:
        List of BessUnit records, ordered by unit_id.

    Raises:
        ValueError: If len(selected_buses) != len(power_ratings).
    """
    if len(selected_buses) != len(power_ratings):
        msg = (
            f"selected_buses ({len(selected_buses)}) and "
            f"power_ratings ({len(power_ratings)}) must have same length"
        )
        raise ValueError(msg)

    prefix = BESS_ID_PREFIX_MAP[network_id]
    units: list[BessUnit] = []

    for i, (bus, power_mw) in enumerate(zip(selected_buses, power_ratings)):
        unit_id = f"{prefix}_{i + 1:03d}"
        energy_mwh = round(power_mw * config.duration_hr, 1)
        ramp_rate = round(
            ref_params.template_ramp_rate_mw_per_min * (power_mw / ref_params.template_power_mw),
            2,
        )

        units.append(
            BessUnit(
                unit_id=unit_id,
                bus=bus.bus,
                power_mw=power_mw,
                energy_mwh=energy_mwh,
                duration_hr=config.duration_hr,
                charge_eff=ref_params.charge_eff,
                discharge_eff=ref_params.discharge_eff,
                roundtrip_eff=ref_params.roundtrip_eff,
                min_soc_pct=ref_params.min_soc_pct,
                max_soc_pct=ref_params.max_soc_pct,
                initial_soc_pct=ref_params.initial_soc_pct,
                ramp_rate_mw_per_min=ramp_rate,
                cyclic_soc=ref_params.cyclic_soc,
            )
        )

    return units


# ---------------------------------------------------------------------------
# Rationale log
# ---------------------------------------------------------------------------


def build_rationale_log(
    scored: list[ScoredBus],
    selected_buses: set[int],
    config: BessFleetConfig,
) -> list[PlacementRationaleEntry]:
    """Build the placement rationale log for all candidate buses.

    Args:
        scored: All scored candidates, sorted by score descending.
        selected_buses: Set of bus numbers that were selected.
        config: Fleet configuration for documenting thresholds.

    Returns:
        List of PlacementRationaleEntry records, one per scored bus,
        in rank order (rank 1 = highest score).
    """
    entries: list[PlacementRationaleEntry] = []
    for rank, s in enumerate(scored, start=1):
        is_selected = s.bus in selected_buses
        if is_selected:
            reason = ""
        elif rank > config.max_units:
            reason = "rank exceeded max_units"
        else:
            reason = "not selected"

        entries.append(
            PlacementRationaleEntry(
                bus=s.bus,
                pd_mw=s.pd_mw,
                area=s.area,
                max_branch_utilization=s.max_branch_utilization,
                normalized_pd=s.normalized_pd,
                inverse_utilization=s.inverse_utilization,
                score=s.score,
                rank=rank,
                selected=is_selected,
                rejection_reason=reason,
            )
        )
    return entries


def write_rationale_log(
    rationale: list[PlacementRationaleEntry],
    dest_path: Path,
) -> None:
    """Write the placement rationale log to CSV.

    Args:
        rationale: Rationale entries from build_rationale_log.
        dest_path: File path to write the CSV.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=RATIONALE_CSV_COLUMNS)
    writer.writeheader()

    for entry in rationale:
        writer.writerow(
            {
                "rank": entry.rank,
                "bus": entry.bus,
                "pd_mw": f"{entry.pd_mw:.1f}",
                "area": entry.area,
                "max_branch_utilization": f"{entry.max_branch_utilization:.4f}",
                "normalized_pd": f"{entry.normalized_pd:.4f}",
                "inverse_utilization": f"{entry.inverse_utilization:.4f}",
                "score": f"{entry.score:.4f}",
                "selected": str(entry.selected).lower(),
                "rejection_reason": entry.rejection_reason,
            }
        )

    dest_path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_bess_fleet(
    bess_units: list[BessUnit],
    system_peak_mw: float,
    config: BessFleetConfig,
    ref_params: StorageRefParams,
) -> None:
    """Validate BESS fleet against constraints from the phase plan.

    Args:
        bess_units: BESS unit definitions to validate.
        system_peak_mw: Total system peak load for fleet fraction checks.
        config: Fleet configuration with sizing constraints.
        ref_params: Storage reference parameters for consistency checks.

    Raises:
        ValueError: If any validation check fails.
    """
    n = len(bess_units)

    # 1. Unit count
    if n < config.min_units or n > config.max_units:
        msg = f"Fleet has {n} units, expected [{config.min_units}, {config.max_units}]"
        raise ValueError(msg)

    # 2. Total fleet power fraction
    total_power = sum(u.power_mw for u in bess_units)
    frac = total_power / system_peak_mw if system_peak_mw > 0 else 0.0
    if frac < config.fleet_fraction_min - 1e-6 or frac > config.fleet_fraction_max + 1e-6:
        msg = (
            f"Fleet fraction {frac:.4f} outside "
            f"[{config.fleet_fraction_min}, {config.fleet_fraction_max}]"
        )
        raise ValueError(msg)

    # 3. Distinct sizes
    unique_sizes = len({u.power_mw for u in bess_units})
    if unique_sizes < config.min_distinct_sizes:
        msg = f"Fleet has {unique_sizes} distinct sizes, need at least {config.min_distinct_sizes}"
        raise ValueError(msg)

    for u in bess_units:
        # 4. Energy = power * duration
        expected_energy = round(u.power_mw * config.duration_hr, 1)
        if abs(u.energy_mwh - expected_energy) > 0.15:
            msg = (
                f"{u.unit_id}: energy_mwh={u.energy_mwh} != "
                f"power_mw * duration_hr = {expected_energy}"
            )
            raise ValueError(msg)

        # 5. Duration
        if abs(u.duration_hr - config.duration_hr) > 1e-6:
            msg = f"{u.unit_id}: duration_hr={u.duration_hr} != {config.duration_hr}"
            raise ValueError(msg)

        # 6. Efficiency bounds
        if u.charge_eff <= 0 or u.charge_eff > 1:
            msg = f"{u.unit_id}: charge_eff={u.charge_eff} not in (0, 1]"
            raise ValueError(msg)
        if u.discharge_eff <= 0 or u.discharge_eff > 1:
            msg = f"{u.unit_id}: discharge_eff={u.discharge_eff} not in (0, 1]"
            raise ValueError(msg)

        # 7. Roundtrip efficiency consistency
        expected_rte = u.charge_eff * u.discharge_eff
        if abs(u.roundtrip_eff - expected_rte) > 1e-6:
            msg = (
                f"{u.unit_id}: roundtrip_eff={u.roundtrip_eff} != "
                f"charge_eff * discharge_eff = {expected_rte}"
            )
            raise ValueError(msg)

        # 8. SoC ordering
        if u.min_soc_pct >= u.max_soc_pct:
            msg = f"{u.unit_id}: min_soc_pct={u.min_soc_pct} >= max_soc_pct={u.max_soc_pct}"
            raise ValueError(msg)

        # 9. Initial SoC within bounds
        if u.initial_soc_pct < u.min_soc_pct or u.initial_soc_pct > u.max_soc_pct:
            msg = (
                f"{u.unit_id}: initial_soc_pct={u.initial_soc_pct} "
                f"outside [{u.min_soc_pct}, {u.max_soc_pct}]"
            )
            raise ValueError(msg)

        # 10. Ramp rate positive
        if u.ramp_rate_mw_per_min <= 0:
            msg = f"{u.unit_id}: ramp_rate_mw_per_min={u.ramp_rate_mw_per_min} <= 0"
            raise ValueError(msg)

        # 13. Cyclic SoC
        if not u.cyclic_soc:
            msg = f"{u.unit_id}: cyclic_soc must be True"
            raise ValueError(msg)

        # 14. Power positive
        if u.power_mw <= 0:
            msg = f"{u.unit_id}: power_mw={u.power_mw} <= 0"
            raise ValueError(msg)

    # 11. Unique unit IDs
    unit_ids = [u.unit_id for u in bess_units]
    if len(set(unit_ids)) != len(unit_ids):
        msg = "Duplicate unit_id values found"
        raise ValueError(msg)

    # 12. Unique buses
    bus_ids = [u.bus for u in bess_units]
    if len(set(bus_ids)) != len(bus_ids):
        msg = "Duplicate bus values found — two BESS units at the same bus"
        raise ValueError(msg)


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------


def write_bess_units_csv(
    bess_units: list[BessUnit],
    dest_path: Path,
) -> None:
    """Write BESS unit definitions to CSV.

    Boolean columns are written as "true" / "false" (lowercase).
    Rows are ordered by unit_id.

    Args:
        bess_units: List of BessUnit records to write.
        dest_path: File path to write the CSV output.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by unit_id
    sorted_units = sorted(bess_units, key=lambda u: u.unit_id)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=BESS_CSV_COLUMNS)
    writer.writeheader()

    for u in sorted_units:
        writer.writerow(
            {
                "unit_id": u.unit_id,
                "bus": u.bus,
                "power_mw": f"{u.power_mw:.1f}",
                "energy_mwh": f"{u.energy_mwh:.1f}",
                "duration_hr": f"{u.duration_hr:.1f}",
                "charge_eff": f"{u.charge_eff:.4f}",
                "discharge_eff": f"{u.discharge_eff:.4f}",
                "roundtrip_eff": f"{u.roundtrip_eff:.4f}",
                "min_soc_pct": f"{u.min_soc_pct:.1f}",
                "max_soc_pct": f"{u.max_soc_pct:.1f}",
                "initial_soc_pct": f"{u.initial_soc_pct:.1f}",
                "ramp_rate_mw_per_min": f"{u.ramp_rate_mw_per_min:.2f}",
                "cyclic_soc": str(u.cyclic_soc).lower(),
            }
        )

    dest_path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def place_bess_for_network(
    network_dir: Path,
    output_dir: Path,
    network_id: BessNetworkId,
    reference_path: Path,
    config: BessFleetConfig | None = None,
    seed: int = 20240302,
) -> BessPlacementResult:
    """Place BESS units for a single network and write output files.

    Args:
        network_dir: Path to the directory containing the cleaned .m file.
        output_dir: Directory to write the output bess_units.csv and
            placement_rationale.csv.
        network_id: Network identifier (SMALL or MEDIUM).
        reference_path: Path to the D1 rts_gmlc_storage_params.csv file.
        config: Fleet configuration. If None, uses the default.
        seed: Random seed for numpy generator.

    Returns:
        A BessPlacementResult with paths, BESS definitions, rationale,
        and fleet summary statistics.

    Raises:
        FileNotFoundError: If the cleaned .m file or reference CSV is not found.
        ValueError: If fleet validation fails.
    """
    if config is None:
        config = BESS_CONFIG_MAP[network_id]

    rng = np.random.default_rng(seed)

    # 1-2. Load bus and branch data
    candidates = load_bus_data(network_dir, network_id, config)

    # Compute system peak from ALL buses (not just candidates)
    m_file = network_dir / NETWORK_M_FILES[network_id]
    all_bus_data = _parse_bus_area_pd(m_file)
    system_peak_mw = sum(pd for _, pd, _ in all_bus_data if pd > 0)

    # 3. Load storage reference
    ref_params = load_storage_reference(reference_path)

    # 4. Score candidates
    scored = score_candidates(candidates)

    # 5. Select top buses
    selected = select_bess_buses(scored, config)

    # 6. Compute unit ratings
    power_ratings = compute_unit_ratings(selected, system_peak_mw, config, rng)

    # 7. Build BESS units
    bess_units = build_bess_units(selected, power_ratings, ref_params, config, network_id)

    # 8. Validate
    validate_bess_fleet(bess_units, system_peak_mw, config, ref_params)

    # 9. Write output files
    bess_csv_path = output_dir / "bess_units.csv"
    write_bess_units_csv(bess_units, bess_csv_path)

    # 10. Build and write rationale
    selected_bus_set = {s.bus for s in selected}
    rationale = build_rationale_log(scored, selected_bus_set, config)
    rationale_path = output_dir / "bess_placement_rationale.csv"
    write_rationale_log(rationale, rationale_path)

    total_power = sum(u.power_mw for u in bess_units)

    return BessPlacementResult(
        network_id=network_id,
        bess_units_csv=str(bess_csv_path),
        bess_units=bess_units,
        rationale=rationale,
        total_power_mw=total_power,
        system_peak_mw=system_peak_mw,
        fleet_fraction=total_power / system_peak_mw if system_peak_mw > 0 else 0.0,
        distinct_sizes=len({u.power_mw for u in bess_units}),
    )


def main(
    data_root: Path | None = None,
    reference_path: Path | None = None,
    seed: int = 20240302,
) -> dict[BessNetworkId, BessPlacementResult]:
    """Entry point: place BESS units for all Phase 3 networks.

    Args:
        data_root: Root directory for data files. Defaults to
            <repo_root>/data/timeseries/.
        reference_path: Path to the D1 storage reference CSV.
        seed: Random seed for reproducible placement across networks.

    Returns:
        Dict mapping network ID to BessPlacementResult.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if data_root is None:
        data_root = repo_root / "timeseries"
    if reference_path is None:
        reference_path = repo_root / "reference" / "rts_gmlc_storage_params.csv"

    results: dict[BessNetworkId, BessPlacementResult] = {}

    for network_id in BessNetworkId:
        network_dir = data_root / network_id.value
        output_dir = data_root / network_id.value

        # Each network gets its own rng offset
        network_seed = seed + hash(network_id.value) % 1000

        print(f"Placing BESS for {network_id.value}...")
        result = place_bess_for_network(
            network_dir=network_dir,
            output_dir=output_dir,
            network_id=network_id,
            reference_path=reference_path,
            seed=network_seed,
        )
        results[network_id] = result

        print(
            f"  Fleet: {result.total_power_mw:.1f} MW "
            f"({result.fleet_fraction:.1%} of {result.system_peak_mw:.1f} MW peak)"
        )
        print(f"  Units: {len(result.bess_units)}, distinct sizes: {result.distinct_sizes}")
        print(f"  Output: {result.bess_units_csv}")
        print()

    return results


if __name__ == "__main__":
    main()
