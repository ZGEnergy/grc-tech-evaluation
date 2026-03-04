"""Tests for the RTS-GMLC Technology Class Reference Table builder.

All tests use synthetic fixture data -- no network access or real RTS-GMLC
files are required. Tests are fully self-contained.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.build_rts_gmlc_reference import (
    CapacityBandThreshold,
    FuelType,
    ReferenceTableResult,
    RtsGmlcGenerator,
    RtsGmlcProvenance,
    TechClassRow,
    aggregate_tech_class,
    build_capacity_band_thresholds,
    build_reference_table,
    classify_generator,
    compute_startup_cost,
    main,
    parse_gen_csv,
    write_reference_csv,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic generator records
# ---------------------------------------------------------------------------


def _make_generator(
    gen_uid: str = "G1",
    bus_id: int = 101,
    unit_type: str = "STEAM",
    fuel: str = "Coal",
    category: str = "Coal",
    pmax_mw: float = 76.0,
    pmin_mw: float = 30.0,
    ramp_rate_mw_per_min: float = 1.5,
    min_up_time_hr: float = 24.0,
    min_down_time_hr: float = 24.0,
    startup_time_cold_hr: float = 48.0,
    startup_time_warm_hr: float = 24.0,
    startup_time_hot_hr: float = 4.0,
    startup_heat_cold_mbtu: float = 10.0,
    startup_heat_warm_mbtu: float = 7.0,
    startup_heat_hot_mbtu: float = 3.0,
    non_fuel_start_cost_dollar: float = 100.0,
    non_fuel_shutdown_cost_dollar: float = 50.0,
    fuel_price_dollar_per_mmbtu: float = 2.0,
    hr_avg_0: float = 10000.0,
) -> RtsGmlcGenerator:
    """Create a synthetic RtsGmlcGenerator with sensible defaults."""
    return RtsGmlcGenerator(
        gen_uid=gen_uid,
        bus_id=bus_id,
        unit_type=unit_type,
        fuel=fuel,
        category=category,
        pmax_mw=pmax_mw,
        pmin_mw=pmin_mw,
        ramp_rate_mw_per_min=ramp_rate_mw_per_min,
        min_up_time_hr=min_up_time_hr,
        min_down_time_hr=min_down_time_hr,
        startup_time_cold_hr=startup_time_cold_hr,
        startup_time_warm_hr=startup_time_warm_hr,
        startup_time_hot_hr=startup_time_hot_hr,
        startup_heat_cold_mbtu=startup_heat_cold_mbtu,
        startup_heat_warm_mbtu=startup_heat_warm_mbtu,
        startup_heat_hot_mbtu=startup_heat_hot_mbtu,
        non_fuel_start_cost_dollar=non_fuel_start_cost_dollar,
        non_fuel_shutdown_cost_dollar=non_fuel_shutdown_cost_dollar,
        fuel_price_dollar_per_mmbtu=fuel_price_dollar_per_mmbtu,
        hr_avg_0=hr_avg_0,
    )


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a CSV file from header and rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


# Standard CSV header matching RTS-GMLC format (some columns with leading spaces).
_FULL_HEADER = [
    "GEN UID",
    " Bus ID",
    "Unit Type",
    "Fuel",
    "Category",
    "PMax MW",
    "PMin MW",
    " Ramp Rate MW/Min",
    "Min Up Time Hr",
    "Min Down Time Hr",
    "Start Time Cold Hr",
    "Start Time Warm Hr",
    "Start Time Hot Hr",
    "Start Heat Cold MBTU",
    "Start Heat Warm MBTU",
    "Start Heat Hot MBTU",
    "Non Fuel Start Cost $",
    "Non Fuel Shutdown Cost $",
    "Fuel Price $/MMBTU",
    "HR_avg_0",
]


def _make_csv_row(
    gen_uid: str = "G1",
    bus_id: str = "101",
    unit_type: str = "STEAM",
    fuel: str = "Coal",
    category: str = "Coal",
    pmax_mw: str = "76.0",
    pmin_mw: str = "30.0",
    ramp_rate: str = "1.5",
    min_up: str = "24",
    min_down: str = "24",
    st_cold: str = "48",
    st_warm: str = "24",
    st_hot: str = "4",
    sh_cold: str = "10",
    sh_warm: str = "7",
    sh_hot: str = "3",
    nf_start: str = "100",
    nf_shutdown: str = "50",
    fuel_price: str = "2.0",
    hr_avg: str = "10000",
) -> list[str]:
    return [
        gen_uid,
        bus_id,
        unit_type,
        fuel,
        category,
        pmax_mw,
        pmin_mw,
        ramp_rate,
        min_up,
        min_down,
        st_cold,
        st_warm,
        st_hot,
        sh_cold,
        sh_warm,
        sh_hot,
        nf_start,
        nf_shutdown,
        fuel_price,
        hr_avg,
    ]


@pytest.fixture
def thresholds() -> list[CapacityBandThreshold]:
    """Standard capacity band thresholds."""
    return build_capacity_band_thresholds()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseGenCsv:
    """Tests for parse_gen_csv function."""

    def test_parse_gen_csv_returns_all_generators(self, tmp_path: Path) -> None:
        """Verify parse_gen_csv returns the correct number of generator records."""
        csv_path = tmp_path / "gen.csv"
        rows = [
            _make_csv_row(gen_uid="G1", pmax_mw="76.0"),
            _make_csv_row(gen_uid="G2", pmax_mw="155.0"),
            _make_csv_row(gen_uid="G3", pmax_mw="350.0"),
        ]
        _write_csv(csv_path, _FULL_HEADER, rows)

        result = parse_gen_csv(csv_path)

        assert len(result) == 3
        for gen in result:
            assert gen.gen_uid != ""
            assert gen.pmax_mw > 0

    def test_parse_gen_csv_strips_column_whitespace(self, tmp_path: Path) -> None:
        """Verify leading-space column names are handled correctly."""
        csv_path = tmp_path / "gen.csv"
        rows = [_make_csv_row(gen_uid="G1", bus_id="205", ramp_rate="2.5")]
        _write_csv(csv_path, _FULL_HEADER, rows)

        result = parse_gen_csv(csv_path)

        assert len(result) == 1
        assert result[0].bus_id == 205
        assert result[0].ramp_rate_mw_per_min == 2.5

    def test_parse_gen_csv_missing_required_columns_raises(self, tmp_path: Path) -> None:
        """Verify ValueError is raised when required columns are missing."""
        # Header missing PMax MW.
        bad_header = [h for h in _FULL_HEADER if h != "PMax MW"]
        csv_path = tmp_path / "gen.csv"
        _write_csv(csv_path, bad_header, [])

        with pytest.raises(ValueError, match="missing required columns"):
            parse_gen_csv(csv_path)


class TestClassifyGenerator:
    """Tests for classify_generator function."""

    def test_classify_generator_coal_steam(self, thresholds: list[CapacityBandThreshold]) -> None:
        """Coal STEAM generators are classified by capacity band."""
        gen_small = _make_generator(fuel="Coal", unit_type="STEAM", pmax_mw=76.0)
        gen_medium = _make_generator(fuel="Coal", unit_type="STEAM", pmax_mw=155.0)

        assert classify_generator(gen_small, thresholds) == "coal_small"
        assert classify_generator(gen_medium, thresholds) == "coal_medium"

    def test_classify_generator_gas_ct(self, thresholds: list[CapacityBandThreshold]) -> None:
        """Gas CT generators are classified with unit type in name."""
        gen_gas_ct = _make_generator(fuel="NG", unit_type="CT", pmax_mw=55.0)
        result = classify_generator(gen_gas_ct, thresholds)
        assert result == "gas_CT"

        gen_oil_ct = _make_generator(fuel="Oil", unit_type="CT", pmax_mw=20.0)
        result_oil = classify_generator(gen_oil_ct, thresholds)
        assert result_oil == "oil_CT"

    def test_classify_generator_sync_cond_excluded(
        self, thresholds: list[CapacityBandThreshold]
    ) -> None:
        """SYNC_COND generators return None (excluded)."""
        gen = _make_generator(unit_type="SYNC_COND", fuel="NG", pmax_mw=0.0)
        assert classify_generator(gen, thresholds) is None

    def test_classify_generator_renewable_classes(
        self, thresholds: list[CapacityBandThreshold]
    ) -> None:
        """Wind and Solar generators are classified into their respective classes."""
        gen_wind = _make_generator(fuel="Wind", unit_type="WIND", pmax_mw=100.0)
        gen_pv = _make_generator(fuel="Solar", unit_type="PV", pmax_mw=50.0)
        gen_rtpv = _make_generator(fuel="Solar", unit_type="RTPV", pmax_mw=10.0)

        assert classify_generator(gen_wind, thresholds) == "wind"
        assert classify_generator(gen_pv, thresholds) == "solar"
        assert classify_generator(gen_rtpv, thresholds) == "solar"


class TestComputeStartupCost:
    """Tests for compute_startup_cost function."""

    def test_compute_startup_cost_known_values(self) -> None:
        """Verify startup cost formula: heat * fuel_price + non_fuel_cost."""
        result = compute_startup_cost(
            startup_heat_mbtu=10.0,
            fuel_price_dollar_per_mmbtu=2.0,
            non_fuel_start_cost_dollar=100.0,
        )
        assert result == pytest.approx(120.0)

    def test_compute_startup_cost_zero_heat(self) -> None:
        """Zero startup heat yields only the non-fuel cost."""
        result = compute_startup_cost(
            startup_heat_mbtu=0.0,
            fuel_price_dollar_per_mmbtu=5.0,
            non_fuel_start_cost_dollar=200.0,
        )
        assert result == pytest.approx(200.0)


class TestAggregateTechClass:
    """Tests for aggregate_tech_class function."""

    def test_aggregate_tech_class_median_pmax(
        self, thresholds: list[CapacityBandThreshold]
    ) -> None:
        """Median pmax_template_mw from three generators."""
        gens = [
            _make_generator(gen_uid="G1", pmax_mw=76.0),
            _make_generator(gen_uid="G2", pmax_mw=76.0),
            _make_generator(gen_uid="G3", pmax_mw=155.0),
        ]
        row = aggregate_tech_class("coal_small", gens, thresholds)
        # median of [76, 76, 155] = 76
        assert row.pmax_template_mw == pytest.approx(76.0)

    def test_aggregate_tech_class_ramp_rate_conversion(
        self, thresholds: list[CapacityBandThreshold]
    ) -> None:
        """ramp_rate_mw_per_hr equals ramp_rate_mw_per_min * 60."""
        gens = [_make_generator(gen_uid="G1", ramp_rate_mw_per_min=2.0)]
        row = aggregate_tech_class("coal_small", gens, thresholds)
        assert row.ramp_rate_mw_per_hr == pytest.approx(row.ramp_rate_mw_per_min * 60.0)
        assert row.ramp_rate_mw_per_hr == pytest.approx(120.0)

    def test_aggregate_tech_class_renewable_zeroes(
        self, thresholds: list[CapacityBandThreshold]
    ) -> None:
        """Renewable classes have zero temporal parameters."""
        gens = [
            _make_generator(
                gen_uid="W1",
                fuel="Wind",
                unit_type="WIND",
                pmax_mw=100.0,
                ramp_rate_mw_per_min=5.0,
                min_up_time_hr=0.0,
                min_down_time_hr=0.0,
                startup_time_cold_hr=0.0,
                non_fuel_start_cost_dollar=0.0,
                non_fuel_shutdown_cost_dollar=0.0,
            ),
        ]
        row = aggregate_tech_class("wind", gens, thresholds)
        assert row.ramp_rate_mw_per_min == 0.0
        assert row.min_up_time_hr == 0.0
        assert row.min_down_time_hr == 0.0
        assert row.startup_time_cold_hr == 0.0
        assert row.startup_cost_cold_dollar == 0.0
        assert row.shutdown_cost_dollar == 0.0

    def test_aggregate_tech_class_empty_raises(
        self, thresholds: list[CapacityBandThreshold]
    ) -> None:
        """Empty generator list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot aggregate empty"):
            aggregate_tech_class("coal_small", [], thresholds)


class TestBuildReferenceTable:
    """Tests for build_reference_table function."""

    def test_build_reference_table_produces_expected_classes(self) -> None:
        """Reference table from a mixed fleet includes expected tech classes."""
        gens = [
            # Coal small.
            _make_generator(gen_uid="C1", fuel="Coal", unit_type="STEAM", pmax_mw=76.0),
            # Coal large.
            _make_generator(gen_uid="C2", fuel="Coal", unit_type="STEAM", pmax_mw=350.0),
            # Gas CC.
            _make_generator(gen_uid="GCC1", fuel="NG", unit_type="CC", pmax_mw=355.0),
            # Gas CT small.
            _make_generator(gen_uid="GCT1", fuel="NG", unit_type="CT", pmax_mw=20.0),
            # Oil CT.
            _make_generator(gen_uid="O1", fuel="Oil", unit_type="CT", pmax_mw=20.0),
            # Nuclear.
            _make_generator(gen_uid="N1", fuel="Nuclear", unit_type="NUCLEAR", pmax_mw=400.0),
            # Hydro.
            _make_generator(gen_uid="H1", fuel="Hydro", unit_type="HYDRO", pmax_mw=50.0),
            # Wind.
            _make_generator(gen_uid="W1", fuel="Wind", unit_type="WIND", pmax_mw=100.0),
            # Solar.
            _make_generator(gen_uid="S1", fuel="Solar", unit_type="PV", pmax_mw=50.0),
        ]

        result = build_reference_table(gens)
        class_names = {tc.tech_class for tc in result.tech_classes}

        expected = {
            "coal_small",
            "coal_large",
            "gas_CC",
            "gas_CT",
            "oil_CT",
            "nuclear",
            "hydro",
            "wind",
            "solar",
        }
        assert expected.issubset(class_names), f"Missing: {expected - class_names}"

        for tc in result.tech_classes:
            assert tc.generator_count > 0

    def test_build_reference_table_excludes_sync_cond(self) -> None:
        """SYNC_COND generators are excluded from tech classes."""
        gens = [
            _make_generator(gen_uid="SC1", fuel="NG", unit_type="SYNC_COND", pmax_mw=0.0),
            _make_generator(gen_uid="C1", fuel="Coal", unit_type="STEAM", pmax_mw=76.0),
        ]

        result = build_reference_table(gens)

        assert "SC1" in result.excluded_gen_uids
        for tc in result.tech_classes:
            assert tc.unit_type != "SYNC_COND"


class TestWriteReferenceCsv:
    """Tests for write_reference_csv function."""

    def _make_result(self) -> tuple[ReferenceTableResult, RtsGmlcProvenance]:
        """Create a minimal result for CSV writing tests."""
        provenance = RtsGmlcProvenance(
            repo_url="https://github.com/GridMod/RTS-GMLC",
            commit_hash="abc123",
            file_path="RTS_Data/SourceData/gen.csv",
            download_timestamp="2025-01-15T12:00:00+00:00",
            script_version="0.1.0",
            num_generators_parsed=3,
            num_tech_classes_produced=1,
        )
        tc = TechClassRow(
            tech_class="coal_small",
            fuel_type="coal",
            unit_type="STEAM",
            capacity_band="small",
            pmax_template_mw=76.0,
            pmin_template_mw=30.0,
            ramp_rate_mw_per_min=1.5,
            ramp_rate_mw_per_hr=90.0,
            min_up_time_hr=24.0,
            min_down_time_hr=24.0,
            startup_time_cold_hr=48.0,
            startup_time_warm_hr=24.0,
            startup_time_hot_hr=4.0,
            startup_cost_cold_dollar=120.0,
            startup_cost_warm_dollar=114.0,
            startup_cost_hot_dollar=106.0,
            shutdown_cost_dollar=50.0,
            capacity_band_min_mw=0.0,
            capacity_band_max_mw=100.0,
            generator_count=3,
            source_gen_uids=["G1", "G2", "G3"],
        )
        result = ReferenceTableResult(
            provenance=provenance,
            tech_classes=[tc],
            capacity_band_thresholds=build_capacity_band_thresholds(),
            excluded_gen_uids=[],
        )
        return result, provenance

    def test_write_reference_csv_has_provenance_header(self, tmp_path: Path) -> None:
        """CSV starts with comment lines containing provenance metadata."""
        result, provenance = self._make_result()
        csv_path = tmp_path / "output.csv"
        write_reference_csv(result, csv_path, provenance=provenance)

        text = csv_path.read_text(encoding="utf-8")
        lines = text.splitlines()

        comment_lines = [line for line in lines if line.startswith("#")]
        assert len(comment_lines) >= 3

        comment_text = "\n".join(comment_lines)
        assert "abc123" in comment_text
        assert "https://github.com/GridMod/RTS-GMLC" in comment_text
        assert "2025-01-15T12:00:00" in comment_text

    def test_write_reference_csv_roundtrip(self, tmp_path: Path) -> None:
        """CSV can be read back with correct row count and column names."""
        result, provenance = self._make_result()
        csv_path = tmp_path / "output.csv"
        write_reference_csv(result, csv_path, provenance=provenance)

        # Read back, skipping comment lines.
        text = csv_path.read_text(encoding="utf-8")
        data_lines = [line for line in text.splitlines() if not line.startswith("#")]
        data_text = "\n".join(data_lines)

        reader = csv.DictReader(data_text.splitlines())
        rows = list(reader)

        assert len(rows) == len(result.tech_classes)

        expected_cols = {
            "tech_class",
            "fuel_type",
            "unit_type",
            "capacity_band",
            "pmax_template_mw",
            "generator_count",
        }
        assert expected_cols.issubset(set(reader.fieldnames or []))

        # Non-renewable classes should have positive pmax.
        for row in rows:
            fuel = row["fuel_type"]
            if fuel not in ("wind", "solar"):
                assert float(row["pmax_template_mw"]) > 0


class TestCapacityBandThresholds:
    """Tests for build_capacity_band_thresholds."""

    def test_build_capacity_band_thresholds_cover_all_fuel_types(self) -> None:
        """Thresholds cover every FuelType enum member."""
        thresholds = build_capacity_band_thresholds()
        covered_fuels = {t.fuel_type for t in thresholds}

        for fuel in FuelType:
            assert fuel in covered_fuels, f"Missing thresholds for fuel type: {fuel}"

    def test_capacity_band_contiguity(self) -> None:
        """For fuel types with multiple bands, boundaries are contiguous."""
        thresholds = build_capacity_band_thresholds()

        # Group by fuel type.
        by_fuel: dict[FuelType, list[CapacityBandThreshold]] = {}
        for t in thresholds:
            by_fuel.setdefault(t.fuel_type, []).append(t)

        for fuel_type, fuel_thresholds in by_fuel.items():
            if len(fuel_thresholds) <= 1:
                continue

            sorted_bands = sorted(fuel_thresholds, key=lambda t: t.min_mw)
            for i in range(len(sorted_bands) - 1):
                cur, nxt = sorted_bands[i], sorted_bands[i + 1]
                assert cur.max_mw == pytest.approx(nxt.min_mw), (
                    f"Non-contiguous bands for {fuel_type}: {cur} -> {nxt}"
                )


class TestMainEntryPoint:
    """Tests for the main() entry point."""

    def test_main_creates_output_directory_and_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() creates output directory, CSV file, and cached gen.csv."""
        # Create a fake gen.csv to avoid network access.
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)

        gen_csv = raw_dir / "gen.csv"
        rows = [
            _make_csv_row(gen_uid="G1", fuel="Coal", unit_type="STEAM", pmax_mw="76.0"),
            _make_csv_row(gen_uid="G2", fuel="NG", unit_type="CT", pmax_mw="55.0"),
            _make_csv_row(gen_uid="G3", fuel="Wind", unit_type="WIND", pmax_mw="100.0"),
        ]
        _write_csv(gen_csv, _FULL_HEADER, rows)

        # Monkeypatch download to be a no-op since file exists.
        result = main(output_dir=tmp_path, commit_hash="test123")

        output_csv = tmp_path / "rts_gmlc_tech_classes.csv"
        assert output_csv.exists()
        assert output_csv.stat().st_size > 0
        assert gen_csv.exists()

        assert len(result.tech_classes) > 0
        assert result.provenance.commit_hash == "test123"


class TestNoNegativeParameters:
    """Test that no tech class has negative parameter values."""

    def test_reference_table_no_negative_parameters(self) -> None:
        """All TechClassRow fields are non-negative."""
        gens = [
            _make_generator(gen_uid="C1", fuel="Coal", unit_type="STEAM", pmax_mw=76.0),
            _make_generator(gen_uid="GCC1", fuel="NG", unit_type="CC", pmax_mw=355.0),
            _make_generator(gen_uid="W1", fuel="Wind", unit_type="WIND", pmax_mw=100.0),
        ]
        result = build_reference_table(gens)

        for tc in result.tech_classes:
            assert tc.ramp_rate_mw_per_min >= 0, f"{tc.tech_class}: negative ramp rate"
            assert tc.min_up_time_hr >= 0, f"{tc.tech_class}: negative min up time"
            assert tc.min_down_time_hr >= 0, f"{tc.tech_class}: negative min down time"
            assert tc.startup_time_cold_hr >= 0, f"{tc.tech_class}: negative startup time"
            assert tc.startup_cost_cold_dollar >= 0, f"{tc.tech_class}: negative startup cost"
            assert tc.shutdown_cost_dollar >= 0, f"{tc.tech_class}: negative shutdown cost"
