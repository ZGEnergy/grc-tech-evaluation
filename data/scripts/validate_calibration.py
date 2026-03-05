"""Calibration Validation & Summary Report (PRD 02/06).

Runs cross-network validation checks on all outputs from Phase 2 Deliverables 1-5
and produces a structured summary report. This is the final deliverable in Phase 2,
serving as the quality gate.

Validation checks fall into five categories:
  1. Completeness (C1-C4)
  2. Physical feasibility (P1-P4)
  3. Single-day feasibility (S1)
  4. Reserve adequacy (R1-R2)
  5. Parameter distribution sanity (D1-D3)
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

TEMPORAL_PARAM_FIELDS: tuple[str, ...] = (
    "ramp_rate_mw_per_min",
    "ramp_rate_mw_per_hr",
    "min_up_time_hr",
    "min_down_time_hr",
    "startup_cost_dollar",
    "startup_time_hr",
    "shutdown_cost_dollar",
)

RENEWABLE_FUEL_TYPES: frozenset[str] = frozenset({"wind", "solar"})

ADEQUACY_PASS_THRESHOLD: float = 1.5
ADEQUACY_FAIL_THRESHOLD: float = 1.0

MAX_FAILING_UIDS_REPORTED: int = 20

NETWORK_M_FILE_NAMES: dict[str, str] = {
    "case39": "case39.m",
    "ACTIVSg2000": "case_ACTIVSg2000.m",
    "ACTIVSg10k": "case_ACTIVSg10k.m",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ValidationNetworkId(StrEnum):
    """Identifiers for networks in the validation scope."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class CheckStatus(StrEnum):
    """Result status for a single validation check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class CheckCategory(StrEnum):
    """Category grouping for validation checks."""

    COMPLETENESS = "completeness"
    PHYSICAL_FEASIBILITY = "physical_feasibility"
    SINGLE_DAY_FEASIBILITY = "single_day_feasibility"
    RESERVE_ADEQUACY = "reserve_adequacy"
    PARAMETER_DISTRIBUTION = "parameter_distribution"


@dataclass(frozen=True)
class CheckResult:
    """Result of a single validation check."""

    check_id: str
    category: CheckCategory
    description: str
    status: CheckStatus
    generators_checked: int
    generators_failing: int
    failing_gen_uids: list[str]
    detail: str


@dataclass(frozen=True)
class NetworkValidationResult:
    """Validation result for a single network."""

    network_id: ValidationNetworkId
    generator_count: int
    check_results: list[CheckResult]
    pass_count: int
    warn_count: int
    fail_count: int
    markdown_report_path: str
    all_passed: bool


@dataclass(frozen=True)
class ValidationSummary:
    """Top-level validation summary across all networks."""

    network_results: list[NetworkValidationResult]
    overall_pass: bool
    total_checks: int
    total_pass: int
    total_warn: int
    total_fail: int
    json_report_path: str
    script_version: str


# ---------------------------------------------------------------------------
# Loading functions
# ---------------------------------------------------------------------------


def load_expected_gen_uids(cleaned_m_path: Path) -> list[str]:
    """Parse cleaned .m file and derive GEN UIDs.

    Uses the bus_{bus}_gen_{idx} convention where idx is the 0-based index
    of the generator in the mpc.gen matrix.

    Args:
        cleaned_m_path: Path to the cleaned MATPOWER .m file.

    Returns:
        A list of gen_uid strings, one per generator, in mpc.gen row order.
    """
    case_data = parse_matpower_case(cleaned_m_path)
    uids: list[str] = []
    for i, gen in enumerate(case_data.generators):
        uid = f"bus_{gen.gen_bus}_gen_{i}"
        uids.append(uid)
    return uids


def load_csv_gen_uids(csv_path: Path, uid_column: str = "gen_uid") -> list[str]:
    """Load gen_uid column from a CSV file.

    Args:
        csv_path: Path to the CSV file.
        uid_column: Name of the column containing gen_uid values.

    Returns:
        A list of gen_uid strings in CSV row order.
    """
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return [row[uid_column].strip() for row in reader]


def load_reference_tech_classes(reference_csv_path: Path) -> set[str]:
    """Load set of valid tech class strings from the D1 reference table.

    Skips comment lines (starting with '#').

    Args:
        reference_csv_path: Path to the rts_gmlc_tech_classes.csv file.

    Returns:
        A set of tech class strings.
    """
    text = reference_csv_path.read_text(encoding="utf-8")
    non_comment_lines = [line for line in text.splitlines() if not line.startswith("#")]
    filtered_text = "\n".join(non_comment_lines)
    reader = csv.DictReader(io.StringIO(filtered_text))
    return {row["tech_class"].strip() for row in reader}


def load_temporal_params_rows(csv_path: Path) -> list[dict[str, str]]:
    """Load gen_temporal_params.csv as a list of dicts.

    Args:
        csv_path: Path to the gen_temporal_params.csv file.

    Returns:
        A list of dicts, one per generator row.
    """
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def load_classification_rows(csv_path: Path) -> list[dict[str, str]]:
    """Load gen_fuel_classification.csv as a list of dicts.

    Args:
        csv_path: Path to the gen_fuel_classification.csv file.

    Returns:
        A list of dicts, one per generator row.
    """
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def load_eligibility_rows(csv_path: Path) -> list[dict[str, str]]:
    """Load reserve_eligibility.csv as a list of dicts.

    Args:
        csv_path: Path to the reserve_eligibility.csv file.

    Returns:
        A list of dicts, one per generator row.
    """
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def load_reserve_requirement(reserve_req_csv_path: Path, product: str) -> float:
    """Load reserve requirement MW for a specific product.

    The D4 CSV has columns: Product, HR_1..HR_24, etc.
    Since the requirement is constant across all hours, reads HR_1.

    Args:
        reserve_req_csv_path: Path to the reserve_requirements_24h.csv file.
        product: The reserve product string (e.g., "spinning", "non_spinning").

    Returns:
        The reserve requirement in MW.

    Raises:
        ValueError: If the product is not found in the CSV.
    """
    text = reserve_req_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row["Product"].strip() == product:
            return float(row["HR_1"])
    msg = f"Product '{product}' not found in {reserve_req_csv_path}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Completeness checks (C1-C4)
# ---------------------------------------------------------------------------


def check_classification_completeness(
    expected_uids: list[str],
    classification_rows: list[dict[str, str]],
) -> CheckResult:
    """C1: Every generator in the .m file has a row in the D2 classification CSV.

    Args:
        expected_uids: Gen UIDs derived from the cleaned .m file.
        classification_rows: Rows from gen_fuel_classification.csv.

    Returns:
        A CheckResult with PASS if all generators are present, FAIL otherwise.
    """
    csv_uids = {row["gen_uid"].strip() for row in classification_rows}
    expected_set = set(expected_uids)
    missing = sorted(expected_set - csv_uids)
    failing = missing[:MAX_FAILING_UIDS_REPORTED]

    status = CheckStatus.PASS if not missing else CheckStatus.FAIL
    detail = (
        f"{len(missing)} generator(s) missing from classification CSV"
        if missing
        else "All generators present in classification CSV"
    )

    return CheckResult(
        check_id="C1",
        category=CheckCategory.COMPLETENESS,
        description="Every generator in .m file has a classification row",
        status=status,
        generators_checked=len(expected_uids),
        generators_failing=len(missing),
        failing_gen_uids=failing,
        detail=detail,
    )


def check_temporal_params_completeness(
    expected_uids: list[str],
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """C2: Every generator in the .m file has a row in the D3 temporal params CSV.

    Args:
        expected_uids: Gen UIDs derived from the cleaned .m file.
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all generators are present, FAIL otherwise.
    """
    csv_uids = {row["gen_uid"].strip() for row in temporal_rows}
    expected_set = set(expected_uids)
    missing = sorted(expected_set - csv_uids)
    failing = missing[:MAX_FAILING_UIDS_REPORTED]

    status = CheckStatus.PASS if not missing else CheckStatus.FAIL
    detail = (
        f"{len(missing)} generator(s) missing from temporal params CSV"
        if missing
        else "All generators present in temporal params CSV"
    )

    return CheckResult(
        check_id="C2",
        category=CheckCategory.COMPLETENESS,
        description="Every generator in .m file has a temporal params row",
        status=status,
        generators_checked=len(expected_uids),
        generators_failing=len(missing),
        failing_gen_uids=failing,
        detail=detail,
    )


def check_eligibility_completeness(
    expected_uids: list[str],
    eligibility_rows: list[dict[str, str]],
) -> CheckResult:
    """C3: Every generator in the .m file has a row in the D5 eligibility CSV.

    Args:
        expected_uids: Gen UIDs derived from the cleaned .m file.
        eligibility_rows: Rows from reserve_eligibility.csv.

    Returns:
        A CheckResult with PASS if all generators are present, FAIL otherwise.
    """
    csv_uids = {row["gen_uid"].strip() for row in eligibility_rows}
    expected_set = set(expected_uids)
    missing = sorted(expected_set - csv_uids)
    failing = missing[:MAX_FAILING_UIDS_REPORTED]

    status = CheckStatus.PASS if not missing else CheckStatus.FAIL
    detail = (
        f"{len(missing)} generator(s) missing from eligibility CSV"
        if missing
        else "All generators present in eligibility CSV"
    )

    return CheckResult(
        check_id="C3",
        category=CheckCategory.COMPLETENESS,
        description="Every generator in .m file has an eligibility row",
        status=status,
        generators_checked=len(expected_uids),
        generators_failing=len(missing),
        failing_gen_uids=failing,
        detail=detail,
    )


def check_tech_class_coverage(
    classification_rows: list[dict[str, str]],
    reference_tech_classes: set[str],
) -> CheckResult:
    """C4: All tech classes assigned to generators exist in the D1 reference table.

    Renewable tech classes (wind, solar) are exempt from this check since they
    may not appear in the reference table.

    Args:
        classification_rows: Rows from gen_fuel_classification.csv.
        reference_tech_classes: Valid tech class strings from D1.

    Returns:
        A CheckResult with PASS if all non-exempt classes exist, FAIL otherwise.
    """
    exempt_classes = {"wind", "solar"}
    assigned_classes: set[str] = set()
    for row in classification_rows:
        tc = row["tech_class"].strip()
        if tc not in exempt_classes:
            assigned_classes.add(tc)

    missing = sorted(assigned_classes - reference_tech_classes)
    generators_with_missing = []
    for row in classification_rows:
        tc = row["tech_class"].strip()
        if tc in missing:
            generators_with_missing.append(row["gen_uid"].strip())

    failing = generators_with_missing[:MAX_FAILING_UIDS_REPORTED]
    status = CheckStatus.PASS if not missing else CheckStatus.FAIL
    detail = (
        f"Unknown tech classes: {missing}"
        if missing
        else "All assigned tech classes exist in reference table"
    )

    return CheckResult(
        check_id="C4",
        category=CheckCategory.COMPLETENESS,
        description="All tech classes exist in D1 reference table",
        status=status,
        generators_checked=len(assigned_classes),
        generators_failing=len(generators_with_missing),
        failing_gen_uids=failing,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Physical feasibility checks (P1-P4)
# ---------------------------------------------------------------------------


def check_ramp_rate_vs_pmax(
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """P1: Ramp rate (MW/hr) does not exceed Pmax for any generator.

    Args:
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all ramp rates are within Pmax, FAIL otherwise.
    """
    failing_uids: list[str] = []
    for row in temporal_rows:
        ramp_hr = float(row["ramp_rate_mw_per_hr"])
        pmax = float(row["pmax_mw"])
        if ramp_hr > pmax and pmax > 0:
            failing_uids.append(row["gen_uid"].strip())

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} generator(s) have ramp_rate_mw_per_hr > pmax_mw"
        if failing_uids
        else "All ramp rates within Pmax bounds"
    )

    return CheckResult(
        check_id="P1",
        category=CheckCategory.PHYSICAL_FEASIBILITY,
        description="Ramp rate (MW/hr) does not exceed Pmax",
        status=status,
        generators_checked=len(temporal_rows),
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


def check_non_negative_costs(
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """P2: All cost fields are non-negative.

    Checks startup_cost_dollar and shutdown_cost_dollar.

    Args:
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all costs are non-negative, FAIL otherwise.
    """
    cost_fields = ("startup_cost_dollar", "shutdown_cost_dollar")
    failing_uids: list[str] = []
    for row in temporal_rows:
        uid = row["gen_uid"].strip()
        for cf in cost_fields:
            val = float(row[cf])
            if val < 0:
                if uid not in failing_uids:
                    failing_uids.append(uid)

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} generator(s) have negative cost values"
        if failing_uids
        else "All cost values are non-negative"
    )

    return CheckResult(
        check_id="P2",
        category=CheckCategory.PHYSICAL_FEASIBILITY,
        description="All cost fields are non-negative",
        status=status,
        generators_checked=len(temporal_rows),
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


def check_thermal_ramp_positive(
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """P3: Thermal generators have positive ramp rates.

    Wind and solar generators are exempt (zero ramp is expected).

    Args:
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all thermal gens have positive ramp, FAIL otherwise.
    """
    failing_uids: list[str] = []
    thermal_count = 0
    for row in temporal_rows:
        fuel = row["fuel_type"].strip().lower()
        if fuel in RENEWABLE_FUEL_TYPES:
            continue
        thermal_count += 1
        ramp_hr = float(row["ramp_rate_mw_per_hr"])
        if ramp_hr <= 0:
            failing_uids.append(row["gen_uid"].strip())

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} thermal generator(s) have zero or negative ramp rate"
        if failing_uids
        else "All thermal generators have positive ramp rates"
    )

    return CheckResult(
        check_id="P3",
        category=CheckCategory.PHYSICAL_FEASIBILITY,
        description="Thermal generators have positive ramp rates",
        status=status,
        generators_checked=thermal_count,
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


def check_pmax_pmin_bounds(
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """P4: Pmax >= Pmin for all generators.

    Args:
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all Pmax >= Pmin, FAIL otherwise.
    """
    failing_uids: list[str] = []
    for row in temporal_rows:
        pmax = float(row["pmax_mw"])
        pmin = float(row["pmin_mw"])
        if pmax < pmin:
            failing_uids.append(row["gen_uid"].strip())

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} generator(s) have Pmax < Pmin"
        if failing_uids
        else "All generators have valid Pmax >= Pmin bounds"
    )

    return CheckResult(
        check_id="P4",
        category=CheckCategory.PHYSICAL_FEASIBILITY,
        description="Pmax >= Pmin for all generators",
        status=status,
        generators_checked=len(temporal_rows),
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Single-day feasibility (S1)
# ---------------------------------------------------------------------------


def check_min_updown_24h(
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """S1: min_up_time + min_down_time <= 24 hours.

    Only checks thermal generators (renewables are exempt).

    Args:
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all generators satisfy constraint, FAIL otherwise.
    """
    failing_uids: list[str] = []
    thermal_count = 0
    for row in temporal_rows:
        fuel = row["fuel_type"].strip().lower()
        if fuel in RENEWABLE_FUEL_TYPES:
            continue
        thermal_count += 1
        min_up = float(row["min_up_time_hr"])
        min_down = float(row["min_down_time_hr"])
        if min_up + min_down > 24.0:
            failing_uids.append(row["gen_uid"].strip())

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} generator(s) have min_up + min_down > 24h"
        if failing_uids
        else "All generators satisfy single-day feasibility"
    )

    return CheckResult(
        check_id="S1",
        category=CheckCategory.SINGLE_DAY_FEASIBILITY,
        description="min_up_time + min_down_time <= 24 hours",
        status=status,
        generators_checked=thermal_count,
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Reserve adequacy (R1-R2)
# ---------------------------------------------------------------------------


def check_spinning_adequacy(
    eligibility_rows: list[dict[str, str]],
    requirement_mw: float,
) -> CheckResult:
    """R1: Spinning reserve eligible capacity meets the requirement.

    PASS if ratio >= 1.5, WARN if >= 1.0, FAIL if < 1.0.

    Args:
        eligibility_rows: Rows from reserve_eligibility.csv.
        requirement_mw: Spinning reserve requirement in MW.

    Returns:
        A CheckResult with PASS/WARN/FAIL based on adequacy ratio.
    """
    eligible_capacity = 0.0
    eligible_count = 0
    for row in eligibility_rows:
        eligible_str = row["spinning_eligible"].strip().lower()
        if eligible_str == "true":
            eligible_capacity += float(row["max_spinning_mw"])
            eligible_count += 1

    ratio = eligible_capacity / requirement_mw if requirement_mw > 0 else 0.0

    if ratio >= ADEQUACY_PASS_THRESHOLD:
        status = CheckStatus.PASS
    elif ratio >= ADEQUACY_FAIL_THRESHOLD:
        status = CheckStatus.WARN
    else:
        status = CheckStatus.FAIL

    detail = (
        f"Eligible capacity: {eligible_capacity:.2f} MW, "
        f"requirement: {requirement_mw:.2f} MW, "
        f"ratio: {ratio:.3f}"
    )

    return CheckResult(
        check_id="R1",
        category=CheckCategory.RESERVE_ADEQUACY,
        description="Spinning reserve eligible capacity meets requirement",
        status=status,
        generators_checked=len(eligibility_rows),
        generators_failing=0 if status == CheckStatus.PASS else eligible_count,
        failing_gen_uids=[],
        detail=detail,
    )


def check_non_spinning_adequacy(
    eligibility_rows: list[dict[str, str]],
    requirement_mw: float,
) -> CheckResult:
    """R2: Non-spinning reserve eligible capacity meets the requirement.

    PASS if ratio >= 1.5, WARN if >= 1.0, FAIL if < 1.0.

    Args:
        eligibility_rows: Rows from reserve_eligibility.csv.
        requirement_mw: Non-spinning reserve requirement in MW.

    Returns:
        A CheckResult with PASS/WARN/FAIL based on adequacy ratio.
    """
    eligible_capacity = 0.0
    eligible_count = 0
    for row in eligibility_rows:
        eligible_str = row["non_spinning_eligible"].strip().lower()
        if eligible_str == "true":
            eligible_capacity += float(row["max_non_spinning_mw"])
            eligible_count += 1

    ratio = eligible_capacity / requirement_mw if requirement_mw > 0 else 0.0

    if ratio >= ADEQUACY_PASS_THRESHOLD:
        status = CheckStatus.PASS
    elif ratio >= ADEQUACY_FAIL_THRESHOLD:
        status = CheckStatus.WARN
    else:
        status = CheckStatus.FAIL

    detail = (
        f"Eligible capacity: {eligible_capacity:.2f} MW, "
        f"requirement: {requirement_mw:.2f} MW, "
        f"ratio: {ratio:.3f}"
    )

    return CheckResult(
        check_id="R2",
        category=CheckCategory.RESERVE_ADEQUACY,
        description="Non-spinning reserve eligible capacity meets requirement",
        status=status,
        generators_checked=len(eligibility_rows),
        generators_failing=0 if status == CheckStatus.PASS else eligible_count,
        failing_gen_uids=[],
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Parameter distribution sanity (D1-D3)
# ---------------------------------------------------------------------------


def check_renewable_zeros(
    temporal_rows: list[dict[str, str]],
) -> CheckResult:
    """D1: Renewable generators have zero temporal parameters.

    Checks that all fields in TEMPORAL_PARAM_FIELDS are zero for wind/solar.

    Args:
        temporal_rows: Rows from gen_temporal_params.csv.

    Returns:
        A CheckResult with PASS if all renewables have zeros, FAIL otherwise.
    """
    failing_uids: list[str] = []
    renewable_count = 0
    for row in temporal_rows:
        fuel = row["fuel_type"].strip().lower()
        if fuel not in RENEWABLE_FUEL_TYPES:
            continue
        renewable_count += 1
        for field_name in TEMPORAL_PARAM_FIELDS:
            val = float(row[field_name])
            if val != 0.0:
                failing_uids.append(row["gen_uid"].strip())
                break

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} renewable generator(s) have nonzero temporal params"
        if failing_uids
        else "All renewable generators have zero temporal parameters"
    )

    return CheckResult(
        check_id="D1",
        category=CheckCategory.PARAMETER_DISTRIBUTION,
        description="Renewable generators have zero temporal parameters",
        status=status,
        generators_checked=renewable_count,
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


def check_nuclear_ineligible(
    eligibility_rows: list[dict[str, str]],
) -> CheckResult:
    """D2: Nuclear generators are ineligible for reserves.

    Both spinning_eligible and non_spinning_eligible should be false.

    Args:
        eligibility_rows: Rows from reserve_eligibility.csv.

    Returns:
        A CheckResult with PASS if nuclear is ineligible, FAIL otherwise.
    """
    failing_uids: list[str] = []
    nuclear_count = 0
    for row in eligibility_rows:
        fuel = row["fuel_type"].strip().lower()
        if fuel != "nuclear":
            continue
        nuclear_count += 1
        spin = row["spinning_eligible"].strip().lower() == "true"
        nonspin = row["non_spinning_eligible"].strip().lower() == "true"
        if spin or nonspin:
            failing_uids.append(row["gen_uid"].strip())

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} nuclear generator(s) are marked eligible for reserves"
        if failing_uids
        else "All nuclear generators are ineligible for reserves"
    )

    return CheckResult(
        check_id="D2",
        category=CheckCategory.PARAMETER_DISTRIBUTION,
        description="Nuclear generators are ineligible for reserves",
        status=status,
        generators_checked=nuclear_count,
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


def check_eligibility_mw_consistency(
    eligibility_rows: list[dict[str, str]],
) -> CheckResult:
    """D3: Eligibility flags are consistent with MW values.

    If spinning_eligible=true, max_spinning_mw must be > 0.
    If non_spinning_eligible=true, max_non_spinning_mw must be > 0.
    If spinning_eligible=false, max_spinning_mw must be 0.
    If non_spinning_eligible=false, max_non_spinning_mw must be 0.

    Args:
        eligibility_rows: Rows from reserve_eligibility.csv.

    Returns:
        A CheckResult with PASS if flags and MW are consistent, FAIL otherwise.
    """
    failing_uids: list[str] = []
    for row in eligibility_rows:
        uid = row["gen_uid"].strip()
        spin_elig = row["spinning_eligible"].strip().lower() == "true"
        nonspin_elig = row["non_spinning_eligible"].strip().lower() == "true"
        spin_mw = float(row["max_spinning_mw"])
        nonspin_mw = float(row["max_non_spinning_mw"])

        inconsistent = False
        if spin_elig and spin_mw <= 0:
            inconsistent = True
        if not spin_elig and spin_mw != 0:
            inconsistent = True
        if nonspin_elig and nonspin_mw <= 0:
            inconsistent = True
        if not nonspin_elig and nonspin_mw != 0:
            inconsistent = True

        if inconsistent and uid not in failing_uids:
            failing_uids.append(uid)

    status = CheckStatus.PASS if not failing_uids else CheckStatus.FAIL
    capped = failing_uids[:MAX_FAILING_UIDS_REPORTED]
    detail = (
        f"{len(failing_uids)} generator(s) have inconsistent eligibility flags and MW"
        if failing_uids
        else "All eligibility flags are consistent with MW values"
    )

    return CheckResult(
        check_id="D3",
        category=CheckCategory.PARAMETER_DISTRIBUTION,
        description="Eligibility flags consistent with MW values",
        status=status,
        generators_checked=len(eligibility_rows),
        generators_failing=len(failing_uids),
        failing_gen_uids=capped,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_markdown_report(
    result: NetworkValidationResult,
    dest_path: Path,
) -> None:
    """Write a per-network markdown validation report.

    Args:
        result: The network validation result.
        dest_path: File path to write the markdown report.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Validation Report: {result.network_id.value}")
    lines.append("")
    lines.append(f"- **Generator count:** {result.generator_count}")
    lines.append(f"- **Checks run:** {len(result.check_results)}")
    lines.append(f"- **PASS:** {result.pass_count}")
    lines.append(f"- **WARN:** {result.warn_count}")
    lines.append(f"- **FAIL:** {result.fail_count}")
    lines.append(f"- **All passed:** {result.all_passed}")
    lines.append("")
    lines.append("## Check Results")
    lines.append("")
    lines.append("| Check ID | Category | Status | Checked | Failing | Description |")
    lines.append("|----------|----------|--------|---------|---------|-------------|")

    for cr in result.check_results:
        lines.append(
            f"| {cr.check_id} | {cr.category.value} | {cr.status.value} "
            f"| {cr.generators_checked} | {cr.generators_failing} "
            f"| {cr.description} |"
        )

    lines.append("")
    lines.append("## Details")
    lines.append("")

    for cr in result.check_results:
        lines.append(f"### {cr.check_id}: {cr.description}")
        lines.append("")
        lines.append(f"**Status:** {cr.status.value}")
        lines.append("")
        lines.append(cr.detail)
        if cr.failing_gen_uids:
            lines.append("")
            lines.append(
                f"**Failing generators (up to {MAX_FAILING_UIDS_REPORTED}):** "
                + ", ".join(cr.failing_gen_uids)
            )
        lines.append("")

    dest_path.write_text("\n".join(lines), encoding="utf-8")


def write_json_report(
    summary: ValidationSummary,
    dest_path: Path,
) -> None:
    """Write consolidated validation results as JSON.

    Uses deterministic formatting (sorted keys, 2-space indent).

    Args:
        summary: The complete validation summary.
        dest_path: File path to write the JSON report.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    data = _summary_to_dict(summary)
    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def _summary_to_dict(summary: ValidationSummary) -> dict:
    """Convert a ValidationSummary to a JSON-serializable dict.

    Args:
        summary: The validation summary.

    Returns:
        A JSON-serializable dict.
    """
    return {
        "overall_pass": summary.overall_pass,
        "total_checks": summary.total_checks,
        "total_pass": summary.total_pass,
        "total_warn": summary.total_warn,
        "total_fail": summary.total_fail,
        "script_version": summary.script_version,
        "json_report_path": summary.json_report_path,
        "network_results": [
            {
                "network_id": nr.network_id.value,
                "generator_count": nr.generator_count,
                "pass_count": nr.pass_count,
                "warn_count": nr.warn_count,
                "fail_count": nr.fail_count,
                "all_passed": nr.all_passed,
                "markdown_report_path": nr.markdown_report_path,
                "check_results": [
                    {
                        "check_id": cr.check_id,
                        "category": cr.category.value,
                        "description": cr.description,
                        "status": cr.status.value,
                        "generators_checked": cr.generators_checked,
                        "generators_failing": cr.generators_failing,
                        "failing_gen_uids": cr.failing_gen_uids,
                        "detail": cr.detail,
                    }
                    for cr in nr.check_results
                ],
            }
            for nr in summary.network_results
        ],
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def validate_network(
    network_id: ValidationNetworkId,
    cleaned_m_path: Path,
    classification_csv_path: Path,
    temporal_params_csv_path: Path,
    eligibility_csv_path: Path,
    reserve_req_csv_path: Path,
    reference_csv_path: Path,
    validation_output_dir: Path,
) -> NetworkValidationResult:
    """Run all validation checks for a single network.

    Args:
        network_id: Which network to validate.
        cleaned_m_path: Path to the cleaned .m file.
        classification_csv_path: Path to D2 gen_fuel_classification.csv.
        temporal_params_csv_path: Path to D3 gen_temporal_params.csv.
        eligibility_csv_path: Path to D5 reserve_eligibility.csv.
        reserve_req_csv_path: Path to D4 reserve_requirements_24h.csv.
        reference_csv_path: Path to D1 rts_gmlc_tech_classes.csv.
        validation_output_dir: Directory for markdown report output.

    Returns:
        A NetworkValidationResult with all check results.
    """
    # Load data
    expected_uids = load_expected_gen_uids(cleaned_m_path)
    classification_rows = load_classification_rows(classification_csv_path)
    temporal_rows = load_temporal_params_rows(temporal_params_csv_path)
    eligibility_rows = load_eligibility_rows(eligibility_csv_path)
    reference_tech_classes = load_reference_tech_classes(reference_csv_path)

    spinning_req = load_reserve_requirement(reserve_req_csv_path, "spinning")
    non_spinning_req = load_reserve_requirement(reserve_req_csv_path, "non_spinning")

    # Run all checks
    checks: list[CheckResult] = [
        # Completeness (C1-C4)
        check_classification_completeness(expected_uids, classification_rows),
        check_temporal_params_completeness(expected_uids, temporal_rows),
        check_eligibility_completeness(expected_uids, eligibility_rows),
        check_tech_class_coverage(classification_rows, reference_tech_classes),
        # Physical feasibility (P1-P4)
        check_ramp_rate_vs_pmax(temporal_rows),
        check_non_negative_costs(temporal_rows),
        check_thermal_ramp_positive(temporal_rows),
        check_pmax_pmin_bounds(temporal_rows),
        # Single-day feasibility (S1)
        check_min_updown_24h(temporal_rows),
        # Reserve adequacy (R1-R2)
        check_spinning_adequacy(eligibility_rows, spinning_req),
        check_non_spinning_adequacy(eligibility_rows, non_spinning_req),
        # Parameter distribution (D1-D3)
        check_renewable_zeros(temporal_rows),
        check_nuclear_ineligible(eligibility_rows),
        check_eligibility_mw_consistency(eligibility_rows),
    ]

    pass_count = sum(1 for c in checks if c.status == CheckStatus.PASS)
    warn_count = sum(1 for c in checks if c.status == CheckStatus.WARN)
    fail_count = sum(1 for c in checks if c.status == CheckStatus.FAIL)
    all_passed = fail_count == 0

    md_path = validation_output_dir / f"{network_id.value}_validation.md"

    result = NetworkValidationResult(
        network_id=network_id,
        generator_count=len(expected_uids),
        check_results=checks,
        pass_count=pass_count,
        warn_count=warn_count,
        fail_count=fail_count,
        markdown_report_path=str(md_path),
        all_passed=all_passed,
    )

    write_markdown_report(result, md_path)

    return result


def print_summary(summary: ValidationSummary) -> None:
    """Print a human-readable validation summary to stdout.

    Args:
        summary: The complete validation summary.
    """
    print("=" * 72)
    print("Calibration Validation Summary")
    print("=" * 72)
    print(f"Script version: {summary.script_version}")
    print(f"Overall pass: {summary.overall_pass}")
    print(
        f"Total checks: {summary.total_checks} "
        f"(PASS: {summary.total_pass}, WARN: {summary.total_warn}, "
        f"FAIL: {summary.total_fail})"
    )
    print()

    for nr in summary.network_results:
        status_str = "ALL PASSED" if nr.all_passed else "HAS FAILURES"
        print(f"  {nr.network_id.value}: {status_str}")
        print(
            f"    Generators: {nr.generator_count}, "
            f"PASS: {nr.pass_count}, WARN: {nr.warn_count}, FAIL: {nr.fail_count}"
        )

    print()


def main(
    timeseries_base_dir: Path | None = None,
    reference_csv_path: Path | None = None,
    validation_output_dir: Path | None = None,
) -> ValidationSummary:
    """Entry point: validate all three networks and write consolidated report.

    Args:
        timeseries_base_dir: Base directory containing per-network subdirectories
            with D2-D5 output CSVs and cleaned .m files.
        reference_csv_path: Path to D1 rts_gmlc_tech_classes.csv.
        validation_output_dir: Directory for validation output files.

    Returns:
        The complete ValidationSummary.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_root / "timeseries"
    if reference_csv_path is None:
        reference_csv_path = repo_root / "reference" / "rts_gmlc_tech_classes.csv"
    if validation_output_dir is None:
        validation_output_dir = repo_root / "validation"

    network_results: list[NetworkValidationResult] = []

    for network_id in ValidationNetworkId:
        network_dir = timeseries_base_dir / network_id.value
        m_file_name = NETWORK_M_FILE_NAMES[network_id.value]
        cleaned_m_path = network_dir / m_file_name

        classification_csv = network_dir / "gen_fuel_classification.csv"
        temporal_csv = network_dir / "gen_temporal_params.csv"
        eligibility_csv = network_dir / "reserve_eligibility.csv"
        reserve_req_csv = network_dir / "reserve_requirements_24h.csv"

        result = validate_network(
            network_id=network_id,
            cleaned_m_path=cleaned_m_path,
            classification_csv_path=classification_csv,
            temporal_params_csv_path=temporal_csv,
            eligibility_csv_path=eligibility_csv,
            reserve_req_csv_path=reserve_req_csv,
            reference_csv_path=reference_csv_path,
            validation_output_dir=validation_output_dir,
        )
        network_results.append(result)

    total_checks = sum(len(nr.check_results) for nr in network_results)
    total_pass = sum(nr.pass_count for nr in network_results)
    total_warn = sum(nr.warn_count for nr in network_results)
    total_fail = sum(nr.fail_count for nr in network_results)
    overall_pass = total_fail == 0

    json_path = validation_output_dir / "validation_results.json"

    summary = ValidationSummary(
        network_results=network_results,
        overall_pass=overall_pass,
        total_checks=total_checks,
        total_pass=total_pass,
        total_warn=total_warn,
        total_fail=total_fail,
        json_report_path=str(json_path),
        script_version=__version__,
    )

    write_json_report(summary, json_path)
    print_summary(summary)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
