"""Reserve Product Definition & Sizing (PRD 02/04).

Defines two reserve products (spinning and non-spinning) and computes the
24-hour reserve requirement profile for each of the three test networks.
The reserve requirement equals the Pmax of the single largest generator
in the network's fleet (N-1 criterion), constant across all 24 hours.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.reconcile_bus_gen import parse_matpower_generators

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ReserveNetworkId(StrEnum):
    """Identifiers for the three networks in scope for reserve definition."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class ReserveProduct(StrEnum):
    """Reserve product identifiers.

    These are the string values written to the Product column
    of reserve_requirements_24h.csv.
    """

    SPINNING = "spinning"
    NON_SPINNING = "non_spinning"


SIZING_BASIS_DESCRIPTION: str = (
    "N-1 criterion: Pmax of largest fleet generator (constant 24h profile)"
)
"""Human-readable description written to the sizing_basis column."""


@dataclass(frozen=True)
class LargestGenerator:
    """Identity and capacity of the largest generator in a fleet.

    Used as the sizing basis for reserve requirements.
    """

    gen_index: int  # 0-based index into the mpc.gen matrix
    gen_bus: int  # bus number the generator is connected to
    gen_uid: str  # GEN UID string, e.g. "bus_30_gen_0"
    pmax_mw: float  # Pmax in MW


@dataclass(frozen=True)
class ReserveRequirement:
    """A single reserve product's 24-hour requirement for one network.

    All 24 hourly values are identical (constant profile).
    """

    product: ReserveProduct
    requirement_mw: float  # constant value across all hours
    sizing_basis: str  # human-readable description
    largest_gen_uid: str  # GEN UID of the sizing generator
    largest_gen_pmax: float  # Pmax of the sizing generator (same as requirement_mw)


@dataclass(frozen=True)
class NetworkReserveResult:
    """Complete reserve definition result for a single network.

    Contains both product requirements and validation metadata.
    """

    network_id: ReserveNetworkId
    largest_generator: LargestGenerator
    spinning_requirement: ReserveRequirement
    non_spinning_requirement: ReserveRequirement
    total_fleet_capacity_mw: float  # sum of Pmax for all generators
    generator_count: int  # total generators in the fleet
    requirement_to_capacity_ratio: float  # requirement_mw / total_fleet_capacity_mw
    output_csv_path: str  # relative path to the written CSV


@dataclass(frozen=True)
class ReserveSizingSummary:
    """Top-level summary of reserve sizing across all networks.

    Returned by the main entry point for logging and documentation.
    """

    network_results: list[NetworkReserveResult]
    script_version: str


# ---------------------------------------------------------------------------
# Generator data extraction
# ---------------------------------------------------------------------------


def load_generator_pmax_values(
    cleaned_m_path: Path,
) -> list[tuple[int, int, float]]:
    """Load generator index, bus number, and Pmax from a cleaned .m file.

    Reads the cleaned .m file (Phase 1 D3 output) and extracts the
    generator data matrix. Returns a list of (gen_index, gen_bus, pmax)
    tuples, one per generator, in the same order as the mpc.gen matrix.

    The gen_index is 0-based. The gen_bus is the integer bus number
    from column 1 of the mpc.gen matrix. The pmax is from column 9
    (PMAX) of the mpc.gen matrix, in MW.

    Reuses the MATPOWER parsing infrastructure from D2
    (parse_matpower_case).

    Args:
        cleaned_m_path: Path to the cleaned .m file, e.g.
            data/timeseries/ACTIVSg2000/case_ACTIVSg2000.m

    Returns:
        A list of (gen_index, gen_bus, pmax_mw) tuples.

    Raises:
        FileNotFoundError: If cleaned_m_path does not exist.
        ValueError: If the .m file has no generators.
    """
    if not cleaned_m_path.exists():
        msg = f"Cleaned .m file not found: {cleaned_m_path}"
        raise FileNotFoundError(msg)

    generators = parse_matpower_generators(cleaned_m_path)

    if not generators:
        msg = f"No generators found in {cleaned_m_path}"
        raise ValueError(msg)

    return [(i, gen.gen_bus, gen.pmax) for i, gen in enumerate(generators)]


def find_largest_generator(
    gen_data: list[tuple[int, int, float]],
) -> LargestGenerator:
    """Identify the generator with the highest Pmax in the fleet.

    If multiple generators share the same maximum Pmax, the one with
    the lowest gen_index is selected (deterministic tiebreaker).

    The GEN UID is constructed as "bus_{bus_number}_gen_{gen_index}"
    following the convention established by D2 reconciliation.

    Args:
        gen_data: List of (gen_index, gen_bus, pmax_mw) tuples from
            load_generator_pmax_values.

    Returns:
        A LargestGenerator with the identity and Pmax of the winner.

    Raises:
        ValueError: If gen_data is empty.
    """
    if not gen_data:
        msg = "Cannot find largest generator in an empty fleet"
        raise ValueError(msg)

    # Sort by (-pmax, gen_index) so the highest Pmax with lowest index comes first
    best = min(gen_data, key=lambda g: (-g[2], g[0]))
    gen_index, gen_bus, pmax_mw = best

    return LargestGenerator(
        gen_index=gen_index,
        gen_bus=gen_bus,
        gen_uid=f"bus_{gen_bus}_gen_{gen_index}",
        pmax_mw=pmax_mw,
    )


# ---------------------------------------------------------------------------
# Reserve requirement computation
# ---------------------------------------------------------------------------


def compute_reserve_requirements(
    largest_gen: LargestGenerator,
) -> tuple[ReserveRequirement, ReserveRequirement]:
    """Compute spinning and non-spinning reserve requirements.

    Both products have the same requirement: the Pmax of the largest
    generator in the fleet, constant across all 24 hours. The sizing
    basis description and largest generator identity are recorded in
    each ReserveRequirement.

    Args:
        largest_gen: The LargestGenerator identified for this network.

    Returns:
        A tuple of (spinning_requirement, non_spinning_requirement).
    """
    spinning = ReserveRequirement(
        product=ReserveProduct.SPINNING,
        requirement_mw=largest_gen.pmax_mw,
        sizing_basis=SIZING_BASIS_DESCRIPTION,
        largest_gen_uid=largest_gen.gen_uid,
        largest_gen_pmax=largest_gen.pmax_mw,
    )
    non_spinning = ReserveRequirement(
        product=ReserveProduct.NON_SPINNING,
        requirement_mw=largest_gen.pmax_mw,
        sizing_basis=SIZING_BASIS_DESCRIPTION,
        largest_gen_uid=largest_gen.gen_uid,
        largest_gen_pmax=largest_gen.pmax_mw,
    )
    return spinning, non_spinning


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_reserve_feasibility(
    requirement_mw: float,
    total_fleet_capacity_mw: float,
    network_id: ReserveNetworkId,
) -> None:
    """Validate that the reserve requirement is feasible.

    Checks that the reserve requirement (largest generator Pmax) is
    strictly less than the total fleet capacity (sum of all Pmax).
    This is a necessary condition: the fleet must have at least one
    other generator beyond the largest to provide reserves.

    This is a minimal sanity check, not a full SCUC feasibility test.
    Full feasibility screening (reserves + peak load < total capacity)
    is performed in Phase 2 D6.

    Args:
        requirement_mw: The reserve requirement in MW.
        total_fleet_capacity_mw: Sum of all generator Pmax in MW.
        network_id: Which network, for error message context.

    Raises:
        ValueError: If requirement_mw >= total_fleet_capacity_mw.
    """
    if requirement_mw >= total_fleet_capacity_mw:
        msg = (
            f"Reserve requirement ({requirement_mw:.2f} MW) is not strictly less than "
            f"total fleet capacity ({total_fleet_capacity_mw:.2f} MW) for network "
            f"{network_id.value}. The fleet cannot provide reserves beyond its largest unit."
        )
        raise ValueError(msg)


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

_HOUR_COLUMNS = [f"HR_{h}" for h in range(1, 25)]


def write_reserve_requirements_csv(
    spinning: ReserveRequirement,
    non_spinning: ReserveRequirement,
    dest_path: Path,
) -> None:
    """Write the reserve requirements to a canonical CSV file.

    Produces a CSV with two data rows (one per product) and columns:
        Product, HR_1, HR_2, ..., HR_24, sizing_basis,
        largest_gen_uid, largest_gen_pmax

    The Product column contains the ReserveProduct string value
    ("spinning" or "non_spinning"). The HR_1 through HR_24 columns
    all contain the same value (requirement_mw), formatted to 2
    decimal places. The sizing_basis column contains the
    human-readable description. The largest_gen_uid and
    largest_gen_pmax columns identify the sizing generator.

    The CSV uses the hour-ending convention from D4: HR_1 =
    00:00-01:00, HR_24 = 23:00-24:00. Since the profile is
    constant, the mapping is trivial but the column names must
    still conform to the schema.

    Parent directories are created if they do not exist.

    Args:
        spinning: The spinning reserve requirement.
        non_spinning: The non-spinning reserve requirement.
        dest_path: Path to write the CSV file.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["Product", *_HOUR_COLUMNS, "sizing_basis", "largest_gen_uid", "largest_gen_pmax"]

    rows: list[list[str]] = []
    for req in (spinning, non_spinning):
        row = [req.product.value]
        row.extend(f"{req.requirement_mw:.2f}" for _ in range(24))
        row.append(req.sizing_basis)
        row.append(req.largest_gen_uid)
        row.append(f"{req.largest_gen_pmax:.2f}")
        rows.append(row)

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def process_network(
    network_id: ReserveNetworkId,
    cleaned_m_path: Path,
    output_dir: Path,
) -> NetworkReserveResult:
    """Run the full reserve definition pipeline for a single network.

    Loads generator Pmax values from the cleaned .m file, identifies
    the largest generator, computes reserve requirements, validates
    feasibility, writes the output CSV, and returns a result summary.

    Args:
        network_id: Which network to process.
        cleaned_m_path: Path to the cleaned .m file for this network.
        output_dir: Directory to write reserve_requirements_24h.csv.
            Typically data/timeseries/<network_id>/.

    Returns:
        A NetworkReserveResult documenting the sizing and output path.

    Raises:
        FileNotFoundError: If cleaned_m_path does not exist.
        ValueError: If the reserve requirement fails the feasibility
            check.
    """
    gen_data = load_generator_pmax_values(cleaned_m_path)
    largest_gen = find_largest_generator(gen_data)
    total_fleet_capacity_mw = sum(pmax for _, _, pmax in gen_data)

    validate_reserve_feasibility(largest_gen.pmax_mw, total_fleet_capacity_mw, network_id)

    spinning, non_spinning = compute_reserve_requirements(largest_gen)

    csv_path = output_dir / "reserve_requirements_24h.csv"
    write_reserve_requirements_csv(spinning, non_spinning, csv_path)

    ratio = largest_gen.pmax_mw / total_fleet_capacity_mw

    logger.info(
        "Network %s: largest_gen=%s (%.2f MW), total_capacity=%.2f MW, ratio=%.4f",
        network_id.value,
        largest_gen.gen_uid,
        largest_gen.pmax_mw,
        total_fleet_capacity_mw,
        ratio,
    )

    return NetworkReserveResult(
        network_id=network_id,
        largest_generator=largest_gen,
        spinning_requirement=spinning,
        non_spinning_requirement=non_spinning,
        total_fleet_capacity_mw=total_fleet_capacity_mw,
        generator_count=len(gen_data),
        requirement_to_capacity_ratio=ratio,
        output_csv_path=str(csv_path),
    )


NETWORK_M_FILE_NAMES: dict[ReserveNetworkId, str] = {
    ReserveNetworkId.TINY: "case39.m",
    ReserveNetworkId.SMALL: "case_ACTIVSg2000.m",
    ReserveNetworkId.MEDIUM: "case_ACTIVSg10k.m",
}
"""Mapping from network ID to the cleaned .m file name."""


def main(
    timeseries_base_dir: Path | None = None,
) -> ReserveSizingSummary:
    """Entry point: define reserves for all three networks.

    Processes TINY (case39), SMALL (ACTIVSg2000), and MEDIUM
    (ACTIVSg10k). For each network, the cleaned .m file is read
    from <timeseries_base_dir>/<network_id>/<m_file_name> and the
    output CSV is written to
    <timeseries_base_dir>/<network_id>/reserve_requirements_24h.csv.

    Default paths resolve relative to the repository root:
    - Cleaned .m files: data/timeseries/<network_id>/
    - Output CSVs: data/timeseries/<network_id>/

    Args:
        timeseries_base_dir: Base directory for input and output.
            Defaults to <repo_root>/data/timeseries/.

    Returns:
        A ReserveSizingSummary covering all three networks.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "timeseries"

    results: list[NetworkReserveResult] = []

    for network_id in ReserveNetworkId:
        m_file_name = NETWORK_M_FILE_NAMES[network_id]
        network_dir = timeseries_base_dir / network_id.value
        cleaned_m_path = network_dir / m_file_name
        result = process_network(network_id, cleaned_m_path, network_dir)
        results.append(result)

    return ReserveSizingSummary(
        network_results=results,
        script_version=__version__,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
