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

    # Pipeline scripts for the full notebook (PRDs 01-05)
    from scripts.tiny_cleanup_classify import (
        CASE39_CLASSIFICATION_TABLE,
        Case39GenClassification,
        RtsGmlcClass,
    )
    from scripts.tiny_gen_temporal_params import (
        assign_all_temporal_params,
        load_gen_classification,
        load_reference_table,
    )
    from scripts.tiny_load_profile import synthesize_load_profile
    from scripts.tiny_reserve_definitions import (
        build_reserve_requirements,
        compute_all_eligibilities,
        define_reserves,
    )
    from scripts.renewable_profiles import (
        synthesize_renewable_profiles,
    )
    from scripts.reconcile_bus_gen import parse_matpower_case

    return (
        CASE39_CLASSIFICATION_TABLE,
        Case39GenClassification,
        Path,
        RtsGmlcClass,
        alt,
        assign_all_temporal_params,
        build_reserve_requirements,
        compute_all_eligibilities,
        define_reserves,
        load_gen_classification,
        load_reference_table,
        parse_matpower_case,
        pd,
        synthesize_load_profile,
        synthesize_renewable_profiles,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        # Generator Calibration: From Snapshot to SCUC

        ## What is Security-Constrained Unit Commitment (SCUC)?

        A MATPOWER case file gives us a **single-instant snapshot**: one set of
        generator outputs, one set of bus loads, one power-flow solution. That is
        enough for power-flow (PF) and optimal power flow (OPF), but real grid
        operations must decide **which generators to turn on, when to start them
        up, and how to ramp them** across a multi-hour horizon. This is the
        **Security-Constrained Unit Commitment (SCUC)** problem.

        SCUC adds temporal dimensions that a static snapshot lacks:

        | Parameter | Snapshot (MATPOWER) | SCUC requirement |
        |-----------|-------------------|------------------|
        | Generator output | Fixed Pg value | Dispatch varies hourly |
        | On/off status | Always on | Binary commitment decision |
        | Ramp rates | Not modeled | MW/min up and down limits |
        | Min up/down times | Not modeled | Hours a unit must stay on/off |
        | Startup costs | Not modeled | Cold/warm/hot $ to bring online |
        | Load profile | Single Pd per bus | 24-hour hourly demand curve |
        | Reserves | Not modeled | Spinning and non-spinning MW |
        | Renewables | Not modeled | Wind and solar with hourly profiles |

        ## Why RTS-GMLC?

        The **Reliability Test System - Grid Modernization Lab Consortium
        (RTS-GMLC)** is the standard open-source dataset for SCUC studies. It
        provides detailed temporal parameters (ramp rates, min up/down times,
        startup costs, load profiles, and renewable profiles) for a realistic
        73-bus test system.

        Since case39 has no temporal data of its own, we **borrow parameter
        templates from RTS-GMLC** by mapping each case39 generator to the
        nearest RTS-GMLC technology class based on fuel type and capacity.

        ## Fuel Classification of case39 Generators

        The IEEE 39-bus system header documents the generator types. We classify
        all 10 generators into fuel categories and map each to an RTS-GMLC
        technology class:

        - **Hydro** (1 unit, bus 30): Large reservoir unit mapped to RTS-GMLC Hydro
        - **Nuclear** (5 units, buses 31-32, 35, 37-38): Baseload mapped to
          RTS-GMLC Nuclear
        - **Coal/Steam** (2 units, buses 33-34): Large fossil mapped to RTS-GMLC
          Coal/Steam
        - **Gas/CC** (1 unit, bus 36): Mid-size fossil mapped to RTS-GMLC Gas/CC
        - **Gas/CC (flexible)** (1 unit, bus 39): External interconnection
          equivalent with enhanced flexibility

        This classification drives every downstream calibration step: temporal
        parameter assignment, reserve eligibility, and renewable integration.
        """
    )
    return


@app.cell
def _(CASE39_CLASSIFICATION_TABLE, pd):
    _records = [
        {
            "gen_index": c.gen_index,
            "bus_id": c.bus_id,
            "fuel_category": c.fuel_category,
            "rts_gmlc_class": c.rts_gmlc_class.value,
            "pmax_mw": c.pmax_mw,
            "pmin_mw": c.pmin_mw,
        }
        for c in CASE39_CLASSIFICATION_TABLE
    ]
    classification_df = pd.DataFrame(_records)
    classification_df
    return (classification_df,)


@app.cell
def _(alt, classification_df):
    _fuel_capacity = (
        classification_df.groupby("fuel_category", as_index=False)["pmax_mw"]
        .sum()
        .rename(columns={"pmax_mw": "total_pmax_mw"})
    )

    generation_mix_chart = (
        alt.Chart(_fuel_capacity)
        .mark_bar()
        .encode(
            x=alt.X(
                "fuel_category:N",
                title="Fuel Category",
                sort="-y",
            ),
            y=alt.Y("total_pmax_mw:Q", title="Total Capacity (MW)"),
            color=alt.Color(
                "fuel_category:N",
                title="Fuel",
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("fuel_category:N", title="Fuel"),
                alt.Tooltip(
                    "total_pmax_mw:Q",
                    title="MW",
                    format=",.0f",
                ),
            ],
        )
        .properties(
            title="case39 Generation Mix by Fuel Category",
            width=450,
            height=300,
        )
    )
    generation_mix_chart
    return (generation_mix_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Temporal Parameters: From Static to Dynamic

        The classification table above tells us **what** each generator is (fuel type,
        capacity, RTS-GMLC class). But a static snapshot cannot answer the questions
        that unit commitment must resolve every hour:

        - **How fast can this unit ramp?** (ramp rate, MW/min)
        - **Once started, how long must it stay on?** (minimum up time, hours)
        - **Once shut down, how long must it stay off?** (minimum down time, hours)
        - **What does it cost to start — and does it matter how long it was off?**
          (hot / warm / cold startup costs, $)
        - **What does it cost just to keep the unit synchronized to the grid?**
          (no-load cost, $/hr)
        - **How quickly can it change output per hour?** (ramp rate, MW/hr — derived
          from MW/min for use in hourly SCUC formulations)

        These six parameter families transform a generator from a rectangle on a
        one-line diagram into an economic agent whose on/off decisions shape the
        commitment schedule and total production cost.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Scaling Methodology: RTS-GMLC Templates

        Since the IEEE 39-bus case provides no temporal data, we borrow parameter
        **templates** from the RTS-GMLC dataset — the standard open-source reference
        for unit commitment studies.

        Each case39 generator was classified into an RTS-GMLC technology class in
        the table above. We now look up that class in a reference table of median
        RTS-GMLC parameters and scale them to match the case39 generator's capacity:

        | Parameter | Scaling rule |
        |-----------|-------------|
        | **Ramp rate** (MW/min) | Linear by Pmax ratio: `template_ramp × (gen_Pmax / template_Pmax)` |
        | **Min up / down time** (hr) | Taken directly from the template (no scaling) |
        | **Startup costs** (hot/warm/cold $) | Taken directly from the template |
        | **No-load cost** ($/hr) | Fixed defaults by tech class (hydro/nuclear $0, coal $450, gas $600) |

        **GAS_CC_FLEXIBLE special adjustments** (bus 39, the external interconnection
        equivalent): This generator represents the aggregate flexibility of an
        external grid connection. It receives:

        - **1.5× ramp rate multiplier** — faster response than a single CC unit
        - **50% min time reduction** (floor 1 hour) — can cycle more freely
        - Same startup costs as standard Gas/CC
        """
    )
    return


@app.cell
def _(
    CASE39_CLASSIFICATION_TABLE,
    Path,
    assign_all_temporal_params,
    load_reference_table,
    mo,
    pd,
):
    @mo.cache
    def _compute_temporal_params():
        from scripts.build_rts_gmlc_reference import main as build_reference

        # Ensure the RTS-GMLC reference CSV exists (idempotent download + build).
        build_reference()

        # Load the reference table from the generated CSV.
        _repo_root = Path(__file__).resolve().parent.parent / "data"
        _ref_csv = _repo_root / "reference" / "rts_gmlc_tech_classes.csv"
        templates = load_reference_table(_ref_csv)

        # Assign temporal parameters to all 10 case39 generators.
        classifications = list(CASE39_CLASSIFICATION_TABLE)
        gen_params = assign_all_temporal_params(classifications, templates)

        return pd.DataFrame(
            [
                {
                    "gen_index": p.gen_index,
                    "bus_id": p.bus_id,
                    "rts_gmlc_class": p.rts_gmlc_class,
                    "pmax_mw": p.pmax_mw,
                    "ramp_rate_mw_per_min": round(p.ramp_rate_mw_per_min, 2),
                    "ramp_rate_mw_per_hr": round(p.ramp_rate_mw_per_hr, 1),
                    "min_up_time_hr": p.min_up_time_hr,
                    "min_down_time_hr": p.min_down_time_hr,
                    "startup_cost_hot": round(p.startup_cost_hot_dollar, 0),
                    "startup_cost_warm": round(p.startup_cost_warm_dollar, 0),
                    "startup_cost_cold": round(p.startup_cost_cold_dollar, 0),
                    "no_load_cost_per_hr": round(p.no_load_cost_dollar_per_hr, 0),
                }
                for p in gen_params
            ]
        )

    temporal_params_df = _compute_temporal_params()
    return (temporal_params_df,)


@app.cell
def _(classification_df, mo, temporal_params_df):
    _before = classification_df[
        ["gen_index", "bus_id", "fuel_category", "pmax_mw", "pmin_mw"]
    ].copy()
    _before.columns = [
        "gen_index",
        "bus_id",
        "fuel",
        "Pmax (MW)",
        "Pmin (MW)",
    ]

    _after = temporal_params_df[
        [
            "gen_index",
            "ramp_rate_mw_per_hr",
            "min_up_time_hr",
            "min_down_time_hr",
            "startup_cost_hot",
            "startup_cost_warm",
            "startup_cost_cold",
            "no_load_cost_per_hr",
        ]
    ].copy()
    _after.columns = [
        "gen_index",
        "Ramp (MW/hr)",
        "Min Up (hr)",
        "Min Down (hr)",
        "Startup Hot ($)",
        "Startup Warm ($)",
        "Startup Cold ($)",
        "No-Load ($/hr)",
    ]

    before_after_df = _before.merge(_after, on="gen_index")

    mo.md("### Before and After: Static Snapshot → SCUC-Ready Generators")
    before_after_df
    return (before_after_df,)


@app.cell
def _(mo):
    mo.md(
        r"""
        **What to notice:**

        - **Ramp rates scale with capacity.** The 1000 MW nuclear units ramp at
          roughly 10× the rate of the 250 MW coal units — but as a fraction of
          Pmax, all units within a technology class share the same ramp
          *percentage*.
        - **Min up/down times are technology-driven, not size-driven.** Nuclear
          units must stay on for 24 hours once started; hydro can cycle in 1 hour.
        - **Startup costs increase with cooling time.** Cold starts cost the most
          (full boiler warmup), hot starts the least. This creates an incentive
          to keep units online during overnight load valleys rather than cycling.
        - **Bus 39 (GAS_CC_FLEXIBLE)** has a noticeably higher ramp rate and
          shorter min times than the standard Gas/CC at bus 36 — reflecting its
          role as an aggregate external interconnection.
        """
    )
    return


@app.cell
def _(alt, temporal_params_df):
    _ramp_data = temporal_params_df[
        ["gen_index", "bus_id", "rts_gmlc_class", "ramp_rate_mw_per_hr"]
    ].copy()
    _ramp_data["label"] = "Bus " + _ramp_data["bus_id"].astype(str)

    ramp_rate_chart = (
        alt.Chart(_ramp_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "label:N",
                title="Generator (Bus)",
                sort=alt.EncodingSortField(field="gen_index", order="ascending"),
            ),
            y=alt.Y(
                "ramp_rate_mw_per_hr:Q",
                title="Ramp Rate (MW/hr)",
            ),
            color=alt.Color(
                "rts_gmlc_class:N",
                title="Fuel / Class",
            ),
            tooltip=[
                alt.Tooltip("label:N", title="Generator"),
                alt.Tooltip("rts_gmlc_class:N", title="Class"),
                alt.Tooltip(
                    "ramp_rate_mw_per_hr:Q",
                    title="MW/hr",
                    format=",.1f",
                ),
            ],
        )
        .properties(
            title="Ramp Rate by Generator (colored by fuel class)",
            width=550,
            height=350,
        )
    )
    ramp_rate_chart
    return (ramp_rate_chart,)


@app.cell
def _(alt, temporal_params_df):
    _cost_records = []
    for _, _row in temporal_params_df.iterrows():
        _lbl = f"Bus {_row['bus_id']}"
        _cost_records.append(
            {
                "generator": _lbl,
                "gen_index": _row["gen_index"],
                "tier": "Hot",
                "cost_dollars": _row["startup_cost_hot"],
            }
        )
        _cost_records.append(
            {
                "generator": _lbl,
                "gen_index": _row["gen_index"],
                "tier": "Warm",
                "cost_dollars": _row["startup_cost_warm"],
            }
        )
        _cost_records.append(
            {
                "generator": _lbl,
                "gen_index": _row["gen_index"],
                "tier": "Cold",
                "cost_dollars": _row["startup_cost_cold"],
            }
        )

    import pandas as _startup_pd

    _startup_df = _startup_pd.DataFrame(_cost_records)

    startup_cost_chart = (
        alt.Chart(_startup_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "generator:N",
                title="Generator (Bus)",
                sort=alt.EncodingSortField(field="gen_index", order="ascending"),
            ),
            y=alt.Y("cost_dollars:Q", title="Startup Cost ($)"),
            color=alt.Color(
                "tier:N",
                title="Startup Tier",
                sort=["Hot", "Warm", "Cold"],
                scale=alt.Scale(
                    domain=["Hot", "Warm", "Cold"],
                    range=["#e45756", "#f58518", "#4c78a8"],
                ),
            ),
            xOffset="tier:N",
            tooltip=[
                alt.Tooltip("generator:N", title="Generator"),
                alt.Tooltip("tier:N", title="Tier"),
                alt.Tooltip("cost_dollars:Q", title="Cost ($)", format=",.0f"),
            ],
        )
        .properties(
            title="Startup Cost Tiers by Generator (Hot / Warm / Cold)",
            width=550,
            height=350,
        )
    )
    startup_cost_chart
    return (startup_cost_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Ready for Unit Commitment

        These 10 generators can now participate in unit commitment. Each has a
        complete set of temporal parameters — ramp rates, minimum up/down times,
        tiered startup costs, and no-load costs — scaled from RTS-GMLC templates
        to match the IEEE 39-bus system's capacity profile.

        The next step is to define the **load profile** and **reserve requirements**
        that the commitment engine will dispatch these generators against.
        """
    )
    return


if __name__ == "__main__":
    app.run()
