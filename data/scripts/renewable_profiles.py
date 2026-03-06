"""Renewable Profile Synthesis & Placement for the case39 (TINY) network.

Defines synthetic wind and solar units for the IEEE 39-bus system and produces
24-hour generation profiles. The .m file is NOT modified -- supplemental CSVs
describe the new resources. Bus placement uses transmission headroom scoring
and area diversity. Capacity targets 15-25% of system peak (~6097 MW).
Wind gets 60%, solar 40%. Profiles use RTS-GMLC capacity factor shapes
for the representative day.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.reconcile_bus_gen import (
    MatpowerCaseData,
    parse_matpower_case,
)

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYSTEM_PEAK_LOAD_MW: float = 6097.0
TARGET_PENETRATION_MIN: float = 0.15
TARGET_PENETRATION_MAX: float = 0.25
WIND_CAPACITY_SHARE: float = 0.60
SOLAR_CAPACITY_SHARE: float = 0.40
NUM_WIND_BUSES: int = 3
NUM_SOLAR_BUSES: int = 2
GENERATOR_BUSES: set[int] = set(range(30, 40))  # buses 30-39
SOLAR_NIGHTTIME_HOURS: set[int] = {1, 2, 3, 4, 5, 6, 21, 22, 23, 24}

# Default RTS-GMLC-derived capacity factor profiles (representative day).
# These are synthetic approximations of typical RTS-GMLC shapes.
DEFAULT_WIND_CF_24H: list[float] = [
    0.42,
    0.45,
    0.48,
    0.50,
    0.47,
    0.43,  # HE1-6: moderate overnight wind
    0.38,
    0.32,
    0.28,
    0.25,
    0.22,
    0.20,  # HE7-12: morning drop-off
    0.18,
    0.20,
    0.23,
    0.27,
    0.32,
    0.38,  # HE13-18: afternoon ramp
    0.44,
    0.50,
    0.55,
    0.58,
    0.52,
    0.46,  # HE19-24: evening peak
]

DEFAULT_SOLAR_CF_24H: list[float] = [
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,  # HE1-6: nighttime zeros
    0.05,
    0.18,
    0.42,
    0.62,
    0.78,
    0.85,  # HE7-12: morning ramp to peak
    0.88,
    0.82,
    0.70,
    0.52,
    0.30,
    0.10,  # HE13-18: afternoon decline
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,  # HE19-24: nighttime zeros
]

HOUR_COLUMNS: list[str] = [f"HR_{h}" for h in range(1, 25)]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class RenewableType(StrEnum):
    """Type of renewable generator."""

    WIND = "wind"
    SOLAR = "solar"


@dataclass(frozen=True)
class BusHeadroomScore:
    """Transmission headroom score for a candidate bus.

    Headroom is estimated as the sum of (rateA - estimated_flow) for all
    branches connected to the bus. Higher scores indicate more room for
    new generation without congestion.
    """

    bus_id: int
    area: int
    headroom_mw: float
    is_generator_bus: bool
    branch_count: int


@dataclass(frozen=True)
class RenewableUnitSpec:
    """Specification for a single synthetic renewable generator."""

    gen_uid: str
    bus_id: int
    renewable_type: RenewableType
    pmax_mw: float
    area: int


@dataclass(frozen=True)
class CapacityFactorProfile:
    """24-hour capacity factor profile (values in [0, 1])."""

    renewable_type: RenewableType
    values: list[float]  # length 24, one per hour ending


@dataclass(frozen=True)
class RenewableProfile24h:
    """24-hour MW profile for a single renewable generator."""

    gen_uid: str
    renewable_type: RenewableType
    pmax_mw: float
    values_mw: list[float]  # length 24, MW output per hour ending


@dataclass(frozen=True)
class BusPlacementResult:
    """Result of the bus placement algorithm."""

    wind_buses: list[int]
    solar_buses: list[int]
    headroom_scores: list[BusHeadroomScore]


@dataclass(frozen=True)
class RenewableSynthesisResult:
    """Complete result of the renewable profile synthesis."""

    units: list[RenewableUnitSpec]
    wind_profiles: list[RenewableProfile24h]
    solar_profiles: list[RenewableProfile24h]
    placement: BusPlacementResult
    total_wind_mw: float
    total_solar_mw: float
    total_renewable_mw: float
    penetration_pct: float


# ---------------------------------------------------------------------------
# Branch loading & headroom scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _BranchRecord:
    """Internal representation of a MATPOWER branch row."""

    fbus: int
    tbus: int
    rate_a: float


def _parse_branches(case_data: MatpowerCaseData) -> list[_BranchRecord]:
    """Parse branch data from the MATPOWER case file.

    Re-reads the .m file to extract the mpc.branch matrix. We need columns:
    fbus (0), tbus (1), rateA (5).

    Args:
        case_data: Previously parsed case data (used for file path).

    Returns:
        List of _BranchRecord.
    """
    import re

    text = Path(case_data.file_path).read_text()
    pattern = re.compile(r"mpc\.branch\s*=\s*\[([^\]]*)\]", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        msg = "Could not locate mpc.branch block"
        raise ValueError(msg)

    branches: list[_BranchRecord] = []
    for line in match.group(1).split(";"):
        line = line.strip()
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        vals = line.split()
        if len(vals) < 6:
            continue
        branches.append(
            _BranchRecord(
                fbus=int(float(vals[0])),
                tbus=int(float(vals[1])),
                rate_a=float(vals[5]),
            )
        )
    return branches


def compute_branch_loading(case_data: MatpowerCaseData) -> list[BusHeadroomScore]:
    """Compute transmission headroom score for every bus in the network.

    For each bus, sums the rateA of all connected branches. Buses with
    generators are flagged (is_generator_bus=True). The area field comes
    from the bus data (column 6, 0-indexed).

    Args:
        case_data: Parsed MATPOWER case data.

    Returns:
        List of BusHeadroomScore sorted by headroom_mw descending.
    """
    branches = _parse_branches(case_data)

    # Build bus area map from parsed bus data
    bus_area: dict[int, int] = {}
    for bus in case_data.buses:
        # Area is the 7th column (0-indexed: bus_i, type, Pd, Qd, Gs, Bs, area)
        # We need to re-parse for area since MatpowerBusRecord doesn't store it.
        bus_area[bus.bus_id] = 0  # placeholder, will be filled below

    # Re-parse areas from file
    text = Path(case_data.file_path).read_text()
    import re

    pattern = re.compile(r"mpc\.bus\s*=\s*\[([^\]]*)\]", re.DOTALL)
    match = pattern.search(text)
    if match:
        for line in match.group(1).split(";"):
            line = line.strip()
            if "%" in line:
                line = line[: line.index("%")]
            line = line.strip()
            if not line:
                continue
            vals = line.split()
            if len(vals) >= 7:
                bus_id = int(float(vals[0]))
                area = int(float(vals[6]))
                bus_area[bus_id] = area

    # Sum rateA for branches connected to each bus
    bus_headroom: dict[int, float] = {b.bus_id: 0.0 for b in case_data.buses}
    bus_branch_count: dict[int, int] = {b.bus_id: 0 for b in case_data.buses}

    for br in branches:
        if br.rate_a > 0:
            if br.fbus in bus_headroom:
                bus_headroom[br.fbus] += br.rate_a
                bus_branch_count[br.fbus] += 1
            if br.tbus in bus_headroom:
                bus_headroom[br.tbus] += br.rate_a
                bus_branch_count[br.tbus] += 1

    gen_buses = {g.gen_bus for g in case_data.generators}

    scores: list[BusHeadroomScore] = []
    for bus in case_data.buses:
        scores.append(
            BusHeadroomScore(
                bus_id=bus.bus_id,
                area=bus_area.get(bus.bus_id, 0),
                headroom_mw=bus_headroom[bus.bus_id],
                is_generator_bus=bus.bus_id in gen_buses,
                branch_count=bus_branch_count[bus.bus_id],
            )
        )

    scores.sort(key=lambda s: s.headroom_mw, reverse=True)
    return scores


# ---------------------------------------------------------------------------
# Bus selection
# ---------------------------------------------------------------------------


def select_renewable_buses(
    scores: list[BusHeadroomScore],
    num_wind: int = NUM_WIND_BUSES,
    num_solar: int = NUM_SOLAR_BUSES,
) -> BusPlacementResult:
    """Select buses for wind and solar placement using headroom and area diversity.

    Selection rules:
    1. Only non-generator buses are candidates.
    2. Candidates sorted by headroom descending.
    3. Wind buses selected first, preferring area diversity.
    4. Solar buses selected from remaining candidates, preferring area diversity.
    5. No overlap between wind and solar bus sets.

    Args:
        scores: Headroom scores for all buses (sorted descending).
        num_wind: Number of wind buses to select.
        num_solar: Number of solar buses to select.

    Returns:
        BusPlacementResult with selected wind and solar buses.

    Raises:
        ValueError: If insufficient non-generator candidate buses.
    """
    candidates = [s for s in scores if not s.is_generator_bus]
    candidates.sort(key=lambda s: s.headroom_mw, reverse=True)

    total_needed = num_wind + num_solar
    if len(candidates) < total_needed:
        msg = f"Need {total_needed} non-generator buses but only {len(candidates)} available"
        raise ValueError(msg)

    def _select_diverse(pool: list[BusHeadroomScore], count: int) -> list[int]:
        """Greedily select buses maximizing area diversity."""
        selected: list[int] = []
        areas_used: set[int] = set()
        remaining = list(pool)

        while len(selected) < count and remaining:
            # First pass: pick from unseen areas
            best = None
            for i, cand in enumerate(remaining):
                if cand.area not in areas_used:
                    best = i
                    break
            if best is None:
                # All areas seen, pick highest headroom
                best = 0

            chosen = remaining.pop(best)
            selected.append(chosen.bus_id)
            areas_used.add(chosen.area)

        return selected

    wind_buses = _select_diverse(candidates, num_wind)
    remaining_candidates = [c for c in candidates if c.bus_id not in set(wind_buses)]
    solar_buses = _select_diverse(remaining_candidates, num_solar)

    return BusPlacementResult(
        wind_buses=wind_buses,
        solar_buses=solar_buses,
        headroom_scores=scores,
    )


# ---------------------------------------------------------------------------
# Capacity computation
# ---------------------------------------------------------------------------


def compute_unit_capacities(
    wind_buses: list[int],
    solar_buses: list[int],
    penetration: float = 0.20,
    system_peak_mw: float = SYSTEM_PEAK_LOAD_MW,
    wind_share: float = WIND_CAPACITY_SHARE,
) -> list[RenewableUnitSpec]:
    """Compute Pmax for each renewable unit based on capacity targets.

    Total renewable capacity = penetration * system_peak_mw.
    Wind gets wind_share of total, solar gets the rest.
    Capacity split evenly among buses of each type.

    Args:
        wind_buses: Bus IDs selected for wind.
        solar_buses: Bus IDs selected for solar.
        penetration: Target renewable penetration (0.15-0.25).
        system_peak_mw: System peak load in MW.
        wind_share: Fraction of total renewable capacity for wind.

    Returns:
        List of RenewableUnitSpec for all renewable units.

    Raises:
        ValueError: If penetration is outside [0.15, 0.25].
    """
    if not (TARGET_PENETRATION_MIN <= penetration <= TARGET_PENETRATION_MAX):
        msg = (
            f"Penetration {penetration:.2%} outside allowed range "
            f"[{TARGET_PENETRATION_MIN:.0%}, {TARGET_PENETRATION_MAX:.0%}]"
        )
        raise ValueError(msg)

    total_mw = penetration * system_peak_mw
    wind_total = total_mw * wind_share
    solar_total = total_mw * (1.0 - wind_share)

    wind_per_bus = wind_total / len(wind_buses) if wind_buses else 0.0
    solar_per_bus = solar_total / len(solar_buses) if solar_buses else 0.0

    units: list[RenewableUnitSpec] = []
    uid_counter = 1

    for bus_id in wind_buses:
        units.append(
            RenewableUnitSpec(
                gen_uid=f"WIND_{uid_counter}",
                bus_id=bus_id,
                renewable_type=RenewableType.WIND,
                pmax_mw=round(wind_per_bus, 2),
                area=0,  # will be filled during synthesis
            )
        )
        uid_counter += 1

    uid_counter = 1
    for bus_id in solar_buses:
        units.append(
            RenewableUnitSpec(
                gen_uid=f"SOLAR_{uid_counter}",
                bus_id=bus_id,
                renewable_type=RenewableType.SOLAR,
                pmax_mw=round(solar_per_bus, 2),
                area=0,  # will be filled during synthesis
            )
        )
        uid_counter += 1

    return units


# ---------------------------------------------------------------------------
# RTS-GMLC profile loading
# ---------------------------------------------------------------------------


def load_rts_gmlc_wind_profile(
    profile_path: Path | None = None,
) -> CapacityFactorProfile:
    """Load RTS-GMLC wind capacity factor profile for the representative day.

    If profile_path is None or the file does not exist, returns the default
    synthetic profile based on RTS-GMLC shapes.

    Args:
        profile_path: Optional path to a CSV with 24 CF values.

    Returns:
        CapacityFactorProfile for wind.
    """
    if profile_path is not None and profile_path.exists():
        values = _load_cf_csv(profile_path)
        return CapacityFactorProfile(renewable_type=RenewableType.WIND, values=values)

    return CapacityFactorProfile(
        renewable_type=RenewableType.WIND,
        values=list(DEFAULT_WIND_CF_24H),
    )


def load_rts_gmlc_solar_profile(
    profile_path: Path | None = None,
) -> CapacityFactorProfile:
    """Load RTS-GMLC solar capacity factor profile for the representative day.

    If profile_path is None or the file does not exist, returns the default
    synthetic profile based on RTS-GMLC shapes. Solar nighttime hours
    (HE 1-6, 21-24) are forced to zero.

    Args:
        profile_path: Optional path to a CSV with 24 CF values.

    Returns:
        CapacityFactorProfile for solar.
    """
    if profile_path is not None and profile_path.exists():
        values = _load_cf_csv(profile_path)
        # Enforce nighttime zeros
        for i in range(24):
            if (i + 1) in SOLAR_NIGHTTIME_HOURS:
                values[i] = 0.0
        return CapacityFactorProfile(renewable_type=RenewableType.SOLAR, values=values)

    return CapacityFactorProfile(
        renewable_type=RenewableType.SOLAR,
        values=list(DEFAULT_SOLAR_CF_24H),
    )


def _load_cf_csv(path: Path) -> list[float]:
    """Load a single-row CF CSV with HR_1..HR_24 columns."""
    with open(path) as fh:
        reader = csv.DictReader(fh)
        row = next(reader)
        return [float(row[f"HR_{h}"]) for h in range(1, 25)]


# ---------------------------------------------------------------------------
# Profile scaling
# ---------------------------------------------------------------------------


def scale_profiles(
    units: list[RenewableUnitSpec],
    wind_cf: CapacityFactorProfile,
    solar_cf: CapacityFactorProfile,
) -> tuple[list[RenewableProfile24h], list[RenewableProfile24h]]:
    """Scale capacity factor profiles to MW for each renewable unit.

    MW_h = CF_h * Pmax for each hour h. Solar nighttime hours are enforced
    to zero regardless of CF values.

    Args:
        units: Renewable unit specifications.
        wind_cf: 24-hour wind capacity factor profile.
        solar_cf: 24-hour solar capacity factor profile.

    Returns:
        Tuple of (wind_profiles, solar_profiles).
    """
    wind_profiles: list[RenewableProfile24h] = []
    solar_profiles: list[RenewableProfile24h] = []

    for unit in units:
        if unit.renewable_type == RenewableType.WIND:
            cf = wind_cf
        else:
            cf = solar_cf

        values_mw = []
        for h_idx, cf_val in enumerate(cf.values):
            hour_ending = h_idx + 1
            if unit.renewable_type == RenewableType.SOLAR and hour_ending in SOLAR_NIGHTTIME_HOURS:
                values_mw.append(0.0)
            else:
                values_mw.append(round(cf_val * unit.pmax_mw, 4))

        profile = RenewableProfile24h(
            gen_uid=unit.gen_uid,
            renewable_type=unit.renewable_type,
            pmax_mw=unit.pmax_mw,
            values_mw=values_mw,
        )

        if unit.renewable_type == RenewableType.WIND:
            wind_profiles.append(profile)
        else:
            solar_profiles.append(profile)

    return wind_profiles, solar_profiles


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_renewable_units_csv(
    units: list[RenewableUnitSpec],
    dest_path: Path,
) -> None:
    """Write renewable unit specifications to CSV.

    Columns: gen_uid, bus_id, type, pmax_mw, area.

    Args:
        units: Renewable unit specifications.
        dest_path: Output CSV file path.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid", "bus_id", "type", "pmax_mw", "area"])
        for u in units:
            writer.writerow([u.gen_uid, u.bus_id, u.renewable_type.value, u.pmax_mw, u.area])


def write_wind_24h_csv(
    profiles: list[RenewableProfile24h],
    dest_path: Path,
) -> None:
    """Write wind 24-hour MW profiles to CSV.

    Columns: gen_uid, HR_1..HR_24.

    Args:
        profiles: Wind MW profiles.
        dest_path: Output CSV file path.
    """
    _write_profile_csv(profiles, dest_path)


def write_solar_24h_csv(
    profiles: list[RenewableProfile24h],
    dest_path: Path,
) -> None:
    """Write solar 24-hour MW profiles to CSV.

    Columns: gen_uid, HR_1..HR_24.

    Args:
        profiles: Solar MW profiles.
        dest_path: Output CSV file path.
    """
    _write_profile_csv(profiles, dest_path)


def _write_profile_csv(
    profiles: list[RenewableProfile24h],
    dest_path: Path,
) -> None:
    """Write profiles in canonical gen_uid + HR_1..HR_24 format."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid"] + HOUR_COLUMNS)
        for p in profiles:
            writer.writerow([p.gen_uid] + [f"{v:.4f}" for v in p.values_mw])


def write_placement_metadata(
    result: RenewableSynthesisResult,
    dest_path: Path,
) -> None:
    """Write placement metadata as JSON for downstream reference.

    Args:
        result: Complete synthesis result.
        dest_path: Output JSON file path.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "system_peak_load_mw": SYSTEM_PEAK_LOAD_MW,
        "total_renewable_mw": result.total_renewable_mw,
        "penetration_pct": result.penetration_pct,
        "wind_buses": result.placement.wind_buses,
        "solar_buses": result.placement.solar_buses,
        "total_wind_mw": result.total_wind_mw,
        "total_solar_mw": result.total_solar_mw,
        "units": [
            {
                "gen_uid": u.gen_uid,
                "bus_id": u.bus_id,
                "type": u.renewable_type.value,
                "pmax_mw": u.pmax_mw,
            }
            for u in result.units
        ],
    }
    with open(dest_path, "w") as fh:
        json.dump(metadata, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def synthesize_renewable_profiles(
    case_data: MatpowerCaseData,
    penetration: float = 0.20,
    wind_cf_path: Path | None = None,
    solar_cf_path: Path | None = None,
) -> RenewableSynthesisResult:
    """Run the full renewable profile synthesis pipeline.

    Steps:
    1. Compute branch loading headroom scores for all buses.
    2. Select wind and solar buses using headroom + area diversity.
    3. Compute unit capacities based on penetration target.
    4. Load RTS-GMLC capacity factor profiles.
    5. Scale profiles to MW.

    Args:
        case_data: Parsed MATPOWER case data.
        penetration: Target renewable penetration (0.15-0.25).
        wind_cf_path: Optional path to wind CF CSV.
        solar_cf_path: Optional path to solar CF CSV.

    Returns:
        RenewableSynthesisResult with all units and profiles.
    """
    # Step 1: Headroom scores
    scores = compute_branch_loading(case_data)

    # Step 2: Bus placement
    placement = select_renewable_buses(scores)

    # Step 3: Capacities
    units = compute_unit_capacities(
        wind_buses=placement.wind_buses,
        solar_buses=placement.solar_buses,
        penetration=penetration,
    )

    # Enrich units with area info from scores
    area_map = {s.bus_id: s.area for s in scores}
    enriched_units = [
        RenewableUnitSpec(
            gen_uid=u.gen_uid,
            bus_id=u.bus_id,
            renewable_type=u.renewable_type,
            pmax_mw=u.pmax_mw,
            area=area_map.get(u.bus_id, 0),
        )
        for u in units
    ]

    # Step 4: Load CF profiles
    wind_cf = load_rts_gmlc_wind_profile(wind_cf_path)
    solar_cf = load_rts_gmlc_solar_profile(solar_cf_path)

    # Step 5: Scale
    wind_profiles, solar_profiles = scale_profiles(enriched_units, wind_cf, solar_cf)

    total_wind = sum(u.pmax_mw for u in enriched_units if u.renewable_type == RenewableType.WIND)
    total_solar = sum(u.pmax_mw for u in enriched_units if u.renewable_type == RenewableType.SOLAR)
    total_renewable = total_wind + total_solar
    penetration_pct = (total_renewable / SYSTEM_PEAK_LOAD_MW) * 100.0

    return RenewableSynthesisResult(
        units=enriched_units,
        wind_profiles=wind_profiles,
        solar_profiles=solar_profiles,
        placement=placement,
        total_wind_mw=total_wind,
        total_solar_mw=total_solar,
        total_renewable_mw=total_renewable,
        penetration_pct=penetration_pct,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    m_file_path: Path | None = None,
    output_dir: Path | None = None,
    penetration: float = 0.20,
) -> RenewableSynthesisResult:
    """Entry point: synthesize renewable profiles and write output CSVs.

    Args:
        m_file_path: Path to the case39.m file. Defaults to
            <repo_root>/data/networks/case39.m.
        output_dir: Output directory for CSVs. Defaults to
            <repo_root>/data/timeseries/case39/.
        penetration: Target renewable penetration (0.15-0.25).

    Returns:
        The complete RenewableSynthesisResult.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if m_file_path is None:
        m_file_path = repo_root / "networks" / "case39.m"
    if output_dir is None:
        output_dir = repo_root / "timeseries" / "case39"

    case_data = parse_matpower_case(m_file_path)
    result = synthesize_renewable_profiles(case_data, penetration=penetration)

    # Write outputs
    write_renewable_units_csv(result.units, output_dir / "renewable_units.csv")
    write_wind_24h_csv(result.wind_profiles, output_dir / "wind_actual_24h.csv")
    write_solar_24h_csv(result.solar_profiles, output_dir / "solar_actual_24h.csv")
    write_placement_metadata(result, output_dir / "renewable_placement.json")

    logger.info(
        "Synthesized %d renewable units: %.1f MW wind + %.1f MW solar = %.1f MW (%.1f%%)",
        len(result.units),
        result.total_wind_mw,
        result.total_solar_mw,
        result.total_renewable_mw,
        result.penetration_pct,
    )

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
