"""Tests for the Evaluation Guide Updates script (PRD 06).

All tests use fixture markdown content rather than actual evaluation guide files.
Selection rationale data is constructed inline to match the D5 JSON structure.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.update_evaluation_guides import (
    EditOperation,
    GuideFileId,
    GuideUpdateContext,
    GuideUpdateResult,
    NetworkTimeSeriesInfo,
    apply_edits,
    build_network_info_from_rationale,
    build_network_info_tiny,
    build_update_context,
    find_marker_line,
    generate_protocol_edits,
    generate_rubric_edits,
    main,
    update_guide,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_RUBRIC_MD = """\
# Phase 1 Evaluation Rubric

## Reference Networks

| Label  | Name         | Buses | Generators |
|--------|--------------|-------|------------|
| TINY   | IEEE 39-bus  | 39    | 10         |
| SMALL  | ACTIVSg 2k  | 2000  | 544        |
| MEDIUM | ACTIVSg 10k | 10000 | 2312       |

## Grading Standards

Each sub-question is scored on a 0-3 scale.
"""

SAMPLE_PROTOCOL_MD = """\
# Phase 1 Test Protocol

## Reference Networks

| Label  | Name         | Buses |
|--------|--------------|-------|
| TINY   | IEEE 39-bus  | 39    |
| SMALL  | ACTIVSg 2k  | 2000  |
| MEDIUM | ACTIVSg 10k | 10000 |

## Data Format Notes

All network data is provided in MATPOWER .m format.

## Suite A — Expressiveness

### A-5: Security-Constrained Unit Commitment (SCUC)

Formulate and solve a 24-hour SCUC problem.

### A-6: Security-Constrained Economic Dispatch (SCED)

Fix the commitment schedule from A-5 and re-dispatch.

### A-8: Stochastic Timeseries Optimization

Solve a stochastic optimization over 24-hour timeseries profiles.

## Suite B — Extensibility

### B-4: Stochastic Scenario Wrapping

Wrap a deterministic solve in a stochastic scenario loop by sampling
load and renewable generation timeseries from a distribution.

## Suite C — Scalability

### C-4: SCUC Scalability

Run A-5 across TINY, SMALL, MEDIUM and measure wall-clock time.

### C-6: Stochastic Scalability

Run stochastic tests across network sizes.
"""


def _make_rationale_dict(
    *,
    selected_date: str = "2016-07-19",
    composite_score: float = 0.8234,
    peak_load_mw: float = 45000.0,
    total_wind_mwh: float = 12000.0,
    total_solar_mwh: float = 8000.0,
) -> dict:
    """Build a mock selection rationale dictionary matching D5 structure."""
    return {
        "network_id": "ACTIVSg2000",
        "selected_date": selected_date,
        "selected_day_index": 200,
        "rank": 1,
        "composite_score": composite_score,
        "score_breakdown": {
            "day_index": 200,
            "date_str": selected_date,
            "composite_score": composite_score,
            "load_level_score": 0.75,
            "wind_score": 0.82,
            "solar_score": 0.68,
            "ramp_score": 0.71,
            "diversity_score": 0.65,
            "weekday_score": 1.0,
            "anomaly_penalty": 0.0,
        },
        "scoring_weights": {
            "load_level": 0.30,
            "wind_generation": 0.20,
            "solar_generation": 0.20,
            "ramp_magnitude": 0.15,
            "renewable_diversity": 0.10,
            "weekday_bonus": 0.05,
        },
        "annual_statistics": {
            "load_mwh_min": 30000.0,
            "load_mwh_mean": 40000.0,
            "load_mwh_max": 55000.0,
        },
        "selected_day_summary": {
            "day_index": 200,
            "date_str": selected_date,
            "total_load_mwh": 42000.0,
            "peak_load_mw": peak_load_mw,
            "total_wind_mwh": total_wind_mwh,
            "total_solar_mwh": total_solar_mwh,
            "peak_wind_mw": 3500.0,
            "peak_solar_mw": 2800.0,
            "max_load_ramp_mw": 1200.0,
            "renewable_penetration": 0.476,
            "missing_hours": 0,
            "is_weekday": True,
        },
        "top_10_candidates": [],
        "total_candidate_days": 365,
        "days_with_anomalies": 3,
        "installed_wind_capacity_mw": 5000.0,
        "installed_solar_capacity_mw": 4000.0,
    }


def _make_context(
    *,
    small_date: str = "2016-07-19",
    medium_date: str = "2016-08-03",
) -> GuideUpdateContext:
    """Build a GuideUpdateContext with realistic data for test use."""
    return GuideUpdateContext(
        networks=[
            build_network_info_tiny(),
            NetworkTimeSeriesInfo(
                network_label="SMALL",
                network_name="ACTIVSg 2k",
                data_dir="data/timeseries/ACTIVSg2000/",
                has_timeseries=True,
                source_description=(
                    "Extracted from ACTIVSg companion data via representative day selection"
                ),
                selected_date=small_date,
                composite_score=0.8234,
                peak_load_mw=45000.0,
                total_wind_mwh=12000.0,
                total_solar_mwh=8000.0,
                available_file_types=["load_24h", "wind_actual_24h", "solar_actual_24h"],
            ),
            NetworkTimeSeriesInfo(
                network_label="MEDIUM",
                network_name="ACTIVSg 10k",
                data_dir="data/timeseries/ACTIVSg10k/",
                has_timeseries=True,
                source_description=(
                    "Extracted from ACTIVSg companion data via representative day selection"
                ),
                selected_date=medium_date,
                composite_score=0.7891,
                peak_load_mw=120000.0,
                total_wind_mwh=35000.0,
                total_solar_mwh=22000.0,
                available_file_types=["load_24h", "wind_actual_24h", "solar_actual_24h"],
            ),
        ],
        schema_doc_relative_path="data/schema/canonical_csv_schema.md",
        schema_json_relative_path="data/schema/canonical_csv_schema.json",
        timeseries_base_dir="data/timeseries/",
        scenario_file_name="scenarios/scenario_multipliers_50x24.csv",
        canonical_csv_version="1.0.0",
        hour_ending_convention="HR_1 through HR_24, hour-ending",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildNetworkInfoTiny:
    def test_build_network_info_tiny_no_rationale(self) -> None:
        """Call build_network_info_tiny and verify TINY network fields."""
        info = build_network_info_tiny()

        assert info.network_label == "TINY"
        assert info.has_timeseries is True
        assert info.selected_date is None
        assert info.composite_score is None
        assert info.peak_load_mw is None
        assert info.total_wind_mwh is None
        assert info.total_solar_mwh is None
        # Source description mentions RTS-GMLC or synthesized
        desc_lower = info.source_description.lower()
        assert "rts-gmlc" in desc_lower or "synthesized" in desc_lower


class TestBuildNetworkInfoFromRationale:
    def test_build_network_info_from_rationale_extracts_date(self) -> None:
        """Construct a mock rationale dict and verify extracted fields."""
        rationale = _make_rationale_dict(
            selected_date="2016-07-19",
            composite_score=0.8234,
            peak_load_mw=45000.0,
            total_wind_mwh=12000.0,
            total_solar_mwh=8000.0,
        )

        info = build_network_info_from_rationale(
            network_label="SMALL",
            network_name="ACTIVSg 2k",
            data_dir="data/timeseries/ACTIVSg2000/",
            rationale=rationale,
            available_files=["load_24h", "wind_actual_24h"],
        )

        assert info.selected_date == "2016-07-19"
        assert info.composite_score == 0.8234
        assert info.peak_load_mw == 45000.0
        assert info.total_wind_mwh == 12000.0
        assert info.total_solar_mwh == 8000.0
        assert info.network_label == "SMALL"
        assert info.has_timeseries is True


class TestBuildUpdateContext:
    def test_build_update_context_three_networks(self, tmp_path: Path) -> None:
        """Call build_update_context with mock repo root and verify 3 networks."""
        # Set up minimal directory structure
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create timeseries directories
        ts_base = repo_root / "data" / "timeseries"
        (ts_base / "case39").mkdir(parents=True)
        (ts_base / "ACTIVSg2000").mkdir(parents=True)
        (ts_base / "ACTIVSg10k").mkdir(parents=True)

        # Write rationale JSONs for SMALL and MEDIUM
        small_rationale = _make_rationale_dict(
            selected_date="2016-07-19",
            composite_score=0.8234,
        )
        (ts_base / "ACTIVSg2000" / "selection_rationale.json").write_text(
            json.dumps(small_rationale)
        )

        medium_rationale = _make_rationale_dict(
            selected_date="2016-08-03",
            composite_score=0.7891,
        )
        medium_rationale["network_id"] = "ACTIVSg10k"
        (ts_base / "ACTIVSg10k" / "selection_rationale.json").write_text(
            json.dumps(medium_rationale)
        )

        context = build_update_context(repo_root)

        assert len(context.networks) == 3
        labels = [n.network_label for n in context.networks]
        assert labels == ["TINY", "SMALL", "MEDIUM"]


class TestGenerateRubricEdits:
    def test_generate_rubric_edits_targets_reference_networks(self) -> None:
        """Verify rubric edits target Reference Networks with TS availability."""
        context = _make_context()
        edits = generate_rubric_edits(context)

        assert len(edits) >= 1
        ref_net_edits = [e for e in edits if "Reference Networks" in e.marker]
        assert len(ref_net_edits) >= 1
        # The new text should mention time series availability
        for edit in ref_net_edits:
            assert "time series" in edit.new_text.lower() or "Time Series" in edit.new_text


class TestGenerateProtocolEdits:
    def test_generate_protocol_edits_includes_timeseries_section(self) -> None:
        """Verify protocol edits include a Time Series Data section after Data Format Notes."""
        context = _make_context()
        edits = generate_protocol_edits(context)

        ts_edits = [
            e for e in edits if e.edit_type == "insert_after" and "Data Format Notes" in e.marker
        ]
        assert len(ts_edits) >= 1
        assert "Time Series Data" in ts_edits[0].new_text

    def test_generate_protocol_edits_updates_a5(self) -> None:
        """Verify protocol edits include A-5 (SCUC) data source references."""
        context = _make_context()
        edits = generate_protocol_edits(context)

        a5_edits = [e for e in edits if "A-5" in e.marker]
        assert len(a5_edits) >= 1
        a5_text = a5_edits[0].new_text
        assert any(
            ref in a5_text
            for ref in ["load_24h.csv", "gen_temporal_params.csv", "data/timeseries/"]
        )

    def test_generate_protocol_edits_updates_a8_stochastic(self) -> None:
        """Verify protocol edits for A-8 distinguish native stochastic vs. provided data."""
        context = _make_context()
        edits = generate_protocol_edits(context)

        a8_edits = [e for e in edits if "A-8" in e.marker]
        assert len(a8_edits) >= 1
        a8_text = a8_edits[0].new_text
        # Should mention forecast/actual pairs for native stochastic
        assert "forecast" in a8_text.lower() or "wind_forecast_24h.csv" in a8_text
        # Should mention scenario multipliers for provided data path
        assert "scenario_multipliers_50x24.csv" in a8_text

    def test_generate_protocol_edits_updates_b4(self) -> None:
        """Verify protocol edits reference scenario multiplier file for B-4."""
        context = _make_context()
        edits = generate_protocol_edits(context)

        b4_edits = [e for e in edits if "B-4" in e.marker]
        assert len(b4_edits) >= 1
        assert "scenario_multipliers_50x24.csv" in b4_edits[0].new_text

    def test_generate_protocol_edits_adds_schema_reference(self) -> None:
        """Verify protocol edits include canonical CSV schema reference."""
        context = _make_context()
        edits = generate_protocol_edits(context)

        schema_edits = [
            e
            for e in edits
            if "canonical_csv_schema.md" in e.new_text or "Canonical CSV Schema" in e.new_text
        ]
        assert len(schema_edits) >= 1


class TestFindMarkerLine:
    def test_find_marker_line_found(self) -> None:
        """Given lines with '### Reference Networks', find the correct index."""
        lines = [
            "# Title",
            "",
            "### Reference Networks",
            "",
            "Some table content",
        ]
        idx = find_marker_line(lines, "Reference Networks")
        assert idx == 2

    def test_find_marker_line_not_found(self) -> None:
        """Marker not in document returns None."""
        lines = ["# Title", "", "Some content"]
        idx = find_marker_line(lines, "Nonexistent Marker")
        assert idx is None


class TestApplyEdits:
    def test_apply_edits_insert_after(self) -> None:
        """Insert text after a known marker line."""
        doc = "# Title\n\n## Marker Line\n\nExisting content."
        edit = EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="Marker Line",
            old_text=None,
            new_text="\nInserted text here.\n",
            description="Test insert",
        )

        updated, applied, skipped = apply_edits(doc, [edit])

        assert applied == 1
        assert len(skipped) == 0
        # The inserted text should appear right after the marker
        assert "Inserted text here." in updated
        # The marker should still be present
        assert "## Marker Line" in updated
        # Existing content should still be present
        assert "Existing content." in updated

    def test_apply_edits_replace_block(self) -> None:
        """Replace a known multi-line block."""
        doc = "Line 1\nOld block start\nOld block middle\nOld block end\nLine 5"
        edit = EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="replace_block",
            marker="",
            old_text="Old block start\nOld block middle\nOld block end",
            new_text="New replacement text",
            description="Test replace",
        )

        updated, applied, skipped = apply_edits(doc, [edit])

        assert applied == 1
        assert len(skipped) == 0
        assert "Old block start" not in updated
        assert "New replacement text" in updated
        assert "Line 1" in updated
        assert "Line 5" in updated

    def test_apply_edits_skips_missing_marker(self) -> None:
        """Edit with nonexistent marker is skipped."""
        doc = "# Title\n\nSome content."
        edit = EditOperation(
            guide=GuideFileId.PROTOCOL,
            edit_type="insert_after",
            marker="Nonexistent Marker",
            old_text=None,
            new_text="Should not appear",
            description="Skipped edit description",
        )

        updated, applied, skipped = apply_edits(doc, [edit])

        assert applied == 0
        assert "Skipped edit description" in skipped
        assert updated == doc


class TestUpdateGuide:
    def test_update_guide_writes_output_file(self, tmp_path: Path) -> None:
        """Create a temp guide, apply an edit, verify output and original unchanged."""
        guide_path = tmp_path / "guide.md"
        guide_path.write_text("# Title\n\n## Marker\n\nOriginal content.\n")

        output_path = tmp_path / "output" / "guide.md"

        edit = EditOperation(
            guide=GuideFileId.RUBRIC,
            edit_type="insert_after",
            marker="## Marker",
            old_text=None,
            new_text="\nAdded by test.\n",
            description="Test insert for update_guide",
        )

        result = update_guide(GuideFileId.RUBRIC, guide_path, [edit], output_path)

        assert isinstance(result, GuideUpdateResult)
        assert result.edits_applied == 1
        assert result.edits_skipped == 0
        assert output_path.exists()
        assert "Added by test." in output_path.read_text()
        # Original should be unchanged
        assert "Added by test." not in guide_path.read_text()


class TestMain:
    def test_main_produces_two_results(self, tmp_path: Path) -> None:
        """Call main with mock repo root and verify 2 GuideUpdateResult objects."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create evaluation guide files
        guides_dir = repo_root / "evaluation_guides"
        guides_dir.mkdir()
        (guides_dir / "Phase1_Evaluation_Rubric_v1.md").write_text(SAMPLE_RUBRIC_MD)
        (guides_dir / "Phase1_Test_Protocol_v2.md").write_text(SAMPLE_PROTOCOL_MD)

        # Create timeseries directories with rationale JSONs
        ts_base = repo_root / "data" / "timeseries"
        (ts_base / "case39").mkdir(parents=True)
        (ts_base / "ACTIVSg2000").mkdir(parents=True)
        (ts_base / "ACTIVSg10k").mkdir(parents=True)

        small_rationale = _make_rationale_dict(selected_date="2016-07-19")
        (ts_base / "ACTIVSg2000" / "selection_rationale.json").write_text(
            json.dumps(small_rationale)
        )

        medium_rationale = _make_rationale_dict(selected_date="2016-08-03")
        medium_rationale["network_id"] = "ACTIVSg10k"
        (ts_base / "ACTIVSg10k" / "selection_rationale.json").write_text(
            json.dumps(medium_rationale)
        )

        # Write to a separate output dir so we don't overwrite fixtures
        output_dir = tmp_path / "output"
        results = main(repo_root, output_dir=output_dir)

        assert len(results) == 2
        assert all(isinstance(r, GuideUpdateResult) for r in results)

        guide_ids = {r.guide for r in results}
        assert GuideFileId.RUBRIC in guide_ids
        assert GuideFileId.PROTOCOL in guide_ids

        # Verify edits were applied (at least some)
        for r in results:
            assert r.edits_applied > 0
