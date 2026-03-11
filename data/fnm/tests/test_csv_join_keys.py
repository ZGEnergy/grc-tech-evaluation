"""Tests for supplemental CSV join-key mapping (PRD 09).

Tests T01-T07 are synthetic (no FNM data required).
Tests T08-T09 are integration tests with synthetic fixtures.
Test T10 requires actual FNM data (FNM_PATH env var + D7 outputs).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.csv_join_keys import (
    CandidateKey,
    JoinCardinality,
    KeyType,
    analyze_csv,
    build_join_key_report,
    discover_candidate_keys,
    get_default_key_patterns,
    report_to_dict,
    report_to_markdown,
    validate_join,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a minimal CSV file."""
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# T01: discover_candidate_keys — bus number
# ---------------------------------------------------------------------------


def test_discover_candidate_keys_bus_number() -> None:
    """T01: CSV with 'bus_num' column discovers a BUS_NUMBER candidate."""
    columns = ["bus_num", "load_mw", "load_mvar"]
    sample = [
        {"bus_num": "1", "load_mw": "100.0", "load_mvar": "50.0"},
        {"bus_num": "2", "load_mw": "200.0", "load_mvar": "75.0"},
        {"bus_num": "3", "load_mw": "150.0", "load_mvar": "60.0"},
    ]
    patterns = get_default_key_patterns()

    candidates = discover_candidate_keys("test.csv", columns, sample, patterns)

    bus_candidates = [c for c in candidates if c.key_type == KeyType.BUS_NUMBER]
    assert len(bus_candidates) == 1
    assert bus_candidates[0].csv_columns == ["bus_num"]
    assert bus_candidates[0].confidence > 0.5


# ---------------------------------------------------------------------------
# T02: discover_candidate_keys — branch composite
# ---------------------------------------------------------------------------


def test_discover_candidate_keys_branch_composite() -> None:
    """T02: CSV with from_bus/to_bus/ckt discovers a BRANCH_COMPOSITE candidate."""
    columns = ["from_bus", "to_bus", "ckt", "rating_a"]
    sample = [
        {"from_bus": "1", "to_bus": "2", "ckt": "1", "rating_a": "100.0"},
        {"from_bus": "3", "to_bus": "4", "ckt": "1", "rating_a": "200.0"},
    ]
    patterns = get_default_key_patterns()

    candidates = discover_candidate_keys("test.csv", columns, sample, patterns)

    branch_candidates = [c for c in candidates if c.key_type == KeyType.BRANCH_COMPOSITE]
    assert len(branch_candidates) >= 1
    assert branch_candidates[0].csv_columns == ["from_bus", "to_bus", "ckt"]


# ---------------------------------------------------------------------------
# T03: discover_candidate_keys — no match
# ---------------------------------------------------------------------------


def test_discover_candidate_keys_no_match() -> None:
    """T03: CSV with unrelated columns returns no candidates (or only UNKNOWN)."""
    columns = ["timestamp", "value", "category"]
    sample = [
        {"timestamp": "2024-01-01", "value": "42.0", "category": "A"},
    ]
    patterns = get_default_key_patterns()

    candidates = discover_candidate_keys("test.csv", columns, sample, patterns)

    real_candidates = [c for c in candidates if c.key_type != KeyType.UNKNOWN]
    assert len(real_candidates) == 0


# ---------------------------------------------------------------------------
# T04: validate_join — perfect match
# ---------------------------------------------------------------------------


def test_validate_join_perfect_match(tmp_path: Path) -> None:
    """T04: All CSV bus numbers exist in intermediate table => 100% match."""
    # Supplemental CSV
    csv_path = tmp_path / "test.csv"
    _write_csv(csv_path, ["bus_num", "load_mw"], [["1", "100"], ["2", "200"], ["3", "150"]])

    # Intermediate bus table
    inter_dir = tmp_path / "intermediate"
    inter_dir.mkdir()
    _write_csv(
        inter_dir / "bus.csv",
        ["I", "NAME", "BASKV"],
        [
            ["1", "BUS1", "138"],
            ["2", "BUS2", "138"],
            ["3", "BUS3", "230"],
            ["4", "BUS4", "345"],
            ["5", "BUS5", "500"],
        ],
    )

    candidate = CandidateKey(
        csv_file="test.csv",
        csv_columns=["bus_num"],
        key_type=KeyType.BUS_NUMBER,
        confidence=0.9,
    )

    result = validate_join(csv_path, candidate, inter_dir, "bus", ["I"])

    assert result.match_rate == 1.0
    assert result.matched_row_count == 3
    assert result.unmatched_row_count == 0
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# T05: validate_join — partial match
# ---------------------------------------------------------------------------


def test_validate_join_partial_match(tmp_path: Path) -> None:
    """T05: 3 of 5 CSV bus numbers match => 60% match, below threshold."""
    csv_path = tmp_path / "test.csv"
    _write_csv(
        csv_path,
        ["bus_num", "load_mw"],
        [["1", "100"], ["2", "200"], ["3", "150"], ["99", "50"], ["100", "75"]],
    )

    inter_dir = tmp_path / "intermediate"
    inter_dir.mkdir()
    _write_csv(
        inter_dir / "bus.csv",
        ["I", "NAME"],
        [["1", "BUS1"], ["2", "BUS2"], ["3", "BUS3"]],
    )

    candidate = CandidateKey(
        csv_file="test.csv",
        csv_columns=["bus_num"],
        key_type=KeyType.BUS_NUMBER,
        confidence=0.9,
    )

    result = validate_join(csv_path, candidate, inter_dir, "bus", ["I"])

    assert result.match_rate == pytest.approx(0.6)
    assert result.unmatched_row_count == 2
    assert result.is_valid is False
    # Verify unmatched samples contain bus 99 and 100
    unmatched_values = {s["bus_num"] for s in result.unmatched_sample}
    assert "99" in unmatched_values
    assert "100" in unmatched_values


# ---------------------------------------------------------------------------
# T06: validate_join — cardinality N:1
# ---------------------------------------------------------------------------


def test_validate_join_cardinality_n_to_1(tmp_path: Path) -> None:
    """T06: Multiple CSV rows reference same bus => MANY_TO_ONE cardinality."""
    csv_path = tmp_path / "test.csv"
    _write_csv(
        csv_path,
        ["bus_num", "load_mw"],
        [["1", "100"], ["1", "110"], ["1", "120"], ["2", "200"], ["2", "210"]],
    )

    inter_dir = tmp_path / "intermediate"
    inter_dir.mkdir()
    _write_csv(
        inter_dir / "bus.csv",
        ["I", "NAME"],
        [["1", "BUS1"], ["2", "BUS2"]],
    )

    candidate = CandidateKey(
        csv_file="test.csv",
        csv_columns=["bus_num"],
        key_type=KeyType.BUS_NUMBER,
        confidence=0.9,
    )

    result = validate_join(csv_path, candidate, inter_dir, "bus", ["I"])

    assert result.cardinality == JoinCardinality.MANY_TO_ONE


# ---------------------------------------------------------------------------
# T07: analyze_csv — selects primary join
# ---------------------------------------------------------------------------


def test_analyze_csv_selects_primary_join(tmp_path: Path) -> None:
    """T07: CSV with bus_num (100% match) and area (85% match) => bus is primary."""
    csv_path = tmp_path / "test.csv"
    _write_csv(
        csv_path,
        ["bus_num", "area", "load_mw"],
        [
            ["1", "10", "100"],
            ["2", "20", "200"],
            ["3", "30", "150"],
            ["4", "40", "175"],
            ["5", "50", "125"],
            ["6", "60", "110"],
            ["7", "70", "130"],
            ["8", "80", "140"],
            ["9", "90", "160"],
            ["10", "100", "180"],
        ],
    )

    inter_dir = tmp_path / "intermediate"
    inter_dir.mkdir()

    # Bus table: all 10 buses present => 100% match
    _write_csv(
        inter_dir / "bus.csv",
        ["I", "NAME"],
        [[str(i), f"BUS{i}"] for i in range(1, 11)],
    )

    # Area table: only 8 of 10 areas present => some won't match, but we need
    # the area column pattern to match. We'll use areas 10-80 (8 of 10 match = 80%).
    # Actually the threshold is 0.80, so 85% means 8.5 of 10. Let's use
    # 9 out of 10 to get a cleaner 90% that is still below 100%.
    # Wait - we want area to achieve 85%. With 10 rows, we need ~8-9 matches.
    # Let's have areas 10,20,30,40,50,60,70,80 in table (8 match) but not 90,100
    # => 80% match. That's at the threshold. Let's add one more to get 90%.
    # Use 9 matches for 90%, still below bus's 100%.
    _write_csv(
        inter_dir / "area.csv",
        ["I", "ARNAME"],
        [[str(i * 10), f"AREA{i}"] for i in range(1, 10)],  # 10..90 (9 values)
    )

    mapping = analyze_csv(csv_path, inter_dir)

    assert mapping.primary_join is not None
    assert mapping.primary_join.candidate.key_type == KeyType.BUS_NUMBER
    assert mapping.primary_join.match_rate == 1.0

    # Area join should be in secondary_joins
    assert len(mapping.secondary_joins) >= 1
    area_joins = [
        sj for sj in mapping.secondary_joins if sj.candidate.key_type == KeyType.AREA_NUMBER
    ]
    assert len(area_joins) == 1
    assert area_joins[0].match_rate == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# T08: build_report — end to end
# ---------------------------------------------------------------------------


def test_build_report_end_to_end(tmp_path: Path) -> None:
    """T08: Build report with 3 synthetic CSVs and 3 intermediate tables."""
    fnm_dir = tmp_path / "fnm"
    fnm_dir.mkdir()
    inter_dir = tmp_path / "intermediate"
    inter_dir.mkdir()

    # Intermediate tables
    _write_csv(
        inter_dir / "bus.csv",
        ["I", "NAME", "BASKV"],
        [[str(i), f"BUS{i}", "138"] for i in range(1, 11)],
    )
    _write_csv(
        inter_dir / "branch.csv",
        ["I", "J", "CKT", "R"],
        [["1", "2", "1", "0.01"], ["3", "4", "1", "0.02"], ["5", "6", "1", "0.03"]],
    )
    _write_csv(
        inter_dir / "generator.csv",
        ["I", "ID", "NAME", "PG"],
        [["1", "1", "GEN1", "100"], ["2", "1", "GEN2", "200"]],
    )

    # LINE_AND_TRANSFORMER.csv — uses branch composite keys
    _write_csv(
        fnm_dir / "LINE_AND_TRANSFORMER.csv",
        ["from_bus", "to_bus", "ckt", "rating_a", "rating_b"],
        [["1", "2", "1", "100", "120"], ["3", "4", "1", "200", "240"]],
    )

    # TRADING_HUB.csv — uses bus number
    _write_csv(
        fnm_dir / "TRADING_HUB.csv",
        ["hub_name", "bus_num", "factor"],
        [["HUB_A", "1", "0.5"], ["HUB_A", "2", "0.3"], ["HUB_B", "3", "0.8"]],
    )

    # CONTINGENCY.csv — uses branch composite keys
    _write_csv(
        fnm_dir / "CONTINGENCY.csv",
        ["ctg_name", "from_bus", "to_bus", "ckt"],
        [["CTG1", "1", "2", "1"], ["CTG2", "5", "6", "1"]],
    )

    manifest_names = [
        "LINE_AND_TRANSFORMER.csv",
        "TRADING_HUB.csv",
        "GEN_DISTRIBUTION_FACTOR.csv",
        "CONTINGENCY.csv",
        "INTERFACE.csv",
        "INTERFACE_ELEMENT.csv",
        "OUTAGE.csv",
    ]

    report = build_join_key_report(
        fnm_path=fnm_dir,
        intermediate_dir=inter_dir,
        manifest_csv_names=manifest_names,
    )

    assert len(report.csv_mappings) == 3
    assert sorted(report.csvs_found) == sorted(
        [
            "LINE_AND_TRANSFORMER.csv",
            "TRADING_HUB.csv",
            "CONTINGENCY.csv",
        ]
    )
    assert sorted(report.csvs_missing) == sorted(
        [
            "GEN_DISTRIBUTION_FACTOR.csv",
            "INTERFACE.csv",
            "INTERFACE_ELEMENT.csv",
            "OUTAGE.csv",
        ]
    )
    assert report.overall_summary.total_csvs_analyzed == 3


# ---------------------------------------------------------------------------
# T09: report_to_dict and JSON roundtrip
# ---------------------------------------------------------------------------


def test_report_to_dict_and_json_roundtrip(tmp_path: Path) -> None:
    """T09: Convert report to dict, serialize/deserialize JSON, verify structure."""
    fnm_dir = tmp_path / "fnm"
    fnm_dir.mkdir()
    inter_dir = tmp_path / "intermediate"
    inter_dir.mkdir()

    # Minimal intermediate table
    _write_csv(inter_dir / "bus.csv", ["I", "NAME"], [["1", "BUS1"], ["2", "BUS2"]])

    # Minimal CSV
    _write_csv(fnm_dir / "TRADING_HUB.csv", ["hub", "bus_num"], [["H1", "1"], ["H1", "2"]])

    report = build_join_key_report(
        fnm_path=fnm_dir,
        intermediate_dir=inter_dir,
        manifest_csv_names=["TRADING_HUB.csv"],
    )

    d = report_to_dict(report)
    json_str = json.dumps(d, indent=2)
    loaded = json.loads(json_str)

    # Verify all top-level keys
    assert "csv_mappings" in loaded
    assert "csvs_found" in loaded
    assert "csvs_missing" in loaded
    assert "intermediate_tables_used" in loaded
    assert "overall_summary" in loaded
    assert "metadata" in loaded

    # Verify enum values are serialized as strings (not objects)
    for mapping in loaded["csv_mappings"]:
        for candidate in mapping["candidate_keys"]:
            assert isinstance(candidate["key_type"], str)
        for vj in mapping["validated_joins"]:
            assert isinstance(vj["cardinality"], str)


# ---------------------------------------------------------------------------
# T10: FNM integration test (requires FNM_PATH and D7 outputs)
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_fnm_join_key_report_all_csvs_analyzed(require_fnm: dict, tmp_path: Path) -> None:
    """T10: Run with actual FNM data and verify results.

    Requires FNM_PATH env var and D7 intermediate tables.
    """
    fnm_path = Path(require_fnm["fnm_path"])

    # Locate intermediate directory relative to repo root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    intermediate_dir = repo_root / "data" / "fnm" / "intermediate" / "canonical"

    if not intermediate_dir.is_dir():
        pytest.skip(f"Intermediate directory not found: {intermediate_dir}")

    output_dir = tmp_path / "csv_join_keys"
    output_dir.mkdir()

    report = build_join_key_report(
        fnm_path=fnm_path,
        intermediate_dir=intermediate_dir,
    )

    # (a) csvs_found is non-empty
    assert len(report.csvs_found) > 0, "No supplemental CSVs found at FNM_PATH"

    # (b) Every found CSV has at least one CandidateKey
    for mapping in report.csv_mappings:
        assert len(mapping.candidate_keys) > 0, (
            f"{mapping.csv_file} has no candidate keys discovered"
        )

    # (c) At least 5 of 7 CSVs have a valid primary join
    csvs_with_primary = sum(1 for m in report.csv_mappings if m.primary_join is not None)
    assert csvs_with_primary >= 5, (
        f"Only {csvs_with_primary} CSVs have a valid primary join (expected >= 5)"
    )

    # (d) Write report files and verify they are non-empty
    import json as json_mod

    json_path = output_dir / "join_key_report.json"
    json_path.write_text(json_mod.dumps(report_to_dict(report), indent=2) + "\n", encoding="utf-8")
    assert json_path.stat().st_size > 0

    md_path = output_dir / "join_key_report.md"
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    assert md_path.stat().st_size > 0

    # Log summary for manual review
    print("\n--- Join Key Report Summary ---")
    print(f"CSVs found: {report.csvs_found}")
    print(f"CSVs missing: {report.csvs_missing}")
    print(f"CSVs with valid primary join: {csvs_with_primary}")
    print(f"Average match rate: {report.overall_summary.average_match_rate:.1%}")
    print(f"CSVs needing review: {report.overall_summary.csvs_needing_review}")
