"""DR Resource Placement & Parameter Definition for Phase 3 networks.

Selects demand-response-eligible buses for the SMALL (ACTIVSg2000) and MEDIUM
(ACTIVSg10k) networks from the highest-load buses in each network's cleaned .m
file. For each selected bus, assigns curtailment/recovery power limits, ramp
rates, participation windows, and the daily energy neutrality flag. Produces
dr_buses.csv files following the Phase 2b PRD-06 schema.

DR models load-shifting flexibility at large industrial and commercial buses.
Curtailed load must be recovered within the same 24-hour horizon so that net
energy withdrawal over 24 hours equals zero.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np

from scripts.reconcile_bus_gen import parse_matpower_case

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class DrNetworkId(StrEnum):
    """Network identifiers in scope for Phase 3 DR placement."""

    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


@dataclass(frozen=True)
class DrBus:
    """Parameter record for a single demand-response-eligible bus.

    DR is modeled as load curtailment (reduction) with mandatory recovery
    (payback) to enforce daily energy neutrality. Recovery power is
    asymmetric with curtailment (typically 75% of the curtailment rate).

    Schema-compatible with Phase 2b PRD-06 DrBus. Field names match the
    output CSV column names exactly.
    """

    dr_id: str  # unique identifier, e.g. "DR_SMALL_001"
    bus: int  # bus number in the network
    max_curtail_mw: float  # maximum load reduction (MW)
    max_recover_mw: float  # maximum load increase for payback (MW)
    curtail_ramp_mw_per_hr: float  # ramp limit on curtailment initiation (MW/hr)
    recover_ramp_mw_per_hr: float  # ramp limit on recovery (MW/hr)
    max_curtail_hours: int  # maximum consecutive hours of curtailment
    min_recovery_gap_hr: float  # minimum hours between curtailment events
    daily_energy_neutral: bool  # if True, curtailed MWh = recovered MWh over 24h
    notification_lead_hr: float  # advance notice required (hours)


@dataclass(frozen=True)
class BusCandidate:
    """Intermediate record for a bus under consideration for DR placement.

    Used during the selection phase to rank buses by load and enforce
    area diversity constraints before committing to final DR parameters.
    """

    bus: int  # bus number
    pd_mw: float  # base-case real power demand (MW) from cleaned .m file
    area: int  # electrical area from MATPOWER bus data (column 7)


@dataclass(frozen=True)
class DrPlacementConfig:
    """Configuration parameters controlling DR placement and sizing.

    All sizing ratios and counts have defaults matching the phase plan
    specification. Override via constructor arguments for sensitivity
    analysis or testing.
    """

    min_buses: int  # minimum DR buses to select (5 for SMALL, 8 for MEDIUM)
    max_buses: int  # maximum DR buses to select (8 for SMALL, 12 for MEDIUM)
    max_buses_per_area: int = 3  # geographic diversity cap
    curtail_fraction_min: float = 0.10  # minimum curtailment as fraction of bus Pd
    curtail_fraction_max: float = 0.15  # maximum curtailment as fraction of bus Pd
    recovery_ratio: float = 0.75  # max_recover_mw / max_curtail_mw
    curtail_ramp_fraction: float = 0.50  # ramp limit as fraction of max_curtail_mw per hour
    recover_ramp_fraction: float = 0.50  # ramp limit as fraction of max_recover_mw per hour
    max_curtail_hours: int = 4  # maximum consecutive curtailment hours
    min_recovery_gap_hr: float = 2.0  # minimum hours between curtailment events
    daily_energy_neutral: bool = True  # enforce daily energy neutrality
    notification_lead_hr: float = 1.0  # advance notice required (hours)
    curtail_target_fraction: float = 0.12  # default curtailment fraction within [min, max]


@dataclass(frozen=True)
class DrPlacementResult:
    """Complete result of DR placement for a single network.

    Bundles the output file path, in-memory DR definitions, and
    summary statistics for downstream validation.
    """

    network_id: DrNetworkId
    dr_buses_csv: str  # relative path to output dr_buses.csv
    dr_buses: list[DrBus]  # in-memory DR definitions
    total_curtail_mw: float  # sum of max_curtail_mw across all DR buses
    system_peak_mw: float  # sum of all bus Pd from cleaned .m file
    dr_fraction_of_peak: float  # total_curtail_mw / system_peak_mw


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SMALL_DR_CONFIG: DrPlacementConfig = DrPlacementConfig(min_buses=5, max_buses=8)
"""Default DR placement configuration for the SMALL (ACTIVSg2000) network.

5-8 buses selected from the highest-load buses, with geographic diversity
enforced at no more than 3 DR buses per electrical area.
"""

MEDIUM_DR_CONFIG: DrPlacementConfig = DrPlacementConfig(min_buses=8, max_buses=12)
"""Default DR placement configuration for the MEDIUM (ACTIVSg10k) network.

8-12 buses selected from the highest-load buses, with geographic diversity
enforced at no more than 3 DR buses per electrical area.
"""

DR_CONFIG_MAP: dict[DrNetworkId, DrPlacementConfig] = {
    DrNetworkId.SMALL: SMALL_DR_CONFIG,
    DrNetworkId.MEDIUM: MEDIUM_DR_CONFIG,
}
"""Mapping from network ID to the corresponding DR placement configuration."""

DR_ID_PREFIX_MAP: dict[DrNetworkId, str] = {
    DrNetworkId.SMALL: "DR_SMALL",
    DrNetworkId.MEDIUM: "DR_MEDIUM",
}
"""Prefix for DR resource IDs, ensuring unique IDs across networks."""

NETWORK_M_FILE_NAMES: dict[DrNetworkId, str] = {
    DrNetworkId.SMALL: "case_ACTIVSg2000.m",
    DrNetworkId.MEDIUM: "case_ACTIVSg10k.m",
}
"""Mapping from network ID to the cleaned .m file name."""

_DR_CSV_COLUMNS: list[str] = [
    "dr_id",
    "bus",
    "max_curtail_mw",
    "max_recover_mw",
    "curtail_ramp_mw_per_hr",
    "recover_ramp_mw_per_hr",
    "max_curtail_hours",
    "min_recovery_gap_hr",
    "daily_energy_neutral",
    "notification_lead_hr",
]
"""Column order for the dr_buses.csv output file."""


# ---------------------------------------------------------------------------
# Bus data loading
# ---------------------------------------------------------------------------


def load_bus_data(
    network_dir: Path,
    network_id: DrNetworkId,
) -> list[BusCandidate]:
    """Load bus-level Pd and area values from the cleaned .m file.

    Parses the bus data section of the cleaned MATPOWER .m file to extract
    bus number (column 1), real power demand Pd (column 3), and area
    (column 7) for all buses. Only buses with Pd > 0 are returned as
    candidates (zero-load buses are not eligible for DR).

    Uses the Phase 1 D2 MATPOWER parser (parse_matpower_case).

    Args:
        network_dir: Path to the directory containing the cleaned .m file
            (e.g., data/timeseries/ACTIVSg2000/).
        network_id: Network identifier used to locate the correct .m file.

    Returns:
        List of BusCandidate records for all buses with nonzero Pd,
        sorted by Pd descending (highest load first).

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
    """
    m_file_name = NETWORK_M_FILE_NAMES[network_id]
    m_file_path = network_dir / m_file_name

    if not m_file_path.exists():
        msg = f"Cleaned .m file not found: {m_file_path}"
        raise FileNotFoundError(msg)

    case_data = parse_matpower_case(m_file_path)

    # Parse the raw .m file text to extract area (column 6, 0-indexed)
    # since MatpowerBusRecord does not store area.
    m_text = m_file_path.read_text()
    area_map = _extract_bus_areas(m_text)

    candidates: list[BusCandidate] = []
    for bus in case_data.buses:
        if bus.pd > 0:
            area = area_map.get(bus.bus_id, 1)
            candidates.append(
                BusCandidate(
                    bus=bus.bus_id,
                    pd_mw=bus.pd,
                    area=area,
                )
            )

    # Sort by Pd descending (highest load first)
    candidates.sort(key=lambda c: -c.pd_mw)
    return candidates


def _extract_bus_areas(m_text: str) -> dict[int, int]:
    """Extract bus ID to area mapping from raw .m file text.

    Parses the mpc.bus block and reads column 6 (0-indexed) as the
    electrical area for each bus.

    Args:
        m_text: Raw .m file text content.

    Returns:
        Dict mapping bus_id (int) to area (int).
    """
    import re

    pattern = re.compile(
        r"mpc\.bus\s*=\s*\[([^\]]*)\]",
        re.DOTALL,
    )
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


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def select_dr_buses(
    candidates: list[BusCandidate],
    config: DrPlacementConfig,
    rng: np.random.Generator,
) -> list[BusCandidate]:
    """Select DR-eligible buses from ranked candidates with area diversity.

    Algorithm:
    1. Candidates arrive sorted by Pd descending (highest load first).
    2. Iterate through candidates in load order. Accept a candidate if
       the number of already-selected buses in that candidate's area
       is below config.max_buses_per_area.
    3. Stop when config.max_buses candidates have been selected or all
       candidates have been considered.
    4. If fewer than config.min_buses are selected after exhausting the
       candidate list, raise ValueError (insufficient eligible buses).

    The rng parameter is accepted for API consistency with other placement
    functions but is not used in the deterministic load-ranked selection.

    Args:
        candidates: Bus candidates sorted by Pd descending. Must contain
            only buses with Pd > 0.
        config: DR placement configuration with bus count limits and
            area diversity cap.
        rng: Seeded numpy random generator (reserved for tie-breaking).

    Returns:
        List of selected BusCandidate records, in selection order
        (highest load first, subject to area cap).

    Raises:
        ValueError: If fewer than config.min_buses can be selected
            given the area diversity constraint.
    """
    selected: list[BusCandidate] = []
    area_counts: dict[int, int] = {}

    for candidate in candidates:
        if len(selected) >= config.max_buses:
            break

        current_area_count = area_counts.get(candidate.area, 0)
        if current_area_count < config.max_buses_per_area:
            selected.append(candidate)
            area_counts[candidate.area] = current_area_count + 1

    if len(selected) < config.min_buses:
        msg = (
            f"Could not select {config.min_buses} DR buses: only {len(selected)} "
            f"eligible buses found given the area diversity constraint "
            f"(max {config.max_buses_per_area} per area)"
        )
        raise ValueError(msg)

    return selected


# ---------------------------------------------------------------------------
# Parameter assignment
# ---------------------------------------------------------------------------


def assign_dr_parameters(
    selected_buses: list[BusCandidate],
    config: DrPlacementConfig,
    network_id: DrNetworkId,
    rng: np.random.Generator,
) -> list[DrBus]:
    """Assign DR parameters to selected buses.

    For each selected bus:
    1. Compute max_curtail_mw = perturbed_fraction * bus.pd_mw,
       clamped to [config.curtail_fraction_min * pd, config.curtail_fraction_max * pd].
       Rounded to 1 decimal place.
    2. Compute max_recover_mw = config.recovery_ratio * max_curtail_mw.
       Rounded to 1 decimal place.
    3. Compute curtail_ramp_mw_per_hr = config.curtail_ramp_fraction * max_curtail_mw.
       Rounded to 1 decimal place.
    4. Compute recover_ramp_mw_per_hr = config.recover_ramp_fraction * max_recover_mw.
       Rounded to 1 decimal place.
    5. Apply static parameters from config.
    6. Assign dr_id as "{DR_ID_PREFIX_MAP[network_id]}_{NNN}".

    The rng parameter introduces small perturbation (+/- 2% of target
    curtailment fraction) to avoid all DR buses having identical
    curtailment-to-load ratios.

    Args:
        selected_buses: Buses selected by select_dr_buses, in selection order.
        config: DR placement configuration with sizing parameters.
        network_id: Network identifier for DR ID prefix.
        rng: Seeded numpy random generator for curtailment fraction
            perturbation.

    Returns:
        List of DrBus records with fully populated parameters,
        in the same order as selected_buses.
    """
    prefix = DR_ID_PREFIX_MAP[network_id]
    dr_buses: list[DrBus] = []

    for i, bus in enumerate(selected_buses):
        # Perturb curtailment fraction by +/- 2%
        perturbation = rng.uniform(-0.02, 0.02)
        target_fraction = config.curtail_target_fraction + perturbation

        # Clamp to [min, max]
        fraction = max(
            config.curtail_fraction_min,
            min(config.curtail_fraction_max, target_fraction),
        )

        max_curtail_mw = round(fraction * bus.pd_mw, 1)
        max_recover_mw = round(config.recovery_ratio * max_curtail_mw, 1)
        curtail_ramp = round(config.curtail_ramp_fraction * max_curtail_mw, 1)
        recover_ramp = round(config.recover_ramp_fraction * max_recover_mw, 1)

        dr_id = f"{prefix}_{i + 1:03d}"

        dr_buses.append(
            DrBus(
                dr_id=dr_id,
                bus=bus.bus,
                max_curtail_mw=max_curtail_mw,
                max_recover_mw=max_recover_mw,
                curtail_ramp_mw_per_hr=curtail_ramp,
                recover_ramp_mw_per_hr=recover_ramp,
                max_curtail_hours=config.max_curtail_hours,
                min_recovery_gap_hr=config.min_recovery_gap_hr,
                daily_energy_neutral=config.daily_energy_neutral,
                notification_lead_hr=config.notification_lead_hr,
            )
        )

    return dr_buses


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_dr_placement(
    dr_buses: list[DrBus],
    candidates: list[BusCandidate],
    config: DrPlacementConfig,
    network_id: DrNetworkId,
) -> None:
    """Validate DR placement against constraints from the phase plan.

    Checks:
    1. Bus count is within [config.min_buses, config.max_buses].
    2. Every DR bus exists in the candidate list (valid bus with Pd > 0).
    3. No more than config.max_buses_per_area DR buses per electrical area.
    4. max_curtail_mw is within [curtail_fraction_min * pd, curtail_fraction_max * pd]
       for each bus, with 2% tolerance for rng perturbation.
    5. max_recover_mw == config.recovery_ratio * max_curtail_mw (within 0.2 MW).
    6. curtail_ramp_mw_per_hr > 0 and recover_ramp_mw_per_hr > 0.
    7. All dr_id values are unique.
    8. daily_energy_neutral is True for all buses.
    9. max_curtail_hours >= 1 and <= 24.
    10. min_recovery_gap_hr >= 0.
    11. notification_lead_hr >= 0.
    12. Total DR curtailment capacity is between 2% and 8% of system peak load.

    Args:
        dr_buses: DR bus definitions to validate.
        candidates: Full candidate list (for bus existence and Pd lookup).
        config: DR placement configuration.
        network_id: Network identifier (for error messages).

    Raises:
        ValueError: If any validation check fails.
    """
    net_label = network_id.value

    # Check 1: Bus count
    n = len(dr_buses)
    if n < config.min_buses or n > config.max_buses:
        msg = f"[{net_label}] DR bus count {n} outside [{config.min_buses}, {config.max_buses}]"
        raise ValueError(msg)

    # Build lookup from candidates
    candidate_map: dict[int, BusCandidate] = {c.bus: c for c in candidates}

    # Check 2: Every DR bus exists in candidates
    for dr in dr_buses:
        if dr.bus not in candidate_map:
            msg = f"[{net_label}] DR bus {dr.bus} not found in candidate list"
            raise ValueError(msg)

    # Check 3: Area diversity
    area_counts: dict[int, int] = {}
    for dr in dr_buses:
        cand = candidate_map[dr.bus]
        area_counts[cand.area] = area_counts.get(cand.area, 0) + 1

    for area, count in area_counts.items():
        if count > config.max_buses_per_area:
            msg = (
                f"[{net_label}] Area {area} has {count} DR buses, "
                f"exceeding max_buses_per_area={config.max_buses_per_area}"
            )
            raise ValueError(msg)

    # Check 4: Curtailment within bounds (with 2% tolerance for perturbation)
    tolerance = 0.02
    for dr in dr_buses:
        cand = candidate_map[dr.bus]
        pd = cand.pd_mw
        lower = (config.curtail_fraction_min - tolerance) * pd
        upper = (config.curtail_fraction_max + tolerance) * pd
        if dr.max_curtail_mw < lower - 0.15 or dr.max_curtail_mw > upper + 0.15:
            msg = (
                f"[{net_label}] DR bus {dr.bus}: max_curtail_mw={dr.max_curtail_mw} "
                f"outside [{lower:.1f}, {upper:.1f}] (Pd={pd:.1f} MW)"
            )
            raise ValueError(msg)

    # Check 5: Recovery ratio
    for dr in dr_buses:
        expected_recover = config.recovery_ratio * dr.max_curtail_mw
        if abs(dr.max_recover_mw - expected_recover) > 0.2:
            msg = (
                f"[{net_label}] DR bus {dr.bus}: max_recover_mw={dr.max_recover_mw} "
                f"!= {config.recovery_ratio} * {dr.max_curtail_mw} = {expected_recover:.1f}"
            )
            raise ValueError(msg)

    # Check 6: Positive ramp limits
    for dr in dr_buses:
        if dr.curtail_ramp_mw_per_hr <= 0:
            msg = (
                f"[{net_label}] DR bus {dr.bus}: "
                f"curtail_ramp_mw_per_hr={dr.curtail_ramp_mw_per_hr} <= 0"
            )
            raise ValueError(msg)
        if dr.recover_ramp_mw_per_hr <= 0:
            msg = (
                f"[{net_label}] DR bus {dr.bus}: "
                f"recover_ramp_mw_per_hr={dr.recover_ramp_mw_per_hr} <= 0"
            )
            raise ValueError(msg)

    # Check 7: Unique dr_ids
    dr_ids = [dr.dr_id for dr in dr_buses]
    if len(set(dr_ids)) != len(dr_ids):
        msg = f"[{net_label}] Duplicate dr_id values found"
        raise ValueError(msg)

    # Check 8: daily_energy_neutral is True
    for dr in dr_buses:
        if not dr.daily_energy_neutral:
            msg = f"[{net_label}] DR bus {dr.bus}: daily_energy_neutral is False"
            raise ValueError(msg)

    # Check 9: max_curtail_hours in [1, 24]
    for dr in dr_buses:
        if dr.max_curtail_hours < 1 or dr.max_curtail_hours > 24:
            msg = (
                f"[{net_label}] DR bus {dr.bus}: "
                f"max_curtail_hours={dr.max_curtail_hours} outside [1, 24]"
            )
            raise ValueError(msg)

    # Check 10: min_recovery_gap_hr >= 0
    for dr in dr_buses:
        if dr.min_recovery_gap_hr < 0:
            msg = f"[{net_label}] DR bus {dr.bus}: min_recovery_gap_hr={dr.min_recovery_gap_hr} < 0"
            raise ValueError(msg)

    # Check 11: notification_lead_hr >= 0
    for dr in dr_buses:
        if dr.notification_lead_hr < 0:
            msg = (
                f"[{net_label}] DR bus {dr.bus}: notification_lead_hr={dr.notification_lead_hr} < 0"
            )
            raise ValueError(msg)

    # Check 12: Total DR capacity between 2% and 8% of system peak
    total_curtail = sum(dr.max_curtail_mw for dr in dr_buses)
    system_peak = sum(c.pd_mw for c in candidates)
    if system_peak > 0:
        dr_fraction = total_curtail / system_peak
        if dr_fraction < 0.02 or dr_fraction > 0.08:
            msg = (
                f"[{net_label}] Total DR curtailment {total_curtail:.1f} MW is "
                f"{dr_fraction:.2%} of system peak {system_peak:.1f} MW, "
                f"outside [2%, 8%]"
            )
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------


def write_dr_buses_csv(
    dr_buses: list[DrBus],
    dest_path: Path,
) -> None:
    """Write DR bus definitions to CSV.

    Produces a CSV file with columns matching the Phase 2b PRD-06
    canonical schema. Boolean columns are written as "true" / "false"
    (lowercase). Float columns use 1 decimal place. Integer columns
    have no decimal points. Rows are ordered by dr_id.

    Args:
        dr_buses: List of DrBus records to write.
        dest_path: File path to write the CSV output. Parent directory
            is created if it does not exist.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by dr_id
    sorted_buses = sorted(dr_buses, key=lambda d: d.dr_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_DR_CSV_COLUMNS)

    for dr in sorted_buses:
        row = [
            dr.dr_id,
            str(dr.bus),
            f"{dr.max_curtail_mw:.1f}",
            f"{dr.max_recover_mw:.1f}",
            f"{dr.curtail_ramp_mw_per_hr:.1f}",
            f"{dr.recover_ramp_mw_per_hr:.1f}",
            str(dr.max_curtail_hours),
            f"{dr.min_recovery_gap_hr:.1f}",
            "true" if dr.daily_energy_neutral else "false",
            f"{dr.notification_lead_hr:.1f}",
        ]
        writer.writerow(row)

    dest_path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def place_dr_for_network(
    network_dir: Path,
    output_dir: Path,
    network_id: DrNetworkId,
    config: DrPlacementConfig | None = None,
    seed: int = 20240301,
) -> DrPlacementResult:
    """Place DR resources for a single network and write output CSV.

    This is the per-network entry point. It:
    1. Loads bus data from the cleaned .m file via load_bus_data.
    2. Selects DR buses via select_dr_buses with area diversity.
    3. Assigns DR parameters via assign_dr_parameters.
    4. Validates placement via validate_dr_placement.
    5. Writes dr_buses.csv to output_dir via write_dr_buses_csv.
    6. Computes summary statistics.

    Args:
        network_dir: Path to the directory containing the cleaned .m file.
        output_dir: Directory to write the output dr_buses.csv.
        network_id: Network identifier (SMALL or MEDIUM).
        config: DR placement configuration. If None, uses the default
            from DR_CONFIG_MAP for the given network_id.
        seed: Random seed for numpy generator (deterministic output).

    Returns:
        A DrPlacementResult with path, DR definitions, and summary stats.

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
        ValueError: If placement validation fails.
    """
    if config is None:
        config = DR_CONFIG_MAP[network_id]

    rng = np.random.default_rng(seed)

    candidates = load_bus_data(network_dir, network_id)
    selected = select_dr_buses(candidates, config, rng)
    dr_buses = assign_dr_parameters(selected, config, network_id, rng)
    validate_dr_placement(dr_buses, candidates, config, network_id)

    csv_path = output_dir / "dr_buses.csv"
    write_dr_buses_csv(dr_buses, csv_path)

    total_curtail = sum(dr.max_curtail_mw for dr in dr_buses)
    system_peak = sum(c.pd_mw for c in candidates)
    dr_fraction = total_curtail / system_peak if system_peak > 0 else 0.0

    return DrPlacementResult(
        network_id=network_id,
        dr_buses_csv=str(csv_path),
        dr_buses=dr_buses,
        total_curtail_mw=total_curtail,
        system_peak_mw=system_peak,
        dr_fraction_of_peak=dr_fraction,
    )


def main(
    data_root: Path | None = None,
    seed: int = 20240301,
) -> dict[DrNetworkId, DrPlacementResult]:
    """Entry point: place DR resources for all Phase 3 networks.

    Iterates over SMALL and MEDIUM networks, calling place_dr_for_network
    for each. Default paths resolve relative to the repository root:
    - network_dir: data/timeseries/<network_id>/
    - output_dir: data/timeseries/<network_id>/

    Args:
        data_root: Root directory for data files. Defaults to
            <repo_root>/data/timeseries/.
        seed: Random seed for reproducible placement across networks.
            Each network gets its own rng derived from this base seed
            plus a network-specific offset.

    Returns:
        Dict mapping network ID to DrPlacementResult.
    """
    if data_root is None:
        repo_root = Path(__file__).resolve().parent.parent
        data_root = repo_root / "timeseries"

    results: dict[DrNetworkId, DrPlacementResult] = {}

    for i, network_id in enumerate(DrNetworkId):
        network_dir = data_root / network_id.value
        output_dir = data_root / network_id.value
        network_seed = seed + i

        result = place_dr_for_network(
            network_dir=network_dir,
            output_dir=output_dir,
            network_id=network_id,
            seed=network_seed,
        )
        results[network_id] = result

        print(
            f"[{network_id.value}] Placed {len(result.dr_buses)} DR buses: "
            f"total_curtail={result.total_curtail_mw:.1f} MW, "
            f"system_peak={result.system_peak_mw:.1f} MW, "
            f"DR_fraction={result.dr_fraction_of_peak:.2%}"
        )

    return results


if __name__ == "__main__":
    main()
