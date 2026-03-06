"""Tests for the Generator Fuel-Type Classification module.

All tests use synthetic fixture data -- no network access, no real .m files,
and no external file dependencies. Tests are fully self-contained.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from scripts.build_rts_gmlc_reference import (
    CapacityBand,
    FuelType,
    build_capacity_band_thresholds,
)
from scripts.classify_gen_fuel import (
    ClassificationNetworkId,
    ClassificationSource,
    ConfidenceLevel,
    GasUnitType,
    GenFuelClassificationRow,
    HeuristicThresholds,
    NetworkClassificationResult,
    assign_capacity_band,
    build_tech_class_counts,
    classify_fuel_from_genfuel,
    classify_generator,
    classify_network,
    compose_tech_class,
    infer_gas_unit_type,
    load_reference_thresholds,
    resolve_fuel_type,
    write_classification_csv,
)
from scripts.reconcile_bus_gen import MatpowerCaseData, MatpowerGenRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gen(
    gen_bus: int = 1,
    pg: float = 0.0,
    qg: float = 0.0,
    pmax: float = 100.0,
    pmin: float = 10.0,
    fuel_type: str | None = None,
) -> MatpowerGenRecord:
    """Create a synthetic MatpowerGenRecord."""
    return MatpowerGenRecord(
        gen_bus=gen_bus,
        pg=pg,
        qg=qg,
        pmax=pmax,
        pmin=pmin,
        fuel_type=fuel_type,
    )


def _make_case_data(
    generators: list[MatpowerGenRecord] | None = None,
    has_genfuel: bool = True,
) -> MatpowerCaseData:
    """Create a synthetic MatpowerCaseData."""
    if generators is None:
        generators = [_make_gen()]
    return MatpowerCaseData(
        file_name="test.m",
        file_path="test.m",
        buses=[],
        generators=generators,
        base_mva=100.0,
        has_genfuel=has_genfuel,
    )


# ---------------------------------------------------------------------------
# Test 1: Standard genfuel label mapping
# ---------------------------------------------------------------------------


def test_genfuel_standard_labels():
    """Standard genfuel labels are correctly mapped to FuelType."""
    assert classify_fuel_from_genfuel("coal") == FuelType.COAL
    assert classify_fuel_from_genfuel("Coal") == FuelType.COAL
    assert classify_fuel_from_genfuel("ng") == FuelType.GAS
    assert classify_fuel_from_genfuel("NG") == FuelType.GAS
    assert classify_fuel_from_genfuel("gas") == FuelType.GAS
    assert classify_fuel_from_genfuel("nuclear") == FuelType.NUCLEAR
    assert classify_fuel_from_genfuel("wind") == FuelType.WIND
    assert classify_fuel_from_genfuel("solar") == FuelType.SOLAR
    assert classify_fuel_from_genfuel("hydro") == FuelType.HYDRO
    assert classify_fuel_from_genfuel("oil") == FuelType.OIL


# ---------------------------------------------------------------------------
# Test 2: Unrecognized genfuel labels return None
# ---------------------------------------------------------------------------


def test_genfuel_unrecognized_returns_none():
    """Unrecognized genfuel labels return None."""
    assert classify_fuel_from_genfuel("biomass") is None
    assert classify_fuel_from_genfuel("geothermal") is None
    assert classify_fuel_from_genfuel("") is None
    assert classify_fuel_from_genfuel(None) is None


# ---------------------------------------------------------------------------
# Test 3: Genfuel + companion agree gives HIGH confidence
# ---------------------------------------------------------------------------


def test_genfuel_companion_agree_high_confidence():
    """When genfuel and companion agree, confidence is HIGH."""
    fuel_type, source, confidence = resolve_fuel_type(
        genfuel_result=FuelType.COAL,
        companion_result=FuelType.COAL,
        heuristic_result=FuelType.GAS,
    )
    assert fuel_type == FuelType.COAL
    assert source == ClassificationSource.GENFUEL
    assert confidence == ConfidenceLevel.HIGH


# ---------------------------------------------------------------------------
# Test 4: Genfuel-only gives MEDIUM confidence
# ---------------------------------------------------------------------------


def test_genfuel_only_medium_confidence():
    """When only genfuel is available, confidence is MEDIUM."""
    fuel_type, source, confidence = resolve_fuel_type(
        genfuel_result=FuelType.NUCLEAR,
        companion_result=None,
        heuristic_result=FuelType.GAS,
    )
    assert fuel_type == FuelType.NUCLEAR
    assert source == ClassificationSource.GENFUEL
    assert confidence == ConfidenceLevel.MEDIUM


# ---------------------------------------------------------------------------
# Test 5: Heuristic fallback gives LOW confidence
# ---------------------------------------------------------------------------


def test_heuristic_fallback_low_confidence():
    """When only heuristic is available, confidence is LOW."""
    fuel_type, source, confidence = resolve_fuel_type(
        genfuel_result=None,
        companion_result=None,
        heuristic_result=FuelType.GAS,
    )
    assert fuel_type == FuelType.GAS
    assert source == ClassificationSource.HEURISTIC
    assert confidence == ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# Test 6: Case39 hardcoded gives HIGH confidence
# ---------------------------------------------------------------------------


def test_case39_hardcoded_high_confidence():
    """Case39 generators use hardcoded map with HIGH confidence."""
    gen = _make_gen(gen_bus=30, pmax=250.0, fuel_type=None)
    thresholds = build_capacity_band_thresholds()

    row = classify_generator(
        gen=gen,
        gen_index=0,
        network_id=ClassificationNetworkId.TINY,
        companion_labels=[],
        thresholds=thresholds,
        heuristic_thresholds=HeuristicThresholds(),
    )

    # gen_index=0 maps to HYDRO in CASE39_FUEL_MAP
    assert row.fuel_type == FuelType.HYDRO
    assert row.source == ClassificationSource.CASE39_HARDCODED
    assert row.confidence == ConfidenceLevel.HIGH


# ---------------------------------------------------------------------------
# Test 7: Gas unit type from gentype field
# ---------------------------------------------------------------------------


def test_gas_unit_type_from_gentype():
    """Gas unit type is inferred from gentype field when available."""
    gen = _make_gen(pmax=50.0)
    assert infer_gas_unit_type(gen, gentype_field="CT") == GasUnitType.CT
    assert infer_gas_unit_type(gen, gentype_field="GT") == GasUnitType.CT
    assert infer_gas_unit_type(gen, gentype_field="CC") == GasUnitType.CC
    assert infer_gas_unit_type(gen, gentype_field="CA") == GasUnitType.CC
    assert infer_gas_unit_type(gen, gentype_field="ST") == GasUnitType.STEAM
    assert infer_gas_unit_type(gen, gentype_field="STEAM") == GasUnitType.STEAM


# ---------------------------------------------------------------------------
# Test 8: Gas unit type from Pmax
# ---------------------------------------------------------------------------


def test_gas_unit_type_from_pmax():
    """Gas unit type is inferred from Pmax when gentype is not available."""
    small_gen = _make_gen(pmax=50.0)
    assert infer_gas_unit_type(small_gen) == GasUnitType.CT

    medium_gen = _make_gen(pmax=200.0)
    assert infer_gas_unit_type(medium_gen) == GasUnitType.CC

    large_gen = _make_gen(pmax=400.0)
    assert infer_gas_unit_type(large_gen) == GasUnitType.STEAM


# ---------------------------------------------------------------------------
# Test 9: Capacity band matching
# ---------------------------------------------------------------------------


def test_capacity_band_matching():
    """Generators are assigned to the correct capacity band."""
    thresholds = build_capacity_band_thresholds()

    # Coal small: < 100 MW
    assert assign_capacity_band(FuelType.COAL, 76.0, thresholds) == CapacityBand.SMALL
    # Coal medium: 100-300 MW
    assert assign_capacity_band(FuelType.COAL, 155.0, thresholds) == CapacityBand.MEDIUM
    # Coal large: >= 300 MW
    assert assign_capacity_band(FuelType.COAL, 350.0, thresholds) == CapacityBand.LARGE


# ---------------------------------------------------------------------------
# Test 10: Capacity band exceeds largest
# ---------------------------------------------------------------------------


def test_capacity_band_exceeds_largest():
    """When Pmax exceeds all defined bands, the largest band is returned."""
    thresholds = build_capacity_band_thresholds()

    # Gas: only small (< 40) and large (>= 40)
    band = assign_capacity_band(FuelType.GAS, 9999.0, thresholds)
    assert band == CapacityBand.LARGE

    # Coal: largest is LARGE (>= 300)
    band = assign_capacity_band(FuelType.COAL, 5000.0, thresholds)
    assert band == CapacityBand.LARGE


# ---------------------------------------------------------------------------
# Test 11: Tech class composition for gas
# ---------------------------------------------------------------------------


def test_tech_class_composition_gas():
    """Gas tech class includes unit type (e.g., gas_CT)."""
    tc = compose_tech_class(FuelType.GAS, "CT", CapacityBand.SMALL)
    assert tc == "gas_CT"

    tc = compose_tech_class(FuelType.GAS, "CC", CapacityBand.LARGE)
    assert tc == "gas_CC"

    tc = compose_tech_class(FuelType.GAS, "STEAM", CapacityBand.LARGE)
    assert tc == "gas_STEAM"


# ---------------------------------------------------------------------------
# Test 12: Tech class for single-band fuels
# ---------------------------------------------------------------------------


def test_tech_class_single_band_fuels():
    """Single-band fuels use just the fuel name as tech class."""
    assert compose_tech_class(FuelType.NUCLEAR, "NUCLEAR", CapacityBand.LARGE) == "nuclear"
    assert compose_tech_class(FuelType.HYDRO, "HYDRO", CapacityBand.SMALL) == "hydro"
    assert compose_tech_class(FuelType.WIND, "WIND", CapacityBand.SMALL) == "wind"
    assert compose_tech_class(FuelType.SOLAR, "PV", CapacityBand.SMALL) == "solar"

    # Coal is multi-band
    assert compose_tech_class(FuelType.COAL, "STEAM", CapacityBand.SMALL) == "coal_small"
    assert compose_tech_class(FuelType.COAL, "STEAM", CapacityBand.LARGE) == "coal_large"


# ---------------------------------------------------------------------------
# Test 13: End-to-end generator classification
# ---------------------------------------------------------------------------


def test_end_to_end_generator_classification():
    """Full classification pipeline for a non-case39 generator."""
    gen = _make_gen(gen_bus=101, pmax=350.0, pmin=100.0, fuel_type="Coal")
    thresholds = build_capacity_band_thresholds()

    row = classify_generator(
        gen=gen,
        gen_index=0,
        network_id=ClassificationNetworkId.SMALL,
        companion_labels=[],
        thresholds=thresholds,
        heuristic_thresholds=HeuristicThresholds(),
    )

    assert row.fuel_type == FuelType.COAL
    assert row.unit_type == "STEAM"
    assert row.capacity_band == CapacityBand.LARGE
    assert row.tech_class == "coal_large"
    assert row.source == ClassificationSource.GENFUEL
    assert row.confidence == ConfidenceLevel.MEDIUM
    assert row.pmax_mw == 350.0
    assert row.gen_uid == "ACTIVSg2000_101_0"


# ---------------------------------------------------------------------------
# Test 14: CSV output columns/order
# ---------------------------------------------------------------------------


def test_csv_output_columns_and_order(tmp_path: Path):
    """CSV output has the correct columns in the expected order."""
    classifications = [
        GenFuelClassificationRow(
            gen_index=0,
            gen_bus=1,
            gen_uid="test_1_0",
            fuel_type=FuelType.COAL,
            gas_unit_type=None,
            unit_type="STEAM",
            capacity_band=CapacityBand.LARGE,
            tech_class="coal_large",
            pmax_mw=350.0,
            pmin_mw=100.0,
            source=ClassificationSource.GENFUEL,
            confidence=ConfidenceLevel.HIGH,
        ),
    ]
    result = NetworkClassificationResult(
        network_id=ClassificationNetworkId.SMALL,
        generator_count=1,
        classifications=classifications,
        tech_class_counts=[],
    )

    csv_path = tmp_path / "test_output.csv"
    write_classification_csv(result, csv_path)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    expected_columns = [
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

    assert reader.fieldnames == expected_columns

    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["fuel_type"] == "coal"
    assert rows[0]["tech_class"] == "coal_large"
    assert rows[0]["gas_unit_type"] == ""  # None rendered as empty


# ---------------------------------------------------------------------------
# Test 15: Tech class count aggregation
# ---------------------------------------------------------------------------


def test_tech_class_count_aggregation():
    """Tech class counts are correctly aggregated from classifications."""
    classifications = [
        GenFuelClassificationRow(
            gen_index=0,
            gen_bus=1,
            gen_uid="u0",
            fuel_type=FuelType.COAL,
            gas_unit_type=None,
            unit_type="STEAM",
            capacity_band=CapacityBand.LARGE,
            tech_class="coal_large",
            pmax_mw=350.0,
            pmin_mw=100.0,
            source=ClassificationSource.GENFUEL,
            confidence=ConfidenceLevel.HIGH,
        ),
        GenFuelClassificationRow(
            gen_index=1,
            gen_bus=2,
            gen_uid="u1",
            fuel_type=FuelType.COAL,
            gas_unit_type=None,
            unit_type="STEAM",
            capacity_band=CapacityBand.LARGE,
            tech_class="coal_large",
            pmax_mw=400.0,
            pmin_mw=120.0,
            source=ClassificationSource.GENFUEL,
            confidence=ConfidenceLevel.HIGH,
        ),
        GenFuelClassificationRow(
            gen_index=2,
            gen_bus=3,
            gen_uid="u2",
            fuel_type=FuelType.GAS,
            gas_unit_type=GasUnitType.CT,
            unit_type="CT",
            capacity_band=CapacityBand.SMALL,
            tech_class="gas_CT",
            pmax_mw=50.0,
            pmin_mw=10.0,
            source=ClassificationSource.GENFUEL,
            confidence=ConfidenceLevel.MEDIUM,
        ),
    ]

    counts = build_tech_class_counts(classifications)

    assert len(counts) == 2

    coal_count = next(c for c in counts if c.tech_class == "coal_large")
    assert coal_count.count == 2
    assert coal_count.total_pmax_mw == 750.0
    assert coal_count.fuel_type == FuelType.COAL

    gas_count = next(c for c in counts if c.tech_class == "gas_CT")
    assert gas_count.count == 1
    assert gas_count.total_pmax_mw == 50.0


# ---------------------------------------------------------------------------
# Test 16: Reference thresholds roundtrip
# ---------------------------------------------------------------------------


def test_reference_thresholds_roundtrip():
    """load_reference_thresholds returns same thresholds as build_capacity_band_thresholds."""
    loaded = load_reference_thresholds()
    direct = build_capacity_band_thresholds()

    assert len(loaded) == len(direct)
    for l_th, d_th in zip(loaded, direct):
        assert l_th.fuel_type == d_th.fuel_type
        assert l_th.band == d_th.band
        assert l_th.min_mw == d_th.min_mw
        assert l_th.max_mw == d_th.max_mw


# ---------------------------------------------------------------------------
# Test 17: Case39 all high confidence
# ---------------------------------------------------------------------------


def test_case39_all_high_confidence():
    """All 10 case39 generators should be classified with HIGH confidence."""
    # Create 10 generators matching CASE39_FUEL_MAP
    generators = [_make_gen(gen_bus=i + 30, pmax=100.0 + i * 50) for i in range(10)]
    case_data = _make_case_data(generators=generators, has_genfuel=False)
    thresholds = build_capacity_band_thresholds()

    result = classify_network(
        network_id=ClassificationNetworkId.TINY,
        case_data=case_data,
        companion_labels=[],
        thresholds=thresholds,
    )

    assert result.generator_count == 10
    assert len(result.classifications) == 10

    for row in result.classifications:
        assert row.confidence == ConfidenceLevel.HIGH
        assert row.source == ClassificationSource.CASE39_HARDCODED


# ---------------------------------------------------------------------------
# Test 18: ACTIVSg2000 no heuristic needed (all have genfuel)
# ---------------------------------------------------------------------------


def test_activsg2000_no_heuristic_needed():
    """ACTIVSg2000 generators with genfuel don't fall through to heuristic."""
    generators = [
        _make_gen(gen_bus=1, pmax=350.0, fuel_type="coal"),
        _make_gen(gen_bus=2, pmax=500.0, fuel_type="nuclear"),
        _make_gen(gen_bus=3, pmax=50.0, fuel_type="ng"),
        _make_gen(gen_bus=4, pmax=200.0, fuel_type="wind"),
        _make_gen(gen_bus=5, pmax=100.0, fuel_type="solar"),
    ]
    case_data = _make_case_data(generators=generators, has_genfuel=True)
    thresholds = build_capacity_band_thresholds()

    result = classify_network(
        network_id=ClassificationNetworkId.SMALL,
        case_data=case_data,
        companion_labels=[],
        thresholds=thresholds,
    )

    assert result.generator_count == 5
    for row in result.classifications:
        assert row.source == ClassificationSource.GENFUEL
        assert row.confidence == ConfidenceLevel.MEDIUM  # genfuel-only
        assert row.source != ClassificationSource.HEURISTIC

    # Verify correct fuel types
    fuel_types = [r.fuel_type for r in result.classifications]
    assert fuel_types == [
        FuelType.COAL,
        FuelType.NUCLEAR,
        FuelType.GAS,
        FuelType.WIND,
        FuelType.SOLAR,
    ]
