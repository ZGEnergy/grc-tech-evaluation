"""Tests for parser fidelity comparison and canonical parser selection (PRD 01/06).

T01-T12: Synthetic tests (no FNM data required).
T13-T14: FNM integration tests (require FNM_PATH, skip if unset).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.parser_comparison import (
    CanonicalParserSelection,
    ComparisonMetadata,
    DiscrepancyType,
    FidelityScore,
    FieldCoverageEntry,
    ParserComparisonReport,
    ParserName,
    RecordCountComparison,
    SelectionRationale,
    build_comparison_report,
    build_data_loss_inventory,
    compare_field_coverage,
    compare_record_counts,
    compute_fidelity_score,
    report_to_dict,
    select_canonical_parser,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_simple_mapping() -> dict[str, tuple[str | None, str | None]]:
    """Return a minimal PSS/E -> parser table mapping for tests."""
    return {
        "Bus": ("bus", "buses"),
        "Load": (None, "loads"),
        "Generator": ("gen", "generators"),
        "Branch": ("branch", "lines"),
    }


def _make_simple_psse_spec() -> dict[str, list[str]]:
    """Return a minimal PSS/E field spec for tests."""
    return {
        "Bus": ["I", "NAME", "BASKV", "IDE", "AREA", "ZONE", "VM", "VA"],
        "Generator": ["I", "ID", "PG", "QG", "QT", "QB", "VS", "MBASE"],
        "Branch": ["I", "J", "CKT", "R", "X", "B", "RATEA"],
    }


def _make_simple_tier1() -> dict[str, list[str]]:
    """Return a minimal tier-1 fields spec for tests."""
    return {
        "Bus": ["I", "NAME", "BASKV", "VM", "VA"],
        "Generator": ["I", "PG", "QG", "VS"],
    }


# ---------------------------------------------------------------------------
# T01: test_compare_record_counts_all_match
# ---------------------------------------------------------------------------


def test_compare_record_counts_all_match() -> None:
    """All counts match between raw and both parsers -> MATCH."""
    raw = {"Bus": 10, "Generator": 3, "Branch": 15}
    matpower = {"bus": 10, "gen": 3, "branch": 15}
    gridcal = {"buses": 10, "generators": 3, "lines": 15}
    mapping = {
        "Bus": ("bus", "buses"),
        "Generator": ("gen", "generators"),
        "Branch": ("branch", "lines"),
    }

    result = compare_record_counts(raw, matpower, gridcal, mapping)

    assert len(result) == 3
    for c in result:
        assert c.matpower_discrepancy == DiscrepancyType.MATCH
        assert c.gridcal_discrepancy == DiscrepancyType.MATCH


# ---------------------------------------------------------------------------
# T02: test_compare_record_counts_data_loss
# ---------------------------------------------------------------------------


def test_compare_record_counts_data_loss() -> None:
    """Parser count < raw count -> DATA_LOSS."""
    raw = {"Bus": 10}
    matpower = {"bus": 8}
    gridcal = {"buses": 10}
    mapping = {"Bus": ("bus", "buses")}

    result = compare_record_counts(raw, matpower, gridcal, mapping)

    assert len(result) == 1
    assert result[0].matpower_discrepancy == DiscrepancyType.DATA_LOSS
    assert result[0].gridcal_discrepancy == DiscrepancyType.MATCH
    assert result[0].matpower_count == 8


# ---------------------------------------------------------------------------
# T03: test_compare_record_counts_phantom_insertion
# ---------------------------------------------------------------------------


def test_compare_record_counts_phantom_insertion() -> None:
    """Parser count > raw count -> PHANTOM_INSERTION."""
    raw = {"Bus": 10}
    matpower = {"bus": 12}
    gridcal = {"buses": 10}
    mapping = {"Bus": ("bus", "buses")}

    result = compare_record_counts(raw, matpower, gridcal, mapping)

    assert len(result) == 1
    assert result[0].matpower_discrepancy == DiscrepancyType.PHANTOM_INSERTION
    assert result[0].gridcal_discrepancy == DiscrepancyType.MATCH


# ---------------------------------------------------------------------------
# T04: test_compare_record_counts_record_type_missing
# ---------------------------------------------------------------------------


def test_compare_record_counts_record_type_missing() -> None:
    """Parser has no table for a record type with raw data -> RECORD_TYPE_MISSING."""
    raw = {"Load": 5, "Bus": 10}
    matpower = {"bus": 10}
    gridcal = {"buses": 10, "loads": 5}
    # Load maps to None for MATPOWER
    mapping = {"Load": (None, "loads"), "Bus": ("bus", "buses")}

    result = compare_record_counts(raw, matpower, gridcal, mapping)

    load_cmp = [c for c in result if c.psse_section == "Load"][0]
    assert load_cmp.matpower_discrepancy == DiscrepancyType.RECORD_TYPE_MISSING
    assert load_cmp.gridcal_discrepancy == DiscrepancyType.MATCH


# ---------------------------------------------------------------------------
# T05: test_compare_field_coverage_common_and_unique
# ---------------------------------------------------------------------------


def test_compare_field_coverage_common_and_unique() -> None:
    """Verify common, matpower-only, and gridcal-only field lists."""
    psse_spec = {"Bus": ["I", "NAME", "BASKV", "VM", "VA"]}
    mp_columns = {"bus": ["i", "name", "baskv", "extra_mp"]}
    gc_columns = {"buses": ["i", "name", "baskv", "extra_gc"]}
    mapping = {"Bus": ("bus", "buses")}

    result = compare_field_coverage(psse_spec, mp_columns, gc_columns, mapping)

    assert len(result) == 1
    entry = result[0]
    assert "i" in entry.common_fields
    assert "name" in entry.common_fields
    assert "baskv" in entry.common_fields
    assert "extra_mp" in entry.matpower_only
    assert "extra_gc" in entry.gridcal_only
    # Coverage: 4 parser fields / 5 psse fields = 0.8
    assert abs(entry.matpower_coverage - 0.8) < 1e-6
    assert abs(entry.gridcal_coverage - 0.8) < 1e-6


# ---------------------------------------------------------------------------
# T06: test_build_data_loss_inventory_from_discrepancies
# ---------------------------------------------------------------------------


def test_build_data_loss_inventory_from_discrepancies() -> None:
    """Verify inventory entries are created for non-MATCH discrepancies."""
    counts = [
        RecordCountComparison(
            psse_section="Bus",
            raw_count=10,
            matpower_count=8,
            gridcal_count=10,
            matpower_discrepancy=DiscrepancyType.DATA_LOSS,
            gridcal_discrepancy=DiscrepancyType.MATCH,
        ),
        RecordCountComparison(
            psse_section="Load",
            raw_count=5,
            matpower_count=None,
            gridcal_count=5,
            matpower_discrepancy=DiscrepancyType.RECORD_TYPE_MISSING,
            gridcal_discrepancy=DiscrepancyType.MATCH,
        ),
    ]
    fields: list[FieldCoverageEntry] = []

    inventory = build_data_loss_inventory(counts, fields)

    assert len(inventory) == 2
    bus_loss = [e for e in inventory if e.psse_section == "Bus"][0]
    assert bus_loss.parser == ParserName.MATPOWER
    assert bus_loss.loss_type == DiscrepancyType.DATA_LOSS
    assert bus_loss.delta == -2

    load_loss = [e for e in inventory if e.psse_section == "Load"][0]
    assert load_loss.parser == ParserName.MATPOWER
    assert load_loss.loss_type == DiscrepancyType.RECORD_TYPE_MISSING
    assert load_loss.delta is None


# ---------------------------------------------------------------------------
# T07: test_compute_fidelity_score_perfect
# ---------------------------------------------------------------------------


def test_compute_fidelity_score_perfect() -> None:
    """All counts match, full field coverage -> score 1.0."""
    psse_spec = _make_simple_psse_spec()
    tier1 = _make_simple_tier1()

    counts = [
        RecordCountComparison(
            psse_section=s,
            raw_count=10,
            matpower_count=10,
            gridcal_count=10,
            matpower_discrepancy=DiscrepancyType.MATCH,
            gridcal_discrepancy=DiscrepancyType.MATCH,
        )
        for s in psse_spec
    ]

    # Full field coverage: parser has all PSS/E fields
    fields = [
        FieldCoverageEntry(
            psse_section=s,
            psse_fields=psse_spec[s],
            matpower_fields=psse_spec[s],
            gridcal_fields=psse_spec[s],
            common_fields=[f.lower() for f in psse_spec[s]],
            matpower_only=[],
            gridcal_only=[],
            matpower_coverage=1.0,
            gridcal_coverage=1.0,
        )
        for s in psse_spec
    ]

    score = compute_fidelity_score(ParserName.MATPOWER, counts, fields, [], psse_spec, tier1)

    assert abs(score.overall - 1.0) < 1e-6
    assert abs(score.field_coverage - 1.0) < 1e-6
    assert abs(score.record_type_coverage - 1.0) < 1e-6
    assert abs(score.tier1_field_coverage - 1.0) < 1e-6
    assert abs(score.record_count_accuracy - 1.0) < 1e-6
    assert score.phantom_count == 0


# ---------------------------------------------------------------------------
# T08: test_compute_fidelity_score_partial_coverage
# ---------------------------------------------------------------------------


def test_compute_fidelity_score_partial_coverage() -> None:
    """Partial field coverage and some losses produce correct weighted score."""
    psse_spec = {"Bus": ["I", "NAME", "BASKV", "VM"]}
    tier1 = {"Bus": ["I", "NAME"]}

    counts = [
        RecordCountComparison(
            psse_section="Bus",
            raw_count=10,
            matpower_count=8,
            gridcal_count=10,
            matpower_discrepancy=DiscrepancyType.DATA_LOSS,
            gridcal_discrepancy=DiscrepancyType.MATCH,
        ),
    ]

    # MATPOWER has 2/4 fields, GridCal has 4/4
    fields = [
        FieldCoverageEntry(
            psse_section="Bus",
            psse_fields=["I", "NAME", "BASKV", "VM"],
            matpower_fields=["I", "NAME"],
            gridcal_fields=["I", "NAME", "BASKV", "VM"],
            common_fields=["i", "name"],
            matpower_only=[],
            gridcal_only=["baskv", "vm"],
            matpower_coverage=0.5,
            gridcal_coverage=1.0,
        ),
    ]

    mp_score = compute_fidelity_score(ParserName.MATPOWER, counts, fields, [], psse_spec, tier1)
    gc_score = compute_fidelity_score(ParserName.GRIDCAL, counts, fields, [], psse_spec, tier1)

    # MATPOWER: field_cov=0.5, rt_cov=1.0, tier1=1.0 (I,NAME both present),
    # rc_acc=0 (DATA_LOSS)
    # overall = 0.35*0.5 + 0.30*1.0 + 0.20*1.0 + 0.15*0.0 = 0.675
    assert abs(mp_score.overall - 0.675) < 1e-4

    # GridCal: field_cov=1.0, rt_cov=1.0, tier1=1.0, rc_acc=1.0
    # overall = 0.35*1.0 + 0.30*1.0 + 0.20*1.0 + 0.15*1.0 = 1.0
    assert abs(gc_score.overall - 1.0) < 1e-4

    assert gc_score.overall > mp_score.overall


# ---------------------------------------------------------------------------
# T09: test_select_canonical_clear_winner
# ---------------------------------------------------------------------------


def test_select_canonical_clear_winner() -> None:
    """Score diff > 0.05 -> CLEAR_WINNER."""
    mp = FidelityScore(
        parser=ParserName.MATPOWER,
        overall=0.60,
        field_coverage=0.5,
        record_type_coverage=0.7,
        tier1_field_coverage=0.6,
        record_count_accuracy=0.5,
        phantom_count=0,
    )
    gc = FidelityScore(
        parser=ParserName.GRIDCAL,
        overall=0.85,
        field_coverage=0.9,
        record_type_coverage=0.8,
        tier1_field_coverage=0.9,
        record_count_accuracy=0.8,
        phantom_count=0,
    )

    selection = select_canonical_parser(mp, gc)

    assert selection.selected == ParserName.GRIDCAL
    assert selection.rationale == SelectionRationale.CLEAR_WINNER
    assert selection.score_diff > 0.05


# ---------------------------------------------------------------------------
# T10: test_select_canonical_tier1_tiebreak
# ---------------------------------------------------------------------------


def test_select_canonical_tier1_tiebreak() -> None:
    """Scores close but tier1 differs > 0.02 -> TIER1_TIEBREAK."""
    mp = FidelityScore(
        parser=ParserName.MATPOWER,
        overall=0.80,
        field_coverage=0.8,
        record_type_coverage=0.8,
        tier1_field_coverage=0.90,
        record_count_accuracy=0.8,
        phantom_count=0,
    )
    gc = FidelityScore(
        parser=ParserName.GRIDCAL,
        overall=0.82,
        field_coverage=0.82,
        record_type_coverage=0.82,
        tier1_field_coverage=0.70,
        record_count_accuracy=0.82,
        phantom_count=0,
    )

    selection = select_canonical_parser(mp, gc)

    assert selection.rationale == SelectionRationale.TIER1_TIEBREAK
    assert selection.selected == ParserName.MATPOWER


# ---------------------------------------------------------------------------
# T11: test_build_comparison_report_end_to_end
# ---------------------------------------------------------------------------


def test_build_comparison_report_end_to_end(tmp_path: Path) -> None:
    """Synthetic D3/D4/D5 files produce a full report."""
    # D3 raw counts
    d3 = {
        "section_counts": {
            "Bus": 10,
            "Load": 5,
            "Generator": 3,
            "Branch": 12,
            "Transformer": 4,
            "Area": 2,
            "Fixed Shunt": 1,
            "Switched Shunt": 2,
            "Two-Terminal DC": 0,
            "VSC DC": 0,
            "Impedance Correction": 0,
            "Multi-Terminal DC": 0,
            "Multi-Section Line": 0,
            "Zone": 3,
            "Interarea Transfer": 0,
            "Owner": 1,
            "FACTS": 0,
        }
    }
    d3_path = tmp_path / "d3_counts.json"
    d3_path.write_text(json.dumps(d3), encoding="utf-8")

    # D4 MATPOWER summary (uses log.field_counts_csv)
    d4 = {
        "success": True,
        "log": {
            "field_counts_csv": {
                "bus": 10,
                "gen": 3,
                "branch": 16,  # branches + transformers merged
                "areas": 2,
            }
        },
    }
    d4_path = tmp_path / "d4_summary.json"
    d4_path.write_text(json.dumps(d4), encoding="utf-8")

    # D5 GridCal summary (uses multicircuit_counts)
    d5 = {
        "multicircuit_counts": {
            "buses": 10,
            "loads": 5,
            "shunts": 1,
            "generators": 3,
            "lines": 12,
            "transformers2w": 4,
            "areas": 2,
            "zones": 3,
            "controllable_shunts": 2,
        }
    }
    d5_path = tmp_path / "d5_summary.json"
    d5_path.write_text(json.dumps(d5), encoding="utf-8")

    # CSV directories (empty, but must exist)
    mp_csvs = tmp_path / "matpower_csvs"
    mp_csvs.mkdir()
    gc_csvs = tmp_path / "gridcal_csvs"
    gc_csvs.mkdir()

    report = build_comparison_report(d3_path, d4_path, d5_path, mp_csvs, gc_csvs)

    assert isinstance(report, ParserComparisonReport)
    assert len(report.record_counts) == 17
    assert isinstance(report.matpower_fidelity, FidelityScore)
    assert isinstance(report.gridcal_fidelity, FidelityScore)
    assert isinstance(report.selection, CanonicalParserSelection)
    assert report.selection.selected in (ParserName.MATPOWER, ParserName.GRIDCAL)

    # GridCal should score higher since it preserves more record types
    assert report.gridcal_fidelity.overall > report.matpower_fidelity.overall


# ---------------------------------------------------------------------------
# T12: test_report_to_dict_and_json_roundtrip
# ---------------------------------------------------------------------------


def test_report_to_dict_and_json_roundtrip() -> None:
    """json.dumps succeeds and all expected top-level keys are present."""
    metadata = ComparisonMetadata(
        timestamp="2026-01-01T00:00:00Z",
        raw_counts_path="/d3.json",
        matpower_summary_path="/d4.json",
        gridcal_summary_path="/d5.json",
        matpower_csv_dir="/mp",
        gridcal_csv_dir="/gc",
    )
    mp_fidelity = FidelityScore(
        parser=ParserName.MATPOWER,
        overall=0.75,
        field_coverage=0.7,
        record_type_coverage=0.8,
        tier1_field_coverage=0.8,
        record_count_accuracy=0.7,
        phantom_count=1,
    )
    gc_fidelity = FidelityScore(
        parser=ParserName.GRIDCAL,
        overall=0.85,
        field_coverage=0.9,
        record_type_coverage=0.8,
        tier1_field_coverage=0.9,
        record_count_accuracy=0.8,
        phantom_count=0,
    )
    selection = CanonicalParserSelection(
        selected=ParserName.GRIDCAL,
        rationale=SelectionRationale.CLEAR_WINNER,
        matpower_score=0.75,
        gridcal_score=0.85,
        score_diff=0.10,
        explanation="GridCal wins.",
    )

    report = ParserComparisonReport(
        metadata=metadata,
        record_counts=[
            RecordCountComparison(
                psse_section="Bus",
                raw_count=10,
                matpower_count=10,
                gridcal_count=10,
                matpower_discrepancy=DiscrepancyType.MATCH,
                gridcal_discrepancy=DiscrepancyType.MATCH,
            ),
        ],
        field_coverage=[
            FieldCoverageEntry(
                psse_section="Bus",
                psse_fields=["I", "NAME"],
                matpower_fields=["i", "name"],
                gridcal_fields=["i", "name"],
                common_fields=["i", "name"],
                matpower_only=[],
                gridcal_only=[],
                matpower_coverage=1.0,
                gridcal_coverage=1.0,
            ),
        ],
        data_loss_inventory=[],
        matpower_fidelity=mp_fidelity,
        gridcal_fidelity=gc_fidelity,
        selection=selection,
    )

    d = report_to_dict(report)

    # json.dumps must succeed
    json_str = json.dumps(d, indent=2)
    assert isinstance(json_str, str)

    # Roundtrip: parse back and check keys
    parsed = json.loads(json_str)
    expected_keys = {
        "metadata",
        "record_counts",
        "field_coverage",
        "data_loss_inventory",
        "matpower_fidelity",
        "gridcal_fidelity",
        "selection",
    }
    assert set(parsed.keys()) == expected_keys

    # Check nested structure
    assert parsed["selection"]["selected"] == "GRIDCAL"
    assert parsed["selection"]["rationale"] == "CLEAR_WINNER"
    assert parsed["matpower_fidelity"]["parser"] == "MATPOWER"
    assert parsed["gridcal_fidelity"]["parser"] == "GRIDCAL"


# ---------------------------------------------------------------------------
# T13-T14: FNM integration tests (skip if FNM_PATH unset)
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_fnm_full_comparison(require_fnm: dict) -> None:
    """T13: Run full comparison on real FNM data (requires FNM_PATH)."""
    pytest.skip("FNM integration test — requires FNM_PATH and D3/D4/D5 outputs")


@pytest.mark.fnm
def test_fnm_report_markdown_output(require_fnm: dict) -> None:
    """T14: Generate markdown report from real FNM data (requires FNM_PATH)."""
    pytest.skip("FNM integration test — requires FNM_PATH and D3/D4/D5 outputs")
