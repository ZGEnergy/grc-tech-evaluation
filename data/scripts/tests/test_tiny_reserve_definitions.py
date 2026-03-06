"""Tests for tiny_reserve_definitions.py (PRD 2b/05).

Sixteen unit tests covering reserve requirements, ramp-based eligibility,
nuclear caps, feasibility checks, and CSV output formatting.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from scripts.tiny_cleanup_classify import (
    Case39GenClassification,
    RtsGmlcClass,
)
from scripts.tiny_gen_temporal_params import GenTemporalParams, build_gen_uid
from scripts.tiny_reserve_definitions import (
    LARGEST_GEN_PMAX_MW,
    NON_SPINNING_DEPLOYMENT_MINUTES,
    NON_SPINNING_REQUIREMENT_MW,
    NUCLEAR_MAX_NON_SPINNING_PCT,
    NUCLEAR_MAX_SPINNING_PCT,
    SPINNING_DEPLOYMENT_MINUTES,
    SPINNING_REQUIREMENT_MW,
    ReserveProduct,
    build_reserve_requirements,
    compute_all_eligibilities,
    compute_generator_eligibility,
    compute_ramp_based_reserve_pct,
    define_reserves,
    validate_reserve_feasibility,
    write_reserve_eligibility_csv,
    write_reserve_requirements_csv,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_classification(
    gen_index: int = 0,
    bus_id: int = 30,
    fuel_category: str = "hydro",
    rts_gmlc_class: RtsGmlcClass = RtsGmlcClass.HYDRO_RESERVOIR,
    pmax_mw: float = 1040.0,
) -> Case39GenClassification:
    """Build a minimal Case39GenClassification for testing."""
    return Case39GenClassification(
        gen_index=gen_index,
        gen_number=gen_index + 1,
        bus_id=bus_id,
        fuel_category=fuel_category,
        rts_gmlc_class=rts_gmlc_class,
        pmax_mw=pmax_mw,
        pmin_mw=0.0,
        classification_source="test",
        rationale="test fixture",
    )


def _make_temporal_params(
    gen_index: int = 0,
    bus_id: int = 30,
    pmax_mw: float = 1040.0,
    ramp_rate_mw_per_hr: float = 600.0,
    rts_gmlc_class: str = "Hydro",
) -> GenTemporalParams:
    """Build a minimal GenTemporalParams for testing."""
    gen_uid = build_gen_uid(bus_id, gen_index + 1)
    return GenTemporalParams(
        gen_uid=gen_uid,
        gen_index=gen_index,
        bus_id=bus_id,
        rts_gmlc_class=rts_gmlc_class,
        tech_class_key="hydro",
        pmax_mw=pmax_mw,
        ramp_rate_mw_per_min=ramp_rate_mw_per_hr / 60.0,
        ramp_rate_mw_per_hr=ramp_rate_mw_per_hr,
        min_up_time_hr=1.0,
        min_down_time_hr=1.0,
        startup_cost_cold_dollar=0.0,
        startup_cost_warm_dollar=0.0,
        startup_cost_hot_dollar=0.0,
        no_load_cost_dollar_per_hr=0.0,
    )


# ---------------------------------------------------------------------------
# 1-2: build_reserve_requirements
# ---------------------------------------------------------------------------


def test_build_reserve_requirements_values() -> None:
    """Spinning = 550 MW and non-spinning = 550 MW."""
    spinning, non_spinning = build_reserve_requirements()

    assert spinning.reserve_type == ReserveProduct.SPINNING
    assert spinning.requirement_mw == SPINNING_REQUIREMENT_MW
    assert spinning.requirement_mw == 550.0

    assert non_spinning.reserve_type == ReserveProduct.NON_SPINNING
    assert non_spinning.requirement_mw == NON_SPINNING_REQUIREMENT_MW
    assert non_spinning.requirement_mw == 550.0


def test_build_reserve_requirements_sum_equals_largest_gen() -> None:
    """Spinning + non-spinning = largest gen Pmax (1100 MW)."""
    spinning, non_spinning = build_reserve_requirements()
    total = spinning.requirement_mw + non_spinning.requirement_mw
    assert total == LARGEST_GEN_PMAX_MW
    assert total == 1100.0


# ---------------------------------------------------------------------------
# 3-5: compute_ramp_based_reserve_pct
# ---------------------------------------------------------------------------


def test_compute_ramp_based_reserve_pct_normal() -> None:
    """Normal case: ramp_mw * (deployment_min / 60) / pmax."""
    # 600 MW/hr * (10 min / 60) / 1040 MW = 100/1040 ~ 0.09615...
    pct = compute_ramp_based_reserve_pct(600.0, 10.0, 1040.0)
    expected = (600.0 * 10.0 / 60.0) / 1040.0
    assert abs(pct - expected) < 1e-9


def test_compute_ramp_based_reserve_pct_capped_at_one() -> None:
    """If ramp MW exceeds Pmax within the window, cap at 1.0."""
    # 10000 MW/hr * (30 min / 60) / 100 MW = 50 => capped to 1.0
    pct = compute_ramp_based_reserve_pct(10000.0, 30.0, 100.0)
    assert pct == 1.0


def test_compute_ramp_based_reserve_pct_rejects_zero_pmax() -> None:
    """pmax_mw must be positive."""
    with pytest.raises(ValueError, match="pmax_mw must be positive"):
        compute_ramp_based_reserve_pct(600.0, 10.0, 0.0)

    with pytest.raises(ValueError, match="pmax_mw must be positive"):
        compute_ramp_based_reserve_pct(600.0, 10.0, -100.0)


# ---------------------------------------------------------------------------
# 6-8: compute_generator_eligibility
# ---------------------------------------------------------------------------


def test_compute_generator_eligibility_nuclear() -> None:
    """Nuclear generators get fixed caps: 5% spinning, 10% non-spinning."""
    cls = _make_classification(
        gen_index=1,
        bus_id=31,
        fuel_category="nuclear",
        rts_gmlc_class=RtsGmlcClass.NUCLEAR,
        pmax_mw=646.0,
    )
    tp = _make_temporal_params(
        gen_index=1,
        bus_id=31,
        pmax_mw=646.0,
        ramp_rate_mw_per_hr=120.0,
        rts_gmlc_class="Nuclear",
    )
    elig = compute_generator_eligibility(cls, tp)

    assert elig.spinning_eligible is True
    assert elig.non_spinning_eligible is True
    assert elig.max_spinning_pct == NUCLEAR_MAX_SPINNING_PCT
    assert elig.max_spinning_pct == 0.05
    assert elig.max_non_spinning_pct == NUCLEAR_MAX_NON_SPINNING_PCT
    assert elig.max_non_spinning_pct == 0.10


def test_compute_generator_eligibility_hydro() -> None:
    """Hydro uses ramp-based percentages (fastest ramp)."""
    cls = _make_classification(
        gen_index=0,
        bus_id=30,
        fuel_category="hydro",
        rts_gmlc_class=RtsGmlcClass.HYDRO_RESERVOIR,
        pmax_mw=1040.0,
    )
    ramp_hr = 600.0
    tp = _make_temporal_params(
        gen_index=0,
        bus_id=30,
        pmax_mw=1040.0,
        ramp_rate_mw_per_hr=ramp_hr,
        rts_gmlc_class="Hydro",
    )
    elig = compute_generator_eligibility(cls, tp)

    expected_spinning = (ramp_hr * SPINNING_DEPLOYMENT_MINUTES / 60.0) / 1040.0
    expected_non_spinning = (ramp_hr * NON_SPINNING_DEPLOYMENT_MINUTES / 60.0) / 1040.0

    assert elig.spinning_eligible is True
    assert elig.non_spinning_eligible is True
    assert abs(elig.max_spinning_pct - expected_spinning) < 1e-9
    assert abs(elig.max_non_spinning_pct - expected_non_spinning) < 1e-9
    assert elig.rts_gmlc_class == "Hydro"


def test_compute_generator_eligibility_gas_cc() -> None:
    """Gas/CC uses ramp-based percentages."""
    cls = _make_classification(
        gen_index=6,
        bus_id=36,
        fuel_category="gas",
        rts_gmlc_class=RtsGmlcClass.GAS_CC,
        pmax_mw=580.0,
    )
    ramp_hr = 300.0
    tp = _make_temporal_params(
        gen_index=6,
        bus_id=36,
        pmax_mw=580.0,
        ramp_rate_mw_per_hr=ramp_hr,
        rts_gmlc_class="Gas/CC",
    )
    elig = compute_generator_eligibility(cls, tp)

    expected_spinning = (ramp_hr * 10.0 / 60.0) / 580.0
    expected_non_spinning = (ramp_hr * 30.0 / 60.0) / 580.0

    assert abs(elig.max_spinning_pct - expected_spinning) < 1e-9
    assert abs(elig.max_non_spinning_pct - expected_non_spinning) < 1e-9


# ---------------------------------------------------------------------------
# 9-10: compute_all_eligibilities
# ---------------------------------------------------------------------------


def test_compute_all_eligibilities_count() -> None:
    """Returns one eligibility per classification record."""
    n = 3
    classifications = [
        _make_classification(gen_index=i, bus_id=30 + i, pmax_mw=100.0 * (i + 1)) for i in range(n)
    ]
    temporal_params = [
        _make_temporal_params(gen_index=i, bus_id=30 + i, pmax_mw=100.0 * (i + 1)) for i in range(n)
    ]
    result = compute_all_eligibilities(classifications, temporal_params)
    assert len(result) == n


def test_compute_all_eligibilities_rejects_mismatched_pmax() -> None:
    """Raises ValueError when pmax_mw differs between classification and temporal."""
    cls = [_make_classification(gen_index=0, pmax_mw=1040.0)]
    tp = [_make_temporal_params(gen_index=0, pmax_mw=999.0)]  # mismatch!

    with pytest.raises(ValueError, match="Pmax mismatch"):
        compute_all_eligibilities(cls, tp)


# ---------------------------------------------------------------------------
# 11-12: validate_reserve_feasibility
# ---------------------------------------------------------------------------


def test_validate_reserve_feasibility_passes() -> None:
    """Feasibility check passes when total eligible capacity >= requirement."""
    cls = _make_classification(pmax_mw=1000.0)
    tp = _make_temporal_params(pmax_mw=1000.0, ramp_rate_mw_per_hr=6000.0)
    elig = compute_generator_eligibility(cls, tp)

    # With 6000 MW/hr ramp and 1000 MW pmax, spinning pct = 1.0 (capped)
    # So total eligible = 1000 MW >= 550 MW
    result = validate_reserve_feasibility(ReserveProduct.SPINNING, SPINNING_REQUIREMENT_MW, [elig])
    assert result.is_feasible is True
    assert result.margin_mw >= 0.0


def test_validate_reserve_feasibility_fails_spinning() -> None:
    """Feasibility check fails when total eligible capacity < requirement."""
    # Small generator with low ramp: can't meet 550 MW spinning
    cls = _make_classification(pmax_mw=100.0)
    tp = _make_temporal_params(pmax_mw=100.0, ramp_rate_mw_per_hr=60.0)
    elig = compute_generator_eligibility(cls, tp)

    result = validate_reserve_feasibility(ReserveProduct.SPINNING, SPINNING_REQUIREMENT_MW, [elig])
    assert result.is_feasible is False
    assert result.margin_mw < 0.0


# ---------------------------------------------------------------------------
# 13-14: write_reserve_requirements_csv_format
# ---------------------------------------------------------------------------


def test_write_reserve_requirements_csv_format(tmp_path: Path) -> None:
    """CSV has columns: reserve_type, HR_1..HR_24; two rows with 550.00."""
    spinning, non_spinning = build_reserve_requirements()
    dest = tmp_path / "reserve_requirements_24h.csv"
    write_reserve_requirements_csv(spinning, non_spinning, dest)

    text = dest.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["reserve_type"] == "spinning"
    assert rows[1]["reserve_type"] == "non_spinning"

    # Check header contains reserve_type + HR_1 through HR_24
    assert reader.fieldnames is not None
    assert reader.fieldnames[0] == "reserve_type"
    for h in range(1, 25):
        col = f"HR_{h}"
        assert col in reader.fieldnames
        assert rows[0][col] == "550.00"
        assert rows[1][col] == "550.00"


# ---------------------------------------------------------------------------
# 15: write_reserve_eligibility_csv
# ---------------------------------------------------------------------------


def test_write_reserve_eligibility_csv_format(tmp_path: Path) -> None:
    """CSV has correct columns and one row per generator."""
    cls_list = [
        _make_classification(gen_index=0, bus_id=30, pmax_mw=500.0),
        _make_classification(gen_index=1, bus_id=31, pmax_mw=600.0),
    ]
    tp_list = [
        _make_temporal_params(gen_index=0, bus_id=30, pmax_mw=500.0),
        _make_temporal_params(gen_index=1, bus_id=31, pmax_mw=600.0),
    ]
    eligibilities = compute_all_eligibilities(cls_list, tp_list)

    dest = tmp_path / "reserve_eligibility.csv"
    write_reserve_eligibility_csv(eligibilities, dest)

    text = dest.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 2
    assert reader.fieldnames is not None
    expected_cols = {
        "gen_uid",
        "gen_index",
        "bus_id",
        "fuel_type",
        "rts_gmlc_class",
        "pmax_mw",
        "ramp_rate_mw_per_hr",
        "spinning_eligible",
        "non_spinning_eligible",
        "max_spinning_pct",
        "max_non_spinning_pct",
    }
    assert expected_cols == set(reader.fieldnames)


def test_write_reserve_eligibility_csv_nuclear_values(tmp_path: Path) -> None:
    """Nuclear gen row has 5% spinning and 10% non-spinning."""
    cls = _make_classification(
        gen_index=1,
        bus_id=31,
        fuel_category="nuclear",
        rts_gmlc_class=RtsGmlcClass.NUCLEAR,
        pmax_mw=646.0,
    )
    tp = _make_temporal_params(
        gen_index=1,
        bus_id=31,
        pmax_mw=646.0,
        ramp_rate_mw_per_hr=120.0,
        rts_gmlc_class="Nuclear",
    )
    elig = [compute_generator_eligibility(cls, tp)]

    dest = tmp_path / "reserve_eligibility.csv"
    write_reserve_eligibility_csv(elig, dest)

    text = dest.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["spinning_eligible"] == "True"
    assert row["non_spinning_eligible"] == "True"
    assert float(row["max_spinning_pct"]) == pytest.approx(0.05)
    assert float(row["max_non_spinning_pct"]) == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# 16: define_reserves end-to-end
# ---------------------------------------------------------------------------


def test_define_reserves_end_to_end(tmp_path: Path) -> None:
    """Full pipeline produces both CSVs and returns valid result."""
    # Build a small fleet: 1 nuclear + 1 hydro with big ramp.
    classifications = [
        _make_classification(
            gen_index=0,
            bus_id=30,
            fuel_category="hydro",
            rts_gmlc_class=RtsGmlcClass.HYDRO_RESERVOIR,
            pmax_mw=1040.0,
        ),
        _make_classification(
            gen_index=1,
            bus_id=31,
            fuel_category="nuclear",
            rts_gmlc_class=RtsGmlcClass.NUCLEAR,
            pmax_mw=646.0,
        ),
    ]
    temporal_params = [
        _make_temporal_params(
            gen_index=0,
            bus_id=30,
            pmax_mw=1040.0,
            ramp_rate_mw_per_hr=6000.0,
            rts_gmlc_class="Hydro",
        ),
        _make_temporal_params(
            gen_index=1,
            bus_id=31,
            pmax_mw=646.0,
            ramp_rate_mw_per_hr=120.0,
            rts_gmlc_class="Nuclear",
        ),
    ]

    result = define_reserves(classifications, temporal_params, tmp_path)

    # Both CSVs exist.
    assert Path(result.requirements_csv_path).exists()
    assert Path(result.eligibility_csv_path).exists()

    # Requirements.
    assert result.spinning_requirement.requirement_mw == 550.0
    assert result.non_spinning_requirement.requirement_mw == 550.0

    # Eligibilities.
    assert len(result.eligibilities) == 2

    # Feasibility — hydro with 6000 MW/hr ramp provides enough capacity.
    assert result.spinning_feasibility.is_feasible is True
    assert result.non_spinning_feasibility.is_feasible is True
