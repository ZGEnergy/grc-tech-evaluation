"""SCUC Feasibility Screening (PRD 03/05).

Verifies necessary conditions for Security-Constrained Unit Commitment (SCUC)
feasibility across all three networks (TINY case39, SMALL ACTIVSg2000, MEDIUM
ACTIVSg10k) for each of the 24 hours in the planning horizon.

Checks are organized into three categories:
  1. Capacity adequacy (hourly): Pmin headroom and Pmax capacity checks.
  2. Ramp adequacy (inter-hour): aggregate fleet ramp vs. load shape.
  3. Parameter validity (per-generator): Pmin/Pmax consistency, non-negative
     costs, and min up/down time validity.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.reconcile_bus_gen import parse_matpower_case

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PMIN_MARGIN: float = 0.95
"""Pmin headroom threshold: sum(Pmin) must be below this fraction of hourly load."""

PMIN_WARN_THRESHOLD: float = 0.90
"""Warning threshold for Pmin/load ratio."""

PMAX_MARGIN: float = 1.05
"""Generation capacity threshold: sum(Pmax) must exceed this multiple of peak load."""

PMAX_WARN_MARGIN: float = 1.10
"""Warning threshold for Pmax/peak_load ratio."""

RAMP_WARN_MARGIN: float = 1.10
"""Warning threshold for ramp adequacy."""

MAX_MIN_UP_DOWN_HR: int = 24
"""Maximum allowed min up/down time in hours. Equals the planning horizon length."""

RENEWABLE_FUEL_TYPES: frozenset[str] = frozenset({"wind", "solar"})
"""Fuel types excluded from Pmin headroom checks and min up/down time validation."""

NETWORK_IDS: tuple[str, ...] = ("case39", "ACTIVSg2000", "ACTIVSg10k")
"""All three networks to validate."""

NETWORK_M_FILE_NAMES: dict[str, str] = {
    "case39": "case39.m",
    "ACTIVSg2000": "case_ACTIVSg2000.m",
    "ACTIVSg10k": "case_ACTIVSg10k.m",
}

MAX_VIOLATIONS_REPORTED: int = 20
"""Cap on per-check violation entries in JSON output."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers for SCUC feasibility screening."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class CheckSeverity(StrEnum):
    """Outcome severity for a single feasibility check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class GeneratorRecord:
    """Generator parameters relevant to SCUC feasibility screening.

    Combines static parameters from the cleaned .m file (Pmin, Pmax)
    with temporal parameters from gen_temporal_params.csv (ramp rates,
    min up/down times, startup/shutdown costs). Renewable generators
    have ramp rates and min up/down times set to 0.0 by convention.
    """

    gen_uid: str
    bus_id: int
    pmax_mw: float
    pmin_mw: float
    fuel_type: str
    tech_class: str
    ramp_rate_mw_per_hr: float
    min_up_time_hr: float
    min_down_time_hr: float
    startup_cost_dollar: float
    shutdown_cost_dollar: float
    is_renewable: bool


@dataclass(frozen=True)
class HourlyCapacityResult:
    """Result of per-hour Pmin headroom and Pmax capacity checks."""

    pmin_load_ratios: list[float]
    tightest_hour: int
    tightest_ratio: float
    sum_pmin_mw: float
    pmin_check_status: CheckSeverity
    pmin_check_message: str

    pmax_total_mw: float
    peak_load_mw: float
    pmax_margin: float
    pmax_check_status: CheckSeverity
    pmax_check_message: str


@dataclass(frozen=True)
class RampAdequacyResult:
    """Result of ramp-up and ramp-down adequacy checks."""

    fleet_ramp_up_mw_per_hr: float
    max_load_increase_mw: float
    ramp_up_hour: int
    ramp_up_margin: float
    ramp_up_status: CheckSeverity
    ramp_up_message: str

    fleet_ramp_down_mw_per_hr: float
    max_load_decrease_mw: float
    ramp_down_hour: int
    ramp_down_margin: float
    ramp_down_status: CheckSeverity
    ramp_down_message: str


@dataclass(frozen=True)
class ParameterViolation:
    """A single generator parameter violation."""

    gen_uid: str
    check_name: str
    message: str
    value: float
    threshold: float | None


@dataclass(frozen=True)
class ParameterValidityResult:
    """Result of per-generator parameter validity checks (e, f, g)."""

    pmin_pmax_violations: list[ParameterViolation]
    cost_violations: list[ParameterViolation]
    time_violations: list[ParameterViolation]
    total_generators_checked: int
    total_violations: int
    pmin_pmax_status: CheckSeverity
    cost_status: CheckSeverity
    time_status: CheckSeverity


@dataclass(frozen=True)
class FeasibilityResult:
    """Complete SCUC feasibility screening result for a single network."""

    network_id: str
    hourly_capacity: HourlyCapacityResult
    ramp_adequacy: RampAdequacyResult
    parameter_validity: ParameterValidityResult
    total_checks: int
    checks_passed: int
    checks_warned: int
    checks_failed: int
    overall_pass: bool
    load_profile_mw: list[float]


@dataclass(frozen=True)
class FeasibilityReport:
    """Consolidated SCUC feasibility report across all networks."""

    network_results: list[FeasibilityResult]
    total_checks: int
    total_passed: int
    total_warned: int
    total_failed: int
    overall_pass: bool
    script_version: str


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_generators(
    network_dir: Path,
    network_id: str,
) -> list[GeneratorRecord]:
    """Load generator parameters from the cleaned .m file and gen_temporal_params.csv.

    Merges static parameters (Pmin, Pmax, bus_id) from the cleaned .m file's
    gen data table with temporal parameters (ramp rates, min up/down times,
    startup/shutdown costs, fuel_type, tech_class) from gen_temporal_params.csv.

    Generators are matched between the .m file and the CSV by position
    (row index), consistent with the reconciliation approach in Phase 1 D2.

    Args:
        network_dir: Path to data/timeseries/<network_id>/ containing
            the cleaned .m file and gen_temporal_params.csv.
        network_id: Network identifier for locating the .m file.

    Returns:
        A list of GeneratorRecord, one per generator in the network.

    Raises:
        FileNotFoundError: If the cleaned .m file or gen_temporal_params.csv
            is not found.
        ValueError: If the generator count in the .m file does not match the
            row count in gen_temporal_params.csv.
    """
    m_file_name = NETWORK_M_FILE_NAMES[network_id]
    m_path = network_dir / m_file_name

    case_data = parse_matpower_case(m_path)

    temporal_csv_path = network_dir / "gen_temporal_params.csv"
    if not temporal_csv_path.exists():
        msg = f"gen_temporal_params.csv not found: {temporal_csv_path}"
        raise FileNotFoundError(msg)

    text = temporal_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    temporal_rows = list(reader)

    if len(case_data.generators) != len(temporal_rows):
        msg = (
            f"Generator count mismatch for {network_id}: "
            f".m file has {len(case_data.generators)} generators, "
            f"gen_temporal_params.csv has {len(temporal_rows)} rows"
        )
        raise ValueError(msg)

    records: list[GeneratorRecord] = []
    for i, (gen, trow) in enumerate(zip(case_data.generators, temporal_rows, strict=True)):
        fuel_type = trow["fuel_type"].strip().lower()
        records.append(
            GeneratorRecord(
                gen_uid=trow["gen_uid"].strip(),
                bus_id=gen.gen_bus,
                pmax_mw=gen.pmax,
                pmin_mw=gen.pmin,
                fuel_type=fuel_type,
                tech_class=trow["tech_class"].strip(),
                ramp_rate_mw_per_hr=float(trow["ramp_rate_mw_per_hr"]),
                min_up_time_hr=float(trow["min_up_time_hr"]),
                min_down_time_hr=float(trow["min_down_time_hr"]),
                startup_cost_dollar=float(trow["startup_cost_dollar"]),
                shutdown_cost_dollar=float(trow["shutdown_cost_dollar"]),
                is_renewable=fuel_type in RENEWABLE_FUEL_TYPES,
            )
        )

    return records


def load_load_profile(
    network_dir: Path,
) -> list[float]:
    """Load the 24-hour system load profile from load_24h.csv.

    Reads the load CSV and sums across all buses for each hour to produce
    a 24-element list of total system load in MW. The CSV uses the canonical
    format with columns bus_id, HR_1..HR_24.

    Args:
        network_dir: Path to data/timeseries/<network_id>/ containing
            load_24h.csv.

    Returns:
        A list of 24 float values representing total system load per hour
        in MW.

    Raises:
        FileNotFoundError: If load_24h.csv is not found.
        ValueError: If the CSV does not contain exactly 24 hourly columns.
    """
    load_csv_path = network_dir / "load_24h.csv"
    if not load_csv_path.exists():
        msg = f"load_24h.csv not found: {load_csv_path}"
        raise FileNotFoundError(msg)

    text = load_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    # Identify HR_1..HR_24 columns
    hr_columns = [f"HR_{h}" for h in range(1, 25)]
    header_set = set(rows[0].keys()) if rows else set()
    for col in hr_columns:
        if col not in header_set:
            msg = f"Missing expected column {col} in load_24h.csv"
            raise ValueError(msg)

    # Sum across all buses for each hour
    load_profile: list[float] = []
    for col in hr_columns:
        total = sum(float(row[col]) for row in rows)
        load_profile.append(total)

    return load_profile


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_pmin_headroom(
    generators: list[GeneratorRecord],
    load_profile: list[float],
) -> HourlyCapacityResult:
    """Check (a) and (b): Pmin headroom and Pmax capacity adequacy.

    For check (a), computes the sum of Pmin across all non-renewable
    generators and compares it to PMIN_MARGIN * load[h] for each hour.

    For check (b), computes the sum of Pmax across all generators
    (including renewables at nameplate capacity) and compares it to
    PMAX_MARGIN * peak_load.

    Args:
        generators: All generators for the network.
        load_profile: 24-hour system load profile in MW.

    Returns:
        An HourlyCapacityResult with per-hour ratios, tightest hour,
        and status for both checks (a) and (b).
    """
    # Check (a): Pmin headroom
    sum_pmin = sum(g.pmin_mw for g in generators if not g.is_renewable)

    ratios: list[float] = []
    for load_h in load_profile:
        ratio = sum_pmin / load_h if load_h > 0 else 0.0
        ratios.append(ratio)

    tightest_hour = 0
    tightest_ratio = 0.0
    if ratios:
        tightest_ratio = max(ratios)
        tightest_hour = ratios.index(tightest_ratio)

    # Determine Pmin check status
    if tightest_ratio >= PMIN_MARGIN:
        pmin_status = CheckSeverity.FAIL
        pmin_msg = (
            f"Pmin headroom FAIL: tightest hour {tightest_hour} has "
            f"sum(Pmin)/load = {tightest_ratio:.4f} >= {PMIN_MARGIN}"
        )
    elif tightest_ratio >= PMIN_WARN_THRESHOLD:
        pmin_status = CheckSeverity.WARN
        pmin_msg = (
            f"Pmin headroom WARN: tightest hour {tightest_hour} has "
            f"sum(Pmin)/load = {tightest_ratio:.4f} >= {PMIN_WARN_THRESHOLD}"
        )
    else:
        pmin_status = CheckSeverity.PASS
        pmin_msg = (
            f"Pmin headroom PASS: tightest hour {tightest_hour} has "
            f"sum(Pmin)/load = {tightest_ratio:.4f}"
        )

    # Check (b): Pmax capacity adequacy
    pmax_total = sum(g.pmax_mw for g in generators)
    peak_load = max(load_profile) if load_profile else 0.0
    pmax_margin = pmax_total / peak_load if peak_load > 0 else 0.0

    if pmax_margin < PMAX_MARGIN:
        pmax_status = CheckSeverity.FAIL
        pmax_msg = f"Pmax capacity FAIL: sum(Pmax)/peak_load = {pmax_margin:.4f} < {PMAX_MARGIN}"
    elif pmax_margin < PMAX_WARN_MARGIN:
        pmax_status = CheckSeverity.WARN
        pmax_msg = (
            f"Pmax capacity WARN: sum(Pmax)/peak_load = {pmax_margin:.4f} < {PMAX_WARN_MARGIN}"
        )
    else:
        pmax_status = CheckSeverity.PASS
        pmax_msg = f"Pmax capacity PASS: sum(Pmax)/peak_load = {pmax_margin:.4f}"

    return HourlyCapacityResult(
        pmin_load_ratios=ratios,
        tightest_hour=tightest_hour,
        tightest_ratio=tightest_ratio,
        sum_pmin_mw=sum_pmin,
        pmin_check_status=pmin_status,
        pmin_check_message=pmin_msg,
        pmax_total_mw=pmax_total,
        peak_load_mw=peak_load,
        pmax_margin=pmax_margin,
        pmax_check_status=pmax_status,
        pmax_check_message=pmax_msg,
    )


def check_ramp_adequacy(
    generators: list[GeneratorRecord],
    load_profile: list[float],
) -> RampAdequacyResult:
    """Check (c) and (d): ramp-up and ramp-down adequacy.

    Computes the maximum hour-over-hour load increase and decrease
    from the 24-hour load profile. Computes the aggregate fleet
    ramp capability as the sum of ramp_rate_mw_per_hr across all
    generators.

    Args:
        generators: All generators for the network.
        load_profile: 24-hour system load profile in MW.

    Returns:
        A RampAdequacyResult with fleet ramp values, max load changes,
        margins, and status for both ramp-up and ramp-down.
    """
    fleet_ramp = sum(g.ramp_rate_mw_per_hr for g in generators)

    # Compute hour-over-hour changes
    max_increase = 0.0
    ramp_up_hour = 0
    max_decrease = 0.0
    ramp_down_hour = 0

    for h in range(len(load_profile) - 1):
        diff = load_profile[h + 1] - load_profile[h]
        if diff > max_increase:
            max_increase = diff
            ramp_up_hour = h
        if -diff > max_decrease:
            max_decrease = -diff
            ramp_down_hour = h

    # Check (c): ramp-up adequacy
    if max_increase <= 0:
        ramp_up_margin = float("inf")
        ramp_up_status = CheckSeverity.PASS
        ramp_up_msg = "Ramp-up PASS: no load increases in profile"
    else:
        ramp_up_margin = fleet_ramp / max_increase
        if fleet_ramp < max_increase:
            ramp_up_status = CheckSeverity.FAIL
            ramp_up_msg = (
                f"Ramp-up FAIL: fleet ramp {fleet_ramp:.1f} MW/hr "
                f"< max load increase {max_increase:.1f} MW at hour {ramp_up_hour}"
            )
        elif ramp_up_margin < RAMP_WARN_MARGIN:
            ramp_up_status = CheckSeverity.WARN
            ramp_up_msg = f"Ramp-up WARN: margin {ramp_up_margin:.4f} < {RAMP_WARN_MARGIN}"
        else:
            ramp_up_status = CheckSeverity.PASS
            ramp_up_msg = f"Ramp-up PASS: margin {ramp_up_margin:.4f}"

    # Check (d): ramp-down adequacy
    if max_decrease <= 0:
        ramp_down_margin = float("inf")
        ramp_down_status = CheckSeverity.PASS
        ramp_down_msg = "Ramp-down PASS: no load decreases in profile"
    else:
        ramp_down_margin = fleet_ramp / max_decrease
        if fleet_ramp < max_decrease:
            ramp_down_status = CheckSeverity.FAIL
            ramp_down_msg = (
                f"Ramp-down FAIL: fleet ramp {fleet_ramp:.1f} MW/hr "
                f"< max load decrease {max_decrease:.1f} MW at hour {ramp_down_hour}"
            )
        elif ramp_down_margin < RAMP_WARN_MARGIN:
            ramp_down_status = CheckSeverity.WARN
            ramp_down_msg = f"Ramp-down WARN: margin {ramp_down_margin:.4f} < {RAMP_WARN_MARGIN}"
        else:
            ramp_down_status = CheckSeverity.PASS
            ramp_down_msg = f"Ramp-down PASS: margin {ramp_down_margin:.4f}"

    return RampAdequacyResult(
        fleet_ramp_up_mw_per_hr=fleet_ramp,
        max_load_increase_mw=max_increase,
        ramp_up_hour=ramp_up_hour,
        ramp_up_margin=ramp_up_margin,
        ramp_up_status=ramp_up_status,
        ramp_up_message=ramp_up_msg,
        fleet_ramp_down_mw_per_hr=fleet_ramp,
        max_load_decrease_mw=max_decrease,
        ramp_down_hour=ramp_down_hour,
        ramp_down_margin=ramp_down_margin,
        ramp_down_status=ramp_down_status,
        ramp_down_message=ramp_down_msg,
    )


def check_pmin_pmax_consistency(
    generators: list[GeneratorRecord],
) -> tuple[list[ParameterViolation], CheckSeverity]:
    """Check (e): no generator has Pmin > Pmax.

    A strict inequality is used (Pmin == Pmax is allowed; it represents
    a must-run unit with no dispatch flexibility).

    Args:
        generators: All generators for the network.

    Returns:
        A tuple of (violations list, check status).
    """
    violations: list[ParameterViolation] = []
    for g in generators:
        if g.pmin_mw > g.pmax_mw:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="pmin_gt_pmax",
                    message=(f"Pmin ({g.pmin_mw:.2f} MW) > Pmax ({g.pmax_mw:.2f} MW)"),
                    value=g.pmin_mw,
                    threshold=g.pmax_mw,
                )
            )
    status = CheckSeverity.FAIL if violations else CheckSeverity.PASS
    return violations, status


def check_cost_non_negative(
    generators: list[GeneratorRecord],
) -> tuple[list[ParameterViolation], CheckSeverity]:
    """Check (f): startup and shutdown costs are non-negative.

    Args:
        generators: All generators for the network.

    Returns:
        A tuple of (violations list, check status).
    """
    violations: list[ParameterViolation] = []
    for g in generators:
        if g.startup_cost_dollar < 0:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="negative_startup_cost",
                    message=f"Negative startup cost: {g.startup_cost_dollar:.2f}",
                    value=g.startup_cost_dollar,
                    threshold=0.0,
                )
            )
        if g.shutdown_cost_dollar < 0:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="negative_shutdown_cost",
                    message=f"Negative shutdown cost: {g.shutdown_cost_dollar:.2f}",
                    value=g.shutdown_cost_dollar,
                    threshold=0.0,
                )
            )
    status = CheckSeverity.FAIL if violations else CheckSeverity.PASS
    return violations, status


def check_min_up_down_times(
    generators: list[GeneratorRecord],
) -> tuple[list[ParameterViolation], CheckSeverity]:
    """Check (g): min up/down times are valid positive integers <= 24.

    For each non-renewable generator, verifies:
    1. min_up_time_hr > 0
    2. min_down_time_hr > 0
    3. min_up_time_hr is an integer value (float with no fractional part)
    4. min_down_time_hr is an integer value
    5. min_up_time_hr <= MAX_MIN_UP_DOWN_HR (24)
    6. min_down_time_hr <= MAX_MIN_UP_DOWN_HR (24)
    7. min_up_time_hr + min_down_time_hr <= MAX_MIN_UP_DOWN_HR (24)

    Renewable generators are skipped.

    Args:
        generators: All generators for the network.

    Returns:
        A tuple of (violations list, check status).
    """
    violations: list[ParameterViolation] = []
    for g in generators:
        if g.is_renewable:
            continue

        # Check min_up_time_hr
        if g.min_up_time_hr <= 0:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_up_time_non_positive",
                    message=f"min_up_time_hr ({g.min_up_time_hr}) is not positive",
                    value=g.min_up_time_hr,
                    threshold=0.0,
                )
            )
        elif not math.isfinite(g.min_up_time_hr) or g.min_up_time_hr != math.floor(
            g.min_up_time_hr
        ):
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_up_time_not_integer",
                    message=f"min_up_time_hr ({g.min_up_time_hr}) is not an integer",
                    value=g.min_up_time_hr,
                    threshold=None,
                )
            )
        elif g.min_up_time_hr > MAX_MIN_UP_DOWN_HR:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_up_time_exceeds_horizon",
                    message=(
                        f"min_up_time_hr ({g.min_up_time_hr}) exceeds {MAX_MIN_UP_DOWN_HR}h horizon"
                    ),
                    value=g.min_up_time_hr,
                    threshold=float(MAX_MIN_UP_DOWN_HR),
                )
            )

        # Check min_down_time_hr
        if g.min_down_time_hr <= 0:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_down_time_non_positive",
                    message=f"min_down_time_hr ({g.min_down_time_hr}) is not positive",
                    value=g.min_down_time_hr,
                    threshold=0.0,
                )
            )
        elif not math.isfinite(g.min_down_time_hr) or g.min_down_time_hr != math.floor(
            g.min_down_time_hr
        ):
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_down_time_not_integer",
                    message=f"min_down_time_hr ({g.min_down_time_hr}) is not an integer",
                    value=g.min_down_time_hr,
                    threshold=None,
                )
            )
        elif g.min_down_time_hr > MAX_MIN_UP_DOWN_HR:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_down_time_exceeds_horizon",
                    message=(
                        f"min_down_time_hr ({g.min_down_time_hr}) "
                        f"exceeds {MAX_MIN_UP_DOWN_HR}h horizon"
                    ),
                    value=g.min_down_time_hr,
                    threshold=float(MAX_MIN_UP_DOWN_HR),
                )
            )

        # Check combined constraint
        total = g.min_up_time_hr + g.min_down_time_hr
        if g.min_up_time_hr > 0 and g.min_down_time_hr > 0 and total > MAX_MIN_UP_DOWN_HR:
            violations.append(
                ParameterViolation(
                    gen_uid=g.gen_uid,
                    check_name="min_up_down_sum_exceeds_horizon",
                    message=(
                        f"min_up_time_hr ({g.min_up_time_hr}) + "
                        f"min_down_time_hr ({g.min_down_time_hr}) = "
                        f"{total} exceeds {MAX_MIN_UP_DOWN_HR}h horizon"
                    ),
                    value=total,
                    threshold=float(MAX_MIN_UP_DOWN_HR),
                )
            )

    status = CheckSeverity.FAIL if violations else CheckSeverity.PASS
    return violations, status


def check_parameter_validity(
    generators: list[GeneratorRecord],
) -> ParameterValidityResult:
    """Run all per-generator parameter checks (e, f, g).

    Orchestrates check_pmin_pmax_consistency, check_cost_non_negative,
    and check_min_up_down_times.

    Args:
        generators: All generators for the network.

    Returns:
        A ParameterValidityResult with per-check violations and status.
    """
    pmin_pmax_violations, pmin_pmax_status = check_pmin_pmax_consistency(generators)
    cost_violations, cost_status = check_cost_non_negative(generators)
    time_violations, time_status = check_min_up_down_times(generators)

    total_violations = len(pmin_pmax_violations) + len(cost_violations) + len(time_violations)

    return ParameterValidityResult(
        pmin_pmax_violations=pmin_pmax_violations,
        cost_violations=cost_violations,
        time_violations=time_violations,
        total_generators_checked=len(generators),
        total_violations=total_violations,
        pmin_pmax_status=pmin_pmax_status,
        cost_status=cost_status,
        time_status=time_status,
    )


# ---------------------------------------------------------------------------
# Network-level orchestration
# ---------------------------------------------------------------------------


def _count_check_statuses(
    *statuses: CheckSeverity,
) -> tuple[int, int, int]:
    """Count PASS, WARN, FAIL occurrences in a list of statuses."""
    passed = sum(1 for s in statuses if s == CheckSeverity.PASS)
    warned = sum(1 for s in statuses if s == CheckSeverity.WARN)
    failed = sum(1 for s in statuses if s == CheckSeverity.FAIL)
    return passed, warned, failed


def validate_network(
    network_id: str,
    timeseries_dir: Path,
) -> FeasibilityResult:
    """Run all SCUC feasibility checks for a single network.

    Args:
        network_id: Network identifier ("case39", "ACTIVSg2000",
            or "ACTIVSg10k").
        timeseries_dir: Base timeseries directory (data/timeseries/).

    Returns:
        A FeasibilityResult for the network.
    """
    network_dir = timeseries_dir / network_id

    try:
        generators = load_generators(network_dir, network_id)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load generators for %s: %s", network_id, exc)
        # Return a result with all checks failed
        empty_capacity = HourlyCapacityResult(
            pmin_load_ratios=[],
            tightest_hour=0,
            tightest_ratio=0.0,
            sum_pmin_mw=0.0,
            pmin_check_status=CheckSeverity.FAIL,
            pmin_check_message=f"File not found: {exc}",
            pmax_total_mw=0.0,
            peak_load_mw=0.0,
            pmax_margin=0.0,
            pmax_check_status=CheckSeverity.FAIL,
            pmax_check_message=f"File not found: {exc}",
        )
        empty_ramp = RampAdequacyResult(
            fleet_ramp_up_mw_per_hr=0.0,
            max_load_increase_mw=0.0,
            ramp_up_hour=0,
            ramp_up_margin=0.0,
            ramp_up_status=CheckSeverity.FAIL,
            ramp_up_message=f"File not found: {exc}",
            fleet_ramp_down_mw_per_hr=0.0,
            max_load_decrease_mw=0.0,
            ramp_down_hour=0,
            ramp_down_margin=0.0,
            ramp_down_status=CheckSeverity.FAIL,
            ramp_down_message=f"File not found: {exc}",
        )
        empty_params = ParameterValidityResult(
            pmin_pmax_violations=[],
            cost_violations=[],
            time_violations=[],
            total_generators_checked=0,
            total_violations=0,
            pmin_pmax_status=CheckSeverity.FAIL,
            cost_status=CheckSeverity.FAIL,
            time_status=CheckSeverity.FAIL,
        )
        return FeasibilityResult(
            network_id=network_id,
            hourly_capacity=empty_capacity,
            ramp_adequacy=empty_ramp,
            parameter_validity=empty_params,
            total_checks=7,
            checks_passed=0,
            checks_warned=0,
            checks_failed=7,
            overall_pass=False,
            load_profile_mw=[],
        )

    try:
        load_profile = load_load_profile(network_dir)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load load profile for %s: %s", network_id, exc)
        # Can still run parameter checks
        load_profile = []

    # Run checks
    if load_profile:
        hourly_capacity = check_pmin_headroom(generators, load_profile)
        ramp_adequacy = check_ramp_adequacy(generators, load_profile)
    else:
        hourly_capacity = HourlyCapacityResult(
            pmin_load_ratios=[],
            tightest_hour=0,
            tightest_ratio=0.0,
            sum_pmin_mw=0.0,
            pmin_check_status=CheckSeverity.FAIL,
            pmin_check_message="Load profile not available",
            pmax_total_mw=0.0,
            peak_load_mw=0.0,
            pmax_margin=0.0,
            pmax_check_status=CheckSeverity.FAIL,
            pmax_check_message="Load profile not available",
        )
        ramp_adequacy = RampAdequacyResult(
            fleet_ramp_up_mw_per_hr=0.0,
            max_load_increase_mw=0.0,
            ramp_up_hour=0,
            ramp_up_margin=0.0,
            ramp_up_status=CheckSeverity.FAIL,
            ramp_up_message="Load profile not available",
            fleet_ramp_down_mw_per_hr=0.0,
            max_load_decrease_mw=0.0,
            ramp_down_hour=0,
            ramp_down_margin=0.0,
            ramp_down_status=CheckSeverity.FAIL,
            ramp_down_message="Load profile not available",
        )

    parameter_validity = check_parameter_validity(generators)

    # Aggregate status counts across all 7 check categories
    all_statuses = [
        hourly_capacity.pmin_check_status,  # (a)
        hourly_capacity.pmax_check_status,  # (b)
        ramp_adequacy.ramp_up_status,  # (c)
        ramp_adequacy.ramp_down_status,  # (d)
        parameter_validity.pmin_pmax_status,  # (e)
        parameter_validity.cost_status,  # (f)
        parameter_validity.time_status,  # (g)
    ]

    passed, warned, failed = _count_check_statuses(*all_statuses)

    return FeasibilityResult(
        network_id=network_id,
        hourly_capacity=hourly_capacity,
        ramp_adequacy=ramp_adequacy,
        parameter_validity=parameter_validity,
        total_checks=len(all_statuses),
        checks_passed=passed,
        checks_warned=warned,
        checks_failed=failed,
        overall_pass=failed == 0,
        load_profile_mw=load_profile,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_feasibility_report(
    network_results: list[FeasibilityResult],
) -> FeasibilityReport:
    """Aggregate per-network results into a consolidated report.

    Args:
        network_results: Feasibility results for all networks.

    Returns:
        A FeasibilityReport with aggregated statistics.
    """
    total_checks = sum(r.total_checks for r in network_results)
    total_passed = sum(r.checks_passed for r in network_results)
    total_warned = sum(r.checks_warned for r in network_results)
    total_failed = sum(r.checks_failed for r in network_results)
    overall_pass = all(r.overall_pass for r in network_results)

    return FeasibilityReport(
        network_results=network_results,
        total_checks=total_checks,
        total_passed=total_passed,
        total_warned=total_warned,
        total_failed=total_failed,
        overall_pass=overall_pass,
        script_version=__version__,
    )


def _violations_to_dicts(
    violations: list[ParameterViolation],
) -> list[dict[str, object]]:
    """Convert violations to JSON-serializable dicts, capped at MAX_VIOLATIONS_REPORTED."""
    capped = violations[:MAX_VIOLATIONS_REPORTED]
    return [
        {
            "gen_uid": v.gen_uid,
            "check_name": v.check_name,
            "message": v.message,
            "value": v.value,
        }
        for v in capped
    ]


def write_feasibility_json(
    report: FeasibilityReport,
    dest_path: Path,
) -> None:
    """Write the feasibility report to JSON for CI consumption.

    Args:
        report: The complete feasibility report.
        dest_path: File path for the output JSON.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    networks_dict: dict[str, object] = {}
    for nr in report.network_results:
        all_violations = (
            nr.parameter_validity.pmin_pmax_violations
            + nr.parameter_validity.cost_violations
            + nr.parameter_validity.time_violations
        )
        networks_dict[nr.network_id] = {
            "overall_pass": nr.overall_pass,
            "hourly_capacity": {
                "pmin_load_ratios": nr.hourly_capacity.pmin_load_ratios,
                "tightest_hour": nr.hourly_capacity.tightest_hour,
                "tightest_ratio": nr.hourly_capacity.tightest_ratio,
                "sum_pmin_mw": nr.hourly_capacity.sum_pmin_mw,
                "pmin_check_status": nr.hourly_capacity.pmin_check_status.value,
                "pmax_total_mw": nr.hourly_capacity.pmax_total_mw,
                "peak_load_mw": nr.hourly_capacity.peak_load_mw,
                "pmax_margin": nr.hourly_capacity.pmax_margin,
                "pmax_check_status": nr.hourly_capacity.pmax_check_status.value,
            },
            "ramp_adequacy": {
                "fleet_ramp_up_mw_per_hr": nr.ramp_adequacy.fleet_ramp_up_mw_per_hr,
                "max_load_increase_mw": nr.ramp_adequacy.max_load_increase_mw,
                "ramp_up_margin": nr.ramp_adequacy.ramp_up_margin,
                "ramp_up_status": nr.ramp_adequacy.ramp_up_status.value,
                "fleet_ramp_down_mw_per_hr": nr.ramp_adequacy.fleet_ramp_down_mw_per_hr,
                "max_load_decrease_mw": nr.ramp_adequacy.max_load_decrease_mw,
                "ramp_down_margin": nr.ramp_adequacy.ramp_down_margin,
                "ramp_down_status": nr.ramp_adequacy.ramp_down_status.value,
            },
            "parameter_validity": {
                "total_generators_checked": nr.parameter_validity.total_generators_checked,
                "total_violations": nr.parameter_validity.total_violations,
                "pmin_pmax_status": nr.parameter_validity.pmin_pmax_status.value,
                "cost_status": nr.parameter_validity.cost_status.value,
                "time_status": nr.parameter_validity.time_status.value,
                "violations": _violations_to_dicts(all_violations),
            },
            "load_profile_mw": nr.load_profile_mw,
        }

    data = {
        "overall_pass": report.overall_pass,
        "total_checks": report.total_checks,
        "total_passed": report.total_passed,
        "total_warned": report.total_warned,
        "total_failed": report.total_failed,
        "networks": networks_dict,
        "script_version": report.script_version,
    }

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
) -> FeasibilityReport:
    """Entry point: run SCUC feasibility screening for all networks.

    Args:
        timeseries_base_dir: Base directory for input data. Defaults
            to <repo_root>/data/timeseries/.

    Returns:
        A FeasibilityReport with results for all networks.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_root / "timeseries"

    network_results: list[FeasibilityResult] = []
    for network_id in NETWORK_IDS:
        result = validate_network(network_id, timeseries_base_dir)
        network_results.append(result)

    report = build_feasibility_report(network_results)

    # Write JSON
    json_path = repo_root / "validation" / "scuc_feasibility_results.json"
    write_feasibility_json(report, json_path)

    # Print summary
    print("=" * 72)
    print("SCUC Feasibility Screening Summary")
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
        status_str = "ALL PASSED" if nr.overall_pass else "HAS FAILURES"
        print(f"  {nr.network_id}: {status_str}")
        print(
            f"    Checks: {nr.total_checks}, "
            f"PASS: {nr.checks_passed}, WARN: {nr.checks_warned}, "
            f"FAIL: {nr.checks_failed}"
        )
        if nr.hourly_capacity.pmin_load_ratios:
            print(
                f"    Tightest Pmin hour: {nr.hourly_capacity.tightest_hour} "
                f"(ratio: {nr.hourly_capacity.tightest_ratio:.4f})"
            )
            print(f"    Pmax margin: {nr.hourly_capacity.pmax_margin:.4f}")
        if nr.parameter_validity.total_violations > 0:
            print(f"    Parameter violations: {nr.parameter_validity.total_violations}")

    print()

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
