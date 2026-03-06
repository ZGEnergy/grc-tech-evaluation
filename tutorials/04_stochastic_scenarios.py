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

    # Renewable profile synthesis (recap from Notebook 02)
    from scripts.renewable_profiles import (
        DEFAULT_SOLAR_CF_24H,
        DEFAULT_WIND_CF_24H,
        RenewableType,
        synthesize_renewable_profiles,
    )
    from scripts.reconcile_bus_gen import parse_matpower_case
    import grid_plot

    # Stochastic scenario pipeline (Phase 05)
    from scripts.tiny_stochastic_scenarios import (
        CorrelationResult,
        ForecastConfig,
        GeneratorProfile,
        ResourceType,
        StudentTFit,
        add_bias,
        clamp_and_zero_nights,
        compute_capacity_factor_changes,
        estimate_tiny_correlation,
        fit_student_t_pooled,
        generate_forecast,
        generate_scenario_multipliers,
        inject_noise,
        load_rts_gmlc_full_year_profiles,
        map_tiny_to_rts_gmlc_generators,
        smooth_profile,
    )

    return (
        CorrelationResult,
        DEFAULT_SOLAR_CF_24H,
        DEFAULT_WIND_CF_24H,
        ForecastConfig,
        GeneratorProfile,
        Path,
        RenewableType,
        ResourceType,
        StudentTFit,
        add_bias,
        alt,
        clamp_and_zero_nights,
        compute_capacity_factor_changes,
        estimate_tiny_correlation,
        fit_student_t_pooled,
        generate_forecast,
        generate_scenario_multipliers,
        grid_plot,
        inject_noise,
        load_rts_gmlc_full_year_profiles,
        map_tiny_to_rts_gmlc_generators,
        np,
        parse_matpower_case,
        pd,
        smooth_profile,
        stats,
        synthesize_renewable_profiles,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        # Stochastic Scenarios: From Deterministic Profiles to Uncertainty

        **Master seed: 42** — all random number generation in this notebook
        and its downstream pipeline uses seed 42 for reproducibility.
        """
    )
    return ()


@app.cell
def _(mo):
    SEED = 42
    mo.md(
        f"""
        ## Recap: Renewable Profiles from Notebook 02

        In the previous notebook we placed **3 wind** and **2 solar**
        generators on the IEEE 39-bus network and synthesized 24-hour
        generation profiles using RTS-GMLC capacity factor shapes.
        Those profiles represent a single **deterministic** forecast —
        one number per generator per hour.

        But real renewable output is never known exactly in advance.
        Wind ramps unpredictably, clouds roll across solar farms, and
        forecast models carry systematic biases. To stress-test a
        unit commitment or economic dispatch solution, we need many
        **stochastic scenarios** that capture this uncertainty.

        This notebook builds the statistical foundation: we fit
        probability distributions to historical forecast errors, then
        use those distributions to generate realistic scenario
        multipliers. `SEED = {SEED}` is used throughout.
        """
    )
    return (SEED,)


@app.cell
def _(Path, alt, pd, synthesize_renewable_profiles, parse_matpower_case):
    # Reload the 5-generator renewable profiles from the case39 network
    _data_dir = Path(__file__).parent.parent / "data"
    _m_file = _data_dir / "networks" / "case39.m"
    _case_data = parse_matpower_case(_m_file)
    _result = synthesize_renewable_profiles(_case_data, penetration=0.20)

    # Build a tidy DataFrame for charting
    _rows = []
    for _p in _result.wind_profiles + _result.solar_profiles:
        for _h, _mw in enumerate(_p.values_mw, start=1):
            _rows.append(
                {
                    "Generator": _p.gen_uid,
                    "Type": _p.renewable_type.value.title(),
                    "Hour Ending": _h,
                    "MW": _mw,
                }
            )
    profiles_df = pd.DataFrame(_rows)

    profiles_chart = (
        alt.Chart(profiles_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Hour Ending:Q", title="Hour Ending", scale=alt.Scale(domain=[1, 24])),
            y=alt.Y("MW:Q", title="Generation (MW)"),
            color=alt.Color("Generator:N", title="Generator"),
            strokeDash=alt.StrokeDash("Type:N", title="Resource Type"),
            tooltip=["Generator:N", "Type:N", "Hour Ending:Q", "MW:Q"],
        )
        .properties(width=650, height=350, title="Renewable Profiles — 5 Generators x 24 Hours")
    )
    profiles_chart
    return (profiles_chart, profiles_df)


@app.cell
def _(Path, grid_plot, mo, parse_matpower_case, pd, synthesize_renewable_profiles):
    # Topology: wind/solar locations sized by nameplate capacity
    import re as _re

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = parse_matpower_case(_case_file)
    _bus_df = pd.DataFrame(
        [
            {"bus_id": b.bus_id, "bus_type_name": b.bus_type.name, "pd_mw": b.pd}
            for b in _case_data.buses
        ]
    )
    _raw = _case_file.read_text()
    _bm = _re.search(r"mpc\.branch\s*=\s*\[([^\]]*)\]", _raw, _re.DOTALL)
    _brows = []
    for _line in _bm.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _brows.append([float(v) for v in _line.split()])
    _br_df = pd.DataFrame(
        _brows,
        columns=[
            "fbus",
            "tbus",
            "r_pu",
            "x_pu",
            "b_pu",
            "rate_a_mva",
            "rate_b_mva",
            "rate_c_mva",
            "ratio",
            "angle",
            "status",
            "angmin",
            "angmax",
        ],
    )
    _br_df["fbus"] = _br_df["fbus"].astype(int)
    _br_df["tbus"] = _br_df["tbus"].astype(int)

    _G = grid_plot.build_graph(_bus_df, _br_df)
    _fig = grid_plot.plot_base_topology(
        _G,
        title="Renewable Locations: Where Forecast Uncertainty Lives",
        bus_size=8,
        bus_color="#ccc",
    )

    _ren = synthesize_renewable_profiles(_case_data, penetration=0.20)
    _resources = [
        {"bus": u.bus_id, "type": u.renewable_type.value.title(), "label": f"{u.pmax_mw:.0f} MW"}
        for u in _ren.units
    ]
    grid_plot.add_resource_markers(_fig, _resources)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    The wind (green) and solar (yellow) generators are spread across the network.
    Each star is sized and labeled by nameplate capacity. The stochastic scenarios
    we build below will perturb these generators' output — understanding their
    spatial distribution helps anticipate where forecast uncertainty has the
    greatest impact on power flows.
    """)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## What Are Forecast Errors?

        A **forecast error** is the difference between what we predicted
        a generator would produce and what it actually produced. In power
        systems, we typically express errors as hour-over-hour *changes*
        in capacity factor rather than absolute MW values, because:

        1. **Normalization** — changes in capacity factor are comparable
           across generators of different sizes.
        2. **Stationarity** — absolute output follows strong diurnal
           patterns, but the *changes* are closer to stationary, making
           them easier to model with a single distribution.

        The change at hour $h$ for generator $g$ is:

        $$\Delta\text{CF}_{g,h} = \text{CF}_{g,h} - \text{CF}_{g,h-1}$$

        We pool these changes across all generators of the same fuel type
        (wind or solar) and across all 8,760 hours to get a large sample
        for distribution fitting.

        **Data source note:** When RTS-GMLC historical profiles are
        available (in `data/rts_gmlc/`), the fits use real observed
        generation data. When those files are absent, the pipeline falls
        back to **synthetic 8760-hour profiles** that mimic RTS-GMLC
        diurnal patterns with manufactured day-to-day variability. The
        statistical results (degrees of freedom, scale parameters,
        correlations) will differ between the two sources. If you see
        "using synthetic profiles" in the console output, the fits are
        based on generated data, not historical observations.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Why Gaussian Is Inadequate: Heavy Tails

        The standard assumption in many models is that forecast errors
        follow a **Gaussian (normal)** distribution. This is convenient
        but dangerously wrong for renewable generation:

        - **Wind ramps** can be sudden and large — a front passage may
          cut output from 80% to 20% of capacity in one hour.
        - **Cloud transients** produce sharp drops in solar output that
          recover equally quickly.
        - These events sit in the **tails** of the error distribution,
          far from the mean.

        A Gaussian distribution underestimates the probability of these
        extreme events. The **Student-t distribution** is a better fit
        because it has heavier tails controlled by a *degrees of freedom*
        ($\nu$) parameter:

        - $\nu \to \infty$: Student-t converges to Gaussian
        - $\nu \approx 3\text{-}5$: substantially heavier tails
        - $\nu < 3$: variance is infinite (extreme events are common)

        Below, we fit both distributions to the same data and compare.
        """
    )
    return ()


@app.cell
def _(
    Path,
    ResourceType,
    compute_capacity_factor_changes,
    fit_student_t_pooled,
    load_rts_gmlc_full_year_profiles,
    np,
):
    # Load synthetic RTS-GMLC full-year profiles and fit Student-t
    _data_dir = Path(__file__).parent.parent / "data"
    _rts_dir = _data_dir / "rts_gmlc"

    # Wind
    wind_profiles_8760, _wind_ids = load_rts_gmlc_full_year_profiles(_rts_dir, ResourceType.WIND)
    _wind_pmax = np.max(wind_profiles_8760, axis=0)
    wind_cf_changes = compute_capacity_factor_changes(wind_profiles_8760, _wind_pmax)
    wind_fit = fit_student_t_pooled(wind_cf_changes, ResourceType.WIND)

    # Solar
    solar_profiles_8760, _solar_ids = load_rts_gmlc_full_year_profiles(_rts_dir, ResourceType.SOLAR)
    _solar_pmax = np.max(solar_profiles_8760, axis=0)
    solar_cf_changes = compute_capacity_factor_changes(solar_profiles_8760, _solar_pmax)
    solar_fit = fit_student_t_pooled(solar_cf_changes, ResourceType.SOLAR)

    return (
        solar_cf_changes,
        solar_fit,
        solar_profiles_8760,
        wind_cf_changes,
        wind_fit,
        wind_profiles_8760,
    )


@app.cell
def _(alt, np, pd, stats, wind_cf_changes, wind_fit):
    # --- Error Histogram with Student-t and Gaussian PDF overlays (wind) ---
    _pooled = wind_cf_changes.ravel()
    _pooled = _pooled[np.abs(_pooled) > 1e-10]

    # Histogram data
    _counts, _edges = np.histogram(_pooled, bins=80, density=True)
    _centers = 0.5 * (_edges[:-1] + _edges[1:])
    _hist_df = pd.DataFrame({"CF Change": _centers, "Density": _counts})

    # PDF curves
    _x = np.linspace(_pooled.min(), _pooled.max(), 300)
    _t_pdf = stats.t.pdf(_x, wind_fit.df, wind_fit.loc, wind_fit.scale)
    _norm_loc, _norm_scale = stats.norm.fit(_pooled)
    _norm_pdf = stats.norm.pdf(_x, _norm_loc, _norm_scale)

    _pdf_df = pd.DataFrame(
        {
            "CF Change": np.concatenate([_x, _x]),
            "Density": np.concatenate([_t_pdf, _norm_pdf]),
            "Distribution": (
                [f"Student-t (df={wind_fit.df:.1f})"] * len(_x) + ["Gaussian"] * len(_x)
            ),
        }
    )

    _hist_layer = (
        alt.Chart(_hist_df)
        .mark_bar(opacity=0.45, color="#4c78a8")
        .encode(
            x=alt.X("CF Change:Q", title="Hour-over-Hour CF Change"),
            y=alt.Y("Density:Q", title="Probability Density"),
        )
    )

    _pdf_layer = (
        alt.Chart(_pdf_df)
        .mark_line(strokeWidth=2.5)
        .encode(
            x="CF Change:Q",
            y="Density:Q",
            color=alt.Color(
                "Distribution:N",
                scale=alt.Scale(
                    domain=[
                        f"Student-t (df={wind_fit.df:.1f})",
                        "Gaussian",
                    ],
                    range=["#e45756", "#72b7b2"],
                ),
                title="Fit",
            ),
        )
    )

    error_hist_chart = (_hist_layer + _pdf_layer).properties(
        width=650,
        height=350,
        title="Wind CF Change Distribution — Student-t vs Gaussian",
    )
    error_hist_chart
    return (error_hist_chart,)


@app.cell
def _(alt, np, pd, stats, wind_cf_changes, wind_fit):
    # --- QQ Plot: Student-t vs Gaussian ---
    _pooled = wind_cf_changes.ravel()
    _pooled = _pooled[np.abs(_pooled) > 1e-10]
    _sorted = np.sort(_pooled)
    _n = len(_sorted)
    _probs = (np.arange(1, _n + 1) - 0.5) / _n

    # Theoretical quantiles
    _t_quantiles = stats.t.ppf(_probs, wind_fit.df, wind_fit.loc, wind_fit.scale)
    _norm_loc, _norm_scale = stats.norm.fit(_pooled)
    _norm_quantiles = stats.norm.ppf(_probs, _norm_loc, _norm_scale)

    # Subsample for chart performance (every 20th point)
    _step = max(1, _n // 500)
    _idx = np.arange(0, _n, _step)

    _qq_df = pd.DataFrame(
        {
            "Empirical": np.concatenate([_sorted[_idx], _sorted[_idx]]),
            "Theoretical": np.concatenate([_t_quantiles[_idx], _norm_quantiles[_idx]]),
            "Distribution": (
                [f"Student-t (df={wind_fit.df:.1f})"] * len(_idx) + ["Gaussian"] * len(_idx)
            ),
        }
    )

    _lo = min(_sorted[_idx].min(), _t_quantiles[_idx].min())
    _hi = max(_sorted[_idx].max(), _t_quantiles[_idx].max())

    _ref_df = pd.DataFrame({"x": [_lo, _hi], "y": [_lo, _hi]})
    _ref_line = (
        alt.Chart(_ref_df).mark_line(strokeDash=[4, 4], color="gray").encode(x="x:Q", y="y:Q")
    )

    _points = (
        alt.Chart(_qq_df)
        .mark_circle(size=12, opacity=0.6)
        .encode(
            x=alt.X("Theoretical:Q", title="Theoretical Quantile"),
            y=alt.Y("Empirical:Q", title="Empirical Quantile"),
            color=alt.Color(
                "Distribution:N",
                scale=alt.Scale(
                    domain=[
                        f"Student-t (df={wind_fit.df:.1f})",
                        "Gaussian",
                    ],
                    range=["#e45756", "#72b7b2"],
                ),
                title="Fit",
            ),
            tooltip=["Distribution:N", "Theoretical:Q", "Empirical:Q"],
        )
    )

    qq_chart = (_ref_line + _points).properties(
        width=450,
        height=450,
        title="QQ Plot — Student-t Tracks Tails, Gaussian Diverges",
    )
    qq_chart
    return (qq_chart,)


@app.cell
def _(mo, pd, wind_fit, solar_fit):
    # --- Fitted Parameter Summary Table ---
    _params_data = [
        {
            "Resource": "Wind",
            "df (degrees of freedom)": f"{wind_fit.df:.2f}",
            "loc (location)": f"{wind_fit.loc:.6f}",
            "scale": f"{wind_fit.scale:.6f}",
            "Sample Size": f"{wind_fit.sample_size:,}",
            "Generators Pooled": str(wind_fit.num_generators_pooled),
        },
        {
            "Resource": "Solar",
            "df (degrees of freedom)": f"{solar_fit.df:.2f}",
            "loc (location)": f"{solar_fit.loc:.6f}",
            "scale": f"{solar_fit.scale:.6f}",
            "Sample Size": f"{solar_fit.sample_size:,}",
            "Generators Pooled": str(solar_fit.num_generators_pooled),
        },
    ]
    params_table = pd.DataFrame(_params_data)
    mo.md(
        f"""
        ### Fitted Student-t Parameters

        {mo.as_html(params_table)}

        The **degrees of freedom** (df) parameter controls tail heaviness.
        Values in the range 3-8 indicate substantially heavier tails than
        a Gaussian. Lower df means more extreme events are probable.
        """
    )
    return (params_table,)


@app.cell
def _(mo, np, stats, wind_cf_changes, wind_fit):
    # --- Concluding insight: quantify how much more likely extremes are ---
    _pooled = wind_cf_changes.ravel()
    _pooled = _pooled[np.abs(_pooled) > 1e-10]
    _norm_loc, _norm_scale = stats.norm.fit(_pooled)

    # Compare tail probabilities at 3-sigma equivalent
    _threshold = 3.0 * _norm_scale
    _t_tail = 2.0 * stats.t.sf(_threshold, wind_fit.df, loc=wind_fit.loc, scale=wind_fit.scale)
    _g_tail = 2.0 * stats.norm.sf(_threshold, loc=_norm_loc, scale=_norm_scale)

    _ratio = _t_tail / _g_tail if _g_tail > 0 else float("inf")

    mo.md(
        f"""
        ## Key Insight: Extreme Errors Are {_ratio:.1f}x More Likely

        At the 3-sigma threshold ($|\\Delta CF| > {_threshold:.4f}$):

        | Model | Tail Probability | Events per Year (8760h) |
        |-------|-----------------|------------------------|
        | **Student-t** | {_t_tail:.4%} | ~{_t_tail * 8760:.0f} |
        | **Gaussian** | {_g_tail:.4%} | ~{_g_tail * 8760:.0f} |

        The Student-t model predicts extreme forecast errors are
        **{_ratio:.1f}x more likely** than a Gaussian model suggests.
        Ignoring this would underestimate reserve requirements and
        congestion risk. The next cells in this notebook (PRDs 02-05)
        will use these fitted distributions to generate correlated
        scenario multipliers via the Iman-Conover method.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Spatial Correlation

        Renewable generators do not fail independently — they share
        weather drivers that create **spatial correlation** in their
        forecast errors.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Why Spatial Correlation Matters

        When multiple wind or solar farms sit in the same weather
        system, their output errors move together. If we generated
        scenarios *independently* for each generator, the portfolio
        errors would diversify away (by the law of large numbers)
        and we would **understate system-wide risk**: reserve
        shortfalls, congestion, and price spikes would all appear
        less likely than they really are.

        We measure spatial dependence with the **Spearman rank
        correlation** — a non-parametric measure that captures
        monotonic (not just linear) relationships. Unlike Pearson
        correlation, Spearman is robust to the heavy-tailed
        distributions we just fitted and does not assume normality.

        The Spearman rank correlation between generators $i$ and $j$
        is computed by:

        1. Rank each generator's hourly output independently
           across the full year (8 760 hours).
        2. Compute the Pearson correlation of those ranks.

        Values near +1 indicate generators that ramp up and down
        together; values near 0 indicate near-independence.
        """
    )
    return ()


@app.cell
def _(
    Path,
    ResourceType,
    estimate_tiny_correlation,
    load_rts_gmlc_full_year_profiles,
    map_tiny_to_rts_gmlc_generators,
    np,
):
    # Estimate the 5x5 Spearman rank correlation matrix for the TINY network
    _data_dir = Path(__file__).parent.parent / "data"
    _rts_dir = _data_dir / "rts_gmlc"
    _ts_dir = _data_dir / "timeseries" / "case39"

    _wind_8760, _wind_ids = load_rts_gmlc_full_year_profiles(_rts_dir, ResourceType.WIND)
    _solar_8760, _solar_ids = load_rts_gmlc_full_year_profiles(_rts_dir, ResourceType.SOLAR)

    _tiny_units_path = _ts_dir / "renewable_units.csv"
    corr_mappings = map_tiny_to_rts_gmlc_generators(_tiny_units_path, _wind_ids, _solar_ids)

    _all_profiles = np.hstack([_wind_8760, _solar_8760])
    _all_ids = _wind_ids + _solar_ids

    corr_result = estimate_tiny_correlation(_all_profiles, corr_mappings, _all_ids)
    corr_matrix_np = np.array(corr_result.matrix)
    corr_gen_labels = corr_result.generator_order
    return corr_gen_labels, corr_mappings, corr_matrix_np, corr_result


@app.cell
def _(alt, corr_gen_labels, corr_matrix_np, np, pd):
    # Build a tidy DataFrame for the 5x5 Spearman rank-correlation heatmap
    _n = len(corr_gen_labels)
    _hm_rows = []
    for _i in range(_n):
        for _j in range(_n):
            _hm_rows.append(
                {
                    "Generator A": corr_gen_labels[_i],
                    "Generator B": corr_gen_labels[_j],
                    "Spearman r": float(np.round(corr_matrix_np[_i, _j], 2)),
                }
            )
    _hm_df = pd.DataFrame(_hm_rows)

    _base = (
        alt.Chart(_hm_df)
        .encode(
            x=alt.X(
                "Generator A:N",
                sort=corr_gen_labels,
                title=None,
            ),
            y=alt.Y(
                "Generator B:N",
                sort=corr_gen_labels,
                title=None,
            ),
        )
        .properties(width=350, height=350)
    )

    _rect = _base.mark_rect().encode(
        color=alt.Color(
            "Spearman r:Q",
            scale=alt.Scale(scheme="redblue", domain=[-1, 1]),
            title="Spearman r",
        ),
    )

    _text = _base.mark_text(fontSize=12).encode(
        text=alt.Text("Spearman r:Q", format=".2f"),
        color=alt.condition(
            alt.datum["Spearman r"] > 0.6,
            alt.value("white"),
            alt.value("black"),
        ),
    )

    corr_heatmap = (_rect + _text).properties(
        title="5x5 Spearman Rank Correlation — TINY Generators"
    )
    corr_heatmap
    return (corr_heatmap,)


@app.cell
def _(corr_matrix_np, corr_gen_labels, mo, np):
    # Annotate the correlation structure
    _off_diag = corr_matrix_np[~np.eye(len(corr_gen_labels), dtype=bool)]
    _mean_abs = float(np.mean(np.abs(_off_diag)))
    _max_abs = float(np.max(np.abs(_off_diag)))
    mo.md(
        f"""
        ### Correlation Structure

        The heatmap reveals the pairwise Spearman rank correlations
        among the 5 TINY generators (3 wind, 2 solar). Key takeaways:

        - **Mean |r|** across off-diagonal pairs: **{_mean_abs:.2f}**
        - **Max |r|**: **{_max_abs:.2f}**
        - Wind-wind pairs tend to be positively correlated (shared
          weather front), while wind-solar cross-correlations are
          weaker — wind and solar resources are driven by different
          meteorological processes.

        This matrix will be used by the Iman-Conover method to impose
        realistic spatial dependence on the independently drawn
        scenario multipliers.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Forecast Generation

        Real-world forecasts are not just "actual + random noise."
        They exhibit **systematic structure** introduced by the
        forecasting model itself.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ### The Smooth + Bias + Noise Pipeline

        Our forecast generation pipeline applies three transformations
        to an actual generation profile to produce a realistic forecast:

        1. **Smooth** — A centered moving-average kernel (window = 3
           hours) removes sharp hour-to-hour fluctuations. Real
           day-ahead forecasts cannot predict rapid sub-hourly
           variability, so the smoothed curve represents the
           forecaster's "best guess" of the underlying trend.

        2. **Bias** — A systematic offset is added, expressed as a
           fraction of Pmax. Wind forecasts are biased upward
           (+2% of capacity) and solar forecasts biased downward
           (-1% of capacity), reflecting typical NWP model tendencies
           observed in production forecasting.

        3. **Noise** — Calibrated Student-t noise is injected, scaled
           by the actual generation level at each hour. This ensures
           errors are heteroscedastic: large when output is high,
           zero when output is zero (night hours for solar).

        After noise injection the forecast is clamped to [0, Pmax]
        and solar nighttime hours are forced to zero.
        """
    )
    return ()


@app.cell
def _(
    ForecastConfig,
    GeneratorProfile,
    SEED,
    generate_forecast,
    np,
    profiles_df,
    solar_fit,
    wind_fit,
):
    # Generate forecast profiles for all 5 TINY generators
    _fc_config = ForecastConfig(
        smoothing_window=3,
        wind_bias_fraction=0.02,
        solar_bias_fraction=-0.01,
        master_seed=SEED,
    )
    _rng = np.random.Generator(np.random.PCG64(SEED))

    # Build GeneratorProfile objects from profiles_df
    _gen_uids = profiles_df["Generator"].unique().tolist()

    fc_actuals: list[GeneratorProfile] = []
    fc_forecasts: list[GeneratorProfile] = []

    for _uid in _gen_uids:
        _sub = profiles_df[profiles_df["Generator"] == _uid].sort_values("Hour Ending")
        _mw_vals = _sub["MW"].values
        _pmax = float(np.max(_mw_vals)) if np.any(_mw_vals > 0) else 0.0
        _rtype = _sub["Type"].iloc[0].lower()
        _t_fit = wind_fit if _rtype == "wind" else solar_fit

        _actual_prof = GeneratorProfile(
            gen_uid=_uid,
            bus_id=0,
            pmax_mw=_pmax,
            hourly_mw=_mw_vals.copy(),
        )
        fc_actuals.append(_actual_prof)

        _fc_prof = generate_forecast(_actual_prof, _t_fit, _fc_config, _rng)
        fc_forecasts.append(_fc_prof)

    fc_config_used = _fc_config
    return fc_actuals, fc_config_used, fc_forecasts


@app.cell
def _(
    add_bias,
    alt,
    fc_actuals,
    fc_config_used,
    np,
    pd,
    smooth_profile,
    wind_fit,
):
    # Step-by-step layered chart for the first wind generator
    _gen = fc_actuals[0]
    _hours = list(range(1, 25))

    _smoothed = smooth_profile(_gen.hourly_mw, fc_config_used.smoothing_window)
    _biased = add_bias(_smoothed, _gen.pmax_mw, fc_config_used.wind_bias_fraction)

    # Re-generate forecast deterministically for this one generator
    _rng_step = np.random.Generator(np.random.PCG64(42))
    from scripts.tiny_stochastic_scenarios import inject_noise as _inj

    _noisy = _inj(_biased, _gen.hourly_mw, wind_fit, _rng_step)
    _forecast = np.clip(_noisy, 0.0, _gen.pmax_mw)

    _step_rows = []
    for _h, _hr in enumerate(_hours):
        _step_rows.append({"Hour Ending": _hr, "MW": _gen.hourly_mw[_h], "Layer": "1 Actual"})
        _step_rows.append({"Hour Ending": _hr, "MW": _smoothed[_h], "Layer": "2 Smoothed"})
        _step_rows.append({"Hour Ending": _hr, "MW": _biased[_h], "Layer": "3 Biased"})
        _step_rows.append({"Hour Ending": _hr, "MW": _forecast[_h], "Layer": "4 Forecast"})
    _step_df = pd.DataFrame(_step_rows)

    step_by_step_chart = (
        alt.Chart(_step_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "Hour Ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y("MW:Q", title="Generation (MW)"),
            color=alt.Color(
                "Layer:N",
                title="Pipeline Stage",
                sort=["1 Actual", "2 Smoothed", "3 Biased", "4 Forecast"],
                scale=alt.Scale(
                    domain=[
                        "1 Actual",
                        "2 Smoothed",
                        "3 Biased",
                        "4 Forecast",
                    ],
                    range=["#4c78a8", "#f58518", "#e45756", "#54a24b"],
                ),
            ),
            strokeDash=alt.StrokeDash(
                "Layer:N",
                sort=["1 Actual", "2 Smoothed", "3 Biased", "4 Forecast"],
            ),
            tooltip=["Layer:N", "Hour Ending:Q", "MW:Q"],
        )
        .properties(
            width=650,
            height=350,
            title=(f"Forecast Pipeline — {_gen.gen_uid} (Actual → Smoothed → Biased → Forecast)"),
        )
    )
    step_by_step_chart
    return (step_by_step_chart,)


@app.cell
def _(alt, fc_actuals, fc_forecasts, pd):
    # Faceted forecast vs actual grid — all 5 generators
    _facet_rows = []
    for _actual, _forecast in zip(fc_actuals, fc_forecasts):
        for _h in range(24):
            _hr = _h + 1
            _facet_rows.append(
                {
                    "Generator": _actual.gen_uid,
                    "Hour Ending": _hr,
                    "MW": _actual.hourly_mw[_h],
                    "Series": "Actual",
                }
            )
            _facet_rows.append(
                {
                    "Generator": _forecast.gen_uid,
                    "Hour Ending": _hr,
                    "MW": _forecast.hourly_mw[_h],
                    "Series": "Forecast",
                }
            )
    _facet_df = pd.DataFrame(_facet_rows)

    forecast_grid = (
        alt.Chart(_facet_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "Hour Ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y("MW:Q", title="MW"),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(
                    domain=["Actual", "Forecast"],
                    range=["#4c78a8", "#e45756"],
                ),
            ),
            tooltip=["Generator:N", "Series:N", "Hour Ending:Q", "MW:Q"],
        )
        .properties(width=250, height=180)
        .facet(
            facet=alt.Facet("Generator:N", title="Generator"),
            columns=3,
        )
        .properties(title="Forecast vs Actual — All 5 TINY Generators")
    )
    forecast_grid
    return (forecast_grid,)


@app.cell
def _(fc_actuals, fc_forecasts, mo, np, pd):
    # RMSE and bias statistics per generator
    _stat_rows = []
    for _actual, _forecast in zip(fc_actuals, fc_forecasts):
        _err = _forecast.hourly_mw - _actual.hourly_mw
        _rmse = float(np.sqrt(np.mean(_err**2)))
        _bias = float(np.mean(_err))
        _stat_rows.append(
            {
                "Generator": _actual.gen_uid,
                "RMSE (MW)": f"{_rmse:.2f}",
                "Bias (MW)": f"{_bias:.2f}",
                "Pmax (MW)": f"{_actual.pmax_mw:.1f}",
                "RMSE / Pmax": f"{_rmse / _actual.pmax_mw:.2%}" if _actual.pmax_mw > 0 else "N/A",
            }
        )
    stats_table = pd.DataFrame(_stat_rows)
    mo.md(
        f"""
        ### Forecast Quality Statistics

        {mo.as_html(stats_table)}

        **RMSE** (root mean squared error) measures overall forecast
        accuracy. **Bias** captures systematic over- or
        under-prediction. Positive bias means the forecast tends to
        over-predict generation; negative bias means under-prediction.

        The RMSE/Pmax ratio puts the error in context: a 5-10%
        ratio is typical for day-ahead wind forecasts; solar
        forecasts tend to have lower ratios during daylight hours
        but are trivially zero at night.
        """
    )
    return (stats_table,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Scenario Generation via Iman-Conover

        With the statistical foundation in place — fitted Student-t
        marginals, estimated spatial correlation, and realistic forecast
        profiles — we can now generate **stochastic scenarios** that
        capture the full range of plausible renewable outcomes.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ### The Iman-Conover Method

        The **Iman-Conover method** (1982) is a rank-reordering technique
        that imposes a target rank correlation structure on independently
        drawn samples **without altering their marginal distributions**.

        The algorithm proceeds in four steps:

        1. **Draw independent samples** — For each generator, draw $N$
           samples from its fitted Student-t distribution. At this stage
           the samples are statistically independent across generators.

        2. **Construct a score matrix** — Generate a reference matrix of
           standard normal scores (van der Waerden scores) and compute
           its sample correlation.

        3. **Transform scores** — Apply a Cholesky-based linear
           transformation so the score matrix has the *target* rank
           correlation (the Spearman matrix from the previous section).

        4. **Reorder originals** — Use the rank ordering of the
           transformed scores to permute the original Student-t samples.
           Each column retains its exact original values (preserving the
           heavy-tailed marginal), but the cross-column rank ordering
           now matches the target correlation.

        This is the standard approach in power systems for generating
        spatially correlated renewable scenarios — it respects both the
        heavy tails we fitted and the spatial dependence we measured.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Multiplicative Scenario Factors

        The Iman-Conover method produces correlated *error samples* in
        capacity-factor-change units. To apply these errors to a forecast
        profile, we convert them to **multiplicative factors**:

        $$\text{multiplier}_{s,g,h} = 1 + \frac{\text{error}_{s,g,h}}{\text{forecast}_{g,h}}$$

        The scenario MW value is then:

        $$\text{MW}_{s,g,h} = \text{multiplier}_{s,g,h} \times \text{forecast}_{g,h}$$

        When the forecast is zero (e.g., solar at night), the multiplier
        is set to 1.0 — there is no generation to scale.

        This multiplicative formulation has two advantages over additive
        errors:

        - **Heteroscedasticity** — Errors scale with output level,
          matching the observation that high-output hours have larger
          absolute errors.
        - **Interpretability** — A multiplier of 1.3 means "30% more
          than forecast," regardless of generator size.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Physical Clamping

        Raw multipliers can produce physically impossible generation
        values — negative MW or output exceeding nameplate capacity.
        After computing the raw multipliers, we apply two-sided clamping:

        $$\text{multiplier}_{s,g,h} \in \left[0,\;\frac{P_{\max,g}}{\text{forecast}_{g,h}}\right]$$

        - **Lower bound = 0** — Generation cannot be negative.
        - **Upper bound = Pmax / forecast** — The scenario MW cannot
          exceed the generator's nameplate capacity.

        For solar generators during nighttime hours, the multiplier is
        forced to 1.0 regardless of the drawn sample, because both the
        forecast and actual output are physically zero.

        A small fraction of samples are typically clamped (< 5%),
        confirming that the fitted distributions are well-calibrated
        but that extreme-tail events do need physical enforcement.
        """
    )
    return ()


@app.cell
def _(
    ForecastConfig,
    SEED,
    corr_result,
    fc_actuals,
    fc_forecasts,
    generate_scenario_multipliers,
    profiles_df,
    solar_fit,
    wind_fit,
):
    # Generate 50 correlated scenario multipliers via Iman-Conover
    _wind_gen_uids = profiles_df[profiles_df["Type"] == "Wind"]["Generator"].unique().tolist()
    _solar_gen_uids = profiles_df[profiles_df["Type"] == "Solar"]["Generator"].unique().tolist()

    # Split forecasts and actuals into wind/solar lists preserving order
    _wind_fc = [f for f in fc_forecasts if f.gen_uid in _wind_gen_uids]
    _solar_fc = [f for f in fc_forecasts if f.gen_uid in _solar_gen_uids]
    _wind_act = [a for a in fc_actuals if a.gen_uid in _wind_gen_uids]
    _solar_act = [a for a in fc_actuals if a.gen_uid in _solar_gen_uids]

    _sc_config = ForecastConfig(
        smoothing_window=3,
        wind_bias_fraction=0.02,
        solar_bias_fraction=-0.01,
        master_seed=SEED,
        num_scenarios=50,
    )

    scenario_set = generate_scenario_multipliers(
        _wind_fc,
        _solar_fc,
        wind_fit,
        solar_fit,
        corr_result,
        _sc_config,
    )

    # Build convenience lists aligned with scenario_set.generator_order
    sc_all_forecasts = list(_wind_fc) + list(_solar_fc)
    sc_all_actuals = list(_wind_act) + list(_solar_act)
    return sc_all_actuals, sc_all_forecasts, scenario_set


@app.cell
def _(alt, np, pd, sc_all_actuals, sc_all_forecasts, scenario_set):
    # --- Wind Fan Plot ---
    # Find wind generators in scenario_set.generator_order
    _wind_indices = [
        i for i, uid in enumerate(scenario_set.generator_order) if "WIND" in uid.upper()
    ]
    _wi = _wind_indices[0]  # first wind generator
    _uid = scenario_set.generator_order[_wi]
    _fc_mw = sc_all_forecasts[_wi].hourly_mw
    _act_mw = sc_all_actuals[_wi].hourly_mw
    _hours = list(range(1, 25))

    # Build scenario MW traces: scenario_mw = multiplier * forecast
    _fan_rows = []
    for _s in range(scenario_set.num_scenarios):
        for _h_idx, _he in enumerate(_hours):
            _mw = float(scenario_set.multipliers[_s, _wi, _h_idx] * _fc_mw[_h_idx])
            _fan_rows.append({"Hour Ending": _he, "MW": _mw, "Scenario": f"S{_s + 1}"})
    _fan_df = pd.DataFrame(_fan_rows)

    # Forecast and actual reference lines
    _ref_rows = []
    for _h_idx, _he in enumerate(_hours):
        _ref_rows.append(
            {
                "Hour Ending": _he,
                "MW": float(_fc_mw[_h_idx]),
                "Series": "Forecast",
            }
        )
        _ref_rows.append(
            {
                "Hour Ending": _he,
                "MW": float(_act_mw[_h_idx]),
                "Series": "Actual",
            }
        )
    _ref_df = pd.DataFrame(_ref_rows)

    _scenario_layer = (
        alt.Chart(_fan_df)
        .mark_line(opacity=0.15, color="steelblue")
        .encode(
            x=alt.X(
                "Hour Ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y("MW:Q", title="Generation (MW)"),
            detail="Scenario:N",
        )
    )

    _fc_layer = (
        alt.Chart(_ref_df[_ref_df["Series"] == "Forecast"])
        .mark_line(strokeDash=[5, 3], color="#e45756", strokeWidth=2)
        .encode(
            x="Hour Ending:Q",
            y="MW:Q",
        )
    )

    _act_layer = (
        alt.Chart(_ref_df[_ref_df["Series"] == "Actual"])
        .mark_line(color="#2d004b", strokeWidth=2.5)
        .encode(
            x="Hour Ending:Q",
            y="MW:Q",
        )
    )

    # Compute y-axis range for annotation positioning
    _all_mw = np.concatenate([_fan_df["MW"].values, _fc_mw, _act_mw])
    _y_max = float(np.max(_all_mw))

    # Legend as text annotations
    _legend_df = pd.DataFrame(
        [
            {"label": "Forecast (dashed)", "x": 20, "y": _y_max * 0.98},
            {"label": "Actual (bold)", "x": 20, "y": _y_max * 0.92},
            {"label": "50 scenarios", "x": 20, "y": _y_max * 0.86},
        ]
    )

    wind_fan_chart = alt.layer(_scenario_layer, _fc_layer, _act_layer).properties(
        width=650,
        height=380,
        title=f"Wind Fan Plot — {_uid} (50 Scenarios)",
    )
    wind_fan_chart
    return (wind_fan_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        This is the dramatic moment where uncertainty becomes visible.
        Each translucent trace is one plausible realization of wind
        output; the **dashed red line** is the day-ahead forecast and
        the **bold dark line** is the actual outcome. The spread of the
        fan quantifies the range of outcomes a unit commitment solver
        must hedge against.

        Notice how the fan widens during high-output hours and narrows
        near zero — this is the heteroscedastic structure built into our
        multiplicative error model.
        """
    )
    return ()


@app.cell
def _(alt, np, pd, sc_all_actuals, sc_all_forecasts, scenario_set):
    # --- Solar Fan Plot ---
    _solar_indices = [
        i for i, uid in enumerate(scenario_set.generator_order) if "SOLAR" in uid.upper()
    ]
    _si = _solar_indices[0]  # first solar generator
    _suid = scenario_set.generator_order[_si]
    _sfc_mw = sc_all_forecasts[_si].hourly_mw
    _sact_mw = sc_all_actuals[_si].hourly_mw
    _shours = list(range(1, 25))

    _sfan_rows = []
    for _s in range(scenario_set.num_scenarios):
        for _h_idx, _he in enumerate(_shours):
            _mw = float(scenario_set.multipliers[_s, _si, _h_idx] * _sfc_mw[_h_idx])
            _sfan_rows.append({"Hour Ending": _he, "MW": _mw, "Scenario": f"S{_s + 1}"})
    _sfan_df = pd.DataFrame(_sfan_rows)

    _sref_rows = []
    for _h_idx, _he in enumerate(_shours):
        _sref_rows.append(
            {
                "Hour Ending": _he,
                "MW": float(_sfc_mw[_h_idx]),
                "Series": "Forecast",
            }
        )
        _sref_rows.append(
            {
                "Hour Ending": _he,
                "MW": float(_sact_mw[_h_idx]),
                "Series": "Actual",
            }
        )
    _sref_df = pd.DataFrame(_sref_rows)

    _sscenario_layer = (
        alt.Chart(_sfan_df)
        .mark_line(opacity=0.15, color="goldenrod")
        .encode(
            x=alt.X(
                "Hour Ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y("MW:Q", title="Generation (MW)"),
            detail="Scenario:N",
        )
    )

    _sfc_layer = (
        alt.Chart(_sref_df[_sref_df["Series"] == "Forecast"])
        .mark_line(strokeDash=[5, 3], color="#e45756", strokeWidth=2)
        .encode(x="Hour Ending:Q", y="MW:Q")
    )

    _sact_layer = (
        alt.Chart(_sref_df[_sref_df["Series"] == "Actual"])
        .mark_line(color="#2d004b", strokeWidth=2.5)
        .encode(x="Hour Ending:Q", y="MW:Q")
    )

    solar_fan_chart = alt.layer(_sscenario_layer, _sfc_layer, _sact_layer).properties(
        width=650,
        height=380,
        title=f"Solar Fan Plot — {_suid} (50 Scenarios)",
    )
    solar_fan_chart
    return (solar_fan_chart,)


@app.cell
def _(alt, np, pd, scenario_set):
    # --- Multiplier Histogram at Peak Hour (HE 14, index 13) ---
    _peak_h = 13  # Hour Ending 14 (peak solar / high wind)
    _mult_rows = []
    for j, uid in enumerate(scenario_set.generator_order):
        for _s in range(scenario_set.num_scenarios):
            _mult_rows.append(
                {
                    "Multiplier": float(scenario_set.multipliers[_s, j, _peak_h]),
                    "Generator": uid,
                }
            )
    _mult_df = pd.DataFrame(_mult_rows)

    multiplier_hist = (
        alt.Chart(_mult_df)
        .mark_bar(opacity=0.6)
        .encode(
            x=alt.X(
                "Multiplier:Q",
                bin=alt.Bin(maxbins=30),
                title="Scenario Multiplier at HE 14",
            ),
            y=alt.Y("count()", title="Count"),
            color=alt.Color("Generator:N", title="Generator"),
        )
        .properties(
            width=650,
            height=350,
            title="Multiplier Distribution at Peak Hour (HE 14)",
        )
    )
    multiplier_hist
    return (multiplier_hist,)


@app.cell
def _(alt, np, pd, scenario_set):
    # --- Two-Generator Scatter Plot showing spatial correlation ---
    # Use the first two generators in scenario_set.generator_order
    _g0 = 0
    _g1 = 1
    _uid0 = scenario_set.generator_order[_g0]
    _uid1 = scenario_set.generator_order[_g1]

    # Use multipliers at HE 14 (peak hour) for both generators
    _scatter_rows = []
    for _s in range(scenario_set.num_scenarios):
        _scatter_rows.append(
            {
                _uid0: float(scenario_set.multipliers[_s, _g0, 13]),
                _uid1: float(scenario_set.multipliers[_s, _g1, 13]),
                "Scenario": _s + 1,
            }
        )
    _scatter_df = pd.DataFrame(_scatter_rows)

    # Compute Spearman r for annotation
    from scipy.stats import spearmanr as _spearmanr

    _sr, _ = _spearmanr(_scatter_df[_uid0].values, _scatter_df[_uid1].values)

    corr_scatter = (
        alt.Chart(_scatter_df)
        .mark_circle(size=50, opacity=0.6, color="#4c78a8")
        .encode(
            x=alt.X(
                f"{_uid0}:Q",
                title=f"Multiplier — {_uid0}",
            ),
            y=alt.Y(
                f"{_uid1}:Q",
                title=f"Multiplier — {_uid1}",
            ),
            tooltip=[
                "Scenario:Q",
                alt.Tooltip(f"{_uid0}:Q", format=".3f"),
                alt.Tooltip(f"{_uid1}:Q", format=".3f"),
            ],
        )
        .properties(
            width=420,
            height=420,
            title=(f"Scenario Multipliers at HE 14 — Spearman r = {_sr:.2f}"),
        )
    )
    corr_scatter
    return (corr_scatter,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Diagnostic Summary

        The **multiplier histogram** shows the distribution of scenario
        factors at peak hour (HE 14). Values cluster around 1.0 (the
        forecast) with heavy tails reflecting the Student-t marginals.
        The spread differs by generator because each has a different
        forecast level and Pmax, producing different clamping bounds.

        The **scatter plot** reveals the spatial correlation imposed by
        the Iman-Conover method: generators that share weather drivers
        (e.g., two wind farms) show a clear positive association in
        their scenario multipliers, while wind-solar pairs are more
        diffuse. This dependence structure is critical — without it,
        portfolio-level risk would be artificially diversified away.
        """
    )
    return ()


@app.cell
def _(
    Path, grid_plot, mo, np, parse_matpower_case, pd, scenario_set, synthesize_renewable_profiles
):
    # Topology: uncertainty magnitude per renewable bus (std dev of multipliers at peak)
    import re as _re
    import plotly.graph_objects as _go

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = parse_matpower_case(_case_file)
    _bus_df = pd.DataFrame(
        [
            {"bus_id": b.bus_id, "bus_type_name": b.bus_type.name, "pd_mw": b.pd}
            for b in _case_data.buses
        ]
    )
    _raw = _case_file.read_text()
    _bm = _re.search(r"mpc\.branch\s*=\s*\[([^\]]*)\]", _raw, _re.DOTALL)
    _brows = []
    for _line in _bm.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _brows.append([float(v) for v in _line.split()])
    _br_df = pd.DataFrame(
        _brows,
        columns=[
            "fbus",
            "tbus",
            "r_pu",
            "x_pu",
            "b_pu",
            "rate_a_mva",
            "rate_b_mva",
            "rate_c_mva",
            "ratio",
            "angle",
            "status",
            "angmin",
            "angmax",
        ],
    )
    _br_df["fbus"] = _br_df["fbus"].astype(int)
    _br_df["tbus"] = _br_df["tbus"].astype(int)

    _G = grid_plot.build_graph(_bus_df, _br_df)
    _fig = grid_plot.plot_base_topology(
        _G,
        title="Forecast Uncertainty by Renewable Bus (Std Dev of Multipliers at Peak)",
        bus_size=8,
        bus_color="#ccc",
    )

    _ren = synthesize_renewable_profiles(_case_data, penetration=0.20)
    _peak_h = 13  # HE14 (0-indexed)
    for _gi, _uid in enumerate(scenario_set.generator_order):
        _std = float(np.std(scenario_set.multipliers[:, _gi, _peak_h]))
        _unit = next((u for u in _ren.units if u.gen_uid == _uid), None)
        if _unit is None:
            continue
        _bx, _by = grid_plot.BUS_POSITIONS[_unit.bus_id]
        _rtype = _unit.renewable_type.value.title()
        _color = grid_plot.FUEL_COLORS.get(_rtype, "#888")
        _sz = max(12, min(40, int(12 + _std * 200)))
        _fig.add_trace(
            _go.Scatter(
                x=[_bx],
                y=[_by],
                mode="markers+text",
                marker=dict(
                    size=_sz,
                    color=_color,
                    symbol="star",
                    line=dict(width=1.5, color="white"),
                    opacity=0.8,
                ),
                text=[f"std={_std:.3f}"],
                textposition="bottom center",
                textfont=dict(size=8),
                hovertext=f"{_uid}<br>{_rtype} @ Bus {_unit.bus_id}<br>Multiplier Std Dev: {_std:.4f}",
                hoverinfo="text",
                showlegend=False,
            )
        )
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Larger stars indicate higher forecast uncertainty at peak hour. Wind generators
    tend to have wider multiplier spread than solar (whose peak-hour output is near
    maximum and thus more predictable). This map answers: **which parts of the grid
    face the most forecast uncertainty?** — critical for understanding where reserve
    capacity and flexible resources have the most value.
    """)
    return


@app.cell
def _(mo, scenario_set):
    _n_sc = scenario_set.num_scenarios
    _n_gen = len(scenario_set.generator_order)
    mo.md(
        f"""
        ## Summary: From Uncertainty to Optimization

        This notebook built a complete stochastic scenario pipeline:

        1. **Student-t fitting** — Heavy-tailed marginals for wind and
           solar forecast errors, calibrated from RTS-GMLC data.
        2. **Spatial correlation** — 5x5 Spearman rank correlation
           estimated from mapped RTS-GMLC profiles.
        3. **Forecast generation** — Smooth + bias + noise pipeline
           producing realistic day-ahead forecasts.
        4. **Iman-Conover scenarios** — **{_n_sc} correlated scenarios**
           across **{_n_gen} generators x 24 hours**, preserving both
           marginal distributions and spatial dependence.

        These {_n_sc} scenarios are the input to a **two-stage stochastic
        unit commitment** formulation:

        - **Stage 1 (here-and-now):** Commit generators based on the
          forecast, before uncertainty is revealed.
        - **Stage 2 (wait-and-see):** For each scenario, re-dispatch
          generation to meet the realized renewable output, incurring
          balancing costs for any mismatch.

        The objective minimizes expected cost across all {_n_sc} scenarios,
        producing a commitment plan that is robust to the full range of
        plausible renewable outcomes — including the extreme tail events
        that a Gaussian model would underestimate.
        """
    )
    return ()


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Next: Notebook 05 — Stochastic Unit Commitment

        With 50 correlated scenarios in hand, Notebook 05 will formulate
        and solve a **two-stage stochastic unit commitment** problem:

        - **Decision variables:** binary on/off status for each thermal
          generator at each hour (Stage 1), plus dispatch MW per
          scenario (Stage 2).
        - **Constraints:** Min up/down times, ramp limits, reserve
          requirements, and power balance per scenario.
        - **Objective:** Minimize expected total cost (startup +
          no-load + energy + reserve shortfall penalties) across all
          scenarios.

        The fan plots above show *why* this matters: a deterministic
        UC using only the forecast would be caught off-guard by the
        tails of the uncertainty distribution. The stochastic
        formulation hedges against those tails by construction.
        """
    )
    return ()


if __name__ == "__main__":
    app.run()
