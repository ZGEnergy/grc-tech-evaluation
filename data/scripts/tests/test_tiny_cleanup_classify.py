"""Tests for tiny_cleanup_classify.py — TINY Snapshot Cleanup & Generator Classification.

Tests use self-contained .m file fixtures for unit tests and the actual
data/networks/case39.m for integration tests (tests 8-11, 14).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.reconcile_bus_gen import parse_matpower_case
from scripts.snapshot_cleanup import (
    CleanupNetworkId,
    CleanupRule,
    FuelCategory,
    apply_generator_cleanup,
    classify_generators,
    compute_bus_modifications,
)
from scripts.tiny_cleanup_classify import (
    CASE39_CLASSIFICATION_TABLE,
    Case39CleanupResult,
    RtsGmlcClass,
    build_case39_classification_table,
    clean_and_classify_case39,
    write_gen_classification_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NETWORKS_DIR = Path(__file__).resolve().parent.parent.parent / "networks"
CASE39_M_FILE = NETWORKS_DIR / "case39.m"

# Expected Pmax values from case39.m
EXPECTED_PMAX = {
    0: 1040.0,
    1: 646.0,
    2: 725.0,
    3: 652.0,
    4: 508.0,
    5: 687.0,
    6: 580.0,
    7: 564.0,
    8: 865.0,
    9: 1100.0,
}

# Expected bus IDs per generator index
EXPECTED_BUS_IDS = {
    0: 30,
    1: 31,
    2: 32,
    3: 33,
    4: 34,
    5: 35,
    6: 36,
    7: 37,
    8: 38,
    9: 39,
}


def _make_gen_data() -> list[tuple[int, float, float]]:
    """Build gen_data from the expected constants (bus_id, pmax, pmin_post_cleanup)."""
    result: list[tuple[int, float, float]] = []
    for i in range(10):
        bus_id = EXPECTED_BUS_IDS[i]
        pmax = EXPECTED_PMAX[i]
        # Only hydro (gen 0) gets nonzero Pmin = 25% of 1040 = 260
        pmin = 260.0 if i == 0 else 0.0
        result.append((bus_id, pmax, pmin))
    return result


# ---------------------------------------------------------------------------
# Test 1: Classification table has 10 entries
# ---------------------------------------------------------------------------


def test_case39_classification_table_has_10_entries() -> None:
    """Verify build_case39_classification_table returns exactly 10 records."""
    gen_data = _make_gen_data()
    table = build_case39_classification_table(gen_data)
    assert len(table) == 10


# ---------------------------------------------------------------------------
# Test 2: Fuel categories
# ---------------------------------------------------------------------------


def test_case39_classification_fuel_categories() -> None:
    """Verify fuel categories match CASE39_FUEL_MAP from Phase 1 D3."""
    gen_data = _make_gen_data()
    table = build_case39_classification_table(gen_data)

    assert table[0].fuel_category == FuelCategory.HYDRO.value
    for i in (1, 2, 5, 7, 8):
        assert table[i].fuel_category == FuelCategory.NUCLEAR.value, f"gen {i}"
    # Gens 3, 4, 6, 9 are mapped to NG in CASE39_FUEL_MAP
    for i in (3, 4, 6, 9):
        assert table[i].fuel_category == FuelCategory.NG.value, f"gen {i}"


# ---------------------------------------------------------------------------
# Test 3: RTS-GMLC classes
# ---------------------------------------------------------------------------


def test_case39_classification_rts_gmlc_classes() -> None:
    """Verify RTS-GMLC technology class assignments."""
    gen_data = _make_gen_data()
    table = build_case39_classification_table(gen_data)

    assert table[0].rts_gmlc_class == RtsGmlcClass.HYDRO_RESERVOIR
    for i in (1, 2, 5, 7, 8):
        assert table[i].rts_gmlc_class == RtsGmlcClass.NUCLEAR, f"gen {i}"
    for i in (3, 4):
        assert table[i].rts_gmlc_class == RtsGmlcClass.COAL_STEAM, f"gen {i}"
    assert table[6].rts_gmlc_class == RtsGmlcClass.GAS_CC
    assert table[9].rts_gmlc_class == RtsGmlcClass.GAS_CC_FLEXIBLE


# ---------------------------------------------------------------------------
# Test 4: Post-cleanup Pmin values
# ---------------------------------------------------------------------------


def test_case39_classification_pmin_values() -> None:
    """Verify post-cleanup Pmin: hydro = 260, all others = 0."""
    gen_data = _make_gen_data()
    table = build_case39_classification_table(gen_data)

    assert table[0].pmin_mw == 260.0
    for i in range(1, 10):
        assert table[i].pmin_mw == 0.0, f"gen {i}"


# ---------------------------------------------------------------------------
# Test 5: Pmax values
# ---------------------------------------------------------------------------


def test_case39_classification_pmax_values() -> None:
    """Verify Pmax values match case39.m."""
    gen_data = _make_gen_data()
    table = build_case39_classification_table(gen_data)

    for i in range(10):
        assert table[i].pmax_mw == EXPECTED_PMAX[i], f"gen {i}"


# ---------------------------------------------------------------------------
# Test 6: Classification source
# ---------------------------------------------------------------------------


def test_case39_classification_source_is_header_map() -> None:
    """Verify all records have classification_source = case39_header_map."""
    gen_data = _make_gen_data()
    table = build_case39_classification_table(gen_data)

    for i, cls in enumerate(table):
        assert cls.classification_source == "case39_header_map", f"gen {i}"


# ---------------------------------------------------------------------------
# Test 7: Rejects wrong gen count
# ---------------------------------------------------------------------------


def test_case39_classification_rejects_wrong_gen_count() -> None:
    """Verify ValueError raised when gen_data length is not 10."""
    with pytest.raises(ValueError, match="exactly 10 generators"):
        build_case39_classification_table(_make_gen_data()[:9])

    with pytest.raises(ValueError, match="exactly 10 generators"):
        build_case39_classification_table(_make_gen_data() + [(99, 100.0, 0.0)])


# ---------------------------------------------------------------------------
# Test 8: Hydro Pmin cleanup (uses actual case39.m)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CASE39_M_FILE.exists(), reason="case39.m not found")
def test_case39_hydro_pmin_cleanup() -> None:
    """Parse actual case39.m, apply cleanup, verify hydro Pmin = 260 MW."""
    case_data = parse_matpower_case(CASE39_M_FILE)
    d3_classifications = classify_generators(case_data, CleanupNetworkId.TINY)
    cleaned_gens, gen_mods = apply_generator_cleanup(case_data, d3_classifications)

    # Gen 0 (bus 30, hydro, Pmax=1040) should have Pmin = 260
    assert cleaned_gens[0].pmin == 260.0

    # Verify a HYDRO_RESERVOIR_PMIN modification record exists
    hydro_pmin_mods = [
        m for m in gen_mods if m.rule == CleanupRule.HYDRO_RESERVOIR_PMIN and m.gen_index == 0
    ]
    assert len(hydro_pmin_mods) == 1
    assert hydro_pmin_mods[0].before_value == 0.0
    assert hydro_pmin_mods[0].after_value == 260.0


# ---------------------------------------------------------------------------
# Test 9: All Pg/Qg cleared (uses actual case39.m)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CASE39_M_FILE.exists(), reason="case39.m not found")
def test_case39_all_pg_qg_cleared() -> None:
    """Parse actual case39.m, apply cleanup, verify all Pg = 0, Qg = 0."""
    case_data = parse_matpower_case(CASE39_M_FILE)
    d3_classifications = classify_generators(case_data, CleanupNetworkId.TINY)
    cleaned_gens, gen_mods = apply_generator_cleanup(case_data, d3_classifications)

    for i, gen in enumerate(cleaned_gens):
        assert gen.pg == 0.0, f"gen {i} Pg != 0"
        assert gen.qg == 0.0, f"gen {i} Qg != 0"

    # All 10 generators have nonzero Pg in source => 10 PG_RESET records
    pg_mods = [m for m in gen_mods if m.rule == CleanupRule.PG_RESET]
    assert len(pg_mods) == 10


# ---------------------------------------------------------------------------
# Test 10: All Vm/Va normalized (uses actual case39.m)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CASE39_M_FILE.exists(), reason="case39.m not found")
def test_case39_all_vm_va_normalized() -> None:
    """Parse actual case39.m, apply bus cleanup, verify all Vm=1.0, Va=0.0.

    Bus 31 is the slack bus with Va=0 but Vm=0.982, so it should have
    a VM_NORMALIZE modification but no VA_NORMALIZE modification.
    """
    case_data = parse_matpower_case(CASE39_M_FILE)
    m_file_text = CASE39_M_FILE.read_text()
    bus_mods = compute_bus_modifications(case_data, m_file_text)

    # All 39 buses should have Vm normalized (all have Vm != 1.0)
    vm_mods = [m for m in bus_mods if m.rule.value == "vm_normalize"]
    assert len(vm_mods) == 39  # All buses have Vm != 1.0

    # 38 buses have Va != 0 (bus 31 has Va = 0)
    va_mods = [m for m in bus_mods if m.rule.value == "va_normalize"]
    assert len(va_mods) == 38  # Bus 31 has Va = 0, no modification

    # Verify bus 31 has no VA_NORMALIZE modification
    bus31_va_mods = [m for m in va_mods if m.bus_id == 31]
    assert len(bus31_va_mods) == 0

    # Verify bus 31 does have a VM_NORMALIZE modification (Vm = 0.982)
    bus31_vm_mods = [m for m in vm_mods if m.bus_id == 31]
    assert len(bus31_vm_mods) == 1
    assert bus31_vm_mods[0].before_value == pytest.approx(0.982)


# ---------------------------------------------------------------------------
# Test 11: Thermal Pmin preserved at zero (uses actual case39.m)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CASE39_M_FILE.exists(), reason="case39.m not found")
def test_case39_thermal_pmin_preserved_at_zero() -> None:
    """Verify all non-hydro generators retain Pmin = 0, no Pmin mods."""
    case_data = parse_matpower_case(CASE39_M_FILE)
    d3_classifications = classify_generators(case_data, CleanupNetworkId.TINY)
    cleaned_gens, gen_mods = apply_generator_cleanup(case_data, d3_classifications)

    for i in range(1, 10):
        assert cleaned_gens[i].pmin == 0.0, f"gen {i}"

    # No Pmin modification records for gens 1-9
    pmin_mods_non_hydro = [m for m in gen_mods if m.field_name == "Pmin" and m.gen_index != 0]
    assert len(pmin_mods_non_hydro) == 0


# ---------------------------------------------------------------------------
# Test 12: CSV columns
# ---------------------------------------------------------------------------


def test_write_gen_classification_csv_columns(tmp_path: Path) -> None:
    """Write classification table to CSV, verify header columns."""
    csv_path = tmp_path / "gen_classification.csv"
    write_gen_classification_csv(CASE39_CLASSIFICATION_TABLE, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == [
            "gen_index",
            "gen_number",
            "bus_id",
            "fuel_category",
            "rts_gmlc_class",
            "pmax_mw",
            "pmin_mw",
            "classification_source",
            "rationale",
        ]


# ---------------------------------------------------------------------------
# Test 13: CSV roundtrip
# ---------------------------------------------------------------------------


def test_write_gen_classification_csv_roundtrip(tmp_path: Path) -> None:
    """Write classification table to CSV, read back, verify all values."""
    csv_path = tmp_path / "gen_classification.csv"
    write_gen_classification_csv(CASE39_CLASSIFICATION_TABLE, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 10

    for i, row in enumerate(rows):
        expected = CASE39_CLASSIFICATION_TABLE[i]
        assert int(row["gen_index"]) == expected.gen_index
        assert int(row["gen_number"]) == expected.gen_number
        assert int(row["bus_id"]) == expected.bus_id
        assert row["fuel_category"] == expected.fuel_category
        assert row["rts_gmlc_class"] == expected.rts_gmlc_class.value
        assert float(row["pmax_mw"]) == expected.pmax_mw
        assert float(row["pmin_mw"]) == expected.pmin_mw
        assert row["classification_source"] == expected.classification_source
        assert row["rationale"] == expected.rationale


# ---------------------------------------------------------------------------
# Test 14: Full pipeline produces all outputs (uses actual case39.m)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CASE39_M_FILE.exists(), reason="case39.m not found")
def test_clean_and_classify_produces_all_outputs(tmp_path: Path) -> None:
    """Call clean_and_classify_case39, verify all 3 output files exist."""
    result = clean_and_classify_case39(NETWORKS_DIR, tmp_path)

    # Verify output files exist
    assert (tmp_path / "case39" / "case39.m").exists()
    assert (tmp_path / "case39" / "gen_classification.csv").exists()
    assert (tmp_path / "case39" / "cleanup_manifest.json").exists()

    # Verify result structure
    assert isinstance(result, Case39CleanupResult)
    assert len(result.classifications) == 10

    # Verify relative paths contain 'case39'
    assert "case39" in result.cleaned_m_file
    assert "case39" in result.gen_classification_csv
    assert "case39" in result.cleanup_manifest_json

    # Verify manifest JSON is valid
    manifest_path = tmp_path / "case39" / "cleanup_manifest.json"
    with open(manifest_path) as fh:
        manifest_data = json.load(fh)
    assert "networks" in manifest_data
    assert len(manifest_data["networks"]) == 1
    assert manifest_data["networks"][0]["network_id"] == "case39"
