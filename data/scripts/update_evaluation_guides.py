"""Evaluation Guide Updates for the data augmentation pipeline (PRD 06).

Reads the existing evaluation guide markdown files (rubric and test protocol),
generates targeted text edits referencing augmented data paths, file formats,
and schema, then writes updated markdown content. Documents the day-ahead
framing for tests A-5, A-6, A-8 and adds canonical CSV schema references.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from scripts.csv_schema import CsvFileType

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class GuideFileId(StrEnum):
    """Identifiers for the two evaluation guide documents."""

    RUBRIC = "rubric"
    PROTOCOL = "protocol"


@dataclass(frozen=True)
class GuideFilePaths:
    """Resolved file paths for the evaluation guide documents."""

    rubric_path: Path
    protocol_path: Path
    schema_doc_path: Path  # data/schema/canonical_csv_schema.md
    schema_json_path: Path  # data/schema/canonical_csv_schema.json

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> GuideFilePaths:
        return cls(
            rubric_path=repo_root / "evaluation_guides" / "Phase1_Evaluation_Rubric_v1.md",
            protocol_path=repo_root / "evaluation_guides" / "Phase1_Test_Protocol_v2.md",
            schema_doc_path=repo_root / "data" / "schema" / "canonical_csv_schema.md",
            schema_json_path=repo_root / "data" / "schema" / "canonical_csv_schema.json",
        )


@dataclass(frozen=True)
class NetworkTimeSeriesInfo:
    """Summary of time series data availability for one network.

    Populated from the selection rationale JSON and directory listing.
    """

    network_label: str  # "TINY", "SMALL", or "MEDIUM"
    network_name: str  # "IEEE 39-bus", "ACTIVSg 2k", "ACTIVSg 10k"
    data_dir: str  # relative path, e.g. "data/timeseries/ACTIVSg2000/"
    has_timeseries: bool
    source_description: str  # e.g. "Extracted from ACTIVSg companion data"
    selected_date: str | None  # ISO 8601, None for TINY
    composite_score: float | None  # None for TINY
    peak_load_mw: float | None
    total_wind_mwh: float | None
    total_solar_mwh: float | None
    available_file_types: list[str]  # e.g. ["load_24h", "wind_actual_24h", ...]


@dataclass(frozen=True)
class GuideUpdateContext:
    """All context needed to apply updates to both evaluation guides.

    Assembled from D4 schema spec, D5 selection rationale, and
    directory inspection.
    """

    networks: list[NetworkTimeSeriesInfo]
    schema_doc_relative_path: str  # "data/schema/canonical_csv_schema.md"
    schema_json_relative_path: str  # "data/schema/canonical_csv_schema.json"
    timeseries_base_dir: str  # "data/timeseries/"
    scenario_file_name: str  # "scenarios/scenario_multipliers_50x24.csv"
    canonical_csv_version: str  # from schema spec
    hour_ending_convention: str  # "HR_1 through HR_24, hour-ending"


@dataclass(frozen=True)
class EditOperation:
    """A single text edit to apply to a guide document.

    Each edit is an insertion after a marker line, a replacement of a
    specific text block, or an append to the end of the document.
    """

    guide: GuideFileId
    edit_type: str  # "insert_after", "replace_block", "append"
    marker: str  # text to search for (line or block start)
    old_text: str | None  # for replace_block: the text to replace
    new_text: str  # the text to insert or replace with
    description: str  # human-readable description of what this edit does


@dataclass(frozen=True)
class GuideUpdateResult:
    """Result of applying all edits to one guide document."""

    guide: GuideFileId
    original_path: Path
    output_path: Path
    edits_applied: int
    edits_skipped: int  # edits whose markers were not found
    skipped_descriptions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


def load_selection_rationale(rationale_path: Path) -> dict:
    """Load a D5 selection rationale JSON file.

    Reads the JSON file and returns the parsed dictionary. The caller
    extracts the fields needed for the guide update context.

    Args:
        rationale_path: Path to a selection_rationale.json file.

    Returns:
        The parsed JSON as a dictionary.

    Raises:
        FileNotFoundError: If rationale_path does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(rationale_path) as fh:
        return json.load(fh)


def build_network_info_tiny() -> NetworkTimeSeriesInfo:
    """Build the NetworkTimeSeriesInfo for the TINY (case39) network.

    TINY has synthesized time series from RTS-GMLC templates (produced
    in Phase 2b), not extracted from ACTIVSg companion data. The
    selected_date, composite_score, and summary statistics are None.

    Returns:
        A NetworkTimeSeriesInfo for the TINY network.
    """
    return NetworkTimeSeriesInfo(
        network_label="TINY",
        network_name="IEEE 39-bus",
        data_dir="data/timeseries/case39/",
        has_timeseries=True,
        source_description="Synthesized from RTS-GMLC templates (Phase 2b)",
        selected_date=None,
        composite_score=None,
        peak_load_mw=None,
        total_wind_mwh=None,
        total_solar_mwh=None,
        available_file_types=[],
    )


def build_network_info_from_rationale(
    network_label: str,
    network_name: str,
    data_dir: str,
    rationale: dict,
    available_files: list[str],
) -> NetworkTimeSeriesInfo:
    """Build a NetworkTimeSeriesInfo from a D5 selection rationale.

    Extracts the selected date, composite score, and summary statistics
    from the rationale dictionary. The available_files list is determined
    by inspecting the data directory.

    Args:
        network_label: "SMALL" or "MEDIUM".
        network_name: "ACTIVSg 2k" or "ACTIVSg 10k".
        data_dir: Relative path to the network's timeseries directory.
        rationale: Parsed selection rationale JSON dictionary.
        available_files: List of CSV file stems found in the data dir.

    Returns:
        A NetworkTimeSeriesInfo with fields populated from the rationale.
    """
    selected_date = rationale.get("selected_date")
    composite_score = rationale.get("composite_score")

    # Extract summary statistics from selected_day_summary
    summary = rationale.get("selected_day_summary", {})
    peak_load_mw = summary.get("peak_load_mw")
    total_wind_mwh = summary.get("total_wind_mwh")
    total_solar_mwh = summary.get("total_solar_mwh")

    return NetworkTimeSeriesInfo(
        network_label=network_label,
        network_name=network_name,
        data_dir=data_dir,
        has_timeseries=True,
        source_description="Extracted from ACTIVSg companion data via representative day selection",
        selected_date=selected_date,
        composite_score=composite_score,
        peak_load_mw=peak_load_mw,
        total_wind_mwh=total_wind_mwh,
        total_solar_mwh=total_solar_mwh,
        available_file_types=available_files,
    )


def _list_csv_file_stems(data_dir: Path) -> list[str]:
    """List CSV file stems in a timeseries data directory.

    Args:
        data_dir: Path to the network's timeseries directory.

    Returns:
        Sorted list of CSV file stems (filenames without extension).
    """
    if not data_dir.is_dir():
        return []
    stems: list[str] = []
    for csv_file in sorted(data_dir.glob("*.csv")):
        stems.append(csv_file.stem)
    return stems


def build_update_context(
    repo_root: Path,
) -> GuideUpdateContext:
    """Assemble the full update context from D4 and D5 outputs.

    Inspects the data directories to determine which files exist,
    loads selection rationale JSONs for SMALL and MEDIUM networks,
    and builds NetworkTimeSeriesInfo for all three networks.

    Falls back gracefully if rationale files do not exist yet (the
    script can still run with partial context, producing updates
    for the sections that do not require rationale data).

    Args:
        repo_root: Path to the grc-tech-evaluation repository root.

    Returns:
        A GuideUpdateContext with all available information.
    """
    timeseries_base = repo_root / "data" / "timeseries"

    # TINY network
    tiny_info = build_network_info_tiny()

    # SMALL network (ACTIVSg2000)
    small_dir = timeseries_base / "ACTIVSg2000"
    small_rationale_path = small_dir / "selection_rationale.json"
    small_files = _list_csv_file_stems(small_dir)
    if small_rationale_path.is_file():
        small_rationale = load_selection_rationale(small_rationale_path)
        small_info = build_network_info_from_rationale(
            network_label="SMALL",
            network_name="ACTIVSg 2k",
            data_dir="data/timeseries/ACTIVSg2000/",
            rationale=small_rationale,
            available_files=small_files,
        )
    else:
        small_info = NetworkTimeSeriesInfo(
            network_label="SMALL",
            network_name="ACTIVSg 2k",
            data_dir="data/timeseries/ACTIVSg2000/",
            has_timeseries=False,
            source_description="Pending representative day selection (D5)",
            selected_date=None,
            composite_score=None,
            peak_load_mw=None,
            total_wind_mwh=None,
            total_solar_mwh=None,
            available_file_types=small_files,
        )

    # MEDIUM network (ACTIVSg10k)
    medium_dir = timeseries_base / "ACTIVSg10k"
    medium_rationale_path = medium_dir / "selection_rationale.json"
    medium_files = _list_csv_file_stems(medium_dir)
    if medium_rationale_path.is_file():
        medium_rationale = load_selection_rationale(medium_rationale_path)
        medium_info = build_network_info_from_rationale(
            network_label="MEDIUM",
            network_name="ACTIVSg 10k",
            data_dir="data/timeseries/ACTIVSg10k/",
            rationale=medium_rationale,
            available_files=medium_files,
        )
    else:
        medium_info = NetworkTimeSeriesInfo(
            network_label="MEDIUM",
            network_name="ACTIVSg 10k",
            data_dir="data/timeseries/ACTIVSg10k/",
            has_timeseries=False,
            source_description="Pending representative day selection (D5)",
            selected_date=None,
            composite_score=None,
            peak_load_mw=None,
            total_wind_mwh=None,
            total_solar_mwh=None,
            available_file_types=medium_files,
        )

    # Determine canonical CSV schema version
    schema_doc_path = repo_root / "data" / "schema" / "canonical_csv_schema.md"
    canonical_csv_version = "1.0.0"
    if schema_doc_path.is_file():
        text = schema_doc_path.read_text()
        version_match = re.search(r"v(\d+\.\d+\.\d+)", text)
        if version_match:
            canonical_csv_version = version_match.group(1)

    return GuideUpdateContext(
        networks=[tiny_info, small_info, medium_info],
        schema_doc_relative_path="data/schema/canonical_csv_schema.md",
        schema_json_relative_path="data/schema/canonical_csv_schema.json",
        timeseries_base_dir="data/timeseries/",
        scenario_file_name="scenarios/scenario_multipliers_50x24.csv",
        canonical_csv_version=canonical_csv_version,
        hour_ending_convention="HR_1 through HR_24, hour-ending",
    )


# ---------------------------------------------------------------------------
# Edit generation
# ---------------------------------------------------------------------------


def _build_timeseries_availability_note(context: GuideUpdateContext) -> str:
    """Build a markdown note about time series availability for all networks."""
    lines: list[str] = []
    lines.append("")
    lines.append("> **Time Series Data Availability**")
    lines.append(">")
    for net in context.networks:
        status = "available" if net.has_timeseries else "pending"
        date_note = ""
        if net.selected_date is not None:
            date_note = f" (selected date: {net.selected_date}"
            if net.composite_score is not None:
                date_note += f", composite score: {net.composite_score:.4f}"
            date_note += ")"
        lines.append(
            f"> - **{net.network_label}** ({net.network_name}): "
            f"24-hour time series {status} — {net.source_description}{date_note}. "
            f"Data directory: `{net.data_dir}`"
        )
    lines.append(">")
    lines.append(
        f"> All CSV files follow the canonical schema specification "
        f"v{context.canonical_csv_version} "
        f"(`{context.schema_doc_relative_path}`)."
    )
    lines.append("")
    return "\n".join(lines)


def _build_file_types_list() -> str:
    """Build a markdown list of all canonical CSV file types."""
    lines: list[str] = []
    for ft in CsvFileType:
        lines.append(f">   - `{ft.value}.csv`")
    return "\n".join(lines)


def generate_rubric_edits(context: GuideUpdateContext) -> list[EditOperation]:
    """Generate the list of edits to apply to the rubric document.

    Produces edits for:
    - Reference Networks table: add time series availability note

    The edits are returned as EditOperation objects that can be
    applied by apply_edits.

    Args:
        context: The assembled update context.

    Returns:
        A list of EditOperation objects targeting the rubric.
    """
    edits: list[EditOperation] = []

    # Add time series availability note after the Reference Networks heading/table
    ts_note = _build_timeseries_availability_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.RUBRIC,
            edit_type="insert_after",
            marker="Reference Networks",
            old_text=None,
            new_text=ts_note,
            description="Add time series availability note to Reference Networks section",
        )
    )

    return edits


def _build_timeseries_data_section(context: GuideUpdateContext) -> str:
    """Build the new 'Time Series Data' section for the test protocol."""
    lines: list[str] = []
    lines.append("")
    lines.append("### Time Series Data")
    lines.append("")
    lines.append(
        "The data augmentation pipeline produces 24-hour temporal profiles for each "
        "reference network. These profiles provide the load, wind, solar, and generator "
        "temporal parameters consumed by tests A-5 (SCUC), A-6 (SCED), A-8 (Stochastic "
        "Timeseries Optimization), B-4 (Stochastic Scenario Wrapping), and the "
        "corresponding scalability tests in Suite C."
    )
    lines.append("")
    lines.append("**Directory structure:**")
    lines.append("")
    lines.append("```")
    lines.append(f"{context.timeseries_base_dir}")
    lines.append("  <network>/")
    lines.append("    load_24h.csv")
    lines.append("    wind_forecast_24h.csv")
    lines.append("    wind_actual_24h.csv")
    lines.append("    solar_forecast_24h.csv")
    lines.append("    solar_actual_24h.csv")
    lines.append("    gen_temporal_params.csv")
    lines.append("    reserve_requirements_24h.csv")
    lines.append("    scenarios/")
    lines.append(f"      {context.scenario_file_name.split('/')[-1]}")
    lines.append("```")
    lines.append("")
    lines.append(
        f"All CSV files conform to the canonical schema specification "
        f"v{context.canonical_csv_version}. Columns use the {context.hour_ending_convention} "
        f"convention. See `{context.schema_doc_relative_path}` for complete format details."
    )
    lines.append("")
    lines.append("**Representative day selection:**")
    lines.append("")
    for net in context.networks:
        if net.selected_date is not None:
            summary_parts = []
            if net.peak_load_mw is not None:
                summary_parts.append(f"peak load {net.peak_load_mw:.1f} MW")
            if net.total_wind_mwh is not None:
                summary_parts.append(f"total wind {net.total_wind_mwh:.1f} MWh")
            if net.total_solar_mwh is not None:
                summary_parts.append(f"total solar {net.total_solar_mwh:.1f} MWh")
            summary_str = ", ".join(summary_parts) if summary_parts else "see rationale"
            lines.append(
                f"- **{net.network_label}** ({net.network_name}): Selected date "
                f"**{net.selected_date}** (composite score {net.composite_score:.4f}; "
                f"{summary_str}). "
                f"Full rationale: `{net.data_dir}selection_rationale.json`."
            )
        elif net.network_label == "TINY":
            lines.append(
                f"- **{net.network_label}** ({net.network_name}): "
                f"{net.source_description}. No representative day selection required."
            )
    lines.append("")
    return "\n".join(lines)


def _build_a5_data_note(context: GuideUpdateContext) -> str:
    """Build the A-5 (SCUC) data source clarification note."""
    return (
        "\n> **Data source (augmented):** The 24-hour commitment horizon uses load profiles "
        "from `load_24h.csv`, wind profiles from `wind_actual_24h.csv`, and solar profiles "
        "from `solar_actual_24h.csv` in the network's `"
        + context.timeseries_base_dir
        + "<network>/` directory. Generator temporal parameters (ramp rates, minimum "
        "up/down times, startup costs) come from `gen_temporal_params.csv`. Reserve "
        "requirements come from `reserve_requirements_24h.csv`.\n"
    )


def _build_a6_data_note(context: GuideUpdateContext) -> str:
    """Build the A-6 (SCED) data source clarification note."""
    return (
        "\n> **Data source (augmented):** The fixed commitment schedule from A-5 is "
        "re-dispatched against the same 24-hour load and renewable profiles "
        "(`load_24h.csv`, `wind_actual_24h.csv`, `solar_actual_24h.csv`) from "
        "`" + context.timeseries_base_dir + "<network>/`.\n"
    )


def _build_a8_stochastic_note(context: GuideUpdateContext) -> str:
    """Build the A-8 (Stochastic) data source and dual-path note."""
    return (
        "\n> **Stochastic data (augmented):** Two paths are supported depending on "
        "tool capability:\n"
        ">\n"
        "> - **(a) Tools with native stochastic support** should use forecast/actual "
        "profile pairs (`wind_forecast_24h.csv` / `wind_actual_24h.csv`, "
        "`solar_forecast_24h.csv` / `solar_actual_24h.csv`) to construct their own "
        "scenario formulation.\n"
        "> - **(b) Tools without native stochastic support** (tested under B-4 instead) "
        "should consume the pre-generated scenario multiplier file "
        "(`" + context.scenario_file_name + "`) for their deterministic scenario loop.\n"
    )


def _build_b4_data_note(context: GuideUpdateContext) -> str:
    """Build the B-4 (Stochastic Scenario Wrapping) data source note."""
    return (
        "\n> **Scenario data (augmented):** The pre-generated scenario multiplier file "
        "`" + context.scenario_file_name + "` provides 50 scenarios across 24 hours. "
        "Tools should consume this file as the input dataset for the deterministic "
        "scenario loop, replacing any previously described distribution sampling.\n"
    )


def _build_schema_reference_note(context: GuideUpdateContext) -> str:
    """Build the Canonical CSV Schema Reference note."""
    return (
        "\n### Canonical CSV Schema Reference\n"
        "\n"
        "All augmented data files conform to the Canonical CSV Schema specification "
        f"v{context.canonical_csv_version}. For complete file format details including "
        "column names, data types, units, and validation rules, see:\n"
        "\n"
        f"- **Markdown documentation:** `{context.schema_doc_relative_path}`\n"
        f"- **JSON Schema:** `{context.schema_json_relative_path}`\n"
    )


def _build_c4_data_note(context: GuideUpdateContext) -> str:
    """Build the C-4 (SCUC scalability) temporal data source note."""
    return (
        "\n> **Temporal data source (augmented):** SCUC scalability tests consume "
        "the same 24-hour temporal profiles from `"
        + context.timeseries_base_dir
        + "<network>/` as test A-5 (load, wind, solar, and generator temporal "
        "parameters).\n"
    )


def _build_c6_data_note(context: GuideUpdateContext) -> str:
    """Build the C-6 (Stochastic scalability) scenario data source note."""
    return (
        "\n> **Scenario data source (augmented):** Stochastic scalability tests consume "
        "the same scenario multiplier file (`" + context.scenario_file_name + "`) "
        "as test B-4.\n"
    )


def generate_protocol_edits(context: GuideUpdateContext) -> list[EditOperation]:
    """Generate the list of edits to apply to the test protocol.

    Produces edits for:
    - Reference Networks table: add time series data column
    - New "Time Series Data" section after "Data Format Notes"
    - A-5 (SCUC): clarify temporal profile source
    - A-6 (SCED): clarify profile source
    - A-8 (Stochastic): add native vs. provided scenario data note
    - B-4 (Stochastic wrapping): reference scenario multiplier file
    - New "Canonical CSV Schema Reference" note
    - C-4 (SCUC scalability): reference temporal data source
    - C-6 (Stochastic scalability): reference scenario data source

    Args:
        context: The assembled update context.

    Returns:
        A list of EditOperation objects targeting the protocol.
    """
    edits: list[EditOperation] = []

    # 1. Reference Networks table: add time series availability note
    ts_note = _build_timeseries_availability_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="Reference Networks",
            old_text=None,
            new_text=ts_note,
            description="Add time series availability note to Reference Networks section",
        )
    )

    # 2. New "Time Series Data" section after "Data Format Notes"
    ts_section = _build_timeseries_data_section(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="Data Format Notes",
            old_text=None,
            new_text=ts_section,
            description="Add Time Series Data section after Data Format Notes",
        )
    )

    # 3. A-5 (SCUC): clarify temporal profile source
    a5_note = _build_a5_data_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="A-5",
            old_text=None,
            new_text=a5_note,
            description="Add augmented data source note to A-5 (SCUC)",
        )
    )

    # 4. A-6 (SCED): clarify profile source
    a6_note = _build_a6_data_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="A-6",
            old_text=None,
            new_text=a6_note,
            description="Add augmented data source note to A-6 (SCED)",
        )
    )

    # 5. A-8 (Stochastic): add native vs. provided scenario data note
    a8_note = _build_a8_stochastic_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="A-8",
            old_text=None,
            new_text=a8_note,
            description="Add stochastic dual-path note to A-8",
        )
    )

    # 6. B-4 (Stochastic Scenario Wrapping): reference scenario multiplier file
    b4_note = _build_b4_data_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="B-4",
            old_text=None,
            new_text=b4_note,
            description="Add scenario multiplier file reference to B-4",
        )
    )

    # 7. Canonical CSV Schema Reference note (append to end)
    schema_note = _build_schema_reference_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="append",
            marker="",
            old_text=None,
            new_text=schema_note,
            description="Add Canonical CSV Schema Reference section",
        )
    )

    # 8. C-4 (SCUC scalability): reference temporal data source
    c4_note = _build_c4_data_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="C-4",
            old_text=None,
            new_text=c4_note,
            description="Add temporal data source note to C-4 (SCUC scalability)",
        )
    )

    # 9. C-6 (Stochastic scalability): reference scenario data source
    c6_note = _build_c6_data_note(context)
    edits.append(
        EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="C-6",
            old_text=None,
            new_text=c6_note,
            description="Add scenario data source note to C-6 (Stochastic scalability)",
        )
    )

    return edits


# ---------------------------------------------------------------------------
# Edit application
# ---------------------------------------------------------------------------


def find_marker_line(lines: list[str], marker: str) -> int | None:
    """Find the line index containing a marker string.

    Searches for the first line that contains the marker as a
    substring (case-sensitive). Returns the 0-based line index,
    or None if not found.

    Args:
        lines: The document lines.
        marker: The substring to search for.

    Returns:
        The 0-based line index, or None.
    """
    for i, line in enumerate(lines):
        if marker in line:
            return i
    return None


def find_block(lines: list[str], old_text: str) -> tuple[int, int] | None:
    """Find the start and end line indices of a text block.

    Searches for a contiguous block of lines that matches old_text
    (after stripping trailing whitespace from each line). Returns
    (start_index, end_index) where end_index is exclusive, or None
    if the block is not found.

    Args:
        lines: The document lines.
        old_text: The multi-line text block to find.

    Returns:
        A tuple of (start, end) line indices, or None.
    """
    old_lines = old_text.split("\n")
    # Strip trailing whitespace for comparison
    old_stripped = [line.rstrip() for line in old_lines]
    n_old = len(old_stripped)

    if n_old == 0:
        return None

    for i in range(len(lines) - n_old + 1):
        match = True
        for j in range(n_old):
            if lines[i + j].rstrip() != old_stripped[j]:
                match = False
                break
        if match:
            return (i, i + n_old)
    return None


def apply_edits(
    document_text: str,
    edits: list[EditOperation],
) -> tuple[str, int, list[str]]:
    """Apply a list of edit operations to a document.

    Processes edits in order. Each edit modifies the document text
    in place (accumulated across edits). If an edit's marker or
    old_text is not found, the edit is skipped and its description
    is recorded.

    Edit types:
    - "insert_after": Insert new_text on the line after the marker.
    - "replace_block": Replace old_text with new_text.
    - "append": Append new_text to the end of the document.

    Args:
        document_text: The full document text.
        edits: List of EditOperation objects to apply.

    Returns:
        A tuple of (updated_text, edits_applied_count,
        skipped_descriptions).
    """
    applied = 0
    skipped: list[str] = []

    for edit in edits:
        if edit.edit_type == "insert_after":
            lines = document_text.split("\n")
            idx = find_marker_line(lines, edit.marker)
            if idx is None:
                skipped.append(edit.description)
                continue
            # Insert new_text lines after the marker line
            new_lines = edit.new_text.split("\n")
            lines = lines[: idx + 1] + new_lines + lines[idx + 1 :]
            document_text = "\n".join(lines)
            applied += 1

        elif edit.edit_type == "replace_block":
            if edit.old_text is None:
                skipped.append(edit.description)
                continue
            lines = document_text.split("\n")
            block = find_block(lines, edit.old_text)
            if block is None:
                skipped.append(edit.description)
                continue
            start, end = block
            new_lines = edit.new_text.split("\n")
            lines = lines[:start] + new_lines + lines[end:]
            document_text = "\n".join(lines)
            applied += 1

        elif edit.edit_type == "append":
            document_text = document_text.rstrip("\n") + "\n" + edit.new_text
            applied += 1

        else:
            skipped.append(edit.description)

    return document_text, applied, skipped


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def update_guide(
    guide_id: GuideFileId,
    guide_path: Path,
    edits: list[EditOperation],
    output_path: Path | None = None,
) -> GuideUpdateResult:
    """Read a guide document, apply edits, and write the result.

    If output_path is None, the guide is updated in place. If
    output_path is provided, the original is left unchanged and
    the updated version is written to output_path.

    Args:
        guide_id: Which guide document this is.
        guide_path: Path to the existing guide document.
        edits: List of edits to apply.
        output_path: Optional separate output path. If None,
            overwrites guide_path.

    Returns:
        A GuideUpdateResult documenting the edits applied and skipped.

    Raises:
        FileNotFoundError: If guide_path does not exist.
    """
    if not guide_path.exists():
        msg = f"Guide file not found: {guide_path}"
        raise FileNotFoundError(msg)

    document_text = guide_path.read_text()
    updated_text, applied, skipped_descs = apply_edits(document_text, edits)

    dest = output_path if output_path is not None else guide_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(updated_text)

    return GuideUpdateResult(
        guide=guide_id,
        original_path=guide_path,
        output_path=dest,
        edits_applied=applied,
        edits_skipped=len(skipped_descs),
        skipped_descriptions=skipped_descs,
    )


def main(
    repo_root: Path | None = None,
    *,
    in_place: bool = False,
    output_dir: Path | None = None,
) -> list[GuideUpdateResult]:
    """Entry point: update both evaluation guide documents.

    Assembles the update context from D4 and D5 outputs, generates
    edits for both guides, and applies them.

    By default, writes updated guides to the output_dir (defaulting
    to evaluation_guides/). If in_place is True, overwrites the
    original files. If output_dir is provided, writes updated files
    there with the same filenames.

    Args:
        repo_root: Repository root. Defaults to auto-detection.
        in_place: If True, overwrite original files.
        output_dir: Directory to write updated files. Defaults to
            the same directory as the originals.

    Returns:
        A list of GuideUpdateResult, one per guide document.
    """
    if repo_root is None:
        # Auto-detect: walk up from this script to find repo root
        repo_root = Path(__file__).resolve().parent.parent.parent

    paths = GuideFilePaths.from_repo_root(repo_root)
    context = build_update_context(repo_root)

    rubric_edits = generate_rubric_edits(context)
    protocol_edits = generate_protocol_edits(context)

    results: list[GuideUpdateResult] = []

    # Determine output paths
    if in_place:
        rubric_output = None
        protocol_output = None
    elif output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        rubric_output = output_dir / paths.rubric_path.name
        protocol_output = output_dir / paths.protocol_path.name
    else:
        rubric_output = None
        protocol_output = None

    results.append(update_guide(GuideFileId.RUBRIC, paths.rubric_path, rubric_edits, rubric_output))
    results.append(
        update_guide(GuideFileId.PROTOCOL, paths.protocol_path, protocol_edits, protocol_output)
    )

    return results


if __name__ == "__main__":
    import sys

    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    guide_results = main(repo, in_place=True)
    for r in guide_results:
        print(
            f"{r.guide}: {r.edits_applied} edits applied, "
            f"{r.edits_skipped} skipped -> {r.output_path}"
        )
        if r.skipped_descriptions:
            for desc in r.skipped_descriptions:
                print(f"  SKIPPED: {desc}")
