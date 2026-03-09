"""Tests for bus exclusion registry (PRD 03/01).

Tests T01-T08 are synthetic unit tests requiring no FNM data.
Tests T09-T10 are synthetic integration tests (end-to-end with temp CSV files).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from fnm.scripts.bus_exclusion_registry import (
    BusExclusionRegistry,
    ExcludedBusRecord,
    ExclusionReason,
    ExclusionSummary,
    IslandSummary,
    RegistryMetadata,
    build_connectivity_graph,
    build_excluded_bus_records,
    build_registry,
    find_connected_components,
    find_ide4_buses,
    find_vm_zero_buses,
    identify_main_island,
    registry_to_csv,
    registry_to_json,
)

# ---------------------------------------------------------------------------
# Helpers to build synthetic bus/branch/transformer rows
# ---------------------------------------------------------------------------


def _bus_row(
    bus_i: int,
    ide: int = 1,
    vm: float = 1.0,
    va: float = 0.0,
    name: str = "",
    area: int = 1,
    zone: int = 1,
    baskv: float = 115.0,
) -> dict:
    return {
        "I": bus_i,
        "IDE": ide,
        "VM": vm,
        "VA": va,
        "NAME": name,
        "AREA": area,
        "ZONE": zone,
        "BASKV": baskv,
    }


def _branch_row(i: int, j: int, st: int = 1) -> dict:
    return {"I": i, "J": j, "ST": st, "CKT": "1"}


def _xfmr_row(i: int, j: int, k: int = 0, stat: int = 1) -> dict:
    return {"I": i, "J": j, "K": k, "STAT": stat, "CKT": "1"}


# ---------------------------------------------------------------------------
# T01: test_find_ide4_buses
# ---------------------------------------------------------------------------


def test_find_ide4_buses() -> None:
    """T01: Create 10 buses, 2 with IDE=4, 1 with IDE=3, rest IDE=1.
    Verify exactly the 2 IDE=4 bus numbers are returned."""
    buses = [
        _bus_row(1, ide=3),  # slack
        _bus_row(2, ide=1),
        _bus_row(3, ide=1),
        _bus_row(4, ide=4),  # isolated
        _bus_row(5, ide=1),
        _bus_row(6, ide=1),
        _bus_row(7, ide=4),  # isolated
        _bus_row(8, ide=1),
        _bus_row(9, ide=1),
        _bus_row(10, ide=1),
    ]
    result = find_ide4_buses(buses)
    assert result == {4, 7}


# ---------------------------------------------------------------------------
# T02: test_find_vm_zero_buses
# ---------------------------------------------------------------------------


def test_find_vm_zero_buses() -> None:
    """T02: Create 10 buses, 3 with VM=0.0, rest with VM in [0.95, 1.05].
    Verify exactly the 3 VM=0 bus numbers are returned. Verify VM=0.001
    is NOT included."""
    buses = [
        _bus_row(1, vm=1.0),
        _bus_row(2, vm=0.0),  # VM=0
        _bus_row(3, vm=0.95),
        _bus_row(4, vm=0.0),  # VM=0
        _bus_row(5, vm=1.05),
        _bus_row(6, vm=0.0),  # VM=0
        _bus_row(7, vm=0.001),  # NOT zero
        _bus_row(8, vm=0.98),
        _bus_row(9, vm=1.02),
        _bus_row(10, vm=0.99),
    ]
    result = find_vm_zero_buses(buses)
    assert result == {2, 4, 6}
    assert 7 not in result  # 0.001 is not zero


# ---------------------------------------------------------------------------
# T03: test_build_connectivity_graph_excludes_ide4
# ---------------------------------------------------------------------------


def test_build_connectivity_graph_excludes_ide4() -> None:
    """T03: 5 buses in a chain (1-2-3-4-5), bus 3 is IDE=4.
    After excluding bus 3, nodes {1,2} and {4,5} should be disconnected."""
    buses = [
        _bus_row(1, ide=1),
        _bus_row(2, ide=1),
        _bus_row(3, ide=4),  # excluded
        _bus_row(4, ide=1),
        _bus_row(5, ide=1),
    ]
    branches = [
        _branch_row(1, 2),
        _branch_row(2, 3),
        _branch_row(3, 4),
        _branch_row(4, 5),
    ]
    adj = build_connectivity_graph(buses, branches, [], excluded_bus_numbers={3})

    # Node 3 not in graph
    assert 3 not in adj

    # Nodes 1,2 connected to each other
    assert 2 in adj[1]
    assert 1 in adj[2]

    # Nodes 4,5 connected to each other
    assert 5 in adj[4]
    assert 4 in adj[5]

    # No path between {1,2} and {4,5}
    assert adj[1] == {2}
    assert adj[2] == {1}
    assert adj[4] == {5}
    assert adj[5] == {4}


# ---------------------------------------------------------------------------
# T04: test_find_connected_components_simple
# ---------------------------------------------------------------------------


def test_find_connected_components_simple() -> None:
    """T04: Two disconnected clusters {1,2,3} and {4,5}."""
    adj: dict[int, set[int]] = {
        1: {2, 3},
        2: {1, 3},
        3: {1, 2},
        4: {5},
        5: {4},
    }
    components = find_connected_components(adj)
    assert len(components) == 2
    sizes = sorted([len(c) for c in components], reverse=True)
    assert sizes == [3, 2]


# ---------------------------------------------------------------------------
# T05: test_identify_main_island
# ---------------------------------------------------------------------------


def test_identify_main_island() -> None:
    """T05: Bus 1 is IDE=3 (slack). Two components: {1,2,3} and {4,5}.
    Main island should contain bus 1."""
    buses = [
        _bus_row(1, ide=3),
        _bus_row(2, ide=1),
        _bus_row(3, ide=1),
        _bus_row(4, ide=1),
        _bus_row(5, ide=1),
    ]
    components = [{1, 2, 3}, {4, 5}]
    idx, slack_bus = identify_main_island(components, buses)
    assert slack_bus == 1
    assert 1 in components[idx]


# ---------------------------------------------------------------------------
# T06: test_three_winding_transformer_connectivity
# ---------------------------------------------------------------------------


def test_three_winding_transformer_connectivity() -> None:
    """T06: 4 buses, one 3-winding transformer (I=1, J=2, K=3). No branches.
    Buses 1, 2, 3 should be mutually connected. Bus 4 is isolated."""
    buses = [
        _bus_row(1, ide=1),
        _bus_row(2, ide=1),
        _bus_row(3, ide=1),
        _bus_row(4, ide=1),
    ]
    xfmrs = [_xfmr_row(1, 2, k=3, stat=1)]
    adj = build_connectivity_graph(buses, [], xfmrs, excluded_bus_numbers=set())

    # 1, 2, 3 are all mutually connected
    assert 2 in adj[1] and 3 in adj[1]
    assert 1 in adj[2] and 3 in adj[2]
    assert 1 in adj[3] and 2 in adj[3]

    # Bus 4 is isolated
    assert adj[4] == set()


# ---------------------------------------------------------------------------
# T07: test_exclusion_priority_ordering
# ---------------------------------------------------------------------------


def test_exclusion_priority_ordering() -> None:
    """T07: A bus that is IDE=4, VM=0, and disconnected. Primary reason
    should be IDE_4_ISOLATED, all_reasons should contain all three."""
    buses = [_bus_row(99, ide=4, vm=0.0)]
    ide4 = {99}
    vm_zero = {99}
    disconnected = {99}

    records = build_excluded_bus_records(buses, ide4, vm_zero, disconnected)
    assert len(records) == 1
    rec = records[0]
    assert rec.primary_reason == ExclusionReason.IDE_4_ISOLATED
    assert ExclusionReason.IDE_4_ISOLATED in rec.all_reasons
    assert ExclusionReason.VM_ZERO_DEENERGIZED in rec.all_reasons
    assert ExclusionReason.DISCONNECTED_ISLAND in rec.all_reasons
    assert len(rec.all_reasons) == 3


# ---------------------------------------------------------------------------
# T08: test_out_of_service_branches_excluded_from_graph
# ---------------------------------------------------------------------------


def test_out_of_service_branches_excluded_from_graph() -> None:
    """T08: 3 buses, branch 1-2 in-service (ST=1), branch 2-3 out-of-service
    (ST=0). Edge 1-2 exists, edge 2-3 does not. Bus 3 is isolated node."""
    buses = [
        _bus_row(1, ide=1),
        _bus_row(2, ide=1),
        _bus_row(3, ide=1),
    ]
    branches = [
        _branch_row(1, 2, st=1),
        _branch_row(2, 3, st=0),
    ]
    adj = build_connectivity_graph(buses, branches, [], excluded_bus_numbers=set())

    assert 2 in adj[1]
    assert 1 in adj[2]
    assert 3 not in adj[2]
    assert adj[3] == set()


# ---------------------------------------------------------------------------
# Helper: write CSV from rows
# ---------------------------------------------------------------------------


def _write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    """Write a simple CSV file."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# T09: test_build_registry_end_to_end_synthetic
# ---------------------------------------------------------------------------


def test_build_registry_end_to_end_synthetic(tmp_path: Path) -> None:
    """T09: End-to-end with synthetic CSV files.

    20 buses:
    - Bus 1: IDE=3 (slack), VM=1.0
    - Buses 2-14: IDE=1, VM in [0.95..1.05] -- main island (14 buses incl slack)
    - Bus 15: IDE=4, VM=0.0  (excluded: IDE=4)
    - Bus 16: IDE=4, VM=1.0  (excluded: IDE=4)
    - Bus 17: IDE=1, VM=0.0  (excluded: VM=0, in main island)
    - Buses 18-20: IDE=1, VM=1.0  (excluded: disconnected island of 3)

    Branches form:
    - Main network: chain 1-2-3-...-14 plus bus 17 connected to bus 14
    - Disconnected island: chain 18-19-20
    - No branches to IDE=4 buses (15, 16)

    Transformers: 3 in-service 2-winding connecting pairs in main island.
    """
    bus_csv = tmp_path / "bus.csv"
    branch_csv = tmp_path / "branch.csv"
    xfmr_csv = tmp_path / "transformer.csv"

    # Bus data
    bus_headers = ["I", "NAME", "BASKV", "IDE", "AREA", "ZONE", "VM", "VA"]
    bus_data: list[list] = []
    # Slack bus
    bus_data.append([1, "SLACK", 230.0, 3, 1, 1, 1.0, 0.0])
    # Main island buses 2-14
    for i in range(2, 15):
        vm = 0.95 + (i % 10) * 0.01
        bus_data.append([i, f"BUS-{i}", 115.0, 1, 1, 1, vm, -1.0 * (i % 5)])
    # IDE=4 buses
    bus_data.append([15, "ISOL-1", 230.0, 4, 2, 2, 0.0, 0.0])
    bus_data.append([16, "ISOL-2", 115.0, 4, 2, 2, 1.0, 0.0])
    # VM=0 bus (still connected in main island)
    bus_data.append([17, "DEENRG", 69.0, 1, 1, 1, 0.0, 0.0])
    # Disconnected island
    bus_data.append([18, "ISLAND-1", 69.0, 1, 3, 3, 1.01, -5.0])
    bus_data.append([19, "ISLAND-2", 69.0, 1, 3, 3, 0.99, -5.5])
    bus_data.append([20, "ISLAND-3", 69.0, 1, 3, 3, 1.0, -4.8])

    _write_csv(bus_csv, bus_headers, bus_data)

    # Branch data: chain 1-2-3-...-14, then 14-17, then 18-19-20
    branch_headers = ["I", "J", "CKT", "ST"]
    branch_data: list[list] = []
    for i in range(1, 14):
        branch_data.append([i, i + 1, "1", 1])
    branch_data.append([14, 17, "1", 1])  # VM=0 bus connected
    branch_data.append([18, 19, "1", 1])  # disconnected island
    branch_data.append([19, 20, "1", 1])

    _write_csv(branch_csv, branch_headers, branch_data)

    # Transformer data: 3 in-service 2-winding in main island
    xfmr_headers = ["I", "J", "K", "CKT", "STAT"]
    xfmr_data: list[list] = [
        [1, 2, 0, "1", 1],
        [5, 6, 0, "1", 1],
        [10, 11, 0, "1", 1],
    ]
    _write_csv(xfmr_csv, xfmr_headers, xfmr_data)

    # Build registry
    registry = build_registry(bus_csv, branch_csv, xfmr_csv)

    # Verify summary
    assert registry.summary.total_buses == 20
    assert registry.summary.ide4_count == 2
    # vm_zero_count counts ALL VM=0 buses (may overlap with IDE=4): bus 15 + bus 17
    assert registry.summary.vm_zero_count == 2

    # Disconnected island: 3 buses (18, 19, 20)
    # Total excluded = 2 (IDE=4) + 1 (VM=0) + 3 (disconnected) = 6
    assert registry.summary.excluded_total == 6
    assert registry.summary.remaining_for_verification == 14

    # Connected components: main (15 buses: 1-14 + 17) + island (3 buses: 18-20) = 2
    assert registry.summary.connected_components == 2

    # Verify excluded_buses sorted by bus number
    bus_nums = [r.bus_number for r in registry.excluded_buses]
    assert bus_nums == sorted(bus_nums)
    assert len(registry.excluded_buses) == 6

    # Verify specific records
    excluded_map = {r.bus_number: r for r in registry.excluded_buses}
    assert excluded_map[15].primary_reason == ExclusionReason.IDE_4_ISOLATED
    assert excluded_map[16].primary_reason == ExclusionReason.IDE_4_ISOLATED
    assert excluded_map[17].primary_reason == ExclusionReason.VM_ZERO_DEENERGIZED
    assert excluded_map[18].primary_reason == ExclusionReason.DISCONNECTED_ISLAND
    assert excluded_map[19].primary_reason == ExclusionReason.DISCONNECTED_ISLAND
    assert excluded_map[20].primary_reason == ExclusionReason.DISCONNECTED_ISLAND


# ---------------------------------------------------------------------------
# T10: test_registry_csv_json_roundtrip
# ---------------------------------------------------------------------------


def test_registry_csv_json_roundtrip(tmp_path: Path) -> None:
    """T10: Build a synthetic registry, write CSV+JSON, read back and verify."""
    # Build a small synthetic registry directly
    rec1 = ExcludedBusRecord(
        bus_number=100,
        bus_name="BUS-A",
        area=1,
        zone=10,
        base_kv=230.0,
        primary_reason=ExclusionReason.IDE_4_ISOLATED,
        all_reasons=[ExclusionReason.IDE_4_ISOLATED, ExclusionReason.VM_ZERO_DEENERGIZED],
        island_id=None,
        vm=0.0,
        va=0.0,
        ide=4,
    )
    rec2 = ExcludedBusRecord(
        bus_number=200,
        bus_name="BUS-B",
        area=2,
        zone=20,
        base_kv=115.0,
        primary_reason=ExclusionReason.DISCONNECTED_ISLAND,
        all_reasons=[ExclusionReason.DISCONNECTED_ISLAND],
        island_id=1,
        vm=1.01,
        va=-3.5,
        ide=1,
    )

    island_main = IslandSummary(
        island_id=0,
        bus_count=50,
        is_main=True,
        slack_bus=1,
        sample_buses=[1, 2, 3, 4, 5],
        voltage_levels=[230.0, 115.0],
    )
    island_disc = IslandSummary(
        island_id=1,
        bus_count=5,
        is_main=False,
        slack_bus=None,
        sample_buses=[200, 201, 202],
        voltage_levels=[115.0],
    )

    summary = ExclusionSummary(
        total_buses=57,
        excluded_total=2,
        excluded_by_reason={
            "ide_4_isolated": 1,
            "disconnected_island": 1,
        },
        remaining_for_verification=55,
        connected_components=2,
        main_island_size=50,
        disconnected_island_count=1,
        disconnected_island_sizes=[5],
        islands=[island_main, island_disc],
        ide4_count=1,
        vm_zero_count=1,
        disconnected_count=1,
    )

    metadata = RegistryMetadata(
        bus_csv_path="bus.csv",
        branch_csv_path="branch.csv",
        transformer_csv_path="transformer.csv",
        generated_timestamp="2026-03-06T12:00:00+00:00",
        slack_bus_number=1,
        vm_zero_threshold=0.0,
        graph_node_count=56,
        graph_edge_count=70,
    )

    registry = BusExclusionRegistry(
        excluded_buses=[rec1, rec2],
        summary=summary,
        metadata=metadata,
    )

    # Write CSV and JSON
    csv_path = tmp_path / "excluded_buses.csv"
    json_path = tmp_path / "excluded_buses.json"

    registry_to_csv(registry, csv_path)
    registry_to_json(registry, json_path)

    # Read CSV back
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    assert len(csv_rows) == 2
    assert csv_rows[0]["bus_number"] == "100"
    assert csv_rows[0]["primary_reason"] == "ide_4_isolated"
    assert "vm_zero_deenergized" in csv_rows[0]["all_reasons"]
    assert csv_rows[0]["island_id"] == ""  # None serialized as empty
    assert csv_rows[1]["bus_number"] == "200"
    assert csv_rows[1]["primary_reason"] == "disconnected_island"
    assert csv_rows[1]["island_id"] == "1"

    # Read JSON back
    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    assert "excluded_buses" in json_data
    assert "summary" in json_data
    assert "metadata" in json_data

    assert len(json_data["excluded_buses"]) == 2
    assert json_data["summary"]["excluded_total"] == len(json_data["excluded_buses"])
    assert (
        json_data["summary"]["remaining_for_verification"]
        == json_data["summary"]["total_buses"] - json_data["summary"]["excluded_total"]
    )
