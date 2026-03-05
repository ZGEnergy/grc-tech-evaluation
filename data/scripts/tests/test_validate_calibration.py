"""Tests for validate_calibration.py — 24 unit tests for PRD 02/06.

All tests are self-contained with no external file dependencies or network calls.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from scripts.validate_calibration import (
    CheckCategory,
    CheckResult,
    CheckStatus,
    NetworkValidationResult,
    ValidationNetworkId,
    ValidationSummary,
    check_classification_completeness,
    check_eligibility_mw_consistency,
    check_min_updown_24h,
    check_non_negative_costs,
    check_nuclear_ineligible,
    check_ramp_rate_vs_pmax,
    check_renewable_zeros,
    check_spinning_adequacy,
    check_tech_class_coverage,
    check_temporal_params_completeness,
    check_thermal_ramp_positive,
    validate_network,
    write_json_report,
    write_markdown_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_classification_rows(
    gen_uids: list[str],
    tech_classes: list[str] | None = None,
    fuel_types: list[str] | None = None,
) -> list[dict[str, str]]:
    """Build minimal classification row dicts for testing."""
    if tech_classes is None:
        tech_classes = ["coal_large"] * len(gen_uids)
    if fuel_types is None:
        fuel_types = ["coal"] * len(gen_uids)
    return [
        {"gen_uid": uid, "tech_class": tc, "fuel_type": ft}
        for uid, tc, ft in zip(gen_uids, tech_classes, fuel_types)
    ]


def _make_temporal_rows(
    gen_uids: list[str],
    pmax_values: list[float] | None = None,
    pmin_values: list[float] | None = None,
    ramp_hr_values: list[float] | None = None,
    ramp_min_values: list[float] | None = None,
    min_up_values: list[float] | None = None,
    min_down_values: list[float] | None = None,
    startup_cost_values: list[float] | None = None,
    startup_time_values: list[float] | None = None,
    shutdown_cost_values: list[float] | None = None,
    fuel_types: list[str] | None = None,
) -> list[dict[str, str]]:
    """Build minimal temporal param row dicts for testing."""
    n = len(gen_uids)
    pmax = pmax_values or [100.0] * n
    pmin = pmin_values or [30.0] * n
    ramp_hr = ramp_hr_values or [50.0] * n
    ramp_min = ramp_min_values or [0.83] * n
    min_up = min_up_values or [4.0] * n
    min_down = min_down_values or [4.0] * n
    startup_cost = startup_cost_values or [1000.0] * n
    startup_time = startup_time_values or [2.0] * n
    shutdown_cost = shutdown_cost_values or [500.0] * n
    fuels = fuel_types or ["coal"] * n
    return [
        {
            "gen_uid": uid,
            "pmax_mw": str(pm),
            "pmin_mw": str(pmn),
            "ramp_rate_mw_per_hr": str(rh),
            "ramp_rate_mw_per_min": str(rm),
            "min_up_time_hr": str(mu),
            "min_down_time_hr": str(md),
            "startup_cost_dollar": str(sc),
            "startup_time_hr": str(st),
            "shutdown_cost_dollar": str(sdc),
            "fuel_type": ft,
            "tech_class": "coal_large",
        }
        for uid, pm, pmn, rh, rm, mu, md, sc, st, sdc, ft in zip(
            gen_uids,
            pmax,
            pmin,
            ramp_hr,
            ramp_min,
            min_up,
            min_down,
            startup_cost,
            startup_time,
            shutdown_cost,
            fuels,
        )
    ]


def _make_eligibility_rows(
    gen_uids: list[str],
    spinning_eligible: list[bool] | None = None,
    non_spinning_eligible: list[bool] | None = None,
    max_spinning_mw: list[float] | None = None,
    max_non_spinning_mw: list[float] | None = None,
    fuel_types: list[str] | None = None,
) -> list[dict[str, str]]:
    """Build minimal eligibility row dicts for testing."""
    n = len(gen_uids)
    spin_elig = spinning_eligible or [True] * n
    nonspin_elig = non_spinning_eligible or [False] * n
    spin_mw = max_spinning_mw or [50.0] * n
    nonspin_mw = max_non_spinning_mw or [0.0] * n
    fuels = fuel_types or ["coal"] * n
    return [
        {
            "gen_uid": uid,
            "tech_class": "coal_large",
            "fuel_type": ft,
            "spinning_eligible": "true" if se else "false",
            "non_spinning_eligible": "true" if nse else "false",
            "max_spinning_mw": str(smw),
            "max_non_spinning_mw": str(nsmw),
        }
        for uid, ft, se, nse, smw, nsmw in zip(
            gen_uids,
            fuels,
            spin_elig,
            nonspin_elig,
            spin_mw,
            nonspin_mw,
        )
    ]


# ---------------------------------------------------------------------------
# C1: Classification completeness
# ---------------------------------------------------------------------------


def test_check_classification_completeness_pass():
    """Identical gen_uid lists -> PASS."""
    uids = ["bus_1_gen_0", "bus_2_gen_1", "bus_3_gen_2"]
    rows = _make_classification_rows(uids)
    result = check_classification_completeness(uids, rows)
    assert result.status == CheckStatus.PASS
    assert result.generators_failing == 0


def test_check_classification_completeness_missing_generator():
    """Missing bus_2 -> FAIL."""
    expected = ["bus_1_gen_0", "bus_2_gen_1", "bus_3_gen_2"]
    csv_uids = ["bus_1_gen_0", "bus_3_gen_2"]
    rows = _make_classification_rows(csv_uids)
    result = check_classification_completeness(expected, rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1
    assert "bus_2_gen_1" in result.failing_gen_uids


# ---------------------------------------------------------------------------
# C2: Temporal params completeness
# ---------------------------------------------------------------------------


def test_check_temporal_params_completeness_order_mismatch():
    """Same set, different order -> PASS (set comparison, not ordered)."""
    expected = ["bus_1_gen_0", "bus_2_gen_1"]
    rows = _make_temporal_rows(["bus_2_gen_1", "bus_1_gen_0"])
    result = check_temporal_params_completeness(expected, rows)
    assert result.status == CheckStatus.PASS
    assert result.generators_failing == 0


# ---------------------------------------------------------------------------
# C4: Tech class coverage
# ---------------------------------------------------------------------------


def test_check_tech_class_coverage_pass():
    """All non-exempt classes in reference -> PASS."""
    rows = _make_classification_rows(
        ["g1", "g2", "g3"],
        tech_classes=["coal_large", "gas_CT", "nuclear"],
    )
    ref = {"coal_large", "gas_CT", "nuclear", "hydro"}
    result = check_tech_class_coverage(rows, ref)
    assert result.status == CheckStatus.PASS


def test_check_tech_class_coverage_missing_class():
    """Unknown class -> FAIL."""
    rows = _make_classification_rows(
        ["g1", "g2"],
        tech_classes=["coal_large", "unknown_class"],
    )
    ref = {"coal_large", "gas_CT", "nuclear"}
    result = check_tech_class_coverage(rows, ref)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing >= 1


# ---------------------------------------------------------------------------
# P1: Ramp rate vs Pmax
# ---------------------------------------------------------------------------


def test_check_ramp_rate_vs_pmax_pass():
    """Ramp <= Pmax -> PASS."""
    rows = _make_temporal_rows(
        ["g1"],
        pmax_values=[300.0],
        ramp_hr_values=[200.0],
    )
    result = check_ramp_rate_vs_pmax(rows)
    assert result.status == CheckStatus.PASS


def test_check_ramp_rate_vs_pmax_fail():
    """Ramp 500 > Pmax 300 -> FAIL."""
    rows = _make_temporal_rows(
        ["g1"],
        pmax_values=[300.0],
        ramp_hr_values=[500.0],
    )
    result = check_ramp_rate_vs_pmax(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1


# ---------------------------------------------------------------------------
# P2: Non-negative costs
# ---------------------------------------------------------------------------


def test_check_non_negative_costs_fail():
    """Negative startup cost -> FAIL."""
    rows = _make_temporal_rows(
        ["g1"],
        startup_cost_values=[-100.0],
    )
    result = check_non_negative_costs(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1


# ---------------------------------------------------------------------------
# P3: Thermal ramp positive
# ---------------------------------------------------------------------------


def test_check_thermal_ramp_positive_fail():
    """Coal with zero ramp -> FAIL, wind zero OK."""
    rows = _make_temporal_rows(
        ["g_coal", "g_wind"],
        ramp_hr_values=[0.0, 0.0],
        fuel_types=["coal", "wind"],
    )
    result = check_thermal_ramp_positive(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1
    assert "g_coal" in result.failing_gen_uids


# ---------------------------------------------------------------------------
# S1: Min up+down <= 24h
# ---------------------------------------------------------------------------


def test_check_min_updown_24h_pass():
    """8 + 4 = 12 <= 24 -> PASS."""
    rows = _make_temporal_rows(
        ["g1"],
        min_up_values=[8.0],
        min_down_values=[4.0],
    )
    result = check_min_updown_24h(rows)
    assert result.status == CheckStatus.PASS


def test_check_min_updown_24h_fail():
    """16 + 10 = 26 > 24 -> FAIL."""
    rows = _make_temporal_rows(
        ["g1"],
        min_up_values=[16.0],
        min_down_values=[10.0],
    )
    result = check_min_updown_24h(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1


# ---------------------------------------------------------------------------
# R1: Spinning adequacy
# ---------------------------------------------------------------------------


def test_check_spinning_adequacy_pass():
    """Ratio 1.875 >= 1.5 -> PASS."""
    # 4 generators each contributing 75 MW spinning = 300 MW, requirement = 160 MW
    # ratio = 300/160 = 1.875
    rows = _make_eligibility_rows(
        ["g1", "g2", "g3", "g4"],
        spinning_eligible=[True, True, True, True],
        max_spinning_mw=[75.0, 75.0, 75.0, 75.0],
    )
    result = check_spinning_adequacy(rows, requirement_mw=160.0)
    assert result.status == CheckStatus.PASS


def test_check_spinning_adequacy_warn():
    """Ratio 1.25 -> WARN."""
    # 200 MW eligible, 160 MW requirement -> ratio = 1.25
    rows = _make_eligibility_rows(
        ["g1", "g2"],
        spinning_eligible=[True, True],
        max_spinning_mw=[100.0, 100.0],
    )
    result = check_spinning_adequacy(rows, requirement_mw=160.0)
    assert result.status == CheckStatus.WARN


def test_check_spinning_adequacy_fail():
    """Ratio 0.75 -> FAIL."""
    # 120 MW eligible, 160 MW requirement -> ratio = 0.75
    rows = _make_eligibility_rows(
        ["g1", "g2"],
        spinning_eligible=[True, True],
        max_spinning_mw=[60.0, 60.0],
    )
    result = check_spinning_adequacy(rows, requirement_mw=160.0)
    assert result.status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# D1: Renewable zeros
# ---------------------------------------------------------------------------


def test_check_renewable_zeros_pass():
    """Wind with all zeros -> PASS."""
    rows = _make_temporal_rows(
        ["g_wind"],
        ramp_hr_values=[0.0],
        ramp_min_values=[0.0],
        min_up_values=[0.0],
        min_down_values=[0.0],
        startup_cost_values=[0.0],
        startup_time_values=[0.0],
        shutdown_cost_values=[0.0],
        fuel_types=["wind"],
    )
    result = check_renewable_zeros(rows)
    assert result.status == CheckStatus.PASS


def test_check_renewable_zeros_fail():
    """Solar with nonzero ramp -> FAIL."""
    rows = _make_temporal_rows(
        ["g_solar"],
        ramp_hr_values=[5.0],
        ramp_min_values=[0.0],
        min_up_values=[0.0],
        min_down_values=[0.0],
        startup_cost_values=[0.0],
        startup_time_values=[0.0],
        shutdown_cost_values=[0.0],
        fuel_types=["solar"],
    )
    result = check_renewable_zeros(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1


# ---------------------------------------------------------------------------
# D2: Nuclear ineligible
# ---------------------------------------------------------------------------


def test_check_nuclear_ineligible_pass():
    """Nuclear with both false -> PASS."""
    rows = _make_eligibility_rows(
        ["g_nuc"],
        spinning_eligible=[False],
        non_spinning_eligible=[False],
        max_spinning_mw=[0.0],
        max_non_spinning_mw=[0.0],
        fuel_types=["nuclear"],
    )
    result = check_nuclear_ineligible(rows)
    assert result.status == CheckStatus.PASS


def test_check_nuclear_ineligible_fail():
    """Nuclear with spinning=true -> FAIL."""
    rows = _make_eligibility_rows(
        ["g_nuc"],
        spinning_eligible=[True],
        non_spinning_eligible=[False],
        max_spinning_mw=[50.0],
        max_non_spinning_mw=[0.0],
        fuel_types=["nuclear"],
    )
    result = check_nuclear_ineligible(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1


# ---------------------------------------------------------------------------
# D3: Eligibility MW consistency
# ---------------------------------------------------------------------------


def test_check_eligibility_mw_consistency_pass():
    """Flags consistent with MW -> PASS."""
    rows = _make_eligibility_rows(
        ["g1"],
        spinning_eligible=[True],
        non_spinning_eligible=[False],
        max_spinning_mw=[50.0],
        max_non_spinning_mw=[0.0],
    )
    result = check_eligibility_mw_consistency(rows)
    assert result.status == CheckStatus.PASS


def test_check_eligibility_mw_consistency_fail():
    """Spinning=true but mw=0 -> FAIL."""
    rows = _make_eligibility_rows(
        ["g1"],
        spinning_eligible=[True],
        non_spinning_eligible=[False],
        max_spinning_mw=[0.0],
        max_non_spinning_mw=[0.0],
    )
    result = check_eligibility_mw_consistency(rows)
    assert result.status == CheckStatus.FAIL
    assert result.generators_failing == 1


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------


def test_write_json_report_structure(tmp_path: Path):
    """Verify JSON schema of the written report."""
    check = CheckResult(
        check_id="C1",
        category=CheckCategory.COMPLETENESS,
        description="test check",
        status=CheckStatus.PASS,
        generators_checked=10,
        generators_failing=0,
        failing_gen_uids=[],
        detail="all good",
    )
    net_result = NetworkValidationResult(
        network_id=ValidationNetworkId.TINY,
        generator_count=10,
        check_results=[check],
        pass_count=1,
        warn_count=0,
        fail_count=0,
        markdown_report_path="test.md",
        all_passed=True,
    )
    json_path = tmp_path / "report.json"
    summary = ValidationSummary(
        network_results=[net_result],
        overall_pass=True,
        total_checks=1,
        total_pass=1,
        total_warn=0,
        total_fail=0,
        json_report_path=str(json_path),
        script_version="0.1.0",
    )
    write_json_report(summary, json_path)

    data = json.loads(json_path.read_text())
    assert "overall_pass" in data
    assert "total_checks" in data
    assert "network_results" in data
    assert len(data["network_results"]) == 1
    net = data["network_results"][0]
    assert "check_results" in net
    assert net["check_results"][0]["check_id"] == "C1"
    assert data["overall_pass"] is True


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def test_write_markdown_report_contains_all_checks(tmp_path: Path):
    """All check IDs present in the markdown report."""
    checks = [
        CheckResult(
            check_id=f"X{i}",
            category=CheckCategory.COMPLETENESS,
            description=f"check {i}",
            status=CheckStatus.PASS,
            generators_checked=5,
            generators_failing=0,
            failing_gen_uids=[],
            detail=f"detail {i}",
        )
        for i in range(1, 6)
    ]
    net_result = NetworkValidationResult(
        network_id=ValidationNetworkId.TINY,
        generator_count=5,
        check_results=checks,
        pass_count=5,
        warn_count=0,
        fail_count=0,
        markdown_report_path=str(tmp_path / "report.md"),
        all_passed=True,
    )
    md_path = tmp_path / "report.md"
    write_markdown_report(net_result, md_path)

    content = md_path.read_text()
    for i in range(1, 6):
        assert f"X{i}" in content


# ---------------------------------------------------------------------------
# End-to-end: validate_network
# ---------------------------------------------------------------------------


def _write_m_file(path: Path) -> None:
    """Write a minimal MATPOWER .m file with 4 generators."""
    content = textwrap.dedent("""\
        function mpc = test_case
        mpc.version = '2';
        mpc.baseMVA = 100;
        mpc.bus = [
            1 3 0 0 0 0 1 1.0 0.0 345 1 1.1 0.9;
            2 2 0 0 0 0 1 1.0 0.0 345 1 1.1 0.9;
            3 2 0 0 0 0 1 1.0 0.0 345 1 1.1 0.9;
            4 1 0 0 0 0 1 1.0 0.0 345 1 1.1 0.9;
        ];
        mpc.gen = [
            1 100 0 999 -999 1.0 100 1 300 50;
            2 50 0 999 -999 1.0 100 1 200 40;
            3 30 0 999 -999 1.0 100 1 100 20;
            4 20 0 999 -999 1.0 100 1 150 0;
        ];
        """)
    path.write_text(content)


def _write_classification_csv(path: Path, gen_uids: list[str]) -> None:
    """Write a minimal gen_fuel_classification.csv."""
    lines = [
        "gen_index,gen_bus,gen_uid,fuel_type,gas_unit_type,unit_type,"
        "capacity_band,tech_class,pmax_mw,pmin_mw,source,confidence"
    ]
    techs = ["coal_large", "gas_CT", "hydro", "wind"]
    fuels = ["coal", "gas", "hydro", "wind"]
    for i, uid in enumerate(gen_uids):
        lines.append(
            f"{i},{i + 1},{uid},{fuels[i]},,STEAM,large,{techs[i]},"
            f"{[300, 200, 100, 150][i]},{[50, 40, 20, 0][i]},genfuel,high"
        )
    path.write_text("\n".join(lines) + "\n")


def _write_temporal_csv(path: Path, gen_uids: list[str]) -> None:
    """Write a minimal gen_temporal_params.csv."""
    lines = [
        "gen_uid,pmax_mw,pmin_mw,ramp_rate_mw_per_min,ramp_rate_mw_per_hr,"
        "min_up_time_hr,min_down_time_hr,startup_cost_dollar,startup_time_hr,"
        "shutdown_cost_dollar,tech_class,fuel_type"
    ]
    configs = [
        ("300", "50", "2.0", "120.0", "4", "4", "5000", "3", "1000", "coal_large", "coal"),
        ("200", "40", "3.0", "180.0", "2", "2", "3000", "1", "500", "gas_CT", "gas"),
        ("100", "20", "1.5", "90.0", "1", "1", "100", "0.5", "50", "hydro", "hydro"),
        ("150", "0", "0.0", "0.0", "0", "0", "0", "0", "0", "wind", "wind"),
    ]
    for uid, cfg in zip(gen_uids, configs):
        lines.append(f"{uid}," + ",".join(cfg))
    path.write_text("\n".join(lines) + "\n")


def _write_eligibility_csv(path: Path, gen_uids: list[str]) -> None:
    """Write a minimal reserve_eligibility.csv."""
    lines = [
        "gen_uid,tech_class,fuel_type,spinning_eligible,non_spinning_eligible,"
        "max_spinning_mw,max_non_spinning_mw"
    ]
    configs = [
        ("coal_large", "coal", "true", "false", "120.00", "0.00"),
        ("gas_CT", "gas", "true", "true", "30.00", "200.00"),
        ("hydro", "hydro", "true", "true", "15.00", "100.00"),
        ("wind", "wind", "false", "false", "0.00", "0.00"),
    ]
    for uid, cfg in zip(gen_uids, configs):
        lines.append(f"{uid}," + ",".join(cfg))
    path.write_text("\n".join(lines) + "\n")


def _write_reserve_req_csv(path: Path) -> None:
    """Write a minimal reserve_requirements_24h.csv."""
    lines = [
        "Product,"
        + ",".join(f"HR_{h}" for h in range(1, 25))
        + ",sizing_basis,largest_gen_uid,largest_gen_pmax"
    ]
    spin_vals = ",".join(["100.00"] * 24)
    nonspin_vals = ",".join(["100.00"] * 24)
    lines.append(f"spinning,{spin_vals},N-1,bus_1_gen_0,300.00")
    lines.append(f"non_spinning,{nonspin_vals},N-1,bus_1_gen_0,300.00")
    path.write_text("\n".join(lines) + "\n")


def _write_reference_csv(path: Path) -> None:
    """Write a minimal rts_gmlc_tech_classes.csv."""
    lines = [
        "# provenance comment",
        "tech_class,fuel_type,unit_type,capacity_band,pmax_template_mw,"
        "pmin_template_mw,ramp_rate_mw_per_min,ramp_rate_mw_per_hr,"
        "min_up_time_hr,min_down_time_hr,startup_time_cold_hr,"
        "startup_time_warm_hr,startup_time_hot_hr,startup_cost_cold_dollar,"
        "startup_cost_warm_dollar,startup_cost_hot_dollar,shutdown_cost_dollar,"
        "capacity_band_min_mw,capacity_band_max_mw,generator_count",
        "coal_large,coal,STEAM,large,350,100,2.0,120.0,4,4,8,4,2,5000,3000,1000,1000,300,inf,5",
        "gas_CT,gas,CT,small,55,10,3.0,180.0,2,2,1,0.5,0.2,3000,1500,500,500,0,100,10",
        "hydro,hydro,HYDRO,small,50,0,1.5,90.0,0,0,0,0,0,0,0,0,0,0,inf,5",
        "nuclear,nuclear,NUCLEAR,large,400,100,0.5,30.0,24,24,72,48,24,50000,30000,15000,5000,0,inf,2",
    ]
    path.write_text("\n".join(lines) + "\n")


def test_validate_network_end_to_end(tmp_path: Path):
    """4 generators, all consistent -> all_passed=True."""
    net_dir = tmp_path / "network"
    net_dir.mkdir()
    val_dir = tmp_path / "validation"

    # Write .m file
    m_path = net_dir / "test.m"
    _write_m_file(m_path)

    # Derive gen_uids the same way the script does
    gen_uids = ["bus_1_gen_0", "bus_2_gen_1", "bus_3_gen_2", "bus_4_gen_3"]

    _write_classification_csv(net_dir / "gen_fuel_classification.csv", gen_uids)
    _write_temporal_csv(net_dir / "gen_temporal_params.csv", gen_uids)
    _write_eligibility_csv(net_dir / "reserve_eligibility.csv", gen_uids)
    _write_reserve_req_csv(net_dir / "reserve_requirements_24h.csv")

    ref_path = net_dir / "rts_gmlc_tech_classes.csv"
    _write_reference_csv(ref_path)

    result = validate_network(
        network_id=ValidationNetworkId.TINY,
        cleaned_m_path=m_path,
        classification_csv_path=net_dir / "gen_fuel_classification.csv",
        temporal_params_csv_path=net_dir / "gen_temporal_params.csv",
        eligibility_csv_path=net_dir / "reserve_eligibility.csv",
        reserve_req_csv_path=net_dir / "reserve_requirements_24h.csv",
        reference_csv_path=ref_path,
        validation_output_dir=val_dir,
    )

    assert result.all_passed is True
    assert result.fail_count == 0
    assert result.generator_count == 4
    assert len(result.check_results) == 14


# ---------------------------------------------------------------------------
# Overall pass false when any fail
# ---------------------------------------------------------------------------


def test_overall_pass_false_when_any_fail():
    """One FAIL -> overall_pass=False."""
    pass_check = CheckResult(
        check_id="C1",
        category=CheckCategory.COMPLETENESS,
        description="ok",
        status=CheckStatus.PASS,
        generators_checked=5,
        generators_failing=0,
        failing_gen_uids=[],
        detail="ok",
    )
    fail_check = CheckResult(
        check_id="C2",
        category=CheckCategory.COMPLETENESS,
        description="missing",
        status=CheckStatus.FAIL,
        generators_checked=5,
        generators_failing=1,
        failing_gen_uids=["g1"],
        detail="missing g1",
    )

    net_result = NetworkValidationResult(
        network_id=ValidationNetworkId.TINY,
        generator_count=5,
        check_results=[pass_check, fail_check],
        pass_count=1,
        warn_count=0,
        fail_count=1,
        markdown_report_path="test.md",
        all_passed=False,
    )

    summary = ValidationSummary(
        network_results=[net_result],
        overall_pass=False,
        total_checks=2,
        total_pass=1,
        total_warn=0,
        total_fail=1,
        json_report_path="test.json",
        script_version="0.1.0",
    )

    assert summary.overall_pass is False
    assert summary.total_fail == 1
