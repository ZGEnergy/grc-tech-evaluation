"""Snapshot Cleanup Script & Manifest for MATPOWER .m case files.

Reads solved power flow snapshots from data/networks/, applies deterministic
cleanup rules (renewable Pmin reset, hydro bimodal Pmin, Pg/Qg clear, bus
voltage normalization), writes cleaned .m files to data/timeseries/<network>/,
and produces a JSON cleanup manifest documenting every modification.

Original .m files in data/networks/ are never modified.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from scripts.reconcile_bus_gen import (
    MatpowerBusRecord,
    MatpowerCaseData,
    MatpowerGenRecord,
    parse_matpower_case,
)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CleanupNetworkId(StrEnum):
    """Identifiers for the three networks in the cleanup scope."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class FuelCategory(StrEnum):
    """Fuel type categories used for cleanup rule dispatch."""

    WIND = "wind"
    SOLAR = "solar"
    HYDRO = "hydro"
    NUCLEAR = "nuclear"
    NG = "ng"
    COAL = "coal"
    UNKNOWN = "unknown"


class CleanupRule(StrEnum):
    """Identifiers for the cleanup rules applied to generators."""

    RENEWABLE_PMIN_RESET = "renewable_pmin_reset"
    HYDRO_RUN_OF_RIVER_PMIN = "hydro_run_of_river_pmin"
    HYDRO_RESERVOIR_PMIN = "hydro_reservoir_pmin"
    PG_RESET = "pg_reset"
    QG_RESET = "qg_reset"


class BusCleanupRule(StrEnum):
    """Identifiers for bus-level cleanup rules."""

    VM_NORMALIZE = "vm_normalize"
    VA_NORMALIZE = "va_normalize"


class FuelClassificationSource(StrEnum):
    """How the fuel type was determined for a generator."""

    GENFUEL_FIELD = "genfuel_field"
    CASE39_HEADER_MAP = "case39_header_map"


@dataclass(frozen=True)
class GeneratorModification:
    """Record of a single field modification on a single generator."""

    gen_index: int
    gen_bus: int
    fuel_type_raw: str | None
    fuel_category: FuelCategory
    classification_source: FuelClassificationSource
    rule: CleanupRule
    field_name: str
    before_value: float
    after_value: float


@dataclass(frozen=True)
class BusModification:
    """Record of a single field modification on a single bus."""

    bus_index: int
    bus_id: int
    rule: BusCleanupRule
    field_name: str
    before_value: float
    after_value: float


@dataclass(frozen=True)
class GeneratorClassification:
    """Fuel type classification for a single generator."""

    gen_index: int
    gen_bus: int
    fuel_type_raw: str | None
    fuel_category: FuelCategory
    classification_source: FuelClassificationSource
    pmax: float
    hydro_subclass: str | None


@dataclass(frozen=True)
class FuelTypeSummary:
    """Count of generators by fuel category for a single network."""

    category: FuelCategory
    count: int
    pmax_total_mw: float


@dataclass(frozen=True)
class RuleSummary:
    """Count of modifications by rule for a single network."""

    rule: str
    modification_count: int


@dataclass(frozen=True)
class NetworkCleanupManifest:
    """Complete cleanup manifest for a single network."""

    network_id: CleanupNetworkId
    source_m_file: str
    cleaned_m_file: str
    bus_count: int
    generator_count: int
    fuel_type_summary: list[FuelTypeSummary]
    rule_summary: list[RuleSummary]
    generator_classifications: list[GeneratorClassification]
    generator_modifications: list[GeneratorModification]
    bus_modifications: list[BusModification]


@dataclass(frozen=True)
class CleanupManifest:
    """Top-level cleanup manifest covering all networks."""

    networks: list[NetworkCleanupManifest]
    script_version: str
    generated_at: str
    cleanup_rules_doc: dict[str, str]
    hydro_threshold_mw: float
    hydro_reservoir_pmin_fraction: float

    @staticmethod
    def rules_documentation() -> dict[str, str]:
        """Return human-readable descriptions of all cleanup rules."""
        return {
            "renewable_pmin_reset": "Wind and solar generators: Pmin set to 0 MW",
            "hydro_run_of_river_pmin": ("Hydro generators with Pmax < threshold: Pmin set to 0 MW"),
            "hydro_reservoir_pmin": (
                "Hydro generators with Pmax >= threshold: Pmin set to fraction * Pmax"
            ),
            "pg_reset": "All generators: Pg set to 0 MW",
            "qg_reset": "All generators: Qg set to 0 MVAr",
            "vm_normalize": "All buses: Vm set to 1.0 pu",
            "va_normalize": "All buses: Va set to 0 degrees",
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HYDRO_THRESHOLD_MW: float = 30.0
"""Pmax threshold (MW) separating run-of-river from reservoir hydro."""

HYDRO_RESERVOIR_PMIN_FRACTION: float = 0.25
"""Fraction of Pmax used as Pmin for reservoir hydro generators."""

CASE39_FUEL_MAP: dict[int, FuelCategory] = {
    0: FuelCategory.HYDRO,
    1: FuelCategory.NUCLEAR,
    2: FuelCategory.NUCLEAR,
    3: FuelCategory.NG,
    4: FuelCategory.NG,
    5: FuelCategory.NUCLEAR,
    6: FuelCategory.NG,
    7: FuelCategory.NUCLEAR,
    8: FuelCategory.NUCLEAR,
    9: FuelCategory.NG,
}
"""Fuel type mapping for case39 generators, derived from the file header."""

NETWORK_M_FILE_NAMES: dict[CleanupNetworkId, str] = {
    CleanupNetworkId.TINY: "case39.m",
    CleanupNetworkId.SMALL: "case_ACTIVSg2000.m",
    CleanupNetworkId.MEDIUM: "case_ACTIVSg10k.m",
}
"""Mapping from network ID to the .m file name in data/networks/."""

# Mapping from lowercase fuel string keywords to FuelCategory.
_FUEL_KEYWORD_MAP: dict[str, FuelCategory] = {
    "wind": FuelCategory.WIND,
    "solar": FuelCategory.SOLAR,
    "hydro": FuelCategory.HYDRO,
    "ng": FuelCategory.NG,
    "coal": FuelCategory.COAL,
    "nuclear": FuelCategory.NUCLEAR,
}

# MATPOWER bus matrix column indices (0-based).
_BUS_COL_VM = 7
_BUS_COL_VA = 8

# MATPOWER gen matrix column indices (0-based).
_GEN_COL_BUS = 0
_GEN_COL_PG = 1
_GEN_COL_QG = 2
_GEN_COL_PMAX = 8
_GEN_COL_PMIN = 9


# ---------------------------------------------------------------------------
# Fuel classification
# ---------------------------------------------------------------------------


def classify_genfuel_string(raw_fuel: str) -> FuelCategory:
    """Map a raw genfuel string to a FuelCategory.

    Handles the standard MATPOWER genfuel labels ('wind', 'solar',
    'hydro', 'ng', 'coal', 'nuclear') as well as non-standard labels
    found in the ACTIVSg cases. Non-standard labels that do not match
    any known fuel keyword are classified as UNKNOWN.

    Args:
        raw_fuel: The genfuel string from the .m file, stripped of
            surrounding quotes and whitespace.

    Returns:
        The corresponding FuelCategory.
    """
    normalized = raw_fuel.strip().lower()
    if normalized in _FUEL_KEYWORD_MAP:
        return _FUEL_KEYWORD_MAP[normalized]
    return FuelCategory.UNKNOWN


def classify_generators(
    case_data: MatpowerCaseData,
    network_id: CleanupNetworkId,
) -> list[GeneratorClassification]:
    """Classify all generators in a parsed case by fuel type.

    For ACTIVSg cases (SMALL, MEDIUM), reads fuel types from the
    genfuel field via classify_genfuel_string. For TINY (case39),
    uses CASE39_FUEL_MAP.

    Args:
        case_data: Parsed MATPOWER case data.
        network_id: Which network this case belongs to.

    Returns:
        A list of GeneratorClassification, one per generator.

    Raises:
        ValueError: If genfuel count doesn't match generator count.
        ValueError: If network_id is TINY and generator count doesn't
            match CASE39_FUEL_MAP.
    """
    classifications: list[GeneratorClassification] = []

    for i, gen in enumerate(case_data.generators):
        if network_id == CleanupNetworkId.TINY:
            if len(case_data.generators) != len(CASE39_FUEL_MAP):
                msg = (
                    f"case39 has {len(case_data.generators)} generators but "
                    f"CASE39_FUEL_MAP has {len(CASE39_FUEL_MAP)} entries"
                )
                raise ValueError(msg)
            fuel_category = CASE39_FUEL_MAP[i]
            source = FuelClassificationSource.CASE39_HEADER_MAP
            fuel_type_raw = None
        else:
            if case_data.has_genfuel:
                genfuel_count = sum(1 for g in case_data.generators if g.fuel_type is not None)
                if genfuel_count != len(case_data.generators):
                    msg = (
                        f"genfuel has {genfuel_count} entries but case has "
                        f"{len(case_data.generators)} generators"
                    )
                    raise ValueError(msg)
            fuel_type_raw = gen.fuel_type
            if fuel_type_raw is not None:
                fuel_category = classify_genfuel_string(fuel_type_raw)
            else:
                fuel_category = FuelCategory.UNKNOWN
            source = FuelClassificationSource.GENFUEL_FIELD

        # Determine hydro subclass
        hydro_subclass: str | None = None
        if fuel_category == FuelCategory.HYDRO:
            if gen.pmax < HYDRO_THRESHOLD_MW:
                hydro_subclass = "run_of_river"
            else:
                hydro_subclass = "reservoir"

        classifications.append(
            GeneratorClassification(
                gen_index=i,
                gen_bus=gen.gen_bus,
                fuel_type_raw=fuel_type_raw,
                fuel_category=fuel_category,
                classification_source=source,
                pmax=gen.pmax,
                hydro_subclass=hydro_subclass,
            )
        )

    return classifications


# ---------------------------------------------------------------------------
# Cleanup application
# ---------------------------------------------------------------------------


def apply_generator_cleanup(
    case_data: MatpowerCaseData,
    classifications: list[GeneratorClassification],
) -> tuple[list[MatpowerGenRecord], list[GeneratorModification]]:
    """Apply generator-level cleanup rules to all generators.

    Creates new MatpowerGenRecord instances with modified values and
    records every modification where before != after.

    Args:
        case_data: The original parsed case data.
        classifications: Generator classifications from classify_generators.

    Returns:
        A tuple of (cleaned_generators, modifications).
    """
    cleaned: list[MatpowerGenRecord] = []
    modifications: list[GeneratorModification] = []

    for i, (gen, cls) in enumerate(zip(case_data.generators, classifications)):
        new_pmin = gen.pmin
        new_pg = gen.pg
        new_qg = gen.qg

        pmin_rule: CleanupRule | None = None

        # Rule 1: Renewable Pmin reset (wind, solar)
        if cls.fuel_category in (FuelCategory.WIND, FuelCategory.SOLAR):
            new_pmin = 0.0
            pmin_rule = CleanupRule.RENEWABLE_PMIN_RESET

        # Rule 2: Hydro bimodal Pmin
        elif cls.fuel_category == FuelCategory.HYDRO:
            if cls.hydro_subclass == "run_of_river":
                new_pmin = 0.0
                pmin_rule = CleanupRule.HYDRO_RUN_OF_RIVER_PMIN
            else:
                new_pmin = HYDRO_RESERVOIR_PMIN_FRACTION * gen.pmax
                pmin_rule = CleanupRule.HYDRO_RESERVOIR_PMIN

        # Rule 3: Pg/Qg reset (all generators)
        new_pg = 0.0
        new_qg = 0.0

        # Record Pmin modification if changed
        if pmin_rule is not None and gen.pmin != new_pmin:
            modifications.append(
                GeneratorModification(
                    gen_index=i,
                    gen_bus=gen.gen_bus,
                    fuel_type_raw=cls.fuel_type_raw,
                    fuel_category=cls.fuel_category,
                    classification_source=cls.classification_source,
                    rule=pmin_rule,
                    field_name="Pmin",
                    before_value=gen.pmin,
                    after_value=new_pmin,
                )
            )

        # Record Pg modification if changed
        if gen.pg != new_pg:
            modifications.append(
                GeneratorModification(
                    gen_index=i,
                    gen_bus=gen.gen_bus,
                    fuel_type_raw=cls.fuel_type_raw,
                    fuel_category=cls.fuel_category,
                    classification_source=cls.classification_source,
                    rule=CleanupRule.PG_RESET,
                    field_name="Pg",
                    before_value=gen.pg,
                    after_value=new_pg,
                )
            )

        # Record Qg modification if changed
        if gen.qg != new_qg:
            modifications.append(
                GeneratorModification(
                    gen_index=i,
                    gen_bus=gen.gen_bus,
                    fuel_type_raw=cls.fuel_type_raw,
                    fuel_category=cls.fuel_category,
                    classification_source=cls.classification_source,
                    rule=CleanupRule.QG_RESET,
                    field_name="Qg",
                    before_value=gen.qg,
                    after_value=new_qg,
                )
            )

        cleaned.append(
            MatpowerGenRecord(
                gen_bus=gen.gen_bus,
                pg=new_pg,
                qg=new_qg,
                pmax=gen.pmax,
                pmin=new_pmin,
                fuel_type=gen.fuel_type,
            )
        )

    return cleaned, modifications


def apply_bus_cleanup(
    case_data: MatpowerCaseData,
) -> tuple[list[MatpowerBusRecord], list[BusModification]]:
    """Apply bus-level cleanup rules to all buses.

    Creates new MatpowerBusRecord instances with Vm set to 1.0 pu
    and Va set to 0 degrees. Records every modification where the
    before value differs from the target.

    Note: MatpowerBusRecord does not store Vm/Va fields, so this
    function returns the original bus records unchanged. The actual
    Vm/Va replacement is done at the text level in write_matpower_case.
    Bus modifications are tracked by parsing the raw .m file text.

    Args:
        case_data: The original parsed case data.

    Returns:
        A tuple of (cleaned_buses, modifications).
    """
    # MatpowerBusRecord doesn't carry Vm/Va, so we return buses as-is.
    # The actual Vm/Va values are replaced in write_matpower_case via text
    # substitution. To record modifications, we need to parse the raw file
    # and extract Vm/Va values. This is handled separately.
    return list(case_data.buses), []


def _extract_bus_vm_va(m_file_text: str) -> list[tuple[float, float]]:
    """Extract Vm (col 7) and Va (col 8) from bus matrix text.

    Returns:
        List of (Vm, Va) tuples, one per bus row.
    """
    pattern = re.compile(
        r"mpc\.bus\s*=\s*\[([^\]]*)\]",
        re.DOTALL,
    )
    match = pattern.search(m_file_text)
    if match is None:
        msg = "Could not locate mpc.bus block"
        raise ValueError(msg)

    block = match.group(1)
    results: list[tuple[float, float]] = []
    for line in block.split(";"):
        line = line.strip()
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        values = line.split()
        try:
            float_vals = [float(v) for v in values]
        except ValueError:
            continue
        if len(float_vals) > _BUS_COL_VA:
            results.append((float_vals[_BUS_COL_VM], float_vals[_BUS_COL_VA]))
    return results


def compute_bus_modifications(
    case_data: MatpowerCaseData,
    m_file_text: str,
) -> list[BusModification]:
    """Compute bus modification records by reading Vm/Va from raw .m text.

    Args:
        case_data: Parsed case data (for bus IDs).
        m_file_text: Raw .m file text content.

    Returns:
        List of BusModification records for Vm/Va changes.
    """
    vm_va_values = _extract_bus_vm_va(m_file_text)
    modifications: list[BusModification] = []

    for i, (bus, (vm, va)) in enumerate(zip(case_data.buses, vm_va_values)):
        if vm != 1.0:
            modifications.append(
                BusModification(
                    bus_index=i,
                    bus_id=bus.bus_id,
                    rule=BusCleanupRule.VM_NORMALIZE,
                    field_name="Vm",
                    before_value=vm,
                    after_value=1.0,
                )
            )
        if va != 0.0:
            modifications.append(
                BusModification(
                    bus_index=i,
                    bus_id=bus.bus_id,
                    rule=BusCleanupRule.VA_NORMALIZE,
                    field_name="Va",
                    before_value=va,
                    after_value=0.0,
                )
            )

    return modifications


# ---------------------------------------------------------------------------
# .m file writing
# ---------------------------------------------------------------------------


def _format_value(val: float) -> str:
    """Format a float for MATPOWER .m file output.

    Uses integer format for whole numbers, otherwise up to 6 decimal places
    with trailing zeros stripped.
    """
    if val == int(val):
        return str(int(val))
    formatted = f"{val:.6f}".rstrip("0").rstrip(".")
    return formatted


def _replace_matrix_block(
    text: str,
    field_name: str,
    column_replacements: dict[int, list[float]],
) -> str:
    """Replace specific columns in a MATPOWER matrix block.

    Reads the mpc.<field_name> block from the text, replaces the specified
    columns with new values while preserving all other columns and the
    overall formatting structure, and returns the modified text.

    Args:
        text: Full .m file text.
        field_name: MATPOWER field name (e.g., "bus", "gen").
        column_replacements: Mapping from 0-based column index to a list
            of new values (one per row).

    Returns:
        Modified .m file text with replaced values.
    """
    pattern = re.compile(
        rf"(mpc\.{re.escape(field_name)}\s*=\s*\[)([^\]]*)(\])",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        msg = f"Could not locate mpc.{field_name} block"
        raise ValueError(msg)

    block = match.group(2)
    new_lines: list[str] = []
    row_idx = 0

    for line in block.split(";"):
        # Preserve empty/comment-only lines
        stripped = line.strip()
        if "%" in stripped:
            comment_pos = stripped.index("%")
            data_part = stripped[:comment_pos].strip()
            comment_part = stripped[comment_pos:]
        else:
            data_part = stripped
            comment_part = ""

        if not data_part:
            # Preserve line as-is (empty or comment-only)
            new_lines.append(line)
            continue

        values = data_part.split()
        try:
            float_vals = [float(v) for v in values]
        except ValueError:
            new_lines.append(line)
            continue

        # Replace specified columns
        for col_idx, replacement_values in column_replacements.items():
            if col_idx < len(float_vals) and row_idx < len(replacement_values):
                float_vals[col_idx] = replacement_values[row_idx]

        # Reconstruct the line with new values, preserving leading whitespace
        leading_ws = ""
        for ch in line:
            if ch in (" ", "\t"):
                leading_ws += ch
            else:
                break

        new_values_str = "\t".join(_format_value(v) for v in float_vals)
        if comment_part:
            new_line = f"{leading_ws}{new_values_str}\t{comment_part}"
        else:
            new_line = f"{leading_ws}{new_values_str}"

        new_lines.append(new_line)
        row_idx += 1

    new_block = ";".join(new_lines)
    return text[: match.start(2)] + new_block + text[match.end(2) :]


def write_matpower_case(
    source_path: Path,
    dest_path: Path,
    cleaned_buses: list[MatpowerBusRecord],
    cleaned_generators: list[MatpowerGenRecord],
) -> None:
    """Write a cleaned MATPOWER .m file preserving all original sections.

    Reads the original .m file as text, replaces the numeric values
    in the mpc.bus and mpc.gen matrix blocks with cleaned values while
    preserving all other sections verbatim.

    Args:
        source_path: Path to the original .m file.
        dest_path: Path to write the cleaned .m file.
        cleaned_buses: Bus records (used for count validation).
        cleaned_generators: Generator records with cleaned values.

    Raises:
        FileNotFoundError: If source_path does not exist.
        ValueError: If counts don't match.
    """
    if not source_path.exists():
        msg = f"Source .m file not found: {source_path}"
        raise FileNotFoundError(msg)

    text = source_path.read_text()

    # Validate row counts
    bus_block = re.search(r"mpc\.bus\s*=\s*\[([^\]]*)\]", text, re.DOTALL)
    gen_block = re.search(r"mpc\.gen\s*=\s*\[([^\]]*)\]", text, re.DOTALL)

    if bus_block is None or gen_block is None:
        msg = "Could not locate mpc.bus or mpc.gen blocks in source file"
        raise ValueError(msg)

    # Count data rows in bus block
    bus_row_count = 0
    for line in bus_block.group(1).split(";"):
        stripped = line.strip()
        if "%" in stripped:
            stripped = stripped[: stripped.index("%")].strip()
        if stripped:
            try:
                [float(v) for v in stripped.split()]
                bus_row_count += 1
            except ValueError:
                pass

    gen_row_count = 0
    for line in gen_block.group(1).split(";"):
        stripped = line.strip()
        if "%" in stripped:
            stripped = stripped[: stripped.index("%")].strip()
        if stripped:
            try:
                [float(v) for v in stripped.split()]
                gen_row_count += 1
            except ValueError:
                pass

    if len(cleaned_buses) != bus_row_count:
        msg = (
            f"Bus count mismatch: {len(cleaned_buses)} cleaned buses "
            f"vs {bus_row_count} rows in source file"
        )
        raise ValueError(msg)

    if len(cleaned_generators) != gen_row_count:
        msg = (
            f"Generator count mismatch: {len(cleaned_generators)} cleaned "
            f"generators vs {gen_row_count} rows in source file"
        )
        raise ValueError(msg)

    # Replace bus Vm (col 7) and Va (col 8)
    bus_vm_values = [1.0] * len(cleaned_buses)
    bus_va_values = [0.0] * len(cleaned_buses)
    text = _replace_matrix_block(
        text, "bus", {_BUS_COL_VM: bus_vm_values, _BUS_COL_VA: bus_va_values}
    )

    # Replace gen Pg (col 1), Qg (col 2), Pmax (col 8), Pmin (col 9)
    gen_pg_values = [g.pg for g in cleaned_generators]
    gen_qg_values = [g.qg for g in cleaned_generators]
    gen_pmax_values = [g.pmax for g in cleaned_generators]
    gen_pmin_values = [g.pmin for g in cleaned_generators]
    text = _replace_matrix_block(
        text,
        "gen",
        {
            _GEN_COL_PG: gen_pg_values,
            _GEN_COL_QG: gen_qg_values,
            _GEN_COL_PMAX: gen_pmax_values,
            _GEN_COL_PMIN: gen_pmin_values,
        },
    )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(text)


# ---------------------------------------------------------------------------
# Manifest construction
# ---------------------------------------------------------------------------


def build_network_manifest(
    network_id: CleanupNetworkId,
    source_path: Path,
    dest_path: Path,
    case_data: MatpowerCaseData,
    classifications: list[GeneratorClassification],
    gen_modifications: list[GeneratorModification],
    bus_modifications: list[BusModification],
) -> NetworkCleanupManifest:
    """Assemble the cleanup manifest for a single network.

    Args:
        network_id: Which network was cleaned.
        source_path: Path to the original .m file.
        dest_path: Path to the cleaned .m file.
        case_data: The original parsed case data.
        classifications: Generator classifications.
        gen_modifications: All generator-level modifications.
        bus_modifications: All bus-level modifications.

    Returns:
        A NetworkCleanupManifest with full modification details.
    """
    # Compute fuel type summary
    fuel_counts: Counter[FuelCategory] = Counter()
    fuel_pmax: dict[FuelCategory, float] = {}
    for cls in classifications:
        fuel_counts[cls.fuel_category] += 1
        fuel_pmax[cls.fuel_category] = fuel_pmax.get(cls.fuel_category, 0.0) + cls.pmax

    fuel_type_summary = sorted(
        [
            FuelTypeSummary(
                category=cat,
                count=count,
                pmax_total_mw=fuel_pmax.get(cat, 0.0),
            )
            for cat, count in fuel_counts.items()
        ],
        key=lambda s: s.category.value,
    )

    # Compute rule summary
    all_rules: list[str] = []
    for mod in gen_modifications:
        all_rules.append(mod.rule.value)
    for mod in bus_modifications:
        all_rules.append(mod.rule.value)

    rule_counts = Counter(all_rules)
    rule_summary = sorted(
        [RuleSummary(rule=rule, modification_count=count) for rule, count in rule_counts.items()],
        key=lambda s: s.rule,
    )

    return NetworkCleanupManifest(
        network_id=network_id,
        source_m_file=str(source_path),
        cleaned_m_file=str(dest_path),
        bus_count=len(case_data.buses),
        generator_count=len(case_data.generators),
        fuel_type_summary=fuel_type_summary,
        rule_summary=rule_summary,
        generator_classifications=classifications,
        generator_modifications=gen_modifications,
        bus_modifications=bus_modifications,
    )


def build_cleanup_manifest(
    network_manifests: list[NetworkCleanupManifest],
    *,
    script_version: str = "0.1.0",
) -> CleanupManifest:
    """Assemble the top-level cleanup manifest from per-network manifests.

    Args:
        network_manifests: List of NetworkCleanupManifest.
        script_version: Version string for the cleanup script.

    Returns:
        A CleanupManifest with all network manifests.
    """
    return CleanupManifest(
        networks=network_manifests,
        script_version=script_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cleanup_rules_doc=CleanupManifest.rules_documentation(),
        hydro_threshold_mw=HYDRO_THRESHOLD_MW,
        hydro_reservoir_pmin_fraction=HYDRO_RESERVOIR_PMIN_FRACTION,
    )


def _serialize_value(obj: object) -> object:
    """Convert non-JSON-serializable types for JSON output."""
    if isinstance(obj, StrEnum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def write_cleanup_manifest(
    manifest: CleanupManifest,
    dest_path: Path,
) -> None:
    """Serialize a CleanupManifest to a human-readable JSON file.

    Args:
        manifest: The cleanup manifest to serialize.
        dest_path: File path to write the JSON output.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(manifest)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize_value)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def clean_network(
    network_id: CleanupNetworkId,
    networks_dir: Path,
    output_dir: Path,
) -> NetworkCleanupManifest:
    """Run the full cleanup pipeline for a single network.

    Args:
        network_id: Which network to clean.
        networks_dir: Path to the data/networks/ directory.
        output_dir: Base directory for output.

    Returns:
        A NetworkCleanupManifest documenting all changes.

    Raises:
        FileNotFoundError: If the .m file is not found.
    """
    m_file_name = NETWORK_M_FILE_NAMES[network_id]
    source_path = networks_dir / m_file_name

    if not source_path.exists():
        msg = f"MATPOWER .m file not found: {source_path}"
        raise FileNotFoundError(msg)

    # Parse the case
    case_data = parse_matpower_case(source_path)

    # Read raw text for bus Vm/Va extraction
    m_file_text = source_path.read_text()

    # Classify generators
    classifications = classify_generators(case_data, network_id)

    # Apply cleanup rules
    cleaned_generators, gen_modifications = apply_generator_cleanup(case_data, classifications)
    cleaned_buses, _ = apply_bus_cleanup(case_data)

    # Compute bus modifications from raw text
    bus_modifications = compute_bus_modifications(case_data, m_file_text)

    # Write cleaned .m file
    dest_dir = output_dir / network_id.value
    dest_path = dest_dir / m_file_name
    write_matpower_case(source_path, dest_path, cleaned_buses, cleaned_generators)

    # Build network manifest
    return build_network_manifest(
        network_id=network_id,
        source_path=source_path,
        dest_path=dest_path,
        case_data=case_data,
        classifications=classifications,
        gen_modifications=gen_modifications,
        bus_modifications=bus_modifications,
    )


def main(
    networks_dir: Path | None = None,
    output_base_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> CleanupManifest:
    """Entry point: clean all three networks and write the manifest.

    Args:
        networks_dir: Directory containing original .m files.
        output_base_dir: Base directory for cleaned output files.
        manifest_path: Where to write the cleanup manifest JSON.

    Returns:
        The complete CleanupManifest.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if networks_dir is None:
        networks_dir = repo_root / "networks"
    if output_base_dir is None:
        output_base_dir = repo_root / "timeseries"
    if manifest_path is None:
        manifest_path = repo_root / "timeseries" / "cleanup_manifest.json"

    network_manifests: list[NetworkCleanupManifest] = []
    for network_id in CleanupNetworkId:
        manifest = clean_network(network_id, networks_dir, output_base_dir)
        network_manifests.append(manifest)

    cleanup_manifest = build_cleanup_manifest(network_manifests, script_version=__version__)
    write_cleanup_manifest(cleanup_manifest, manifest_path)

    return cleanup_manifest


if __name__ == "__main__":
    main()
