"""Tests for assign_temporal_params.py — Generator Temporal Parameter Assignment.

17 unit tests covering reference table loading, classification loading,
capacity ratio computation, extensive parameter scaling, temporal parameter
assignment for thermal and renewable generators, Pmin computation, validation,
CSV output, and end-to-end network processing.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.assign_temporal_params import (
    OUTPUT_CSV_COLUMNS,
    TemporalNetworkId,
    TemporalParamRow,
    assign_temporal_params,
    compute_pmax_ratio,
    compute_pmin,
    is_renewable,
    load_classification,
    load_reference_table,
    make_renewable_row,
    process_network,
    scale_extensive_param,
    validate_temporal_params,
    write_temporal_params_csv,
)
from scripts.build_rts_gmlc_reference import FuelType, TechClassRow
from scripts.classify_gen_fuel import (
    CapacityBand,
    ClassificationSource,
    ConfidenceLevel,
    GasUnitType,
    GenFuelClassificationRow,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic reference table and classification data
# ---------------------------------------------------------------------------

_REFERENCE_CSV_HEADER = (
    "tech_class,fuel_type,unit_type,capacity_band,"
    "pmax_template_mw,pmin_template_mw,"
    "ramp_rate_mw_per_min,ramp_rate_mw_per_hr,"
    "min_up_time_hr,min_down_time_hr,"
    "startup_time_cold_hr,startup_time_warm_hr,startup_time_hot_hr,"
    "startup_cost_cold_dollar,startup_cost_warm_dollar,startup_cost_hot_dollar,"
    "shutdown_cost_dollar,capacity_band_min_mw,capacity_band_max_mw,generator_count"
)

_REFERENCE_ROWS = [
    "coal_large,coal,STEAM,large,350.0,175.0,1.5,90.0,8.0,8.0,12.0,8.0,4.0,10000.0,7000.0,4000.0,500.0,300.0,inf,3",
    "gas_CT,gas,CT,small,55.0,11.0,4.0,240.0,2.0,2.0,1.0,0.5,0.25,1000.0,700.0,400.0,100.0,0.0,40.0,5",
    "gas_CC,gas,CC,large,355.0,142.0,5.0,300.0,4.0,4.0,2.0,1.0,0.5,5000.0,3500.0,2000.0,200.0,40.0,inf,4",
    "nuclear,nuclear,NUCLEAR,large,400.0,200.0,0.5,30.0,24.0,48.0,48.0,24.0,12.0,20000.0,15000.0,10000.0,1000.0,0.0,inf,2",
    "hydro,hydro,HYDRO,small,50.0,0.0,5.0,300.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,inf,3",
    "wind,wind,WIND,small,100.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,inf,5",
    "solar,solar,PV,small,50.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,inf,3",
]


def _write_reference_csv(tmp_path: Path) -> Path:
    """Write a synthetic reference CSV and return its path."""
    csv_path = tmp_path / "rts_gmlc_tech_classes.csv"
    lines = [
        "# RTS-GMLC Technology Class Reference Table",
        "# Test fixture",
        "#",
        _REFERENCE_CSV_HEADER,
        *_REFERENCE_ROWS,
    ]
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def _make_classification_row(
    gen_uid: str = "test_1_0",
    gen_index: int = 0,
    gen_bus: int = 1,
    fuel_type: FuelType = FuelType.COAL,
    tech_class: str = "coal_large",
    pmax_mw: float = 350.0,
    pmin_mw: float = 0.0,
    gas_unit_type: GasUnitType | None = None,
    unit_type: str = "STEAM",
    capacity_band: CapacityBand = CapacityBand.LARGE,
) -> GenFuelClassificationRow:
    """Create a synthetic classification row."""
    return GenFuelClassificationRow(
        gen_index=gen_index,
        gen_bus=gen_bus,
        gen_uid=gen_uid,
        fuel_type=fuel_type,
        gas_unit_type=gas_unit_type,
        unit_type=unit_type,
        capacity_band=capacity_band,
        tech_class=tech_class,
        pmax_mw=pmax_mw,
        pmin_mw=pmin_mw,
        source=ClassificationSource.GENFUEL,
        confidence=ConfidenceLevel.HIGH,
    )


def _write_classification_csv(dest_path: Path, rows: list[GenFuelClassificationRow]) -> Path:
    """Write classification rows to a CSV for load_classification."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "gen_index,gen_bus,gen_uid,fuel_type,gas_unit_type,unit_type,"
        "capacity_band,tech_class,pmax_mw,pmin_mw,source,confidence"
    )
    lines = [header]
    for r in rows:
        gut = r.gas_unit_type.value if r.gas_unit_type else ""
        lines.append(
            f"{r.gen_index},{r.gen_bus},{r.gen_uid},{r.fuel_type.value},{gut},"
            f"{r.unit_type},{r.capacity_band.value},{r.tech_class},"
            f"{r.pmax_mw},{r.pmin_mw},{r.source.value},{r.confidence.value}"
        )
    dest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest_path


@pytest.fixture()
def reference_csv(tmp_path: Path) -> Path:
    """Create a synthetic reference CSV in tmp_path."""
    return _write_reference_csv(tmp_path)


@pytest.fixture()
def ref_table(reference_csv: Path) -> dict[str, TechClassRow]:
    """Load the synthetic reference table."""
    return load_reference_table(reference_csv)


# ---------------------------------------------------------------------------
# Test 1: test_load_reference_table_indexes_by_tech_class
# ---------------------------------------------------------------------------


def test_load_reference_table_indexes_by_tech_class(reference_csv: Path) -> None:
    """Reference table is indexed by tech_class string with correct keys."""
    result = load_reference_table(reference_csv)
    assert isinstance(result, dict)
    expected_keys = {"coal_large", "gas_CT", "gas_CC", "nuclear", "hydro", "wind", "solar"}
    assert set(result.keys()) == expected_keys
    # Verify one entry
    coal = result["coal_large"]
    assert coal.pmax_template_mw == 350.0
    assert coal.ramp_rate_mw_per_min == 1.5


# ---------------------------------------------------------------------------
# Test 2: test_load_reference_table_skips_comment_lines
# ---------------------------------------------------------------------------


def test_load_reference_table_skips_comment_lines(tmp_path: Path) -> None:
    """Comment lines (starting with #) are skipped during parsing."""
    csv_path = tmp_path / "ref.csv"
    lines = [
        "# This is a comment",
        "# Another comment",
        "# More comments",
        _REFERENCE_CSV_HEADER,
        _REFERENCE_ROWS[0],  # coal_large only
    ]
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = load_reference_table(csv_path)
    assert len(result) == 1
    assert "coal_large" in result


# ---------------------------------------------------------------------------
# Test 3: test_load_classification_returns_all_rows
# ---------------------------------------------------------------------------


def test_load_classification_returns_all_rows(tmp_path: Path) -> None:
    """load_classification returns one row per generator in the CSV."""
    rows = [
        _make_classification_row(gen_uid="g0", gen_index=0, fuel_type=FuelType.COAL),
        _make_classification_row(
            gen_uid="g1",
            gen_index=1,
            fuel_type=FuelType.GAS,
            tech_class="gas_CT",
            unit_type="CT",
            gas_unit_type=GasUnitType.CT,
            capacity_band=CapacityBand.SMALL,
        ),
        _make_classification_row(
            gen_uid="g2",
            gen_index=2,
            fuel_type=FuelType.WIND,
            tech_class="wind",
            unit_type="WIND",
            capacity_band=CapacityBand.SMALL,
        ),
    ]
    csv_path = tmp_path / "gen_fuel_classification.csv"
    _write_classification_csv(csv_path, rows)

    loaded = load_classification(csv_path)
    assert len(loaded) == 3
    assert loaded[0].gen_uid == "g0"
    assert loaded[1].fuel_type == FuelType.GAS
    assert loaded[2].tech_class == "wind"


# ---------------------------------------------------------------------------
# Test 4: test_compute_pmax_ratio_normal
# ---------------------------------------------------------------------------


def test_compute_pmax_ratio_normal() -> None:
    """Capacity ratio is gen_pmax / template_pmax for normal values."""
    assert compute_pmax_ratio(700.0, 350.0) == pytest.approx(2.0)
    assert compute_pmax_ratio(175.0, 350.0) == pytest.approx(0.5)
    assert compute_pmax_ratio(350.0, 350.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test 5: test_compute_pmax_ratio_zero_template
# ---------------------------------------------------------------------------


def test_compute_pmax_ratio_zero_template() -> None:
    """Capacity ratio returns 1.0 when template Pmax is zero (avoids division by zero)."""
    assert compute_pmax_ratio(100.0, 0.0) == 1.0
    assert compute_pmax_ratio(0.0, 0.0) == 1.0


# ---------------------------------------------------------------------------
# Test 6: test_scale_extensive_param
# ---------------------------------------------------------------------------


def test_scale_extensive_param() -> None:
    """Extensive parameters scale linearly with capacity ratio."""
    assert scale_extensive_param(100.0, 2.0) == pytest.approx(200.0)
    assert scale_extensive_param(100.0, 0.5) == pytest.approx(50.0)
    assert scale_extensive_param(0.0, 2.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 7: test_assign_temporal_params_thermal_scaling
# ---------------------------------------------------------------------------


def test_assign_temporal_params_thermal_scaling(ref_table: dict[str, TechClassRow]) -> None:
    """Thermal generator: extensive params scale by ratio, intensive params copied."""
    gen = _make_classification_row(
        gen_uid="thermal_1",
        fuel_type=FuelType.COAL,
        tech_class="coal_large",
        pmax_mw=700.0,  # 2x template (350 MW)
    )
    result = assign_temporal_params(gen, ref_table)
    assert result is not None

    # Capacity ratio should be 2.0
    assert result.pmax_ratio == pytest.approx(2.0)

    # Extensive: ramp_rate_mw_per_min = 1.5 * 2.0 = 3.0
    assert result.ramp_rate_mw_per_min == pytest.approx(3.0)
    # Extensive: ramp_rate_mw_per_hr = 90.0 * 2.0 = 180.0
    assert result.ramp_rate_mw_per_hr == pytest.approx(180.0)
    # Extensive: startup_cost = 10000 * 2.0 = 20000
    assert result.startup_cost_dollar == pytest.approx(20000.0)
    # Extensive: shutdown_cost = 500 * 2.0 = 1000
    assert result.shutdown_cost_dollar == pytest.approx(1000.0)

    # Intensive: copied directly from template
    assert result.min_up_time_hr == 8.0
    assert result.min_down_time_hr == 8.0
    assert result.startup_time_hr == 12.0


# ---------------------------------------------------------------------------
# Test 8: test_assign_temporal_params_renewable_zeroes
# ---------------------------------------------------------------------------


def test_assign_temporal_params_renewable_zeroes(ref_table: dict[str, TechClassRow]) -> None:
    """Renewable generator gets all-zero temporal parameters."""
    gen = _make_classification_row(
        gen_uid="wind_1",
        fuel_type=FuelType.WIND,
        tech_class="wind",
        pmax_mw=150.0,
        unit_type="WIND",
        capacity_band=CapacityBand.SMALL,
    )
    result = assign_temporal_params(gen, ref_table)
    assert result is not None
    assert result.ramp_rate_mw_per_min == 0.0
    assert result.ramp_rate_mw_per_hr == 0.0
    assert result.min_up_time_hr == 0.0
    assert result.min_down_time_hr == 0.0
    assert result.startup_cost_dollar == 0.0
    assert result.startup_time_hr == 0.0
    assert result.shutdown_cost_dollar == 0.0
    assert result.pmin_mw == 0.0


# ---------------------------------------------------------------------------
# Test 9: test_make_renewable_row_all_zeros
# ---------------------------------------------------------------------------


def test_make_renewable_row_all_zeros() -> None:
    """make_renewable_row produces a row with all temporal params set to zero."""
    row = make_renewable_row("solar_1", 50.0, "solar", "solar")
    assert row.pmax_mw == 50.0
    assert row.pmin_mw == 0.0
    assert row.ramp_rate_mw_per_min == 0.0
    assert row.ramp_rate_mw_per_hr == 0.0
    assert row.min_up_time_hr == 0.0
    assert row.min_down_time_hr == 0.0
    assert row.startup_cost_dollar == 0.0
    assert row.startup_time_hr == 0.0
    assert row.shutdown_cost_dollar == 0.0
    assert row.tech_class == "solar"
    assert row.fuel_type == "solar"


# ---------------------------------------------------------------------------
# Test 10: test_is_renewable
# ---------------------------------------------------------------------------


def test_is_renewable() -> None:
    """is_renewable returns True for wind/solar, False for thermal fuels."""
    assert is_renewable("wind") is True
    assert is_renewable("solar") is True
    assert is_renewable("Wind") is True
    assert is_renewable("SOLAR") is True
    assert is_renewable("coal") is False
    assert is_renewable("gas") is False
    assert is_renewable("nuclear") is False
    assert is_renewable("hydro") is False
    assert is_renewable("oil") is False


# ---------------------------------------------------------------------------
# Test 11: test_compute_pmin_preserves_ratio
# ---------------------------------------------------------------------------


def test_compute_pmin_preserves_ratio() -> None:
    """Pmin = (template_pmin / template_pmax) * gen_pmax preserves ratio."""
    # Template: pmin=175, pmax=350 => ratio 0.5. Gen pmax=700 => pmin=350
    assert compute_pmin(700.0, 175.0, 350.0) == pytest.approx(350.0)

    # Template: pmin=0, pmax=50 => ratio 0. Gen pmax=200 => pmin=0
    assert compute_pmin(200.0, 0.0, 50.0) == pytest.approx(0.0)

    # Template pmax=0 => returns 0 (renewable case)
    assert compute_pmin(100.0, 0.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Test 12: test_validate_temporal_params_clean
# ---------------------------------------------------------------------------


def test_validate_temporal_params_clean() -> None:
    """Clean parameters produce no warnings."""
    params = [
        TemporalParamRow(
            gen_uid="clean_1",
            pmax_mw=350.0,
            pmin_mw=100.0,
            ramp_rate_mw_per_min=1.5,
            ramp_rate_mw_per_hr=90.0,
            min_up_time_hr=8.0,
            min_down_time_hr=8.0,
            startup_cost_dollar=10000.0,
            startup_time_hr=12.0,
            shutdown_cost_dollar=500.0,
            tech_class="coal_large",
            fuel_type="coal",
        )
    ]
    warnings = validate_temporal_params(params)
    assert warnings == []


# ---------------------------------------------------------------------------
# Test 13: test_validate_temporal_params_ramp_exceeds_pmax
# ---------------------------------------------------------------------------


def test_validate_temporal_params_ramp_exceeds_pmax() -> None:
    """Ramp rate (MW/hr) exceeding Pmax triggers a warning."""
    params = [
        TemporalParamRow(
            gen_uid="bad_ramp",
            pmax_mw=100.0,
            pmin_mw=20.0,
            ramp_rate_mw_per_min=2.0,
            ramp_rate_mw_per_hr=150.0,  # exceeds pmax of 100
            min_up_time_hr=4.0,
            min_down_time_hr=4.0,
            startup_cost_dollar=1000.0,
            startup_time_hr=2.0,
            shutdown_cost_dollar=100.0,
            tech_class="gas_CT",
            fuel_type="gas",
        )
    ]
    warnings = validate_temporal_params(params)
    assert len(warnings) == 1
    assert warnings[0].parameter == "ramp_rate_mw_per_hr"
    assert "exceeds Pmax" in warnings[0].message


# ---------------------------------------------------------------------------
# Test 14: test_validate_temporal_params_updown_exceeds_24h
# ---------------------------------------------------------------------------


def test_validate_temporal_params_updown_exceeds_24h() -> None:
    """Min up + min down > 24h triggers a warning."""
    params = [
        TemporalParamRow(
            gen_uid="slow_nuc",
            pmax_mw=400.0,
            pmin_mw=200.0,
            ramp_rate_mw_per_min=0.5,
            ramp_rate_mw_per_hr=30.0,
            min_up_time_hr=24.0,
            min_down_time_hr=48.0,  # 24 + 48 = 72 > 24
            startup_cost_dollar=20000.0,
            startup_time_hr=48.0,
            shutdown_cost_dollar=1000.0,
            tech_class="nuclear",
            fuel_type="nuclear",
        )
    ]
    warnings = validate_temporal_params(params)
    updown_warns = [w for w in warnings if "24h" in w.message]
    assert len(updown_warns) == 1


# ---------------------------------------------------------------------------
# Test 15: test_write_temporal_params_csv_columns_and_format
# ---------------------------------------------------------------------------


def test_write_temporal_params_csv_columns_and_format(tmp_path: Path) -> None:
    """CSV output has correct columns in the right order."""
    params = [
        TemporalParamRow(
            gen_uid="gen_1",
            pmax_mw=350.0,
            pmin_mw=175.0,
            ramp_rate_mw_per_min=1.5,
            ramp_rate_mw_per_hr=90.0,
            min_up_time_hr=8.0,
            min_down_time_hr=8.0,
            startup_cost_dollar=10000.0,
            startup_time_hr=12.0,
            shutdown_cost_dollar=500.0,
            tech_class="coal_large",
            fuel_type="coal",
        )
    ]
    csv_path = tmp_path / "test_output.csv"
    write_temporal_params_csv(params, csv_path)

    with open(csv_path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == OUTPUT_CSV_COLUMNS
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["gen_uid"] == "gen_1"
    assert float(row["pmax_mw"]) == pytest.approx(350.0)
    assert float(row["pmin_mw"]) == pytest.approx(175.0)
    assert row["tech_class"] == "coal_large"
    assert row["fuel_type"] == "coal"


# ---------------------------------------------------------------------------
# Test 16: test_process_network_end_to_end
# ---------------------------------------------------------------------------


def test_process_network_end_to_end(tmp_path: Path) -> None:
    """End-to-end: process_network reads classification, assigns params, writes CSV."""
    # Set up reference table
    ref_csv = _write_reference_csv(tmp_path)
    ref_table = load_reference_table(ref_csv)

    # Set up classification CSV
    network_id = TemporalNetworkId.TINY
    classification_dir = tmp_path / "classification"
    network_cls_dir = classification_dir / network_id.value
    network_cls_dir.mkdir(parents=True)

    gens = [
        _make_classification_row(
            gen_uid="case39_1_0",
            gen_index=0,
            gen_bus=1,
            fuel_type=FuelType.COAL,
            tech_class="coal_large",
            pmax_mw=700.0,
            pmin_mw=0.0,
        ),
        _make_classification_row(
            gen_uid="case39_2_1",
            gen_index=1,
            gen_bus=2,
            fuel_type=FuelType.WIND,
            tech_class="wind",
            pmax_mw=100.0,
            pmin_mw=0.0,
            unit_type="WIND",
            capacity_band=CapacityBand.SMALL,
        ),
        _make_classification_row(
            gen_uid="case39_3_2",
            gen_index=2,
            gen_bus=3,
            fuel_type=FuelType.GAS,
            tech_class="gas_CT",
            pmax_mw=55.0,
            pmin_mw=0.0,
            gas_unit_type=GasUnitType.CT,
            unit_type="CT",
            capacity_band=CapacityBand.SMALL,
        ),
    ]
    _write_classification_csv(network_cls_dir / "gen_fuel_classification.csv", gens)

    output_dir = tmp_path / "timeseries"

    result = process_network(
        network_id=network_id,
        classification_dir=classification_dir,
        reference_table=ref_table,
        output_dir=output_dir,
    )

    assert result.generator_count == 3
    assert result.thermal_count == 2  # coal + gas
    assert result.renewable_count == 1  # wind
    assert len(result.temporal_params) == 3

    # Verify output CSV exists
    output_csv = output_dir / network_id.value / "gen_temporal_params.csv"
    assert output_csv.exists()

    # Read it back and verify
    with open(output_csv, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 3

    # Coal generator at 700 MW (2x template): ramp should be scaled
    coal_row = [r for r in rows if r["gen_uid"] == "case39_1_0"][0]
    assert float(coal_row["ramp_rate_mw_per_min"]) == pytest.approx(3.0)

    # Wind generator: all zeros
    wind_row = [r for r in rows if r["gen_uid"] == "case39_2_1"][0]
    assert float(wind_row["ramp_rate_mw_per_min"]) == 0.0
    assert float(wind_row["startup_cost_dollar"]) == 0.0


# ---------------------------------------------------------------------------
# Test 17: test_process_network_missing_tech_class_warns
# ---------------------------------------------------------------------------


def test_process_network_missing_tech_class_warns(tmp_path: Path) -> None:
    """Generator with unknown tech class produces a validation warning."""
    # Reference table without 'oil_CT'
    ref_csv = _write_reference_csv(tmp_path)
    ref_table = load_reference_table(ref_csv)

    network_id = TemporalNetworkId.TINY
    classification_dir = tmp_path / "classification"
    network_cls_dir = classification_dir / network_id.value
    network_cls_dir.mkdir(parents=True)

    gens = [
        _make_classification_row(
            gen_uid="case39_5_0",
            gen_index=0,
            gen_bus=5,
            fuel_type=FuelType.OIL,
            tech_class="oil_CT",  # NOT in reference table
            pmax_mw=20.0,
            pmin_mw=0.0,
            unit_type="CT",
            capacity_band=CapacityBand.SMALL,
        ),
    ]
    _write_classification_csv(network_cls_dir / "gen_fuel_classification.csv", gens)

    output_dir = tmp_path / "timeseries"

    result = process_network(
        network_id=network_id,
        classification_dir=classification_dir,
        reference_table=ref_table,
        output_dir=output_dir,
    )

    # Should have a warning about missing tech class
    assert len(result.validation_warnings) >= 1
    missing_warns = [
        w for w in result.validation_warnings if "not found in reference table" in w.message
    ]
    assert len(missing_warns) == 1
    assert missing_warns[0].gen_uid == "case39_5_0"
