"""Tests for validate_referential_integrity.py — 18 unit tests for PRD 05/02.

All tests are self-contained with no external file dependencies or network calls.
Synthetic fixtures provide minimal CSV and .m file content for each check.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from scripts.validate_referential_integrity import (
    CheckStatus,
    CsvIdSet,
    MFileIdSets,
    NetworkId,
    check_bess_reserve_linkage,
    check_branch_references,
    check_bus_references,
    check_dr_bus_load,
    check_generator_references,
    check_ids_exist,
    check_reserve_temporal_linkage,
    check_scenario_forecast_alignment,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csv_id_set(
    ids: set[int | str],
    file_path: str = "test.csv",
    id_column: str = "bus_id",
) -> CsvIdSet:
    """Build a CsvIdSet for testing."""
    return CsvIdSet(file_path=file_path, id_column_name=id_column, ids=ids)


def _make_m_ids(
    bus_ids: set[int] | None = None,
    gen_count: int = 0,
    gen_bus_ids: list[int] | None = None,
    branch_count: int = 0,
    bus_pd: dict[int, float] | None = None,
) -> MFileIdSets:
    """Build an MFileIdSets for testing."""
    if bus_ids is None:
        bus_ids = set()
    if gen_bus_ids is None:
        gen_bus_ids = list(range(1, gen_count + 1))
    if bus_pd is None:
        bus_pd = {bid: 100.0 for bid in bus_ids}

    gen_indices = set(range(gen_count))
    branch_indices = set(range(branch_count))
    branch_from = list(range(1, branch_count + 1))
    branch_to = list(range(2, branch_count + 2))

    return MFileIdSets(
        bus_ids=bus_ids,
        gen_indices=gen_indices,
        gen_bus_ids=gen_bus_ids,
        branch_indices=branch_indices,
        branch_from_bus=branch_from,
        branch_to_bus=branch_to,
        bus_pd=bus_pd,
    )


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    """Write a minimal CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [header] + rows
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_m_file(
    path: Path,
    bus_rows: list[str],
    gen_rows: list[str],
    branch_rows: list[str],
) -> None:
    """Write a minimal MATPOWER .m file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    bus_block = ";\n".join(bus_rows)
    gen_block = ";\n".join(gen_rows)
    branch_block = ";\n".join(branch_rows)
    content = textwrap.dedent(f"""\
        function mpc = test_case
        mpc.version = '2';
        mpc.baseMVA = 100;
        mpc.bus = [
        {bus_block};
        ];
        mpc.gen = [
        {gen_block};
        ];
        mpc.branch = [
        {branch_block};
        ];
    """)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1-3: check_ids_exist tests
# ---------------------------------------------------------------------------


def test_check_ids_exist_all_present() -> None:
    """Given source IDs {1,2,3} and target {1,2,3,4,5}, result is PASS."""
    source = _make_csv_id_set({1, 2, 3})
    result = check_ids_exist(
        source=source,
        target_ids={1, 2, 3, 4, 5},
        target_file="target.m",
        check_name="test_check",
        description="test",
    )
    assert result.status == CheckStatus.PASS
    assert result.orphaned_ids == []
    assert result.total_ids_checked == 3


def test_check_ids_exist_orphaned_ids() -> None:
    """Given source IDs {1,2,99} and target {1,2,3}, result is FAIL with orphan 99."""
    source = _make_csv_id_set({1, 2, 99})
    result = check_ids_exist(
        source=source,
        target_ids={1, 2, 3},
        target_file="target.m",
        check_name="test_check",
        description="test",
    )
    assert result.status == CheckStatus.FAIL
    assert len(result.orphaned_ids) == 1
    assert result.orphaned_ids[0].id_value == 99


def test_check_ids_exist_empty_source() -> None:
    """Given empty source and any target, result is PASS with 0 IDs checked."""
    source = _make_csv_id_set(set())
    result = check_ids_exist(
        source=source,
        target_ids={1, 2, 3},
        target_file="target.m",
        check_name="test_check",
        description="test",
    )
    assert result.status == CheckStatus.PASS
    assert result.total_ids_checked == 0


# ---------------------------------------------------------------------------
# 4-6: check_bus_references tests
# ---------------------------------------------------------------------------


def test_check_bus_references_valid_network(tmp_path: Path) -> None:
    """Bus IDs {1,3,5} in load CSV all exist in .m bus table {1,2,3,4,5}."""
    m_ids = _make_m_ids(bus_ids={1, 2, 3, 4, 5})
    csv_path = tmp_path / "load_24h.csv"
    _write_csv(csv_path, "bus_id,HR_1", ["1,100.0", "3,200.0", "5,300.0"])

    results = check_bus_references(m_ids, [(csv_path, "bus_id")], NetworkId.TINY)
    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS


def test_check_bus_references_orphaned_bus(tmp_path: Path) -> None:
    """Bus ID 7 in load CSV does not exist in .m bus table {1,2,3}."""
    m_ids = _make_m_ids(bus_ids={1, 2, 3})
    csv_path = tmp_path / "load_24h.csv"
    _write_csv(csv_path, "bus_id,HR_1", ["1,100.0", "2,200.0", "7,300.0"])

    results = check_bus_references(m_ids, [(csv_path, "bus_id")], NetworkId.TINY)
    assert len(results) == 1
    assert results[0].status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in results[0].orphaned_ids]
    assert 7 in orphan_values


def test_check_bus_references_skips_missing_file(tmp_path: Path) -> None:
    """A nonexistent CSV produces SKIPPED result."""
    m_ids = _make_m_ids(bus_ids={1, 2, 3})
    missing = tmp_path / "nonexistent.csv"

    results = check_bus_references(m_ids, [(missing, "bus_id")], NetworkId.TINY)
    assert len(results) == 1
    assert results[0].status == CheckStatus.SKIPPED
    assert results[0].skip_reason is not None


# ---------------------------------------------------------------------------
# 7-8: check_generator_references tests
# ---------------------------------------------------------------------------


def test_check_generator_references_valid(tmp_path: Path) -> None:
    """Gen UIDs in temporal params CSV match .m gen table."""
    gen_bus_ids = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    m_ids = _make_m_ids(
        bus_ids=set(gen_bus_ids),
        gen_count=10,
        gen_bus_ids=gen_bus_ids,
    )
    csv_path = tmp_path / "gen_temporal_params.csv"
    _write_csv(
        csv_path,
        "gen_uid,pmax",
        [
            f"bus_{gen_bus_ids[0]}_gen_0,100",
            f"bus_{gen_bus_ids[1]}_gen_1,200",
            f"bus_{gen_bus_ids[5]}_gen_5,300",
            f"bus_{gen_bus_ids[9]}_gen_9,400",
        ],
    )

    results = check_generator_references(m_ids, [(csv_path, "gen_uid")], NetworkId.TINY)
    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS


def test_check_generator_references_orphaned_gen(tmp_path: Path) -> None:
    """Gen UID referencing nonexistent gen index 7 when only 0-4 exist."""
    gen_bus_ids = [10, 20, 30, 40, 50]
    m_ids = _make_m_ids(
        bus_ids=set(gen_bus_ids),
        gen_count=5,
        gen_bus_ids=gen_bus_ids,
    )
    csv_path = tmp_path / "reserve_eligibility.csv"
    _write_csv(
        csv_path,
        "gen_uid,spinning_eligible",
        ["bus_999_gen_7,true"],
    )

    results = check_generator_references(m_ids, [(csv_path, "gen_uid")], NetworkId.TINY)
    assert len(results) == 1
    assert results[0].status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in results[0].orphaned_ids]
    assert "bus_999_gen_7" in orphan_values


# ---------------------------------------------------------------------------
# 9-10: check_branch_references tests
# ---------------------------------------------------------------------------


def test_check_branch_references_valid(tmp_path: Path) -> None:
    """Branch indices {2,5,8,14} all exist in .m branch table (0-19)."""
    m_ids = _make_m_ids(branch_count=20)
    csv_path = tmp_path / "flowgates.csv"
    _write_csv(
        csv_path,
        "flowgate_id,line_ids,weights,limit_mw",
        [
            "FG_01,2;5,1.0;1.0,500",
            "FG_02,8;14,0.5;0.5,300",
        ],
    )

    result = check_branch_references(m_ids, csv_path, "line_ids", NetworkId.TINY)
    assert result.status == CheckStatus.PASS


def test_check_branch_references_orphaned_branch(tmp_path: Path) -> None:
    """Branch index 15 does not exist in .m branch table (0-9)."""
    m_ids = _make_m_ids(branch_count=10)
    csv_path = tmp_path / "flowgates.csv"
    _write_csv(
        csv_path,
        "flowgate_id,line_ids,weights,limit_mw",
        ["FG_01,3;15,1.0;1.0,500"],
    )

    result = check_branch_references(m_ids, csv_path, "line_ids", NetworkId.TINY)
    assert result.status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in result.orphaned_ids]
    assert 15 in orphan_values
    # Verify flowgate context is included
    assert any("FG_01" in o.context for o in result.orphaned_ids)


# ---------------------------------------------------------------------------
# 11-12: check_reserve_temporal_linkage tests
# ---------------------------------------------------------------------------


def test_check_reserve_temporal_linkage_valid(tmp_path: Path) -> None:
    """Reserve-eligible generators {0,1,2} all have temporal params entries."""
    reserve_path = tmp_path / "reserve_eligibility.csv"
    _write_csv(
        reserve_path,
        "gen_uid,spinning_eligible,non_spinning_eligible",
        [
            "gen_0,true,false",
            "gen_1,true,false",
            "gen_2,false,true",
        ],
    )
    temporal_path = tmp_path / "gen_temporal_params.csv"
    _write_csv(
        temporal_path,
        "gen_uid,pmax",
        ["gen_0,100", "gen_1,200", "gen_2,300", "gen_3,400", "gen_4,500"],
    )

    result = check_reserve_temporal_linkage(reserve_path, temporal_path, "gen_uid", NetworkId.TINY)
    assert result.status == CheckStatus.PASS


def test_check_reserve_temporal_linkage_missing_entry(tmp_path: Path) -> None:
    """Generator gen_5 is spinning-eligible but has no temporal params entry."""
    reserve_path = tmp_path / "reserve_eligibility.csv"
    _write_csv(
        reserve_path,
        "gen_uid,spinning_eligible,non_spinning_eligible",
        ["gen_5,true,false"],
    )
    temporal_path = tmp_path / "gen_temporal_params.csv"
    _write_csv(
        temporal_path,
        "gen_uid,pmax",
        ["gen_0,100", "gen_1,200", "gen_2,300", "gen_3,400"],
    )

    result = check_reserve_temporal_linkage(reserve_path, temporal_path, "gen_uid", NetworkId.TINY)
    assert result.status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in result.orphaned_ids]
    assert "gen_5" in orphan_values


# ---------------------------------------------------------------------------
# 13-14: check_bess_reserve_linkage tests
# ---------------------------------------------------------------------------


def test_check_bess_reserve_linkage_valid(tmp_path: Path) -> None:
    """BESS_1 and BESS_2 in reserve eligibility both exist in bess_units.csv."""
    reserve_path = tmp_path / "reserve_eligibility.csv"
    _write_csv(
        reserve_path,
        "gen_uid,spinning_eligible,non_spinning_eligible",
        [
            "BESS_1,true,true",
            "BESS_2,true,false",
            "gen_0,true,false",  # non-BESS entry, ignored
        ],
    )
    bess_path = tmp_path / "bess_units.csv"
    _write_csv(
        bess_path,
        "unit_id,bus_id,power_mw,energy_mwh",
        ["BESS_1,10,50,200", "BESS_2,20,100,400", "BESS_3,30,75,300"],
    )

    result = check_bess_reserve_linkage(reserve_path, bess_path, NetworkId.TINY)
    assert result.status == CheckStatus.PASS


def test_check_bess_reserve_linkage_orphaned_unit(tmp_path: Path) -> None:
    """BESS_4 in reserve eligibility does not exist in bess_units.csv."""
    reserve_path = tmp_path / "reserve_eligibility.csv"
    _write_csv(
        reserve_path,
        "gen_uid,spinning_eligible,non_spinning_eligible",
        ["BESS_4,true,true"],
    )
    bess_path = tmp_path / "bess_units.csv"
    _write_csv(
        bess_path,
        "unit_id,bus_id,power_mw,energy_mwh",
        ["BESS_1,10,50,200", "BESS_2,20,100,400"],
    )

    result = check_bess_reserve_linkage(reserve_path, bess_path, NetworkId.TINY)
    assert result.status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in result.orphaned_ids]
    assert "BESS_4" in orphan_values


# ---------------------------------------------------------------------------
# 15-16: check_dr_bus_load tests
# ---------------------------------------------------------------------------


def test_check_dr_bus_load_valid(tmp_path: Path) -> None:
    """DR bus 20 has Pd=680 MW -> PASS."""
    m_ids = _make_m_ids(
        bus_ids={10, 20, 30},
        bus_pd={10: 100.0, 20: 680.0, 30: 50.0},
    )
    dr_path = tmp_path / "dr_buses.csv"
    _write_csv(dr_path, "bus_id,max_curtailment_mw", ["20,50.0"])

    result = check_dr_bus_load(m_ids, dr_path, NetworkId.TINY)
    assert result.status == CheckStatus.PASS


def test_check_dr_bus_load_zero_load_bus(tmp_path: Path) -> None:
    """DR bus 10 has Pd=0 MW -> FAIL (zero-load bus)."""
    m_ids = _make_m_ids(
        bus_ids={10, 20, 30},
        bus_pd={10: 0.0, 20: 680.0, 30: 50.0},
    )
    dr_path = tmp_path / "dr_buses.csv"
    _write_csv(dr_path, "bus_id,max_curtailment_mw", ["10,50.0"])

    result = check_dr_bus_load(m_ids, dr_path, NetworkId.TINY)
    assert result.status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in result.orphaned_ids]
    assert 10 in orphan_values
    assert any("zero load" in o.context for o in result.orphaned_ids)


# ---------------------------------------------------------------------------
# 17-18: check_scenario_forecast_alignment tests
# ---------------------------------------------------------------------------


def test_check_scenario_forecast_alignment_matching(tmp_path: Path) -> None:
    """Scenario gen_uids {G1,G2,G3} match forecast gen_uids {G1,G2,G3}."""
    scenario_path = tmp_path / "scenarios" / "scenario_multipliers_wind_50x24.csv"
    _write_csv(
        scenario_path,
        "gen_uid,scenario,HR_1",
        ["G1,1,0.95", "G2,1,1.05", "G3,1,0.90"],
    )
    forecast_path = tmp_path / "wind_forecast_24h.csv"
    _write_csv(
        forecast_path,
        "gen_uid,HR_1",
        ["G1,100", "G2,200", "G3,300"],
    )

    result = check_scenario_forecast_alignment(
        scenario_path, forecast_path, "gen_uid", "wind", NetworkId.TINY
    )
    assert result.status == CheckStatus.PASS


def test_check_scenario_forecast_alignment_mismatch(tmp_path: Path) -> None:
    """Scenario has G4 not in forecast; forecast has G3 not in scenarios."""
    scenario_path = tmp_path / "scenarios" / "scenario_multipliers_wind_50x24.csv"
    _write_csv(
        scenario_path,
        "gen_uid,scenario,HR_1",
        ["G1,1,0.95", "G2,1,1.05", "G4,1,0.90"],
    )
    forecast_path = tmp_path / "wind_forecast_24h.csv"
    _write_csv(
        forecast_path,
        "gen_uid,HR_1",
        ["G1,100", "G2,200", "G3,300"],
    )

    result = check_scenario_forecast_alignment(
        scenario_path, forecast_path, "gen_uid", "wind", NetworkId.TINY
    )
    assert result.status == CheckStatus.FAIL
    orphan_values = [o.id_value for o in result.orphaned_ids]
    assert "G4" in orphan_values
    # G3 should also appear as in forecast but not scenarios
    assert "G3" in orphan_values
    contexts = [o.context for o in result.orphaned_ids]
    assert any("in scenarios but not in forecast" in c for c in contexts)
    assert any("in forecast but not in scenarios" in c for c in contexts)
