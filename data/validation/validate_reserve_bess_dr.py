"""Reserve, BESS & DR Plausibility Checks (PRD 05/04).

Implements physical plausibility checks for reserve adequacy, BESS parameter
consistency, and demand response feasibility across all three test networks
(TINY case39, SMALL ACTIVSg2000, MEDIUM ACTIVSg10k).

These checks complement PRD-03's SCUC feasibility screens by validating the
ancillary service and flexible resource layers of the dataset.

All validation logic uses only Python stdlib modules.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_HOURS: int = 24
"""The 24-hour planning horizon."""

RESERVE_MAX_LOAD_FRACTION: float = 0.15
"""Maximum sane reserve requirement as a fraction of system load."""

BESS_MIN_DURATION_HR: float = 1.0
"""Minimum BESS duration (energy_mwh / power_mw) in hours."""

BESS_RTE_MIN: float = 0.70
"""Minimum physically plausible round-trip efficiency."""

BESS_RTE_MAX: float = 0.99
"""Maximum physically plausible round-trip efficiency."""

HR_COLUMNS: list[str] = [f"HR_{h}" for h in range(1, 25)]
"""The 24 hour-ending column names HR_1 through HR_24."""

NETWORK_DIRS: dict[str, str] = {
    "TINY": "case39",
    "SMALL": "ACTIVSg2000",
    "MEDIUM": "ACTIVSg10k",
}
"""Mapping from tier label to network directory name."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ValidationNetworkId(StrEnum):
    """Network identifiers for Phase 5 validation."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class CheckSeverity(StrEnum):
    """Outcome severity for a single validation check."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class CheckResult:
    """Result of a single validation check.

    Attributes:
        check_id: Unique identifier for the check.
        network_id: Network this check was run against.
        passed: Whether the check passed.
        severity: Severity level of the check.
        message: Human-readable summary.
        details: Diagnostic data (failing hours, units, margin values, etc.).
    """

    check_id: str
    network_id: ValidationNetworkId
    passed: bool
    severity: CheckSeverity
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReserveAdequacyDetails:
    """Diagnostic details for reserve adequacy checks.

    Attributes:
        product: Reserve product name (spinning / non_spinning).
        requirement_mw_per_hour: 24-element list of hourly requirements.
        eligible_capacity_mw: Total eligible capacity across the fleet.
        margin_mw_per_hour: 24-element list of capacity minus requirement.
        tightest_hour: Hour index (0-based) with smallest margin.
        tightest_margin_mw: Margin at the tightest hour.
        all_hours_adequate: Whether all hours have non-negative margin.
    """

    product: str
    requirement_mw_per_hour: list[float]
    eligible_capacity_mw: float
    margin_mw_per_hour: list[float]
    tightest_hour: int
    tightest_margin_mw: float
    all_hours_adequate: bool


@dataclass(frozen=True)
class ReserveSanityDetails:
    """Diagnostic details for reserve requirement sanity bounds.

    Attributes:
        product: Reserve product name.
        requirement_mw_per_hour: 24-element list of hourly requirements.
        load_mw_per_hour: 24-element list of hourly system load.
        ratio_per_hour: 24-element list of requirement/load ratios.
        max_ratio: Maximum ratio across all hours.
        max_ratio_hour: Hour index (0-based) of the maximum ratio.
        all_positive: Whether all requirements are positive.
        within_bound: Whether all ratios are within RESERVE_MAX_LOAD_FRACTION.
    """

    product: str
    requirement_mw_per_hour: list[float]
    load_mw_per_hour: list[float]
    ratio_per_hour: list[float]
    max_ratio: float
    max_ratio_hour: int
    all_positive: bool
    within_bound: bool


@dataclass(frozen=True)
class BessCheckDetails:
    """Diagnostic details for BESS parameter checks.

    Attributes:
        check_name: Name of the BESS sub-check.
        total_units: Total number of BESS units evaluated.
        failing_units: List of unit_id values that failed.
        failing_values: Map of unit_id to the failing parameter value(s).
    """

    check_name: str
    total_units: int
    failing_units: list[str]
    failing_values: dict[str, object]


@dataclass(frozen=True)
class DrCheckDetails:
    """Diagnostic details for DR checks.

    Attributes:
        check_name: Name of the DR sub-check.
        total_resources: Total number of DR resources evaluated.
        failing_resources: List of DR resource identifiers that failed.
        failing_values: Map of resource id to the failing parameter value(s).
    """

    check_name: str
    total_resources: int
    failing_resources: list[str]
    failing_values: dict[str, object]


@dataclass(frozen=True)
class HourlyBusLoad:
    """Per-bus hourly load profile.

    Attributes:
        bus_id: Bus identifier.
        load_mw: 24-element list of hourly load in MW.
    """

    bus_id: int
    load_mw: list[float]


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return rows as list of dicts."""
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def load_reserve_requirements(network_dir: Path) -> dict[str, list[float]]:
    """Load hourly reserve requirements from reserve_requirements_24h.csv.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        A dict mapping product name (e.g. "spinning", "non_spinning") to
        a 24-element list of hourly requirements in MW.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    csv_path = network_dir / "reserve_requirements_24h.csv"
    if not csv_path.exists():
        msg = f"reserve_requirements_24h.csv not found: {csv_path}"
        raise FileNotFoundError(msg)

    rows = _read_csv(csv_path)
    result: dict[str, list[float]] = {}
    for row in rows:
        product = row["product"].strip().lower()
        hourly = [float(row[col]) for col in HR_COLUMNS]
        result[product] = hourly
    return result


def load_reserve_eligibility(
    network_dir: Path,
) -> list[dict[str, str]]:
    """Load reserve eligibility data from reserve_eligibility.csv.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        A list of row dicts from the CSV, one per eligible unit.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    csv_path = network_dir / "reserve_eligibility.csv"
    if not csv_path.exists():
        msg = f"reserve_eligibility.csv not found: {csv_path}"
        raise FileNotFoundError(msg)
    return _read_csv(csv_path)


def load_system_load(network_dir: Path) -> list[float]:
    """Load the 24-hour system load profile from load_24h.csv.

    Sums across all buses for each hour to produce a 24-element list
    of total system load in MW.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        A 24-element list of total system load per hour in MW.

    Raises:
        FileNotFoundError: If load_24h.csv does not exist.
    """
    csv_path = network_dir / "load_24h.csv"
    if not csv_path.exists():
        msg = f"load_24h.csv not found: {csv_path}"
        raise FileNotFoundError(msg)

    rows = _read_csv(csv_path)
    load_profile: list[float] = []
    for col in HR_COLUMNS:
        total = sum(float(row[col]) for row in rows)
        load_profile.append(total)
    return load_profile


def load_bus_hourly_loads(network_dir: Path) -> list[HourlyBusLoad]:
    """Load per-bus hourly load profiles from load_24h.csv.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        A list of HourlyBusLoad, one per bus in the load CSV.

    Raises:
        FileNotFoundError: If load_24h.csv does not exist.
    """
    csv_path = network_dir / "load_24h.csv"
    if not csv_path.exists():
        msg = f"load_24h.csv not found: {csv_path}"
        raise FileNotFoundError(msg)

    rows = _read_csv(csv_path)
    result: list[HourlyBusLoad] = []
    for row in rows:
        # Bus column may be "bus_id" or "bus"
        bus_key = "bus_id" if "bus_id" in row else "bus"
        bus_id = int(row[bus_key])
        load_mw = [float(row[col]) for col in HR_COLUMNS]
        result.append(HourlyBusLoad(bus_id=bus_id, load_mw=load_mw))
    return result


def load_bess_units(network_dir: Path) -> list[dict[str, str]]:
    """Load BESS unit definitions from bess_units.csv.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        A list of row dicts from the CSV, one per BESS unit.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    csv_path = network_dir / "bess_units.csv"
    if not csv_path.exists():
        msg = f"bess_units.csv not found: {csv_path}"
        raise FileNotFoundError(msg)
    return _read_csv(csv_path)


def load_dr_buses(network_dir: Path) -> list[dict[str, str]]:
    """Load demand response bus definitions from dr_buses.csv.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        A list of row dicts from the CSV, one per DR bus.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    csv_path = network_dir / "dr_buses.csv"
    if not csv_path.exists():
        msg = f"dr_buses.csv not found: {csv_path}"
        raise FileNotFoundError(msg)
    return _read_csv(csv_path)


# ---------------------------------------------------------------------------
# Reserve checks
# ---------------------------------------------------------------------------


def check_reserve_spinning_adequacy(
    reserve_requirements: dict[str, list[float]],
    reserve_eligibility: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check that spinning-eligible capacity exceeds spinning requirement each hour.

    For each of the 24 hours, verifies that the total spinning-eligible capacity
    (sum of max_spinning_mw across all units flagged spinning_eligible=true)
    exceeds the spinning reserve requirement for that hour.

    Args:
        reserve_requirements: Dict mapping product to 24 hourly requirements.
        reserve_eligibility: List of eligibility row dicts from CSV.
        network_id: Network being checked.

    Returns:
        A CheckResult with ReserveAdequacyDetails in the details dict.
    """
    spinning_req = reserve_requirements.get("spinning", [0.0] * NUM_HOURS)

    # Sum eligible capacity
    eligible_capacity = 0.0
    for row in reserve_eligibility:
        eligible_str = row.get("spinning_eligible", "false").strip().lower()
        if eligible_str in ("true", "1"):
            mw_str = row.get("max_spinning_mw", "0").strip()
            eligible_capacity += float(mw_str) if mw_str else 0.0

    margins = [eligible_capacity - spinning_req[h] for h in range(NUM_HOURS)]
    tightest_hour = 0
    tightest_margin = margins[0]
    for h in range(1, NUM_HOURS):
        if margins[h] < tightest_margin:
            tightest_margin = margins[h]
            tightest_hour = h

    all_adequate = all(m >= 0.0 for m in margins)

    details_obj = ReserveAdequacyDetails(
        product="spinning",
        requirement_mw_per_hour=spinning_req,
        eligible_capacity_mw=eligible_capacity,
        margin_mw_per_hour=margins,
        tightest_hour=tightest_hour,
        tightest_margin_mw=tightest_margin,
        all_hours_adequate=all_adequate,
    )

    if all_adequate:
        msg = (
            f"Spinning reserve adequate: tightest hour {tightest_hour} "
            f"margin {tightest_margin:.1f} MW"
        )
    else:
        failing = [h for h in range(NUM_HOURS) if margins[h] < 0]
        msg = (
            f"Spinning reserve inadequate: {len(failing)} hours fail, "
            f"worst hour {tightest_hour} deficit {tightest_margin:.1f} MW"
        )

    return CheckResult(
        check_id="reserve_spinning_adequacy",
        network_id=network_id,
        passed=all_adequate,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "product": details_obj.product,
            "eligible_capacity_mw": details_obj.eligible_capacity_mw,
            "tightest_hour": details_obj.tightest_hour,
            "tightest_margin_mw": details_obj.tightest_margin_mw,
            "all_hours_adequate": details_obj.all_hours_adequate,
            "margin_mw_per_hour": details_obj.margin_mw_per_hour,
        },
    )


def check_reserve_non_spinning_adequacy(
    reserve_requirements: dict[str, list[float]],
    reserve_eligibility: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check that non-spinning-eligible capacity exceeds requirement each hour.

    Same structure as spinning adequacy, using non_spinning_eligible and
    max_non_spinning_mw fields.

    Args:
        reserve_requirements: Dict mapping product to 24 hourly requirements.
        reserve_eligibility: List of eligibility row dicts from CSV.
        network_id: Network being checked.

    Returns:
        A CheckResult with ReserveAdequacyDetails in the details dict.
    """
    ns_req = reserve_requirements.get("non_spinning", [0.0] * NUM_HOURS)

    eligible_capacity = 0.0
    for row in reserve_eligibility:
        eligible_str = row.get("non_spinning_eligible", "false").strip().lower()
        if eligible_str in ("true", "1"):
            mw_str = row.get("max_non_spinning_mw", "0").strip()
            eligible_capacity += float(mw_str) if mw_str else 0.0

    margins = [eligible_capacity - ns_req[h] for h in range(NUM_HOURS)]
    tightest_hour = 0
    tightest_margin = margins[0]
    for h in range(1, NUM_HOURS):
        if margins[h] < tightest_margin:
            tightest_margin = margins[h]
            tightest_hour = h

    all_adequate = all(m >= 0.0 for m in margins)

    details_obj = ReserveAdequacyDetails(
        product="non_spinning",
        requirement_mw_per_hour=ns_req,
        eligible_capacity_mw=eligible_capacity,
        margin_mw_per_hour=margins,
        tightest_hour=tightest_hour,
        tightest_margin_mw=tightest_margin,
        all_hours_adequate=all_adequate,
    )

    if all_adequate:
        msg = (
            f"Non-spinning reserve adequate: tightest hour {tightest_hour} "
            f"margin {tightest_margin:.1f} MW"
        )
    else:
        failing = [h for h in range(NUM_HOURS) if margins[h] < 0]
        msg = (
            f"Non-spinning reserve inadequate: {len(failing)} hours fail, "
            f"worst hour {tightest_hour} deficit {tightest_margin:.1f} MW"
        )

    return CheckResult(
        check_id="reserve_non_spinning_adequacy",
        network_id=network_id,
        passed=all_adequate,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "product": details_obj.product,
            "eligible_capacity_mw": details_obj.eligible_capacity_mw,
            "tightest_hour": details_obj.tightest_hour,
            "tightest_margin_mw": details_obj.tightest_margin_mw,
            "all_hours_adequate": details_obj.all_hours_adequate,
            "margin_mw_per_hour": details_obj.margin_mw_per_hour,
        },
    )


def check_reserve_requirements_sanity(
    reserve_requirements: dict[str, list[float]],
    system_load: list[float],
    network_id: ValidationNetworkId,
) -> list[CheckResult]:
    """Check that reserve requirements are positive and within sane bounds.

    For each reserve product, verifies:
    1. All hourly requirements are positive (> 0 MW).
    2. No hourly requirement exceeds RESERVE_MAX_LOAD_FRACTION (15%) of
       the corresponding hour's system load.

    Args:
        reserve_requirements: Dict mapping product to 24 hourly requirements.
        system_load: 24-element list of total system load per hour.
        network_id: Network being checked.

    Returns:
        A list of CheckResult, one per reserve product.
    """
    results: list[CheckResult] = []

    for product, req_mw in reserve_requirements.items():
        ratios = [
            req_mw[h] / system_load[h] if system_load[h] > 0 else 0.0 for h in range(NUM_HOURS)
        ]
        all_positive = all(r > 0.0 for r in req_mw)
        within_bound = all(r <= RESERVE_MAX_LOAD_FRACTION for r in ratios)

        max_ratio = max(ratios) if ratios else 0.0
        max_ratio_hour = ratios.index(max_ratio) if ratios else 0

        details_obj = ReserveSanityDetails(
            product=product,
            requirement_mw_per_hour=req_mw,
            load_mw_per_hour=system_load,
            ratio_per_hour=ratios,
            max_ratio=max_ratio,
            max_ratio_hour=max_ratio_hour,
            all_positive=all_positive,
            within_bound=within_bound,
        )

        passed = all_positive and within_bound
        parts: list[str] = []
        if not all_positive:
            parts.append("non-positive requirements found")
        if not within_bound:
            parts.append(
                f"max ratio {max_ratio:.2%} at hour {max_ratio_hour} "
                f"exceeds {RESERVE_MAX_LOAD_FRACTION:.0%}"
            )
        if passed:
            msg = (
                f"Reserve sanity OK for {product}: "
                f"max ratio {max_ratio:.2%} at hour {max_ratio_hour}"
            )
        else:
            msg = f"Reserve sanity FAIL for {product}: {'; '.join(parts)}"

        results.append(
            CheckResult(
                check_id=f"reserve_sanity_{product}",
                network_id=network_id,
                passed=passed,
                severity=CheckSeverity.ERROR,
                message=msg,
                details={
                    "product": details_obj.product,
                    "max_ratio": details_obj.max_ratio,
                    "max_ratio_hour": details_obj.max_ratio_hour,
                    "all_positive": details_obj.all_positive,
                    "within_bound": details_obj.within_bound,
                },
            )
        )

    return results


# ---------------------------------------------------------------------------
# BESS checks
# ---------------------------------------------------------------------------


def check_bess_positivity(
    bess_rows: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check BESS parameter positivity and minimum duration.

    For every BESS unit, verifies:
    - power_mw > 0
    - energy_mwh > 0
    - energy_mwh >= power_mw * BESS_MIN_DURATION_HR (at least 1-hour duration)

    Args:
        bess_rows: List of row dicts from bess_units.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with BessCheckDetails in the details dict.
    """
    failing_units: list[str] = []
    failing_values: dict[str, object] = {}

    for row in bess_rows:
        unit_id = row["unit_id"].strip()
        power_mw = float(row["power_mw"])
        energy_mwh = float(row["energy_mwh"])

        issues: list[str] = []
        if power_mw <= 0:
            issues.append(f"power_mw={power_mw}")
        if energy_mwh <= 0:
            issues.append(f"energy_mwh={energy_mwh}")
        if power_mw > 0 and energy_mwh < power_mw * BESS_MIN_DURATION_HR:
            duration = energy_mwh / power_mw if power_mw > 0 else 0.0
            issues.append(f"duration={duration:.2f}hr < {BESS_MIN_DURATION_HR}hr")

        if issues:
            failing_units.append(unit_id)
            failing_values[unit_id] = issues

    details_obj = BessCheckDetails(
        check_name="bess_positivity",
        total_units=len(bess_rows),
        failing_units=failing_units,
        failing_values=failing_values,
    )

    passed = len(failing_units) == 0
    if passed:
        msg = f"All {len(bess_rows)} BESS units pass positivity checks"
    else:
        msg = (
            f"{len(failing_units)}/{len(bess_rows)} BESS units fail "
            f"positivity checks: {', '.join(failing_units)}"
        )

    return CheckResult(
        check_id="bess_positivity",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": details_obj.check_name,
            "total_units": details_obj.total_units,
            "failing_units": details_obj.failing_units,
            "failing_values": details_obj.failing_values,
        },
    )


def check_bess_efficiency(
    bess_rows: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check BESS round-trip efficiency is within physical bounds.

    For every BESS unit, verifies that the round-trip efficiency is
    in [BESS_RTE_MIN, BESS_RTE_MAX] (i.e. [0.70, 0.99]).

    Args:
        bess_rows: List of row dicts from bess_units.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with BessCheckDetails in the details dict.
    """
    failing_units: list[str] = []
    failing_values: dict[str, object] = {}

    for row in bess_rows:
        unit_id = row["unit_id"].strip()
        rte = float(row["roundtrip_eff"])

        if rte < BESS_RTE_MIN or rte > BESS_RTE_MAX:
            failing_units.append(unit_id)
            failing_values[unit_id] = {
                "roundtrip_eff": rte,
                "bounds": [BESS_RTE_MIN, BESS_RTE_MAX],
            }

    details_obj = BessCheckDetails(
        check_name="bess_efficiency",
        total_units=len(bess_rows),
        failing_units=failing_units,
        failing_values=failing_values,
    )

    passed = len(failing_units) == 0
    if passed:
        msg = f"All {len(bess_rows)} BESS units have valid efficiency"
    else:
        msg = (
            f"{len(failing_units)}/{len(bess_rows)} BESS units have "
            f"out-of-range efficiency: {', '.join(failing_units)}"
        )

    return CheckResult(
        check_id="bess_efficiency",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": details_obj.check_name,
            "total_units": details_obj.total_units,
            "failing_units": details_obj.failing_units,
            "failing_values": details_obj.failing_values,
        },
    )


def check_bess_soc_ordering(
    bess_rows: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check BESS SoC parameter ordering.

    For every BESS unit, verifies:
    - min_soc_pct < max_soc_pct
    - min_soc_pct <= initial_soc_pct <= max_soc_pct

    Args:
        bess_rows: List of row dicts from bess_units.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with BessCheckDetails in the details dict.
    """
    failing_units: list[str] = []
    failing_values: dict[str, object] = {}

    for row in bess_rows:
        unit_id = row["unit_id"].strip()
        min_soc = float(row["min_soc_pct"])
        max_soc = float(row["max_soc_pct"])
        init_soc = float(row["initial_soc_pct"])

        issues: list[str] = []
        if min_soc >= max_soc:
            issues.append(f"min_soc_pct={min_soc} >= max_soc_pct={max_soc}")
        if init_soc < min_soc or init_soc > max_soc:
            issues.append(f"initial_soc_pct={init_soc} outside [{min_soc}, {max_soc}]")

        if issues:
            failing_units.append(unit_id)
            failing_values[unit_id] = issues

    details_obj = BessCheckDetails(
        check_name="bess_soc_ordering",
        total_units=len(bess_rows),
        failing_units=failing_units,
        failing_values=failing_values,
    )

    passed = len(failing_units) == 0
    if passed:
        msg = f"All {len(bess_rows)} BESS units pass SoC ordering checks"
    else:
        msg = (
            f"{len(failing_units)}/{len(bess_rows)} BESS units fail "
            f"SoC ordering: {', '.join(failing_units)}"
        )

    return CheckResult(
        check_id="bess_soc_ordering",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": details_obj.check_name,
            "total_units": details_obj.total_units,
            "failing_units": details_obj.failing_units,
            "failing_values": details_obj.failing_values,
        },
    )


def check_bess_cyclic_soc_feasibility(
    bess_rows: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check cyclic SoC feasibility for BESS units with cyclic_soc=true.

    For every BESS unit with cyclic_soc=true, verifies that the unit can
    return to its initial SoC within the 24-hour horizon. The feasibility
    condition is that the initial SoC is within the usable SoC band
    [min_soc_pct, max_soc_pct], which is already checked by the SoC
    ordering check. Additionally verifies that the usable SoC band is
    non-degenerate (has positive width) so that cycling is possible.

    Args:
        bess_rows: List of row dicts from bess_units.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with BessCheckDetails in the details dict.
    """
    failing_units: list[str] = []
    failing_values: dict[str, object] = {}

    for row in bess_rows:
        unit_id = row["unit_id"].strip()
        cyclic_str = row.get("cyclic_soc", "true").strip().lower()
        if cyclic_str not in ("true", "1"):
            continue

        power_mw = float(row["power_mw"])
        energy_mwh = float(row["energy_mwh"])
        min_soc = float(row["min_soc_pct"])
        max_soc = float(row["max_soc_pct"])
        init_soc = float(row["initial_soc_pct"])
        rte = float(row["roundtrip_eff"])

        issues: list[str] = []

        # Check init_soc within usable band
        if init_soc < min_soc or init_soc > max_soc:
            issues.append(f"initial_soc_pct={init_soc} outside [{min_soc}, {max_soc}]")

        # Check usable band is non-degenerate
        if min_soc >= max_soc:
            issues.append(f"degenerate SoC band: min_soc_pct={min_soc} >= max_soc_pct={max_soc}")

        # Check that efficiency allows cycling (rte > 0)
        if rte <= 0:
            issues.append(f"roundtrip_eff={rte} <= 0, cycling impossible")

        if issues:
            failing_units.append(unit_id)
            failing_values[unit_id] = {
                "issues": issues,
                "power_mw": power_mw,
                "energy_mwh": energy_mwh,
                "min_soc_pct": min_soc,
                "max_soc_pct": max_soc,
                "initial_soc_pct": init_soc,
                "roundtrip_eff": rte,
            }

    details_obj = BessCheckDetails(
        check_name="bess_cyclic_soc_feasibility",
        total_units=len(bess_rows),
        failing_units=failing_units,
        failing_values=failing_values,
    )

    cyclic_count = sum(
        1 for r in bess_rows if r.get("cyclic_soc", "true").strip().lower() in ("true", "1")
    )
    passed = len(failing_units) == 0
    if passed:
        msg = f"All {cyclic_count} cyclic BESS units pass feasibility check"
    else:
        msg = (
            f"{len(failing_units)}/{cyclic_count} cyclic BESS units "
            f"fail feasibility: {', '.join(failing_units)}"
        )

    return CheckResult(
        check_id="bess_cyclic_soc_feasibility",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": details_obj.check_name,
            "total_units": details_obj.total_units,
            "failing_units": details_obj.failing_units,
            "failing_values": details_obj.failing_values,
        },
    )


# ---------------------------------------------------------------------------
# DR checks
# ---------------------------------------------------------------------------


def check_dr_positivity(
    dr_rows: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check DR power parameter positivity.

    For every DR bus, verifies max_curtail_mw > 0 and max_recover_mw > 0.

    Args:
        dr_rows: List of row dicts from dr_buses.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with DrCheckDetails in the details dict.
    """
    failing_resources: list[str] = []
    failing_values: dict[str, object] = {}

    for row in dr_rows:
        # DR id may be "dr_id" or "bus_id" or "bus"
        dr_id = row.get("dr_id", row.get("bus_id", row.get("bus", "unknown")))
        dr_id = str(dr_id).strip()

        curtail = float(row["max_curtail_mw"])
        recover = float(row["max_recover_mw"])

        issues: list[str] = []
        if curtail <= 0:
            issues.append(f"max_curtail_mw={curtail}")
        if recover <= 0:
            issues.append(f"max_recover_mw={recover}")

        if issues:
            failing_resources.append(dr_id)
            failing_values[dr_id] = issues

    details_obj = DrCheckDetails(
        check_name="dr_positivity",
        total_resources=len(dr_rows),
        failing_resources=failing_resources,
        failing_values=failing_values,
    )

    passed = len(failing_resources) == 0
    if passed:
        msg = f"All {len(dr_rows)} DR resources pass positivity checks"
    else:
        msg = (
            f"{len(failing_resources)}/{len(dr_rows)} DR resources fail "
            f"positivity: {', '.join(failing_resources)}"
        )

    return CheckResult(
        check_id="dr_positivity",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": details_obj.check_name,
            "total_resources": details_obj.total_resources,
            "failing_resources": details_obj.failing_resources,
            "failing_values": details_obj.failing_values,
        },
    )


def check_dr_energy_neutrality_feasibility(
    dr_rows: list[dict[str, str]],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check DR energy neutrality achievability.

    For every DR bus with daily_energy_neutral=true, verifies that the
    curtailed energy can be fully recovered within 24 hours:
      max_curtail_mw * max_curtail_hours <= max_recover_mw * (24 - max_curtail_hours)

    Args:
        dr_rows: List of row dicts from dr_buses.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with DrCheckDetails in the details dict.
    """
    failing_resources: list[str] = []
    failing_values: dict[str, object] = {}

    for row in dr_rows:
        neutral_str = row.get("daily_energy_neutral", "true").strip().lower()
        if neutral_str not in ("true", "1"):
            continue

        dr_id = row.get("dr_id", row.get("bus_id", row.get("bus", "unknown")))
        dr_id = str(dr_id).strip()

        curtail_mw = float(row["max_curtail_mw"])
        recover_mw = float(row["max_recover_mw"])
        max_curtail_hours = float(row["max_curtail_hours"])

        curtail_energy = curtail_mw * max_curtail_hours
        recovery_hours = NUM_HOURS - max_curtail_hours
        recover_energy = recover_mw * recovery_hours

        if curtail_energy > recover_energy:
            failing_resources.append(dr_id)
            failing_values[dr_id] = {
                "curtail_mwh": curtail_energy,
                "recover_mwh": recover_energy,
                "max_curtail_mw": curtail_mw,
                "max_recover_mw": recover_mw,
                "max_curtail_hours": max_curtail_hours,
            }

    neutral_count = sum(
        1 for r in dr_rows if r.get("daily_energy_neutral", "true").strip().lower() in ("true", "1")
    )
    passed = len(failing_resources) == 0
    if passed:
        msg = f"All {neutral_count} energy-neutral DR resources pass feasibility check"
    else:
        msg = (
            f"{len(failing_resources)}/{neutral_count} energy-neutral DR "
            f"resources fail: {', '.join(failing_resources)}"
        )

    return CheckResult(
        check_id="dr_energy_neutrality",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": "dr_energy_neutrality",
            "total_resources": neutral_count,
            "failing_resources": failing_resources,
            "failing_values": failing_values,
        },
    )


def check_dr_curtailment_vs_local_load(
    dr_rows: list[dict[str, str]],
    bus_loads: list[HourlyBusLoad],
    network_id: ValidationNetworkId,
) -> CheckResult:
    """Check DR curtailment does not exceed local bus load.

    For every DR bus, verifies that max_curtail_mw does not exceed the
    local bus load at any of the 24 hours. A DR resource that exceeds
    the local load would produce negative demand.

    Args:
        dr_rows: List of row dicts from dr_buses.csv.
        bus_loads: List of HourlyBusLoad from load_24h.csv.
        network_id: Network being checked.

    Returns:
        A CheckResult with DrCheckDetails in the details dict.
    """
    # Build bus_id -> HourlyBusLoad lookup
    bus_load_map: dict[int, HourlyBusLoad] = {bl.bus_id: bl for bl in bus_loads}

    failing_resources: list[str] = []
    failing_values: dict[str, object] = {}

    for row in dr_rows:
        dr_id = row.get("dr_id", row.get("bus_id", row.get("bus", "unknown")))
        dr_id_str = str(dr_id).strip()

        # Get the bus_id for load lookup
        bus_id = int(row.get("bus", row.get("bus_id", "0")).strip())
        curtail_mw = float(row["max_curtail_mw"])

        bl = bus_load_map.get(bus_id)
        if bl is None:
            # No load data for this bus -- skip or flag
            continue

        failing_hours: list[int] = []
        for h in range(NUM_HOURS):
            if curtail_mw > bl.load_mw[h]:
                failing_hours.append(h)

        if failing_hours:
            failing_resources.append(dr_id_str)
            failing_values[dr_id_str] = {
                "max_curtail_mw": curtail_mw,
                "failing_hours": failing_hours,
                "load_at_failing_hours": [bl.load_mw[h] for h in failing_hours],
            }

    passed = len(failing_resources) == 0
    if passed:
        msg = f"All {len(dr_rows)} DR resources have curtailment within local load"
    else:
        msg = (
            f"{len(failing_resources)}/{len(dr_rows)} DR resources "
            f"exceed local load: {', '.join(failing_resources)}"
        )

    return CheckResult(
        check_id="dr_curtailment_vs_load",
        network_id=network_id,
        passed=passed,
        severity=CheckSeverity.ERROR,
        message=msg,
        details={
            "check_name": "dr_curtailment_vs_load",
            "total_resources": len(dr_rows),
            "failing_resources": failing_resources,
            "failing_values": failing_values,
        },
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_reserve_checks(
    network_dir: Path,
    network_id: ValidationNetworkId,
) -> list[CheckResult]:
    """Run all reserve adequacy and sanity checks for a single network.

    Args:
        network_dir: Path to the network's timeseries directory.
        network_id: Network identifier.

    Returns:
        A list of CheckResult for all reserve checks.
    """
    results: list[CheckResult] = []

    reserve_req = load_reserve_requirements(network_dir)
    eligibility = load_reserve_eligibility(network_dir)
    system_load = load_system_load(network_dir)

    results.append(check_reserve_spinning_adequacy(reserve_req, eligibility, network_id))
    results.append(check_reserve_non_spinning_adequacy(reserve_req, eligibility, network_id))
    results.extend(check_reserve_requirements_sanity(reserve_req, system_load, network_id))

    return results


def run_bess_checks(
    network_dir: Path,
    network_id: ValidationNetworkId,
) -> list[CheckResult]:
    """Run all BESS parameter checks for a single network.

    Args:
        network_dir: Path to the network's timeseries directory.
        network_id: Network identifier.

    Returns:
        A list of CheckResult for all BESS checks.
    """
    bess_rows = load_bess_units(network_dir)

    return [
        check_bess_positivity(bess_rows, network_id),
        check_bess_efficiency(bess_rows, network_id),
        check_bess_soc_ordering(bess_rows, network_id),
        check_bess_cyclic_soc_feasibility(bess_rows, network_id),
    ]


def run_dr_checks(
    network_dir: Path,
    network_id: ValidationNetworkId,
) -> list[CheckResult]:
    """Run all DR checks for a single network.

    Args:
        network_dir: Path to the network's timeseries directory.
        network_id: Network identifier.

    Returns:
        A list of CheckResult for all DR checks.
    """
    dr_rows = load_dr_buses(network_dir)
    bus_loads = load_bus_hourly_loads(network_dir)

    return [
        check_dr_positivity(dr_rows, network_id),
        check_dr_energy_neutrality_feasibility(dr_rows, network_id),
        check_dr_curtailment_vs_local_load(dr_rows, bus_loads, network_id),
    ]


def run_all_reserve_bess_dr_checks(
    network_dir: Path,
    network_id: ValidationNetworkId,
) -> list[CheckResult]:
    """Run all reserve, BESS, and DR checks for a single network.

    Args:
        network_dir: Path to the network's timeseries directory.
        network_id: Network identifier.

    Returns:
        Combined list of CheckResult from all three check groups.
    """
    results: list[CheckResult] = []
    results.extend(run_reserve_checks(network_dir, network_id))
    results.extend(run_bess_checks(network_dir, network_id))
    results.extend(run_dr_checks(network_dir, network_id))
    return results


def validate_all_networks(
    timeseries_base_dir: Path | None = None,
) -> list[CheckResult]:
    """Run all reserve, BESS, and DR checks across all three networks.

    Args:
        timeseries_base_dir: Base directory containing network subdirectories.
            Defaults to <repo_root>/data/timeseries/.

    Returns:
        A combined list of CheckResult across all networks.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "data" / "timeseries"

    all_results: list[CheckResult] = []

    for tier, dir_name in NETWORK_DIRS.items():
        network_id = ValidationNetworkId(dir_name)
        network_dir = timeseries_base_dir / dir_name
        try:
            results = run_all_reserve_bess_dr_checks(network_dir, network_id)
            all_results.extend(results)
        except FileNotFoundError as exc:
            logger.error("Skipping %s: %s", dir_name, exc)
            all_results.append(
                CheckResult(
                    check_id="file_not_found",
                    network_id=network_id,
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=str(exc),
                )
            )

    return all_results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = validate_all_networks()
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} checks")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.network_id}/{r.check_id}: {r.message}")
