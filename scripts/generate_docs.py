"""Dataset Documentation & CLAUDE.md Update (PRD 05/08).

Produces ``data/timeseries/README.md`` (comprehensive dataset documentation)
and updates ``CLAUDE.md`` with an "Augmented Data" section. Both generated
by this script.

All core logic uses only Python stdlib modules.
"""

from __future__ import annotations

import csv
import logging
import re
import textwrap
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


@dataclass(frozen=True)
class ColumnDocEntry:
    """Documentation for a single CSV column."""

    name: str
    dtype: str  # "int", "float", "str", "bool"
    unit: str
    description: str


@dataclass(frozen=True)
class FileTypeDoc:
    """Documentation for one CSV file type."""

    file_type: str
    filename: str
    description: str
    columns: list[ColumnDocEntry]
    row_semantics: str


@dataclass(frozen=True)
class NetworkSummary:
    """Computed summary statistics for a single network."""

    network_id: NetworkId
    display_name: str
    bus_count: int
    gen_count: int
    branch_count: int
    peak_load_mw: float
    total_renewable_capacity_mw: float
    renewable_penetration_pct: float
    bess_unit_count: int
    total_bess_power_mw: float
    total_bess_energy_mwh: float
    dr_bus_count: int
    total_dr_curtailment_mw: float
    flowgate_count: int
    scenario_count_wind: int
    scenario_count_solar: int


@dataclass(frozen=True)
class ProvenanceEntry:
    """Provenance record for a data source."""

    source_name: str
    provider: str
    url: str
    version: str
    license: str
    citation: str
    networks_used: list[NetworkId]
    notes: str


@dataclass(frozen=True)
class KnownLimitation:
    """A documented limitation of the augmented dataset."""

    title: str
    description: str
    affected_networks: list[NetworkId] | None
    mitigation: str


@dataclass(frozen=True)
class RegenerationStep:
    """One step in the data regeneration procedure."""

    step_number: int
    script_path: str
    description: str
    prerequisites: list[str]
    estimated_runtime: str


@dataclass(frozen=True)
class DirectoryTreeEntry:
    """One entry in the directory tree listing."""

    relative_path: str
    is_directory: bool
    annotation: str
    indent_level: int


@dataclass(frozen=True)
class ReadmeContent:
    """All content needed to render the README."""

    title: str
    introduction: str
    directory_tree: list[DirectoryTreeEntry]
    file_type_docs: list[FileTypeDoc]
    network_summaries: list[NetworkSummary]
    methodology_sections: dict[str, str]
    provenance_entries: list[ProvenanceEntry]
    known_limitations: list[KnownLimitation]
    regeneration_steps: list[RegenerationStep]
    validation_instructions: str
    manifest_reference: str


@dataclass(frozen=True)
class ClaudeMdUpdate:
    """Content for the CLAUDE.md Augmented Data section."""

    section_heading: str  # "Augmented Data"
    directory_overview: str
    scripts_overview: str
    csv_conventions: str
    validation_command: str
    manifest_location: str
    readme_pointer: str


# ---------------------------------------------------------------------------
# Directory tree
# ---------------------------------------------------------------------------


def walk_timeseries_tree(timeseries_base_dir: Path) -> list[DirectoryTreeEntry]:
    """Walk the timeseries directory and return sorted entries.

    Args:
        timeseries_base_dir: Root directory of the timeseries data.

    Returns:
        Sorted list of DirectoryTreeEntry for every file and directory found.
    """
    entries: list[DirectoryTreeEntry] = []
    if not timeseries_base_dir.is_dir():
        return entries

    base = timeseries_base_dir

    def _walk(directory: Path, depth: int) -> None:
        children = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        for child in children:
            rel = str(child.relative_to(base))
            if child.is_dir():
                entries.append(
                    DirectoryTreeEntry(
                        relative_path=rel,
                        is_directory=True,
                        annotation=f"{child.name}/",
                        indent_level=depth,
                    )
                )
                _walk(child, depth + 1)
            else:
                entries.append(
                    DirectoryTreeEntry(
                        relative_path=rel,
                        is_directory=False,
                        annotation=child.name,
                        indent_level=depth,
                    )
                )

    _walk(base, 0)
    return entries


def render_directory_tree(entries: list[DirectoryTreeEntry]) -> str:
    """Render directory tree entries as a Markdown fenced code block.

    Args:
        entries: List of DirectoryTreeEntry to render.

    Returns:
        Markdown string with fenced code block.
    """
    lines = ["```"]
    lines.append("data/timeseries/")
    for entry in entries:
        indent = "  " * (entry.indent_level + 1)
        lines.append(f"{indent}{entry.annotation}")
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File type documentation
# ---------------------------------------------------------------------------

_HR_COLS: list[ColumnDocEntry] = [
    ColumnDocEntry(
        name=f"HR_{h}",
        dtype="float",
        unit="MW",
        description=f"Load/generation value for hour-ending {h}",
    )
    for h in range(1, 25)
]

_HR_COLS_DIMENSIONLESS: list[ColumnDocEntry] = [
    ColumnDocEntry(
        name=f"HR_{h}",
        dtype="float",
        unit="dimensionless",
        description=f"Scenario multiplier for hour-ending {h}",
    )
    for h in range(1, 25)
]

_HR_COLS_RESERVE: list[ColumnDocEntry] = [
    ColumnDocEntry(
        name=f"HR_{h}",
        dtype="float",
        unit="MW",
        description=f"Reserve requirement for hour-ending {h}",
    )
    for h in range(1, 25)
]


def build_file_type_docs() -> list[FileTypeDoc]:
    """Build documentation for all 13 CSV file types.

    Returns:
        List of 13 FileTypeDoc entries covering every CSV type in the schema.
    """
    return [
        FileTypeDoc(
            file_type="load_24h",
            filename="load_24h.csv",
            description="Hourly load profile for each bus over 24 hours.",
            columns=[
                ColumnDocEntry("bus_id", "int", "none", "Bus identifier"),
                *_HR_COLS,
            ],
            row_semantics="One row per bus with non-zero load.",
        ),
        FileTypeDoc(
            file_type="wind_forecast_24h",
            filename="wind_forecast_24h.csv",
            description="Day-ahead wind generation forecast for each wind generator.",
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                *_HR_COLS,
            ],
            row_semantics="One row per wind generator.",
        ),
        FileTypeDoc(
            file_type="wind_actual_24h",
            filename="wind_actual_24h.csv",
            description="Actual (realised) wind generation for each wind generator.",
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                *_HR_COLS,
            ],
            row_semantics="One row per wind generator.",
        ),
        FileTypeDoc(
            file_type="solar_forecast_24h",
            filename="solar_forecast_24h.csv",
            description="Day-ahead solar generation forecast for each solar generator.",
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                *_HR_COLS,
            ],
            row_semantics="One row per solar generator.",
        ),
        FileTypeDoc(
            file_type="solar_actual_24h",
            filename="solar_actual_24h.csv",
            description="Actual (realised) solar generation for each solar generator.",
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                *_HR_COLS,
            ],
            row_semantics="One row per solar generator.",
        ),
        FileTypeDoc(
            file_type="gen_temporal_params",
            filename="gen_temporal_params.csv",
            description=(
                "Generator temporal parameters including capacity limits, ramp rates, "
                "minimum up/down times, and costs."
            ),
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                ColumnDocEntry("pmax", "float", "MW", "Maximum power output"),
                ColumnDocEntry("pmin", "float", "MW", "Minimum power output"),
                ColumnDocEntry("ramp_rate", "float", "MW/min", "Ramp rate limit"),
                ColumnDocEntry("min_up_time", "float", "hours", "Minimum up time"),
                ColumnDocEntry("min_down_time", "float", "hours", "Minimum down time"),
                ColumnDocEntry("startup_cost", "float", "$/start", "Startup cost"),
                ColumnDocEntry("shutdown_cost", "float", "$/start", "Shutdown cost"),
                ColumnDocEntry("marginal_cost", "float", "$/MWh", "Marginal cost"),
                ColumnDocEntry("fuel_type", "str", "none", "Fuel type classification"),
                ColumnDocEntry("unit_type", "str", "none", "Unit type classification"),
            ],
            row_semantics="One row per generator.",
        ),
        FileTypeDoc(
            file_type="gen_fuel_classification",
            filename="gen_fuel_classification.csv",
            description=(
                "Generator fuel type classification mapping generators to fuel categories "
                "and renewable status."
            ),
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                ColumnDocEntry("fuel_type", "str", "none", "Primary fuel type"),
                ColumnDocEntry(
                    "is_renewable", "bool", "none", "Whether generator is renewable"
                ),
            ],
            row_semantics="One row per generator.",
        ),
        FileTypeDoc(
            file_type="reserve_requirements_24h",
            filename="reserve_requirements_24h.csv",
            description="Hourly reserve requirements by product type.",
            columns=[
                ColumnDocEntry("product", "str", "none", "Reserve product name"),
                *_HR_COLS_RESERVE,
            ],
            row_semantics="One row per reserve product.",
        ),
        FileTypeDoc(
            file_type="reserve_eligibility",
            filename="reserve_eligibility.csv",
            description="Generator eligibility for reserve products.",
            columns=[
                ColumnDocEntry("gen_uid", "str", "none", "Generator unique identifier"),
                ColumnDocEntry(
                    "spinning_eligible", "bool", "none", "Eligible for spinning reserve"
                ),
                ColumnDocEntry(
                    "non_spinning_eligible",
                    "bool",
                    "none",
                    "Eligible for non-spinning reserve",
                ),
                ColumnDocEntry(
                    "max_spinning_mw",
                    "float",
                    "MW",
                    "Maximum spinning reserve contribution",
                ),
                ColumnDocEntry(
                    "max_non_spinning_mw",
                    "float",
                    "MW",
                    "Maximum non-spinning reserve contribution",
                ),
            ],
            row_semantics="One row per generator.",
        ),
        FileTypeDoc(
            file_type="bess_units",
            filename="bess_units.csv",
            description="Battery energy storage system unit specifications.",
            columns=[
                ColumnDocEntry("unit_id", "str", "none", "BESS unit identifier"),
                ColumnDocEntry("bus_id", "int", "none", "Bus where BESS is connected"),
                ColumnDocEntry("power_mw", "float", "MW", "Rated power capacity"),
                ColumnDocEntry("energy_mwh", "float", "MWh", "Rated energy capacity"),
                ColumnDocEntry(
                    "efficiency", "float", "fraction", "Round-trip efficiency (0-1)"
                ),
                ColumnDocEntry(
                    "min_soc", "float", "fraction", "Minimum state of charge (0-1)"
                ),
                ColumnDocEntry(
                    "max_soc", "float", "fraction", "Maximum state of charge (0-1)"
                ),
                ColumnDocEntry(
                    "init_soc", "float", "fraction", "Initial state of charge (0-1)"
                ),
            ],
            row_semantics="One row per BESS unit.",
        ),
        FileTypeDoc(
            file_type="dr_buses",
            filename="dr_buses.csv",
            description="Demand response eligible buses and parameters.",
            columns=[
                ColumnDocEntry("bus_id", "int", "none", "Bus identifier"),
                ColumnDocEntry(
                    "max_curtailment_mw", "float", "MW", "Maximum curtailable load"
                ),
                ColumnDocEntry(
                    "curtailment_cost", "float", "$/MWh", "Cost of load curtailment"
                ),
                ColumnDocEntry(
                    "max_hours", "float", "hours", "Maximum curtailment duration"
                ),
            ],
            row_semantics="One row per demand response bus.",
        ),
        FileTypeDoc(
            file_type="flowgates",
            filename="flowgates.csv",
            description="Flowgate definitions with constituent lines and limits.",
            columns=[
                ColumnDocEntry("flowgate_id", "str", "none", "Flowgate identifier"),
                ColumnDocEntry(
                    "line_ids", "str", "none", "Semicolon-separated branch IDs"
                ),
                ColumnDocEntry(
                    "weights",
                    "str",
                    "none",
                    "Semicolon-separated weights for each line",
                ),
                ColumnDocEntry("limit_mw", "float", "MW", "Flowgate MW limit"),
            ],
            row_semantics="One row per flowgate.",
        ),
        FileTypeDoc(
            file_type="scenario_multipliers",
            filename="scenarios/scenario_multipliers_{wind,solar}_50x24.csv",
            description=(
                "Stochastic scenario multipliers for wind and solar generation. "
                "Each row is one (scenario, generator) pair with 24 hourly multipliers."
            ),
            columns=[
                ColumnDocEntry("scenario_id", "int", "none", "Scenario index (1-50)"),
                ColumnDocEntry(
                    "generator_id", "str", "none", "Generator unique identifier"
                ),
                *_HR_COLS_DIMENSIONLESS,
            ],
            row_semantics="One row per (scenario, generator) combination.",
        ),
    ]


def render_schema_reference(file_type_docs: list[FileTypeDoc]) -> str:
    """Render file type documentation as Markdown tables.

    Args:
        file_type_docs: List of FileTypeDoc to render.

    Returns:
        Markdown string with one table per file type.
    """
    sections: list[str] = []
    for ftd in file_type_docs:
        lines: list[str] = []
        lines.append(f"### {ftd.file_type}")
        lines.append("")
        lines.append(f"**File:** `{ftd.filename}`")
        lines.append("")
        lines.append(ftd.description)
        lines.append("")
        lines.append(f"**Row semantics:** {ftd.row_semantics}")
        lines.append("")
        lines.append("| Column | Type | Unit | Description |")
        lines.append("|--------|------|------|-------------|")
        for col in ftd.columns:
            lines.append(
                f"| {col.name} | {col.dtype} | {col.unit} | {col.description} |"
            )
        lines.append("")
        sections.append("\n".join(lines))
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Network summary computation
# ---------------------------------------------------------------------------


def _count_mpc_rows(m_file: Path, section: str) -> int:
    """Count data rows in a MATPOWER .m file section.

    Scans for ``mpc.<section> = [`` then counts non-comment, non-empty
    lines until ``];``.

    Args:
        m_file: Path to the .m file.
        section: Section name (e.g., "bus", "gen", "branch").

    Returns:
        Number of data rows found, or 0 if section not found.
    """
    if not m_file.exists():
        return 0

    text = m_file.read_text(encoding="utf-8")
    pattern = re.compile(rf"mpc\.{section}\s*=\s*\[")
    match = pattern.search(text)
    if not match:
        return 0

    count = 0
    for line in text[match.end() :].splitlines():
        stripped = line.strip()
        if stripped.startswith("];"):
            break
        if stripped == "" or stripped.startswith("%"):
            continue
        count += 1
    return count


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return rows as list of dicts.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of row dicts, or empty list if file doesn't exist.
    """
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _safe_float(value: str, default: float = 0.0) -> float:
    """Convert string to float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _count_scenario_ids(csv_path: Path) -> int:
    """Count distinct scenario IDs in a scenario multiplier CSV.

    Args:
        csv_path: Path to the scenario CSV file.

    Returns:
        Number of distinct scenario IDs, or 0 if file doesn't exist.
    """
    rows = _read_csv_rows(csv_path)
    if not rows:
        return 0
    ids = {r.get("scenario_id", "") for r in rows}
    ids.discard("")
    return len(ids)


def compute_network_summary(
    network_id: NetworkId,
    timeseries_dir: Path,
    networks_dir: Path,
) -> NetworkSummary:
    """Compute summary statistics for a single network.

    Parses .m files for bus/gen/branch counts and reads CSVs for
    BESS, DR, flowgate, and scenario counts.

    Args:
        network_id: Network identifier.
        timeseries_dir: Base timeseries directory (contains network subdirs).
        networks_dir: Directory containing .m case files.

    Returns:
        A NetworkSummary with computed statistics.
    """
    display_names = {
        NetworkId.TINY: "IEEE 39-Bus (case39)",
        NetworkId.SMALL: "ACTIVSg2000",
        NetworkId.MEDIUM: "ACTIVSg10k",
    }

    # Find .m file — try *_clean.m first, then plain case file
    m_file = None
    for pattern in [f"{network_id.value}_clean.m", f"{network_id.value}.m"]:
        candidate = networks_dir / pattern
        if candidate.exists():
            m_file = candidate
            break
    if m_file is None:
        # Try any .m file containing the network name
        for f in networks_dir.glob("*.m"):
            if network_id.value.lower() in f.name.lower():
                m_file = f
                break

    bus_count = _count_mpc_rows(m_file, "bus") if m_file else 0
    gen_count = _count_mpc_rows(m_file, "gen") if m_file else 0
    branch_count = _count_mpc_rows(m_file, "branch") if m_file else 0

    net_dir = timeseries_dir / network_id.value

    # Load peak
    load_rows = _read_csv_rows(net_dir / "load_24h.csv")
    peak_load = 0.0
    if load_rows:
        hr_cols = [c for c in load_rows[0] if c.startswith("HR_")]
        for h in hr_cols:
            hour_total = sum(_safe_float(r.get(h, "0")) for r in load_rows)
            peak_load = max(peak_load, hour_total)

    # Renewable capacity from gen_temporal_params
    gen_rows = _read_csv_rows(net_dir / "gen_temporal_params.csv")
    wind_rows = _read_csv_rows(net_dir / "wind_forecast_24h.csv")
    solar_rows = _read_csv_rows(net_dir / "solar_forecast_24h.csv")
    renewable_gen_uids = {r.get("gen_uid", "") for r in wind_rows} | {
        r.get("gen_uid", "") for r in solar_rows
    }
    renewable_gen_uids.discard("")
    total_renewable_cap = 0.0
    for r in gen_rows:
        if r.get("gen_uid", "") in renewable_gen_uids:
            total_renewable_cap += _safe_float(r.get("pmax", "0"))

    renewable_pct = (total_renewable_cap / peak_load * 100.0) if peak_load > 0 else 0.0

    # BESS
    bess_rows = _read_csv_rows(net_dir / "bess_units.csv")
    bess_count = len(bess_rows)
    bess_power = sum(_safe_float(r.get("power_mw", "0")) for r in bess_rows)
    bess_energy = sum(_safe_float(r.get("energy_mwh", "0")) for r in bess_rows)

    # DR
    dr_rows = _read_csv_rows(net_dir / "dr_buses.csv")
    dr_count = len(dr_rows)
    dr_curtailment = sum(_safe_float(r.get("max_curtailment_mw", "0")) for r in dr_rows)

    # Flowgates
    fg_rows = _read_csv_rows(net_dir / "flowgates.csv")
    fg_count = len(fg_rows)

    # Scenarios
    scenarios_dir = net_dir / "scenarios"
    wind_scenario_count = _count_scenario_ids(
        scenarios_dir / "scenario_multipliers_wind_50x24.csv"
    )
    solar_scenario_count = _count_scenario_ids(
        scenarios_dir / "scenario_multipliers_solar_50x24.csv"
    )

    return NetworkSummary(
        network_id=network_id,
        display_name=display_names.get(network_id, network_id.value),
        bus_count=bus_count,
        gen_count=gen_count,
        branch_count=branch_count,
        peak_load_mw=round(peak_load, 1),
        total_renewable_capacity_mw=round(total_renewable_cap, 1),
        renewable_penetration_pct=round(renewable_pct, 1),
        bess_unit_count=bess_count,
        total_bess_power_mw=round(bess_power, 1),
        total_bess_energy_mwh=round(bess_energy, 1),
        dr_bus_count=dr_count,
        total_dr_curtailment_mw=round(dr_curtailment, 1),
        flowgate_count=fg_count,
        scenario_count_wind=wind_scenario_count,
        scenario_count_solar=solar_scenario_count,
    )


def compute_all_network_summaries(
    timeseries_base_dir: Path,
    networks_dir: Path,
) -> list[NetworkSummary]:
    """Compute summaries for all networks.

    Args:
        timeseries_base_dir: Base timeseries directory.
        networks_dir: Directory containing .m case files.

    Returns:
        List of NetworkSummary, one per network.
    """
    return [
        compute_network_summary(nid, timeseries_base_dir, networks_dir)
        for nid in NetworkId
    ]


def render_summary_table(summaries: list[NetworkSummary]) -> str:
    """Render network summaries as a Markdown table.

    Args:
        summaries: List of NetworkSummary to render.

    Returns:
        Markdown table string.
    """
    lines: list[str] = []
    lines.append(
        "| Network | Buses | Gens | Branches | Peak Load (MW) "
        "| Renewable Cap (MW) | Renewable % | BESS Units | DR Buses "
        "| Flowgates | Wind Scenarios | Solar Scenarios |"
    )
    lines.append(
        "|---------|-------|------|----------|----------------"
        "|--------------------|-------------|------------|----------"
        "|-----------|----------------|-----------------|"
    )
    for s in summaries:
        lines.append(
            f"| {s.display_name} | {s.bus_count} | {s.gen_count} | {s.branch_count} "
            f"| {s.peak_load_mw} | {s.total_renewable_capacity_mw} "
            f"| {s.renewable_penetration_pct} | {s.bess_unit_count} | {s.dr_bus_count} "
            f"| {s.flowgate_count} | {s.scenario_count_wind} | {s.scenario_count_solar} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Methodology sections
# ---------------------------------------------------------------------------


def build_methodology_sections() -> dict[str, str]:
    """Build static methodology documentation for 8 data layers.

    Returns:
        Dict mapping section title to Markdown prose.
    """
    return {
        "Load Profiles": (
            "Hourly load profiles (load_24h.csv) are derived from the MATPOWER case "
            "bus data. Each bus with non-zero Pd (real power demand) gets a row with "
            "24 hourly values representing a typical daily load shape. Load values are "
            "scaled from the base case snapshot to create a realistic diurnal pattern."
        ),
        "Wind Generation": (
            "Wind forecast and actual profiles are generated using a Student-t "
            "distribution error model applied to capacity-scaled base profiles. "
            "The forecast represents the day-ahead prediction, while the actual "
            "represents realised generation including forecast errors."
        ),
        "Solar Generation": (
            "Solar forecast and actual profiles follow the same methodology as wind "
            "but with a solar-specific diurnal shape (zero generation at night). "
            "Forecast errors are modelled using a Student-t distribution with "
            "parameters calibrated to observed solar forecast accuracy."
        ),
        "Generator Parameters": (
            "Generator temporal parameters (gen_temporal_params.csv) combine MATPOWER "
            "case generator data with additional parameters from the RTS-GMLC dataset. "
            "These include ramp rates, minimum up/down times, startup/shutdown costs, "
            "and marginal costs assigned by fuel type."
        ),
        "Reserve Requirements": (
            "Reserve requirements are computed as a fraction of peak system load and "
            "renewable capacity. Spinning and non-spinning products are defined with "
            "hourly MW requirements that vary with net load. Generator eligibility "
            "is determined by unit type and ramp capability."
        ),
        "Battery Energy Storage": (
            "BESS units are placed at buses selected by a placement score algorithm "
            "that considers load magnitude, renewable proximity, and network congestion. "
            "Each unit has rated power (MW), energy (MWh), round-trip efficiency, "
            "and state-of-charge constraints."
        ),
        "Demand Response": (
            "Demand response buses are selected from high-load buses that meet "
            "curtailment eligibility criteria. Each DR bus has a maximum curtailable "
            "load (MW), curtailment cost ($/MWh), and optional maximum duration "
            "constraint."
        ),
        "Stochastic Scenarios": (
            "Scenario multipliers provide 50 stochastic scenarios for wind and solar "
            "generation. Each scenario is a set of hourly multipliers applied to the "
            "forecast profile. Multipliers are generated using a Student-t copula "
            "model that preserves spatial and temporal correlations."
        ),
    }


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def build_provenance_entries() -> list[ProvenanceEntry]:
    """Build provenance records for the three data sources.

    Returns:
        List of 3 ProvenanceEntry: ACTIVSg, RTS-GMLC, MATPOWER.
    """
    return [
        ProvenanceEntry(
            source_name="ACTIVSg Synthetic Grid Cases",
            provider="Texas A&M University",
            url="https://electricgrids.engr.tamu.edu/electric-grid-test-cases/",
            version="2000-bus and 10k-bus",
            license="CC BY 4.0",
            citation=(
                "A. B. Birchfield et al., 'Grid Structural Characteristics as "
                "Validation Criteria for Synthetic Networks,' IEEE Trans. Power "
                "Syst., 2017."
            ),
            networks_used=[NetworkId.SMALL, NetworkId.MEDIUM],
            notes=(
                "Provides the base network topology, bus loads, generator capacities, "
                "and branch parameters for the SMALL and MEDIUM test cases."
            ),
        ),
        ProvenanceEntry(
            source_name="RTS-GMLC",
            provider="NREL / GridMod",
            url="https://github.com/GridMod/RTS-GMLC",
            version="v0.3.2",
            license="BSD 3-Clause",
            citation=(
                "C. Barrows et al., 'The IEEE Reliability Test System: A Proposed "
                "2019 Update,' IEEE Trans. Power Syst., 2020."
            ),
            networks_used=[NetworkId.TINY],
            notes=(
                "Generator cost curves, temporal parameters, and fuel classifications "
                "used as templates for the TINY network augmentation."
            ),
        ),
        ProvenanceEntry(
            source_name="MATPOWER",
            provider="MATPOWER / Cornell",
            url="https://matpower.org/",
            version="8.0",
            license="BSD 3-Clause",
            citation=(
                "R. D. Zimmerman et al., 'MATPOWER: Steady-State Operations, "
                "Planning, and Analysis Tools for Power Systems Research and "
                "Education,' IEEE Trans. Power Syst., 2011."
            ),
            networks_used=[NetworkId.TINY, NetworkId.SMALL, NetworkId.MEDIUM],
            notes=(
                "Provides the case39 (IEEE 39-bus) base network and the MATPOWER "
                "data format used by all three test cases."
            ),
        ),
    ]


def render_provenance_section(entries: list[ProvenanceEntry]) -> str:
    """Render provenance entries as Markdown.

    Args:
        entries: List of ProvenanceEntry to render.

    Returns:
        Markdown string with provenance details.
    """
    sections: list[str] = []
    for entry in entries:
        nets = ", ".join(n.value for n in entry.networks_used)
        lines = [
            f"### {entry.source_name}",
            "",
            f"- **Provider:** {entry.provider}",
            f"- **URL:** {entry.url}",
            f"- **Version:** {entry.version}",
            f"- **License:** {entry.license}",
            f"- **Networks:** {nets}",
            f"- **Citation:** {entry.citation}",
            "",
            entry.notes,
            "",
        ]
        sections.append("\n".join(lines))
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Known limitations
# ---------------------------------------------------------------------------


def build_known_limitations() -> list[KnownLimitation]:
    """Build the list of 6 known dataset limitations.

    Returns:
        List of 6 KnownLimitation entries.
    """
    return [
        KnownLimitation(
            title="Single snapshot load profile",
            description=(
                "Load profiles represent a single day shape scaled from the "
                "MATPOWER base case. Real systems exhibit seasonal and "
                "weather-driven load variation."
            ),
            affected_networks=None,
            mitigation=(
                "For multi-day studies, users should apply their own load "
                "scaling factors or use external load forecast data."
            ),
        ),
        KnownLimitation(
            title="Simplified renewable forecast errors",
            description=(
                "Forecast errors use a parametric Student-t model rather than "
                "empirical distributions from real forecast systems."
            ),
            affected_networks=None,
            mitigation=(
                "Parameters are calibrated to be representative but users "
                "requiring higher fidelity should substitute empirical "
                "forecast error distributions."
            ),
        ),
        KnownLimitation(
            title="Uniform BESS specifications",
            description=(
                "All BESS units within a network share the same efficiency "
                "and SOC parameters. Real storage fleets are heterogeneous."
            ),
            affected_networks=None,
            mitigation=(
                "Users can modify bess_units.csv to introduce heterogeneous "
                "specifications for specific studies."
            ),
        ),
        KnownLimitation(
            title="Static reserve requirements",
            description=(
                "Reserve requirements are computed from a fixed formula and "
                "do not adapt dynamically to system conditions."
            ),
            affected_networks=None,
            mitigation=(
                "For dynamic reserve studies, replace reserve_requirements_24h.csv "
                "with time-varying requirements."
            ),
        ),
        KnownLimitation(
            title="Limited scenario count for TINY network",
            description=(
                "The case39 network has fewer generators, resulting in lower "
                "scenario diversity in the stochastic multipliers."
            ),
            affected_networks=[NetworkId.TINY],
            mitigation=(
                "Increase scenario count by re-running scenario generation "
                "with a higher scenario_count parameter."
            ),
        ),
        KnownLimitation(
            title="No transmission contingency data",
            description=(
                "The dataset does not include N-1 contingency definitions or "
                "contingency-specific transfer limits."
            ),
            affected_networks=None,
            mitigation=(
                "Users should generate contingency lists from the branch data "
                "using a standard transmission-planning methodology."
            ),
        ),
    ]


def render_limitations_section(limitations: list[KnownLimitation]) -> str:
    """Render known limitations as Markdown.

    Args:
        limitations: List of KnownLimitation to render.

    Returns:
        Markdown string with numbered limitations.
    """
    lines: list[str] = []
    for i, lim in enumerate(limitations, 1):
        lines.append(f"### {i}. {lim.title}")
        lines.append("")
        lines.append(lim.description)
        lines.append("")
        if lim.affected_networks:
            nets = ", ".join(n.value for n in lim.affected_networks)
            lines.append(f"**Affected networks:** {nets}")
            lines.append("")
        lines.append(f"**Mitigation:** {lim.mitigation}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Regeneration steps
# ---------------------------------------------------------------------------


def build_regeneration_steps() -> list[RegenerationStep]:
    """Build ordered regeneration steps.

    Returns:
        List of >= 5 ordered RegenerationStep entries.
    """
    return [
        RegenerationStep(
            step_number=1,
            script_path="scripts/generate_load_profiles.py",
            description=(
                "Generate 24-hour load profiles from MATPOWER case bus data. "
                "Reads .m files and produces load_24h.csv for each network."
            ),
            prerequisites=["MATPOWER .m files in data/networks/"],
            estimated_runtime="< 1 minute",
        ),
        RegenerationStep(
            step_number=2,
            script_path="scripts/generate_renewables.py",
            description=(
                "Generate wind and solar forecast/actual profiles with "
                "Student-t error model. Produces 4 CSV files per network."
            ),
            prerequisites=["load_24h.csv for each network", "numpy", "scipy"],
            estimated_runtime="1-2 minutes",
        ),
        RegenerationStep(
            step_number=3,
            script_path="scripts/generate_reserves_bess_dr.py",
            description=(
                "Generate reserve requirements, BESS placements, and DR bus "
                "selections. Produces reserve, BESS, DR, and flowgate CSVs."
            ),
            prerequisites=[
                "load_24h.csv",
                "wind/solar profiles",
                "gen_temporal_params.csv",
            ],
            estimated_runtime="< 1 minute",
        ),
        RegenerationStep(
            step_number=4,
            script_path="scripts/generate_scenarios.py",
            description=(
                "Generate stochastic scenario multipliers using Student-t "
                "copula. Produces scenario_multipliers_{wind,solar}_50x24.csv."
            ),
            prerequisites=["wind/solar profiles", "numpy", "scipy"],
            estimated_runtime="2-5 minutes",
        ),
        RegenerationStep(
            step_number=5,
            script_path="scripts/validate_schema.py",
            description=(
                "Validate all generated CSV files against the canonical schema. "
                "Checks column names, types, constraints, and row counts."
            ),
            prerequisites=["All CSV files generated"],
            estimated_runtime="< 1 minute",
        ),
        RegenerationStep(
            step_number=6,
            script_path="scripts/generate_manifest.py",
            description=(
                "Generate the reproducibility manifest (manifest.json) with "
                "SHA-256 checksums, seed values, and software versions."
            ),
            prerequisites=["All CSV files generated", "All validation passed"],
            estimated_runtime="< 1 minute",
        ),
        RegenerationStep(
            step_number=7,
            script_path="scripts/generate_docs.py",
            description=(
                "Generate this README and update CLAUDE.md with the Augmented Data section."
            ),
            prerequisites=["All CSV files generated"],
            estimated_runtime="< 1 minute",
        ),
    ]


def render_regeneration_section(steps: list[RegenerationStep]) -> str:
    """Render regeneration steps as Markdown.

    Args:
        steps: List of RegenerationStep to render.

    Returns:
        Markdown string with ordered steps.
    """
    lines: list[str] = []
    for step in steps:
        lines.append(f"### Step {step.step_number}: {step.script_path}")
        lines.append("")
        lines.append(step.description)
        lines.append("")
        if step.prerequisites:
            lines.append("**Prerequisites:**")
            for prereq in step.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")
        lines.append(f"**Estimated runtime:** {step.estimated_runtime}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation instructions
# ---------------------------------------------------------------------------


def build_validation_instructions() -> str:
    """Build validation instructions as Markdown.

    Returns:
        Markdown string with validation commands and instructions.
    """
    return textwrap.dedent("""\
        To validate the generated data, run the following commands inside the
        devcontainer:

        ```bash
        # Schema conformance checks
        devcontainer exec --workspace-folder . bash -c \\
          "cd /workspace && PYTHONPATH=. python -m scripts.validate_schema"

        # Cross-network consistency checks
        devcontainer exec --workspace-folder . bash -c \\
          "cd /workspace && PYTHONPATH=. python -m scripts.validate_cross_network"

        # Regenerate and verify manifest checksums
        devcontainer exec --workspace-folder . bash -c \\
          "cd /workspace && PYTHONPATH=. python -m scripts.generate_manifest"
        ```

        All validation scripts exit with code 0 on success and non-zero on failure.
    """).rstrip()


# ---------------------------------------------------------------------------
# README assembly and rendering
# ---------------------------------------------------------------------------


def build_readme_content(
    timeseries_base_dir: Path,
    networks_dir: Path,
) -> ReadmeContent:
    """Assemble all components into a ReadmeContent.

    Args:
        timeseries_base_dir: Base timeseries directory.
        networks_dir: Directory containing .m case files.

    Returns:
        A fully populated ReadmeContent.
    """
    return ReadmeContent(
        title="Augmented Timeseries Data",
        introduction=(
            "This directory contains augmented timeseries data for power system "
            "modeling tool evaluation. The data is derived from MATPOWER case files "
            "and augmented with realistic load profiles, renewable generation "
            "forecasts, generator parameters, reserve requirements, battery storage "
            "specifications, demand response parameters, flowgate definitions, and "
            "stochastic scenarios.\n\n"
            "Three network tiers are provided: TINY (case39, IEEE 39-bus), "
            "SMALL (ACTIVSg2000), and MEDIUM (ACTIVSg10k)."
        ),
        directory_tree=walk_timeseries_tree(timeseries_base_dir),
        file_type_docs=build_file_type_docs(),
        network_summaries=compute_all_network_summaries(
            timeseries_base_dir, networks_dir
        ),
        methodology_sections=build_methodology_sections(),
        provenance_entries=build_provenance_entries(),
        known_limitations=build_known_limitations(),
        regeneration_steps=build_regeneration_steps(),
        validation_instructions=build_validation_instructions(),
        manifest_reference=(
            "A reproducibility manifest is available at "
            "`data/timeseries/manifest.json`. It contains SHA-256 checksums "
            "for all generated files, RNG seed values, generation parameters, "
            "and software versions. See `scripts/generate_manifest.py` for details."
        ),
    )


def render_readme(content: ReadmeContent) -> str:
    """Render ReadmeContent as a complete Markdown document.

    Args:
        content: The ReadmeContent to render.

    Returns:
        Complete Markdown string.
    """
    sections: list[str] = []

    # Title
    sections.append(f"# {content.title}")
    sections.append("")
    sections.append(content.introduction)
    sections.append("")

    # Directory tree
    sections.append("## Directory Structure")
    sections.append("")
    sections.append(render_directory_tree(content.directory_tree))
    sections.append("")

    # Network summaries
    sections.append("## Network Summary")
    sections.append("")
    sections.append(render_summary_table(content.network_summaries))
    sections.append("")

    # Schema reference
    sections.append("## CSV Schema Reference")
    sections.append("")
    sections.append(render_schema_reference(content.file_type_docs))

    # Methodology
    sections.append("## Data Generation Methodology")
    sections.append("")
    for title, prose in content.methodology_sections.items():
        sections.append(f"### {title}")
        sections.append("")
        sections.append(prose)
        sections.append("")

    # Provenance
    sections.append("## Data Provenance")
    sections.append("")
    sections.append(render_provenance_section(content.provenance_entries))

    # Known limitations
    sections.append("## Known Limitations")
    sections.append("")
    sections.append(render_limitations_section(content.known_limitations))

    # Regeneration
    sections.append("## Data Regeneration")
    sections.append("")
    sections.append(render_regeneration_section(content.regeneration_steps))

    # Validation
    sections.append("## Validation")
    sections.append("")
    sections.append(content.validation_instructions)
    sections.append("")

    # Manifest reference
    sections.append("## Reproducibility Manifest")
    sections.append("")
    sections.append(content.manifest_reference)
    sections.append("")

    return "\n".join(sections)


def write_readme(content: ReadmeContent, output_path: Path) -> None:
    """Write rendered README to disk.

    Args:
        content: The ReadmeContent to render and write.
        output_path: Destination file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = render_readme(content)
    output_path.write_text(text, encoding="utf-8")
    logger.info("Wrote README to %s", output_path)


# ---------------------------------------------------------------------------
# CLAUDE.md update
# ---------------------------------------------------------------------------


def build_claude_md_update() -> ClaudeMdUpdate:
    """Build the CLAUDE.md Augmented Data section content.

    Returns:
        A ClaudeMdUpdate with all section content.
    """
    return ClaudeMdUpdate(
        section_heading="Augmented Data",
        directory_overview=(
            "`data/timeseries/` contains augmented timeseries data for three network "
            "tiers: TINY (case39), SMALL (ACTIVSg2000), MEDIUM (ACTIVSg10k). Each "
            "network subdirectory has CSV files for load, wind, solar, generator "
            "parameters, reserves, BESS, demand response, flowgates, and stochastic "
            "scenarios."
        ),
        scripts_overview=(
            "`scripts/` contains Python generation and validation scripts. All scripts "
            "use only Python stdlib (csv, json, pathlib, dataclasses). Run them inside "
            "the devcontainer with `PYTHONPATH=.`."
        ),
        csv_conventions=(
            "CSV files use hour-ending columns (HR_1 through HR_24) for temporal data. "
            "All MW values are non-negative floats. ID columns (bus_id, gen_uid, etc.) "
            "are never null. Boolean columns use lowercase `true`/`false`."
        ),
        validation_command=(
            'devcontainer exec --workspace-folder . bash -c "'
            'cd /workspace && PYTHONPATH=. python -m scripts.validate_schema"'
        ),
        manifest_location="data/timeseries/manifest.json",
        readme_pointer=(
            "See `data/timeseries/README.md` for comprehensive dataset documentation "
            "including schema reference, methodology, provenance, and known limitations."
        ),
    )


def render_claude_md_section(update: ClaudeMdUpdate) -> str:
    """Render a ClaudeMdUpdate as Markdown.

    Args:
        update: The ClaudeMdUpdate to render.

    Returns:
        Markdown string for the section.
    """
    lines = [
        f"## {update.section_heading}",
        "",
        update.directory_overview,
        "",
        update.scripts_overview,
        "",
        f"**CSV conventions:** {update.csv_conventions}",
        "",
        "**Validation:**",
        "",
        "```bash",
        update.validation_command,
        "```",
        "",
        f"**Manifest:** `{update.manifest_location}`",
        "",
        update.readme_pointer,
        "",
    ]
    return "\n".join(lines)


def apply_claude_md_update(claude_md_path: Path, update: ClaudeMdUpdate) -> None:
    """Apply the Augmented Data section to CLAUDE.md idempotently.

    If ``## Augmented Data`` already exists, replaces it (up to the next
    ``## `` heading or EOF). Otherwise appends it.

    Args:
        claude_md_path: Path to the CLAUDE.md file.
        update: The ClaudeMdUpdate content to apply.
    """
    section_text = render_claude_md_section(update)

    if not claude_md_path.exists():
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        claude_md_path.write_text(section_text, encoding="utf-8")
        logger.info("Created %s with Augmented Data section", claude_md_path)
        return

    existing = claude_md_path.read_text(encoding="utf-8")

    # Check if section already exists
    pattern = re.compile(
        r"^## Augmented Data\s*\n.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(existing)

    if match:
        # Replace existing section
        new_content = existing[: match.start()] + section_text + existing[match.end() :]
    else:
        # Append section
        if existing and not existing.endswith("\n"):
            new_content = existing + "\n\n" + section_text
        else:
            new_content = existing + "\n" + section_text

    claude_md_path.write_text(new_content, encoding="utf-8")
    logger.info("Updated %s with Augmented Data section", claude_md_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def generate_docs(
    timeseries_base_dir: Path | None = None,
    networks_dir: Path | None = None,
    readme_output_path: Path | None = None,
    claude_md_path: Path | None = None,
    repo_dir: Path | None = None,
) -> None:
    """Generate dataset documentation and update CLAUDE.md.

    This is the main entry point. All directory arguments default to
    locations relative to the repository root.

    Args:
        timeseries_base_dir: Base directory for per-network timeseries.
        networks_dir: Directory containing .m case files.
        readme_output_path: Where to write README.md.
        claude_md_path: Path to CLAUDE.md to update.
        repo_dir: Repository root.
    """
    if repo_dir is None:
        repo_dir = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_dir / "data" / "timeseries"

    if networks_dir is None:
        networks_dir = repo_dir / "data" / "networks"

    if readme_output_path is None:
        readme_output_path = timeseries_base_dir / "README.md"

    if claude_md_path is None:
        claude_md_path = repo_dir / "CLAUDE.md"

    content = build_readme_content(timeseries_base_dir, networks_dir)
    write_readme(content, readme_output_path)

    update = build_claude_md_update()
    apply_claude_md_update(claude_md_path, update)

    logger.info("Documentation generation complete")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_docs()
