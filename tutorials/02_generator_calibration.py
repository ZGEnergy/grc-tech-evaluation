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
    import grid_plot

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
        grid_plot,
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
def _(Path, classification_df, grid_plot, mo, parse_matpower_case, pd, re):
    # Topology diagram: generators colored by fuel type, sized by Pmax
    import re as _re

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = parse_matpower_case(_case_file)
    _bus_df = pd.DataFrame(
        [
            {"bus_id": b.bus_id, "bus_type_name": b.bus_type.name, "pd_mw": b.pd}
            for b in _case_data.buses
        ]
    )
    _raw_text = _case_file.read_text()
    _branch_match = _re.search(r"mpc\.branch\s*=\s*\[([^\]]*)\]", _raw_text, _re.DOTALL)
    _branch_rows = []
    for _line in _branch_match.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _branch_rows.append([float(v) for v in _line.split()])
    _branch_df = pd.DataFrame(
        _branch_rows,
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
    _branch_df["fbus"] = _branch_df["fbus"].astype(int)
    _branch_df["tbus"] = _branch_df["tbus"].astype(int)

    _G = grid_plot.build_graph(_bus_df, _branch_df)
    _fig = grid_plot.plot_base_topology(
        _G,
        title="Generator Fleet by Fuel Type and Capacity",
        bus_size=8,
        bus_color="#ccc",
    )
    _gen_plot_df = classification_df.rename(
        columns={"bus_id": "gen_bus", "fuel_category": "fuel_type"}
    )
    grid_plot.add_generator_markers(_fig, _gen_plot_df, fuel_col="fuel_type")
    grid_plot.add_load_markers(_fig, _bus_df)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Each square shows a generator colored by fuel type and sized by Pmax. Load
    triangles (orange, sized by MW) show where demand concentrates. Nuclear
    dominates the perimeter while hydro anchors the top-left. The two coal units
    and single gas unit cluster in the lower portion of the network.
    """)
    return


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
        _repo_root = Path(__file__).resolve().parent.parent / "data"
        _ref_dir = _repo_root / "reference"
        build_reference(output_dir=_ref_dir)

        # Load the reference table from the generated CSV.
        _ref_csv = _ref_dir / "rts_gmlc_tech_classes.csv"
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


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 24-Hour Load Profile

        A **load profile** describes how electricity demand varies across the
        hours of a day. While a MATPOWER snapshot gives a single Pd value per
        bus, unit commitment requires a full 24-hour demand trajectory so the
        optimizer can schedule generators to meet load at every hour.

        ### RTS-GMLC Hourly Shape Template

        We borrow the system-level hourly load shape from a representative
        **RTS-GMLC winter weekday** — 24 MW values that capture the typical
        daily demand pattern: an overnight valley, a morning ramp, and an
        evening peak. The shape is normalized to fraction-of-peak so it can
        be applied to any system size.

        ### Proportional Bus-Level Distribution

        Each bus's 24-hour load is computed as:

        > `load_bus_h = fraction_h × Pd_bus`

        where `fraction_h` is the normalized shape at hour *h* and `Pd_bus` is
        the base-case real power demand from the MATPOWER file. Buses with
        zero Pd are excluded. This preserves each bus's share of total load
        at every hour and ensures the system peak equals total base-case Pd.

        ### Hour-Ending Convention

        All hours use the **hour-ending (HE)** convention standard in ERCOT
        and RTS-GMLC: HE1 = midnight–1 AM, HE24 = 11 PM–midnight. An HE
        label refers to the end of the interval, not the start.
        """
    )
    return


@app.cell
def _(Path, mo, synthesize_load_profile):
    @mo.cache
    def _synthesize_load():
        _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
        return synthesize_load_profile(_case_file)

    load_profile_result = _synthesize_load()
    return (load_profile_result,)


@app.cell
def _(alt, load_profile_result, pd):
    # Build system-level 24h load from metadata
    _sys_mw = load_profile_result.metadata.hourly_system_mw
    _sys_df = pd.DataFrame({"hour_ending": list(range(1, 25)), "system_mw": _sys_mw})

    _peak_mw = max(_sys_mw)
    _valley_mw = min(_sys_mw)
    _peak_he = _sys_mw.index(_peak_mw) + 1
    _valley_he = _sys_mw.index(_valley_mw) + 1

    _line = (
        alt.Chart(_sys_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "hour_ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y(
                "system_mw:Q",
                title="System Load (MW)",
                scale=alt.Scale(zero=False),
            ),
            tooltip=[
                alt.Tooltip("hour_ending:Q", title="HE"),
                alt.Tooltip("system_mw:Q", title="MW", format=",.1f"),
            ],
        )
    )

    _peak_df = pd.DataFrame([{"hour_ending": _peak_he, "system_mw": _peak_mw}])
    _valley_df = pd.DataFrame([{"hour_ending": _valley_he, "system_mw": _valley_mw}])

    _peak_text = (
        alt.Chart(_peak_df)
        .mark_text(dy=-12, fontSize=12, fontWeight="bold", color="#e45756")
        .encode(
            x="hour_ending:Q",
            y="system_mw:Q",
            text=alt.value(f"Peak {_peak_mw:,.0f} MW (HE{_peak_he})"),
        )
    )
    _valley_text = (
        alt.Chart(_valley_df)
        .mark_text(dy=14, fontSize=12, fontWeight="bold", color="#4c78a8")
        .encode(
            x="hour_ending:Q",
            y="system_mw:Q",
            text=alt.value(f"Valley {_valley_mw:,.0f} MW (HE{_valley_he})"),
        )
    )

    system_load_curve_chart = (_line + _peak_text + _valley_text).properties(
        title="case39 System Load Profile (24 Hours)",
        width=600,
        height=350,
    )
    system_load_curve_chart
    return (system_load_curve_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        The peak occurs in the early evening (HE15–HE18 range) when both
        commercial and residential loads overlap. The valley falls in the
        pre-dawn hours (HE3–HE5) when only baseload demand remains. The
        **peak-to-valley ratio** quantifies how much the system must ramp
        over the day — higher ratios demand more flexible generation.
        """
    )
    return


@app.cell
def _(alt, load_profile_result, pd):
    # Build long-format DataFrame for stacked area chart
    _bus_records = []
    for _row in load_profile_result.rows:
        for _h_idx, _mw_val in enumerate(_row.hourly_mw):
            _bus_records.append(
                {
                    "hour_ending": _h_idx + 1,
                    "bus_id": f"Bus {_row.bus_id}",
                    "load_mw": round(_mw_val, 2),
                }
            )
    _bus_long_df = pd.DataFrame(_bus_records)

    per_bus_stacked_area_chart = (
        alt.Chart(_bus_long_df)
        .mark_area()
        .encode(
            x=alt.X(
                "hour_ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y(
                "sum(load_mw):Q",
                title="Load (MW)",
                stack="zero",
            ),
            color=alt.Color(
                "bus_id:N",
                title="Bus",
                sort=alt.EncodingSortField(field="bus_id", order="ascending"),
            ),
            tooltip=[
                alt.Tooltip("bus_id:N", title="Bus"),
                alt.Tooltip("hour_ending:Q", title="HE"),
                alt.Tooltip("load_mw:Q", title="MW", format=",.1f"),
            ],
        )
        .properties(
            title="Per-Bus Load Contribution (Stacked Area, 24 Hours)",
            width=600,
            height=350,
        )
    )
    per_bus_stacked_area_chart
    return (per_bus_stacked_area_chart,)


@app.cell
def _(load_profile_result, mo):
    _meta = load_profile_result.metadata
    _sys_mw_summary = _meta.hourly_system_mw
    _peak_val = max(_sys_mw_summary)
    _valley_val = min(_sys_mw_summary)
    _ratio = _peak_val / _valley_val if _valley_val > 0 else float("inf")

    mo.md(
        f"""
        ### Load Profile Summary Statistics

        | Metric | Value |
        |--------|-------|
        | **Peak System Load** | {_peak_val:,.1f} MW |
        | **Valley System Load** | {_valley_val:,.1f} MW |
        | **Peak-to-Valley Ratio** | {_ratio:.2f} |
        | **Load Bus Count** | {_meta.load_buses} |
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Operating Reserves

        Operating reserves are generation capacity held back from energy
        dispatch so the system can respond to sudden supply shortfalls —
        a generator tripping offline, a transmission line faulting, or an
        unexpected load spike. Without reserves, any single contingency
        could cascade into widespread outages.

        Reserves come in two flavors, distinguished by response speed:

        - **Spinning reserves** — capacity on generators that are already
          synchronized to the grid and can ramp up within **10 minutes**.
          These provide the first line of defense after a contingency.
        - **Non-spinning reserves** — capacity on units that may be offline
          but can start and deliver power within **30 minutes**. These
          backfill the spinning response and restore the reserve margin.

        The amount of reserves a generator can provide depends directly on
        its **ramp rate**: a unit that ramps at 120 MW/hr can deliver
        20 MW of spinning reserve (120 × 10/60) and 60 MW of non-spinning
        reserve (120 × 30/60) within the respective deployment windows.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### The N-1 Contingency Criterion

        The standard reliability rule is **N-1**: the system must carry
        enough reserves to survive the loss of its single largest
        generating unit without shedding load.

        In case39, the largest generator is **1100 MW** (the
        interconnection equivalent at bus 39). The total reserve
        requirement is therefore 1100 MW, split evenly:

        | Product | Requirement | Deployment window |
        |---------|-------------|-------------------|
        | Spinning | **550 MW** | 10 minutes |
        | Non-spinning | **550 MW** | 30 minutes |

        This 50/50 split is constant across all 24 hours — a simplification
        that works well for this tutorial fleet. Production systems often
        vary reserve requirements by hour based on forecasted load and
        renewable uncertainty.

        **Nuclear caps:** The five nuclear units (buses 31, 32, 35, 37,
        38) have Pmax values of 646, 725, 687, 564, and 865 MW
        respectively — a total of **3487 MW**, roughly 47% of the
        fleet's installed capacity. They are technically eligible for
        reserves, but reactor physics limits how much output they can
        change quickly. We cap their contribution at **5% of Pmax for
        spinning** and **10% of Pmax for non-spinning** — so for example
        the largest nuclear unit (865 MW at bus 38) provides at most
        43 MW spinning and 87 MW non-spinning reserve.
        """
    )
    return


@app.cell
def _(
    CASE39_CLASSIFICATION_TABLE,
    Path,
    assign_all_temporal_params,
    build_reserve_requirements,
    compute_all_eligibilities,
    load_reference_table,
    mo,
    pd,
):
    from scripts.tiny_reserve_definitions import (
        ReserveProduct,
        validate_reserve_feasibility,
    )

    @mo.cache
    def _compute_reserve_eligibility():
        from scripts.build_rts_gmlc_reference import main as build_reference

        build_reference()

        _repo_root = Path(__file__).resolve().parent.parent / "data"
        _ref_csv = _repo_root / "reference" / "rts_gmlc_tech_classes.csv"
        templates = load_reference_table(_ref_csv)

        classifications = list(CASE39_CLASSIFICATION_TABLE)
        gen_params = assign_all_temporal_params(classifications, templates)

        spinning_req, non_spinning_req = build_reserve_requirements()
        eligibilities = compute_all_eligibilities(classifications, gen_params)

        spinning_feas = validate_reserve_feasibility(
            ReserveProduct.SPINNING,
            spinning_req.requirement_mw,
            eligibilities,
        )
        non_spinning_feas = validate_reserve_feasibility(
            ReserveProduct.NON_SPINNING,
            non_spinning_req.requirement_mw,
            eligibilities,
        )

        elig_df = pd.DataFrame(
            [
                {
                    "gen_index": e.gen_index,
                    "bus_id": e.bus_id,
                    "fuel_type": e.fuel_type,
                    "rts_gmlc_class": e.rts_gmlc_class,
                    "pmax_mw": e.pmax_mw,
                    "max_spinning_mw": round(e.pmax_mw * e.max_spinning_pct, 1),
                    "max_non_spinning_mw": round(e.pmax_mw * e.max_non_spinning_pct, 1),
                    "max_spinning_pct": round(e.max_spinning_pct, 4),
                    "max_non_spinning_pct": round(e.max_non_spinning_pct, 4),
                }
                for e in eligibilities
            ]
        )

        feasibility_df = pd.DataFrame(
            [
                {
                    "product": f.product.value,
                    "requirement_mw": f.requirement_mw,
                    "total_eligible_mw": f.total_eligible_capacity_mw,
                    "margin_mw": f.margin_mw,
                    "is_feasible": f.is_feasible,
                }
                for f in [spinning_feas, non_spinning_feas]
            ]
        )

        return elig_df, feasibility_df

    reserve_eligibility_df, reserve_feasibility_df = _compute_reserve_eligibility()
    return (
        ReserveProduct,
        reserve_eligibility_df,
        reserve_feasibility_df,
        validate_reserve_feasibility,
    )


@app.cell
def _(alt, reserve_eligibility_df, pd):
    _bar_records = []
    for _, _r in reserve_eligibility_df.iterrows():
        _label = f"Bus {_r['bus_id']}"
        _bar_records.append(
            {
                "generator": _label,
                "gen_index": _r["gen_index"],
                "product": "Spinning",
                "eligible_mw": _r["max_spinning_mw"],
                "fuel": _r["fuel_type"],
            }
        )
        _bar_records.append(
            {
                "generator": _label,
                "gen_index": _r["gen_index"],
                "product": "Non-Spinning",
                "eligible_mw": _r["max_non_spinning_mw"],
                "fuel": _r["fuel_type"],
            }
        )
    _bar_df = pd.DataFrame(_bar_records)

    eligible_capacity_stacked_bar = (
        alt.Chart(_bar_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "generator:N",
                title="Generator (Bus)",
                sort=alt.EncodingSortField(field="gen_index", order="ascending"),
            ),
            y=alt.Y(
                "eligible_mw:Q",
                title="Eligible Reserve Capacity (MW)",
                stack="zero",
            ),
            color=alt.Color(
                "product:N",
                title="Reserve Product",
                scale=alt.Scale(
                    domain=["Spinning", "Non-Spinning"],
                    range=["#e45756", "#4c78a8"],
                ),
            ),
            tooltip=[
                alt.Tooltip("generator:N", title="Generator"),
                alt.Tooltip("fuel:N", title="Fuel"),
                alt.Tooltip("product:N", title="Product"),
                alt.Tooltip("eligible_mw:Q", title="MW", format=",.1f"),
            ],
        )
        .properties(
            title=("Eligible Reserve Capacity by Generator (Spinning + Non-Spinning)"),
            width=550,
            height=350,
        )
    )
    eligible_capacity_stacked_bar
    return (eligible_capacity_stacked_bar,)


@app.cell
def _(alt, reserve_feasibility_df, pd):
    _feas_records = []
    for _, _r in reserve_feasibility_df.iterrows():
        _feas_records.append(
            {
                "product": _r["product"].replace("_", "-").title(),
                "category": "Requirement",
                "mw": _r["requirement_mw"],
            }
        )
        _feas_records.append(
            {
                "product": _r["product"].replace("_", "-").title(),
                "category": "Eligible Capacity",
                "mw": _r["total_eligible_mw"],
            }
        )
    _feas_df = pd.DataFrame(_feas_records)

    feasibility_margin_chart = (
        alt.Chart(_feas_df)
        .mark_bar()
        .encode(
            x=alt.X("product:N", title="Reserve Product"),
            y=alt.Y("mw:Q", title="MW"),
            color=alt.Color(
                "category:N",
                title="",
                scale=alt.Scale(
                    domain=["Requirement", "Eligible Capacity"],
                    range=["#e45756", "#4c78a8"],
                ),
            ),
            xOffset="category:N",
            tooltip=[
                alt.Tooltip("product:N", title="Product"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("mw:Q", title="MW", format=",.1f"),
            ],
        )
        .properties(
            title="Reserve Feasibility: Requirement vs Eligible Capacity",
            width=400,
            height=350,
        )
    )
    feasibility_margin_chart
    return (feasibility_margin_chart,)


@app.cell
def _(alt, reserve_eligibility_df, pd):
    _nuc_df = reserve_eligibility_df.copy()
    _nuc_df["is_nuclear"] = _nuc_df["rts_gmlc_class"] == "Nuclear"
    _nuc_df["label"] = "Bus " + _nuc_df["bus_id"].astype(str)

    _contrib_records = []
    for _, _r in _nuc_df.iterrows():
        _contrib_records.append(
            {
                "generator": _r["label"],
                "gen_index": _r["gen_index"],
                "is_nuclear": _r["is_nuclear"],
                "spinning_mw": _r["max_spinning_mw"],
                "spinning_pct": _r["max_spinning_pct"] * 100,
            }
        )
    _contrib_df = pd.DataFrame(_contrib_records)

    nuclear_contribution_chart = (
        alt.Chart(_contrib_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "generator:N",
                title="Generator (Bus)",
                sort=alt.EncodingSortField(field="gen_index", order="ascending"),
            ),
            y=alt.Y(
                "spinning_mw:Q",
                title="Max Spinning Reserve (MW)",
            ),
            color=alt.Color(
                "is_nuclear:N",
                title="Nuclear?",
                scale=alt.Scale(
                    domain=[True, False],
                    range=["#f58518", "#4c78a8"],
                ),
                legend=alt.Legend(
                    labelExpr=(
                        "datum.value === true ? 'Nuclear (5% cap)' : 'Non-Nuclear (ramp-based)'"
                    )
                ),
            ),
            tooltip=[
                alt.Tooltip("generator:N", title="Generator"),
                alt.Tooltip("spinning_mw:Q", title="Spinning MW", format=",.1f"),
                alt.Tooltip(
                    "spinning_pct:Q",
                    title="% of Pmax",
                    format=".1f",
                ),
            ],
        )
        .properties(
            title=("Nuclear vs Non-Nuclear Spinning Reserve Contribution"),
            width=550,
            height=350,
        )
    )
    nuclear_contribution_chart
    return (nuclear_contribution_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        Despite providing nearly half the fleet's installed capacity
        (3487 MW out of ~7400 MW total), nuclear units contribute very
        little spinning reserve — only 5% of each unit's Pmax, ranging
        from 28 MW (bus 37, 564 MW) to 43 MW (bus 38, 865 MW). This is
        a consequence of the 5% cap imposed by reactor ramp limitations.
        The non-nuclear generators (hydro, coal, and gas) carry the bulk
        of the reserve burden through their higher ramp-based eligibility
        percentages.

        The thermal fleet is calibrated — ramp rates, commitment
        parameters, reserve eligibility — but case39 has **no renewable
        generation**. The next section adds wind and solar profiles to
        explore how variable resources change the commitment problem.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Synthetic Renewable Generation

        The 10 thermal generators calibrated above — nuclear, coal, gas, and
        hydro — provide the dispatchable backbone of the case39 fleet. But
        modern grids derive a growing share of energy from **variable
        renewable resources** (wind and solar) whose output fluctuates with
        weather rather than operator decisions.

        Adding renewables to the commitment problem changes it fundamentally:

        - **Net load** (load minus renewables) replaces gross load as the
          signal that thermal units must follow. High renewable output
          reduces the number of thermal units needed online, while rapid
          drops in wind or solar force fast-ramping units to compensate.
        - **Reserve requirements** may increase to cover renewable forecast
          uncertainty — a topic explored in later notebooks.

        ### Bus Placement via Headroom Scoring

        Where should new wind and solar generators connect? Injecting power
        at an already-congested bus would violate thermal limits on
        transmission lines. We score every **non-generator bus** by its
        **transmission headroom** — the sum of unused thermal capacity
        (rateA minus estimated flow) on all connected branches. Buses with
        high headroom can absorb new generation without congestion. We also
        diversify across network areas so that renewable output is
        geographically spread.

        ### Capacity Factor Profiles

        Each renewable type has a characteristic **capacity factor (CF)**
        shape — the fraction of nameplate capacity produced in each hour:

        - **Wind** CF is highest overnight and in the evening, lowest in
          the early afternoon. Crucially, wind output is **non-zero in
          every hour** — unlike solar, wind farms produce power around
          the clock, though the amount varies.
        - **Solar** CF follows a bell curve centered on midday and is
          **exactly zero at night** (HE 1–6 and HE 21–24). The sharp
          morning ramp-up and evening ramp-down create the "duck curve"
          that thermal units must accommodate.

        We use synthetic profiles derived from **RTS-GMLC representative
        day** shapes, scaled to each unit's nameplate capacity (Pmax).
        """
    )
    return


@app.cell
def _(Path, mo, parse_matpower_case, synthesize_renewable_profiles):
    @mo.cache
    def _compute_renewables():
        _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
        _case_data = parse_matpower_case(_case_file)
        return synthesize_renewable_profiles(_case_data, penetration=0.20)

    renewable_result = _compute_renewables()
    return (renewable_result,)


@app.cell
def _(pd, renewable_result):
    _unit_records = [
        {
            "gen_uid": u.gen_uid,
            "bus_id": u.bus_id,
            "type": u.renewable_type.value,
            "pmax_mw": u.pmax_mw,
            "area": u.area,
        }
        for u in renewable_result.units
    ]
    renewable_units_df = pd.DataFrame(_unit_records)
    renewable_units_df
    return (renewable_units_df,)


@app.cell
def _(Path, grid_plot, mo, parse_matpower_case, pd, renewable_units_df):
    # Topology diagram: wind and solar locations on the network
    import re as _re

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = parse_matpower_case(_case_file)
    _bus_df = pd.DataFrame(
        [
            {"bus_id": b.bus_id, "bus_type_name": b.bus_type.name, "pd_mw": b.pd}
            for b in _case_data.buses
        ]
    )
    _raw_text = _case_file.read_text()
    _bm = _re.search(r"mpc\.branch\s*=\s*\[([^\]]*)\]", _raw_text, _re.DOTALL)
    _brows = []
    for _line in _bm.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _brows.append([float(v) for v in _line.split()])
    _branch_df = pd.DataFrame(
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
    _branch_df["fbus"] = _branch_df["fbus"].astype(int)
    _branch_df["tbus"] = _branch_df["tbus"].astype(int)

    _G = grid_plot.build_graph(_bus_df, _branch_df)
    _fig = grid_plot.plot_base_topology(
        _G,
        title="Renewable Generation Placement on IEEE 39-Bus Network",
        bus_size=8,
        bus_color="#ccc",
    )

    _resources = []
    for _, _r in renewable_units_df.iterrows():
        _resources.append(
            {
                "bus": int(_r["bus_id"]),
                "type": _r["type"].title(),
                "label": f"{_r['pmax_mw']:.0f} MW",
                "mw": _r["pmax_mw"],
            }
        )
    grid_plot.add_resource_markers(_fig, _resources)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Wind generators (green stars) and solar generators (yellow stars) are placed
    at buses with high transmission headroom, spread across different network areas
    to diversify output. This geographic distribution means renewable variability
    affects multiple parts of the network, not just one corridor.
    """)
    return


@app.cell
def _(alt, pd, renewable_result):
    _wind_records = []
    for _wp in renewable_result.wind_profiles:
        for _h_idx, _mw in enumerate(_wp.values_mw):
            _wind_records.append(
                {
                    "hour_ending": _h_idx + 1,
                    "gen_uid": _wp.gen_uid,
                    "mw": round(_mw, 2),
                }
            )
    _wind_df = pd.DataFrame(_wind_records)

    wind_profile_chart = (
        alt.Chart(_wind_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "hour_ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y("mw:Q", title="Wind Output (MW)"),
            color=alt.Color("gen_uid:N", title="Wind Unit"),
            tooltip=[
                alt.Tooltip("gen_uid:N", title="Unit"),
                alt.Tooltip("hour_ending:Q", title="HE"),
                alt.Tooltip("mw:Q", title="MW", format=",.1f"),
            ],
        )
        .properties(
            title="Wind Generation Profiles (24 Hours)",
            width=600,
            height=350,
        )
    )
    wind_profile_chart
    return (wind_profile_chart,)


@app.cell
def _(alt, pd, renewable_result):
    _solar_records = []
    for _sp in renewable_result.solar_profiles:
        for _h_idx, _mw in enumerate(_sp.values_mw):
            _solar_records.append(
                {
                    "hour_ending": _h_idx + 1,
                    "gen_uid": _sp.gen_uid,
                    "mw": round(_mw, 2),
                }
            )
    _solar_df = pd.DataFrame(_solar_records)

    solar_profile_chart = (
        alt.Chart(_solar_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "hour_ending:Q",
                title="Hour Ending",
                scale=alt.Scale(domain=[1, 24]),
            ),
            y=alt.Y("mw:Q", title="Solar Output (MW)"),
            color=alt.Color("gen_uid:N", title="Solar Unit"),
            tooltip=[
                alt.Tooltip("gen_uid:N", title="Unit"),
                alt.Tooltip("hour_ending:Q", title="HE"),
                alt.Tooltip("mw:Q", title="MW", format=",.1f"),
            ],
        )
        .properties(
            title="Solar Generation Profiles (24 Hours)",
            width=600,
            height=350,
        )
    )
    solar_profile_chart
    return (solar_profile_chart,)


@app.cell
def _(mo, renewable_result):
    _wind_peak_he = (
        max(
            range(24),
            key=lambda i: sum(wp.values_mw[i] for wp in renewable_result.wind_profiles),
        )
        + 1
    )
    _solar_peak_he = (
        max(
            range(24),
            key=lambda i: sum(sp.values_mw[i] for sp in renewable_result.solar_profiles),
        )
        + 1
    )

    mo.md(
        f"""
        ### Profile Patterns

        **Wind** output peaks in the evening (HE {_wind_peak_he}) and dips
        in the early afternoon — the inverse of load and solar patterns.
        All three wind units share the same capacity factor shape (derived
        from the RTS-GMLC representative day) and the same nameplate
        capacity, so their MW output profiles are identical.

        **Solar** output follows a symmetric bell curve, peaking near
        midday (HE {_solar_peak_he}). Output is **exactly zero** for
        10 nighttime hours (HE 1–6, HE 21–24), which means the thermal
        fleet must cover the full load during those hours with no solar
        contribution.

        This complementary timing — wind strongest when solar is weakest
        — is a key reason portfolios combine both technologies.
        """
    )
    return


@app.cell
def _(alt, classification_df, load_profile_result, pd, renewable_result):
    # Find peak hour from load profile
    _sys_mw_mix = load_profile_result.metadata.hourly_system_mw
    _peak_he_idx = _sys_mw_mix.index(max(_sys_mw_mix))
    _peak_load_mw = max(_sys_mw_mix)

    # Thermal capacity at peak (total Pmax of all thermal gens)
    _thermal_total_mw = classification_df["pmax_mw"].sum()

    # Renewable output at peak hour
    _wind_at_peak = sum(wp.values_mw[_peak_he_idx] for wp in renewable_result.wind_profiles)
    _solar_at_peak = sum(sp.values_mw[_peak_he_idx] for sp in renewable_result.solar_profiles)

    _mix_records = [
        {"category": "Thermal Capacity", "mw": _thermal_total_mw},
        {"category": "Wind @ Peak", "mw": round(_wind_at_peak, 1)},
        {"category": "Solar @ Peak", "mw": round(_solar_at_peak, 1)},
        {"category": "Peak Load", "mw": _peak_load_mw},
    ]
    _mix_df = pd.DataFrame(_mix_records)

    generation_mix_peak_chart = (
        alt.Chart(_mix_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "category:N",
                title="",
                sort=["Thermal Capacity", "Wind @ Peak", "Solar @ Peak", "Peak Load"],
            ),
            y=alt.Y("mw:Q", title="MW"),
            color=alt.Color(
                "category:N",
                title="",
                scale=alt.Scale(
                    domain=[
                        "Thermal Capacity",
                        "Wind @ Peak",
                        "Solar @ Peak",
                        "Peak Load",
                    ],
                    range=["#4c78a8", "#72b7b2", "#f58518", "#e45756"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("mw:Q", title="MW", format=",.1f"),
            ],
        )
        .properties(
            title=(f"Generation Mix vs Peak Load (HE {_peak_he_idx + 1})"),
            width=500,
            height=350,
        )
    )
    generation_mix_peak_chart
    return (generation_mix_peak_chart,)


@app.cell
def _(mo, renewable_result):
    mo.md(
        f"""
        ## Notebook Summary: The Fully Augmented Fleet

        This notebook transformed the IEEE 39-bus snapshot into a
        **SCUC-ready dataset** with five calibration layers:

        1. **Fuel classification** — 10 thermal generators mapped to
           RTS-GMLC technology classes (hydro, nuclear, coal, gas).
        2. **Temporal parameters** — ramp rates, min up/down times,
           tiered startup costs, and no-load costs scaled from RTS-GMLC
           templates.
        3. **24-hour load profile** — system demand shaped by an
           RTS-GMLC winter weekday pattern, distributed proportionally
           across load buses.
        4. **Operating reserves** — spinning and non-spinning products
           sized by the N-1 criterion, with nuclear caps on reserve
           contribution.
        5. **Renewable generation** — {len(renewable_result.units)}
           synthetic units ({renewable_result.total_wind_mw:.0f} MW wind
           + {renewable_result.total_solar_mw:.0f} MW solar =
           {renewable_result.total_renewable_mw:.0f} MW,
           {renewable_result.penetration_pct:.1f}% penetration) placed
           by transmission headroom scoring with 24-hour profiles.

        The complete fleet now comprises **10 thermal + 5 renewable = 15
        generators** with all parameters needed for unit commitment.

        **Next: Notebook 03** builds the SCUC formulation itself —
        assembling these generators, load profiles, reserves, and
        renewable profiles into the mixed-integer program that each
        evaluation tool must solve.
        """
    )
    return


if __name__ == "__main__":
    app.run()
