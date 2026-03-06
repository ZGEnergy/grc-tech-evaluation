"""Tests for snapshot_cleanup.py — Snapshot Cleanup Script & Manifest.

All tests use self-contained .m file fixtures as strings. No reading of
actual data/networks/ files.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from scripts.reconcile_bus_gen import (
    BusType,
    MatpowerBusRecord,
    MatpowerCaseData,
    MatpowerGenRecord,
    parse_matpower_case,
)
from scripts.snapshot_cleanup import (
    HYDRO_RESERVOIR_PMIN_FRACTION,
    HYDRO_THRESHOLD_MW,
    BusCleanupRule,
    BusModification,
    CleanupManifest,
    CleanupNetworkId,
    CleanupRule,
    FuelCategory,
    FuelClassificationSource,
    FuelTypeSummary,
    GeneratorClassification,
    GeneratorModification,
    NetworkCleanupManifest,
    RuleSummary,
    apply_generator_cleanup,
    build_cleanup_manifest,
    build_network_manifest,
    classify_generators,
    classify_genfuel_string,
    compute_bus_modifications,
    main,
    write_cleanup_manifest,
    write_matpower_case,
)

# ---------------------------------------------------------------------------
# Minimal .m file fixtures
# ---------------------------------------------------------------------------

MINIMAL_CASE_M = textwrap.dedent("""\
    function mpc = case_test
    mpc.version = '2';
    mpc.baseMVA = 100;

    %% bus data
    mpc.bus = [
        1\t3\t50\t20\t0\t0\t1\t1.05\t-5.0\t138\t1\t1.1\t0.9;
        2\t2\t30\t10\t0\t0\t1\t1.02\t-3.0\t138\t1\t1.1\t0.9;
        3\t1\t20\t5\t0\t0\t1\t0.98\t-2.0\t138\t1\t1.1\t0.9;
    ];

    %% generator data
    mpc.gen = [
        1\t100\t20\t50\t-20\t1.05\t100\t1\t200\t100;
        2\t50\t10\t30\t-10\t1.02\t100\t1\t80\t50;
        3\t30\t5\t20\t-5\t0.98\t100\t1\t60\t30;
    ];

    %% branch data
    mpc.branch = [
        1\t2\t0.01\t0.1\t0.02\t100\t100\t100\t0\t0\t1\t-360\t360;
        2\t3\t0.02\t0.2\t0.04\t100\t100\t100\t0\t0\t1\t-360\t360;
    ];

    %% gencost
    mpc.gencost = [
        2\t0\t0\t3\t0.02\t2\t0;
        2\t0\t0\t3\t0.03\t3\t0;
        2\t0\t0\t3\t0.04\t4\t0;
    ];
    """)

MINIMAL_CASE_WITH_GENFUEL_M = textwrap.dedent("""\
    function mpc = case_test_fuel
    mpc.version = '2';
    mpc.baseMVA = 100;

    %% bus data
    mpc.bus = [
        1\t3\t50\t20\t0\t0\t1\t1.05\t-5.0\t138\t1\t1.1\t0.9;
        2\t2\t30\t10\t0\t0\t1\t1.02\t-3.0\t138\t1\t1.1\t0.9;
        3\t1\t20\t5\t0\t0\t1\t0.98\t-2.0\t138\t1\t1.1\t0.9;
        4\t1\t10\t3\t0\t0\t1\t1.01\t-1.0\t138\t1\t1.1\t0.9;
        5\t2\t15\t4\t0\t0\t1\t0.99\t-4.0\t138\t1\t1.1\t0.9;
        6\t1\t5\t2\t0\t0\t1\t1.03\t-0.5\t138\t1\t1.1\t0.9;
        7\t2\t25\t8\t0\t0\t1\t1.0\t0.0\t138\t1\t1.1\t0.9;
    ];

    %% generator data
    %% bus Pg  Qg  Qmax Qmin Vg   mBase status Pmax Pmin
    mpc.gen = [
        1\t100\t20\t50\t-20\t1.05\t100\t1\t200\t100;
        2\t50\t10\t30\t-10\t1.02\t100\t1\t80\t80;
        3\t30\t5\t20\t-5\t0.98\t100\t1\t60\t60;
        4\t10\t2\t10\t-5\t1.01\t100\t1\t20\t20;
        5\t40\t8\t25\t-15\t0.99\t100\t1\t100\t50;
        6\t5\t1\t5\t-2\t1.03\t100\t1\t10\t5;
        7\t0\t0\t10\t-5\t1.0\t100\t1\t50\t0;
    ];

    %% branch data
    mpc.branch = [
        1\t2\t0.01\t0.1\t0.02\t100\t100\t100\t0\t0\t1\t-360\t360;
        2\t3\t0.02\t0.2\t0.04\t100\t100\t100\t0\t0\t1\t-360\t360;
    ];

    %% generator fuel type
    mpc.genfuel = {
        'ng';
        'wind';
        'solar';
        'hydro';
        'hydro';
        'coal';
        'nuclear';
    };
    """)


def _make_case_data(
    generators: list[MatpowerGenRecord],
    buses: list[MatpowerBusRecord] | None = None,
    has_genfuel: bool = False,
) -> MatpowerCaseData:
    """Create a minimal MatpowerCaseData for testing."""
    if buses is None:
        bus_ids = {g.gen_bus for g in generators}
        buses = [
            MatpowerBusRecord(
                bus_id=bid,
                bus_type=BusType.PQ,
                pd=10.0,
                qd=5.0,
                base_kv=138.0,
            )
            for bid in sorted(bus_ids)
        ]
    return MatpowerCaseData(
        file_name="test_case.m",
        file_path="test_case.m",
        buses=buses,
        generators=generators,
        base_mva=100.0,
        has_genfuel=has_genfuel,
    )


def _make_gen(
    bus: int = 1,
    pg: float = 100.0,
    qg: float = 20.0,
    pmax: float = 200.0,
    pmin: float = 100.0,
    fuel_type: str | None = None,
) -> MatpowerGenRecord:
    return MatpowerGenRecord(gen_bus=bus, pg=pg, qg=qg, pmax=pmax, pmin=pmin, fuel_type=fuel_type)


def _make_classification(
    gen_index: int = 0,
    gen_bus: int = 1,
    fuel_category: FuelCategory = FuelCategory.NG,
    fuel_type_raw: str | None = "ng",
    source: FuelClassificationSource = FuelClassificationSource.GENFUEL_FIELD,
    pmax: float = 200.0,
    hydro_subclass: str | None = None,
) -> GeneratorClassification:
    return GeneratorClassification(
        gen_index=gen_index,
        gen_bus=gen_bus,
        fuel_type_raw=fuel_type_raw,
        fuel_category=fuel_category,
        classification_source=source,
        pmax=pmax,
        hydro_subclass=hydro_subclass,
    )


# ---------------------------------------------------------------------------
# Test 1: classify_genfuel_string — standard labels
# ---------------------------------------------------------------------------


class TestClassifyGenfuelStandardLabels:
    def test_wind(self) -> None:
        assert classify_genfuel_string("wind") == FuelCategory.WIND

    def test_solar(self) -> None:
        assert classify_genfuel_string("solar") == FuelCategory.SOLAR

    def test_hydro(self) -> None:
        assert classify_genfuel_string("hydro") == FuelCategory.HYDRO

    def test_ng(self) -> None:
        assert classify_genfuel_string("ng") == FuelCategory.NG

    def test_coal(self) -> None:
        assert classify_genfuel_string("coal") == FuelCategory.COAL

    def test_nuclear(self) -> None:
        assert classify_genfuel_string("nuclear") == FuelCategory.NUCLEAR

    def test_case_insensitive(self) -> None:
        assert classify_genfuel_string("Wind") == FuelCategory.WIND
        assert classify_genfuel_string("SOLAR") == FuelCategory.SOLAR
        assert classify_genfuel_string("  Hydro  ") == FuelCategory.HYDRO


# ---------------------------------------------------------------------------
# Test 2: classify_genfuel_string — non-standard labels
# ---------------------------------------------------------------------------


class TestClassifyGenfuelNonstandardLabels:
    def test_van_horn(self) -> None:
        assert classify_genfuel_string("VAN HORN 0") == FuelCategory.UNKNOWN

    def test_presidio(self) -> None:
        assert classify_genfuel_string("PRESIDIO 2 0") == FuelCategory.UNKNOWN

    def test_westport(self) -> None:
        assert classify_genfuel_string("WESTPORT 2") == FuelCategory.UNKNOWN

    def test_neah_bay(self) -> None:
        assert classify_genfuel_string("NEAH BAY 1") == FuelCategory.UNKNOWN

    def test_big_spring(self) -> None:
        assert classify_genfuel_string("BIG SPRING 5 1") == FuelCategory.UNKNOWN

    def test_empty_string(self) -> None:
        assert classify_genfuel_string("") == FuelCategory.UNKNOWN


# ---------------------------------------------------------------------------
# Test 3: classify_generators — ACTIVSg uses genfuel field
# ---------------------------------------------------------------------------


class TestClassifyGeneratorsACTIVSg:
    def test_uses_genfuel_source(self) -> None:
        """Verify classifications sourced from GENFUEL_FIELD."""
        gens = [
            _make_gen(bus=1, pmax=100, fuel_type="ng"),
            _make_gen(bus=2, pmax=50, fuel_type="wind"),
            _make_gen(bus=3, pmax=30, fuel_type="solar"),
            _make_gen(bus=4, pmax=200, fuel_type="coal"),
            _make_gen(bus=5, pmax=80, fuel_type="hydro"),
            _make_gen(bus=6, pmax=500, fuel_type="nuclear"),
            _make_gen(bus=7, pmax=10, fuel_type="VAN HORN 0"),
        ]
        case_data = _make_case_data(gens, has_genfuel=True)
        classifications = classify_generators(case_data, CleanupNetworkId.SMALL)

        assert len(classifications) == 7
        for cls in classifications:
            assert cls.classification_source == FuelClassificationSource.GENFUEL_FIELD

        cats = [c.fuel_category for c in classifications]
        assert cats.count(FuelCategory.NG) == 1
        assert cats.count(FuelCategory.WIND) == 1
        assert cats.count(FuelCategory.SOLAR) == 1
        assert cats.count(FuelCategory.COAL) == 1
        assert cats.count(FuelCategory.HYDRO) == 1
        assert cats.count(FuelCategory.NUCLEAR) == 1
        assert cats.count(FuelCategory.UNKNOWN) == 1


# ---------------------------------------------------------------------------
# Test 4: classify_generators — case39 uses header map
# ---------------------------------------------------------------------------


class TestClassifyGeneratorsCase39:
    def test_uses_header_map(self) -> None:
        """Verify case39 uses CASE39_HEADER_MAP source for all 10 generators."""
        gens = [
            _make_gen(bus=30, pmax=1040),  # hydro
            _make_gen(bus=31, pmax=646),  # nuclear
            _make_gen(bus=32, pmax=725),  # nuclear
            _make_gen(bus=33, pmax=652),  # ng
            _make_gen(bus=34, pmax=508),  # ng
            _make_gen(bus=35, pmax=687),  # nuclear
            _make_gen(bus=36, pmax=580),  # ng
            _make_gen(bus=37, pmax=564),  # nuclear
            _make_gen(bus=38, pmax=865),  # nuclear
            _make_gen(bus=39, pmax=1100),  # ng
        ]
        case_data = _make_case_data(gens)
        classifications = classify_generators(case_data, CleanupNetworkId.TINY)

        assert len(classifications) == 10
        for cls in classifications:
            assert cls.classification_source == FuelClassificationSource.CASE39_HEADER_MAP

        cats = [c.fuel_category for c in classifications]
        assert cats.count(FuelCategory.HYDRO) == 1
        assert cats.count(FuelCategory.NUCLEAR) == 5
        assert cats.count(FuelCategory.NG) == 4


# ---------------------------------------------------------------------------
# Test 5: classify_generators — hydro subclass
# ---------------------------------------------------------------------------


class TestClassifyGeneratorsHydroSubclass:
    def test_run_of_river_below_threshold(self) -> None:
        """Hydro with Pmax < 30 MW -> run_of_river."""
        gens = [_make_gen(bus=1, pmax=20, fuel_type="hydro")]
        case_data = _make_case_data(gens, has_genfuel=True)
        classifications = classify_generators(case_data, CleanupNetworkId.SMALL)
        assert classifications[0].hydro_subclass == "run_of_river"

    def test_reservoir_at_threshold(self) -> None:
        """Hydro with Pmax == 30 MW -> reservoir."""
        gens = [_make_gen(bus=1, pmax=30, fuel_type="hydro")]
        case_data = _make_case_data(gens, has_genfuel=True)
        classifications = classify_generators(case_data, CleanupNetworkId.SMALL)
        assert classifications[0].hydro_subclass == "reservoir"

    def test_reservoir_above_threshold(self) -> None:
        """Hydro with Pmax > 30 MW -> reservoir."""
        gens = [_make_gen(bus=1, pmax=100, fuel_type="hydro")]
        case_data = _make_case_data(gens, has_genfuel=True)
        classifications = classify_generators(case_data, CleanupNetworkId.SMALL)
        assert classifications[0].hydro_subclass == "reservoir"

    def test_non_hydro_has_no_subclass(self) -> None:
        """Non-hydro generators have hydro_subclass=None."""
        gens = [_make_gen(bus=1, pmax=100, fuel_type="wind")]
        case_data = _make_case_data(gens, has_genfuel=True)
        classifications = classify_generators(case_data, CleanupNetworkId.SMALL)
        assert classifications[0].hydro_subclass is None


# ---------------------------------------------------------------------------
# Test 6: renewable Pmin reset
# ---------------------------------------------------------------------------


class TestRenewablePminReset:
    def test_wind_pmin_reset(self) -> None:
        """Wind generator with Pmin=Pmax has Pmin set to 0."""
        gens = [_make_gen(bus=1, pg=50, qg=5, pmax=50, pmin=50, fuel_type="wind")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [
            _make_classification(
                fuel_category=FuelCategory.WIND,
                fuel_type_raw="wind",
                pmax=50,
            )
        ]
        cleaned, mods = apply_generator_cleanup(case_data, cls)
        assert cleaned[0].pmin == 0.0
        pmin_mods = [m for m in mods if m.rule == CleanupRule.RENEWABLE_PMIN_RESET]
        assert len(pmin_mods) == 1
        assert pmin_mods[0].field_name == "Pmin"
        assert pmin_mods[0].before_value == 50.0
        assert pmin_mods[0].after_value == 0.0

    def test_solar_pmin_reset(self) -> None:
        """Solar generator with Pmin=Pmax has Pmin set to 0."""
        gens = [_make_gen(bus=2, pg=30, qg=2, pmax=30, pmin=30, fuel_type="solar")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [
            _make_classification(
                fuel_category=FuelCategory.SOLAR,
                fuel_type_raw="solar",
                pmax=30,
            )
        ]
        cleaned, mods = apply_generator_cleanup(case_data, cls)
        assert cleaned[0].pmin == 0.0
        pmin_mods = [m for m in mods if m.rule == CleanupRule.RENEWABLE_PMIN_RESET]
        assert len(pmin_mods) == 1


# ---------------------------------------------------------------------------
# Test 7: hydro run-of-river Pmin
# ---------------------------------------------------------------------------


class TestHydroRunOfRiverPmin:
    def test_below_threshold(self) -> None:
        """Hydro Pmax=20 MW (< 30) -> Pmin set to 0."""
        gens = [_make_gen(bus=1, pg=15, qg=3, pmax=20, pmin=10, fuel_type="hydro")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [
            _make_classification(
                fuel_category=FuelCategory.HYDRO,
                fuel_type_raw="hydro",
                pmax=20,
                hydro_subclass="run_of_river",
            )
        ]
        cleaned, mods = apply_generator_cleanup(case_data, cls)
        assert cleaned[0].pmin == 0.0
        pmin_mods = [m for m in mods if m.rule == CleanupRule.HYDRO_RUN_OF_RIVER_PMIN]
        assert len(pmin_mods) == 1
        assert pmin_mods[0].before_value == 10.0
        assert pmin_mods[0].after_value == 0.0


# ---------------------------------------------------------------------------
# Test 8: hydro reservoir Pmin
# ---------------------------------------------------------------------------


class TestHydroReservoirPmin:
    def test_above_threshold(self) -> None:
        """Hydro Pmax=100 MW (>= 30) -> Pmin set to 25% of Pmax = 25."""
        gens = [_make_gen(bus=1, pg=80, qg=10, pmax=100, pmin=80, fuel_type="hydro")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [
            _make_classification(
                fuel_category=FuelCategory.HYDRO,
                fuel_type_raw="hydro",
                pmax=100,
                hydro_subclass="reservoir",
            )
        ]
        cleaned, mods = apply_generator_cleanup(case_data, cls)
        assert cleaned[0].pmin == 25.0
        pmin_mods = [m for m in mods if m.rule == CleanupRule.HYDRO_RESERVOIR_PMIN]
        assert len(pmin_mods) == 1
        assert pmin_mods[0].before_value == 80.0
        assert pmin_mods[0].after_value == 25.0


# ---------------------------------------------------------------------------
# Test 9: thermal Pmin preserved
# ---------------------------------------------------------------------------


class TestThermalPminPreserved:
    def test_ng_pmin_unchanged(self) -> None:
        """NG generator Pmin is not modified."""
        gens = [_make_gen(bus=1, pg=100, qg=20, pmax=200, pmin=50, fuel_type="ng")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [_make_classification(fuel_category=FuelCategory.NG, fuel_type_raw="ng", pmax=200)]
        cleaned, mods = apply_generator_cleanup(case_data, cls)
        assert cleaned[0].pmin == 50.0
        pmin_mods = [m for m in mods if m.field_name == "Pmin"]
        assert len(pmin_mods) == 0

    def test_coal_pmin_unchanged(self) -> None:
        """Coal generator Pmin is not modified."""
        gens = [_make_gen(bus=2, pg=150, qg=30, pmax=300, pmin=100, fuel_type="coal")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [
            _make_classification(
                gen_bus=2, fuel_category=FuelCategory.COAL, fuel_type_raw="coal", pmax=300
            )
        ]
        cleaned, mods = apply_generator_cleanup(case_data, cls)
        assert cleaned[0].pmin == 100.0
        pmin_mods = [m for m in mods if m.field_name == "Pmin"]
        assert len(pmin_mods) == 0


# ---------------------------------------------------------------------------
# Test 10: Pg/Qg reset all generators
# ---------------------------------------------------------------------------


class TestPgQgResetAllGenerators:
    def test_all_pg_qg_zeroed(self) -> None:
        """All generators have Pg=0 and Qg=0 after cleanup."""
        gens = [
            _make_gen(bus=1, pg=100, qg=20, pmax=200, pmin=50, fuel_type="ng"),
            _make_gen(bus=2, pg=50, qg=10, pmax=80, pmin=80, fuel_type="wind"),
            _make_gen(bus=3, pg=30, qg=5, pmax=60, pmin=30, fuel_type="coal"),
        ]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [
            _make_classification(
                gen_index=0,
                gen_bus=1,
                fuel_category=FuelCategory.NG,
                fuel_type_raw="ng",
                pmax=200,
            ),
            _make_classification(
                gen_index=1,
                gen_bus=2,
                fuel_category=FuelCategory.WIND,
                fuel_type_raw="wind",
                pmax=80,
            ),
            _make_classification(
                gen_index=2,
                gen_bus=3,
                fuel_category=FuelCategory.COAL,
                fuel_type_raw="coal",
                pmax=60,
            ),
        ]
        cleaned, mods = apply_generator_cleanup(case_data, cls)

        for g in cleaned:
            assert g.pg == 0.0
            assert g.qg == 0.0

        pg_mods = [m for m in mods if m.rule == CleanupRule.PG_RESET]
        qg_mods = [m for m in mods if m.rule == CleanupRule.QG_RESET]
        assert len(pg_mods) == 3  # all had nonzero Pg
        assert len(qg_mods) == 3  # all had nonzero Qg


# ---------------------------------------------------------------------------
# Test 11: bus Vm/Va normalization
# ---------------------------------------------------------------------------


class TestBusVmVaNormalization:
    def test_vm_va_modifications_recorded(self) -> None:
        """Bus modifications recorded for Vm != 1.0 and Va != 0.0."""
        buses = [
            MatpowerBusRecord(bus_id=1, bus_type=BusType.REF, pd=50, qd=20, base_kv=138),
            MatpowerBusRecord(bus_id=2, bus_type=BusType.PV, pd=30, qd=10, base_kv=138),
            MatpowerBusRecord(bus_id=3, bus_type=BusType.PQ, pd=20, qd=5, base_kv=138),
        ]
        case_data = _make_case_data(
            generators=[_make_gen(bus=1)],
            buses=buses,
        )

        m_text = textwrap.dedent("""\
            mpc.bus = [
                1\t3\t50\t20\t0\t0\t1\t1.05\t-5.0\t138\t1\t1.1\t0.9;
                2\t2\t30\t10\t0\t0\t1\t1.02\t-3.0\t138\t1\t1.1\t0.9;
                3\t1\t20\t5\t0\t0\t1\t0.98\t-2.0\t138\t1\t1.1\t0.9;
            ];
        """)

        bus_mods = compute_bus_modifications(case_data, m_text)

        vm_mods = [m for m in bus_mods if m.rule == BusCleanupRule.VM_NORMALIZE]
        va_mods = [m for m in bus_mods if m.rule == BusCleanupRule.VA_NORMALIZE]

        # All 3 buses have non-flat Vm
        assert len(vm_mods) == 3
        # All 3 buses have non-zero Va
        assert len(va_mods) == 3

        # Check specific values
        assert vm_mods[0].before_value == 1.05
        assert vm_mods[0].after_value == 1.0
        assert va_mods[0].before_value == -5.0
        assert va_mods[0].after_value == 0.0


# ---------------------------------------------------------------------------
# Test 12: no-op modifications not logged
# ---------------------------------------------------------------------------


class TestNoOpModificationsNotLogged:
    def test_pg_zero_not_logged(self) -> None:
        """Generator with Pg=0 creates no PG_RESET modification."""
        gens = [_make_gen(bus=1, pg=0, qg=0, pmax=200, pmin=50, fuel_type="ng")]
        case_data = _make_case_data(gens, has_genfuel=True)
        cls = [_make_classification(fuel_category=FuelCategory.NG, fuel_type_raw="ng", pmax=200)]
        _, mods = apply_generator_cleanup(case_data, cls)
        pg_mods = [m for m in mods if m.rule == CleanupRule.PG_RESET]
        qg_mods = [m for m in mods if m.rule == CleanupRule.QG_RESET]
        assert len(pg_mods) == 0
        assert len(qg_mods) == 0

    def test_bus_vm_one_not_logged(self) -> None:
        """Bus with Vm=1.0 creates no VM_NORMALIZE modification."""
        buses = [
            MatpowerBusRecord(bus_id=1, bus_type=BusType.PQ, pd=10, qd=5, base_kv=138),
        ]
        case_data = _make_case_data(generators=[_make_gen(bus=1)], buses=buses)

        m_text = textwrap.dedent("""\
            mpc.bus = [
                1\t1\t10\t5\t0\t0\t1\t1.0\t0.0\t138\t1\t1.1\t0.9;
            ];
        """)

        bus_mods = compute_bus_modifications(case_data, m_text)
        assert len(bus_mods) == 0


# ---------------------------------------------------------------------------
# Test 13: write_matpower_case preserves sections
# ---------------------------------------------------------------------------


class TestWriteMatpowerCasePreservesSections:
    def test_branch_gencost_preserved(self, tmp_path: Path) -> None:
        """Non-modified sections (branch, gencost) are preserved in output."""
        source_path = tmp_path / "source.m"
        source_path.write_text(MINIMAL_CASE_M)
        dest_path = tmp_path / "output" / "cleaned.m"

        case_data = parse_matpower_case(source_path)

        # Create cleaned generators (all Pg/Qg zeroed)
        cleaned_gens = [
            MatpowerGenRecord(
                gen_bus=g.gen_bus,
                pg=0.0,
                qg=0.0,
                pmax=g.pmax,
                pmin=g.pmin,
                fuel_type=g.fuel_type,
            )
            for g in case_data.generators
        ]
        cleaned_buses = list(case_data.buses)

        write_matpower_case(source_path, dest_path, cleaned_buses, cleaned_gens)

        assert dest_path.exists()
        output_text = dest_path.read_text()

        # Branch data should be preserved
        assert "mpc.branch" in output_text

        # gencost should be preserved
        assert "mpc.gencost" in output_text

    def test_genfuel_preserved(self, tmp_path: Path) -> None:
        """genfuel section is preserved in output."""
        source_path = tmp_path / "source.m"
        source_path.write_text(MINIMAL_CASE_WITH_GENFUEL_M)
        dest_path = tmp_path / "output" / "cleaned.m"

        case_data = parse_matpower_case(source_path)

        cleaned_gens = [
            MatpowerGenRecord(
                gen_bus=g.gen_bus,
                pg=0.0,
                qg=0.0,
                pmax=g.pmax,
                pmin=g.pmin,
                fuel_type=g.fuel_type,
            )
            for g in case_data.generators
        ]
        cleaned_buses = list(case_data.buses)

        write_matpower_case(source_path, dest_path, cleaned_buses, cleaned_gens)

        output_text = dest_path.read_text()
        assert "mpc.genfuel" in output_text
        assert "'ng'" in output_text
        assert "'wind'" in output_text
        assert "'solar'" in output_text


# ---------------------------------------------------------------------------
# Test 14: write_matpower_case — valid format (re-parseable)
# ---------------------------------------------------------------------------


class TestWriteMatpowerCaseValidFormat:
    def test_reparseable(self, tmp_path: Path) -> None:
        """Cleaned file can be re-parsed by parse_matpower_case."""
        source_path = tmp_path / "source.m"
        source_path.write_text(MINIMAL_CASE_M)
        dest_path = tmp_path / "output" / "cleaned.m"

        case_data = parse_matpower_case(source_path)

        cleaned_gens = [
            MatpowerGenRecord(
                gen_bus=g.gen_bus,
                pg=0.0,
                qg=0.0,
                pmax=g.pmax,
                pmin=0.0,
                fuel_type=g.fuel_type,
            )
            for g in case_data.generators
        ]
        cleaned_buses = list(case_data.buses)

        write_matpower_case(source_path, dest_path, cleaned_buses, cleaned_gens)

        # Re-parse the cleaned file
        reparsed = parse_matpower_case(dest_path)
        assert len(reparsed.buses) == len(case_data.buses)
        assert len(reparsed.generators) == len(case_data.generators)

        # Verify cleaned values
        for g in reparsed.generators:
            assert g.pg == 0.0
            assert g.qg == 0.0
            assert g.pmin == 0.0


# ---------------------------------------------------------------------------
# Test 15: manifest fuel type summary
# ---------------------------------------------------------------------------


class TestManifestFuelTypeSummary:
    def test_fuel_counts_and_pmax(self) -> None:
        """Fuel type summary has correct counts and Pmax totals."""
        classifications = [
            _make_classification(gen_index=0, fuel_category=FuelCategory.NG, pmax=200),
            _make_classification(gen_index=1, fuel_category=FuelCategory.NG, pmax=150),
            _make_classification(gen_index=2, fuel_category=FuelCategory.WIND, pmax=80),
            _make_classification(gen_index=3, fuel_category=FuelCategory.SOLAR, pmax=50),
        ]

        gens = [
            _make_gen(bus=1, pmax=200, fuel_type="ng"),
            _make_gen(bus=2, pmax=150, fuel_type="ng"),
            _make_gen(bus=3, pmax=80, fuel_type="wind"),
            _make_gen(bus=4, pmax=50, fuel_type="solar"),
        ]
        case_data = _make_case_data(gens, has_genfuel=True)

        manifest = build_network_manifest(
            network_id=CleanupNetworkId.SMALL,
            source_path=Path("data/networks/test.m"),
            dest_path=Path("data/timeseries/test/test.m"),
            case_data=case_data,
            classifications=classifications,
            gen_modifications=[],
            bus_modifications=[],
        )

        summary_by_cat = {s.category: s for s in manifest.fuel_type_summary}
        assert summary_by_cat[FuelCategory.NG].count == 2
        assert summary_by_cat[FuelCategory.NG].pmax_total_mw == 350.0
        assert summary_by_cat[FuelCategory.WIND].count == 1
        assert summary_by_cat[FuelCategory.WIND].pmax_total_mw == 80.0
        assert summary_by_cat[FuelCategory.SOLAR].count == 1
        assert summary_by_cat[FuelCategory.SOLAR].pmax_total_mw == 50.0


# ---------------------------------------------------------------------------
# Test 16: manifest rule summary
# ---------------------------------------------------------------------------


class TestManifestRuleSummary:
    def test_rule_counts(self) -> None:
        """Rule summary correctly counts modifications per rule."""
        gen_mods = [
            GeneratorModification(
                gen_index=0,
                gen_bus=1,
                fuel_type_raw="wind",
                fuel_category=FuelCategory.WIND,
                classification_source=FuelClassificationSource.GENFUEL_FIELD,
                rule=CleanupRule.RENEWABLE_PMIN_RESET,
                field_name="Pmin",
                before_value=50.0,
                after_value=0.0,
            ),
            GeneratorModification(
                gen_index=0,
                gen_bus=1,
                fuel_type_raw="wind",
                fuel_category=FuelCategory.WIND,
                classification_source=FuelClassificationSource.GENFUEL_FIELD,
                rule=CleanupRule.PG_RESET,
                field_name="Pg",
                before_value=50.0,
                after_value=0.0,
            ),
            GeneratorModification(
                gen_index=1,
                gen_bus=2,
                fuel_type_raw="ng",
                fuel_category=FuelCategory.NG,
                classification_source=FuelClassificationSource.GENFUEL_FIELD,
                rule=CleanupRule.PG_RESET,
                field_name="Pg",
                before_value=100.0,
                after_value=0.0,
            ),
        ]
        bus_mods = [
            BusModification(
                bus_index=0,
                bus_id=1,
                rule=BusCleanupRule.VM_NORMALIZE,
                field_name="Vm",
                before_value=1.05,
                after_value=1.0,
            ),
        ]

        gens = [
            _make_gen(bus=1, pmax=50, fuel_type="wind"),
            _make_gen(bus=2, pmax=200, fuel_type="ng"),
        ]
        case_data = _make_case_data(gens, has_genfuel=True)

        manifest = build_network_manifest(
            network_id=CleanupNetworkId.SMALL,
            source_path=Path("data/networks/test.m"),
            dest_path=Path("data/timeseries/test/test.m"),
            case_data=case_data,
            classifications=[
                _make_classification(gen_index=0, fuel_category=FuelCategory.WIND, pmax=50),
                _make_classification(gen_index=1, fuel_category=FuelCategory.NG, pmax=200),
            ],
            gen_modifications=gen_mods,
            bus_modifications=bus_mods,
        )

        summary_by_rule = {s.rule: s.modification_count for s in manifest.rule_summary}
        assert summary_by_rule["renewable_pmin_reset"] == 1
        assert summary_by_rule["pg_reset"] == 2
        assert summary_by_rule["vm_normalize"] == 1


# ---------------------------------------------------------------------------
# Test 17: write_cleanup_manifest roundtrip
# ---------------------------------------------------------------------------


class TestWriteCleanupManifestRoundtrip:
    def test_json_roundtrip(self, tmp_path: Path) -> None:
        """Manifest survives JSON write/read roundtrip."""
        gen_mod = GeneratorModification(
            gen_index=0,
            gen_bus=1,
            fuel_type_raw="wind",
            fuel_category=FuelCategory.WIND,
            classification_source=FuelClassificationSource.GENFUEL_FIELD,
            rule=CleanupRule.RENEWABLE_PMIN_RESET,
            field_name="Pmin",
            before_value=50.0,
            after_value=0.0,
        )
        bus_mod = BusModification(
            bus_index=0,
            bus_id=1,
            rule=BusCleanupRule.VM_NORMALIZE,
            field_name="Vm",
            before_value=1.05,
            after_value=1.0,
        )
        network_manifest = NetworkCleanupManifest(
            network_id=CleanupNetworkId.SMALL,
            source_m_file="data/networks/case_ACTIVSg2000.m",
            cleaned_m_file="data/timeseries/ACTIVSg2000/case_ACTIVSg2000.m",
            bus_count=3,
            generator_count=1,
            fuel_type_summary=[
                FuelTypeSummary(
                    category=FuelCategory.WIND,
                    count=1,
                    pmax_total_mw=50.0,
                ),
            ],
            rule_summary=[
                RuleSummary(rule="renewable_pmin_reset", modification_count=1),
                RuleSummary(rule="vm_normalize", modification_count=1),
            ],
            generator_classifications=[
                GeneratorClassification(
                    gen_index=0,
                    gen_bus=1,
                    fuel_type_raw="wind",
                    fuel_category=FuelCategory.WIND,
                    classification_source=FuelClassificationSource.GENFUEL_FIELD,
                    pmax=50.0,
                    hydro_subclass=None,
                ),
            ],
            generator_modifications=[gen_mod],
            bus_modifications=[bus_mod],
        )

        cleanup_manifest = build_cleanup_manifest([network_manifest], script_version="0.1.0")

        dest = tmp_path / "manifest.json"
        write_cleanup_manifest(cleanup_manifest, dest)

        # Read back
        with open(dest) as f:
            data = json.load(f)

        # Check top-level fields
        assert data["script_version"] == "0.1.0"
        assert data["hydro_threshold_mw"] == HYDRO_THRESHOLD_MW
        assert data["hydro_reservoir_pmin_fraction"] == HYDRO_RESERVOIR_PMIN_FRACTION
        assert "generated_at" in data
        assert len(data["networks"]) == 1

        net = data["networks"][0]
        assert net["network_id"] == "ACTIVSg2000"
        assert net["bus_count"] == 3
        assert net["generator_count"] == 1

        # Check nested generator modification
        assert len(net["generator_modifications"]) == 1
        gm = net["generator_modifications"][0]
        assert gm["fuel_category"] == "wind"
        assert gm["rule"] == "renewable_pmin_reset"
        assert gm["before_value"] == 50.0
        assert gm["after_value"] == 0.0

        # Check nested bus modification
        assert len(net["bus_modifications"]) == 1
        bm = net["bus_modifications"][0]
        assert bm["rule"] == "vm_normalize"
        assert bm["before_value"] == 1.05
        assert bm["after_value"] == 1.0

        # Check enum serialized as string
        assert net["generator_classifications"][0]["classification_source"] == "genfuel_field"

        # Check rules documentation
        assert "renewable_pmin_reset" in data["cleanup_rules_doc"]
        assert "vm_normalize" in data["cleanup_rules_doc"]


# ---------------------------------------------------------------------------
# Test 18: main produces cleaned files for all networks
# ---------------------------------------------------------------------------


class TestMainProducesCleanedFiles:
    def test_all_three_networks(self, tmp_path: Path) -> None:
        """main() produces cleaned .m files and manifest for all networks."""
        networks_dir = tmp_path / "networks"
        networks_dir.mkdir()
        output_dir = tmp_path / "timeseries"
        manifest_path = output_dir / "cleanup_manifest.json"

        # Create minimal .m files for each network
        # case39: 10 generators, no genfuel
        case39_m = textwrap.dedent("""\
            function mpc = case39
            mpc.version = '2';
            mpc.baseMVA = 100;
            mpc.bus = [
                30\t2\t0\t0\t0\t0\t1\t1.05\t-5\t345\t1\t1.1\t0.9;
                31\t2\t10\t5\t0\t0\t1\t1.02\t-3\t345\t1\t1.1\t0.9;
                32\t2\t20\t10\t0\t0\t1\t0.98\t-2\t345\t1\t1.1\t0.9;
                33\t2\t15\t8\t0\t0\t1\t1.01\t-1\t345\t1\t1.1\t0.9;
                34\t2\t25\t12\t0\t0\t1\t0.99\t-4\t345\t1\t1.1\t0.9;
                35\t2\t30\t15\t0\t0\t1\t1.03\t-0.5\t345\t1\t1.1\t0.9;
                36\t2\t18\t9\t0\t0\t1\t1.04\t-1.5\t345\t1\t1.1\t0.9;
                37\t2\t22\t11\t0\t0\t1\t1.0\t0\t345\t1\t1.1\t0.9;
                38\t2\t28\t14\t0\t0\t1\t0.97\t-6\t345\t1\t1.1\t0.9;
                39\t3\t0\t0\t0\t0\t1\t1.06\t-8\t345\t1\t1.1\t0.9;
            ];
            mpc.gen = [
                30\t250\t50\t200\t-100\t1.05\t100\t1\t1040\t200;
                31\t500\t100\t300\t-150\t1.02\t100\t1\t646\t200;
                32\t600\t120\t350\t-200\t0.98\t100\t1\t725\t200;
                33\t400\t80\t250\t-100\t1.01\t100\t1\t652\t200;
                34\t300\t60\t200\t-80\t0.99\t100\t1\t508\t200;
                35\t450\t90\t280\t-120\t1.03\t100\t1\t687\t200;
                36\t350\t70\t220\t-90\t1.04\t100\t1\t580\t200;
                37\t400\t85\t260\t-110\t1.0\t100\t1\t564\t200;
                38\t550\t110\t320\t-180\t0.97\t100\t1\t865\t200;
                39\t800\t160\t400\t-200\t1.06\t100\t1\t1100\t200;
            ];
            mpc.branch = [
                30\t31\t0.01\t0.1\t0.02\t100\t100\t100\t0\t0\t1\t-360\t360;
            ];
        """)
        (networks_dir / "case39.m").write_text(case39_m)

        # ACTIVSg2000: 2 generators with genfuel
        activsg2000_m = textwrap.dedent("""\
            function mpc = case_ACTIVSg2000
            mpc.version = '2';
            mpc.baseMVA = 100;
            mpc.bus = [
                1\t3\t50\t20\t0\t0\t1\t1.05\t-5\t138\t1\t1.1\t0.9;
                2\t2\t30\t10\t0\t0\t1\t1.02\t-3\t138\t1\t1.1\t0.9;
            ];
            mpc.gen = [
                1\t100\t20\t50\t-20\t1.05\t100\t1\t200\t100;
                2\t50\t10\t30\t-10\t1.02\t100\t1\t80\t80;
            ];
            mpc.branch = [
                1\t2\t0.01\t0.1\t0.02\t100\t100\t100\t0\t0\t1\t-360\t360;
            ];
            mpc.genfuel = {
                'ng';
                'wind';
            };
        """)
        (networks_dir / "case_ACTIVSg2000.m").write_text(activsg2000_m)

        # ACTIVSg10k: 2 generators with genfuel
        activsg10k_m = textwrap.dedent("""\
            function mpc = case_ACTIVSg10k
            mpc.version = '2';
            mpc.baseMVA = 100;
            mpc.bus = [
                1\t3\t50\t20\t0\t0\t1\t1.05\t-5\t138\t1\t1.1\t0.9;
                2\t2\t30\t10\t0\t0\t1\t1.02\t-3\t138\t1\t1.1\t0.9;
            ];
            mpc.gen = [
                1\t80\t15\t40\t-15\t1.05\t100\t1\t150\t100;
                2\t40\t8\t20\t-8\t1.02\t100\t1\t60\t60;
            ];
            mpc.branch = [
                1\t2\t0.01\t0.1\t0.02\t100\t100\t100\t0\t0\t1\t-360\t360;
            ];
            mpc.genfuel = {
                'coal';
                'solar';
            };
        """)
        (networks_dir / "case_ACTIVSg10k.m").write_text(activsg10k_m)

        result = main(
            networks_dir=networks_dir,
            output_base_dir=output_dir,
            manifest_path=manifest_path,
        )

        # Check cleaned files exist
        assert (output_dir / "case39" / "case39.m").exists()
        assert (output_dir / "ACTIVSg2000" / "case_ACTIVSg2000.m").exists()
        assert (output_dir / "ACTIVSg10k" / "case_ACTIVSg10k.m").exists()

        # Check manifest
        assert manifest_path.exists()
        assert isinstance(result, CleanupManifest)
        assert len(result.networks) == 3

        # Verify network IDs
        net_ids = {n.network_id for n in result.networks}
        assert net_ids == {
            CleanupNetworkId.TINY,
            CleanupNetworkId.SMALL,
            CleanupNetworkId.MEDIUM,
        }

        # Verify cleaned file can be re-parsed
        reparsed = parse_matpower_case(output_dir / "case39" / "case39.m")
        assert len(reparsed.generators) == 10
        for g in reparsed.generators:
            assert g.pg == 0.0
            assert g.qg == 0.0
