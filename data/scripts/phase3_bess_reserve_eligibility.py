"""BESS Reserve Eligibility Integration for SMALL and MEDIUM networks.

Integrates battery energy storage system (BESS) units from Phase 3 D2 (BESS Unit
Placement & Sizing) into the per-network reserve eligibility framework established
by Phase 2 D5 (Reserve Eligibility Assignment). Reads BESS unit definitions from D2's
bess_units.csv, computes each unit's maximum reserve contribution, appends BESS rows
to the existing reserve_eligibility.csv, and re-runs the adequacy cross-check.

The maximum spinning reserve contribution for a BESS unit is
min(power_mw, ramp_rate_mw_per_min * 10), following the same 10-minute delivery window
formula used for thermal generators in Phase 2 D5. The maximum non-spinning reserve
contribution is simply power_mw (BESS has zero startup time).

This script overwrites the Phase 2 D5 reserve_eligibility.csv with combined
thermal + BESS rows. Prior BESS rows are filtered out before re-appending, ensuring
idempotent execution.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.assign_reserve_eligibility import (
    OUTPUT_CSV_COLUMNS,
    SPINNING_RAMP_WINDOW_MIN,
    ReserveEligibilityRow,
)
from scripts.define_reserves import ReserveProduct
from scripts.phase3_bess_placement import BessUnit

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class BessReserveNetworkId(StrEnum):
    """Network identifiers in scope for BESS reserve eligibility integration."""

    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


# --- BESS-specific constants ---

BESS_TECH_CLASS: str = "bess"
"""Technology class string for BESS rows in reserve_eligibility.csv.

Must match the 'bess' key in Phase 2 D5's TECH_CLASS_ELIGIBILITY lookup table.
"""

BESS_FUEL_TYPE: str = "storage"
"""Fuel type string for BESS rows in reserve_eligibility.csv."""

BESS_SPINNING_ELIGIBLE: bool = True
"""BESS units are always spinning-eligible (can respond within 10 minutes
when online or on standby)."""

BESS_NON_SPINNING_ELIGIBLE: bool = True
"""BESS units are always non-spinning-eligible (can respond instantaneously
from idle state -- zero startup time)."""

SOC_NOTE_TEXT: str = (
    "Actual reserve availability depends on SoC: "
    "max_up_reserve <= (max_soc - current_soc) * energy_mwh / delivery_window_hr; "
    "max_down_reserve <= (current_soc - min_soc) * energy_mwh / delivery_window_hr. "
    "Tools must enforce SoC-dependent limits dynamically."
)
"""Documentation note appended to BESS rows in reserve_eligibility.csv.

Explains that the static max_spinning_mw and max_non_spinning_mw values
represent power-capacity limits, not energy-availability limits. The actual
available reserve in any hour is further constrained by the BESS unit's
current SoC and the delivery window duration.
"""


# --- BESS eligibility row ---


@dataclass(frozen=True)
class BessReserveEligibilityRow:
    """A BESS unit's reserve eligibility determination.

    Extends the Phase 2 D5 ReserveEligibilityRow schema with a soc_note
    field. When written to CSV, the first 7 columns match the Phase 2
    schema exactly; the soc_note is an additional 8th column.
    """

    gen_uid: str  # BESS unit_id, e.g., "BESS_SMALL_001"
    tech_class: str  # always "bess"
    fuel_type: str  # always "storage"
    spinning_eligible: bool  # always True
    non_spinning_eligible: bool  # always True
    max_spinning_mw: float  # min(power_mw, ramp_rate * 10 min)
    max_non_spinning_mw: float  # power_mw (zero startup time)
    soc_note: str  # SOC_NOTE_TEXT or empty string


# --- Adequacy comparison ---


@dataclass(frozen=True)
class AdequacyComparison:
    """Before-and-after comparison of reserve adequacy when BESS is added.

    Captures the pre-BESS (thermal-only) and post-BESS (thermal + BESS)
    adequacy ratios for a single reserve product in a single network.
    """

    product: str  # "spinning" or "non_spinning"
    pre_bess_eligible_mw: float  # sum of thermal max_{product}_mw
    post_bess_eligible_mw: float  # thermal + BESS max_{product}_mw
    bess_contribution_mw: float  # BESS-only max_{product}_mw
    requirement_mw: float  # from Phase 2 D4
    pre_bess_ratio: float  # pre_bess_eligible_mw / requirement_mw
    post_bess_ratio: float  # post_bess_eligible_mw / requirement_mw
    ratio_improvement: float  # post_bess_ratio - pre_bess_ratio
    bess_fraction_of_eligible: float  # bess_contribution_mw / post_bess_eligible_mw
    is_adequate: bool  # post_bess_eligible_mw > requirement_mw


# --- Network result ---


@dataclass(frozen=True)
class BessReserveIntegrationResult:
    """Complete result of BESS reserve eligibility integration for one network.

    Contains the BESS eligibility rows, adequacy comparisons, and
    summary statistics.
    """

    network_id: BessReserveNetworkId
    bess_unit_count: int
    thermal_row_count: int  # rows from Phase 2 D5
    total_row_count: int  # thermal + BESS
    bess_eligibility_rows: list[BessReserveEligibilityRow]
    total_bess_spinning_mw: float
    total_bess_non_spinning_mw: float
    spinning_adequacy: AdequacyComparison
    non_spinning_adequacy: AdequacyComparison
    output_csv_path: str  # relative path to written CSV
    warnings: list[str]


@dataclass(frozen=True)
class BessReserveIntegrationSummary:
    """Top-level summary of BESS reserve integration across all networks.

    Returned by the main entry point for logging and CI consumption.
    """

    network_results: list[BessReserveIntegrationResult]
    script_version: str


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def load_bess_units(
    bess_units_csv_path: Path,
) -> list[BessUnit]:
    """Load BESS unit definitions from the Phase 3 D2 output CSV.

    Reads bess_units.csv and parses each row into a BessUnit dataclass.
    Required columns: unit_id, bus, power_mw, energy_mwh, duration_hr,
    charge_eff, discharge_eff, roundtrip_eff, min_soc_pct, max_soc_pct,
    initial_soc_pct, ramp_rate_mw_per_min, cyclic_soc.

    Args:
        bess_units_csv_path: Path to
            data/timeseries/<network>/bess_units.csv.

    Returns:
        A list of BessUnit records, one per BESS unit, in file order.

    Raises:
        FileNotFoundError: If bess_units_csv_path does not exist.
        ValueError: If required columns are missing or the file
            contains no data rows.
    """
    if not bess_units_csv_path.exists():
        msg = f"BESS units file not found: {bess_units_csv_path}"
        raise FileNotFoundError(msg)

    text = bess_units_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    required_columns = {
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

    if reader.fieldnames is None:
        msg = f"BESS units file has no header: {bess_units_csv_path}"
        raise ValueError(msg)

    missing = required_columns - set(reader.fieldnames)
    if missing:
        msg = f"BESS units file missing columns: {sorted(missing)}"
        raise ValueError(msg)

    units: list[BessUnit] = []
    for row in reader:
        cyclic_str = row["cyclic_soc"].strip().lower()
        units.append(
            BessUnit(
                unit_id=row["unit_id"].strip(),
                bus=int(row["bus"]),
                power_mw=float(row["power_mw"]),
                energy_mwh=float(row["energy_mwh"]),
                duration_hr=float(row["duration_hr"]),
                charge_eff=float(row["charge_eff"]),
                discharge_eff=float(row["discharge_eff"]),
                roundtrip_eff=float(row["roundtrip_eff"]),
                min_soc_pct=float(row["min_soc_pct"]),
                max_soc_pct=float(row["max_soc_pct"]),
                initial_soc_pct=float(row["initial_soc_pct"]),
                ramp_rate_mw_per_min=float(row["ramp_rate_mw_per_min"]),
                cyclic_soc=cyclic_str == "true",
            )
        )

    if not units:
        msg = f"BESS units file contains no data rows: {bess_units_csv_path}"
        raise ValueError(msg)

    return units


def load_existing_eligibility(
    eligibility_csv_path: Path,
) -> list[ReserveEligibilityRow]:
    """Load the existing Phase 2 D5 reserve eligibility CSV.

    Reads reserve_eligibility.csv and parses each row into a
    ReserveEligibilityRow. These are the thermal/hydro/renewable
    generator rows that BESS rows will be appended to.

    The soc_note column may or may not be present in the Phase 2 D5
    output (it was not defined in the original D5 schema). If absent,
    an empty string is used for each row's soc_note.

    Args:
        eligibility_csv_path: Path to
            data/timeseries/<network>/reserve_eligibility.csv.

    Returns:
        A list of ReserveEligibilityRow, one per generator, in file
        order. BESS rows from a prior run of this script (if any) are
        filtered out to ensure idempotency.

    Raises:
        FileNotFoundError: If eligibility_csv_path does not exist.
        ValueError: If required columns are missing or the file
            contains no data rows.
    """
    if not eligibility_csv_path.exists():
        msg = f"Eligibility file not found: {eligibility_csv_path}"
        raise FileNotFoundError(msg)

    text = eligibility_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    required_columns = set(OUTPUT_CSV_COLUMNS)
    if reader.fieldnames is None:
        msg = f"Eligibility file has no header: {eligibility_csv_path}"
        raise ValueError(msg)

    missing = required_columns - set(reader.fieldnames)
    if missing:
        msg = f"Eligibility file missing columns: {sorted(missing)}"
        raise ValueError(msg)

    rows: list[ReserveEligibilityRow] = []
    for row in reader:
        # Filter out prior BESS rows for idempotency
        tech_class = row["tech_class"].strip()
        if tech_class == BESS_TECH_CLASS:
            continue

        spinning_str = row["spinning_eligible"].strip().lower()
        non_spinning_str = row["non_spinning_eligible"].strip().lower()

        rows.append(
            ReserveEligibilityRow(
                gen_uid=row["gen_uid"].strip(),
                tech_class=tech_class,
                fuel_type=row["fuel_type"].strip(),
                spinning_eligible=spinning_str == "true",
                non_spinning_eligible=non_spinning_str == "true",
                max_spinning_mw=float(row["max_spinning_mw"]),
                max_non_spinning_mw=float(row["max_non_spinning_mw"]),
            )
        )

    if not rows:
        msg = f"Eligibility file contains no non-BESS data rows: {eligibility_csv_path}"
        raise ValueError(msg)

    return rows


def load_reserve_requirement(
    reserve_req_csv_path: Path,
    product: str,
) -> float:
    """Load the reserve requirement for a single product from Phase 2 D4.

    Reads reserve_requirements_24h.csv, finds the row matching the
    given product name ("spinning" or "non_spinning"), and returns
    the requirement MW value. Since the profile is constant across
    hours, the HR_1 column value is used.

    Args:
        reserve_req_csv_path: Path to
            data/timeseries/<network>/reserve_requirements_24h.csv.
        product: Product name string ("spinning" or "non_spinning").

    Returns:
        The reserve requirement in MW.

    Raises:
        FileNotFoundError: If reserve_req_csv_path does not exist.
        ValueError: If the product is not found in the CSV.
    """
    if not reserve_req_csv_path.exists():
        msg = f"Reserve requirements file not found: {reserve_req_csv_path}"
        raise FileNotFoundError(msg)

    text = reserve_req_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    for row in reader:
        if row["Product"].strip() == product:
            return float(row["HR_1"])

    msg = f"Product '{product}' not found in {reserve_req_csv_path}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# BESS reserve computation
# ---------------------------------------------------------------------------


def compute_bess_max_spinning_mw(
    power_mw: float,
    ramp_rate_mw_per_min: float,
) -> float:
    """Compute maximum spinning reserve contribution for a BESS unit.

    For BESS:
        max_spinning_mw = min(power_mw, ramp_rate_mw_per_min * 10)

    Uses the same 10-minute delivery window formula as thermal
    generators in Phase 2 D5. In practice, BESS ramp rates are
    typically fast enough that the result equals power_mw (ramp
    capacity exceeds power capacity). The min() operation is retained
    for generality and consistency with the thermal formula.

    Args:
        power_mw: BESS power rating in MW (symmetric charge/discharge).
        ramp_rate_mw_per_min: BESS ramp rate from D2 output, in MW
            per minute.

    Returns:
        The maximum spinning reserve contribution in MW.
    """
    ramp_capacity = ramp_rate_mw_per_min * SPINNING_RAMP_WINDOW_MIN
    return min(power_mw, ramp_capacity)


def compute_bess_max_non_spinning_mw(
    power_mw: float,
) -> float:
    """Compute maximum non-spinning reserve contribution for a BESS unit.

    For BESS:
        max_non_spinning_mw = power_mw

    BESS has zero startup time -- it can respond instantaneously from
    idle state. There is no startup-time gate (unlike thermal generators
    in Phase 2 D5 which require startup_time_hr <= 0.5). The full
    power capacity is available as non-spinning reserve.

    Args:
        power_mw: BESS power rating in MW.

    Returns:
        The maximum non-spinning reserve contribution in MW (equal
        to power_mw).
    """
    return power_mw


# ---------------------------------------------------------------------------
# Eligibility row construction
# ---------------------------------------------------------------------------


def build_bess_eligibility_row(
    bess_unit: BessUnit,
) -> BessReserveEligibilityRow:
    """Construct a reserve eligibility row for a single BESS unit.

    Orchestrates the full eligibility determination: computes MW
    limits using compute_bess_max_spinning_mw and
    compute_bess_max_non_spinning_mw, then packages the result
    into a BessReserveEligibilityRow with the standard BESS
    constants (tech_class, fuel_type, eligibility flags) and the
    SoC documentation note.

    Args:
        bess_unit: A BessUnit from D2's bess_units.csv.

    Returns:
        A BessReserveEligibilityRow with eligibility flags and
        MW limits.
    """
    max_spinning = compute_bess_max_spinning_mw(
        bess_unit.power_mw,
        bess_unit.ramp_rate_mw_per_min,
    )
    max_non_spinning = compute_bess_max_non_spinning_mw(bess_unit.power_mw)

    return BessReserveEligibilityRow(
        gen_uid=bess_unit.unit_id,
        tech_class=BESS_TECH_CLASS,
        fuel_type=BESS_FUEL_TYPE,
        spinning_eligible=BESS_SPINNING_ELIGIBLE,
        non_spinning_eligible=BESS_NON_SPINNING_ELIGIBLE,
        max_spinning_mw=max_spinning,
        max_non_spinning_mw=max_non_spinning,
        soc_note=SOC_NOTE_TEXT,
    )


def build_all_bess_eligibility_rows(
    bess_units: list[BessUnit],
) -> list[BessReserveEligibilityRow]:
    """Construct reserve eligibility rows for all BESS units in a network.

    Calls build_bess_eligibility_row for each unit and returns the
    results sorted by gen_uid (unit_id) for deterministic output
    ordering.

    Args:
        bess_units: All BESS units from D2's bess_units.csv.

    Returns:
        A list of BessReserveEligibilityRow, sorted by gen_uid.

    Raises:
        ValueError: If bess_units is empty.
    """
    if not bess_units:
        msg = "bess_units must not be empty"
        raise ValueError(msg)

    rows = [build_bess_eligibility_row(u) for u in bess_units]
    rows.sort(key=lambda r: r.gen_uid)
    return rows


# ---------------------------------------------------------------------------
# Merge and write
# ---------------------------------------------------------------------------


EXTENDED_OUTPUT_CSV_COLUMNS: tuple[str, ...] = (
    "gen_uid",
    "tech_class",
    "fuel_type",
    "spinning_eligible",
    "non_spinning_eligible",
    "max_spinning_mw",
    "max_non_spinning_mw",
    "soc_note",
)
"""Canonical column order for the updated reserve_eligibility.csv.

Extends Phase 2 D5's OUTPUT_CSV_COLUMNS with the soc_note column.
The first 7 columns are identical to Phase 2 D5's schema.
"""


def merge_eligibility_rows(
    thermal_rows: list[ReserveEligibilityRow],
    bess_rows: list[BessReserveEligibilityRow],
) -> list[BessReserveEligibilityRow]:
    """Merge thermal generator and BESS eligibility rows.

    Thermal rows are converted to BessReserveEligibilityRow with an
    empty soc_note field, then BESS rows are appended. The original
    ordering of thermal rows is preserved; BESS rows appear at the
    end sorted by gen_uid.

    Args:
        thermal_rows: Existing thermal/hydro/renewable eligibility
            rows from Phase 2 D5.
        bess_rows: BESS eligibility rows from build_all_bess_eligibility_rows.

    Returns:
        A combined list with thermal rows first, then BESS rows.
    """
    combined: list[BessReserveEligibilityRow] = []

    # Convert thermal rows to BessReserveEligibilityRow with empty soc_note
    for tr in thermal_rows:
        combined.append(
            BessReserveEligibilityRow(
                gen_uid=tr.gen_uid,
                tech_class=tr.tech_class,
                fuel_type=tr.fuel_type,
                spinning_eligible=tr.spinning_eligible,
                non_spinning_eligible=tr.non_spinning_eligible,
                max_spinning_mw=tr.max_spinning_mw,
                max_non_spinning_mw=tr.max_non_spinning_mw,
                soc_note="",
            )
        )

    # Append BESS rows (already sorted by gen_uid)
    combined.extend(bess_rows)

    return combined


def write_combined_eligibility_csv(
    combined_rows: list[BessReserveEligibilityRow],
    dest_path: Path,
) -> None:
    """Write the combined (thermal + BESS) reserve eligibility CSV.

    Produces a CSV with one row per resource (generator or BESS unit)
    and columns in the order defined by EXTENDED_OUTPUT_CSV_COLUMNS.

    Boolean columns are written as lowercase "true" or "false".
    MW columns are formatted to 2 decimal places. The soc_note column
    is empty for thermal generators and contains SOC_NOTE_TEXT for
    BESS rows.

    Overwrites the existing reserve_eligibility.csv from Phase 2 D5.
    Parent directories are created if they do not exist.

    This function is idempotent: writing the same combined rows
    twice produces byte-identical output.

    Args:
        combined_rows: Ordered list of eligibility rows to write.
        dest_path: File path to write the CSV.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXTENDED_OUTPUT_CSV_COLUMNS)

    for row in combined_rows:
        writer.writerow(
            [
                row.gen_uid,
                row.tech_class,
                row.fuel_type,
                "true" if row.spinning_eligible else "false",
                "true" if row.non_spinning_eligible else "false",
                f"{row.max_spinning_mw:.2f}",
                f"{row.max_non_spinning_mw:.2f}",
                row.soc_note,
            ]
        )

    dest_path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Adequacy cross-check
# ---------------------------------------------------------------------------


def _compute_single_adequacy(
    product: str,
    thermal_rows: list[ReserveEligibilityRow],
    bess_rows: list[BessReserveEligibilityRow],
    requirement_mw: float,
    spinning: bool,
) -> AdequacyComparison:
    """Compute adequacy comparison for a single reserve product.

    Args:
        product: Product name ("spinning" or "non_spinning").
        thermal_rows: Thermal/hydro/renewable eligibility rows.
        bess_rows: BESS eligibility rows.
        requirement_mw: Reserve requirement in MW.
        spinning: If True, use max_spinning_mw; else max_non_spinning_mw.

    Returns:
        An AdequacyComparison for the product.
    """
    if spinning:
        pre_mw = sum(r.max_spinning_mw for r in thermal_rows if r.spinning_eligible)
        bess_mw = sum(r.max_spinning_mw for r in bess_rows)
    else:
        pre_mw = sum(r.max_non_spinning_mw for r in thermal_rows if r.non_spinning_eligible)
        bess_mw = sum(r.max_non_spinning_mw for r in bess_rows)

    post_mw = pre_mw + bess_mw

    if requirement_mw == 0.0:
        pre_ratio = float("inf")
        post_ratio = float("inf")
    else:
        pre_ratio = pre_mw / requirement_mw
        post_ratio = post_mw / requirement_mw

    ratio_improvement = post_ratio - pre_ratio
    bess_fraction = bess_mw / post_mw if post_mw > 0 else 0.0

    return AdequacyComparison(
        product=product,
        pre_bess_eligible_mw=pre_mw,
        post_bess_eligible_mw=post_mw,
        bess_contribution_mw=bess_mw,
        requirement_mw=requirement_mw,
        pre_bess_ratio=pre_ratio,
        post_bess_ratio=post_ratio,
        ratio_improvement=ratio_improvement,
        bess_fraction_of_eligible=bess_fraction,
        is_adequate=post_mw > requirement_mw,
    )


def compute_adequacy_comparison(
    thermal_rows: list[ReserveEligibilityRow],
    bess_rows: list[BessReserveEligibilityRow],
    spinning_requirement_mw: float,
    non_spinning_requirement_mw: float,
) -> tuple[AdequacyComparison, AdequacyComparison]:
    """Compute before-and-after adequacy comparison for BESS integration.

    Sums max_spinning_mw and max_non_spinning_mw across thermal rows
    (pre-BESS baseline) and across thermal + BESS rows (post-BESS).
    Computes the adequacy ratio for each and the improvement.

    If requirement_mw is zero (degenerate case), ratios are set to
    float('inf') and is_adequate is True.

    Args:
        thermal_rows: Phase 2 D5 thermal/hydro/renewable eligibility rows.
        bess_rows: BESS eligibility rows from this deliverable.
        spinning_requirement_mw: Spinning reserve requirement from D4.
        non_spinning_requirement_mw: Non-spinning reserve requirement
            from D4.

    Returns:
        A tuple of (spinning_comparison, non_spinning_comparison).
    """
    spinning = _compute_single_adequacy(
        product=ReserveProduct.SPINNING.value,
        thermal_rows=thermal_rows,
        bess_rows=bess_rows,
        requirement_mw=spinning_requirement_mw,
        spinning=True,
    )

    non_spinning = _compute_single_adequacy(
        product=ReserveProduct.NON_SPINNING.value,
        thermal_rows=thermal_rows,
        bess_rows=bess_rows,
        requirement_mw=non_spinning_requirement_mw,
        spinning=False,
    )

    return spinning, non_spinning


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


BESS_UNITS_FILE: str = "bess_units.csv"
"""Name of the D2 BESS unit definitions CSV within each network directory."""

RESERVE_ELIGIBILITY_FILE: str = "reserve_eligibility.csv"
"""Name of the Phase 2 D5 eligibility CSV (input and output)."""

RESERVE_REQUIREMENTS_FILE: str = "reserve_requirements_24h.csv"
"""Name of the Phase 2 D4 reserve requirements CSV."""


def process_network(
    network_id: BessReserveNetworkId,
    bess_units_csv_path: Path,
    eligibility_csv_path: Path,
    reserve_req_csv_path: Path,
    output_dir: Path,
) -> BessReserveIntegrationResult:
    """Run the full BESS reserve integration pipeline for a single network.

    Steps:
    1. Load BESS unit definitions from D2's bess_units.csv.
    2. Load existing thermal eligibility rows from D5's reserve_eligibility.csv.
    3. Build BESS eligibility rows with computed MW limits.
    4. Load reserve requirements from D4's reserve_requirements_24h.csv.
    5. Compute before-and-after adequacy comparison.
    6. Merge thermal and BESS rows.
    7. Write the combined eligibility CSV (overwriting the D5 output).
    8. Return the integration result with summary statistics.

    The function filters out any existing BESS rows in the eligibility
    CSV before appending new ones, ensuring idempotent execution.

    Args:
        network_id: Which network to process (SMALL or MEDIUM).
        bess_units_csv_path: Path to D2's bess_units.csv.
        eligibility_csv_path: Path to D5's reserve_eligibility.csv
            (read as input, then overwritten with combined output).
        reserve_req_csv_path: Path to D4's reserve_requirements_24h.csv.
        output_dir: Directory to write the updated reserve_eligibility.csv.

    Returns:
        A BessReserveIntegrationResult with BESS rows, adequacy
        comparisons, and warnings.

    Raises:
        FileNotFoundError: If any input CSV does not exist.
        ValueError: If BESS units CSV is empty or has missing columns.
    """
    # 1. Load BESS units
    bess_units = load_bess_units(bess_units_csv_path)

    # 2. Load existing thermal eligibility (filters out prior BESS rows)
    thermal_rows = load_existing_eligibility(eligibility_csv_path)

    # 3. Build BESS eligibility rows
    bess_rows = build_all_bess_eligibility_rows(bess_units)

    # 4. Load reserve requirements
    spinning_req = load_reserve_requirement(reserve_req_csv_path, ReserveProduct.SPINNING.value)
    non_spinning_req = load_reserve_requirement(
        reserve_req_csv_path, ReserveProduct.NON_SPINNING.value
    )

    # 5. Compute adequacy comparison
    spinning_adequacy, non_spinning_adequacy = compute_adequacy_comparison(
        thermal_rows, bess_rows, spinning_req, non_spinning_req
    )

    # 6. Merge rows
    combined = merge_eligibility_rows(thermal_rows, bess_rows)

    # 7. Write combined CSV
    output_csv_path = output_dir / RESERVE_ELIGIBILITY_FILE
    write_combined_eligibility_csv(combined, output_csv_path)

    # 8. Build result with warnings
    warnings: list[str] = []

    # Warn if BESS contribution is negligible (< 1 percentage point improvement)
    if spinning_adequacy.ratio_improvement < 0.01:
        warn_msg = (
            f"BESS spinning reserve contribution is negligible for {network_id.value}: "
            f"adequacy ratio improved by only {spinning_adequacy.ratio_improvement:.4f} "
            f"({spinning_adequacy.ratio_improvement * 100:.2f} percentage points)"
        )
        logger.warning(warn_msg)
        warnings.append(warn_msg)

    if non_spinning_adequacy.ratio_improvement < 0.01:
        warn_msg = (
            f"BESS non-spinning reserve contribution is negligible for {network_id.value}: "
            f"adequacy ratio improved by only {non_spinning_adequacy.ratio_improvement:.4f} "
            f"({non_spinning_adequacy.ratio_improvement * 100:.2f} percentage points)"
        )
        logger.warning(warn_msg)
        warnings.append(warn_msg)

    if not spinning_adequacy.is_adequate:
        warn_msg = (
            f"Spinning reserve inadequate for {network_id.value} even with BESS: "
            f"eligible capacity {spinning_adequacy.post_bess_eligible_mw:.2f} MW "
            f"<= requirement {spinning_adequacy.requirement_mw:.2f} MW"
        )
        logger.warning(warn_msg)
        warnings.append(warn_msg)

    if not non_spinning_adequacy.is_adequate:
        warn_msg = (
            f"Non-spinning reserve inadequate for {network_id.value} even with BESS: "
            f"eligible capacity {non_spinning_adequacy.post_bess_eligible_mw:.2f} MW "
            f"<= requirement {non_spinning_adequacy.requirement_mw:.2f} MW"
        )
        logger.warning(warn_msg)
        warnings.append(warn_msg)

    total_bess_spinning = sum(r.max_spinning_mw for r in bess_rows)
    total_bess_non_spinning = sum(r.max_non_spinning_mw for r in bess_rows)

    return BessReserveIntegrationResult(
        network_id=network_id,
        bess_unit_count=len(bess_units),
        thermal_row_count=len(thermal_rows),
        total_row_count=len(combined),
        bess_eligibility_rows=bess_rows,
        total_bess_spinning_mw=total_bess_spinning,
        total_bess_non_spinning_mw=total_bess_non_spinning,
        spinning_adequacy=spinning_adequacy,
        non_spinning_adequacy=non_spinning_adequacy,
        output_csv_path=str(output_csv_path),
        warnings=warnings,
    )


NETWORK_IDS: tuple[BessReserveNetworkId, ...] = (
    BessReserveNetworkId.SMALL,
    BessReserveNetworkId.MEDIUM,
)
"""Networks to process, in order."""


def main(
    timeseries_base_dir: Path | None = None,
) -> BessReserveIntegrationSummary:
    """Entry point: integrate BESS reserve eligibility for SMALL and MEDIUM.

    Processes both networks. For each, reads the D2, D5, and D4 CSVs
    from <timeseries_base_dir>/<network_id>/ and writes the updated
    reserve_eligibility.csv back to the same directory.

    Default paths resolve relative to the repository root:
    - All input and output CSVs: data/timeseries/<network_id>/

    Args:
        timeseries_base_dir: Base directory for input and output.
            Defaults to <repo_root>/data/timeseries/.

    Returns:
        A BessReserveIntegrationSummary covering both networks.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "timeseries"

    network_results: list[BessReserveIntegrationResult] = []

    for network_id in NETWORK_IDS:
        network_dir = timeseries_base_dir / network_id.value

        bess_csv = network_dir / BESS_UNITS_FILE
        eligibility_csv = network_dir / RESERVE_ELIGIBILITY_FILE
        reserve_req_csv = network_dir / RESERVE_REQUIREMENTS_FILE

        # Check for missing files
        missing: list[str] = []
        for path, label in [
            (bess_csv, "D2 BESS units"),
            (eligibility_csv, "D5 reserve eligibility"),
            (reserve_req_csv, "D4 reserve requirements"),
        ]:
            if not path.exists():
                missing.append(f"{label}: {path}")

        if missing:
            logger.warning(
                "Skipping %s -- missing files: %s",
                network_id.value,
                "; ".join(missing),
            )
            continue

        result = process_network(
            network_id=network_id,
            bess_units_csv_path=bess_csv,
            eligibility_csv_path=eligibility_csv,
            reserve_req_csv_path=reserve_req_csv,
            output_dir=network_dir,
        )
        network_results.append(result)

    summary = BessReserveIntegrationSummary(
        network_results=network_results,
        script_version=__version__,
    )

    print_summary(summary)
    return summary


def print_summary(summary: BessReserveIntegrationSummary) -> None:
    """Print a human-readable summary of the BESS reserve integration.

    Lists each network with: BESS unit count, total BESS spinning and
    non-spinning MW, pre/post-BESS adequacy ratios for each product,
    and the BESS fraction of total eligible capacity. Flags any
    networks where the BESS contribution improves the adequacy ratio
    by less than 1 percentage point (indicating a negligibly small
    BESS fleet relative to reserve requirements).

    Args:
        summary: The top-level integration summary.
    """
    print("=" * 72)
    print("BESS Reserve Eligibility Integration Summary")
    print("=" * 72)
    print(f"Script version: {summary.script_version}")
    print()

    for nr in summary.network_results:
        print(f"Network: {nr.network_id.value}")
        print(f"  BESS units added: {nr.bess_unit_count}")
        print(f"  Thermal rows (from D5): {nr.thermal_row_count}")
        print(f"  Total rows (combined): {nr.total_row_count}")
        print(f"  Total BESS spinning MW: {nr.total_bess_spinning_mw:.2f}")
        print(f"  Total BESS non-spinning MW: {nr.total_bess_non_spinning_mw:.2f}")
        print()

        for adq in (nr.spinning_adequacy, nr.non_spinning_adequacy):
            label = adq.product.replace("_", "-")
            print(f"  {label} reserve adequacy:")
            print(
                f"    Pre-BESS:  {adq.pre_bess_eligible_mw:.2f} MW "
                f"(ratio {adq.pre_bess_ratio:.3f}x)"
            )
            print(
                f"    Post-BESS: {adq.post_bess_eligible_mw:.2f} MW "
                f"(ratio {adq.post_bess_ratio:.3f}x)"
            )
            print(
                f"    BESS contribution: {adq.bess_contribution_mw:.2f} MW "
                f"({adq.bess_fraction_of_eligible:.1%} of eligible)"
            )
            print(
                f"    Improvement: {adq.ratio_improvement:.4f} "
                f"({'ADEQUATE' if adq.is_adequate else 'INADEQUATE'})"
            )
            if adq.ratio_improvement < 0.01:
                print("    ** BESS contribution is negligible (<1 ppt improvement)")
            print()

        print(f"  Output: {nr.output_csv_path}")

        if nr.warnings:
            print(f"  Warnings ({len(nr.warnings)}):")
            for w in nr.warnings:
                print(f"    - {w}")
        print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
