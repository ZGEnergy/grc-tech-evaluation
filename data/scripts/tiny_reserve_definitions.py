"""Reserve Product Definitions for TINY (case39).

Defines spinning and non-spinning reserve requirements and per-generator
reserve eligibility for the 10-generator IEEE 39-bus fleet.  Reserve
requirement follows the N-1 criterion: total = Pmax of the largest
generator (1100 MW).  Phase 2b uses a 50/50 split: spinning = 550 MW,
non-spinning = 550 MW, constant across 24 hours.

Output artifacts:
  - data/timeseries/case39/reserve_requirements_24h.csv
  - data/timeseries/case39/reserve_eligibility.csv
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.tiny_cleanup_classify import (
    Case39GenClassification,
    RtsGmlcClass,
)
from scripts.tiny_gen_temporal_params import (
    GenTemporalParams,
    assign_all_temporal_params,
    build_gen_uid,
    load_gen_classification,
    load_reference_table,
)

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LARGEST_GEN_PMAX_MW: float = 1100.0
SPINNING_FRACTION: float = 0.5
NON_SPINNING_FRACTION: float = 0.5
SPINNING_REQUIREMENT_MW: float = 550.0
NON_SPINNING_REQUIREMENT_MW: float = 550.0
NUM_HOURS: int = 24
SPINNING_DEPLOYMENT_MINUTES: float = 10.0
NON_SPINNING_DEPLOYMENT_MINUTES: float = 30.0
NUCLEAR_MAX_SPINNING_PCT: float = 0.05
NUCLEAR_MAX_NON_SPINNING_PCT: float = 0.10


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ReserveProduct(StrEnum):
    SPINNING = "spinning"
    NON_SPINNING = "non_spinning"


@dataclass(frozen=True)
class ReserveRequirementProfile:
    """A single reserve product's constant 24-hour requirement."""

    reserve_type: ReserveProduct
    requirement_mw: float


@dataclass(frozen=True)
class GeneratorReserveEligibility:
    """Per-generator reserve eligibility record."""

    gen_uid: str
    gen_index: int
    bus_id: int
    fuel_type: str
    rts_gmlc_class: str
    pmax_mw: float
    ramp_rate_mw_per_hr: float
    spinning_eligible: bool
    non_spinning_eligible: bool
    max_spinning_pct: float
    max_non_spinning_pct: float


@dataclass(frozen=True)
class ReserveFeasibilityCheck:
    """Result of checking whether the fleet can meet a reserve requirement."""

    product: ReserveProduct
    requirement_mw: float
    total_eligible_capacity_mw: float
    is_feasible: bool
    margin_mw: float


@dataclass(frozen=True)
class ReserveDefinitionResult:
    """Complete result of reserve definition for the TINY fleet."""

    requirements_csv_path: str
    eligibility_csv_path: str
    spinning_requirement: ReserveRequirementProfile
    non_spinning_requirement: ReserveRequirementProfile
    eligibilities: list[GeneratorReserveEligibility]
    spinning_feasibility: ReserveFeasibilityCheck
    non_spinning_feasibility: ReserveFeasibilityCheck


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def load_gen_classification_csv(
    csv_path: Path | None = None,
) -> list[Case39GenClassification]:
    """Load the case39 generator classification table.

    Delegates to ``tiny_gen_temporal_params.load_gen_classification`` for
    CSV parsing, or returns the hardcoded table when *csv_path* is None.

    Args:
        csv_path: Optional path to gen_classification.csv.

    Returns:
        List of Case39GenClassification records.
    """
    return load_gen_classification(csv_path)


def load_gen_temporal_params(
    csv_path: Path | None = None,
    reference_csv: Path | None = None,
) -> list[GenTemporalParams]:
    """Load or compute generator temporal parameters.

    If *csv_path* is provided, reads gen_temporal_params.csv directly.
    Otherwise computes from the hardcoded classification table and the
    RTS-GMLC reference table.

    Args:
        csv_path: Optional path to gen_temporal_params.csv.
        reference_csv: Path to rts_gmlc_tech_classes.csv (used only when
            csv_path is None).

    Returns:
        List of GenTemporalParams, one per generator.
    """
    if csv_path is not None:
        if not csv_path.exists():
            msg = f"Temporal params CSV not found: {csv_path}"
            raise FileNotFoundError(msg)

        text = csv_path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))

        params: list[GenTemporalParams] = []
        for row in reader:
            params.append(
                GenTemporalParams(
                    gen_uid=row["gen_uid"],
                    gen_index=int(row["gen_index"]),
                    bus_id=int(row["bus_id"]),
                    rts_gmlc_class=row["rts_gmlc_class"],
                    tech_class_key=row["tech_class_key"],
                    pmax_mw=float(row["pmax_mw"]),
                    ramp_rate_mw_per_min=float(row["ramp_rate_mw_per_min"]),
                    ramp_rate_mw_per_hr=float(row["ramp_rate_mw_per_hr"]),
                    min_up_time_hr=float(row["min_up_time_hr"]),
                    min_down_time_hr=float(row["min_down_time_hr"]),
                    startup_cost_cold_dollar=float(row["startup_cost_cold_dollar"]),
                    startup_cost_warm_dollar=float(row["startup_cost_warm_dollar"]),
                    startup_cost_hot_dollar=float(row["startup_cost_hot_dollar"]),
                    no_load_cost_dollar_per_hr=float(row["no_load_cost_dollar_per_hr"]),
                )
            )
        return params

    # Compute from hardcoded classification + reference table.
    if reference_csv is None:
        repo_root = Path(__file__).resolve().parent.parent
        reference_csv = repo_root / "reference" / "rts_gmlc_tech_classes.csv"

    templates = load_reference_table(reference_csv)
    classifications = load_gen_classification()
    return assign_all_temporal_params(classifications, templates)


# ---------------------------------------------------------------------------
# Reserve requirements
# ---------------------------------------------------------------------------


def build_reserve_requirements() -> tuple[ReserveRequirementProfile, ReserveRequirementProfile]:
    """Build spinning and non-spinning reserve requirement profiles.

    Both requirements are constant at 550 MW across all 24 hours,
    derived from the N-1 criterion (1100 MW largest gen x 50%).

    Returns:
        Tuple of (spinning, non_spinning) ReserveRequirementProfile.
    """
    spinning = ReserveRequirementProfile(
        reserve_type=ReserveProduct.SPINNING,
        requirement_mw=SPINNING_REQUIREMENT_MW,
    )
    non_spinning = ReserveRequirementProfile(
        reserve_type=ReserveProduct.NON_SPINNING,
        requirement_mw=NON_SPINNING_REQUIREMENT_MW,
    )
    return spinning, non_spinning


# ---------------------------------------------------------------------------
# Eligibility computation
# ---------------------------------------------------------------------------


def compute_ramp_based_reserve_pct(
    ramp_rate_mw_per_hr: float,
    deployment_minutes: float,
    pmax_mw: float,
) -> float:
    """Compute ramp-based reserve percentage for a generator.

    The percentage represents the fraction of Pmax that the generator can
    ramp within the deployment window:

        pct = (ramp_rate_mw_per_hr * deployment_minutes / 60) / pmax_mw

    Result is capped at 1.0 (a generator cannot provide more than its
    full capacity as reserves).

    Args:
        ramp_rate_mw_per_hr: Generator ramp rate in MW/hr.
        deployment_minutes: Deployment window in minutes (10 for spinning,
            30 for non-spinning).
        pmax_mw: Generator Pmax in MW.

    Returns:
        Reserve percentage in [0, 1].

    Raises:
        ValueError: If pmax_mw is zero or negative.
    """
    if pmax_mw <= 0:
        msg = f"pmax_mw must be positive, got {pmax_mw}"
        raise ValueError(msg)

    ramp_mw = ramp_rate_mw_per_hr * (deployment_minutes / 60.0)
    pct = ramp_mw / pmax_mw
    return min(pct, 1.0)


def compute_generator_eligibility(
    classification: Case39GenClassification,
    temporal_params: GenTemporalParams,
) -> GeneratorReserveEligibility:
    """Compute reserve eligibility for a single generator.

    Nuclear generators get fixed caps (5% spinning, 10% non-spinning).
    All others use ramp-based percentages with deployment windows of
    10 minutes (spinning) and 30 minutes (non-spinning).

    All generators are eligible for both products (spinning_eligible and
    non_spinning_eligible are always True).

    Args:
        classification: Generator classification record.
        temporal_params: Generator temporal parameters (contains ramp rate).

    Returns:
        GeneratorReserveEligibility for this generator.
    """
    gen_uid = build_gen_uid(classification.bus_id, classification.gen_number)

    if classification.rts_gmlc_class == RtsGmlcClass.NUCLEAR:
        max_spinning_pct = NUCLEAR_MAX_SPINNING_PCT
        max_non_spinning_pct = NUCLEAR_MAX_NON_SPINNING_PCT
    else:
        max_spinning_pct = compute_ramp_based_reserve_pct(
            temporal_params.ramp_rate_mw_per_hr,
            SPINNING_DEPLOYMENT_MINUTES,
            classification.pmax_mw,
        )
        max_non_spinning_pct = compute_ramp_based_reserve_pct(
            temporal_params.ramp_rate_mw_per_hr,
            NON_SPINNING_DEPLOYMENT_MINUTES,
            classification.pmax_mw,
        )

    return GeneratorReserveEligibility(
        gen_uid=gen_uid,
        gen_index=classification.gen_index,
        bus_id=classification.bus_id,
        fuel_type=classification.fuel_category,
        rts_gmlc_class=classification.rts_gmlc_class.value,
        pmax_mw=classification.pmax_mw,
        ramp_rate_mw_per_hr=temporal_params.ramp_rate_mw_per_hr,
        spinning_eligible=True,
        non_spinning_eligible=True,
        max_spinning_pct=max_spinning_pct,
        max_non_spinning_pct=max_non_spinning_pct,
    )


def compute_all_eligibilities(
    classifications: list[Case39GenClassification],
    temporal_params_list: list[GenTemporalParams],
) -> list[GeneratorReserveEligibility]:
    """Compute reserve eligibility for all generators.

    Matches classification and temporal parameter records by gen_index
    and pmax_mw.  Raises if the two lists have different lengths or if
    pmax_mw values do not match for any generator.

    Args:
        classifications: Classification records from PRD-01.
        temporal_params_list: Temporal parameter records from PRD-02.

    Returns:
        List of GeneratorReserveEligibility, one per generator.

    Raises:
        ValueError: If list lengths differ or pmax_mw values mismatch.
    """
    if len(classifications) != len(temporal_params_list):
        msg = (
            f"Classification count ({len(classifications)}) != "
            f"temporal params count ({len(temporal_params_list)})"
        )
        raise ValueError(msg)

    # Index temporal params by gen_index for matching.
    tp_by_index: dict[int, GenTemporalParams] = {tp.gen_index: tp for tp in temporal_params_list}

    eligibilities: list[GeneratorReserveEligibility] = []
    for cls in classifications:
        tp = tp_by_index.get(cls.gen_index)
        if tp is None:
            msg = f"No temporal params for gen_index {cls.gen_index}"
            raise ValueError(msg)

        if abs(cls.pmax_mw - tp.pmax_mw) > 0.01:
            msg = (
                f"Pmax mismatch for gen_index {cls.gen_index}: "
                f"classification={cls.pmax_mw}, temporal={tp.pmax_mw}"
            )
            raise ValueError(msg)

        eligibilities.append(compute_generator_eligibility(cls, tp))

    return eligibilities


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_reserve_feasibility(
    product: ReserveProduct,
    requirement_mw: float,
    eligibilities: list[GeneratorReserveEligibility],
) -> ReserveFeasibilityCheck:
    """Check whether the fleet can meet a reserve requirement.

    Computes total eligible capacity as the sum of
    pmax_mw * max_<product>_pct for each eligible generator.

    Args:
        product: Which reserve product to check.
        requirement_mw: The requirement in MW.
        eligibilities: Per-generator eligibility records.

    Returns:
        ReserveFeasibilityCheck with feasibility result and margin.
    """
    total = 0.0
    for elig in eligibilities:
        if product == ReserveProduct.SPINNING and elig.spinning_eligible:
            total += elig.pmax_mw * elig.max_spinning_pct
        elif product == ReserveProduct.NON_SPINNING and elig.non_spinning_eligible:
            total += elig.pmax_mw * elig.max_non_spinning_pct

    return ReserveFeasibilityCheck(
        product=product,
        requirement_mw=requirement_mw,
        total_eligible_capacity_mw=round(total, 4),
        is_feasible=total >= requirement_mw,
        margin_mw=round(total - requirement_mw, 4),
    )


def validate_eligibility_records(
    eligibilities: list[GeneratorReserveEligibility],
) -> list[str]:
    """Validate eligibility records for consistency.

    Checks:
    - All percentages are in [0, 1].
    - Every generator has at least one eligibility (spinning or non-spinning).

    Args:
        eligibilities: List of eligibility records.

    Returns:
        List of error strings (empty if all valid).
    """
    errors: list[str] = []
    for e in eligibilities:
        if not (0.0 <= e.max_spinning_pct <= 1.0):
            errors.append(f"{e.gen_uid}: max_spinning_pct {e.max_spinning_pct} not in [0, 1]")
        if not (0.0 <= e.max_non_spinning_pct <= 1.0):
            errors.append(
                f"{e.gen_uid}: max_non_spinning_pct {e.max_non_spinning_pct} not in [0, 1]"
            )
        if not e.spinning_eligible and not e.non_spinning_eligible:
            errors.append(f"{e.gen_uid}: not eligible for any reserve product")
    return errors


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

_HOUR_COLUMNS = [f"HR_{h}" for h in range(1, 25)]


def write_reserve_requirements_csv(
    spinning: ReserveRequirementProfile,
    non_spinning: ReserveRequirementProfile,
    dest_path: Path,
) -> None:
    """Write the 24-hour reserve requirements to CSV.

    Produces a CSV with columns: reserve_type, HR_1 .. HR_24.
    Two rows: spinning (550 MW) and non_spinning (550 MW).

    Args:
        spinning: Spinning reserve requirement profile.
        non_spinning: Non-spinning reserve requirement profile.
        dest_path: Path to write the CSV.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["reserve_type", *_HOUR_COLUMNS]

    rows: list[list[str]] = []
    for req in (spinning, non_spinning):
        row = [req.reserve_type.value]
        row.extend(f"{req.requirement_mw:.2f}" for _ in range(NUM_HOURS))
        rows.append(row)

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


_ELIGIBILITY_COLUMNS = [
    "gen_uid",
    "gen_index",
    "bus_id",
    "fuel_type",
    "rts_gmlc_class",
    "pmax_mw",
    "ramp_rate_mw_per_hr",
    "spinning_eligible",
    "non_spinning_eligible",
    "max_spinning_pct",
    "max_non_spinning_pct",
]


def write_reserve_eligibility_csv(
    eligibilities: list[GeneratorReserveEligibility],
    dest_path: Path,
) -> None:
    """Write per-generator reserve eligibility to CSV.

    One row per generator, ordered by gen_index.

    Args:
        eligibilities: List of eligibility records.
        dest_path: Path to write the CSV.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_elig = sorted(eligibilities, key=lambda e: e.gen_index)

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ELIGIBILITY_COLUMNS)
        writer.writeheader()
        for e in sorted_elig:
            writer.writerow(
                {
                    "gen_uid": e.gen_uid,
                    "gen_index": e.gen_index,
                    "bus_id": e.bus_id,
                    "fuel_type": e.fuel_type,
                    "rts_gmlc_class": e.rts_gmlc_class,
                    "pmax_mw": e.pmax_mw,
                    "ramp_rate_mw_per_hr": round(e.ramp_rate_mw_per_hr, 4),
                    "spinning_eligible": e.spinning_eligible,
                    "non_spinning_eligible": e.non_spinning_eligible,
                    "max_spinning_pct": round(e.max_spinning_pct, 6),
                    "max_non_spinning_pct": round(e.max_non_spinning_pct, 6),
                }
            )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def define_reserves(
    classifications: list[Case39GenClassification],
    temporal_params_list: list[GenTemporalParams],
    output_dir: Path,
) -> ReserveDefinitionResult:
    """Run the full reserve definition pipeline for TINY (case39).

    1. Build reserve requirements (550 MW spinning, 550 MW non-spinning).
    2. Compute per-generator eligibility.
    3. Validate eligibility records.
    4. Validate reserve feasibility.
    5. Write reserve_requirements_24h.csv.
    6. Write reserve_eligibility.csv.

    Args:
        classifications: Generator classification records from PRD-01.
        temporal_params_list: Generator temporal parameters from PRD-02.
        output_dir: Directory for output CSVs.

    Returns:
        ReserveDefinitionResult with paths, requirements, eligibilities,
        and feasibility checks.

    Raises:
        ValueError: If eligibility validation fails or reserve
            requirements are infeasible.
    """
    # 1. Requirements.
    spinning_req, non_spinning_req = build_reserve_requirements()

    # 2. Eligibility.
    eligibilities = compute_all_eligibilities(classifications, temporal_params_list)

    # 3. Validate eligibility records.
    errors = validate_eligibility_records(eligibilities)
    if errors:
        msg = "Eligibility validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)

    # 4. Feasibility.
    spinning_feas = validate_reserve_feasibility(
        ReserveProduct.SPINNING, spinning_req.requirement_mw, eligibilities
    )
    non_spinning_feas = validate_reserve_feasibility(
        ReserveProduct.NON_SPINNING, non_spinning_req.requirement_mw, eligibilities
    )

    # 5. Write requirements CSV.
    req_csv_path = output_dir / "reserve_requirements_24h.csv"
    write_reserve_requirements_csv(spinning_req, non_spinning_req, req_csv_path)

    # 6. Write eligibility CSV.
    elig_csv_path = output_dir / "reserve_eligibility.csv"
    write_reserve_eligibility_csv(eligibilities, elig_csv_path)

    return ReserveDefinitionResult(
        requirements_csv_path=str(req_csv_path),
        eligibility_csv_path=str(elig_csv_path),
        spinning_requirement=spinning_req,
        non_spinning_requirement=non_spinning_req,
        eligibilities=eligibilities,
        spinning_feasibility=spinning_feas,
        non_spinning_feasibility=non_spinning_feas,
    )


def main(
    output_dir: Path | None = None,
    reference_csv: Path | None = None,
) -> ReserveDefinitionResult:
    """Entry point: define reserves for the TINY (case39) fleet.

    Loads classification and temporal parameters, then runs the full
    reserve definition pipeline.

    Args:
        output_dir: Directory for output CSVs.
            Defaults to <repo_root>/data/timeseries/case39/.
        reference_csv: Path to rts_gmlc_tech_classes.csv.
            Defaults to <repo_root>/data/reference/rts_gmlc_tech_classes.csv.

    Returns:
        ReserveDefinitionResult with all outputs and checks.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if output_dir is None:
        output_dir = repo_root / "timeseries" / "case39"
    if reference_csv is None:
        reference_csv = repo_root / "reference" / "rts_gmlc_tech_classes.csv"

    classifications = load_gen_classification_csv()
    temporal_params_list = load_gen_temporal_params(reference_csv=reference_csv)

    return define_reserves(classifications, temporal_params_list, output_dir)


if __name__ == "__main__":
    main()
