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
        ForecastConfig,
        ResourceType,
        StudentTFit,
        compute_capacity_factor_changes,
        fit_student_t_pooled,
        generate_forecast,
        generate_scenario_multipliers,
        load_rts_gmlc_full_year_profiles,
    )

    return (
        DEFAULT_SOLAR_CF_24H,
        DEFAULT_WIND_CF_24H,
        ForecastConfig,
        Path,
        RenewableType,
        ResourceType,
        StudentTFit,
        alt,
        compute_capacity_factor_changes,
        fit_student_t_pooled,
        generate_forecast,
        generate_scenario_multipliers,
        load_rts_gmlc_full_year_profiles,
        np,
        parse_matpower_case,
        pd,
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


if __name__ == "__main__":
    app.run()
