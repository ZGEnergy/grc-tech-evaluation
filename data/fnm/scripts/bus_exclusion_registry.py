"""Bus Exclusion Registry for FNM verification.

Analyzes intermediate format bus, branch, and transformer tables to identify
all buses that must be excluded from ACPF and DCPF verification metrics.
Three exclusion categories: PSS/E-declared isolated buses (IDE=4),
de-energized buses (VM=0), and topologically disconnected buses.

For each excluded bus, the registry records bus number, name, area, zone,
base kV, and a machine-readable exclusion reason. Output formats: CSV and JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Exclusion reason classification
# ---------------------------------------------------------------------------


class ExclusionReason(Enum):
    """Why a bus is excluded from verification metrics."""

    IDE_4_ISOLATED = "ide_4_isolated"
    """Bus type code IDE=4 in the PSS/E bus record."""

    VM_ZERO_DEENERGIZED = "vm_zero_deenergized"
    """Bus voltage magnitude VM=0.0 in the solved case."""

    DISCONNECTED_ISLAND = "disconnected_island"
    """Bus belongs to a connected component that does not contain the slack bus."""


# Priority order for primary reason assignment when multiple apply.
# Lower index = higher priority.
EXCLUSION_PRIORITY: list[ExclusionReason] = [
    ExclusionReason.IDE_4_ISOLATED,
    ExclusionReason.VM_ZERO_DEENERGIZED,
    ExclusionReason.DISCONNECTED_ISLAND,
]


# ---------------------------------------------------------------------------
# Per-bus exclusion record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExcludedBusRecord:
    """A single bus excluded from verification metrics."""

    bus_number: int
    """PSS/E bus number (I field)."""

    bus_name: str
    """PSS/E bus name (NAME field). May be empty or whitespace-padded."""

    area: int
    """Area number (AREA field)."""

    zone: int
    """Zone number (ZONE field)."""

    base_kv: float
    """Bus base voltage in kV (BASKV field)."""

    primary_reason: ExclusionReason
    """The highest-priority exclusion reason that applies to this bus."""

    all_reasons: list[ExclusionReason]
    """All exclusion reasons that apply, ordered by priority."""

    island_id: int | None
    """Connected component ID this bus belongs to. None if IDE=4 and the
    bus was excluded before connectivity analysis."""

    vm: float
    """Voltage magnitude from the bus table (for diagnostic reference)."""

    va: float
    """Voltage angle from the bus table (for diagnostic reference)."""

    ide: int
    """Bus type code from the bus table."""


# ---------------------------------------------------------------------------
# Island summary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IslandSummary:
    """Summary of one connected component in the network."""

    island_id: int
    """Sequential integer ID. 0 = main island (contains the slack bus)."""

    bus_count: int
    """Number of buses in this island."""

    is_main: bool
    """True if this island contains the slack bus."""

    slack_bus: int | None
    """Slack bus number if this is the main island, else None."""

    sample_buses: list[int]
    """Up to 5 bus numbers from this island (for diagnostic display)."""

    voltage_levels: list[float]
    """Distinct base kV values present in this island, sorted descending."""


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExclusionSummary:
    """Aggregate statistics for the bus exclusion registry."""

    total_buses: int
    """Total number of buses in the intermediate format bus table."""

    excluded_total: int
    """Total number of unique excluded buses."""

    excluded_by_reason: dict[str, int]
    """Count of buses where each reason is the primary reason."""

    remaining_for_verification: int
    """total_buses - excluded_total."""

    connected_components: int
    """Total number of connected components found."""

    main_island_size: int
    """Number of buses in the main island."""

    disconnected_island_count: int
    """Number of connected components that are NOT the main island."""

    disconnected_island_sizes: list[int]
    """Size of each disconnected island, sorted descending."""

    islands: list[IslandSummary]
    """Summary of every connected component, main island first."""

    ide4_count: int
    """Number of buses with IDE=4."""

    vm_zero_count: int
    """Number of buses with VM=0.0. May overlap with IDE=4 count."""

    disconnected_count: int
    """Number of buses whose primary reason is DISCONNECTED_ISLAND."""


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegistryMetadata:
    """Provenance metadata for the bus exclusion registry."""

    bus_csv_path: str
    """Path to the bus table CSV that was analyzed."""

    branch_csv_path: str
    """Path to the branch table CSV used for connectivity."""

    transformer_csv_path: str
    """Path to the transformer table CSV used for connectivity."""

    generated_timestamp: str
    """ISO 8601 timestamp of when the registry was generated."""

    slack_bus_number: int
    """The slack bus (IDE=3) used as the main island anchor."""

    vm_zero_threshold: float
    """Threshold for VM=0 detection."""

    graph_node_count: int
    """Number of nodes in the connectivity graph (total buses minus IDE=4)."""

    graph_edge_count: int
    """Number of edges in the connectivity graph."""


# ---------------------------------------------------------------------------
# Top-level registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusExclusionRegistry:
    """Complete bus exclusion registry output."""

    excluded_buses: list[ExcludedBusRecord]
    """All excluded buses, sorted by bus number."""

    summary: ExclusionSummary
    """Aggregate statistics."""

    metadata: RegistryMetadata
    """Provenance and configuration metadata."""


# ---------------------------------------------------------------------------
# Column name mapping helpers
# ---------------------------------------------------------------------------

_BUS_COLUMN_MAP: dict[str, list[str]] = {
    "I": ["i", "bus_i", "number", "bus_number"],
    "IDE": ["ide", "type", "bus_type"],
    "VM": ["vm", "vm_pu"],
    "VA": ["va", "va_deg"],
    "BASKV": ["baskv", "basekv", "vnom", "base_kv"],
    "NAME": ["name", "bus_name"],
    "AREA": ["area"],
    "ZONE": ["zone"],
    "OWNER": ["owner"],
}

_BRANCH_COLUMN_MAP: dict[str, list[str]] = {
    "I": ["i", "fbus", "from_bus"],
    "J": ["j", "tbus", "to_bus"],
    "CKT": ["ckt", "circuit"],
    "ST": ["st", "status", "br_status"],
}

_TRANSFORMER_COLUMN_MAP: dict[str, list[str]] = {
    "I": ["i", "fbus", "bus1"],
    "J": ["j", "tbus", "bus2"],
    "K": ["k", "bus3"],
    "CKT": ["ckt", "circuit"],
    "STAT": ["stat", "status"],
}


def _resolve_columns(
    headers: list[str],
    column_map: dict[str, list[str]],
    required: list[str],
) -> dict[str, int]:
    """Map normalized column names to CSV column indices.

    Args:
        headers: Raw CSV header row.
        column_map: Mapping from canonical name to list of variant names.
        required: Canonical names that must be found.

    Returns:
        Dict mapping canonical name to column index.

    Raises:
        ValueError: If a required column cannot be found.
    """
    lower_headers = [h.strip().lower() for h in headers]
    result: dict[str, int] = {}

    for canonical, variants in column_map.items():
        # Check canonical name first (case-insensitive)
        canonical_lower = canonical.lower()
        if canonical_lower in lower_headers:
            result[canonical] = lower_headers.index(canonical_lower)
            continue
        # Check variants
        for variant in variants:
            if variant.lower() in lower_headers:
                result[canonical] = lower_headers.index(variant.lower())
                break

    missing = [r for r in required if r not in result]
    if missing:
        raise ValueError(f"Required columns not found: {missing}. Available headers: {headers}")
    return result


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def load_bus_table(bus_csv_path: Path) -> list[dict[str, str | int | float]]:
    """Load the intermediate format bus table from CSV.

    Reads the bus CSV produced by the canonical parser. Expects columns
    matching the Phase 1 D7 intermediate format bus schema.

    Args:
        bus_csv_path: Path to the bus table CSV file.

    Returns:
        List of dicts with keys normalized to PSS/E field names and values
        cast to appropriate types.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not bus_csv_path.exists():
        raise FileNotFoundError(f"Bus CSV not found: {bus_csv_path}")

    with open(bus_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Bus CSV is empty: {bus_csv_path}")

    headers = rows[0]
    col_map = _resolve_columns(headers, _BUS_COLUMN_MAP, required=["I", "IDE", "VM"])
    data_rows = rows[1:]

    result: list[dict[str, str | int | float]] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        bus: dict[str, str | int | float] = {}
        bus["I"] = int(float(row[col_map["I"]].strip()))
        bus["IDE"] = int(float(row[col_map["IDE"]].strip()))
        bus["VM"] = float(row[col_map["VM"]].strip())
        bus["VA"] = float(row[col_map.get("VA", col_map["VM"])].strip()) if "VA" in col_map else 0.0
        bus["BASKV"] = float(row[col_map["BASKV"]].strip()) if "BASKV" in col_map else 0.0
        bus["NAME"] = row[col_map["NAME"]].strip() if "NAME" in col_map else ""
        bus["AREA"] = int(float(row[col_map["AREA"]].strip())) if "AREA" in col_map else 0
        bus["ZONE"] = int(float(row[col_map["ZONE"]].strip())) if "ZONE" in col_map else 0

        result.append(bus)

    return result


def load_branch_table(branch_csv_path: Path) -> list[dict[str, str | int | float]]:
    """Load the intermediate format branch table from CSV.

    Args:
        branch_csv_path: Path to the branch table CSV file.

    Returns:
        List of dicts with keys normalized to I, J, CKT, ST.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not branch_csv_path.exists():
        raise FileNotFoundError(f"Branch CSV not found: {branch_csv_path}")

    with open(branch_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Branch CSV is empty: {branch_csv_path}")

    headers = rows[0]
    col_map = _resolve_columns(headers, _BRANCH_COLUMN_MAP, required=["I", "J", "ST"])
    data_rows = rows[1:]

    result: list[dict[str, str | int | float]] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        branch: dict[str, str | int | float] = {}
        branch["I"] = int(float(row[col_map["I"]].strip()))
        branch["J"] = int(float(row[col_map["J"]].strip()))
        branch["ST"] = int(float(row[col_map["ST"]].strip()))
        branch["CKT"] = row[col_map["CKT"]].strip() if "CKT" in col_map else ""

        result.append(branch)

    return result


def load_transformer_table(
    transformer_csv_path: Path,
) -> list[dict[str, str | int | float]]:
    """Load the intermediate format transformer table from CSV.

    Args:
        transformer_csv_path: Path to the transformer table CSV file.

    Returns:
        List of dicts with keys normalized to I, J, K, CKT, STAT.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns cannot be identified.
    """
    if not transformer_csv_path.exists():
        raise FileNotFoundError(f"Transformer CSV not found: {transformer_csv_path}")

    with open(transformer_csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Transformer CSV is empty: {transformer_csv_path}")

    headers = rows[0]
    col_map = _resolve_columns(headers, _TRANSFORMER_COLUMN_MAP, required=["I", "J", "STAT"])
    data_rows = rows[1:]

    result: list[dict[str, str | int | float]] = []
    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        xfmr: dict[str, str | int | float] = {}
        xfmr["I"] = int(float(row[col_map["I"]].strip()))
        xfmr["J"] = int(float(row[col_map["J"]].strip()))
        xfmr["K"] = int(float(row[col_map["K"]].strip())) if "K" in col_map else 0
        xfmr["STAT"] = int(float(row[col_map["STAT"]].strip()))
        xfmr["CKT"] = row[col_map["CKT"]].strip() if "CKT" in col_map else ""

        result.append(xfmr)

    return result


# ---------------------------------------------------------------------------
# Exclusion detection -- IDE=4
# ---------------------------------------------------------------------------


def find_ide4_buses(bus_rows: list[dict]) -> set[int]:
    """Identify buses with IDE=4 (PSS/E isolated bus type code).

    Args:
        bus_rows: Bus table rows from ``load_bus_table()``.

    Returns:
        Set of bus numbers (I) where IDE == 4.
    """
    return {int(row["I"]) for row in bus_rows if int(row["IDE"]) == 4}


# ---------------------------------------------------------------------------
# Exclusion detection -- VM=0
# ---------------------------------------------------------------------------


def find_vm_zero_buses(
    bus_rows: list[dict],
    threshold: float = 0.0,
) -> set[int]:
    """Identify buses with voltage magnitude of exactly zero.

    Args:
        bus_rows: Bus table rows from ``load_bus_table()``.
        threshold: VM values <= this threshold are classified as zero.

    Returns:
        Set of bus numbers (I) where VM <= threshold.
    """
    return {int(row["I"]) for row in bus_rows if float(row["VM"]) <= threshold}


# ---------------------------------------------------------------------------
# Network connectivity analysis
# ---------------------------------------------------------------------------


def build_connectivity_graph(
    bus_rows: list[dict],
    branch_rows: list[dict],
    transformer_rows: list[dict],
    excluded_bus_numbers: set[int],
) -> dict[int, set[int]]:
    """Build an undirected adjacency list from in-service branches and
    transformers, excluding pre-identified buses.

    Args:
        bus_rows: All bus table rows (used to enumerate graph nodes).
        branch_rows: Branch table rows.
        transformer_rows: Transformer table rows.
        excluded_bus_numbers: Bus numbers to exclude from the graph.

    Returns:
        Adjacency list mapping each bus number to the set of connected buses.
    """
    # Initialize nodes: all non-excluded buses
    adjacency: dict[int, set[int]] = {}
    for row in bus_rows:
        bus_num = int(row["I"])
        if bus_num not in excluded_bus_numbers:
            adjacency[bus_num] = set()

    def _add_edge(a: int, b: int) -> None:
        if a == b:
            return
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)

    # Edges from in-service branches
    for row in branch_rows:
        if int(row["ST"]) != 1:
            continue
        i = int(row["I"])
        j = int(row["J"])
        _add_edge(i, j)

    # Edges from in-service transformers
    for row in transformer_rows:
        if int(row["STAT"]) != 1:
            continue
        i = int(row["I"])
        j = int(row["J"])
        k = int(row.get("K", 0))

        # Two-winding: K=0
        _add_edge(i, j)

        # Three-winding: K!=0 -> fully connect I, J, K
        if k != 0:
            _add_edge(i, k)
            _add_edge(j, k)

    return adjacency


def find_connected_components(
    adjacency: dict[int, set[int]],
) -> list[set[int]]:
    """Find all connected components in an undirected graph via BFS.

    Args:
        adjacency: Undirected adjacency list.

    Returns:
        List of sets sorted by descending size.
    """
    visited: set[int] = set()
    components: list[set[int]] = []

    for node in adjacency:
        if node in visited:
            continue
        # BFS
        queue: deque[int] = deque([node])
        component: set[int] = set()
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)

    # Sort by descending size
    components.sort(key=len, reverse=True)
    return components


def identify_main_island(
    components: list[set[int]],
    bus_rows: list[dict],
) -> tuple[int, int]:
    """Identify the main island as the component containing the slack bus.

    Args:
        components: Connected components from ``find_connected_components()``.
        bus_rows: Bus table rows (to find IDE=3 bus).

    Returns:
        Tuple of (component_index, slack_bus_number).

    Raises:
        ValueError: If no bus with IDE=3 is found.
    """
    # Find the first IDE=3 bus
    slack_bus: int | None = None
    for row in bus_rows:
        if int(row["IDE"]) == 3:
            slack_bus = int(row["I"])
            break

    if slack_bus is None:
        raise ValueError("No slack bus (IDE=3) found in the bus table.")

    for idx, component in enumerate(components):
        if slack_bus in component:
            return idx, slack_bus

    raise ValueError(
        f"Slack bus {slack_bus} not found in any connected component. "
        "It may have been excluded as IDE=4."
    )


def find_disconnected_buses(
    components: list[set[int]],
    main_island_index: int,
) -> set[int]:
    """Return bus numbers from all components except the main island.

    Args:
        components: Connected components.
        main_island_index: Index of the main island.

    Returns:
        Set of bus numbers belonging to non-main-island components.
    """
    result: set[int] = set()
    for idx, component in enumerate(components):
        if idx != main_island_index:
            result |= component
    return result


# ---------------------------------------------------------------------------
# Registry assembly
# ---------------------------------------------------------------------------


def build_excluded_bus_records(
    bus_rows: list[dict],
    ide4_buses: set[int],
    vm_zero_buses: set[int],
    disconnected_buses: set[int],
) -> list[ExcludedBusRecord]:
    """Assemble ExcludedBusRecord for every excluded bus.

    Args:
        bus_rows: All bus table rows.
        ide4_buses: Bus numbers with IDE=4.
        vm_zero_buses: Bus numbers with VM=0.
        disconnected_buses: Bus numbers in disconnected islands.

    Returns:
        List of ExcludedBusRecord sorted by bus_number ascending.
    """
    all_excluded = ide4_buses | vm_zero_buses | disconnected_buses
    if not all_excluded:
        return []

    # Build lookup by bus number
    bus_lookup: dict[int, dict] = {}
    for row in bus_rows:
        bus_lookup[int(row["I"])] = row

    records: list[ExcludedBusRecord] = []
    for bus_num in sorted(all_excluded):
        bus_row = bus_lookup.get(bus_num)
        if bus_row is None:
            continue

        # Determine all applicable reasons in priority order
        all_reasons: list[ExclusionReason] = []
        for reason in EXCLUSION_PRIORITY:
            if reason == ExclusionReason.IDE_4_ISOLATED and bus_num in ide4_buses:
                all_reasons.append(reason)
            elif reason == ExclusionReason.VM_ZERO_DEENERGIZED and bus_num in vm_zero_buses:
                all_reasons.append(reason)
            elif reason == ExclusionReason.DISCONNECTED_ISLAND and bus_num in disconnected_buses:
                all_reasons.append(reason)

        primary_reason = all_reasons[0]

        # IDE=4 buses have island_id=None (excluded before connectivity)
        island_id: int | None = None
        if bus_num in ide4_buses:
            island_id = None
        # For non-IDE=4 buses, island_id will be set by the caller if needed
        # We leave it as None here; build_registry sets it properly

        records.append(
            ExcludedBusRecord(
                bus_number=bus_num,
                bus_name=str(bus_row.get("NAME", "")),
                area=int(bus_row.get("AREA", 0)),
                zone=int(bus_row.get("ZONE", 0)),
                base_kv=float(bus_row.get("BASKV", 0.0)),
                primary_reason=primary_reason,
                all_reasons=all_reasons,
                island_id=island_id,
                vm=float(bus_row.get("VM", 0.0)),
                va=float(bus_row.get("VA", 0.0)),
                ide=int(bus_row.get("IDE", 0)),
            )
        )

    return records


def _assign_island_ids(
    records: list[ExcludedBusRecord],
    components: list[set[int]],
    main_island_index: int,
) -> list[ExcludedBusRecord]:
    """Assign island_id to excluded bus records based on component membership.

    Main island = island_id 0. Other islands get sequential IDs starting at 1,
    ordered by descending size.

    IDE=4 buses retain island_id=None.
    """
    # Build bus -> island_id mapping
    bus_to_island: dict[int, int] = {}
    # Main island gets id=0
    for bus_num in components[main_island_index]:
        bus_to_island[bus_num] = 0

    # Other islands get sequential IDs by descending size
    other_indices = [i for i in range(len(components)) if i != main_island_index]
    # They are already sorted by descending size from find_connected_components
    for isl_id, idx in enumerate(other_indices, start=1):
        for bus_num in components[idx]:
            bus_to_island[bus_num] = isl_id

    updated: list[ExcludedBusRecord] = []
    for rec in records:
        if rec.primary_reason == ExclusionReason.IDE_4_ISOLATED:
            updated.append(rec)
        else:
            rec_island_id: int | None = bus_to_island.get(rec.bus_number)
            updated.append(
                ExcludedBusRecord(
                    bus_number=rec.bus_number,
                    bus_name=rec.bus_name,
                    area=rec.area,
                    zone=rec.zone,
                    base_kv=rec.base_kv,
                    primary_reason=rec.primary_reason,
                    all_reasons=rec.all_reasons,
                    island_id=rec_island_id,
                    vm=rec.vm,
                    va=rec.va,
                    ide=rec.ide,
                )
            )
    return updated


def build_island_summaries(
    components: list[set[int]],
    main_island_index: int,
    slack_bus_number: int,
    bus_rows: list[dict],
) -> list[IslandSummary]:
    """Build IslandSummary for every connected component.

    Args:
        components: Connected components.
        main_island_index: Index of the main island.
        slack_bus_number: The slack bus number.
        bus_rows: Bus table rows (for base kV lookup).

    Returns:
        List of IslandSummary, main island first, then by descending size.
    """
    bus_kv: dict[int, float] = {}
    for row in bus_rows:
        bus_kv[int(row["I"])] = float(row.get("BASKV", 0.0))

    summaries: list[IslandSummary] = []

    # Main island first (id=0)
    main_component = components[main_island_index]
    main_buses_sorted = sorted(main_component)
    main_kvs = sorted({bus_kv.get(b, 0.0) for b in main_component}, reverse=True)
    summaries.append(
        IslandSummary(
            island_id=0,
            bus_count=len(main_component),
            is_main=True,
            slack_bus=slack_bus_number,
            sample_buses=main_buses_sorted[:5],
            voltage_levels=main_kvs,
        )
    )

    # Other islands by descending size
    other_indices = [i for i in range(len(components)) if i != main_island_index]
    for island_id, idx in enumerate(other_indices, start=1):
        comp = components[idx]
        comp_sorted = sorted(comp)
        kvs = sorted({bus_kv.get(b, 0.0) for b in comp}, reverse=True)
        summaries.append(
            IslandSummary(
                island_id=island_id,
                bus_count=len(comp),
                is_main=False,
                slack_bus=None,
                sample_buses=comp_sorted[:5],
                voltage_levels=kvs,
            )
        )

    return summaries


def build_exclusion_summary(
    total_buses: int,
    excluded_records: list[ExcludedBusRecord],
    island_summaries: list[IslandSummary],
    ide4_count: int,
    vm_zero_count: int,
    disconnected_count: int,
) -> ExclusionSummary:
    """Compute aggregate exclusion statistics.

    Args:
        total_buses: Total buses in the bus table.
        excluded_records: All excluded bus records.
        island_summaries: Island summaries.
        ide4_count: Total IDE=4 buses.
        vm_zero_count: Total VM=0 buses (may overlap with IDE=4).
        disconnected_count: Buses excluded primarily for disconnection.

    Returns:
        An ExclusionSummary with all fields populated.
    """
    excluded_total = len(excluded_records)

    # Count by primary reason
    excluded_by_reason: dict[str, int] = {}
    for reason in ExclusionReason:
        count = sum(1 for r in excluded_records if r.primary_reason == reason)
        if count > 0:
            excluded_by_reason[reason.value] = count

    main_island_size = 0
    disconnected_islands: list[IslandSummary] = []
    for s in island_summaries:
        if s.is_main:
            main_island_size = s.bus_count
        else:
            disconnected_islands.append(s)

    disconnected_island_sizes = sorted([s.bus_count for s in disconnected_islands], reverse=True)

    return ExclusionSummary(
        total_buses=total_buses,
        excluded_total=excluded_total,
        excluded_by_reason=excluded_by_reason,
        remaining_for_verification=total_buses - excluded_total,
        connected_components=len(island_summaries),
        main_island_size=main_island_size,
        disconnected_island_count=len(disconnected_islands),
        disconnected_island_sizes=disconnected_island_sizes,
        islands=island_summaries,
        ide4_count=ide4_count,
        vm_zero_count=vm_zero_count,
        disconnected_count=disconnected_count,
    )


# ---------------------------------------------------------------------------
# Registry orchestration
# ---------------------------------------------------------------------------


def build_registry(
    bus_csv_path: Path,
    branch_csv_path: Path,
    transformer_csv_path: Path,
    vm_zero_threshold: float = 0.0,
) -> BusExclusionRegistry:
    """Orchestrate the full bus exclusion analysis.

    Args:
        bus_csv_path: Path to the bus table CSV.
        branch_csv_path: Path to the branch table CSV.
        transformer_csv_path: Path to the transformer table CSV.
        vm_zero_threshold: Threshold for VM=0 detection (default 0.0).

    Returns:
        A complete BusExclusionRegistry.

    Raises:
        FileNotFoundError: If any input CSV does not exist.
        ValueError: If required columns are missing or no slack bus found.
    """
    # 1. Load tables
    bus_rows = load_bus_table(bus_csv_path)
    branch_rows = load_branch_table(branch_csv_path)
    transformer_rows = load_transformer_table(transformer_csv_path)

    # 2. Identify IDE=4 buses
    ide4_buses = find_ide4_buses(bus_rows)

    # 3. Identify VM=0 buses
    vm_zero_buses = find_vm_zero_buses(bus_rows, threshold=vm_zero_threshold)

    # 4. Build connectivity graph (excluding IDE=4 buses)
    adjacency = build_connectivity_graph(
        bus_rows, branch_rows, transformer_rows, excluded_bus_numbers=ide4_buses
    )

    # Count edges
    edge_count = sum(len(neighbors) for neighbors in adjacency.values()) // 2

    # 5. Find connected components
    components = find_connected_components(adjacency)

    # 6. Identify main island
    main_island_index, slack_bus_number = identify_main_island(components, bus_rows)

    # 7. Find disconnected buses
    disconnected_buses = find_disconnected_buses(components, main_island_index)

    # 8. Build records
    excluded_records = build_excluded_bus_records(
        bus_rows, ide4_buses, vm_zero_buses, disconnected_buses
    )

    # Assign island IDs
    excluded_records = _assign_island_ids(excluded_records, components, main_island_index)

    # 9. Build island summaries
    island_summaries = build_island_summaries(
        components, main_island_index, slack_bus_number, bus_rows
    )

    # Count disconnected_count = buses whose primary reason is DISCONNECTED_ISLAND
    disconnected_primary_count = sum(
        1 for r in excluded_records if r.primary_reason == ExclusionReason.DISCONNECTED_ISLAND
    )

    # 10. Build summary
    summary = build_exclusion_summary(
        total_buses=len(bus_rows),
        excluded_records=excluded_records,
        island_summaries=island_summaries,
        ide4_count=len(ide4_buses),
        vm_zero_count=len(vm_zero_buses),
        disconnected_count=disconnected_primary_count,
    )

    # Build metadata
    metadata = RegistryMetadata(
        bus_csv_path=str(bus_csv_path),
        branch_csv_path=str(branch_csv_path),
        transformer_csv_path=str(transformer_csv_path),
        generated_timestamp=datetime.now(timezone.utc).isoformat(),
        slack_bus_number=slack_bus_number,
        vm_zero_threshold=vm_zero_threshold,
        graph_node_count=len(adjacency),
        graph_edge_count=edge_count,
    )

    return BusExclusionRegistry(
        excluded_buses=excluded_records,
        summary=summary,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Output serialization
# ---------------------------------------------------------------------------


def registry_to_dict(registry: BusExclusionRegistry) -> dict:
    """Convert a BusExclusionRegistry to a JSON-serializable dict.

    Args:
        registry: The registry to serialize.

    Returns:
        A dict safe for ``json.dumps()``.
    """
    excluded_buses = []
    for rec in registry.excluded_buses:
        excluded_buses.append(
            {
                "bus_number": rec.bus_number,
                "bus_name": rec.bus_name,
                "area": rec.area,
                "zone": rec.zone,
                "base_kv": rec.base_kv,
                "primary_reason": rec.primary_reason.value,
                "all_reasons": [r.value for r in rec.all_reasons],
                "island_id": rec.island_id,
                "vm": rec.vm,
                "va": rec.va,
                "ide": rec.ide,
            }
        )

    s = registry.summary
    summary = {
        "total_buses": s.total_buses,
        "excluded_total": s.excluded_total,
        "excluded_by_reason": s.excluded_by_reason,
        "remaining_for_verification": s.remaining_for_verification,
        "connected_components": s.connected_components,
        "main_island_size": s.main_island_size,
        "disconnected_island_count": s.disconnected_island_count,
        "disconnected_island_sizes": s.disconnected_island_sizes,
        "islands": [
            {
                "island_id": isl.island_id,
                "bus_count": isl.bus_count,
                "is_main": isl.is_main,
                "slack_bus": isl.slack_bus,
                "sample_buses": isl.sample_buses,
                "voltage_levels": isl.voltage_levels,
            }
            for isl in s.islands
        ],
        "ide4_count": s.ide4_count,
        "vm_zero_count": s.vm_zero_count,
        "disconnected_count": s.disconnected_count,
    }

    m = registry.metadata
    metadata = {
        "bus_csv_path": m.bus_csv_path,
        "branch_csv_path": m.branch_csv_path,
        "transformer_csv_path": m.transformer_csv_path,
        "generated_timestamp": m.generated_timestamp,
        "slack_bus_number": m.slack_bus_number,
        "vm_zero_threshold": m.vm_zero_threshold,
        "graph_node_count": m.graph_node_count,
        "graph_edge_count": m.graph_edge_count,
    }

    return {
        "excluded_buses": excluded_buses,
        "summary": summary,
        "metadata": metadata,
    }


def registry_to_csv(registry: BusExclusionRegistry, output_path: Path) -> None:
    """Write the excluded bus list as a CSV file.

    Args:
        registry: The bus exclusion registry.
        output_path: Path to write the CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "bus_number",
        "bus_name",
        "area",
        "zone",
        "base_kv",
        "primary_reason",
        "all_reasons",
        "island_id",
        "vm",
        "va",
        "ide",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in registry.excluded_buses:
            writer.writerow(
                {
                    "bus_number": rec.bus_number,
                    "bus_name": rec.bus_name,
                    "area": rec.area,
                    "zone": rec.zone,
                    "base_kv": rec.base_kv,
                    "primary_reason": rec.primary_reason.value,
                    "all_reasons": ";".join(r.value for r in rec.all_reasons),
                    "island_id": rec.island_id if rec.island_id is not None else "",
                    "vm": rec.vm,
                    "va": rec.va,
                    "ide": rec.ide,
                }
            )


def registry_to_json(registry: BusExclusionRegistry, output_path: Path) -> None:
    """Write the complete registry as a JSON file.

    Args:
        registry: The bus exclusion registry.
        output_path: Path to write the JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = registry_to_dict(registry)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the bus exclusion registry.

    Args:
        argv: Command-line arguments. If ``None``, reads from ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(
        description="Analyze FNM intermediate format to build a bus exclusion registry."
    )
    parser.add_argument(
        "--bus-csv",
        type=Path,
        required=True,
        help="Path to the bus table CSV.",
    )
    parser.add_argument(
        "--branch-csv",
        type=Path,
        required=True,
        help="Path to the branch table CSV.",
    )
    parser.add_argument(
        "--transformer-csv",
        type=Path,
        required=True,
        help="Path to the transformer table CSV.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/fnm/reference/).",
    )
    parser.add_argument(
        "--vm-threshold",
        type=float,
        default=0.0,
        help="VM threshold for de-energized classification (default: 0.0).",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    output_dir: Path = args.output_dir or Path("data/fnm/reference")

    try:
        registry = build_registry(
            bus_csv_path=args.bus_csv,
            branch_csv_path=args.branch_csv,
            transformer_csv_path=args.transformer_csv,
            vm_zero_threshold=args.vm_threshold,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1 if "slack" in str(exc).lower() else 2)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "excluded_buses.csv"
    json_path = output_dir / "excluded_buses.json"

    registry_to_csv(registry, csv_path)
    registry_to_json(registry, json_path)

    s = registry.summary
    print(f"Total buses: {s.total_buses}")
    print(
        f"Excluded: {s.excluded_total} "
        f"(IDE=4: {s.ide4_count}, VM=0: {s.vm_zero_count}, "
        f"disconnected: {s.disconnected_count})"
    )
    print(f"Remaining for verification: {s.remaining_for_verification}")
    print(
        f"Connected components: {s.connected_components} (main island: {s.main_island_size} buses)"
    )
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
