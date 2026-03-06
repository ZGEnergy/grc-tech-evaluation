"""Tests for bus/generator reconciliation (PRD 02).

All tests are self-contained: minimal .m file fixtures are defined as string
constants and written to tmp_path. No network calls, no reading from data/networks/.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.reconcile_bus_gen import (
    BusType,
    CheckResult,
    CheckStatus,
    CompanionBusInfo,
    MatpowerBusRecord,
    MatpowerCaseData,
    MatpowerGenRecord,
    NetworkReconciliation,
    ReconciliationNetworkId,
    ReconciliationReport,
    ReconciliationVerdict,
    check_bus_count,
    check_bus_id_sets,
    check_bus_types,
    check_generator_fuel_types,
    extract_companion_bus_ids,
    main,
    parse_matpower_buses,
    parse_matpower_case,
    parse_matpower_generators,
    reconcile_network,
    write_reconciliation_report,
)

# ---------------------------------------------------------------------------
# Minimal MATPOWER .m file fixtures
# ---------------------------------------------------------------------------

# 5-bus case WITH genfuel (2 PQ, 2 PV, 1 REF, 3 generators)
M_FILE_WITH_GENFUEL = """\
function mpc = case5
mpc.version = '2';
mpc.baseMVA = 100;

%% bus data
% bus_i type Pd    Qd   Gs Bs area Vm   Va  baseKV zone Vmax Vmin
mpc.bus = [
    1  3  0.0   0.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    2  2  20.0  10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
    3  1  45.0  15.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
    4  1  40.0  5.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    5  2  60.0  10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
];

%% generator data
% bus Pg   Qg  Qmax Qmin Vg  mBase status Pmax Pmin
mpc.gen = [
    1  40.0  0.0  30   -30  1.0  100  1  100  0;
    2  170.0 0.0  127  -127 1.0  100  1  300  0;
    5  50.0  0.0  40   -40  1.0  100  1  200  0;
];

mpc.genfuel = {
    'ng';
    'wind';
    'solar';
};
"""

# 3-bus case WITHOUT genfuel (1 PQ, 1 PV, 1 REF, 2 generators)
M_FILE_NO_GENFUEL = """\
function mpc = case3
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1  3  0.0  0.0  0  0  1  1.0  0.0  345  1  1.1  0.9;
    2  2  50.0 20.0 0  0  1  1.0  0.0  345  1  1.1  0.9;
    3  1  60.0 25.0 0  0  1  1.0  0.0  345  1  1.1  0.9;
];

mpc.gen = [
    1  100.0  0.0  50  -50  1.0  100  1  200  10;
    2  80.0   0.0  40  -40  1.0  100  1  150  5;
];
"""

# 4-bus case with TWO REF buses (invalid) for bus_types failure test
M_FILE_TWO_REF = """\
function mpc = case4_bad
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1  3  0.0  0.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    2  3  0.0  0.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    3  2  40.0 10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
    4  1  50.0 15.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
];

mpc.gen = [
    1  50.0  0.0  30  -30  1.0  100  1  100  0;
    2  60.0  0.0  30  -30  1.0  100  1  120  0;
    3  40.0  0.0  20  -20  1.0  100  1  80   0;
];
"""

# Mismatched genfuel case: generator on wind bus has fuel_type 'coal'
M_FILE_FUEL_MISMATCH = """\
function mpc = case3_fuel
mpc.version = '2';
mpc.baseMVA = 100;

mpc.bus = [
    1  3  0.0  0.0  0  0  1  1.0  0.0  230  1  1.1  0.9;
    2  2  20.0 10.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
    3  1  30.0 15.0 0  0  1  1.0  0.0  230  1  1.1  0.9;
];

mpc.gen = [
    1  50.0  0.0  30  -30  1.0  100  1  100  0;
    2  40.0  0.0  20  -20  1.0  100  1  80   0;
];

mpc.genfuel = {
    'ng';
    'coal';
};
"""


def _write_m_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write a .m file fixture and return its path."""
    p = tmp_path / name
    p.write_text(content)
    return p


def _make_manifest(
    tmp_path: Path,
    network_id: str,
    load_bus_ids: list[int],
    wind_bus_ids: list[int],
    solar_bus_ids: list[int],
) -> Path:
    """Create a minimal D1 download manifest JSON and return its path."""
    manifest = {
        "networks": [
            {
                "network_id": network_id,
                "download_url": "https://example.com",
                "download_timestamp": "2024-01-01T00:00:00+00:00",
                "raw_directory": str(tmp_path),
                "files": [
                    {
                        "file_name": f"{network_id}_load.csv",
                        "file_path": str(tmp_path / f"{network_id}_load.csv"),
                        "file_size_bytes": 1000,
                        "series_type": "load",
                        "num_rows": 100,
                        "num_columns": len(load_bus_ids) + 1,
                        "columns": [],
                        "temporal_resolution_minutes": 60,
                        "date_range_start": "2019-01-01",
                        "date_range_end": "2019-12-31",
                        "bus_ids": load_bus_ids,
                        "quirks": [],
                    },
                    {
                        "file_name": f"{network_id}_wind.csv",
                        "file_path": str(tmp_path / f"{network_id}_wind.csv"),
                        "file_size_bytes": 500,
                        "series_type": "wind",
                        "num_rows": 100,
                        "num_columns": len(wind_bus_ids) + 1,
                        "columns": [],
                        "temporal_resolution_minutes": 60,
                        "date_range_start": "2019-01-01",
                        "date_range_end": "2019-12-31",
                        "bus_ids": wind_bus_ids,
                        "quirks": [],
                    },
                    {
                        "file_name": f"{network_id}_solar.csv",
                        "file_path": str(tmp_path / f"{network_id}_solar.csv"),
                        "file_size_bytes": 500,
                        "series_type": "solar",
                        "num_rows": 100,
                        "num_columns": len(solar_bus_ids) + 1,
                        "columns": [],
                        "temporal_resolution_minutes": 60,
                        "date_range_start": "2019-01-01",
                        "date_range_end": "2019-12-31",
                        "bus_ids": solar_bus_ids,
                        "quirks": [],
                    },
                ],
                "total_size_bytes": 2000,
            }
        ],
        "script_version": "0.1.0",
        "python_version": "3.12.0",
        "generated_at": "2024-01-01T00:00:00+00:00",
    }
    p = tmp_path / "download_manifest.json"
    p.write_text(json.dumps(manifest, indent=2))
    return p


def _make_case_data(
    buses: list[MatpowerBusRecord],
    generators: list[MatpowerGenRecord],
    has_genfuel: bool = True,
) -> MatpowerCaseData:
    """Build a MatpowerCaseData from bus/gen lists."""
    return MatpowerCaseData(
        file_name="test.m",
        file_path="test.m",
        buses=buses,
        generators=generators,
        base_mva=100.0,
        has_genfuel=has_genfuel,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseBuses:
    def test_parse_buses_extracts_correct_count(self, tmp_path: Path) -> None:
        """Parse .m fixtures and verify bus counts (5, 3, 4)."""
        m5 = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        m3 = _write_m_file(tmp_path, "case3.m", M_FILE_NO_GENFUEL)
        m4 = _write_m_file(tmp_path, "case4.m", M_FILE_TWO_REF)

        assert len(parse_matpower_buses(m5)) == 5
        assert len(parse_matpower_buses(m3)) == 3
        assert len(parse_matpower_buses(m4)) == 4

    def test_parse_buses_extracts_bus_ids(self, tmp_path: Path) -> None:
        """Verify bus IDs include known values and have no duplicates."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        buses = parse_matpower_buses(m_path)
        bus_ids = [b.bus_id for b in buses]

        assert 1 in bus_ids
        assert 5 in bus_ids
        assert len(bus_ids) == len(set(bus_ids)), "Duplicate bus IDs found"

    def test_parse_buses_extracts_bus_types(self, tmp_path: Path) -> None:
        """Verify bus type distribution includes PQ, PV, and exactly one REF."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        buses = parse_matpower_buses(m_path)

        types = [b.bus_type for b in buses]
        assert BusType.PQ in types
        assert BusType.PV in types
        assert types.count(BusType.REF) == 1


class TestParseGenerators:
    def test_parse_generators_extracts_correct_count(self, tmp_path: Path) -> None:
        """Verify generator count matches rows in mpc.gen."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        gens = parse_matpower_generators(m_path)
        assert len(gens) == 3

    def test_parse_generators_includes_fuel_types(self, tmp_path: Path) -> None:
        """Verify non-None fuel_type for all generators when genfuel present."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        gens = parse_matpower_generators(m_path)

        for g in gens:
            assert g.fuel_type is not None, f"Generator on bus {g.gen_bus} has None fuel_type"

        fuel_types = {g.fuel_type for g in gens}
        assert "wind" in fuel_types
        assert "solar" in fuel_types
        assert "ng" in fuel_types

    def test_parse_generators_no_genfuel_returns_none(self, tmp_path: Path) -> None:
        """Verify fuel_type=None for all generators when genfuel absent."""
        m_path = _write_m_file(tmp_path, "case3.m", M_FILE_NO_GENFUEL)
        gens = parse_matpower_generators(m_path)

        for g in gens:
            assert g.fuel_type is None, f"Generator on bus {g.gen_bus} has fuel_type={g.fuel_type}"


class TestParseCase:
    def test_parse_matpower_case_combines_bus_and_gen(self, tmp_path: Path) -> None:
        """Verify parse_matpower_case returns consistent MatpowerCaseData."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        case = parse_matpower_case(m_path)

        assert case.has_genfuel is True
        assert len(case.buses) == 5
        assert len(case.generators) == 3
        assert case.base_mva == 100.0
        assert case.file_name == "case5.m"

        # Verify no-genfuel case
        m3 = _write_m_file(tmp_path, "case3.m", M_FILE_NO_GENFUEL)
        case3 = parse_matpower_case(m3)
        assert case3.has_genfuel is False
        assert len(case3.buses) == 3
        assert len(case3.generators) == 2


class TestExtractCompanionBusIds:
    def test_extract_companion_bus_ids_from_manifest(self, tmp_path: Path) -> None:
        """Given a fixture manifest, verify correct bus ID extraction."""
        manifest_path = _make_manifest(
            tmp_path,
            network_id="ACTIVSg2000",
            load_bus_ids=[1, 2, 3, 4],
            wind_bus_ids=[2],
            solar_bus_ids=[5],
        )

        info = extract_companion_bus_ids(manifest_path, ReconciliationNetworkId.ACTIVSG2000)

        assert info.load_bus_ids == {1, 2, 3, 4}
        assert info.wind_bus_ids == {2}
        assert info.solar_bus_ids == {5}
        assert info.all_bus_ids == {1, 2, 3, 4, 5}


class TestCheckBusCount:
    def test_check_bus_count_pass(self) -> None:
        """All companion bus IDs are a subset of .m bus IDs -> PASS."""
        buses = [
            MatpowerBusRecord(bus_id=i, bus_type=BusType.PQ, pd=0, qd=0, base_kv=230)
            for i in range(1, 6)
        ]
        case = _make_case_data(buses, [], has_genfuel=False)
        companion = CompanionBusInfo(
            load_bus_ids={1, 2, 3},
            wind_bus_ids={4},
            solar_bus_ids={5},
            all_bus_ids={1, 2, 3, 4, 5},
        )

        result = check_bus_count(case, companion)
        assert result.status == CheckStatus.PASS


class TestCheckBusIdSets:
    def test_check_bus_id_sets_detects_missing_ids(self) -> None:
        """Companion has bus ID 99 not in .m -> FAIL with missing ID listed."""
        buses = [
            MatpowerBusRecord(bus_id=i, bus_type=BusType.PQ, pd=0, qd=0, base_kv=230)
            for i in [1, 2, 3]
        ]
        case = _make_case_data(buses, [], has_genfuel=False)
        companion = CompanionBusInfo(
            load_bus_ids={1, 2, 99},
            wind_bus_ids=set(),
            solar_bus_ids=set(),
            all_bus_ids={1, 2, 99},
        )

        result = check_bus_id_sets(case, companion)
        assert result.status == CheckStatus.FAIL
        assert 99 in result.details["missing_from_m"]


class TestCheckBusTypes:
    def test_check_bus_types_validates_single_ref(self) -> None:
        """One REF bus + PV buses all have generators -> PASS."""
        buses = [
            MatpowerBusRecord(bus_id=1, bus_type=BusType.REF, pd=0, qd=0, base_kv=230),
            MatpowerBusRecord(bus_id=2, bus_type=BusType.PV, pd=20, qd=10, base_kv=230),
            MatpowerBusRecord(bus_id=3, bus_type=BusType.PQ, pd=30, qd=15, base_kv=230),
        ]
        gens = [
            MatpowerGenRecord(gen_bus=1, pg=50, qg=0, pmax=100, pmin=0, fuel_type="ng"),
            MatpowerGenRecord(gen_bus=2, pg=40, qg=0, pmax=80, pmin=0, fuel_type="wind"),
        ]
        case = _make_case_data(buses, gens)

        result = check_bus_types(case)
        assert result.status == CheckStatus.PASS


class TestCheckGeneratorFuelTypes:
    def test_check_generator_fuel_types_detects_mismatch(self) -> None:
        """Generator on wind bus has fuel_type='coal' -> FAIL."""
        buses = [
            MatpowerBusRecord(bus_id=1, bus_type=BusType.REF, pd=0, qd=0, base_kv=230),
            MatpowerBusRecord(bus_id=2, bus_type=BusType.PV, pd=20, qd=10, base_kv=230),
        ]
        gens = [
            MatpowerGenRecord(gen_bus=1, pg=50, qg=0, pmax=100, pmin=0, fuel_type="ng"),
            MatpowerGenRecord(gen_bus=2, pg=40, qg=0, pmax=80, pmin=0, fuel_type="coal"),
        ]
        case = _make_case_data(buses, gens, has_genfuel=True)
        companion = CompanionBusInfo(
            load_bus_ids={1},
            wind_bus_ids={2},
            solar_bus_ids=set(),
            all_bus_ids={1, 2},
        )

        result = check_generator_fuel_types(case, companion)
        assert result.status == CheckStatus.FAIL
        mismatches = result.details["mismatches"]
        assert len(mismatches) >= 1
        assert mismatches[0]["gen_bus"] == 2
        assert mismatches[0]["fuel_type"] == "coal"
        assert mismatches[0]["expected"] == "wind"

    def test_check_generator_fuel_types_na_without_genfuel(self) -> None:
        """has_genfuel=False -> NOT_APPLICABLE."""
        buses = [
            MatpowerBusRecord(bus_id=1, bus_type=BusType.REF, pd=0, qd=0, base_kv=230),
        ]
        gens = [
            MatpowerGenRecord(gen_bus=1, pg=50, qg=0, pmax=100, pmin=0, fuel_type=None),
        ]
        case = _make_case_data(buses, gens, has_genfuel=False)
        companion = CompanionBusInfo(
            load_bus_ids={1},
            wind_bus_ids=set(),
            solar_bus_ids=set(),
            all_bus_ids={1},
        )

        result = check_generator_fuel_types(case, companion)
        assert result.status == CheckStatus.NOT_APPLICABLE


class TestReconcileNetwork:
    def test_reconcile_network_case39_is_na(self, tmp_path: Path) -> None:
        """case39 -> NOT_APPLICABLE, empty checks, no replacement recommended."""
        m_path = _write_m_file(tmp_path, "case39.m", M_FILE_NO_GENFUEL)
        manifest_path = _make_manifest(tmp_path, "ACTIVSg2000", [1], [], [])

        result = reconcile_network(m_path, manifest_path, ReconciliationNetworkId.TINY)

        assert result.verdict == ReconciliationVerdict.NOT_APPLICABLE
        assert result.checks == []
        assert result.replacement_recommended is False

    def test_reconcile_network_aligned_verdict(self, tmp_path: Path) -> None:
        """Fully consistent .m + companion -> ALIGNED, no replacement."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        # Companion references buses that exist in the .m file,
        # wind bus 2 matches gen fuel 'wind', solar bus 5 matches 'solar'
        manifest_path = _make_manifest(
            tmp_path,
            network_id="ACTIVSg2000",
            load_bus_ids=[3, 4],
            wind_bus_ids=[2],
            solar_bus_ids=[5],
        )

        result = reconcile_network(m_path, manifest_path, ReconciliationNetworkId.ACTIVSG2000)

        assert result.verdict == ReconciliationVerdict.ALIGNED
        assert result.replacement_recommended is False
        assert len(result.checks) == 5

    def test_reconcile_network_mismatched_verdict(self, tmp_path: Path) -> None:
        """Companion has bus ID 99 not in .m -> MISMATCHED + replacement."""
        m_path = _write_m_file(tmp_path, "case5.m", M_FILE_WITH_GENFUEL)
        manifest_path = _make_manifest(
            tmp_path,
            network_id="ACTIVSg2000",
            load_bus_ids=[3, 4, 99],  # 99 not in .m
            wind_bus_ids=[2],
            solar_bus_ids=[5],
        )

        result = reconcile_network(m_path, manifest_path, ReconciliationNetworkId.ACTIVSG2000)

        assert result.verdict == ReconciliationVerdict.MISMATCHED
        assert result.replacement_recommended is True


class TestWriteReport:
    def test_write_reconciliation_report_roundtrip(self, tmp_path: Path) -> None:
        """Write report to JSON, read back, verify all fields survive."""
        check = CheckResult(
            check_name="bus_count",
            status=CheckStatus.PASS,
            description="5 buses match",
            details={"m_bus_count": 5, "companion_bus_count": 3, "overlap_count": 3},
        )
        net = NetworkReconciliation(
            network_id=ReconciliationNetworkId.ACTIVSG2000,
            m_file_path="data/networks/case_ACTIVSg2000.m",
            verdict=ReconciliationVerdict.ALIGNED,
            checks=[check],
            replacement_recommended=False,
            notes=["all good"],
        )
        report = ReconciliationReport(
            networks=[net],
            script_version="0.1.0",
            generated_at="2024-01-01T00:00:00+00:00",
            d1_manifest_path="data/timeseries/download_manifest.json",
        )

        dest = tmp_path / "report.json"
        write_reconciliation_report(report, dest)

        with open(dest) as fh:
            data = json.load(fh)

        assert data["script_version"] == "0.1.0"
        assert data["d1_manifest_path"] == "data/timeseries/download_manifest.json"
        assert len(data["networks"]) == 1

        net_data = data["networks"][0]
        assert net_data["network_id"] == "ACTIVSg2000"
        assert net_data["verdict"] == "aligned"
        assert net_data["replacement_recommended"] is False
        assert net_data["notes"] == ["all good"]

        check_data = net_data["checks"][0]
        assert check_data["check_name"] == "bus_count"
        assert check_data["status"] == "pass"
        assert check_data["details"]["m_bus_count"] == 5


class TestMain:
    def test_main_produces_report_for_all_three_networks(self, tmp_path: Path) -> None:
        """main() with fixture data returns report with 3 network entries."""
        # Set up networks dir with .m files
        networks_dir = tmp_path / "networks"
        networks_dir.mkdir()
        _write_m_file(networks_dir, "case_ACTIVSg2000.m", M_FILE_WITH_GENFUEL)
        _write_m_file(networks_dir, "case_ACTIVSg10k.m", M_FILE_WITH_GENFUEL)
        _write_m_file(networks_dir, "case39.m", M_FILE_NO_GENFUEL)

        # Create manifest with entries for both ACTIVSg networks
        manifest = {
            "networks": [
                {
                    "network_id": "ACTIVSg2000",
                    "download_url": "https://example.com",
                    "download_timestamp": "2024-01-01T00:00:00+00:00",
                    "raw_directory": str(tmp_path),
                    "files": [
                        {
                            "file_name": "ACTIVSg2000_load.csv",
                            "file_path": "load.csv",
                            "file_size_bytes": 100,
                            "series_type": "load",
                            "num_rows": 10,
                            "num_columns": 3,
                            "columns": [],
                            "temporal_resolution_minutes": 60,
                            "date_range_start": "2019-01-01",
                            "date_range_end": "2019-12-31",
                            "bus_ids": [3, 4],
                            "quirks": [],
                        },
                        {
                            "file_name": "ACTIVSg2000_wind.csv",
                            "file_path": "wind.csv",
                            "file_size_bytes": 100,
                            "series_type": "wind",
                            "num_rows": 10,
                            "num_columns": 2,
                            "columns": [],
                            "temporal_resolution_minutes": 60,
                            "date_range_start": "2019-01-01",
                            "date_range_end": "2019-12-31",
                            "bus_ids": [2],
                            "quirks": [],
                        },
                        {
                            "file_name": "ACTIVSg2000_solar.csv",
                            "file_path": "solar.csv",
                            "file_size_bytes": 100,
                            "series_type": "solar",
                            "num_rows": 10,
                            "num_columns": 2,
                            "columns": [],
                            "temporal_resolution_minutes": 60,
                            "date_range_start": "2019-01-01",
                            "date_range_end": "2019-12-31",
                            "bus_ids": [5],
                            "quirks": [],
                        },
                    ],
                    "total_size_bytes": 300,
                },
                {
                    "network_id": "ACTIVSg10k",
                    "download_url": "https://example.com",
                    "download_timestamp": "2024-01-01T00:00:00+00:00",
                    "raw_directory": str(tmp_path),
                    "files": [
                        {
                            "file_name": "ACTIVSg10k_load.csv",
                            "file_path": "load.csv",
                            "file_size_bytes": 100,
                            "series_type": "load",
                            "num_rows": 10,
                            "num_columns": 3,
                            "columns": [],
                            "temporal_resolution_minutes": 60,
                            "date_range_start": "2019-01-01",
                            "date_range_end": "2019-12-31",
                            "bus_ids": [3, 4],
                            "quirks": [],
                        },
                        {
                            "file_name": "ACTIVSg10k_wind.csv",
                            "file_path": "wind.csv",
                            "file_size_bytes": 100,
                            "series_type": "wind",
                            "num_rows": 10,
                            "num_columns": 2,
                            "columns": [],
                            "temporal_resolution_minutes": 60,
                            "date_range_start": "2019-01-01",
                            "date_range_end": "2019-12-31",
                            "bus_ids": [2],
                            "quirks": [],
                        },
                        {
                            "file_name": "ACTIVSg10k_solar.csv",
                            "file_path": "solar.csv",
                            "file_size_bytes": 100,
                            "series_type": "solar",
                            "num_rows": 10,
                            "num_columns": 2,
                            "columns": [],
                            "temporal_resolution_minutes": 60,
                            "date_range_start": "2019-01-01",
                            "date_range_end": "2019-12-31",
                            "bus_ids": [5],
                            "quirks": [],
                        },
                    ],
                    "total_size_bytes": 300,
                },
            ],
            "script_version": "0.1.0",
            "python_version": "3.12.0",
            "generated_at": "2024-01-01T00:00:00+00:00",
        }

        manifest_path = tmp_path / "download_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        output_path = tmp_path / "reconciliation_report.json"

        report = main(
            networks_dir=networks_dir,
            manifest_path=manifest_path,
            output_path=output_path,
        )

        assert len(report.networks) == 3
        network_ids = {n.network_id for n in report.networks}
        assert ReconciliationNetworkId.ACTIVSG2000 in network_ids
        assert ReconciliationNetworkId.ACTIVSG10K in network_ids
        assert ReconciliationNetworkId.TINY in network_ids

        # Verify report file was written
        assert output_path.exists()
