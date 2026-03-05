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
        (wind or solar) and across all 8,760 hours of a synthetic year
        to get a large sample for distribution fitting.
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


if __name__ == "__main__":
    app.run()
