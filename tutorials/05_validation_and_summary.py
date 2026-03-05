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
    import pandas as pd
    from pathlib import Path

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

    return (
        CheckStatus,
        IntegrityCheckResult,
        NetworkId,
        NetworkIntegrityReport,
        Path,
        alt,
        bess_dr_main,
        cleanup_main,
        flowgates_main,
        load_profile_main,
        pd,
        reserve_main,
        stochastic_main,
        temporal_params_main,
        validate_network_integrity,
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


if __name__ == "__main__":
    app.run()
