"""Generator Temporal Parameter Assignment for TINY (case39).

Assigns unit commitment and economic dispatch temporal parameters to each of
the 10 generators in the IEEE 39-bus case by looking up RTS-GMLC technology
class templates. The fuel-type classification from Phase 2b D1 maps each
generator to an RtsGmlcClass. This module uses that mapping to retrieve
template parameters (ramp rate, min up/down times, startup costs, no-load cost)
and writes gen_temporal_params.csv.

Ramp rates are scaled linearly by gen Pmax / template Pmax.  Min up/down times
and startup costs are taken directly from the template.  GAS_CC_FLEXIBLE class
(bus 39 interconnection equivalent) gets 1.5x ramp multiplier and 50% min time
reduction (floor 1 hour).

Output artifact:
  - data/timeseries/case39/gen_temporal_params.csv
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.tiny_cleanup_classify import (
    CASE39_CLASSIFICATION_TABLE,
    Case39GenClassification,
    RtsGmlcClass,
)

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FLEXIBLE_RAMP_MULTIPLIER: float = 1.5
FLEXIBLE_MIN_TIME_FRACTION: float = 0.5
MIN_UP_DOWN_TIME_FLOOR_HR: float = 1.0


class TechClassKey(StrEnum):
    """Keys into the RTS-GMLC reference table's tech_class column.

    Each value matches the ``tech_class`` string produced by
    ``build_rts_gmlc_reference.py`` for the relevant fuel/unit-type/band
    combination.
    """

    HYDRO = "hydro"
    NUCLEAR = "nuclear"
    COAL_LARGE = "coal_large"
    GAS_CC = "gas_CC"


# Map each RtsGmlcClass used in the case39 classification to the
# corresponding tech_class key in the reference table.
RTS_GMLC_CLASS_TO_TECH_KEY: dict[RtsGmlcClass, TechClassKey] = {
    RtsGmlcClass.HYDRO_RESERVOIR: TechClassKey.HYDRO,
    RtsGmlcClass.NUCLEAR: TechClassKey.NUCLEAR,
    RtsGmlcClass.COAL_STEAM: TechClassKey.COAL_LARGE,
    RtsGmlcClass.GAS_CC: TechClassKey.GAS_CC,
    RtsGmlcClass.GAS_CC_FLEXIBLE: TechClassKey.GAS_CC,
}


# Default no-load costs ($/hr) by tech class.  These are not in the
# RTS-GMLC reference CSV and must be specified separately.
NO_LOAD_COST_DEFAULTS: dict[TechClassKey, float] = {
    TechClassKey.HYDRO: 0.0,
    TechClassKey.NUCLEAR: 0.0,
    TechClassKey.COAL_LARGE: 450.0,
    TechClassKey.GAS_CC: 600.0,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RtsGmlcTemplateParams:
    """Template parameters for one RTS-GMLC technology class row.

    Loaded from data/reference/rts_gmlc_tech_classes.csv.
    """

    tech_class: str
    pmax_template_mw: float
    ramp_rate_mw_per_min: float
    min_up_time_hr: float
    min_down_time_hr: float
    startup_cost_cold_dollar: float
    startup_cost_warm_dollar: float
    startup_cost_hot_dollar: float


@dataclass(frozen=True)
class GenTemporalParams:
    """Assigned temporal parameters for a single case39 generator."""

    gen_uid: str
    gen_index: int
    bus_id: int
    rts_gmlc_class: str
    tech_class_key: str
    pmax_mw: float
    ramp_rate_mw_per_min: float
    ramp_rate_mw_per_hr: float
    min_up_time_hr: float
    min_down_time_hr: float
    startup_cost_cold_dollar: float
    startup_cost_warm_dollar: float
    startup_cost_hot_dollar: float
    no_load_cost_dollar_per_hr: float


@dataclass(frozen=True)
class TemporalParamsResult:
    """Complete result of temporal parameter assignment for all generators."""

    gen_params: list[GenTemporalParams]
    csv_path: str  # relative path to output CSV


# ---------------------------------------------------------------------------
# Reference table loading
# ---------------------------------------------------------------------------


def load_reference_table(
    csv_path: Path,
) -> dict[str, RtsGmlcTemplateParams]:
    """Load the RTS-GMLC tech class reference table from CSV.

    Reads the reference CSV produced by ``build_rts_gmlc_reference.py``,
    skipping comment lines (starting with ``#``).  Returns a dict keyed by
    ``tech_class`` string.

    Args:
        csv_path: Path to ``rts_gmlc_tech_classes.csv``.

    Returns:
        Dict mapping tech_class string to RtsGmlcTemplateParams.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing.
    """
    if not csv_path.exists():
        msg = f"Reference table not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    # Strip comment lines.
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    content = "\n".join(lines)

    reader = csv.DictReader(io.StringIO(content))
    required = {
        "tech_class",
        "pmax_template_mw",
        "ramp_rate_mw_per_min",
        "min_up_time_hr",
        "min_down_time_hr",
        "startup_cost_cold_dollar",
        "startup_cost_warm_dollar",
        "startup_cost_hot_dollar",
    }

    if reader.fieldnames is None:
        msg = "Reference CSV has no header row"
        raise ValueError(msg)

    missing = required - set(reader.fieldnames)
    if missing:
        msg = f"Reference CSV missing columns: {sorted(missing)}"
        raise ValueError(msg)

    templates: dict[str, RtsGmlcTemplateParams] = {}
    for row in reader:
        tc = row["tech_class"].strip()
        templates[tc] = RtsGmlcTemplateParams(
            tech_class=tc,
            pmax_template_mw=float(row["pmax_template_mw"]),
            ramp_rate_mw_per_min=float(row["ramp_rate_mw_per_min"]),
            min_up_time_hr=float(row["min_up_time_hr"]),
            min_down_time_hr=float(row["min_down_time_hr"]),
            startup_cost_cold_dollar=float(row["startup_cost_cold_dollar"]),
            startup_cost_warm_dollar=float(row["startup_cost_warm_dollar"]),
            startup_cost_hot_dollar=float(row["startup_cost_hot_dollar"]),
        )

    return templates


# ---------------------------------------------------------------------------
# Classification loading
# ---------------------------------------------------------------------------


def load_gen_classification(
    csv_path: Path | None = None,
) -> list[Case39GenClassification]:
    """Load the case39 generator classification table.

    If *csv_path* is ``None``, returns the hardcoded
    ``CASE39_CLASSIFICATION_TABLE`` from ``tiny_cleanup_classify``.
    Otherwise reads the CSV at *csv_path* and reconstructs classification
    records.

    Args:
        csv_path: Optional path to ``gen_classification.csv``.

    Returns:
        List of Case39GenClassification, one per generator.
    """
    if csv_path is None:
        return list(CASE39_CLASSIFICATION_TABLE)

    if not csv_path.exists():
        msg = f"Classification CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    classifications: list[Case39GenClassification] = []
    for row in reader:
        classifications.append(
            Case39GenClassification(
                gen_index=int(row["gen_index"]),
                gen_number=int(row["gen_number"]),
                bus_id=int(row["bus_id"]),
                fuel_category=row["fuel_category"],
                rts_gmlc_class=RtsGmlcClass(row["rts_gmlc_class"]),
                pmax_mw=float(row["pmax_mw"]),
                pmin_mw=float(row["pmin_mw"]),
                classification_source=row["classification_source"],
                rationale=row["rationale"],
            )
        )

    return classifications


# ---------------------------------------------------------------------------
# Parameter computation helpers
# ---------------------------------------------------------------------------


def compute_scaled_ramp_rate(
    template_ramp_mw_per_min: float,
    template_pmax_mw: float,
    gen_pmax_mw: float,
) -> float:
    """Scale ramp rate linearly by capacity ratio.

    ``scaled_ramp = template_ramp * (gen_pmax / template_pmax)``

    Args:
        template_ramp_mw_per_min: Template ramp rate in MW/min.
        template_pmax_mw: Template Pmax in MW.
        gen_pmax_mw: Generator Pmax in MW.

    Returns:
        Scaled ramp rate in MW/min.

    Raises:
        ValueError: If template_pmax_mw is zero or negative.
    """
    if template_pmax_mw <= 0:
        msg = f"Template Pmax must be positive, got {template_pmax_mw}"
        raise ValueError(msg)
    return template_ramp_mw_per_min * (gen_pmax_mw / template_pmax_mw)


def compute_min_times(
    template_min_up_hr: float,
    template_min_down_hr: float,
    is_flexible: bool,
) -> tuple[float, float]:
    """Compute min up and min down times, applying flexible reduction if needed.

    For standard generators, times are taken directly from the template.
    For GAS_CC_FLEXIBLE, times are multiplied by ``FLEXIBLE_MIN_TIME_FRACTION``
    with a floor of ``MIN_UP_DOWN_TIME_FLOOR_HR``.

    Args:
        template_min_up_hr: Template min up time in hours.
        template_min_down_hr: Template min down time in hours.
        is_flexible: Whether to apply the flexible reduction.

    Returns:
        Tuple of (min_up_time_hr, min_down_time_hr).
    """
    if is_flexible:
        min_up = template_min_up_hr * FLEXIBLE_MIN_TIME_FRACTION
        min_down = template_min_down_hr * FLEXIBLE_MIN_TIME_FRACTION
    else:
        min_up = template_min_up_hr
        min_down = template_min_down_hr

    # Apply floor for all generators (hydro templates have 0.0 min times)
    min_up = max(min_up, MIN_UP_DOWN_TIME_FLOOR_HR)
    min_down = max(min_down, MIN_UP_DOWN_TIME_FLOOR_HR)
    return min_up, min_down


def compute_no_load_cost(
    tech_key: TechClassKey,
) -> float:
    """Look up the no-load cost for a technology class.

    Args:
        tech_key: Technology class key.

    Returns:
        No-load cost in $/hr.
    """
    return NO_LOAD_COST_DEFAULTS.get(tech_key, 0.0)


# ---------------------------------------------------------------------------
# Generator UID
# ---------------------------------------------------------------------------


def build_gen_uid(bus_id: int, gen_number: int) -> str:
    """Build a generator UID string.

    Format: ``case39_bus{bus_id}_gen{gen_number}``

    Args:
        bus_id: Bus number the generator is connected to.
        gen_number: 1-based generator number.

    Returns:
        Generator UID string.
    """
    return f"case39_bus{bus_id}_gen{gen_number}"


# ---------------------------------------------------------------------------
# Core assignment
# ---------------------------------------------------------------------------


def assign_temporal_params(
    classification: Case39GenClassification,
    templates: dict[str, RtsGmlcTemplateParams],
) -> GenTemporalParams:
    """Assign temporal parameters to a single generator.

    Looks up the matching RTS-GMLC template, scales ramp rate by capacity,
    applies flexible adjustments for GAS_CC_FLEXIBLE, and assigns no-load cost.

    Args:
        classification: Classification record for this generator.
        templates: Reference table keyed by tech_class string.

    Returns:
        GenTemporalParams for this generator.

    Raises:
        KeyError: If the tech class is not found in templates.
    """
    tech_key = RTS_GMLC_CLASS_TO_TECH_KEY[classification.rts_gmlc_class]
    template = templates[tech_key.value]

    is_flexible = classification.rts_gmlc_class == RtsGmlcClass.GAS_CC_FLEXIBLE

    # Scale ramp rate.
    scaled_ramp = compute_scaled_ramp_rate(
        template.ramp_rate_mw_per_min,
        template.pmax_template_mw,
        classification.pmax_mw,
    )
    # Apply flexible multiplier.
    if is_flexible:
        scaled_ramp *= FLEXIBLE_RAMP_MULTIPLIER

    # Min up/down times.
    min_up, min_down = compute_min_times(
        template.min_up_time_hr,
        template.min_down_time_hr,
        is_flexible=is_flexible,
    )

    # No-load cost.
    no_load = compute_no_load_cost(tech_key)

    gen_uid = build_gen_uid(classification.bus_id, classification.gen_number)

    # Enforce startup cost ordering: cold >= warm >= hot
    cold = template.startup_cost_cold_dollar
    warm = min(template.startup_cost_warm_dollar, cold)
    hot = min(template.startup_cost_hot_dollar, warm)

    return GenTemporalParams(
        gen_uid=gen_uid,
        gen_index=classification.gen_index,
        bus_id=classification.bus_id,
        rts_gmlc_class=classification.rts_gmlc_class.value,
        tech_class_key=tech_key.value,
        pmax_mw=classification.pmax_mw,
        ramp_rate_mw_per_min=scaled_ramp,
        ramp_rate_mw_per_hr=scaled_ramp * 60.0,
        min_up_time_hr=min_up,
        min_down_time_hr=min_down,
        startup_cost_cold_dollar=cold,
        startup_cost_warm_dollar=warm,
        startup_cost_hot_dollar=hot,
        no_load_cost_dollar_per_hr=no_load,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_gen_params(params: GenTemporalParams) -> list[str]:
    """Validate temporal parameters for a single generator.

    Checks:
    - Ramp rate is positive.
    - Min up/down times are >= MIN_UP_DOWN_TIME_FLOOR_HR.
    - Startup costs are non-negative and cold >= warm >= hot.
    - No-load cost is non-negative.

    Args:
        params: Temporal parameters for one generator.

    Returns:
        List of validation error strings (empty if valid).
    """
    errors: list[str] = []
    uid = params.gen_uid

    if params.ramp_rate_mw_per_min <= 0:
        errors.append(f"{uid}: ramp_rate_mw_per_min must be positive")

    if params.min_up_time_hr < MIN_UP_DOWN_TIME_FLOOR_HR:
        errors.append(
            f"{uid}: min_up_time_hr {params.min_up_time_hr} < floor {MIN_UP_DOWN_TIME_FLOOR_HR}"
        )
    if params.min_down_time_hr < MIN_UP_DOWN_TIME_FLOOR_HR:
        errors.append(
            f"{uid}: min_down_time_hr {params.min_down_time_hr} < floor {MIN_UP_DOWN_TIME_FLOOR_HR}"
        )

    if params.startup_cost_cold_dollar < 0:
        errors.append(f"{uid}: startup_cost_cold_dollar must be non-negative")
    if params.startup_cost_warm_dollar < 0:
        errors.append(f"{uid}: startup_cost_warm_dollar must be non-negative")
    if params.startup_cost_hot_dollar < 0:
        errors.append(f"{uid}: startup_cost_hot_dollar must be non-negative")

    if params.startup_cost_cold_dollar < params.startup_cost_warm_dollar:
        errors.append(f"{uid}: cold startup cost < warm startup cost")
    if params.startup_cost_warm_dollar < params.startup_cost_hot_dollar:
        errors.append(f"{uid}: warm startup cost < hot startup cost")

    if params.no_load_cost_dollar_per_hr < 0:
        errors.append(f"{uid}: no_load_cost_dollar_per_hr must be non-negative")

    return errors


def validate_all_params(gen_params: list[GenTemporalParams]) -> list[str]:
    """Validate temporal parameters for all generators.

    Checks individual generator validation plus:
    - Exactly 10 generators.
    - No duplicate gen_index values.

    Args:
        gen_params: List of temporal parameters for all generators.

    Returns:
        List of validation error strings (empty if all valid).
    """
    errors: list[str] = []

    if len(gen_params) != 10:
        errors.append(f"Expected 10 generators, got {len(gen_params)}")

    seen_indices: set[int] = set()
    for params in gen_params:
        if params.gen_index in seen_indices:
            errors.append(f"Duplicate gen_index: {params.gen_index}")
        seen_indices.add(params.gen_index)
        errors.extend(validate_gen_params(params))

    return errors


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

_OUTPUT_COLUMNS = [
    "gen_uid",
    "gen_index",
    "bus_id",
    "rts_gmlc_class",
    "tech_class_key",
    "pmax_mw",
    "ramp_rate_mw_per_min",
    "ramp_rate_mw_per_hr",
    "min_up_time_hr",
    "min_down_time_hr",
    "startup_cost_cold_dollar",
    "startup_cost_warm_dollar",
    "startup_cost_hot_dollar",
    "no_load_cost_dollar_per_hr",
]


def write_gen_temporal_params_csv(
    gen_params: list[GenTemporalParams],
    dest_path: Path,
) -> None:
    """Write generator temporal parameters to CSV.

    Produces a CSV with columns matching ``_OUTPUT_COLUMNS``, one row per
    generator ordered by gen_index.

    Args:
        gen_params: List of GenTemporalParams for all generators.
        dest_path: File path to write the CSV output.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_params = sorted(gen_params, key=lambda p: p.gen_index)

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_OUTPUT_COLUMNS)
        writer.writeheader()
        for p in sorted_params:
            writer.writerow(
                {
                    "gen_uid": p.gen_uid,
                    "gen_index": p.gen_index,
                    "bus_id": p.bus_id,
                    "rts_gmlc_class": p.rts_gmlc_class,
                    "tech_class_key": p.tech_class_key,
                    "pmax_mw": p.pmax_mw,
                    "ramp_rate_mw_per_min": round(p.ramp_rate_mw_per_min, 6),
                    "ramp_rate_mw_per_hr": round(p.ramp_rate_mw_per_hr, 4),
                    "min_up_time_hr": p.min_up_time_hr,
                    "min_down_time_hr": p.min_down_time_hr,
                    "startup_cost_cold_dollar": round(p.startup_cost_cold_dollar, 2),
                    "startup_cost_warm_dollar": round(p.startup_cost_warm_dollar, 2),
                    "startup_cost_hot_dollar": round(p.startup_cost_hot_dollar, 2),
                    "no_load_cost_dollar_per_hr": round(p.no_load_cost_dollar_per_hr, 2),
                }
            )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def assign_all_temporal_params(
    classifications: list[Case39GenClassification],
    templates: dict[str, RtsGmlcTemplateParams],
) -> list[GenTemporalParams]:
    """Assign temporal parameters to all case39 generators.

    Iterates over the classification table, looks up the matching template
    for each generator, and produces a GenTemporalParams record.

    Args:
        classifications: Generator classification table from Phase 2b D1.
        templates: Reference table keyed by tech_class string.

    Returns:
        List of GenTemporalParams, one per generator.

    Raises:
        ValueError: If validation fails for any generator.
    """
    gen_params: list[GenTemporalParams] = []
    for cls in classifications:
        params = assign_temporal_params(cls, templates)
        gen_params.append(params)

    errors = validate_all_params(gen_params)
    if errors:
        msg = "Temporal parameter validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)

    return gen_params


def main(
    reference_csv: Path | None = None,
    output_dir: Path | None = None,
) -> TemporalParamsResult:
    """Entry point: assign temporal parameters and write CSV.

    Orchestrates the full workflow:
    1. Load the RTS-GMLC reference table.
    2. Load the generator classification table.
    3. Assign temporal parameters to each generator.
    4. Validate all parameters.
    5. Write gen_temporal_params.csv.

    Args:
        reference_csv: Path to rts_gmlc_tech_classes.csv.
            Defaults to <repo_root>/data/reference/rts_gmlc_tech_classes.csv.
        output_dir: Base directory for output.
            Defaults to <repo_root>/data/timeseries/case39/.

    Returns:
        TemporalParamsResult with parameters and output path.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if reference_csv is None:
        reference_csv = repo_root / "reference" / "rts_gmlc_tech_classes.csv"
    if output_dir is None:
        output_dir = repo_root / "timeseries" / "case39"

    # 1. Load reference table.
    templates = load_reference_table(reference_csv)

    # 2. Load classification (use hardcoded table).
    classifications = load_gen_classification()

    # 3-4. Assign and validate.
    gen_params = assign_all_temporal_params(classifications, templates)

    # 5. Write CSV.
    csv_path = output_dir / "gen_temporal_params.csv"
    write_gen_temporal_params_csv(gen_params, csv_path)

    return TemporalParamsResult(
        gen_params=gen_params,
        csv_path=str(csv_path),
    )


if __name__ == "__main__":
    main()
