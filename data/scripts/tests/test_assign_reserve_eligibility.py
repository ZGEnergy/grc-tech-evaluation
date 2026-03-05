"""Tests for reserve eligibility assignment (PRD 05)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.assign_reserve_eligibility import (
    OUTPUT_CSV_COLUMNS,
    EligibilityNetworkId,
    ReserveEligibilityRow,
    TechClassEligibility,
    assign_eligibility,
    check_adequacy,
    compute_max_non_spinning_mw,
    compute_max_spinning_mw,
    lookup_eligibility,
    process_network,
    write_eligibility_csv,
)
from scripts.assign_temporal_params import TemporalParamRow
from scripts.build_rts_gmlc_reference import FuelType
from scripts.classify_gen_fuel import (
    CapacityBand,
    ClassificationSource,
    ConfidenceLevel,
    GasUnitType,
    GenFuelClassificationRow,
)

# ---------------------------------------------------------------------------
# Helpers to build test fixtures
# ---------------------------------------------------------------------------


def _make_classification(
    gen_uid: str = "test_1_0",
    tech_class: str = "gas_CT_small",
    fuel_type: FuelType = FuelType.GAS,
    pmax_mw: float = 50.0,
    pmin_mw: float = 10.0,
    gas_unit_type: GasUnitType | None = GasUnitType.CT,
    unit_type: str = "CT",
    capacity_band: CapacityBand = CapacityBand.SMALL,
    source: ClassificationSource = ClassificationSource.GENFUEL,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
) -> GenFuelClassificationRow:
    return GenFuelClassificationRow(
        gen_index=0,
        gen_bus=1,
        gen_uid=gen_uid,
        fuel_type=fuel_type,
        gas_unit_type=gas_unit_type,
        unit_type=unit_type,
        capacity_band=capacity_band,
        tech_class=tech_class,
        pmax_mw=pmax_mw,
        pmin_mw=pmin_mw,
        source=source,
        confidence=confidence,
    )


def _make_temporal(
    gen_uid: str = "test_1_0",
    pmax_mw: float = 50.0,
    ramp_rate_mw_per_min: float = 8.0,
    startup_time_hr: float = 0.1,
    tech_class: str = "gas_CT_small",
    fuel_type: str = "gas",
) -> TemporalParamRow:
    return TemporalParamRow(
        gen_uid=gen_uid,
        pmax_mw=pmax_mw,
        pmin_mw=10.0,
        ramp_rate_mw_per_min=ramp_rate_mw_per_min,
        ramp_rate_mw_per_hr=ramp_rate_mw_per_min * 60,
        min_up_time_hr=1.0,
        min_down_time_hr=1.0,
        startup_cost_dollar=1000.0,
        startup_time_hr=startup_time_hr,
        shutdown_cost_dollar=500.0,
        tech_class=tech_class,
        fuel_type=fuel_type,
    )


# ---------------------------------------------------------------------------
# Test 1: lookup_eligibility for known classes
# ---------------------------------------------------------------------------


def test_lookup_eligibility_known_classes() -> None:
    coal = lookup_eligibility("coal_large")
    assert coal.spinning_eligible is True
    assert coal.non_spinning_eligible is False

    gas_ct = lookup_eligibility("gas_CT_small")
    assert gas_ct.spinning_eligible is True
    assert gas_ct.non_spinning_eligible is True

    nuclear = lookup_eligibility("nuclear")
    assert nuclear.spinning_eligible is False
    assert nuclear.non_spinning_eligible is False

    wind = lookup_eligibility("wind")
    assert wind.spinning_eligible is False
    assert wind.non_spinning_eligible is False

    hydro = lookup_eligibility("hydro")
    assert hydro.spinning_eligible is True
    assert hydro.non_spinning_eligible is True

    bess = lookup_eligibility("bess")
    assert bess.spinning_eligible is True
    assert bess.non_spinning_eligible is True


# ---------------------------------------------------------------------------
# Test 2: lookup_eligibility for unknown class
# ---------------------------------------------------------------------------


def test_lookup_eligibility_unknown_class_returns_ineligible() -> None:
    result = lookup_eligibility("geothermal_large")
    assert isinstance(result, TechClassEligibility)
    assert result.spinning_eligible is False
    assert result.non_spinning_eligible is False


# ---------------------------------------------------------------------------
# Test 3: compute_max_spinning_mw ramp-limited
# ---------------------------------------------------------------------------


def test_compute_max_spinning_mw_ramp_limited() -> None:
    result = compute_max_spinning_mw(
        pmax_mw=400.0, ramp_rate_mw_per_min=5.0, spinning_eligible=True
    )
    assert result == 50.0


# ---------------------------------------------------------------------------
# Test 4: compute_max_spinning_mw pmax-limited
# ---------------------------------------------------------------------------


def test_compute_max_spinning_mw_pmax_limited() -> None:
    result = compute_max_spinning_mw(
        pmax_mw=100.0, ramp_rate_mw_per_min=20.0, spinning_eligible=True
    )
    assert result == 100.0


# ---------------------------------------------------------------------------
# Test 5: compute_max_spinning_mw ineligible
# ---------------------------------------------------------------------------


def test_compute_max_spinning_mw_ineligible() -> None:
    result = compute_max_spinning_mw(
        pmax_mw=400.0, ramp_rate_mw_per_min=10.0, spinning_eligible=False
    )
    assert result == 0.0


# ---------------------------------------------------------------------------
# Test 6: compute_max_non_spinning_mw fast start
# ---------------------------------------------------------------------------


def test_compute_max_non_spinning_mw_fast_start() -> None:
    result = compute_max_non_spinning_mw(
        pmax_mw=50.0, startup_time_hr=0.1, non_spinning_eligible=True
    )
    assert result == 50.0


# ---------------------------------------------------------------------------
# Test 7: compute_max_non_spinning_mw slow start
# ---------------------------------------------------------------------------


def test_compute_max_non_spinning_mw_slow_start() -> None:
    result = compute_max_non_spinning_mw(
        pmax_mw=400.0, startup_time_hr=4.0, non_spinning_eligible=True
    )
    assert result == 0.0


# ---------------------------------------------------------------------------
# Test 8: compute_max_non_spinning_mw boundary (exactly 0.5)
# ---------------------------------------------------------------------------


def test_compute_max_non_spinning_mw_boundary() -> None:
    result = compute_max_non_spinning_mw(
        pmax_mw=200.0, startup_time_hr=0.5, non_spinning_eligible=True
    )
    assert result == 200.0


# ---------------------------------------------------------------------------
# Test 9: compute_max_non_spinning_mw ineligible
# ---------------------------------------------------------------------------


def test_compute_max_non_spinning_mw_ineligible() -> None:
    result = compute_max_non_spinning_mw(
        pmax_mw=50.0, startup_time_hr=0.1, non_spinning_eligible=False
    )
    assert result == 0.0


# ---------------------------------------------------------------------------
# Test 10: assign_eligibility for thermal (gas CT)
# ---------------------------------------------------------------------------


def test_assign_eligibility_thermal_generator() -> None:
    cls = _make_classification(
        gen_uid="bus_1_gen_0",
        tech_class="gas_CT_small",
        fuel_type=FuelType.GAS,
        pmax_mw=50.0,
    )
    tp = _make_temporal(
        gen_uid="bus_1_gen_0",
        pmax_mw=50.0,
        ramp_rate_mw_per_min=8.0,
        startup_time_hr=0.1,
    )
    result = assign_eligibility(cls, tp)

    assert result.spinning_eligible is True
    assert result.non_spinning_eligible is True
    # min(50, 8*10=80) = 50
    assert result.max_spinning_mw == 50.0
    # startup 0.1 <= 0.5 -> pmax = 50
    assert result.max_non_spinning_mw == 50.0


# ---------------------------------------------------------------------------
# Test 11: assign_eligibility for nuclear
# ---------------------------------------------------------------------------


def test_assign_eligibility_nuclear_generator() -> None:
    cls = _make_classification(
        gen_uid="bus_5_gen_0",
        tech_class="nuclear",
        fuel_type=FuelType.NUCLEAR,
        pmax_mw=400.0,
        gas_unit_type=None,
        unit_type="NUCLEAR",
    )
    tp = _make_temporal(
        gen_uid="bus_5_gen_0",
        pmax_mw=400.0,
        ramp_rate_mw_per_min=0.0,
        startup_time_hr=24.0,
        tech_class="nuclear",
        fuel_type="nuclear",
    )
    result = assign_eligibility(cls, tp)

    assert result.spinning_eligible is False
    assert result.non_spinning_eligible is False
    assert result.max_spinning_mw == 0.0
    assert result.max_non_spinning_mw == 0.0


# ---------------------------------------------------------------------------
# Test 12: assign_eligibility for renewable (wind)
# ---------------------------------------------------------------------------


def test_assign_eligibility_renewable_generator() -> None:
    cls = _make_classification(
        gen_uid="bus_10_gen_0",
        tech_class="wind",
        fuel_type=FuelType.WIND,
        pmax_mw=200.0,
        gas_unit_type=None,
        unit_type="WIND",
    )
    tp = _make_temporal(
        gen_uid="bus_10_gen_0",
        pmax_mw=200.0,
        ramp_rate_mw_per_min=0.0,
        startup_time_hr=0.0,
        tech_class="wind",
        fuel_type="wind",
    )
    result = assign_eligibility(cls, tp)

    assert result.spinning_eligible is False
    assert result.non_spinning_eligible is False
    assert result.max_spinning_mw == 0.0
    assert result.max_non_spinning_mw == 0.0


# ---------------------------------------------------------------------------
# Test 13: assign_eligibility gen_uid mismatch
# ---------------------------------------------------------------------------


def test_assign_eligibility_gen_uid_mismatch_raises() -> None:
    cls = _make_classification(gen_uid="bus_1_gen_0")
    tp = _make_temporal(gen_uid="bus_2_gen_1")

    with pytest.raises(ValueError, match="gen_uid mismatch"):
        assign_eligibility(cls, tp)


# ---------------------------------------------------------------------------
# Test 14: check_adequacy adequate
# ---------------------------------------------------------------------------


def test_check_adequacy_adequate() -> None:
    rows = [
        ReserveEligibilityRow("g1", "gas_CT_small", "gas", True, True, 100.0, 100.0),
        ReserveEligibilityRow("g2", "coal_large", "coal", True, False, 200.0, 0.0),
        ReserveEligibilityRow("g3", "hydro", "hydro", True, True, 150.0, 150.0),
        ReserveEligibilityRow("g4", "nuclear", "nuclear", False, False, 0.0, 0.0),
        ReserveEligibilityRow("g5", "wind", "wind", False, False, 0.0, 0.0),
    ]
    spin_adeq, _ = check_adequacy(rows, 300.0, 200.0)

    assert spin_adeq.eligible_capacity_mw == 450.0
    assert spin_adeq.eligible_generator_count == 3
    assert spin_adeq.adequacy_ratio == pytest.approx(1.5)
    assert spin_adeq.is_adequate is True


# ---------------------------------------------------------------------------
# Test 15: check_adequacy inadequate
# ---------------------------------------------------------------------------


def test_check_adequacy_inadequate() -> None:
    rows = [
        ReserveEligibilityRow("g1", "gas_CT_small", "gas", True, True, 100.0, 100.0),
        ReserveEligibilityRow("g2", "coal_large", "coal", True, False, 100.0, 0.0),
    ]
    spin_adeq, _ = check_adequacy(rows, 500.0, 200.0)

    assert spin_adeq.is_adequate is False
    assert spin_adeq.adequacy_ratio == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Test 16: write_eligibility_csv format
# ---------------------------------------------------------------------------


def test_write_eligibility_csv_format(tmp_path: Path) -> None:
    rows = [
        ReserveEligibilityRow("g1", "gas_CT_small", "gas", True, True, 50.0, 50.0),
        ReserveEligibilityRow("g2", "coal_large", "coal", True, False, 200.0, 0.0),
        ReserveEligibilityRow("g3", "nuclear", "nuclear", False, False, 0.0, 0.0),
        ReserveEligibilityRow("g4", "wind", "wind", False, False, 0.0, 0.0),
    ]

    dest = tmp_path / "reserve_eligibility.csv"
    write_eligibility_csv(rows, dest)

    text = dest.read_text(encoding="utf-8")
    lines = text.strip().split("\n")

    # (a) Header matches OUTPUT_CSV_COLUMNS
    header = lines[0].split(",")
    assert tuple(header) == OUTPUT_CSV_COLUMNS

    # (b) Exactly 4 data rows
    assert len(lines) == 5  # 1 header + 4 data

    # Parse data rows
    reader = csv.DictReader(lines)
    data_rows = list(reader)
    assert len(data_rows) == 4

    # (c) Boolean columns are "true" or "false"
    for dr in data_rows:
        assert dr["spinning_eligible"] in ("true", "false")
        assert dr["non_spinning_eligible"] in ("true", "false")

    # (d) MW columns parse as floats with 2 decimal places
    for dr in data_rows:
        for col in ("max_spinning_mw", "max_non_spinning_mw"):
            val_str = dr[col]
            float(val_str)  # should not raise
            assert "." in val_str
            decimals = val_str.split(".")[1]
            assert len(decimals) == 2

    # (e) Nuclear and wind rows have 0.00
    nuclear_row = data_rows[2]
    assert nuclear_row["tech_class"] == "nuclear"
    assert nuclear_row["max_spinning_mw"] == "0.00"
    assert nuclear_row["max_non_spinning_mw"] == "0.00"

    wind_row = data_rows[3]
    assert wind_row["tech_class"] == "wind"
    assert wind_row["max_spinning_mw"] == "0.00"
    assert wind_row["max_non_spinning_mw"] == "0.00"


# ---------------------------------------------------------------------------
# Test 17: process_network end-to-end
# ---------------------------------------------------------------------------


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Helper to write a CSV file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_process_network_end_to_end(tmp_path: Path) -> None:
    net_dir = tmp_path / "case39"
    net_dir.mkdir()

    # D2 classification CSV: 5 generators
    d2_header = [
        "gen_index",
        "gen_bus",
        "gen_uid",
        "fuel_type",
        "gas_unit_type",
        "unit_type",
        "capacity_band",
        "tech_class",
        "pmax_mw",
        "pmin_mw",
        "source",
        "confidence",
    ]
    d2_rows = [
        [
            "0",
            "1",
            "g0",
            "coal",
            "",
            "STEAM",
            "large",
            "coal_large",
            "300.0",
            "100.0",
            "genfuel",
            "high",
        ],
        [
            "1",
            "2",
            "g1",
            "gas",
            "CT",
            "CT",
            "small",
            "gas_CT_small",
            "50.0",
            "10.0",
            "genfuel",
            "high",
        ],
        [
            "2",
            "3",
            "g2",
            "nuclear",
            "",
            "NUCLEAR",
            "small",
            "nuclear",
            "400.0",
            "200.0",
            "genfuel",
            "high",
        ],
        ["3", "4", "g3", "wind", "", "WIND", "small", "wind", "200.0", "0.0", "genfuel", "high"],
        ["4", "5", "g4", "hydro", "", "HYDRO", "small", "hydro", "150.0", "0.0", "genfuel", "high"],
    ]
    _write_csv(net_dir / "gen_fuel_classification.csv", d2_header, d2_rows)

    # D3 temporal params CSV: 5 generators (matching D2)
    d3_header = [
        "gen_uid",
        "pmax_mw",
        "pmin_mw",
        "ramp_rate_mw_per_min",
        "ramp_rate_mw_per_hr",
        "min_up_time_hr",
        "min_down_time_hr",
        "startup_cost_dollar",
        "startup_time_hr",
        "shutdown_cost_dollar",
        "tech_class",
        "fuel_type",
    ]
    d3_rows = [
        # coal_large: ramp 3 MW/min -> spin = min(300, 30) = 30; startup 8h > 0.5 -> nonspin 0
        [
            "g0",
            "300.0",
            "100.0",
            "3.0",
            "180.0",
            "8.0",
            "8.0",
            "5000.0",
            "8.0",
            "2000.0",
            "coal_large",
            "coal",
        ],
        # gas_CT: ramp 8 MW/min -> spin = min(50, 80) = 50; startup 0.1 <= 0.5 -> nonspin 50
        [
            "g1",
            "50.0",
            "10.0",
            "8.0",
            "480.0",
            "1.0",
            "1.0",
            "1000.0",
            "0.1",
            "500.0",
            "gas_CT_small",
            "gas",
        ],
        # nuclear: ineligible
        [
            "g2",
            "400.0",
            "200.0",
            "0.0",
            "0.0",
            "24.0",
            "24.0",
            "0.0",
            "24.0",
            "0.0",
            "nuclear",
            "nuclear",
        ],
        # wind: ineligible
        ["g3", "200.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "wind", "wind"],
        # hydro: ramp 10 MW/min -> spin = min(150, 100) = 100; startup 0.05 <= 0.5 -> nonspin 150
        [
            "g4",
            "150.0",
            "0.0",
            "10.0",
            "600.0",
            "0.0",
            "0.0",
            "0.0",
            "0.05",
            "0.0",
            "hydro",
            "hydro",
        ],
    ]
    _write_csv(net_dir / "gen_temporal_params.csv", d3_header, d3_rows)

    # D4 reserve requirements CSV
    hr_cols = [f"HR_{h}" for h in range(1, 25)]
    d4_header = ["Product", *hr_cols, "sizing_basis", "largest_gen_uid", "largest_gen_pmax"]
    spin_row = ["spinning", *["100.00"] * 24, "N-1", "g2", "400.00"]
    nonspin_row = ["non_spinning", *["100.00"] * 24, "N-1", "g2", "400.00"]
    _write_csv(net_dir / "reserve_requirements_24h.csv", d4_header, [spin_row, nonspin_row])

    result = process_network(
        network_id=EligibilityNetworkId.TINY,
        classification_csv_path=net_dir / "gen_fuel_classification.csv",
        temporal_params_csv_path=net_dir / "gen_temporal_params.csv",
        reserve_req_csv_path=net_dir / "reserve_requirements_24h.csv",
        output_dir=net_dir,
    )

    # (a) Counts
    assert result.generator_count == 5
    # spinning: coal(True) + gas_CT(True) + hydro(True) = 3
    assert result.spinning_eligible_count == 3
    # non-spinning: gas_CT(True) + hydro(True) = 2
    assert result.non_spinning_eligible_count == 2

    # (b) Output CSV exists
    output_csv = net_dir / "reserve_eligibility.csv"
    assert output_csv.exists()

    # (c) Read back and verify
    text = output_csv.read_text(encoding="utf-8")
    reader = csv.DictReader(text.strip().split("\n"))
    csv_rows = list(reader)
    assert len(csv_rows) == 5

    # Check specific rows
    coal_row = csv_rows[0]
    assert coal_row["gen_uid"] == "g0"
    assert coal_row["spinning_eligible"] == "true"
    assert coal_row["non_spinning_eligible"] == "false"

    gas_row = csv_rows[1]
    assert gas_row["gen_uid"] == "g1"
    assert gas_row["spinning_eligible"] == "true"
    assert gas_row["non_spinning_eligible"] == "true"

    nuclear_row = csv_rows[2]
    assert nuclear_row["spinning_eligible"] == "false"
    assert nuclear_row["non_spinning_eligible"] == "false"

    # (d) Spinning adequacy: 30 + 50 + 100 = 180 > 100
    assert result.spinning_adequacy.is_adequate is True


# ---------------------------------------------------------------------------
# Test 18: process_network row count mismatch
# ---------------------------------------------------------------------------


def test_process_network_d2_d3_row_count_mismatch_raises(tmp_path: Path) -> None:
    net_dir = tmp_path / "case39"
    net_dir.mkdir()

    # D2 with 5 rows
    d2_header = [
        "gen_index",
        "gen_bus",
        "gen_uid",
        "fuel_type",
        "gas_unit_type",
        "unit_type",
        "capacity_band",
        "tech_class",
        "pmax_mw",
        "pmin_mw",
        "source",
        "confidence",
    ]
    d2_rows = [
        [
            "0",
            "1",
            "g0",
            "coal",
            "",
            "STEAM",
            "large",
            "coal_large",
            "300.0",
            "100.0",
            "genfuel",
            "high",
        ],
        [
            "1",
            "2",
            "g1",
            "gas",
            "CT",
            "CT",
            "small",
            "gas_CT_small",
            "50.0",
            "10.0",
            "genfuel",
            "high",
        ],
        [
            "2",
            "3",
            "g2",
            "nuclear",
            "",
            "NUCLEAR",
            "small",
            "nuclear",
            "400.0",
            "200.0",
            "genfuel",
            "high",
        ],
        ["3", "4", "g3", "wind", "", "WIND", "small", "wind", "200.0", "0.0", "genfuel", "high"],
        ["4", "5", "g4", "hydro", "", "HYDRO", "small", "hydro", "150.0", "0.0", "genfuel", "high"],
    ]
    _write_csv(net_dir / "gen_fuel_classification.csv", d2_header, d2_rows)

    # D3 with only 4 rows (mismatch)
    d3_header = [
        "gen_uid",
        "pmax_mw",
        "pmin_mw",
        "ramp_rate_mw_per_min",
        "ramp_rate_mw_per_hr",
        "min_up_time_hr",
        "min_down_time_hr",
        "startup_cost_dollar",
        "startup_time_hr",
        "shutdown_cost_dollar",
        "tech_class",
        "fuel_type",
    ]
    d3_rows = [
        [
            "g0",
            "300.0",
            "100.0",
            "3.0",
            "180.0",
            "8.0",
            "8.0",
            "5000.0",
            "8.0",
            "2000.0",
            "coal_large",
            "coal",
        ],
        [
            "g1",
            "50.0",
            "10.0",
            "8.0",
            "480.0",
            "1.0",
            "1.0",
            "1000.0",
            "0.1",
            "500.0",
            "gas_CT_small",
            "gas",
        ],
        [
            "g2",
            "400.0",
            "200.0",
            "0.0",
            "0.0",
            "24.0",
            "24.0",
            "0.0",
            "24.0",
            "0.0",
            "nuclear",
            "nuclear",
        ],
        ["g3", "200.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "wind", "wind"],
    ]
    _write_csv(net_dir / "gen_temporal_params.csv", d3_header, d3_rows)

    # D4 (not needed for this test but process_network requires it to exist
    # -- the error should fire before we read D4, but let's provide it anyway)
    hr_cols = [f"HR_{h}" for h in range(1, 25)]
    d4_header = ["Product", *hr_cols, "sizing_basis", "largest_gen_uid", "largest_gen_pmax"]
    _write_csv(
        net_dir / "reserve_requirements_24h.csv",
        d4_header,
        [["spinning", *["100.00"] * 24, "N-1", "g2", "400.00"]],
    )

    with pytest.raises(ValueError, match="Row count mismatch"):
        process_network(
            network_id=EligibilityNetworkId.TINY,
            classification_csv_path=net_dir / "gen_fuel_classification.csv",
            temporal_params_csv_path=net_dir / "gen_temporal_params.csv",
            reserve_req_csv_path=net_dir / "reserve_requirements_24h.csv",
            output_dir=net_dir,
        )
