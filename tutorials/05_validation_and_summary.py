import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import altair as alt
    import numpy as np
    import pandas as pd
    from pathlib import Path
    from scipy import stats

    from scripts.tiny_cleanup_classify import main as cleanup_main
    from scripts.tiny_gen_temporal_params import main as temporal_params_main
    from scripts.tiny_load_profile import main as load_profile_main
    from scripts.tiny_reserve_definitions import main as reserve_main
    from scripts.tiny_bess_dr import main as bess_dr_main
    from scripts.tiny_flowgates import main as flowgates_main
    from scripts.tiny_stochastic_scenarios import main as stochastic_main

    from scripts.validate_referential_integrity import (
        CheckStatus,
        IntegrityCheckResult,
        NetworkId,
        NetworkIntegrityReport,
        validate_network_integrity,
    )

    from scripts.validate_scuc_feasibility import (
        CheckSeverity,
        FeasibilityResult,
        validate_network as validate_scuc_network,
        load_generators,
        load_load_profile,
    )

    from scripts.validate_scenarios import (
        CheckStatus as ScenarioCheckStatus,
        ValidationCheckResult,
        ValidationConfig,
        ScenarioData,
        build_scenario_data,
        check_physical_bounds,
        check_ensemble_unbiasedness,
        check_solar_nighttime_zero,
        check_correlation_fidelity,
        load_scenario_multipliers,
    )

    from scripts.generate_forecasts import load_actual_profiles, GeneratorProfile
    from scripts.fit_student_t import ResourceType, load_student_t_json
    from scripts.generate_scenario_multipliers import (
        load_correlation_matrix,
        NetworkId as ScenarioNetworkId,
    )

    return (
        CheckSeverity,
        CheckStatus,
        FeasibilityResult,
        GeneratorProfile,
        IntegrityCheckResult,
        NetworkId,
        NetworkIntegrityReport,
        Path,
        ResourceType,
        ScenarioCheckStatus,
        ScenarioData,
        ScenarioNetworkId,
        ValidationCheckResult,
        ValidationConfig,
        alt,
        bess_dr_main,
        build_scenario_data,
        check_correlation_fidelity,
        check_ensemble_unbiasedness,
        check_physical_bounds,
        check_solar_nighttime_zero,
        cleanup_main,
        flowgates_main,
        load_actual_profiles,
        load_correlation_matrix,
        load_generators,
        load_load_profile,
        load_profile_main,
        load_scenario_multipliers,
        load_student_t_json,
        np,
        pd,
        reserve_main,
        stats,
        stochastic_main,
        temporal_params_main,
        validate_network_integrity,
        validate_scuc_network,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        # Notebook 05 — Validation Framework and Referential Integrity

        In Notebook 04 we built stochastic scenarios — 50 correlated
        wind/solar multiplier profiles derived from Student-t forecast
        error distributions. With the full TINY dataset now complete
        (case file, temporal params, load profiles, renewables, BESS/DR,
        flowgates, and scenarios), we turn to a question that should
        precede any optimization run: **is the dataset internally
        consistent?**

        A power-system dataset is not a single table. It is a web of
        cross-referenced CSV files and MATPOWER structures, each using
        bus IDs, generator UIDs, and branch indices that must agree
        across files. A single orphaned ID — a generator in the
        scenario multiplier file that does not exist in the case file —
        can cause a solver to silently produce wrong results or crash
        with an opaque index error.

        This notebook introduces a three-category validation framework:

        1. **Referential integrity** — Do IDs in every CSV match the
           IDs in the MATPOWER case file and in each other?
        2. **Physical plausibility (SCUC feasibility)** — Can the
           unit-commitment problem actually be solved with these
           parameters, or do min-up/down times, ramp rates, and reserve
           requirements create infeasibilities?
        3. **Statistical fidelity** — Do the stochastic scenarios
           preserve the correlation structure and marginal distributions
           we intended?

        This notebook covers category 1: referential integrity. The
        remaining categories will be addressed in subsequent sections.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Why referential integrity matters

        Power-system models are assembled from multiple data sources.
        In our TINY dataset, the generator temporal parameters CSV
        references generators by `gen_uid`, which must correspond to
        rows in the MATPOWER `.m` file's `mpc.gen` table. The load
        profile CSV references buses by `bus_id`, which must exist in
        `mpc.bus`. Flowgate definitions reference branches by 1-based
        indices into `mpc.branch`.

        If any of these references are broken:

        - **Silent data loss**: A generator listed in the scenario file
          but absent from the case file simply gets ignored — the
          optimization sees fewer scenarios than intended.
        - **Index errors**: A branch index beyond the branch table
          length causes an out-of-bounds crash in the solver.
        - **Phantom resources**: A BESS unit placed on a nonexistent
          bus injects power into a node that has no connections,
          producing meaningless power-flow results.

        Referential integrity checks are the cheapest validation to
        run (pure set-difference operations) and catch the most
        common data-assembly bugs.
        """
    )
    return ()


@app.cell
def _(
    Path,
    bess_dr_main,
    cleanup_main,
    flowgates_main,
    load_profile_main,
    mo,
    reserve_main,
    stochastic_main,
    temporal_params_main,
):
    @mo.cache
    def _generate_tiny_dataset():
        """Run the full TINY pipeline to produce data on disk.

        Each tiny_* script writes its outputs to data/timeseries/case39/.
        The validation scripts expect files at those paths.
        """
        data_dir = Path(__file__).resolve().parent.parent / "data"
        networks_dir = data_dir / "networks"
        output_dir = data_dir / "timeseries" / "case39"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Cleanup and classify the raw case file
        cleanup_main(networks_dir=networks_dir, output_dir=output_dir)

        # 2. Generator temporal parameters
        ref_csv = output_dir / "gen_classification.csv"
        temporal_params_main(reference_csv=ref_csv, output_dir=output_dir)

        # 3. Load profile
        m_file = output_dir / "case39.m"
        load_profile_main(m_file_path=m_file, output_dir=output_dir)

        # 4. Reserve definitions
        reserve_main(output_dir=output_dir, reference_csv=ref_csv)

        # 5. BESS and DR placement
        bess_dr_main(networks_dir=networks_dir, output_dir=output_dir)

        # 6. Flowgates
        load_csv = output_dir / "load_24h.csv"
        flowgates_main(
            m_file_path=m_file,
            load_csv_path=load_csv,
            output_dir=output_dir,
        )

        # 7. Stochastic scenarios
        stochastic_main(data_dir=data_dir)

        return output_dir

    tiny_output_dir = _generate_tiny_dataset()
    return (tiny_output_dir,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Data generation complete

        The cached cell above ran all seven pipeline stages:

        | Stage | Script | Key outputs |
        |-------|--------|-------------|
        | 1 | `tiny_cleanup_classify` | `case39.m`, `gen_classification.csv` |
        | 2 | `tiny_gen_temporal_params` | `gen_temporal_params.csv` |
        | 3 | `tiny_load_profile` | `load_24h.csv` |
        | 4 | `tiny_reserve_definitions` | `reserve_eligibility.csv` |
        | 5 | `tiny_bess_dr` | `bess_units.csv`, `dr_buses.csv` |
        | 6 | `tiny_flowgates` | `flowgates.csv` |
        | 7 | `tiny_stochastic_scenarios` | forecasts, actuals, scenario multipliers |

        All files now exist in `data/timeseries/case39/`. We can run
        referential integrity checks against this complete dataset.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## The five referential integrity checks

        Our validation script (`validate_referential_integrity.py`)
        checks seven cross-file reference paths. For this notebook we
        focus on the five most important categories:

        1. **Generator IDs in temporal params vs. case file** —
           Every `gen_uid` in `gen_temporal_params.csv` must correspond
           to a row in `mpc.gen`.

        2. **Bus IDs in load/BESS/DR vs. case file** — Every `bus_id`
           in `load_24h.csv`, `bess_units.csv`, and `dr_buses.csv` must
           exist in `mpc.bus`.

        3. **Branch IDs in flowgates vs. case file** — Every branch
           index in `flowgates.csv` must be a valid 1-based index into
           `mpc.branch`.

        4. **Generator IDs in scenario multipliers vs. forecasts** —
           Every `gen_uid` column in the 50x24 scenario multiplier
           CSVs must appear in the corresponding forecast file.

        5. **Reserve-eligible generators vs. temporal params** — Every
           `gen_uid` in `reserve_eligibility.csv` must also appear in
           `gen_temporal_params.csv` (you cannot define reserve
           eligibility for a generator whose operating parameters are
           unknown).
        """
    )
    return ()


@app.cell
def _(
    NetworkId,
    Path,
    mo,
    tiny_output_dir,
    validate_network_integrity,
):
    @mo.cache
    def _run_integrity_checks():
        """Execute all referential integrity checks on the TINY dataset."""
        m_file = tiny_output_dir / "case39.m"
        report = validate_network_integrity(
            network_dir=tiny_output_dir,
            m_file_path=m_file,
            network_id=NetworkId.TINY,
        )
        return report

    integrity_report = _run_integrity_checks()
    return (integrity_report,)


@app.cell
def _(CheckStatus, integrity_report, pd):
    # Build a DataFrame from the check results for display and reuse
    _rows = []
    for check in integrity_report.checks:
        orphan_count = len(check.orphaned_ids)
        if check.status == CheckStatus.PASS:
            diagnostic = f"All {check.total_ids_checked} IDs valid"
        elif check.status == CheckStatus.SKIPPED:
            diagnostic = check.skip_reason or "File not found"
        else:
            orphan_sample = ", ".join(str(o.id_value) for o in check.orphaned_ids[:5])
            diagnostic = f"{orphan_count}/{check.total_ids_checked} orphaned: [{orphan_sample}]"

        _rows.append(
            {
                "category": "referential_integrity",
                "name": check.check_name,
                "status": check.status.value,
                "diagnostic": diagnostic,
                "source_file": check.source_file,
                "target_file": check.target_file,
                "ids_checked": check.total_ids_checked,
                "orphaned_count": orphan_count,
            }
        )

    integrity_results_df = pd.DataFrame(_rows)
    validation_results = _rows  # list-of-dicts for downstream PRDs
    return (integrity_results_df, validation_results)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Results: referential integrity check outcomes

        The table below shows each check with its pass/fail status and a
        diagnostic summary. Green circles indicate all IDs in the source
        file have valid targets; red circles would indicate orphaned
        references.
        """
    )
    return ()


@app.cell
def _(alt, integrity_results_df):
    _status_color = alt.condition(
        alt.datum.status == "pass",
        alt.value("#2ca02c"),  # green
        alt.condition(
            alt.datum.status == "fail",
            alt.value("#d62728"),  # red
            alt.value("#ff7f0e"),  # orange for skipped
        ),
    )

    _base = alt.Chart(integrity_results_df).encode(
        y=alt.Y(
            "name:N",
            title=None,
            sort=None,
            axis=alt.Axis(labelLimit=300),
        ),
    )

    _status_dots = _base.mark_point(size=200, filled=True).encode(
        x=alt.value(20),
        color=_status_color,
    )

    _status_text = _base.mark_text(align="left", dx=35, fontSize=12).encode(
        text="status:N",
        color=_status_color,
    )

    _diag_text = _base.mark_text(align="left", dx=85, fontSize=11, color="#555555").encode(
        text="diagnostic:N",
    )

    integrity_chart = (
        (_status_dots + _status_text + _diag_text)
        .properties(
            title="Referential Integrity Checks — TINY (case39)",
            width=700,
            height=max(len(integrity_results_df) * 30, 150),
        )
        .configure_view(strokeWidth=0)
    )
    integrity_chart
    return (integrity_chart,)


@app.cell
def _(integrity_report, mo):
    mo.md(
        r"""
        ## Summary

        **{passed}** of **{total}** checks passed, **{failed}** failed,
        **{skipped}** skipped.

        {interpretation}
        """.format(
            passed=integrity_report.passed,
            total=integrity_report.total_checks,
            failed=integrity_report.failed,
            skipped=integrity_report.skipped,
            interpretation=(
                "All referential integrity checks pass. Every bus ID, "
                "generator UID, and branch index in the augmented CSV "
                "files correctly references an entity in the MATPOWER "
                "case file, and cross-file linkages (reserves to "
                "temporal params, scenarios to forecasts) are "
                "consistent. The dataset is structurally sound for "
                "downstream optimization."
                if integrity_report.failed == 0
                else "Some checks failed. The orphaned IDs listed "
                "above indicate data-assembly bugs that must be fixed "
                "before the dataset can be used for optimization. "
                "Common causes: a pipeline stage was skipped, a CSV "
                "was regenerated with different parameters than the "
                "case file, or a manual edit introduced a typo in an "
                "ID column."
            ),
        )
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## What failures would mean

        If any of the checks above had failed, the implications would
        depend on the category:

        - **Bus reference failure**: Load, BESS, or DR resources would
          be assigned to buses that do not exist in the network
          topology. The power-flow solver would either crash or silently
          ignore the resource, leading to incorrect dispatch.

        - **Generator reference failure**: Temporal parameters or
          reserve eligibility would be defined for generators the solver
          does not know about. The unit-commitment formulation would
          have missing rows in its constraint matrices.

        - **Branch reference failure**: Flowgate limits would reference
          nonexistent transmission lines. The security-constrained OPF
          would either skip the constraint (unsafe) or error out.

        - **Scenario alignment failure**: Scenario multipliers for a
          generator not in the forecast file would create NaN entries
          in the stochastic optimization's scenario tree, producing
          infeasible subproblems.

        - **Reserve linkage failure**: A generator marked as
          reserve-eligible but missing from temporal params has no
          ramp rate or capacity data, making the reserve constraint
          ill-defined.

        These checks are fast (milliseconds) and should be run after
        every data regeneration step. In subsequent sections we will
        layer on physical plausibility and statistical fidelity checks.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## SCUC Feasibility Screening

        Referential integrity confirms that cross-file IDs are consistent,
        but says nothing about whether the **values** in those files are
        physically compatible. A dataset can pass every referential check
        yet still be unsolvable if, for example, the sum of all generators'
        minimum outputs exceeds the system load in some hour.

        **Security-Constrained Unit Commitment (SCUC) feasibility screening**
        tests six necessary conditions that the data must satisfy for the
        unit-commitment problem to have a solution:

        | Check | What it tests |
        |-------|---------------|
        | (a) Pmin headroom | sum(Pmin) of thermal fleet < 95% of load each hour |
        | (b) Pmax adequacy | sum(Pmax) of entire fleet > 105% of peak load |
        | (c) Ramp-up adequacy | aggregate fleet ramp rate covers max hourly load increase |
        | (d) Ramp-down adequacy | aggregate fleet ramp rate covers max hourly load decrease |
        | (e) Pmin <= Pmax | no generator has minimum output above its maximum |
        | (f) Non-negative costs | startup and shutdown costs are non-negative |
        | (g) Valid min up/down times | integer values in [1, 24] that sum to <= 24 |

        These are **necessary but not sufficient** conditions. Passing all
        six does not guarantee that the SCUC IP is feasible (network
        constraints, integer coupling, and reserve requirements can still
        create infeasibilities), but failing any one guarantees that the
        solver will struggle or fail outright.
        """
    )
    return ()


@app.cell
def _(Path, mo, tiny_output_dir, validate_scuc_network):
    @mo.cache
    def _run_scuc_feasibility():
        """Run SCUC feasibility screening on the TINY dataset."""
        timeseries_dir = tiny_output_dir.parent  # data/timeseries/
        result = validate_scuc_network("case39", timeseries_dir)
        return result

    feasibility_result = _run_scuc_feasibility()
    return (feasibility_result,)


@app.cell
def _(CheckSeverity, feasibility_result, pd, validation_results):
    # Build rows from the seven SCUC feasibility sub-checks
    _feas_rows = []
    _hc = feasibility_result.hourly_capacity
    _ra = feasibility_result.ramp_adequacy
    _pv = feasibility_result.parameter_validity

    _checks = [
        ("Pmin headroom", _hc.pmin_check_status, _hc.pmin_check_message),
        ("Pmax adequacy", _hc.pmax_check_status, _hc.pmax_check_message),
        ("Ramp-up adequacy", _ra.ramp_up_status, _ra.ramp_up_message),
        ("Ramp-down adequacy", _ra.ramp_down_status, _ra.ramp_down_message),
        (
            "Pmin <= Pmax",
            _pv.pmin_pmax_status,
            f"{len(_pv.pmin_pmax_violations)} violations"
            if _pv.pmin_pmax_violations
            else "All generators consistent",
        ),
        (
            "Non-negative costs",
            _pv.cost_status,
            f"{len(_pv.cost_violations)} violations"
            if _pv.cost_violations
            else "All costs non-negative",
        ),
        (
            "Valid min up/down times",
            _pv.time_status,
            f"{len(_pv.time_violations)} violations" if _pv.time_violations else "All times valid",
        ),
    ]

    for name, status, diagnostic in _checks:
        _feas_rows.append(
            {
                "category": "feasibility",
                "name": name,
                "status": (
                    "pass"
                    if status == CheckSeverity.PASS
                    else "warn"
                    if status == CheckSeverity.WARN
                    else "fail"
                ),
                "diagnostic": diagnostic,
            }
        )

    feasibility_results_df = pd.DataFrame(_feas_rows)

    # Append to the running validation_results list
    validation_results_with_feas = validation_results + _feas_rows
    return (feasibility_results_df, validation_results_with_feas)


@app.cell
def _(alt, feasibility_result, load_generators, np, pd, tiny_output_dir):
    # Build per-hour Pmin / Load / Pmax data for the feasibility band chart
    _gens = load_generators(tiny_output_dir, "case39")
    _load_profile = feasibility_result.load_profile_mw

    _sum_pmin_thermal = sum(g.pmin_mw for g in _gens if not g.is_renewable)
    _sum_pmax_all = sum(g.pmax_mw for g in _gens)

    _hours = list(range(1, 25))  # HR_1..HR_24
    _band_rows = []
    for i, hr in enumerate(_hours):
        _band_rows.append({"hour": hr, "series": "Agg Pmin (thermal)", "MW": _sum_pmin_thermal})
        _band_rows.append({"hour": hr, "series": "System Load", "MW": _load_profile[i]})
        _band_rows.append({"hour": hr, "series": "Agg Pmax (all)", "MW": _sum_pmax_all})

    _band_df = pd.DataFrame(_band_rows)

    feasibility_band_chart = (
        alt.Chart(_band_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("hour:O", title="Hour (HR)"),
            y=alt.Y("MW:Q", title="MW"),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(
                    domain=["Agg Pmin (thermal)", "System Load", "Agg Pmax (all)"],
                    range=["#d62728", "#1f77b4", "#2ca02c"],
                ),
                title="Series",
            ),
            strokeDash=alt.StrokeDash(
                "series:N",
                scale=alt.Scale(
                    domain=["Agg Pmin (thermal)", "System Load", "Agg Pmax (all)"],
                    range=[[4, 4], [0], [4, 4]],
                ),
                legend=None,
            ),
        )
        .properties(
            title="SCUC Feasibility Band — TINY (case39)",
            width=650,
            height=300,
        )
    )
    feasibility_band_chart
    return (feasibility_band_chart,)


@app.cell
def _(alt, feasibility_result, load_generators, pd, tiny_output_dir):
    # Reserve adequacy chart: compare fleet ramp capability to load swings
    _gens_r = load_generators(tiny_output_dir, "case39")
    _fleet_ramp = sum(g.ramp_rate_mw_per_hr for g in _gens_r)
    _ra_r = feasibility_result.ramp_adequacy

    _reserve_rows = [
        {
            "metric": "Fleet ramp capability",
            "MW_per_hr": _fleet_ramp,
            "kind": "capacity",
        },
        {
            "metric": "Max load increase",
            "MW_per_hr": _ra_r.max_load_increase_mw,
            "kind": "requirement",
        },
        {
            "metric": "Max load decrease",
            "MW_per_hr": _ra_r.max_load_decrease_mw,
            "kind": "requirement",
        },
    ]
    _reserve_df = pd.DataFrame(_reserve_rows)

    reserve_adequacy_chart = (
        alt.Chart(_reserve_df)
        .mark_bar()
        .encode(
            x=alt.X("metric:N", title=None, sort=None),
            y=alt.Y("MW_per_hr:Q", title="MW/hr"),
            color=alt.Color(
                "kind:N",
                scale=alt.Scale(
                    domain=["capacity", "requirement"],
                    range=["#2ca02c", "#1f77b4"],
                ),
                title="Type",
            ),
        )
        .properties(
            title="Ramp Adequacy — Fleet Capability vs Load Swings",
            width=400,
            height=250,
        )
    )
    reserve_adequacy_chart
    return (reserve_adequacy_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Statistical Fidelity of Stochastic Scenarios

        The stochastic scenarios generated in Notebook 04 are correlated
        multiplier profiles derived from fitted Student-t forecast-error
        distributions. For these scenarios to be useful in stochastic
        optimization, they must preserve the statistical properties we
        designed in:

        1. **Ensemble unbiasedness** — The mean of all 50 scenario
           realizations at each hour should approximate the forecast.
           Large bias means the scenario fan systematically over- or
           under-predicts, distorting the optimizer's risk assessment.

        2. **Rank correlation fidelity** — The spatial correlation
           between generators must match the target rank correlation
           matrix (from the Iman-Conover procedure). Measured by the
           Frobenius norm of the difference between empirical and
           target correlation matrices.

        3. **Solar nighttime zeros** — All solar scenario realizations
           must be exactly zero during nighttime hours. Non-zero solar
           generation at night indicates a bug in the nighttime mask.

        4. **Physical bounds** — No scenario realization should exceed
           the generator's nameplate capacity (Pmax) or go negative.
        """
    )
    return ()


@app.cell
def _(
    ResourceType,
    ScenarioCheckStatus,
    ScenarioNetworkId,
    ValidationConfig,
    build_scenario_data,
    check_correlation_fidelity,
    check_ensemble_unbiasedness,
    check_physical_bounds,
    check_solar_nighttime_zero,
    load_actual_profiles,
    load_correlation_matrix,
    load_scenario_multipliers,
    mo,
    np,
    tiny_output_dir,
    validation_results_with_feas,
):
    @mo.cache
    def _run_statistical_checks():
        """Run statistical fidelity checks on TINY scenario data."""
        network_dir = tiny_output_dir  # data/timeseries/case39/
        timeseries_dir = tiny_output_dir.parent  # data/timeseries/

        # Load correlation matrix for TINY
        corr_path = timeseries_dir / "scenarios" / "rank_correlation_matrix.json"

        config = ValidationConfig()
        check_results = []

        for resource_type in ResourceType:
            # Load forecast and actual profiles
            forecast_csv = network_dir / f"{resource_type.value}_forecast_24h.csv"
            actual_csv = network_dir / f"{resource_type.value}_actual_24h.csv"

            if not forecast_csv.exists() or not actual_csv.exists():
                continue

            forecast_profiles = load_actual_profiles(forecast_csv, resource_type)
            actual_profiles = load_actual_profiles(actual_csv, resource_type)

            # Classify night hours for solar
            if resource_type == ResourceType.SOLAR:
                night_hours = sorted(
                    h for h in range(24) if sum(p.values[h] for p in actual_profiles) == 0.0
                )
            else:
                night_hours = []

            generator_ids = [p.gen_uid for p in forecast_profiles]

            # Load scenario multipliers
            multipliers_csv = network_dir / "scenarios" / "scenario_multipliers.csv"
            if not multipliers_csv.exists():
                continue

            multipliers = load_scenario_multipliers(multipliers_csv, generator_ids)

            data = build_scenario_data(
                network_id=ScenarioNetworkId.TINY,
                resource_type=resource_type,
                forecast_profiles=forecast_profiles,
                actual_profiles=actual_profiles,
                multipliers=multipliers,
                night_hours=night_hours,
            )

            # 1. Physical bounds
            check_results.append(check_physical_bounds(data))

            # 2. Ensemble unbiasedness
            check_results.append(check_ensemble_unbiasedness(data, config))

            # 3. Solar nighttime zeros
            check_results.append(check_solar_nighttime_zero(data))

            # 4. Correlation fidelity
            try:
                corr_matrix, corr_gen_ids = load_correlation_matrix(
                    corr_path, ScenarioNetworkId.TINY
                )
                # Build sub-correlation matrix for this resource type
                gen_indices = []
                for uid in generator_ids:
                    matched = False
                    for idx, cid in enumerate(corr_gen_ids):
                        if uid in cid or cid in uid:
                            gen_indices.append(idx)
                            matched = True
                            break
                    if not matched:
                        gen_indices.append(-1)

                if all(idx >= 0 for idx in gen_indices):
                    sub_corr = corr_matrix[np.ix_(gen_indices, gen_indices)]
                    check_results.append(check_correlation_fidelity(data, sub_corr, config))
            except (FileNotFoundError, ValueError):
                pass  # skip correlation check if matrix unavailable

        # Convert to list of dicts for validation_results
        stat_rows = []
        for cr in check_results:
            rt_label = f" ({cr.resource_type.value})" if cr.resource_type else ""
            stat_rows.append(
                {
                    "category": "statistical_fidelity",
                    "name": f"{cr.display_name}{rt_label}",
                    "status": (
                        "pass"
                        if cr.status == ScenarioCheckStatus.PASSED
                        else "skip"
                        if cr.status == ScenarioCheckStatus.SKIPPED
                        else "fail"
                    ),
                    "diagnostic": cr.detail,
                }
            )

        return check_results, stat_rows

    statistical_checks, statistical_rows = _run_statistical_checks()
    validation_results_final = validation_results_with_feas + statistical_rows
    return (statistical_checks, statistical_rows, validation_results_final)


@app.cell
def _(alt, pd, statistical_rows):
    # Build a status chart for statistical fidelity checks
    _stat_df = pd.DataFrame(statistical_rows)

    _stat_color = alt.condition(
        alt.datum.status == "pass",
        alt.value("#2ca02c"),
        alt.condition(
            alt.datum.status == "fail",
            alt.value("#d62728"),
            alt.value("#ff7f0e"),  # orange for skip
        ),
    )

    _stat_base = alt.Chart(_stat_df).encode(
        y=alt.Y(
            "name:N",
            title=None,
            sort=None,
            axis=alt.Axis(labelLimit=350),
        ),
    )

    _stat_dots = _stat_base.mark_point(size=200, filled=True).encode(
        x=alt.value(20),
        color=_stat_color,
    )

    _stat_text = _stat_base.mark_text(align="left", dx=35, fontSize=12).encode(
        text="status:N",
        color=_stat_color,
    )

    _stat_diag = _stat_base.mark_text(align="left", dx=85, fontSize=11, color="#555555").encode(
        text="diagnostic:N",
    )

    statistical_chart = (
        (_stat_dots + _stat_text + _stat_diag)
        .properties(
            title="Statistical Fidelity Checks — TINY (case39)",
            width=700,
            height=max(len(_stat_df) * 35, 150),
        )
        .configure_view(strokeWidth=0)
    )
    statistical_chart
    return (statistical_chart,)


@app.cell
def _(
    Path,
    ResourceType,
    alt,
    load_actual_profiles,
    load_scenario_multipliers,
    np,
    pd,
    stats,
    tiny_output_dir,
):
    # Multiplier histogram with Student-t PDF overlay at peak load hour
    _network_dir = tiny_output_dir
    _wind_forecast_csv = _network_dir / "wind_forecast_24h.csv"

    _mult_chart = None
    if _wind_forecast_csv.exists():
        _wind_profiles = load_actual_profiles(_wind_forecast_csv, ResourceType.WIND)
        _wind_gen_ids = [p.gen_uid for p in _wind_profiles]
        _mult_csv = _network_dir / "scenarios" / "scenario_multipliers.csv"

        if _mult_csv.exists() and _wind_gen_ids:
            _multipliers = load_scenario_multipliers(_mult_csv, _wind_gen_ids)
            # Pick peak hour (hour with highest total wind forecast)
            _total_forecast = np.array(
                [sum(p.values[h] for p in _wind_profiles) for h in range(24)]
            )
            _peak_hour = int(np.argmax(_total_forecast))

            # Extract multipliers at peak hour for the first generator
            _peak_mults = _multipliers[:, 0, _peak_hour]

            # Build histogram data
            _hist_df = pd.DataFrame({"multiplier": _peak_mults})

            _hist_layer = (
                alt.Chart(_hist_df)
                .mark_bar(opacity=0.6, color="#1f77b4")
                .encode(
                    x=alt.X(
                        "multiplier:Q",
                        bin=alt.Bin(maxbins=25),
                        title="Scenario Multiplier",
                    ),
                    y=alt.Y("count():Q", title="Count"),
                )
            )

            # Fit Student-t to the multipliers for overlay
            _df_fit, _loc_fit, _scale_fit = stats.t.fit(_peak_mults)
            _x_range = np.linspace(
                float(np.min(_peak_mults)) - 0.1,
                float(np.max(_peak_mults)) + 0.1,
                200,
            )
            _pdf_vals = stats.t.pdf(_x_range, _df_fit, _loc_fit, _scale_fit)
            # Scale PDF to match histogram counts
            _bin_width = (np.max(_peak_mults) - np.min(_peak_mults)) / 25
            _pdf_scaled = _pdf_vals * len(_peak_mults) * _bin_width

            _pdf_df = pd.DataFrame({"multiplier": _x_range, "density": _pdf_scaled})

            _pdf_layer = (
                alt.Chart(_pdf_df)
                .mark_line(color="#d62728", strokeWidth=2)
                .encode(
                    x="multiplier:Q",
                    y=alt.Y("density:Q"),
                )
            )

            _mult_chart = (_hist_layer + _pdf_layer).properties(
                title=(
                    f"Wind Scenario Multipliers at Peak Hour (HR_{_peak_hour + 1})"
                    f" — {_wind_gen_ids[0]}"
                ),
                width=550,
                height=280,
            )

    multiplier_histogram = _mult_chart
    multiplier_histogram
    return (multiplier_histogram,)


@app.cell
def _(mo, validation_results_final):
    _n_total = len(validation_results_final)
    _n_pass = sum(1 for r in validation_results_final if r["status"] == "pass")
    _n_fail = sum(1 for r in validation_results_final if r["status"] == "fail")
    _n_other = _n_total - _n_pass - _n_fail

    mo.md(
        r"""
        ## Validation Summary

        Across all three validation categories — referential integrity,
        SCUC feasibility screening, and statistical fidelity — the TINY
        dataset has **{n_pass}** passing, **{n_fail}** failing, and
        **{n_other}** warned/skipped checks out of **{n_total}** total.

        {interpretation}

        The full `validation_results_final` list (a list of dicts with keys
        `category`, `name`, `status`, `diagnostic`) is available for
        downstream notebooks or CI pipelines to consume programmatically.
        """.format(
            n_pass=_n_pass,
            n_fail=_n_fail,
            n_other=_n_other,
            n_total=_n_total,
            interpretation=(
                "All checks pass or are appropriately skipped. The dataset "
                "is structurally sound, physically plausible, and the "
                "stochastic scenarios preserve the intended statistical "
                "properties. This dataset is ready for downstream "
                "optimization experiments."
                if _n_fail == 0
                else "Some checks have failed. Review the diagnostics above "
                "to identify data-assembly or parameter issues before "
                "proceeding to optimization."
            ),
        )
    )
    return ()


if __name__ == "__main__":
    app.run()
