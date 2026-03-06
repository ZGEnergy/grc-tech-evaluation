"""Tests for SCUC feasibility screening (PRD 03/05)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_scuc_feasibility import (
    CheckSeverity,
    FeasibilityResult,
    GeneratorRecord,
    HourlyCapacityResult,
    ParameterValidityResult,
    RampAdequacyResult,
    build_feasibility_report,
    check_cost_non_negative,
    check_min_up_down_times,
    check_pmin_headroom,
    check_pmin_pmax_consistency,
    check_ramp_adequacy,
    validate_network,
    write_feasibility_json,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gen(
    uid: str = "gen_0",
    bus_id: int = 1,
    pmax_mw: float = 100.0,
    pmin_mw: float = 20.0,
    fuel_type: str = "gas_cc",
    tech_class: str = "gas_CC_large",
    ramp_rate_mw_per_hr: float = 50.0,
    min_up_time_hr: float = 4.0,
    min_down_time_hr: float = 4.0,
    startup_cost_dollar: float = 1000.0,
    shutdown_cost_dollar: float = 500.0,
    is_renewable: bool = False,
) -> GeneratorRecord:
    """Helper to create a GeneratorRecord with defaults."""
    return GeneratorRecord(
        gen_uid=uid,
        bus_id=bus_id,
        pmax_mw=pmax_mw,
        pmin_mw=pmin_mw,
        fuel_type=fuel_type,
        tech_class=tech_class,
        ramp_rate_mw_per_hr=ramp_rate_mw_per_hr,
        min_up_time_hr=min_up_time_hr,
        min_down_time_hr=min_down_time_hr,
        startup_cost_dollar=startup_cost_dollar,
        shutdown_cost_dollar=shutdown_cost_dollar,
        is_renewable=is_renewable,
    )


def _flat_load(mw: float, hours: int = 24) -> list[float]:
    """Create a flat load profile."""
    return [mw] * hours


# ---------------------------------------------------------------------------
# Test check_pmin_headroom (checks a & b)
# ---------------------------------------------------------------------------


class TestCheckPminHeadroom:
    """Tests for check_pmin_headroom (checks a and b)."""

    def test_check_pmin_headroom_passes_comfortable_margin(self) -> None:
        """Test 1: Pmin sum=400 MW, load=1000 MW -> ratio 0.40, PASS."""
        generators = [_make_gen(uid=f"gen_{i}", pmin_mw=80.0, pmax_mw=500.0) for i in range(5)]
        load_profile = _flat_load(1000.0)

        result = check_pmin_headroom(generators, load_profile)

        assert result.pmin_check_status == CheckSeverity.PASS
        assert len(result.pmin_load_ratios) == 24
        for ratio in result.pmin_load_ratios:
            assert abs(ratio - 0.40) < 1e-9

    def test_check_pmin_headroom_warns_tight_margin(self) -> None:
        """Test 2: Pmin sum=920 MW, load=1000 MW -> ratio 0.92, WARN."""
        # 4 gens with pmin=230 each -> 920 total
        generators = [_make_gen(uid=f"gen_{i}", pmin_mw=230.0, pmax_mw=500.0) for i in range(4)]
        load_profile = _flat_load(1000.0)

        result = check_pmin_headroom(generators, load_profile)

        assert result.pmin_check_status == CheckSeverity.WARN
        assert abs(result.tightest_ratio - 0.92) < 1e-9

    def test_check_pmin_headroom_fails_exceeds_threshold(self) -> None:
        """Test 3: Pmin sum=960 MW, load=1000 MW -> ratio 0.96, FAIL."""
        # 4 gens with pmin=240 each -> 960 total
        generators = [_make_gen(uid=f"gen_{i}", pmin_mw=240.0, pmax_mw=500.0) for i in range(4)]
        load_profile = _flat_load(1000.0)

        result = check_pmin_headroom(generators, load_profile)

        assert result.pmin_check_status == CheckSeverity.FAIL

    def test_check_pmin_headroom_excludes_renewables(self) -> None:
        """Test 4: Renewables excluded from Pmin sum."""
        non_renewable = [_make_gen(uid=f"gen_{i}", pmin_mw=100.0, pmax_mw=500.0) for i in range(3)]
        renewable = [
            _make_gen(
                uid=f"wind_{i}",
                pmin_mw=0.0,
                pmax_mw=200.0,
                fuel_type="wind",
                is_renewable=True,
            )
            for i in range(2)
        ]
        generators = non_renewable + renewable
        load_profile = _flat_load(1000.0)

        result = check_pmin_headroom(generators, load_profile)

        assert result.sum_pmin_mw == 300.0
        assert result.pmin_check_status == CheckSeverity.PASS

    def test_check_pmax_capacity_passes(self) -> None:
        """Test 5: Pmax=2200 MW, peak_load=2000 MW -> margin 1.10, PASS."""
        generators = [_make_gen(uid=f"gen_{i}", pmax_mw=440.0, pmin_mw=50.0) for i in range(5)]
        load_profile = _flat_load(2000.0)

        result = check_pmin_headroom(generators, load_profile)

        assert result.pmax_check_status == CheckSeverity.PASS
        assert abs(result.pmax_margin - 1.10) < 1e-9

    def test_check_pmax_capacity_fails_insufficient(self) -> None:
        """Test 6: Pmax=2000 MW, peak_load=2000 MW -> margin 1.00, FAIL."""
        generators = [_make_gen(uid=f"gen_{i}", pmax_mw=400.0, pmin_mw=50.0) for i in range(5)]
        load_profile = _flat_load(2000.0)

        result = check_pmin_headroom(generators, load_profile)

        assert result.pmax_check_status == CheckSeverity.FAIL
        assert abs(result.pmax_margin - 1.00) < 1e-9


# ---------------------------------------------------------------------------
# Test check_ramp_adequacy (checks c & d)
# ---------------------------------------------------------------------------


class TestCheckRampAdequacy:
    """Tests for check_ramp_adequacy (checks c and d)."""

    def test_check_ramp_up_adequacy_passes(self) -> None:
        """Test 7: Fleet ramp=500 MW/hr, max increase=300 MW -> PASS."""
        generators = [_make_gen(uid=f"gen_{i}", ramp_rate_mw_per_hr=100.0) for i in range(5)]
        # Load profile with max increase of 300 MW at hour 5->6
        load_profile = [1000.0] * 5 + [1300.0] + [1000.0] * 18

        result = check_ramp_adequacy(generators, load_profile)

        assert result.ramp_up_status == CheckSeverity.PASS
        assert abs(result.ramp_up_margin - 500.0 / 300.0) < 1e-9

    def test_check_ramp_up_adequacy_fails_insufficient(self) -> None:
        """Test 8: Fleet ramp=200 MW/hr, max increase=300 MW -> FAIL."""
        generators = [_make_gen(uid=f"gen_{i}", ramp_rate_mw_per_hr=40.0) for i in range(5)]
        # Load profile with 300 MW increase
        load_profile = [1000.0] * 5 + [1300.0] + [1000.0] * 18

        result = check_ramp_adequacy(generators, load_profile)

        assert result.ramp_up_status == CheckSeverity.FAIL

    def test_check_ramp_down_adequacy_warns_tight(self) -> None:
        """Test 9: Fleet ramp=330 MW/hr, max decrease=310 MW -> margin ~1.065, WARN."""
        generators = [_make_gen(uid=f"gen_{i}", ramp_rate_mw_per_hr=66.0) for i in range(5)]
        # Load profile with 310 MW decrease
        load_profile = [1000.0] * 5 + [690.0] + [1000.0] * 18

        result = check_ramp_adequacy(generators, load_profile)

        assert result.ramp_down_status == CheckSeverity.WARN
        expected_margin = 330.0 / 310.0
        assert abs(result.ramp_down_margin - expected_margin) < 1e-9


# ---------------------------------------------------------------------------
# Test check_pmin_pmax_consistency (check e)
# ---------------------------------------------------------------------------


class TestCheckPminPmaxConsistency:
    """Tests for check_pmin_pmax_consistency (check e)."""

    def test_check_pmin_pmax_consistency_passes(self) -> None:
        """Test 10: All 5 gens have Pmin <= Pmax -> PASS."""
        generators = [_make_gen(uid=f"gen_{i}", pmin_mw=20.0, pmax_mw=100.0) for i in range(5)]

        violations, status = check_pmin_pmax_consistency(generators)

        assert violations == []
        assert status == CheckSeverity.PASS

    def test_check_pmin_pmax_consistency_fails(self) -> None:
        """Test 11: One gen has Pmin=200 > Pmax=150 -> FAIL."""
        generators = [
            _make_gen(uid="good_gen", pmin_mw=20.0, pmax_mw=100.0),
            _make_gen(uid="bad_gen", pmin_mw=200.0, pmax_mw=150.0),
        ]

        violations, status = check_pmin_pmax_consistency(generators)

        assert len(violations) == 1
        assert violations[0].check_name == "pmin_gt_pmax"
        assert violations[0].gen_uid == "bad_gen"
        assert status == CheckSeverity.FAIL


# ---------------------------------------------------------------------------
# Test check_cost_non_negative (check f)
# ---------------------------------------------------------------------------


class TestCheckCostNonNegative:
    """Tests for check_cost_non_negative (check f)."""

    def test_check_cost_non_negative_passes(self) -> None:
        """Test 12: All gens have non-negative costs (including zero) -> PASS."""
        generators = [
            _make_gen(uid=f"gen_{i}", startup_cost_dollar=1000.0, shutdown_cost_dollar=500.0)
            for i in range(4)
        ] + [
            _make_gen(uid="gen_4", startup_cost_dollar=0.0, shutdown_cost_dollar=0.0),
        ]

        violations, status = check_cost_non_negative(generators)

        assert violations == []
        assert status == CheckSeverity.PASS

    def test_check_cost_non_negative_fails_negative_startup(self) -> None:
        """Test 13: One gen has negative startup cost -> FAIL."""
        generators = [
            _make_gen(uid="bad_gen", startup_cost_dollar=-100.0),
        ]

        violations, status = check_cost_non_negative(generators)

        assert status == CheckSeverity.FAIL
        assert any(v.check_name == "negative_startup_cost" for v in violations)


# ---------------------------------------------------------------------------
# Test check_min_up_down_times (check g)
# ---------------------------------------------------------------------------


class TestCheckMinUpDownTimes:
    """Tests for check_min_up_down_times (check g)."""

    def test_check_min_up_down_times_valid(self) -> None:
        """Test 14: Valid min up/down times -> PASS."""
        generators = [
            _make_gen(uid="gen_0", min_up_time_hr=4.0, min_down_time_hr=4.0),
            _make_gen(uid="gen_1", min_up_time_hr=8.0, min_down_time_hr=6.0),
            _make_gen(uid="gen_2", min_up_time_hr=12.0, min_down_time_hr=8.0),
        ]

        violations, status = check_min_up_down_times(generators)

        assert violations == []
        assert status == CheckSeverity.PASS

    def test_check_min_up_down_times_fails_exceeds_horizon(self) -> None:
        """Test 15: min_up=14 + min_down=12 = 26 > 24 -> FAIL."""
        generators = [
            _make_gen(uid="bad_gen", min_up_time_hr=14.0, min_down_time_hr=12.0),
        ]

        violations, status = check_min_up_down_times(generators)

        assert status == CheckSeverity.FAIL
        sum_violations = [
            v for v in violations if v.check_name == "min_up_down_sum_exceeds_horizon"
        ]
        assert len(sum_violations) >= 1

    def test_check_min_up_down_times_skips_renewables(self) -> None:
        """Test 16: Renewables with min_up=0, min_down=0 are skipped -> PASS."""
        generators = [
            _make_gen(
                uid="solar_0",
                fuel_type="solar",
                is_renewable=True,
                min_up_time_hr=0.0,
                min_down_time_hr=0.0,
            ),
            _make_gen(
                uid="solar_1",
                fuel_type="solar",
                is_renewable=True,
                min_up_time_hr=0.0,
                min_down_time_hr=0.0,
            ),
        ]

        violations, status = check_min_up_down_times(generators)

        assert violations == []
        assert status == CheckSeverity.PASS


# ---------------------------------------------------------------------------
# Test validate_network (integration)
# ---------------------------------------------------------------------------


class TestValidateNetwork:
    """Integration tests for validate_network."""

    def test_validate_network_all_pass(self, tmp_path: Path) -> None:
        """Test 17: Synthetic dataset where all checks pass."""
        network_id = "case39"
        network_dir = tmp_path / network_id

        # Create a minimal .m file
        network_dir.mkdir(parents=True)
        m_content = _build_minimal_m_file(
            gen_count=5,
            pmax=200.0,
            pmin=20.0,
        )
        (network_dir / "case39.m").write_text(m_content)

        # Create gen_temporal_params.csv
        temporal_csv = _build_temporal_csv(
            gen_count=5,
            pmax=200.0,
            pmin=20.0,
            ramp_rate=100.0,
            min_up=4.0,
            min_down=4.0,
            startup_cost=1000.0,
            shutdown_cost=500.0,
            fuel_type="gas_cc",
            tech_class="gas_CC_large",
        )
        (network_dir / "gen_temporal_params.csv").write_text(temporal_csv)

        # Create load_24h.csv (low enough load for comfortable margins)
        load_csv = _build_load_csv(
            bus_count=5,
            hourly_load_per_bus=50.0,  # total = 250 MW/hr, well below sum(Pmin)=100
        )
        (network_dir / "load_24h.csv").write_text(load_csv)

        result = validate_network(network_id, tmp_path)

        assert result.overall_pass is True
        assert result.checks_failed == 0


# ---------------------------------------------------------------------------
# Test build_feasibility_report
# ---------------------------------------------------------------------------


class TestBuildFeasibilityReport:
    """Tests for build_feasibility_report."""

    def test_build_feasibility_report_any_fail_blocks_pass(self) -> None:
        """Test 18: One failing network means overall_pass is False."""
        # Two passing networks
        passing_result = _make_feasibility_result(
            network_id="case39",
            overall_pass=True,
            checks_passed=7,
            checks_failed=0,
        )
        passing_result_2 = _make_feasibility_result(
            network_id="ACTIVSg2000",
            overall_pass=True,
            checks_passed=7,
            checks_failed=0,
        )
        # One failing network
        failing_result = _make_feasibility_result(
            network_id="ACTIVSg10k",
            overall_pass=False,
            checks_passed=6,
            checks_failed=1,
        )

        report = build_feasibility_report([passing_result, passing_result_2, failing_result])

        assert report.overall_pass is False
        assert report.total_failed == 1


# ---------------------------------------------------------------------------
# Test write_feasibility_json
# ---------------------------------------------------------------------------


class TestWriteFeasibilityJson:
    """Tests for JSON serialization."""

    def test_write_feasibility_json_creates_file(self, tmp_path: Path) -> None:
        """Verify JSON output is written and parseable."""
        result = _make_feasibility_result(
            network_id="case39",
            overall_pass=True,
            checks_passed=7,
            checks_failed=0,
        )
        report = build_feasibility_report([result])
        dest = tmp_path / "output.json"

        write_feasibility_json(report, dest)

        assert dest.exists()
        data = json.loads(dest.read_text())
        assert data["overall_pass"] is True
        assert "networks" in data
        assert "case39" in data["networks"]


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------


def _build_minimal_m_file(
    gen_count: int,
    pmax: float,
    pmin: float,
    bus_count: int = 5,
) -> str:
    """Build a minimal MATPOWER .m file content."""
    lines = [
        "function mpc = case39",
        "mpc.version = '2';",
        "mpc.baseMVA = 100;",
        "",
        "mpc.bus = [",
    ]
    for i in range(1, bus_count + 1):
        # bus_i type Pd Qd Gs Bs area Vm Va baseKV zone Vmax Vmin
        bus_type = 3 if i == 1 else 1
        lines.append(f"  {i}\t{bus_type}\t100\t50\t0\t0\t1\t1.0\t0\t345\t1\t1.1\t0.9;")
    lines.append("];")
    lines.append("")
    lines.append("mpc.gen = [")
    for i in range(gen_count):
        bus = (i % bus_count) + 1
        # bus Pg Qg Qmax Qmin Vg mBase status Pmax Pmin ...extra cols
        tail = "\t0" * 11 + ";"
        lines.append(f"  {bus}\t100\t0\t999\t-999\t1.0\t100\t1\t{pmax}\t{pmin}{tail}")
    lines.append("];")
    lines.append("")
    lines.append("mpc.branch = [")
    for i in range(1, bus_count):
        lines.append(f"  {i}\t{i + 1}\t0.01\t0.1\t0\t250\t250\t250\t0\t0\t1\t-360\t360;")
    lines.append("];")
    return "\n".join(lines) + "\n"


def _build_temporal_csv(
    gen_count: int,
    pmax: float,
    pmin: float,
    ramp_rate: float,
    min_up: float,
    min_down: float,
    startup_cost: float,
    shutdown_cost: float,
    fuel_type: str,
    tech_class: str,
) -> str:
    """Build gen_temporal_params.csv content."""
    header = (
        "gen_uid,pmax_mw,pmin_mw,ramp_rate_mw_per_min,ramp_rate_mw_per_hr,"
        "min_up_time_hr,min_down_time_hr,startup_cost_dollar,startup_time_hr,"
        "shutdown_cost_dollar,tech_class,fuel_type"
    )
    rows = [header]
    for i in range(gen_count):
        bus = (i % 5) + 1
        uid = f"bus_{bus}_gen_{i}"
        rows.append(
            f"{uid},{pmax},{pmin},{ramp_rate / 60:.4f},{ramp_rate},"
            f"{min_up},{min_down},{startup_cost},1.0,"
            f"{shutdown_cost},{tech_class},{fuel_type}"
        )
    return "\n".join(rows) + "\n"


def _build_load_csv(
    bus_count: int,
    hourly_load_per_bus: float,
) -> str:
    """Build load_24h.csv content."""
    header = "bus_id," + ",".join(f"HR_{h}" for h in range(1, 25))
    rows = [header]
    for bus in range(1, bus_count + 1):
        values = ",".join(str(hourly_load_per_bus) for _ in range(24))
        rows.append(f"{bus},{values}")
    return "\n".join(rows) + "\n"


def _make_feasibility_result(
    network_id: str,
    overall_pass: bool,
    checks_passed: int,
    checks_failed: int,
    checks_warned: int = 0,
) -> FeasibilityResult:
    """Build a minimal FeasibilityResult for testing aggregation."""
    return FeasibilityResult(
        network_id=network_id,
        hourly_capacity=HourlyCapacityResult(
            pmin_load_ratios=[0.5] * 24,
            tightest_hour=0,
            tightest_ratio=0.5,
            sum_pmin_mw=500.0,
            pmin_check_status=CheckSeverity.PASS,
            pmin_check_message="ok",
            pmax_total_mw=2000.0,
            peak_load_mw=1000.0,
            pmax_margin=2.0,
            pmax_check_status=CheckSeverity.PASS,
            pmax_check_message="ok",
        ),
        ramp_adequacy=RampAdequacyResult(
            fleet_ramp_up_mw_per_hr=500.0,
            max_load_increase_mw=100.0,
            ramp_up_hour=0,
            ramp_up_margin=5.0,
            ramp_up_status=CheckSeverity.PASS,
            ramp_up_message="ok",
            fleet_ramp_down_mw_per_hr=500.0,
            max_load_decrease_mw=100.0,
            ramp_down_hour=0,
            ramp_down_margin=5.0,
            ramp_down_status=CheckSeverity.PASS,
            ramp_down_message="ok",
        ),
        parameter_validity=ParameterValidityResult(
            pmin_pmax_violations=[],
            cost_violations=[],
            time_violations=[],
            total_generators_checked=10,
            total_violations=0,
            pmin_pmax_status=CheckSeverity.PASS if overall_pass else CheckSeverity.FAIL,
            cost_status=CheckSeverity.PASS,
            time_status=CheckSeverity.PASS,
        ),
        total_checks=7,
        checks_passed=checks_passed,
        checks_warned=checks_warned,
        checks_failed=checks_failed,
        overall_pass=overall_pass,
        load_profile_mw=[1000.0] * 24,
    )
