"""Generator Fuel-Type Classification for MATPOWER test networks.

Classifies every generator in the TINY (case39), SMALL (ACTIVSg2000), and
MEDIUM (ACTIVSg10k) networks by fuel type and capacity band, producing a
per-network mapping CSV that links each generator to an RTS-GMLC technology
class from the Phase 2 D1 reference table.

Classification uses a three-level priority chain per generator:
  1. genfuel field in the .m file
  2. Fuel-type labels from companion CSVs
  3. Heuristic classifier based on Pmax and cost curve slope

Each generator's classification records which source determined its fuel
type and a confidence flag.
"""

from __future__ import annotations

import csv
import io
import sys
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path

from scripts.build_rts_gmlc_reference import (
    CapacityBand,
    CapacityBandThreshold,
    FuelType,
    build_capacity_band_thresholds,
)
from scripts.reconcile_bus_gen import (
    MatpowerCaseData,
    MatpowerGenRecord,
    parse_matpower_case,
)
from scripts.snapshot_cleanup import (
    CASE39_FUEL_MAP,
    FuelCategory,
)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ClassificationNetworkId(StrEnum):
    """Identifiers for the three test networks."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class GasUnitType(StrEnum):
    """Gas generator sub-types based on prime mover."""

    CT = "CT"
    CC = "CC"
    STEAM = "STEAM"


class ClassificationSource(StrEnum):
    """How the fuel type was determined for a generator."""

    GENFUEL = "genfuel"
    COMPANION = "companion"
    HEURISTIC = "heuristic"
    CASE39_HARDCODED = "case39_hardcoded"


class ConfidenceLevel(StrEnum):
    """Confidence in the fuel type classification."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


NETWORK_M_FILE_NAMES: dict[ClassificationNetworkId, str] = {
    ClassificationNetworkId.TINY: "case39.m",
    ClassificationNetworkId.SMALL: "case_ACTIVSg2000.m",
    ClassificationNetworkId.MEDIUM: "case_ACTIVSg10k.m",
}


@dataclass(frozen=True)
class GenFuelClassificationRow:
    """Classification result for a single generator."""

    gen_index: int
    gen_bus: int
    gen_uid: str
    fuel_type: FuelType
    gas_unit_type: GasUnitType | None
    unit_type: str  # composed unit type string (e.g., "CT", "STEAM", "NUCLEAR")
    capacity_band: CapacityBand
    tech_class: str  # e.g., "coal_large", "gas_CT_small"
    pmax_mw: float
    pmin_mw: float
    source: ClassificationSource
    confidence: ConfidenceLevel


@dataclass(frozen=True)
class HeuristicFeatures:
    """Features extracted from a generator for heuristic classification."""

    pmax_mw: float
    pmin_mw: float
    cost_slope: float  # $/MWh marginal cost from gencost if available


@dataclass(frozen=True)
class HeuristicThresholds:
    """Threshold values for the heuristic fuel-type classifier."""

    nuclear_pmax_min: float = 400.0
    coal_pmax_min: float = 100.0
    gas_cc_pmax_min: float = 200.0
    gas_ct_pmax_max: float = 200.0
    wind_cost_max: float = 5.0
    solar_cost_max: float = 5.0
    hydro_cost_max: float = 10.0
    nuclear_cost_max: float = 15.0
    coal_cost_max: float = 30.0


@dataclass(frozen=True)
class CompanionFuelLabel:
    """Fuel-type label from a companion CSV file."""

    gen_bus: int
    gen_index_at_bus: int  # 0-based index among generators at this bus
    fuel_type: FuelType
    source_file: str


@dataclass(frozen=True)
class TechClassCount:
    """Count of generators assigned to a particular technology class."""

    tech_class: str
    fuel_type: FuelType
    capacity_band: CapacityBand
    count: int
    total_pmax_mw: float


@dataclass(frozen=True)
class NetworkClassificationResult:
    """Complete classification result for one network."""

    network_id: ClassificationNetworkId
    generator_count: int
    classifications: list[GenFuelClassificationRow]
    tech_class_counts: list[TechClassCount]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClassificationSummary:
    """Summary across all networks."""

    networks: list[NetworkClassificationResult]
    script_version: str


# ---------------------------------------------------------------------------
# Genfuel label mapping
# ---------------------------------------------------------------------------

# Mapping from genfuel strings (case-insensitive) to FuelType.
_GENFUEL_TO_FUELTYPE: dict[str, FuelType] = {
    "coal": FuelType.COAL,
    "ng": FuelType.GAS,
    "gas": FuelType.GAS,
    "oil": FuelType.OIL,
    "nuclear": FuelType.NUCLEAR,
    "hydro": FuelType.HYDRO,
    "wind": FuelType.WIND,
    "solar": FuelType.SOLAR,
}

# Mapping from FuelCategory (snapshot_cleanup) to FuelType.
_FUEL_CATEGORY_TO_FUELTYPE: dict[FuelCategory, FuelType] = {
    FuelCategory.COAL: FuelType.COAL,
    FuelCategory.NG: FuelType.GAS,
    FuelCategory.NUCLEAR: FuelType.NUCLEAR,
    FuelCategory.HYDRO: FuelType.HYDRO,
    FuelCategory.WIND: FuelType.WIND,
    FuelCategory.SOLAR: FuelType.SOLAR,
}


# ---------------------------------------------------------------------------
# Classification functions
# ---------------------------------------------------------------------------


def load_case_data(m_file_path: Path) -> MatpowerCaseData:
    """Load and parse a MATPOWER .m case file.

    Args:
        m_file_path: Path to the .m file.

    Returns:
        Parsed MatpowerCaseData.
    """
    return parse_matpower_case(m_file_path)


def classify_fuel_from_genfuel(raw_fuel: str | None) -> FuelType | None:
    """Map a genfuel field string to a FuelType.

    Args:
        raw_fuel: The genfuel string from the .m file, or None if absent.

    Returns:
        The corresponding FuelType, or None if the label is not recognized.
    """
    if raw_fuel is None:
        return None
    normalized = raw_fuel.strip().lower()
    return _GENFUEL_TO_FUELTYPE.get(normalized)


def classify_fuel_from_companion(
    gen_bus: int,
    gen_index_at_bus: int,
    companion_labels: list[CompanionFuelLabel],
) -> FuelType | None:
    """Look up fuel type from companion CSV labels.

    Args:
        gen_bus: Bus number the generator is connected to.
        gen_index_at_bus: 0-based index among generators at this bus.
        companion_labels: Pre-loaded companion fuel labels.

    Returns:
        The FuelType from the companion data, or None if not found.
    """
    for label in companion_labels:
        if label.gen_bus == gen_bus and label.gen_index_at_bus == gen_index_at_bus:
            return label.fuel_type
    return None


def classify_fuel_by_heuristic(
    features: HeuristicFeatures,
    thresholds: HeuristicThresholds,
) -> FuelType:
    """Classify fuel type using heuristic rules based on Pmax and cost slope.

    The heuristic uses cost slope as the primary discriminator when available,
    falling back to capacity-based rules.

    Args:
        features: Extracted generator features.
        thresholds: Threshold values for classification boundaries.

    Returns:
        The inferred FuelType.
    """
    cost = features.cost_slope
    pmax = features.pmax_mw

    # Cost-based rules (when cost data is meaningful)
    if cost <= thresholds.wind_cost_max and pmax < thresholds.coal_pmax_min:
        return FuelType.WIND
    if cost <= thresholds.solar_cost_max and pmax < thresholds.gas_cc_pmax_min:
        return FuelType.SOLAR
    if cost <= thresholds.hydro_cost_max:
        return FuelType.HYDRO
    if cost <= thresholds.nuclear_cost_max and pmax >= thresholds.nuclear_pmax_min:
        return FuelType.NUCLEAR

    # Capacity-based fallback
    if pmax >= thresholds.nuclear_pmax_min and cost <= thresholds.nuclear_cost_max:
        return FuelType.NUCLEAR
    if pmax >= thresholds.coal_pmax_min and cost <= thresholds.coal_cost_max:
        return FuelType.COAL
    if pmax >= thresholds.gas_cc_pmax_min:
        return FuelType.GAS
    if pmax < thresholds.gas_ct_pmax_max:
        return FuelType.GAS

    return FuelType.GAS  # default fallback


def resolve_fuel_type(
    genfuel_result: FuelType | None,
    companion_result: FuelType | None,
    heuristic_result: FuelType,
) -> tuple[FuelType, ClassificationSource, ConfidenceLevel]:
    """Resolve fuel type from the three classification sources using priority chain.

    Priority: genfuel > companion > heuristic.
    Confidence:
      - genfuel + companion agree -> HIGH
      - genfuel only -> MEDIUM
      - companion only -> MEDIUM
      - heuristic fallback -> LOW

    Args:
        genfuel_result: Result from genfuel field, or None.
        companion_result: Result from companion CSV, or None.
        heuristic_result: Result from heuristic classifier.

    Returns:
        Tuple of (fuel_type, source, confidence).
    """
    if genfuel_result is not None and companion_result is not None:
        if genfuel_result == companion_result:
            return genfuel_result, ClassificationSource.GENFUEL, ConfidenceLevel.HIGH
        # Disagreement: trust genfuel
        return genfuel_result, ClassificationSource.GENFUEL, ConfidenceLevel.MEDIUM

    if genfuel_result is not None:
        return genfuel_result, ClassificationSource.GENFUEL, ConfidenceLevel.MEDIUM

    if companion_result is not None:
        return companion_result, ClassificationSource.COMPANION, ConfidenceLevel.MEDIUM

    return heuristic_result, ClassificationSource.HEURISTIC, ConfidenceLevel.LOW


def infer_gas_unit_type(
    gen: MatpowerGenRecord,
    gentype_field: str | None = None,
) -> GasUnitType:
    """Infer the gas unit sub-type (CT, CC, or STEAM).

    Uses the gentype field if available, otherwise infers from Pmax:
      - Pmax < 100 MW -> CT
      - Pmax >= 100 MW and < 300 MW -> CC
      - Pmax >= 300 MW -> STEAM

    Args:
        gen: The generator record.
        gentype_field: Optional gentype string from the .m file.

    Returns:
        The inferred GasUnitType.
    """
    if gentype_field is not None:
        normalized = gentype_field.strip().upper()
        if normalized in ("CT", "GT"):
            return GasUnitType.CT
        if normalized in ("CC", "CA"):
            return GasUnitType.CC
        if normalized in ("ST", "STEAM"):
            return GasUnitType.STEAM

    # Infer from Pmax
    if gen.pmax < 100.0:
        return GasUnitType.CT
    if gen.pmax < 300.0:
        return GasUnitType.CC
    return GasUnitType.STEAM


def infer_unit_type(
    fuel_type: FuelType,
    gen: MatpowerGenRecord,
    gas_unit_type: GasUnitType | None = None,
) -> str:
    """Determine the unit type string for a generator.

    For gas generators, uses the gas_unit_type. For other fuels, returns
    a canonical unit type string.

    Args:
        fuel_type: The classified fuel type.
        gen: The generator record.
        gas_unit_type: The gas sub-type, required when fuel_type is GAS.

    Returns:
        A unit type string (e.g., "CT", "STEAM", "NUCLEAR", "HYDRO").
    """
    if fuel_type == FuelType.GAS and gas_unit_type is not None:
        return gas_unit_type.value
    unit_type_map: dict[FuelType, str] = {
        FuelType.COAL: "STEAM",
        FuelType.OIL: "CT",
        FuelType.NUCLEAR: "NUCLEAR",
        FuelType.HYDRO: "HYDRO",
        FuelType.WIND: "WIND",
        FuelType.SOLAR: "PV",
    }
    return unit_type_map.get(fuel_type, "STEAM")


def assign_capacity_band(
    fuel_type: FuelType,
    pmax_mw: float,
    thresholds: list[CapacityBandThreshold],
) -> CapacityBand:
    """Assign a capacity band to a generator based on its fuel type and Pmax.

    Finds the matching CapacityBandThreshold for the generator's fuel type
    and Pmax. If Pmax exceeds all defined bands, returns the largest band.

    Args:
        fuel_type: The generator's classified fuel type.
        pmax_mw: The generator's maximum real power output (MW).
        thresholds: Capacity band thresholds from build_capacity_band_thresholds.

    Returns:
        The matching CapacityBand.
    """
    fuel_thresholds = [t for t in thresholds if t.fuel_type == fuel_type]
    if not fuel_thresholds:
        return CapacityBand.SMALL

    fuel_thresholds.sort(key=lambda t: t.min_mw)

    for i, threshold in enumerate(fuel_thresholds):
        is_last = i == len(fuel_thresholds) - 1
        if is_last:
            if pmax_mw >= threshold.min_mw:
                return threshold.band
        else:
            if threshold.min_mw <= pmax_mw < threshold.max_mw:
                return threshold.band

    # Exceeds all bands: return the largest
    return fuel_thresholds[-1].band


def compose_tech_class(
    fuel_type: FuelType,
    unit_type: str,
    capacity_band: CapacityBand,
) -> str:
    """Compose a technology class string from fuel type, unit type, and band.

    Naming conventions match build_rts_gmlc_reference:
      - Gas/Oil: include unit type, e.g., "gas_CT", "oil_CT"
      - Single-band fuels: just fuel name, e.g., "nuclear", "hydro"
      - Multi-band fuels: fuel + band, e.g., "coal_small", "coal_large"

    Args:
        fuel_type: The generator's fuel type.
        unit_type: The unit type string.
        capacity_band: The capacity band.

    Returns:
        A technology class string.
    """
    # Gas and oil always include unit type
    if fuel_type in (FuelType.GAS, FuelType.OIL):
        return f"{fuel_type.value}_{unit_type}"

    # Renewables, nuclear, hydro: single-band, just fuel name
    single_band_fuels = {FuelType.NUCLEAR, FuelType.HYDRO, FuelType.WIND, FuelType.SOLAR}
    if fuel_type in single_band_fuels:
        return fuel_type.value

    # Coal: multi-band
    return f"{fuel_type.value}_{capacity_band.value}"


def classify_generator(
    gen: MatpowerGenRecord,
    gen_index: int,
    network_id: ClassificationNetworkId,
    companion_labels: list[CompanionFuelLabel],
    thresholds: list[CapacityBandThreshold],
    heuristic_thresholds: HeuristicThresholds,
    gentype_field: str | None = None,
    gen_index_at_bus: int = 0,
) -> GenFuelClassificationRow:
    """Classify a single generator by fuel type, unit type, and capacity band.

    For case39 (TINY), uses the hardcoded CASE39_FUEL_MAP with HIGH confidence.
    For other networks, applies the three-level priority chain.

    Args:
        gen: The generator record from the .m file.
        gen_index: 0-based index of this generator in the case.
        network_id: Which network this generator belongs to.
        companion_labels: Pre-loaded companion fuel labels.
        thresholds: Capacity band thresholds.
        heuristic_thresholds: Thresholds for the heuristic classifier.
        gentype_field: Optional gentype string from the .m file.
        gen_index_at_bus: 0-based index among generators at the same bus.

    Returns:
        A GenFuelClassificationRow with the full classification.
    """
    gen_uid = build_gen_uid(network_id, gen.gen_bus, gen_index)

    # Case39: use hardcoded map
    if network_id == ClassificationNetworkId.TINY:
        fuel_cat = CASE39_FUEL_MAP[gen_index]
        fuel_type = _FUEL_CATEGORY_TO_FUELTYPE[fuel_cat]
        source = ClassificationSource.CASE39_HARDCODED
        confidence = ConfidenceLevel.HIGH
    else:
        # Three-level priority chain
        genfuel_result = classify_fuel_from_genfuel(gen.fuel_type)

        companion_result = classify_fuel_from_companion(
            gen.gen_bus, gen_index_at_bus, companion_labels
        )

        heuristic_features = HeuristicFeatures(
            pmax_mw=gen.pmax,
            pmin_mw=gen.pmin,
            cost_slope=0.0,  # cost slope from gencost would go here
        )
        heuristic_result = classify_fuel_by_heuristic(heuristic_features, heuristic_thresholds)

        fuel_type, source, confidence = resolve_fuel_type(
            genfuel_result, companion_result, heuristic_result
        )

    # Determine gas unit type
    gas_unit_type: GasUnitType | None = None
    if fuel_type == FuelType.GAS:
        gas_unit_type = infer_gas_unit_type(gen, gentype_field)

    # Determine unit type string
    unit_type_str = infer_unit_type(fuel_type, gen, gas_unit_type)

    # Assign capacity band
    band = assign_capacity_band(fuel_type, gen.pmax, thresholds)

    # Compose tech class
    tech_class = compose_tech_class(fuel_type, unit_type_str, band)

    return GenFuelClassificationRow(
        gen_index=gen_index,
        gen_bus=gen.gen_bus,
        gen_uid=gen_uid,
        fuel_type=fuel_type,
        gas_unit_type=gas_unit_type,
        unit_type=unit_type_str,
        capacity_band=band,
        tech_class=tech_class,
        pmax_mw=gen.pmax,
        pmin_mw=gen.pmin,
        source=source,
        confidence=confidence,
    )


def load_companion_fuel_labels(
    companion_csv_path: Path,
) -> list[CompanionFuelLabel]:
    """Load fuel-type labels from a companion CSV file.

    The CSV must have columns: gen_bus, gen_index_at_bus, fuel_type, source_file.

    Args:
        companion_csv_path: Path to the companion fuel labels CSV.

    Returns:
        A list of CompanionFuelLabel records.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not companion_csv_path.exists():
        return []

    labels: list[CompanionFuelLabel] = []
    text = companion_csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    for row in reader:
        fuel_str = row["fuel_type"].strip().lower()
        fuel_type = _GENFUEL_TO_FUELTYPE.get(fuel_str)
        if fuel_type is None:
            continue
        labels.append(
            CompanionFuelLabel(
                gen_bus=int(row["gen_bus"]),
                gen_index_at_bus=int(row["gen_index_at_bus"]),
                fuel_type=fuel_type,
                source_file=row.get("source_file", ""),
            )
        )

    return labels


def load_reference_thresholds() -> list[CapacityBandThreshold]:
    """Load capacity band thresholds from the RTS-GMLC reference table builder.

    Returns:
        A list of CapacityBandThreshold from build_rts_gmlc_reference.
    """
    return build_capacity_band_thresholds()


def build_gen_uid(
    network_id: ClassificationNetworkId,
    gen_bus: int,
    gen_index: int,
) -> str:
    """Build a unique generator identifier.

    Format: {network_id}_{gen_bus}_{gen_index}

    Args:
        network_id: The network this generator belongs to.
        gen_bus: The bus number.
        gen_index: The 0-based generator index in the case.

    Returns:
        A unique generator ID string.
    """
    return f"{network_id.value}_{gen_bus}_{gen_index}"


def classify_network(
    network_id: ClassificationNetworkId,
    case_data: MatpowerCaseData,
    companion_labels: list[CompanionFuelLabel],
    thresholds: list[CapacityBandThreshold],
    heuristic_thresholds: HeuristicThresholds | None = None,
) -> NetworkClassificationResult:
    """Classify all generators in a single network.

    Args:
        network_id: Which network to classify.
        case_data: Parsed MATPOWER case data.
        companion_labels: Pre-loaded companion fuel labels.
        thresholds: Capacity band thresholds.
        heuristic_thresholds: Thresholds for heuristic classifier.

    Returns:
        A NetworkClassificationResult with all generator classifications.
    """
    if heuristic_thresholds is None:
        heuristic_thresholds = HeuristicThresholds()

    classifications: list[GenFuelClassificationRow] = []
    warnings: list[str] = []

    # Track per-bus generator count for correct companion CSV lookup
    bus_gen_count: dict[int, int] = {}

    for i, gen in enumerate(case_data.generators):
        gen_index_at_bus = bus_gen_count.get(gen.gen_bus, 0)
        bus_gen_count[gen.gen_bus] = gen_index_at_bus + 1

        row = classify_generator(
            gen=gen,
            gen_index=i,
            network_id=network_id,
            companion_labels=companion_labels,
            thresholds=thresholds,
            heuristic_thresholds=heuristic_thresholds,
            gen_index_at_bus=gen_index_at_bus,
        )
        classifications.append(row)

    tech_class_counts = build_tech_class_counts(classifications)

    return NetworkClassificationResult(
        network_id=network_id,
        generator_count=len(case_data.generators),
        classifications=classifications,
        tech_class_counts=tech_class_counts,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "gen_index",
    "gen_bus",
    "gen_uid",
    "fuel_type",
    "gas_unit_type",
    "unit_type",
    "capacity_band",
    "tech_class",
    "pmax_mw",
    "pmin_mw",
    "source",
    "confidence",
]


def write_classification_csv(
    result: NetworkClassificationResult,
    dest_path: Path,
) -> None:
    """Write classification results to a CSV file.

    Args:
        result: The network classification result.
        dest_path: File path to write the CSV output.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUMNS)
    writer.writeheader()

    for row in result.classifications:
        row_dict = asdict(row)
        # Only include columns in _CSV_COLUMNS
        filtered = {k: row_dict[k] for k in _CSV_COLUMNS}
        # Convert None gas_unit_type to empty string
        if filtered["gas_unit_type"] is None:
            filtered["gas_unit_type"] = ""
        writer.writerow(filtered)

    dest_path.write_text(output.getvalue(), encoding="utf-8")


def build_tech_class_counts(
    classifications: list[GenFuelClassificationRow],
) -> list[TechClassCount]:
    """Aggregate generator counts by technology class.

    Args:
        classifications: All classified generators.

    Returns:
        A list of TechClassCount, sorted by tech_class.
    """
    counts: dict[str, list[GenFuelClassificationRow]] = {}
    for row in classifications:
        counts.setdefault(row.tech_class, []).append(row)

    result: list[TechClassCount] = []
    for tc_name in sorted(counts):
        rows = counts[tc_name]
        first = rows[0]
        total_pmax = sum(r.pmax_mw for r in rows)
        result.append(
            TechClassCount(
                tech_class=tc_name,
                fuel_type=first.fuel_type,
                capacity_band=first.capacity_band,
                count=len(rows),
                total_pmax_mw=total_pmax,
            )
        )

    return result


def print_classification_summary(summary: ClassificationSummary) -> None:
    """Print a human-readable summary of the classification results.

    Args:
        summary: The classification summary across all networks.
    """
    print("=" * 72)
    print("Generator Fuel-Type Classification Summary")
    print("=" * 72)

    for net_result in summary.networks:
        print(f"\nNetwork: {net_result.network_id.value}")
        print(f"  Generators: {net_result.generator_count}")
        print(f"  Technology classes: {len(net_result.tech_class_counts)}")

        fmt = "    {:<25s} {:>5d}  {:>10.1f} MW"
        for tc in net_result.tech_class_counts:
            print(fmt.format(tc.tech_class, tc.count, tc.total_pmax_mw))

        if net_result.warnings:
            print("  Warnings:")
            for w in net_result.warnings:
                print(f"    - {w}")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    networks_dir: Path | None = None,
    output_dir: Path | None = None,
) -> ClassificationSummary:
    """Entry point: classify all generators across all three networks.

    Args:
        networks_dir: Directory containing .m files.
        output_dir: Directory for classification CSV output.

    Returns:
        The complete ClassificationSummary.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if networks_dir is None:
        networks_dir = repo_root / "networks"
    if output_dir is None:
        output_dir = repo_root / "classification"

    thresholds = load_reference_thresholds()
    heuristic_thresholds = HeuristicThresholds()

    network_results: list[NetworkClassificationResult] = []

    for network_id in ClassificationNetworkId:
        m_file_name = NETWORK_M_FILE_NAMES[network_id]
        m_file_path = networks_dir / m_file_name

        if not m_file_path.exists():
            print(
                f"WARNING: Skipping {network_id.value} — file not found: {m_file_path}",
                file=sys.stderr,
            )
            continue

        case_data = load_case_data(m_file_path)

        # Load companion labels if available
        companion_csv = networks_dir / f"{network_id.value}_fuel_labels.csv"
        companion_labels = load_companion_fuel_labels(companion_csv)

        result = classify_network(
            network_id=network_id,
            case_data=case_data,
            companion_labels=companion_labels,
            thresholds=thresholds,
            heuristic_thresholds=heuristic_thresholds,
        )

        # Write per-network CSV
        csv_path = output_dir / f"{network_id.value}_classification.csv"
        write_classification_csv(result, csv_path)

        network_results.append(result)

    summary = ClassificationSummary(
        networks=network_results,
        script_version=__version__,
    )

    print_classification_summary(summary)
    return summary


if __name__ == "__main__":
    main()
