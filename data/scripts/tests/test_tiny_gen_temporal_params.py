"""Tests for tiny_gen_temporal_params.py — Generator Temporal Parameter Assignment.

17 unit tests covering reference table loading, classification loading,
ramp rate scaling, flexible multiplier, min times standard/flexible,
nuclear slow ramp, hydro fast ramp, startup cost validation, count
validation, CSV columns, CSV roundtrip, and end-to-end pipeline.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.tiny_cleanup_classify import (
    CASE39_CLASSIFICATION_TABLE,
    RtsGmlcClass,
)
from scripts.tiny_gen_temporal_params import (
    _OUTPUT_COLUMNS,
    FLEXIBLE_MIN_TIME_FRACTION,
    MIN_UP_DOWN_TIME_FLOOR_HR,
    GenTemporalParams,
    RtsGmlcTemplateParams,
    assign_all_temporal_params,
    assign_temporal_params,
    compute_min_times,
    compute_scaled_ramp_rate,
    load_gen_classification,
    load_reference_table,
    validate_all_params,
    validate_gen_params,
    write_gen_temporal_params_csv,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic reference table
# ---------------------------------------------------------------------------

# Realistic template values loosely based on RTS-GMLC medians.
_SYNTHETIC_TEMPLATES: dict[str, RtsGmlcTemplateParams] = {
    "hydro": RtsGmlcTemplateParams(
        tech_class="hydro",
        pmax_template_mw=50.0,
        ramp_rate_mw_per_min=5.0,
        min_up_time_hr=1.0,
        min_down_time_hr=1.0,
        startup_cost_cold_dollar=0.0,
        startup_cost_warm_dollar=0.0,
        startup_cost_hot_dollar=0.0,
    ),
    "nuclear": RtsGmlcTemplateParams(
        tech_class="nuclear",
        pmax_template_mw=400.0,
        ramp_rate_mw_per_min=0.5,
        min_up_time_hr=24.0,
        min_down_time_hr=48.0,
        startup_cost_cold_dollar=20000.0,
        startup_cost_warm_dollar=15000.0,
        startup_cost_hot_dollar=10000.0,
    ),
    "coal_large": RtsGmlcTemplateParams(
        tech_class="coal_large",
        pmax_template_mw=350.0,
        ramp_rate_mw_per_min=1.5,
        min_up_time_hr=8.0,
        min_down_time_hr=8.0,
        startup_cost_cold_dollar=10000.0,
        startup_cost_warm_dollar=7000.0,
        startup_cost_hot_dollar=4000.0,
    ),
    "gas_CC": RtsGmlcTemplateParams(
        tech_class="gas_CC",
        pmax_template_mw=355.0,
        ramp_rate_mw_per_min=4.0,
        min_up_time_hr=4.0,
        min_down_time_hr=4.0,
        startup_cost_cold_dollar=5000.0,
        startup_cost_warm_dollar=3500.0,
        startup_cost_hot_dollar=2000.0,
    ),
}


def _write_reference_csv(tmp_path: Path) -> Path:
    """Write a synthetic reference CSV and return its path."""
    csv_path = tmp_path / "rts_gmlc_tech_classes.csv"
    lines = [
        "# RTS-GMLC Technology Class Reference Table",
        "# Test fixture",
        "#",
    ]
    header = (
        "tech_class,fuel_type,unit_type,capacity_band,"
        "pmax_template_mw,pmin_template_mw,"
        "ramp_rate_mw_per_min,ramp_rate_mw_per_hr,"
        "min_up_time_hr,min_down_time_hr,"
        "startup_time_cold_hr,startup_time_warm_hr,startup_time_hot_hr,"
        "startup_cost_cold_dollar,startup_cost_warm_dollar,startup_cost_hot_dollar,"
        "shutdown_cost_dollar,capacity_band_min_mw,capacity_band_max_mw,generator_count"
    )
    lines.append(header)
    for t in _SYNTHETIC_TEMPLATES.values():
        lines.append(
            f"{t.tech_class},fuel,unit,band,"
            f"{t.pmax_template_mw},{0.0},"
            f"{t.ramp_rate_mw_per_min},{t.ramp_rate_mw_per_min * 60},"
            f"{t.min_up_time_hr},{t.min_down_time_hr},"
            f"0,0,0,"
            f"{t.startup_cost_cold_dollar},{t.startup_cost_warm_dollar},"
            f"{t.startup_cost_hot_dollar},"
            f"0,0,inf,1"
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


@pytest.fixture()
def reference_csv(tmp_path: Path) -> Path:
    """Create a synthetic reference CSV in tmp_path."""
    return _write_reference_csv(tmp_path)


@pytest.fixture()
def templates() -> dict[str, RtsGmlcTemplateParams]:
    """Return the synthetic templates dict directly."""
    return dict(_SYNTHETIC_TEMPLATES)


# ---------------------------------------------------------------------------
# Test 1: Reference table loading
# ---------------------------------------------------------------------------


class TestLoadReferenceTable:
    """Tests for load_reference_table."""

    def test_load_reference_table_returns_all_keys(self, reference_csv: Path) -> None:
        """T1: load_reference_table parses all 4 tech classes from CSV."""
        result = load_reference_table(reference_csv)
        assert set(result.keys()) == {"hydro", "nuclear", "coal_large", "gas_CC"}

    def test_load_reference_table_values_correct(self, reference_csv: Path) -> None:
        """T2: Parsed template values match what was written."""
        result = load_reference_table(reference_csv)
        hydro = result["hydro"]
        assert hydro.pmax_template_mw == 50.0
        assert hydro.ramp_rate_mw_per_min == 5.0
        assert hydro.min_up_time_hr == 1.0

    def test_load_reference_table_missing_file(self, tmp_path: Path) -> None:
        """T3: FileNotFoundError for non-existent CSV."""
        with pytest.raises(FileNotFoundError):
            load_reference_table(tmp_path / "nonexistent.csv")


# ---------------------------------------------------------------------------
# Test 2: Classification loading
# ---------------------------------------------------------------------------


class TestLoadGenClassification:
    """Tests for load_gen_classification."""

    def test_load_from_hardcoded_table(self) -> None:
        """T4: Default (no csv_path) returns the hardcoded 10-gen table."""
        result = load_gen_classification()
        assert len(result) == 10
        assert result[0].bus_id == 30
        assert result[9].rts_gmlc_class == RtsGmlcClass.GAS_CC_FLEXIBLE


# ---------------------------------------------------------------------------
# Test 3: Ramp rate scaling
# ---------------------------------------------------------------------------


class TestComputeScaledRampRate:
    """Tests for compute_scaled_ramp_rate."""

    def test_ramp_rate_linear_scaling(self) -> None:
        """T5: Ramp rate scales linearly with Pmax ratio."""
        # Template: 4.0 MW/min at 355 MW; gen at 710 MW => 8.0 MW/min
        result = compute_scaled_ramp_rate(4.0, 355.0, 710.0)
        assert result == pytest.approx(8.0, rel=1e-6)

    def test_ramp_rate_identity(self) -> None:
        """T6: Same Pmax as template => same ramp rate."""
        result = compute_scaled_ramp_rate(4.0, 355.0, 355.0)
        assert result == pytest.approx(4.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 4: Flexible ramp multiplier
# ---------------------------------------------------------------------------


class TestFlexibleRampMultiplier:
    """Tests for the 1.5x flexible ramp multiplier on GAS_CC_FLEXIBLE."""

    def test_flexible_gen_gets_ramp_multiplier(
        self, templates: dict[str, RtsGmlcTemplateParams]
    ) -> None:
        """T7: Gen 9 (GAS_CC_FLEXIBLE) ramp includes 1.5x multiplier."""
        cls9 = CASE39_CLASSIFICATION_TABLE[9]
        assert cls9.rts_gmlc_class == RtsGmlcClass.GAS_CC_FLEXIBLE

        params = assign_temporal_params(cls9, templates)

        # Expected: template_ramp * (gen_pmax / template_pmax) * 1.5
        gas_cc = templates["gas_CC"]
        expected_ramp = gas_cc.ramp_rate_mw_per_min * (cls9.pmax_mw / gas_cc.pmax_template_mw) * 1.5
        assert params.ramp_rate_mw_per_min == pytest.approx(expected_ramp, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 5: Min times standard vs flexible
# ---------------------------------------------------------------------------


class TestComputeMinTimes:
    """Tests for compute_min_times."""

    def test_standard_min_times(self) -> None:
        """T8: Standard generator gets template times unchanged."""
        up, down = compute_min_times(8.0, 8.0, is_flexible=False)
        assert up == 8.0
        assert down == 8.0

    def test_flexible_min_times_reduced(self) -> None:
        """T9: Flexible gen gets 50% reduction with floor of 1 hour."""
        up, down = compute_min_times(4.0, 4.0, is_flexible=True)
        assert up == pytest.approx(4.0 * FLEXIBLE_MIN_TIME_FRACTION)
        assert down == pytest.approx(4.0 * FLEXIBLE_MIN_TIME_FRACTION)

    def test_flexible_min_times_floor(self) -> None:
        """T10: Floor of 1 hour applied when reduction would go below."""
        up, down = compute_min_times(1.0, 1.0, is_flexible=True)
        # 1.0 * 0.5 = 0.5, but floor is 1.0
        assert up == MIN_UP_DOWN_TIME_FLOOR_HR
        assert down == MIN_UP_DOWN_TIME_FLOOR_HR


# ---------------------------------------------------------------------------
# Test 6: Nuclear slow ramp
# ---------------------------------------------------------------------------


class TestNuclearSlowRamp:
    """Test nuclear generator ramp rate scaling."""

    def test_nuclear_ramp_scaled_slowly(self, templates: dict[str, RtsGmlcTemplateParams]) -> None:
        """T11: Nuclear gen has a slow ramp rate, scaled by capacity."""
        cls1 = CASE39_CLASSIFICATION_TABLE[1]  # Nuclear, bus 31, 646 MW
        assert cls1.rts_gmlc_class == RtsGmlcClass.NUCLEAR

        params = assign_temporal_params(cls1, templates)

        # Nuclear template: 0.5 MW/min at 400 MW => scaled to 646 MW
        expected = 0.5 * (646.0 / 400.0)
        assert params.ramp_rate_mw_per_min == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 7: Hydro fast ramp
# ---------------------------------------------------------------------------


class TestHydroFastRamp:
    """Test hydro generator ramp rate scaling."""

    def test_hydro_ramp_scaled(self, templates: dict[str, RtsGmlcTemplateParams]) -> None:
        """T12: Hydro gen ramp rate scales with capacity (large unit)."""
        cls0 = CASE39_CLASSIFICATION_TABLE[0]  # Hydro, bus 30, 1040 MW
        assert cls0.rts_gmlc_class == RtsGmlcClass.HYDRO_RESERVOIR

        params = assign_temporal_params(cls0, templates)

        # Hydro template: 5.0 MW/min at 50 MW => scaled to 1040 MW
        expected = 5.0 * (1040.0 / 50.0)
        assert params.ramp_rate_mw_per_min == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 8: Startup cost validation
# ---------------------------------------------------------------------------


class TestStartupCostValidation:
    """Tests for startup cost ordering validation."""

    def test_valid_startup_cost_ordering(self) -> None:
        """T13: cold >= warm >= hot passes validation."""
        params = GenTemporalParams(
            gen_uid="test_gen",
            gen_index=0,
            bus_id=30,
            rts_gmlc_class="Hydro",
            tech_class_key="hydro",
            pmax_mw=100.0,
            ramp_rate_mw_per_min=5.0,
            ramp_rate_mw_per_hr=300.0,
            min_up_time_hr=1.0,
            min_down_time_hr=1.0,
            startup_cost_cold_dollar=1000.0,
            startup_cost_warm_dollar=500.0,
            startup_cost_hot_dollar=200.0,
            no_load_cost_dollar_per_hr=0.0,
        )
        errors = validate_gen_params(params)
        assert errors == []

    def test_invalid_startup_cost_ordering(self) -> None:
        """T14: warm > cold fails validation."""
        params = GenTemporalParams(
            gen_uid="bad_gen",
            gen_index=0,
            bus_id=30,
            rts_gmlc_class="Hydro",
            tech_class_key="hydro",
            pmax_mw=100.0,
            ramp_rate_mw_per_min=5.0,
            ramp_rate_mw_per_hr=300.0,
            min_up_time_hr=1.0,
            min_down_time_hr=1.0,
            startup_cost_cold_dollar=100.0,
            startup_cost_warm_dollar=500.0,
            startup_cost_hot_dollar=200.0,
            no_load_cost_dollar_per_hr=0.0,
        )
        errors = validate_gen_params(params)
        assert any("cold startup cost < warm" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 9: Count validation
# ---------------------------------------------------------------------------


class TestCountValidation:
    """Tests for validate_all_params count check."""

    def test_wrong_count_raises_error(self) -> None:
        """T15: validate_all_params flags wrong generator count."""
        params = GenTemporalParams(
            gen_uid="only_one",
            gen_index=0,
            bus_id=30,
            rts_gmlc_class="Hydro",
            tech_class_key="hydro",
            pmax_mw=100.0,
            ramp_rate_mw_per_min=5.0,
            ramp_rate_mw_per_hr=300.0,
            min_up_time_hr=1.0,
            min_down_time_hr=1.0,
            startup_cost_cold_dollar=0.0,
            startup_cost_warm_dollar=0.0,
            startup_cost_hot_dollar=0.0,
            no_load_cost_dollar_per_hr=0.0,
        )
        errors = validate_all_params([params])
        assert any("Expected 10" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 10-11: CSV output
# ---------------------------------------------------------------------------


class TestCsvOutput:
    """Tests for write_gen_temporal_params_csv."""

    def _make_sample_params(self) -> list[GenTemporalParams]:
        """Create a minimal single-gen list for CSV tests."""
        return [
            GenTemporalParams(
                gen_uid="case39_bus30_gen1",
                gen_index=0,
                bus_id=30,
                rts_gmlc_class="Hydro",
                tech_class_key="hydro",
                pmax_mw=1040.0,
                ramp_rate_mw_per_min=104.0,
                ramp_rate_mw_per_hr=6240.0,
                min_up_time_hr=1.0,
                min_down_time_hr=1.0,
                startup_cost_cold_dollar=0.0,
                startup_cost_warm_dollar=0.0,
                startup_cost_hot_dollar=0.0,
                no_load_cost_dollar_per_hr=0.0,
            )
        ]

    def test_csv_columns_match(self, tmp_path: Path) -> None:
        """T16: CSV header columns match _OUTPUT_COLUMNS."""
        csv_path = tmp_path / "test.csv"
        write_gen_temporal_params_csv(self._make_sample_params(), csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == _OUTPUT_COLUMNS

    def test_csv_roundtrip(self, tmp_path: Path) -> None:
        """T17: Values survive CSV write/read roundtrip."""
        csv_path = tmp_path / "roundtrip.csv"
        original = self._make_sample_params()
        write_gen_temporal_params_csv(original, csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        assert row["gen_uid"] == "case39_bus30_gen1"
        assert int(row["gen_index"]) == 0
        assert int(row["bus_id"]) == 30
        assert float(row["pmax_mw"]) == pytest.approx(1040.0)
        assert float(row["ramp_rate_mw_per_min"]) == pytest.approx(104.0)


# ---------------------------------------------------------------------------
# Test 12: End-to-end pipeline
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """Integration test for the full assign_all_temporal_params pipeline."""

    def test_full_pipeline_produces_10_params(
        self, templates: dict[str, RtsGmlcTemplateParams]
    ) -> None:
        """E2E: Pipeline produces valid params for all 10 generators."""
        classifications = load_gen_classification()
        gen_params = assign_all_temporal_params(classifications, templates)

        assert len(gen_params) == 10

        # Every gen has a positive ramp rate.
        for p in gen_params:
            assert p.ramp_rate_mw_per_min > 0
            assert p.ramp_rate_mw_per_hr == pytest.approx(p.ramp_rate_mw_per_min * 60.0)

        # Gen 9 is flexible.
        gen9 = [p for p in gen_params if p.gen_index == 9][0]
        assert gen9.rts_gmlc_class == RtsGmlcClass.GAS_CC_FLEXIBLE.value

        # Nuclear gens have high min up time.
        nuclear_indices = {1, 2, 5, 7, 8}
        for p in gen_params:
            if p.gen_index in nuclear_indices:
                assert p.min_up_time_hr == 24.0

    def test_full_pipeline_csv_write(
        self, templates: dict[str, RtsGmlcTemplateParams], tmp_path: Path
    ) -> None:
        """E2E: Pipeline writes valid CSV with all 10 rows."""
        classifications = load_gen_classification()
        gen_params = assign_all_temporal_params(classifications, templates)

        csv_path = tmp_path / "gen_temporal_params.csv"
        write_gen_temporal_params_csv(gen_params, csv_path)

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 10
        # Rows are sorted by gen_index.
        indices = [int(r["gen_index"]) for r in rows]
        assert indices == list(range(10))
