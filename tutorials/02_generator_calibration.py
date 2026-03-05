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


if __name__ == "__main__":
    app.run()
