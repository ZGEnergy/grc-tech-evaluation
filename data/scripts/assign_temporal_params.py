"""Generator Temporal Parameter Assignment for MATPOWER test networks.

Assigns temporal parameters (ramp rates, min up/down times, startup/shutdown costs)
to every generator in TINY (case39), SMALL (ACTIVSg2000), and MEDIUM (ACTIVSg10k)
networks by joining each generator's fuel-type classification from D2 with the
RTS-GMLC technology class reference table from D1.

Extensive parameters (ramp rates, startup/shutdown costs) scale linearly with generator
capacity ratio. Intensive parameters (min up/down times, startup time) are copied directly
without scaling. Renewable generators receive zero for all temporal parameters.
"""

from __future__ import annotations

import csv
import io
import sys
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from scripts.build_rts_gmlc_reference import FuelType, TechClassRow
from scripts.classify_gen_fuel import GenFuelClassificationRow

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TemporalNetworkId(StrEnum):
    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


EXTENSIVE_PARAMS: tuple[str, ...] = (
    "ramp_rate_mw_per_min",
    "ramp_rate_mw_per_hr",
    "startup_cost_dollar",
    "shutdown_cost_dollar",
)

INTENSIVE_PARAMS: tuple[str, ...] = (
    "min_up_time_hr",
    "min_down_time_hr",
    "startup_time_hr",
)

RENEWABLE_FUEL_TYPES: frozenset[str] = frozenset({"wind", "solar"})

NETWORK_CLASSIFICATION_FILE: str = "gen_fuel_classification.csv"
NETWORK_OUTPUT_FILE: str = "gen_temporal_params.csv"

OUTPUT_CSV_COLUMNS: tuple[str, ...] = (
    "gen_uid",
    "pmax_mw",
    "pmin_mw",
    "ramp_rate_mw_per_min",
    "ramp_rate_mw_per_hr",
    "min_up_time_hr",
    "min_down_time_hr",
    "startup_cost_dollar",
    "startup_time_hr",
    "shutdown_cost_dollar",
    "tech_class",
    "fuel_type",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemporalParamRow:
    gen_uid: str
    pmax_mw: float
    pmin_mw: float
    ramp_rate_mw_per_min: float
    ramp_rate_mw_per_hr: float
    min_up_time_hr: float
    min_down_time_hr: float
    startup_cost_dollar: float
    startup_time_hr: float
    shutdown_cost_dollar: float
    tech_class: str
    fuel_type: str


@dataclass(frozen=True)
class ScalingResult:
    gen_uid: str
    tech_class: str
    pmax_ratio: float
    ramp_rate_mw_per_min: float
    ramp_rate_mw_per_hr: float
    min_up_time_hr: float
    min_down_time_hr: float
    startup_cost_dollar: float
    startup_time_hr: float
    shutdown_cost_dollar: float
    pmin_mw: float


@dataclass(frozen=True)
class ParameterValidationWarning:
    gen_uid: str
    parameter: str
    value: float
    threshold: float
    message: str


@dataclass(frozen=True)
class NetworkTemporalResult:
    network_id: TemporalNetworkId
    generator_count: int
    temporal_params: list[TemporalParamRow]
    renewable_count: int
    thermal_count: int
    fuel_type_counts: dict[str, int]
    validation_warnings: list[ParameterValidationWarning]
    output_csv_path: str


@dataclass(frozen=True)
class TemporalAssignmentSummary:
    network_results: list[NetworkTemporalResult]
    reference_table_path: str
    script_version: str


# ---------------------------------------------------------------------------
# Reference table loading
# ---------------------------------------------------------------------------


def load_reference_table(csv_path: Path) -> dict[str, TechClassRow]:
    """Load the RTS-GMLC technology class reference CSV into a dict keyed by tech_class.

    Skips comment lines (starting with '#'). Parses each data row into a TechClassRow.

    Args:
        csv_path: Path to the rts_gmlc_tech_classes.csv file.

    Returns:
        A dict mapping tech_class string to TechClassRow.

    Raises:
        FileNotFoundError: If csv_path does not exist.
    """
    if not csv_path.exists():
        msg = f"Reference table not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")

    # Filter out comment lines.
    non_comment_lines = [line for line in text.splitlines() if not line.startswith("#")]
    filtered_text = "\n".join(non_comment_lines)

    reader = csv.DictReader(io.StringIO(filtered_text))
    result: dict[str, TechClassRow] = {}

    for row in reader:
        tech_class = row["tech_class"].strip()
        result[tech_class] = TechClassRow(
            tech_class=tech_class,
            fuel_type=row["fuel_type"].strip(),
            unit_type=row["unit_type"].strip(),
            capacity_band=row["capacity_band"].strip(),
            pmax_template_mw=float(row["pmax_template_mw"]),
            pmin_template_mw=float(row["pmin_template_mw"]),
            ramp_rate_mw_per_min=float(row["ramp_rate_mw_per_min"]),
            ramp_rate_mw_per_hr=float(row["ramp_rate_mw_per_hr"]),
            min_up_time_hr=float(row["min_up_time_hr"]),
            min_down_time_hr=float(row["min_down_time_hr"]),
            startup_time_cold_hr=float(row["startup_time_cold_hr"]),
            startup_time_warm_hr=float(row["startup_time_warm_hr"]),
            startup_time_hot_hr=float(row["startup_time_hot_hr"]),
            startup_cost_cold_dollar=float(row["startup_cost_cold_dollar"]),
            startup_cost_warm_dollar=float(row["startup_cost_warm_dollar"]),
            startup_cost_hot_dollar=float(row["startup_cost_hot_dollar"]),
            shutdown_cost_dollar=float(row["shutdown_cost_dollar"]),
            capacity_band_min_mw=float(row["capacity_band_min_mw"]),
            capacity_band_max_mw=float(row["capacity_band_max_mw"]),
            generator_count=int(row["generator_count"]),
            source_gen_uids=[],  # Not stored in CSV output
        )

    return result


# ---------------------------------------------------------------------------
# Classification loading
# ---------------------------------------------------------------------------


def load_classification(csv_path: Path) -> list[GenFuelClassificationRow]:
    """Load generator fuel classification CSV produced by D2.

    Args:
        csv_path: Path to the gen_fuel_classification.csv file.

    Returns:
        A list of GenFuelClassificationRow, one per generator.

    Raises:
        FileNotFoundError: If csv_path does not exist.
    """
    if not csv_path.exists():
        msg = f"Classification file not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[GenFuelClassificationRow] = []

    for row in reader:
        gas_unit_type_str = row.get("gas_unit_type", "").strip()
        gas_unit_type = None
        if gas_unit_type_str:
            from scripts.classify_gen_fuel import GasUnitType

            gas_unit_type = GasUnitType(gas_unit_type_str)

        from scripts.classify_gen_fuel import (
            CapacityBand,
            ClassificationSource,
            ConfidenceLevel,
        )

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


# ---------------------------------------------------------------------------
# Core computation functions
# ---------------------------------------------------------------------------


def compute_pmax_ratio(gen_pmax: float, template_pmax: float) -> float:
    """Compute the capacity ratio of a generator to its template class.

    Args:
        gen_pmax: Generator's maximum power output (MW).
        template_pmax: Template class Pmax (MW).

    Returns:
        The ratio gen_pmax / template_pmax. Returns 1.0 if template_pmax is zero
        to avoid division by zero.
    """
    if template_pmax <= 0.0:
        return 1.0
    return gen_pmax / template_pmax


def scale_extensive_param(template_value: float, pmax_ratio: float) -> float:
    """Scale an extensive parameter by the capacity ratio.

    Args:
        template_value: The template parameter value.
        pmax_ratio: The capacity ratio (gen_pmax / template_pmax).

    Returns:
        The scaled parameter value.
    """
    return template_value * pmax_ratio


def compute_pmin(
    gen_pmax: float,
    template_pmin: float,
    template_pmax: float,
) -> float:
    """Compute generator Pmin from template Pmin/Pmax ratio.

    Pmin = (template_pmin / template_pmax) * gen_pmax

    For renewables (template_pmax == 0), returns 0.0.

    Args:
        gen_pmax: Generator's Pmax (MW).
        template_pmin: Template class Pmin (MW).
        template_pmax: Template class Pmax (MW).

    Returns:
        The computed Pmin (MW).
    """
    if template_pmax <= 0.0:
        return 0.0
    ratio = template_pmin / template_pmax
    return ratio * gen_pmax


def is_renewable(fuel_type: str) -> bool:
    """Check if a fuel type is renewable (wind or solar).

    Args:
        fuel_type: The fuel type string.

    Returns:
        True if the fuel type is wind or solar.
    """
    return fuel_type.lower() in RENEWABLE_FUEL_TYPES


def make_renewable_row(
    gen_uid: str, pmax_mw: float, tech_class: str, fuel_type: str
) -> TemporalParamRow:
    """Create a TemporalParamRow with all temporal parameters set to zero.

    Used for renewable generators (wind, solar) that have no commitment constraints.

    Args:
        gen_uid: Generator unique identifier.
        pmax_mw: Generator Pmax (MW).
        tech_class: Technology class string.
        fuel_type: Fuel type string.

    Returns:
        A TemporalParamRow with zero temporal parameters.
    """
    return TemporalParamRow(
        gen_uid=gen_uid,
        pmax_mw=pmax_mw,
        pmin_mw=0.0,
        ramp_rate_mw_per_min=0.0,
        ramp_rate_mw_per_hr=0.0,
        min_up_time_hr=0.0,
        min_down_time_hr=0.0,
        startup_cost_dollar=0.0,
        startup_time_hr=0.0,
        shutdown_cost_dollar=0.0,
        tech_class=tech_class,
        fuel_type=fuel_type,
    )


def assign_temporal_params(
    gen: GenFuelClassificationRow,
    ref_table: dict[str, TechClassRow],
) -> ScalingResult | None:
    """Assign temporal parameters to a single generator by lookup and scaling.

    For thermal generators: looks up the tech class in the reference table,
    computes capacity ratio, scales extensive params, copies intensive params.
    For renewables: returns a ScalingResult with all zeros.

    Args:
        gen: The generator's fuel classification row.
        ref_table: The reference table keyed by tech_class.

    Returns:
        A ScalingResult with computed parameters, or None if the tech class
        is not found in the reference table.
    """
    if is_renewable(gen.fuel_type.value):
        return ScalingResult(
            gen_uid=gen.gen_uid,
            tech_class=gen.tech_class,
            pmax_ratio=0.0,
            ramp_rate_mw_per_min=0.0,
            ramp_rate_mw_per_hr=0.0,
            min_up_time_hr=0.0,
            min_down_time_hr=0.0,
            startup_cost_dollar=0.0,
            startup_time_hr=0.0,
            shutdown_cost_dollar=0.0,
            pmin_mw=0.0,
        )

    template = ref_table.get(gen.tech_class)
    if template is None:
        return None

    ratio = compute_pmax_ratio(gen.pmax_mw, template.pmax_template_mw)

    # Scale extensive parameters
    ramp_min = scale_extensive_param(template.ramp_rate_mw_per_min, ratio)
    ramp_hr = scale_extensive_param(template.ramp_rate_mw_per_hr, ratio)
    # Use cold startup cost as the canonical startup cost
    startup_cost = scale_extensive_param(template.startup_cost_cold_dollar, ratio)
    shutdown_cost = scale_extensive_param(template.shutdown_cost_dollar, ratio)

    # Intensive parameters: copy directly
    min_up = template.min_up_time_hr
    min_down = template.min_down_time_hr
    startup_time = template.startup_time_cold_hr

    # Compute Pmin
    pmin = compute_pmin(gen.pmax_mw, template.pmin_template_mw, template.pmax_template_mw)

    return ScalingResult(
        gen_uid=gen.gen_uid,
        tech_class=gen.tech_class,
        pmax_ratio=ratio,
        ramp_rate_mw_per_min=ramp_min,
        ramp_rate_mw_per_hr=ramp_hr,
        min_up_time_hr=min_up,
        min_down_time_hr=min_down,
        startup_cost_dollar=startup_cost,
        startup_time_hr=startup_time,
        shutdown_cost_dollar=shutdown_cost,
        pmin_mw=pmin,
    )


def build_temporal_param_row(
    gen: GenFuelClassificationRow,
    scaling: ScalingResult,
) -> TemporalParamRow:
    """Build a TemporalParamRow from a classification row and scaling result.

    Args:
        gen: The generator's classification row.
        scaling: The computed scaling result.

    Returns:
        A TemporalParamRow combining identity and temporal parameters.
    """
    return TemporalParamRow(
        gen_uid=gen.gen_uid,
        pmax_mw=gen.pmax_mw,
        pmin_mw=scaling.pmin_mw,
        ramp_rate_mw_per_min=scaling.ramp_rate_mw_per_min,
        ramp_rate_mw_per_hr=scaling.ramp_rate_mw_per_hr,
        min_up_time_hr=scaling.min_up_time_hr,
        min_down_time_hr=scaling.min_down_time_hr,
        startup_cost_dollar=scaling.startup_cost_dollar,
        startup_time_hr=scaling.startup_time_hr,
        shutdown_cost_dollar=scaling.shutdown_cost_dollar,
        tech_class=gen.tech_class,
        fuel_type=gen.fuel_type.value,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_temporal_params(params: list[TemporalParamRow]) -> list[ParameterValidationWarning]:
    """Validate temporal parameters for all generators.

    Checks:
    - Ramp rates non-negative
    - ramp_rate_mw_per_hr <= pmax_mw (for non-renewables)
    - min_up_time_hr + min_down_time_hr <= 24h
    - pmin_mw <= pmax_mw

    Args:
        params: List of TemporalParamRow to validate.

    Returns:
        A list of ParameterValidationWarning for any violations.
    """
    warnings: list[ParameterValidationWarning] = []

    for p in params:
        # Skip renewables for ramp/time checks (all zeros)
        if is_renewable(p.fuel_type):
            continue

        if p.ramp_rate_mw_per_min < 0.0:
            warnings.append(
                ParameterValidationWarning(
                    gen_uid=p.gen_uid,
                    parameter="ramp_rate_mw_per_min",
                    value=p.ramp_rate_mw_per_min,
                    threshold=0.0,
                    message="Ramp rate (MW/min) is negative",
                )
            )

        if p.ramp_rate_mw_per_hr < 0.0:
            warnings.append(
                ParameterValidationWarning(
                    gen_uid=p.gen_uid,
                    parameter="ramp_rate_mw_per_hr",
                    value=p.ramp_rate_mw_per_hr,
                    threshold=0.0,
                    message="Ramp rate (MW/hr) is negative",
                )
            )

        if p.ramp_rate_mw_per_hr > p.pmax_mw:
            warnings.append(
                ParameterValidationWarning(
                    gen_uid=p.gen_uid,
                    parameter="ramp_rate_mw_per_hr",
                    value=p.ramp_rate_mw_per_hr,
                    threshold=p.pmax_mw,
                    message=(
                        f"Ramp rate (MW/hr) {p.ramp_rate_mw_per_hr:.1f}"
                        f" exceeds Pmax {p.pmax_mw:.1f}"
                    ),
                )
            )

        total_updown = p.min_up_time_hr + p.min_down_time_hr
        if total_updown > 24.0:
            warnings.append(
                ParameterValidationWarning(
                    gen_uid=p.gen_uid,
                    parameter="min_up_time_hr+min_down_time_hr",
                    value=total_updown,
                    threshold=24.0,
                    message=f"Min up + min down = {total_updown:.1f}h exceeds 24h",
                )
            )

        if p.pmin_mw > p.pmax_mw:
            warnings.append(
                ParameterValidationWarning(
                    gen_uid=p.gen_uid,
                    parameter="pmin_mw",
                    value=p.pmin_mw,
                    threshold=p.pmax_mw,
                    message=f"Pmin {p.pmin_mw:.1f} exceeds Pmax {p.pmax_mw:.1f}",
                )
            )

    return warnings


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_temporal_params_csv(params: list[TemporalParamRow], dest_path: Path) -> None:
    """Write temporal parameters to a CSV file.

    Columns are ordered per OUTPUT_CSV_COLUMNS. Creates parent directories if needed.

    Args:
        params: List of TemporalParamRow to write.
        dest_path: File path to write the CSV output.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(OUTPUT_CSV_COLUMNS))
    writer.writeheader()

    for p in params:
        row_dict = asdict(p)
        writer.writerow(row_dict)

    dest_path.write_text(output.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Network processing
# ---------------------------------------------------------------------------


def process_network(
    network_id: TemporalNetworkId,
    classification_dir: Path,
    reference_table: dict[str, TechClassRow],
    output_dir: Path,
) -> NetworkTemporalResult:
    """Process a single network: load classification, assign params, write CSV.

    Args:
        network_id: Which network to process.
        classification_dir: Directory containing gen_fuel_classification.csv files.
        reference_table: The loaded reference table.
        output_dir: Directory to write the output CSV.

    Returns:
        A NetworkTemporalResult with all parameters and validation warnings.
    """
    # Load classification
    classification_csv = classification_dir / network_id.value / NETWORK_CLASSIFICATION_FILE
    classifications = load_classification(classification_csv)

    temporal_params: list[TemporalParamRow] = []
    warnings: list[ParameterValidationWarning] = []
    renewable_count = 0
    thermal_count = 0
    fuel_type_counts: dict[str, int] = {}

    for gen in classifications:
        fuel = gen.fuel_type.value
        fuel_type_counts[fuel] = fuel_type_counts.get(fuel, 0) + 1

        if is_renewable(fuel):
            renewable_count += 1
            row = make_renewable_row(gen.gen_uid, gen.pmax_mw, gen.tech_class, fuel)
            temporal_params.append(row)
        else:
            thermal_count += 1
            scaling = assign_temporal_params(gen, reference_table)
            if scaling is None:
                # Tech class not found in reference table — warn and use zeros
                warnings.append(
                    ParameterValidationWarning(
                        gen_uid=gen.gen_uid,
                        parameter="tech_class",
                        value=0.0,
                        threshold=0.0,
                        message=f"Tech class '{gen.tech_class}' not found in reference table",
                    )
                )
                row = make_renewable_row(gen.gen_uid, gen.pmax_mw, gen.tech_class, fuel)
                temporal_params.append(row)
            else:
                row = build_temporal_param_row(gen, scaling)
                temporal_params.append(row)

    # Validate
    validation_warnings = validate_temporal_params(temporal_params)
    warnings.extend(validation_warnings)

    # Write output CSV
    output_network_dir = output_dir / network_id.value
    output_csv_path = output_network_dir / NETWORK_OUTPUT_FILE
    write_temporal_params_csv(temporal_params, output_csv_path)

    return NetworkTemporalResult(
        network_id=network_id,
        generator_count=len(classifications),
        temporal_params=temporal_params,
        renewable_count=renewable_count,
        thermal_count=thermal_count,
        fuel_type_counts=fuel_type_counts,
        validation_warnings=warnings,
        output_csv_path=str(output_csv_path),
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(summary: TemporalAssignmentSummary) -> None:
    """Print a human-readable summary of the temporal parameter assignment.

    Args:
        summary: The complete assignment summary.
    """
    print("=" * 72)
    print("Generator Temporal Parameter Assignment Summary")
    print("=" * 72)
    print(f"Reference table: {summary.reference_table_path}")
    print(f"Script version: {summary.script_version}")
    print()

    for nr in summary.network_results:
        print(f"Network: {nr.network_id.value}")
        print(f"  Generators: {nr.generator_count}")
        print(f"  Thermal: {nr.thermal_count}")
        print(f"  Renewable: {nr.renewable_count}")
        print(f"  Fuel types: {nr.fuel_type_counts}")
        print(f"  Output: {nr.output_csv_path}")
        if nr.validation_warnings:
            print(f"  Warnings ({len(nr.validation_warnings)}):")
            for w in nr.validation_warnings:
                print(f"    - [{w.gen_uid}] {w.message}")
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    classification_dir: Path | None = None,
    reference_csv_path: Path | None = None,
    output_dir: Path | None = None,
) -> TemporalAssignmentSummary:
    """Entry point: assign temporal parameters for all three networks.

    Args:
        classification_dir: Directory containing per-network classification CSVs.
        reference_csv_path: Path to the RTS-GMLC reference table CSV.
        output_dir: Directory for output CSVs.

    Returns:
        The complete TemporalAssignmentSummary.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if classification_dir is None:
        classification_dir = repo_root / "classification"
    if reference_csv_path is None:
        reference_csv_path = repo_root / "reference" / "rts_gmlc_tech_classes.csv"
    if output_dir is None:
        output_dir = repo_root / "timeseries"

    # Load reference table
    reference_table = load_reference_table(reference_csv_path)

    network_results: list[NetworkTemporalResult] = []

    for network_id in TemporalNetworkId:
        classification_csv = classification_dir / network_id.value / NETWORK_CLASSIFICATION_FILE
        if not classification_csv.exists():
            print(
                f"WARNING: Skipping {network_id.value} — "
                f"classification file not found: {classification_csv}",
                file=sys.stderr,
            )
            continue

        result = process_network(
            network_id=network_id,
            classification_dir=classification_dir,
            reference_table=reference_table,
            output_dir=output_dir,
        )
        network_results.append(result)

    summary = TemporalAssignmentSummary(
        network_results=network_results,
        reference_table_path=str(reference_csv_path),
        script_version=__version__,
    )

    print_summary(summary)
    return summary


if __name__ == "__main__":
    main()
