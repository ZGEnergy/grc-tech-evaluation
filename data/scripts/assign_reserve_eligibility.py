"""Reserve Eligibility Assignment for MATPOWER test networks.

Assigns reserve eligibility flags to every generator in TINY (case39),
SMALL (ACTIVSg2000), and MEDIUM (ACTIVSg10k) networks based on technology
class. Eligibility is a static property of the generator's technology --
whether a generator *provides* reserves in a given hour is decided by the
SCUC optimizer, but the optimizer needs the eligibility boundary up front.

For spinning reserve, the generator must be online and able to ramp within
10 minutes: max_spinning_mw = min(pmax_mw, ramp_rate_mw_per_min * 10).
For non-spinning reserve, the generator must start within 30 minutes:
max_non_spinning_mw = pmax_mw if startup_time_hr <= 0.5, else 0.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.assign_temporal_params import TemporalParamRow
from scripts.classify_gen_fuel import GenFuelClassificationRow
from scripts.define_reserves import ReserveProduct

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class EligibilityNetworkId(StrEnum):
    """Identifiers for the three test networks."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


@dataclass(frozen=True)
class TechClassEligibility:
    """Eligibility flags for a single technology class."""

    tech_class: str
    spinning_eligible: bool
    non_spinning_eligible: bool


TECH_CLASS_ELIGIBILITY: dict[str, TechClassEligibility] = {
    "coal_small": TechClassEligibility(
        "coal_small", spinning_eligible=True, non_spinning_eligible=False
    ),
    "coal_medium": TechClassEligibility(
        "coal_medium", spinning_eligible=True, non_spinning_eligible=False
    ),
    "coal_large": TechClassEligibility(
        "coal_large", spinning_eligible=True, non_spinning_eligible=False
    ),
    "gas_CT_small": TechClassEligibility(
        "gas_CT_small", spinning_eligible=True, non_spinning_eligible=True
    ),
    "gas_CT_large": TechClassEligibility(
        "gas_CT_large", spinning_eligible=True, non_spinning_eligible=True
    ),
    "gas_CC": TechClassEligibility("gas_CC", spinning_eligible=True, non_spinning_eligible=False),
    "gas_CC_large": TechClassEligibility(
        "gas_CC_large", spinning_eligible=True, non_spinning_eligible=False
    ),
    "gas_STEAM": TechClassEligibility(
        "gas_STEAM", spinning_eligible=True, non_spinning_eligible=False
    ),
    "oil_CT": TechClassEligibility("oil_CT", spinning_eligible=True, non_spinning_eligible=True),
    "nuclear": TechClassEligibility(
        "nuclear", spinning_eligible=False, non_spinning_eligible=False
    ),
    "hydro": TechClassEligibility("hydro", spinning_eligible=True, non_spinning_eligible=True),
    "wind": TechClassEligibility("wind", spinning_eligible=False, non_spinning_eligible=False),
    "solar": TechClassEligibility("solar", spinning_eligible=False, non_spinning_eligible=False),
    "bess": TechClassEligibility("bess", spinning_eligible=True, non_spinning_eligible=True),
}

SPINNING_RAMP_WINDOW_MIN: float = 10.0
NON_SPINNING_STARTUP_THRESHOLD_HR: float = 0.5


@dataclass(frozen=True)
class ReserveEligibilityRow:
    """Reserve eligibility result for a single generator."""

    gen_uid: str
    tech_class: str
    fuel_type: str
    spinning_eligible: bool
    non_spinning_eligible: bool
    max_spinning_mw: float
    max_non_spinning_mw: float


@dataclass(frozen=True)
class AdequacyCheckResult:
    """Result of a reserve adequacy cross-check for one product."""

    product: str
    requirement_mw: float
    eligible_capacity_mw: float
    eligible_generator_count: int
    adequacy_ratio: float
    is_adequate: bool


@dataclass(frozen=True)
class NetworkEligibilityResult:
    """Complete eligibility result for a single network."""

    network_id: EligibilityNetworkId
    generator_count: int
    eligibility_rows: list[ReserveEligibilityRow]
    spinning_eligible_count: int
    non_spinning_eligible_count: int
    total_spinning_eligible_mw: float
    total_non_spinning_eligible_mw: float
    spinning_adequacy: AdequacyCheckResult
    non_spinning_adequacy: AdequacyCheckResult
    output_csv_path: str
    warnings: list[str]


@dataclass(frozen=True)
class EligibilityAssignmentSummary:
    """Top-level summary across all networks."""

    network_results: list[NetworkEligibilityResult]
    script_version: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_CSV_COLUMNS: tuple[str, ...] = (
    "gen_uid",
    "tech_class",
    "fuel_type",
    "spinning_eligible",
    "non_spinning_eligible",
    "max_spinning_mw",
    "max_non_spinning_mw",
)

NETWORK_IDS: tuple[EligibilityNetworkId, ...] = (
    EligibilityNetworkId.TINY,
    EligibilityNetworkId.SMALL,
    EligibilityNetworkId.MEDIUM,
)

CLASSIFICATION_FILE: str = "gen_fuel_classification.csv"
TEMPORAL_PARAMS_FILE: str = "gen_temporal_params.csv"
RESERVE_REQUIREMENTS_FILE: str = "reserve_requirements_24h.csv"
OUTPUT_FILE: str = "reserve_eligibility.csv"


# ---------------------------------------------------------------------------
# Loading functions
# ---------------------------------------------------------------------------


def load_classification(classification_csv_path: Path) -> list[GenFuelClassificationRow]:
    """Load generator fuel classification CSV produced by D2.

    Args:
        classification_csv_path: Path to the gen_fuel_classification.csv file.

    Returns:
        A list of GenFuelClassificationRow, one per generator.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not classification_csv_path.exists():
        msg = f"Classification file not found: {classification_csv_path}"
        raise FileNotFoundError(msg)

    from scripts.build_rts_gmlc_reference import FuelType
    from scripts.classify_gen_fuel import (
        CapacityBand,
        ClassificationSource,
        ConfidenceLevel,
        GasUnitType,
    )

    text = classification_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[GenFuelClassificationRow] = []

    for row in reader:
        gas_unit_type_str = row.get("gas_unit_type", "").strip()
        gas_unit_type = GasUnitType(gas_unit_type_str) if gas_unit_type_str else None

        rows.append(
            GenFuelClassificationRow(
                gen_index=int(row["gen_index"]),
                gen_bus=int(row["gen_bus"]),
                gen_uid=row["gen_uid"].strip(),
                fuel_type=FuelType(row["fuel_type"].strip()),
                gas_unit_type=gas_unit_type,
                unit_type=row["unit_type"].strip(),
                capacity_band=CapacityBand(row["capacity_band"].strip()),
                tech_class=row["tech_class"].strip(),
                pmax_mw=float(row["pmax_mw"]),
                pmin_mw=float(row["pmin_mw"]),
                source=ClassificationSource(row["source"].strip()),
                confidence=ConfidenceLevel(row["confidence"].strip()),
            )
        )

    return rows


def load_temporal_params(temporal_params_csv_path: Path) -> list[TemporalParamRow]:
    """Load generator temporal parameters CSV produced by D3.

    Args:
        temporal_params_csv_path: Path to the gen_temporal_params.csv file.

    Returns:
        A list of TemporalParamRow, one per generator.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not temporal_params_csv_path.exists():
        msg = f"Temporal params file not found: {temporal_params_csv_path}"
        raise FileNotFoundError(msg)

    text = temporal_params_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[TemporalParamRow] = []

    for row in reader:
        rows.append(
            TemporalParamRow(
                gen_uid=row["gen_uid"].strip(),
                pmax_mw=float(row["pmax_mw"]),
                pmin_mw=float(row["pmin_mw"]),
                ramp_rate_mw_per_min=float(row["ramp_rate_mw_per_min"]),
                ramp_rate_mw_per_hr=float(row["ramp_rate_mw_per_hr"]),
                min_up_time_hr=float(row["min_up_time_hr"]),
                min_down_time_hr=float(row["min_down_time_hr"]),
                startup_cost_dollar=float(row["startup_cost_dollar"]),
                startup_time_hr=float(row["startup_time_hr"]),
                shutdown_cost_dollar=float(row["shutdown_cost_dollar"]),
                tech_class=row["tech_class"].strip(),
                fuel_type=row["fuel_type"].strip(),
            )
        )

    return rows


def load_reserve_requirement(reserve_req_csv_path: Path, product: str) -> float:
    """Load the reserve requirement for a specific product from the D4 CSV.

    The D4 CSV has columns: Product, HR_1..HR_24, sizing_basis, etc.
    Since the requirement is constant across all hours, we read HR_1.

    Args:
        reserve_req_csv_path: Path to the reserve_requirements_24h.csv file.
        product: The reserve product string (e.g., "spinning", "non_spinning").

    Returns:
        The reserve requirement in MW.

    Raises:
        FileNotFoundError: If the file does not exist.
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
# Eligibility logic
# ---------------------------------------------------------------------------


def lookup_eligibility(tech_class: str) -> TechClassEligibility:
    """Look up eligibility flags for a technology class.

    Returns a conservative default (both flags False) for unknown classes.

    Args:
        tech_class: The technology class string (e.g., "gas_CT_small").

    Returns:
        A TechClassEligibility with the eligibility flags.
    """
    default = TechClassEligibility(
        tech_class=tech_class,
        spinning_eligible=False,
        non_spinning_eligible=False,
    )
    return TECH_CLASS_ELIGIBILITY.get(tech_class, default)


def compute_max_spinning_mw(
    pmax_mw: float,
    ramp_rate_mw_per_min: float,
    spinning_eligible: bool,
) -> float:
    """Compute the maximum spinning reserve contribution in MW.

    For spinning-eligible generators: min(pmax_mw, ramp_rate * 10 min).
    For ineligible generators: 0.0.

    Args:
        pmax_mw: Generator maximum power output (MW).
        ramp_rate_mw_per_min: Ramp rate in MW per minute.
        spinning_eligible: Whether the generator is spinning-eligible.

    Returns:
        The maximum spinning reserve MW.
    """
    if not spinning_eligible:
        return 0.0
    ramp_capacity = ramp_rate_mw_per_min * SPINNING_RAMP_WINDOW_MIN
    return min(pmax_mw, ramp_capacity)


def compute_max_non_spinning_mw(
    pmax_mw: float,
    startup_time_hr: float,
    non_spinning_eligible: bool,
) -> float:
    """Compute the maximum non-spinning reserve contribution in MW.

    For non-spinning-eligible generators with startup_time_hr <= 0.5: pmax_mw.
    Otherwise: 0.0.

    Args:
        pmax_mw: Generator maximum power output (MW).
        startup_time_hr: Generator startup time in hours.
        non_spinning_eligible: Whether the generator is non-spinning-eligible.

    Returns:
        The maximum non-spinning reserve MW.
    """
    if not non_spinning_eligible:
        return 0.0
    if startup_time_hr <= NON_SPINNING_STARTUP_THRESHOLD_HR:
        return pmax_mw
    return 0.0


def assign_eligibility(
    classification: GenFuelClassificationRow,
    temporal_params: TemporalParamRow,
) -> ReserveEligibilityRow:
    """Assign reserve eligibility to a single generator.

    Joins the D2 classification with D3 temporal parameters to produce
    eligibility flags and MW limits.

    Args:
        classification: The generator's fuel classification from D2.
        temporal_params: The generator's temporal parameters from D3.

    Returns:
        A ReserveEligibilityRow with eligibility flags and MW limits.

    Raises:
        ValueError: If the gen_uid does not match between classification
            and temporal_params.
    """
    if classification.gen_uid != temporal_params.gen_uid:
        msg = (
            f"gen_uid mismatch: classification has '{classification.gen_uid}', "
            f"temporal_params has '{temporal_params.gen_uid}'"
        )
        raise ValueError(msg)

    eligibility = lookup_eligibility(classification.tech_class)

    max_spin = compute_max_spinning_mw(
        pmax_mw=classification.pmax_mw,
        ramp_rate_mw_per_min=temporal_params.ramp_rate_mw_per_min,
        spinning_eligible=eligibility.spinning_eligible,
    )

    max_nonspin = compute_max_non_spinning_mw(
        pmax_mw=classification.pmax_mw,
        startup_time_hr=temporal_params.startup_time_hr,
        non_spinning_eligible=eligibility.non_spinning_eligible,
    )

    return ReserveEligibilityRow(
        gen_uid=classification.gen_uid,
        tech_class=classification.tech_class,
        fuel_type=classification.fuel_type.value
        if hasattr(classification.fuel_type, "value")
        else str(classification.fuel_type),
        spinning_eligible=eligibility.spinning_eligible,
        non_spinning_eligible=eligibility.non_spinning_eligible,
        max_spinning_mw=max_spin,
        max_non_spinning_mw=max_nonspin,
    )


# ---------------------------------------------------------------------------
# Adequacy checking
# ---------------------------------------------------------------------------


def check_adequacy(
    eligibility_rows: list[ReserveEligibilityRow],
    spinning_requirement_mw: float,
    non_spinning_requirement_mw: float,
) -> tuple[AdequacyCheckResult, AdequacyCheckResult]:
    """Check whether the eligible fleet can meet reserve requirements.

    Args:
        eligibility_rows: All generator eligibility rows for a network.
        spinning_requirement_mw: The spinning reserve requirement (MW).
        non_spinning_requirement_mw: The non-spinning reserve requirement (MW).

    Returns:
        A tuple of (spinning_adequacy, non_spinning_adequacy).
    """
    spin_gens = [r for r in eligibility_rows if r.spinning_eligible]
    spin_capacity = sum(r.max_spinning_mw for r in spin_gens)
    spin_ratio = spin_capacity / spinning_requirement_mw if spinning_requirement_mw > 0 else 0.0

    nonspin_gens = [r for r in eligibility_rows if r.non_spinning_eligible]
    nonspin_capacity = sum(r.max_non_spinning_mw for r in nonspin_gens)
    nonspin_ratio = (
        nonspin_capacity / non_spinning_requirement_mw if non_spinning_requirement_mw > 0 else 0.0
    )

    spinning_adequacy = AdequacyCheckResult(
        product=ReserveProduct.SPINNING.value,
        requirement_mw=spinning_requirement_mw,
        eligible_capacity_mw=spin_capacity,
        eligible_generator_count=len(spin_gens),
        adequacy_ratio=spin_ratio,
        is_adequate=spin_capacity > spinning_requirement_mw,
    )

    non_spinning_adequacy = AdequacyCheckResult(
        product=ReserveProduct.NON_SPINNING.value,
        requirement_mw=non_spinning_requirement_mw,
        eligible_capacity_mw=nonspin_capacity,
        eligible_generator_count=len(nonspin_gens),
        adequacy_ratio=nonspin_ratio,
        is_adequate=nonspin_capacity > non_spinning_requirement_mw,
    )

    return spinning_adequacy, non_spinning_adequacy


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_eligibility_csv(
    eligibility_rows: list[ReserveEligibilityRow],
    dest_path: Path,
) -> None:
    """Write reserve eligibility to a CSV file.

    Boolean columns use lowercase "true"/"false" strings for portability.
    MW columns are formatted to 2 decimal places.

    Args:
        eligibility_rows: The eligibility rows to write.
        dest_path: File path to write the CSV output.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(OUTPUT_CSV_COLUMNS)

    for row in eligibility_rows:
        writer.writerow(
            [
                row.gen_uid,
                row.tech_class,
                row.fuel_type,
                "true" if row.spinning_eligible else "false",
                "true" if row.non_spinning_eligible else "false",
                f"{row.max_spinning_mw:.2f}",
                f"{row.max_non_spinning_mw:.2f}",
            ]
        )

    dest_path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Network processing
# ---------------------------------------------------------------------------


def process_network(
    network_id: EligibilityNetworkId,
    classification_csv_path: Path,
    temporal_params_csv_path: Path,
    reserve_req_csv_path: Path,
    output_dir: Path,
) -> NetworkEligibilityResult:
    """Process a single network: load inputs, assign eligibility, write CSV.

    Args:
        network_id: Which network to process.
        classification_csv_path: Path to the D2 classification CSV.
        temporal_params_csv_path: Path to the D3 temporal params CSV.
        reserve_req_csv_path: Path to the D4 reserve requirements CSV.
        output_dir: Directory to write the output CSV.

    Returns:
        A NetworkEligibilityResult with all eligibility data and adequacy checks.

    Raises:
        ValueError: If D2 and D3 row counts do not match.
    """
    classifications = load_classification(classification_csv_path)
    temporal_params = load_temporal_params(temporal_params_csv_path)

    if len(classifications) != len(temporal_params):
        msg = (
            f"Row count mismatch for {network_id.value}: "
            f"D2 classification has {len(classifications)} rows, "
            f"D3 temporal params has {len(temporal_params)} rows"
        )
        raise ValueError(msg)

    # Build eligibility rows
    eligibility_rows: list[ReserveEligibilityRow] = []
    for cls_row, tp_row in zip(classifications, temporal_params):
        elig_row = assign_eligibility(cls_row, tp_row)
        eligibility_rows.append(elig_row)

    # Load reserve requirements
    spinning_req = load_reserve_requirement(reserve_req_csv_path, ReserveProduct.SPINNING.value)
    non_spinning_req = load_reserve_requirement(
        reserve_req_csv_path, ReserveProduct.NON_SPINNING.value
    )

    # Adequacy checks
    spinning_adequacy, non_spinning_adequacy = check_adequacy(
        eligibility_rows, spinning_req, non_spinning_req
    )

    # Log warnings for inadequate reserves
    warnings: list[str] = []
    if not spinning_adequacy.is_adequate:
        warn_msg = (
            f"Spinning reserve inadequate for {network_id.value}: "
            f"eligible capacity {spinning_adequacy.eligible_capacity_mw:.2f} MW "
            f"<= requirement {spinning_adequacy.requirement_mw:.2f} MW "
            f"(ratio {spinning_adequacy.adequacy_ratio:.2f})"
        )
        logger.warning(warn_msg)
        warnings.append(warn_msg)

    if not non_spinning_adequacy.is_adequate:
        warn_msg = (
            f"Non-spinning reserve inadequate for {network_id.value}: "
            f"eligible capacity {non_spinning_adequacy.eligible_capacity_mw:.2f} MW "
            f"<= requirement {non_spinning_adequacy.requirement_mw:.2f} MW "
            f"(ratio {non_spinning_adequacy.adequacy_ratio:.2f})"
        )
        logger.warning(warn_msg)
        warnings.append(warn_msg)

    # Write output CSV
    output_csv_path = output_dir / OUTPUT_FILE
    write_eligibility_csv(eligibility_rows, output_csv_path)

    # Compute counts
    spinning_eligible_count = sum(1 for r in eligibility_rows if r.spinning_eligible)
    non_spinning_eligible_count = sum(1 for r in eligibility_rows if r.non_spinning_eligible)
    total_spinning_mw = sum(r.max_spinning_mw for r in eligibility_rows)
    total_non_spinning_mw = sum(r.max_non_spinning_mw for r in eligibility_rows)

    return NetworkEligibilityResult(
        network_id=network_id,
        generator_count=len(eligibility_rows),
        eligibility_rows=eligibility_rows,
        spinning_eligible_count=spinning_eligible_count,
        non_spinning_eligible_count=non_spinning_eligible_count,
        total_spinning_eligible_mw=total_spinning_mw,
        total_non_spinning_eligible_mw=total_non_spinning_mw,
        spinning_adequacy=spinning_adequacy,
        non_spinning_adequacy=non_spinning_adequacy,
        output_csv_path=str(output_csv_path),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(summary: EligibilityAssignmentSummary) -> None:
    """Print a human-readable summary of the eligibility assignment.

    Args:
        summary: The complete assignment summary.
    """
    print("=" * 72)
    print("Reserve Eligibility Assignment Summary")
    print("=" * 72)
    print(f"Script version: {summary.script_version}")
    print()

    for nr in summary.network_results:
        print(f"Network: {nr.network_id.value}")
        print(f"  Generators: {nr.generator_count}")
        print(f"  Spinning eligible: {nr.spinning_eligible_count}")
        print(f"  Non-spinning eligible: {nr.non_spinning_eligible_count}")
        print(f"  Total spinning MW: {nr.total_spinning_eligible_mw:.2f}")
        print(f"  Total non-spinning MW: {nr.total_non_spinning_eligible_mw:.2f}")
        print(
            f"  Spinning adequacy: {nr.spinning_adequacy.adequacy_ratio:.2f}x "
            f"({'ADEQUATE' if nr.spinning_adequacy.is_adequate else 'INADEQUATE'})"
        )
        print(
            f"  Non-spinning adequacy: {nr.non_spinning_adequacy.adequacy_ratio:.2f}x "
            f"({'ADEQUATE' if nr.non_spinning_adequacy.is_adequate else 'INADEQUATE'})"
        )
        print(f"  Output: {nr.output_csv_path}")
        if nr.warnings:
            print(f"  Warnings ({len(nr.warnings)}):")
            for w in nr.warnings:
                print(f"    - {w}")
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
) -> EligibilityAssignmentSummary:
    """Entry point: assign reserve eligibility for all three networks.

    Args:
        timeseries_base_dir: Base directory containing per-network subdirectories
            with D2, D3, and D4 output CSVs. Defaults to <repo_root>/data/timeseries/.

    Returns:
        The complete EligibilityAssignmentSummary.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "timeseries"

    network_results: list[NetworkEligibilityResult] = []

    for network_id in NETWORK_IDS:
        network_dir = timeseries_base_dir / network_id.value
        classification_csv = network_dir / CLASSIFICATION_FILE
        temporal_csv = network_dir / TEMPORAL_PARAMS_FILE
        reserve_req_csv = network_dir / RESERVE_REQUIREMENTS_FILE

        # Skip if input files are missing
        missing = []
        for path, label in [
            (classification_csv, "D2 classification"),
            (temporal_csv, "D3 temporal params"),
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
            classification_csv_path=classification_csv,
            temporal_params_csv_path=temporal_csv,
            reserve_req_csv_path=reserve_req_csv,
            output_dir=network_dir,
        )
        network_results.append(result)

    summary = EligibilityAssignmentSummary(
        network_results=network_results,
        script_version=__version__,
    )

    print_summary(summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
