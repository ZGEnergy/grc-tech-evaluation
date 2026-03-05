"""Tests for Cross-Network Consistency Checks (PRD 05/06).

Each test function corresponds to one success criterion from the PRD.
Most tests use direct NetworkSummary fixtures (no file I/O). The
integration test (test_validate_cross_network_overall_pass) creates
temporary directories with minimal CSV and .m files.
"""

from __future__ import annotations

import textwrap
from pathlib import Path


from scripts.validate_cross_network import (
    ConsistencyStatus,
    CrossNetworkComparisonTable,
    NetworkId,
    NetworkSummary,
    build_comparison_table,
    check_bess_fleet_pct,
    check_bess_rte_identical,
    check_dr_fleet_pct,
    check_flowgate_count_range,
    check_renewable_penetration,
    check_reserve_ratio_consistency,
    check_structural_counts,
    check_student_t_df_consistency,
    run_all_cross_network_checks,
    validate_cross_network,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(
    network_id: NetworkId = NetworkId.TINY,
    bus_count: int = 39,
    gen_count: int = 10,
    branch_count: int = 46,
    peak_load_mw: float = 8000.0,
    bess_fleet_mw: float = 300.0,
    bess_rte_values: list[float] | None = None,
    dr_curtail_mw: float = 240.0,
    spinning_reserve_peak_mw: float = 480.0,
    non_spinning_reserve_peak_mw: float = 320.0,
    renewable_peak_mw: float = 1600.0,
    flowgate_count: int = 4,
    wind_student_t_df: float | None = 5.0,
    solar_student_t_df: float | None = 6.0,
) -> NetworkSummary:
    """Build a NetworkSummary with sensible defaults."""
    if bess_rte_values is None:
        bess_rte_values = [0.85]
    return NetworkSummary(
        network_id=network_id,
        bus_count=bus_count,
        gen_count=gen_count,
        branch_count=branch_count,
        peak_load_mw=peak_load_mw,
        bess_fleet_mw=bess_fleet_mw,
        bess_rte_values=bess_rte_values,
        dr_curtail_mw=dr_curtail_mw,
        spinning_reserve_peak_mw=spinning_reserve_peak_mw,
        non_spinning_reserve_peak_mw=non_spinning_reserve_peak_mw,
        renewable_peak_mw=renewable_peak_mw,
        flowgate_count=flowgate_count,
        wind_student_t_df=wind_student_t_df,
        solar_student_t_df=solar_student_t_df,
    )


def _three_summaries(**overrides: object) -> list[NetworkSummary]:
    """Build a list of three NetworkSummary with per-network overrides.

    overrides keys use the pattern: <field>_TINY, <field>_SMALL, <field>_MEDIUM.
    Unqualified keys apply to all networks.
    """
    defaults = {
        NetworkId.TINY: {
            "bus_count": 39,
            "gen_count": 10,
            "branch_count": 46,
            "peak_load_mw": 8000.0,
            "bess_fleet_mw": 300.0,
            "bess_rte_values": [0.85],
            "dr_curtail_mw": 240.0,
            "spinning_reserve_peak_mw": 480.0,
            "non_spinning_reserve_peak_mw": 320.0,
            "renewable_peak_mw": 1600.0,
            "flowgate_count": 4,
            "wind_student_t_df": 5.0,
            "solar_student_t_df": 6.0,
        },
        NetworkId.SMALL: {
            "bus_count": 2000,
            "gen_count": 544,
            "branch_count": 3000,
            "peak_load_mw": 12000.0,
            "bess_fleet_mw": 500.0,
            "bess_rte_values": [0.85],
            "dr_curtail_mw": 600.0,
            "spinning_reserve_peak_mw": 780.0,
            "non_spinning_reserve_peak_mw": 480.0,
            "renewable_peak_mw": 3000.0,
            "flowgate_count": 4,
            "wind_student_t_df": 6.0,
            "solar_student_t_df": 7.0,
        },
        NetworkId.MEDIUM: {
            "bus_count": 10000,
            "gen_count": 3000,
            "branch_count": 13000,
            "peak_load_mw": 40000.0,
            "bess_fleet_mw": 1500.0,
            "bess_rte_values": [0.85],
            "dr_curtail_mw": 1600.0,
            "spinning_reserve_peak_mw": 2800.0,
            "non_spinning_reserve_peak_mw": 1600.0,
            "renewable_peak_mw": 12000.0,
            "flowgate_count": 5,
            "wind_student_t_df": None,
            "solar_student_t_df": None,
        },
    }

    # Apply overrides
    for key, val in overrides.items():
        for nid in (NetworkId.TINY, NetworkId.SMALL, NetworkId.MEDIUM):
            suffix = f"_{nid.name}"
            if key.endswith(suffix):
                field_name = key[: -len(suffix)]
                defaults[nid][field_name] = val
            elif not any(key.endswith(f"_{n.name}") for n in NetworkId):
                defaults[nid][key] = val

    return [_make_summary(network_id=nid, **params) for nid, params in defaults.items()]


# ---------------------------------------------------------------------------
# 1. test_check_bess_rte_identical_passes
# ---------------------------------------------------------------------------


def test_check_bess_rte_identical_passes() -> None:
    """All networks bess_rte_values=[0.85] -> PASS."""
    summaries = _three_summaries()
    result = check_bess_rte_identical(summaries)
    assert result.status == ConsistencyStatus.PASS
    assert result.check_id == "bess_rte_identical"


# ---------------------------------------------------------------------------
# 2. test_check_bess_rte_identical_fails_different_values
# ---------------------------------------------------------------------------


def test_check_bess_rte_identical_fails_different_values() -> None:
    """MEDIUM has [0.90] -> FAIL."""
    summaries = _three_summaries(bess_rte_values_MEDIUM=[0.90])
    result = check_bess_rte_identical(summaries)
    assert result.status == ConsistencyStatus.FAIL


# ---------------------------------------------------------------------------
# 3. test_check_bess_fleet_pct_passes
# ---------------------------------------------------------------------------


def test_check_bess_fleet_pct_passes() -> None:
    """Ratios 3.75%, 4.17%, 3.75% -> PASS."""
    summaries = _three_summaries(
        peak_load_mw_TINY=8000.0,
        bess_fleet_mw_TINY=300.0,  # 3.75%
        peak_load_mw_SMALL=12000.0,
        bess_fleet_mw_SMALL=500.0,  # 4.17%
        peak_load_mw_MEDIUM=40000.0,
        bess_fleet_mw_MEDIUM=1500.0,  # 3.75%
    )
    result = check_bess_fleet_pct(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 4. test_check_bess_fleet_pct_fails_too_high
# ---------------------------------------------------------------------------


def test_check_bess_fleet_pct_fails_too_high() -> None:
    """SMALL 8.33% -> FAIL."""
    summaries = _three_summaries(
        peak_load_mw_SMALL=12000.0,
        bess_fleet_mw_SMALL=1000.0,  # 8.33%
    )
    result = check_bess_fleet_pct(summaries)
    assert result.status == ConsistencyStatus.FAIL


# ---------------------------------------------------------------------------
# 5. test_check_dr_fleet_pct_passes
# ---------------------------------------------------------------------------


def test_check_dr_fleet_pct_passes() -> None:
    """Ratios 3%, 5%, 4% -> PASS."""
    summaries = _three_summaries(
        peak_load_mw_TINY=8000.0,
        dr_curtail_mw_TINY=240.0,  # 3%
        peak_load_mw_SMALL=12000.0,
        dr_curtail_mw_SMALL=600.0,  # 5%
        peak_load_mw_MEDIUM=40000.0,
        dr_curtail_mw_MEDIUM=1600.0,  # 4%
    )
    result = check_dr_fleet_pct(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 6. test_check_dr_fleet_pct_fails_too_low
# ---------------------------------------------------------------------------


def test_check_dr_fleet_pct_fails_too_low() -> None:
    """TINY 0.5% -> FAIL."""
    summaries = _three_summaries(
        peak_load_mw_TINY=8000.0,
        dr_curtail_mw_TINY=40.0,  # 0.5%
    )
    result = check_dr_fleet_pct(summaries)
    assert result.status == ConsistencyStatus.FAIL


# ---------------------------------------------------------------------------
# 7. test_check_reserve_ratio_consistency_passes
# ---------------------------------------------------------------------------


def test_check_reserve_ratio_consistency_passes() -> None:
    """Spinning ratios 6.0%, 6.5%, 7.0% (diff 1pp) -> PASS."""
    summaries = _three_summaries(
        peak_load_mw_TINY=10000.0,
        spinning_reserve_peak_mw_TINY=600.0,  # 6.0%
        peak_load_mw_SMALL=10000.0,
        spinning_reserve_peak_mw_SMALL=650.0,  # 6.5%
        peak_load_mw_MEDIUM=10000.0,
        spinning_reserve_peak_mw_MEDIUM=700.0,  # 7.0%
    )
    result = check_reserve_ratio_consistency(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 8. test_check_reserve_ratio_consistency_fails
# ---------------------------------------------------------------------------


def test_check_reserve_ratio_consistency_fails() -> None:
    """Spinning ratios 5.0%, 5.5%, 8.0% (diff 3pp) -> FAIL."""
    summaries = _three_summaries(
        peak_load_mw_TINY=10000.0,
        spinning_reserve_peak_mw_TINY=500.0,  # 5.0%
        peak_load_mw_SMALL=10000.0,
        spinning_reserve_peak_mw_SMALL=550.0,  # 5.5%
        peak_load_mw_MEDIUM=10000.0,
        spinning_reserve_peak_mw_MEDIUM=800.0,  # 8.0%
    )
    result = check_reserve_ratio_consistency(summaries)
    assert result.status == ConsistencyStatus.FAIL


# ---------------------------------------------------------------------------
# 9. test_check_renewable_penetration_passes
# ---------------------------------------------------------------------------


def test_check_renewable_penetration_passes() -> None:
    """Ratios 20%, 25%, 30% -> PASS."""
    summaries = _three_summaries(
        peak_load_mw_TINY=10000.0,
        renewable_peak_mw_TINY=2000.0,  # 20%
        peak_load_mw_SMALL=10000.0,
        renewable_peak_mw_SMALL=2500.0,  # 25%
        peak_load_mw_MEDIUM=10000.0,
        renewable_peak_mw_MEDIUM=3000.0,  # 30%
    )
    result = check_renewable_penetration(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 10. test_check_student_t_df_consistency_passes
# ---------------------------------------------------------------------------


def test_check_student_t_df_consistency_passes() -> None:
    """TINY wind=5,solar=6; SMALL wind=6,solar=7; MEDIUM=None -> PASS."""
    summaries = _three_summaries(
        wind_student_t_df_TINY=5.0,
        solar_student_t_df_TINY=6.0,
        wind_student_t_df_SMALL=6.0,
        solar_student_t_df_SMALL=7.0,
        wind_student_t_df_MEDIUM=None,
        solar_student_t_df_MEDIUM=None,
    )
    result = check_student_t_df_consistency(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 11. test_check_student_t_df_consistency_skipped
# ---------------------------------------------------------------------------


def test_check_student_t_df_consistency_skipped() -> None:
    """All None -> SKIPPED."""
    summaries = _three_summaries(
        wind_student_t_df_TINY=None,
        solar_student_t_df_TINY=None,
        wind_student_t_df_SMALL=None,
        solar_student_t_df_SMALL=None,
        wind_student_t_df_MEDIUM=None,
        solar_student_t_df_MEDIUM=None,
    )
    result = check_student_t_df_consistency(summaries)
    assert result.status == ConsistencyStatus.SKIPPED


# ---------------------------------------------------------------------------
# 12. test_check_flowgate_count_range_passes
# ---------------------------------------------------------------------------


def test_check_flowgate_count_range_passes() -> None:
    """Counts 3, 4, 5 -> PASS."""
    summaries = _three_summaries(
        flowgate_count_TINY=3,
        flowgate_count_SMALL=4,
        flowgate_count_MEDIUM=5,
    )
    result = check_flowgate_count_range(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 13. test_check_structural_counts_passes
# ---------------------------------------------------------------------------


def test_check_structural_counts_passes() -> None:
    """Correct counts -> PASS."""
    summaries = _three_summaries(
        bus_count_TINY=39,
        gen_count_TINY=10,
        branch_count_TINY=46,
        bus_count_SMALL=2000,
        gen_count_SMALL=544,
        branch_count_SMALL=3000,
        bus_count_MEDIUM=10000,
        gen_count_MEDIUM=3000,
        branch_count_MEDIUM=13000,
    )
    result = check_structural_counts(summaries)
    assert result.status == ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# 14. test_check_structural_counts_fails_wrong_bus_count
# ---------------------------------------------------------------------------


def test_check_structural_counts_fails_wrong_bus_count() -> None:
    """TINY bus_count=30 -> FAIL."""
    summaries = _three_summaries(bus_count_TINY=30)
    result = check_structural_counts(summaries)
    assert result.status == ConsistencyStatus.FAIL


# ---------------------------------------------------------------------------
# 15. test_build_comparison_table_populates_all_metrics
# ---------------------------------------------------------------------------


def test_build_comparison_table_populates_all_metrics() -> None:
    """12 metrics, 3 networks."""
    summaries = _three_summaries()
    check_results = run_all_cross_network_checks(summaries)
    table = build_comparison_table(summaries, check_results)

    assert isinstance(table, CrossNetworkComparisonTable)
    assert len(table.metrics) == 12
    assert len(table.networks) == 3

    # Every metric has an entry for every network
    for metric in table.metrics:
        assert metric in table.values
        assert metric in table.statuses
        for nid in table.networks:
            assert nid in table.values[metric]
            assert nid in table.statuses[metric]


# ---------------------------------------------------------------------------
# 16. test_validate_cross_network_overall_pass
# ---------------------------------------------------------------------------


def _write_mfile(path: Path, bus_count: int, gen_count: int, branch_count: int) -> None:
    """Write a minimal MATPOWER .m file with the given counts."""
    bus_rows = "\n".join(
        f"\t{i}\t1\t100\t50\t0\t0\t1\t1.0\t0\t345\t1\t1.06\t0.94;"
        for i in range(1, bus_count + 1)
    )
    gen_rows = "\n".join(
        f"\t{i}\t100\t0\t300\t-100\t1.0\t100\t1\t200\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0;"
        for i in range(1, gen_count + 1)
    )
    branch_rows = "\n".join(
        "\t1\t2\t0.01\t0.1\t0.02\t100\t100\t100\t0\t0\t1\t-360\t360;"
        for _ in range(branch_count)
    )
    content = textwrap.dedent(f"""\
        function mpc = testcase
        mpc.bus = [
        {bus_rows}
        ];
        mpc.gen = [
        {gen_rows}
        ];
        mpc.branch = [
        {branch_rows}
        ];
    """)
    path.write_text(content, encoding="utf-8")


def _write_load_csv(path: Path, bus_count: int, load_per_bus: float) -> None:
    """Write load_24h.csv with uniform load."""
    hr_header = ",".join(HR_COLUMNS)
    lines = [f"bus_id,{hr_header}"]
    for i in range(1, bus_count + 1):
        vals = ",".join(str(load_per_bus) for _ in range(24))
        lines.append(f"{i},{vals}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_bess_csv(path: Path, units: list[tuple[str, float, float]]) -> None:
    """Write bess_units.csv. Each tuple is (unit_id, power_mw, roundtrip_eff)."""
    lines = [
        "unit_id,bus,power_mw,energy_mwh,roundtrip_eff,"
        "min_soc_pct,max_soc_pct,initial_soc_pct,cyclic_soc"
    ]
    for uid, pmw, rte in units:
        lines.append(f"{uid},1,{pmw},{pmw * 4},{rte},10,90,50,true")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_dr_csv(path: Path, resources: list[tuple[str, float]]) -> None:
    """Write dr_buses.csv. Each tuple is (dr_id, max_curtail_mw)."""
    lines = [
        "dr_id,bus,max_curtail_mw,max_recover_mw,max_curtail_hours,daily_energy_neutral"
    ]
    for dr_id, mw in resources:
        lines.append(f"{dr_id},1,{mw},{mw},4,true")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_reserve_csv(path: Path, spinning: float, non_spinning: float) -> None:
    """Write reserve_requirements_24h.csv."""
    hr_header = ",".join(HR_COLUMNS)
    lines = [f"product,{hr_header}"]
    spin_vals = ",".join(str(spinning) for _ in range(24))
    ns_vals = ",".join(str(non_spinning) for _ in range(24))
    lines.append(f"spinning,{spin_vals}")
    lines.append(f"non_spinning,{ns_vals}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_renewable_csv(
    dir_path: Path,
    wind_mw: float,
    solar_mw: float,
    gen_count: int = 2,
) -> None:
    """Write wind_forecast_24h.csv and solar_forecast_24h.csv."""
    hr_header = ",".join(HR_COLUMNS)
    per_gen_wind = wind_mw / gen_count
    per_gen_solar = solar_mw / gen_count

    for fname, per_gen in [
        ("wind_forecast_24h.csv", per_gen_wind),
        ("solar_forecast_24h.csv", per_gen_solar),
    ]:
        lines = [f"gen_id,{hr_header}"]
        for i in range(1, gen_count + 1):
            vals = ",".join(str(per_gen) for _ in range(24))
            lines.append(f"gen_{i},{vals}")
        (dir_path / fname).write_text("\n".join(lines), encoding="utf-8")


def _write_flowgates_csv(path: Path, count: int) -> None:
    """Write flowgates.csv with the given number of flowgates."""
    lines = ["flowgate_id,from_bus,to_bus,limit_mw"]
    for i in range(1, count + 1):
        lines.append(f"fg_{i},1,2,100")
    path.write_text("\n".join(lines), encoding="utf-8")


HR_COLUMNS = [f"HR_{h}" for h in range(1, 25)]


def test_validate_cross_network_overall_pass(tmp_path: Path) -> None:
    """Full integration with tmp dirs -> overall_pass=True."""
    ts_base = tmp_path / "timeseries"
    net_base = tmp_path / "networks"

    # Network configs: (dir_name, mfile_name, bus, gen, branch,
    #                   peak_load_per_bus, bess_mw, dr_mw,
    #                   spinning, non_spinning, wind_mw, solar_mw, flowgates)
    configs = [
        (
            "case39",
            "case39_clean.m",
            39,
            10,
            46,
            200.0,  # peak_load = 39 * 200 = 7800
            300.0,  # bess 3.85%
            240.0,  # dr 3.08%
            480.0,  # spinning 6.15%
            320.0,
            800.0,
            800.0,  # renewable 20.5%
            3,
        ),
        (
            "ACTIVSg2000",
            "ACTIVSg2000_clean.m",
            2000,
            544,
            3000,
            6.0,  # peak_load = 2000 * 6 = 12000
            500.0,  # bess 4.17%
            600.0,  # dr 5.0%
            780.0,  # spinning 6.5%
            480.0,
            1500.0,
            1500.0,  # renewable 25%
            4,
        ),
        (
            "ACTIVSg10k",
            "ACTIVSg10k_clean.m",
            10000,
            3000,
            13000,
            4.0,  # peak_load = 10000 * 4 = 40000
            1500.0,  # bess 3.75%
            1600.0,  # dr 4.0%
            2800.0,  # spinning 7.0%
            1600.0,
            6000.0,
            6000.0,  # renewable 30%
            5,
        ),
    ]

    for (
        dir_name,
        mfile_name,
        bus,
        gen,
        branch,
        load_per_bus,
        bess_mw,
        dr_mw,
        spinning,
        non_spinning,
        wind_mw,
        solar_mw,
        fg_count,
    ) in configs:
        net_dir = ts_base / dir_name
        net_dir.mkdir(parents=True)

        # .m file
        net_base.mkdir(parents=True, exist_ok=True)
        _write_mfile(net_base / mfile_name, bus, gen, branch)

        # timeseries CSVs
        _write_load_csv(net_dir / "load_24h.csv", bus, load_per_bus)
        _write_bess_csv(
            net_dir / "bess_units.csv",
            [("bess_1", bess_mw, 0.85)],
        )
        _write_dr_csv(
            net_dir / "dr_buses.csv",
            [("dr_1", dr_mw)],
        )
        _write_reserve_csv(
            net_dir / "reserve_requirements_24h.csv",
            spinning,
            non_spinning,
        )
        _write_renewable_csv(net_dir, wind_mw, solar_mw)
        _write_flowgates_csv(net_dir / "flowgates.csv", fg_count)

    report = validate_cross_network(
        timeseries_base_dir=ts_base,
        networks_base_dir=net_base,
    )

    assert report.overall_pass is True
    assert report.checks_failed == 0
    assert report.total_checks == 8
    assert report.checks_passed + report.checks_skipped == report.total_checks
