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

    # BESS & DR resource definitions
    from scripts.tiny_bess_dr import (
        BessUnit,
        DrBus,
        build_bess_unit,
        build_dr_bus,
    )

    # Flowgate identification (used in later PRDs)
    from scripts.tiny_flowgates import (
        FlowgateDefinition,
        FlowgateResult,
        parse_matpower_case_extended,
    )

    # Load profile synthesis (used in later PRDs)
    from scripts.tiny_load_profile import (
        synthesize_load_profile,
    )

    return (
        BessUnit,
        DrBus,
        FlowgateDefinition,
        FlowgateResult,
        Path,
        alt,
        build_bess_unit,
        build_dr_bus,
        parse_matpower_case_extended,
        pd,
        synthesize_load_profile,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        # Infrastructure Augmentation: BESS and Demand Response

        The IEEE 39-bus case file defines generators, loads, and branches,
        but it contains no **energy storage** or **demand-side flexibility**.
        Modern grid operations rely on both to manage congestion, smooth
        renewable intermittency, and provide reserves. This notebook
        introduces the two infrastructure additions we layer onto case39:
        a Battery Energy Storage System (BESS) and a Demand Response (DR)
        program.

        ## Battery Energy Storage Systems (BESS)

        A BESS is a grid-connected battery that can **charge** (absorb power
        from the grid) or **discharge** (inject power into the grid) within
        its rated power capacity. Key characteristics:

        | Concept | Description |
        |---------|-------------|
        | **Power rating (MW)** | Maximum instantaneous charge or discharge rate |
        | **Energy capacity (MWh)** | Total energy the battery can store |
        | **Duration (hours)** | Energy / Power — a 4-hour battery can discharge at full power for 4 hours |
        | **Round-trip efficiency** | Fraction of energy recovered after a full charge-discharge cycle |
        | **State of Charge (SoC)** | Current stored energy as a fraction of capacity (0 to 1) |

        ### Peak Shaving

        The primary economic use of a BESS in day-ahead markets is **peak
        shaving**: charge during low-price off-peak hours when generation is
        cheap and plentiful, then discharge during high-price on-peak hours
        to displace expensive peakers. This flattens the net load curve and
        reduces system-wide production costs.

        ### Cyclic State of Charge

        In a 24-hour unit commitment horizon, the BESS must end the day at
        the **same SoC it started with** (the cyclic SoC constraint). Without
        this constraint, the optimizer would simply drain the battery to zero
        by the end of the horizon, producing an artificially cheap schedule
        that borrows energy from the next day. The cyclic constraint ensures
        the BESS operates sustainably across consecutive days.

        The SoC trajectory over 24 hours typically follows a pattern:

        1. **Off-peak charging** (early morning): SoC rises from initial level
        2. **On-peak discharging** (morning through afternoon): SoC falls
        3. **Evening recharging**: SoC recovers to initial level

        SoC is bounded between minimum and maximum limits (e.g., 10%-90%)
        to protect battery health and longevity.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Demand Response (DR)

        Demand Response allows specific load buses to **temporarily reduce
        consumption** in exchange for a curtailment payment. Unlike load
        shedding (which is an emergency action with no recovery obligation),
        DR is a **voluntary, market-based** mechanism with two key constraints:

        ### DR vs. Load Shedding

        | Feature | Load Shedding | Demand Response |
        |---------|--------------|-----------------|
        | Trigger | Emergency (frequency collapse) | Economic dispatch signal |
        | Duration | Until emergency clears | Bounded (e.g., max 4 hours) |
        | Recovery | No obligation | Must recover curtailed energy |
        | Cost | Value of Lost Load (~$10,000/MWh) | Contract price (~$200/MWh) |
        | Participation | Involuntary | Voluntary enrollment |

        ### Energy Neutrality

        The energy neutrality constraint requires that the **total energy
        curtailed** during DR activation equals the **total energy recovered**
        afterward. If a bus curtails 25 MW for 2 hours (50 MWh), it must
        later increase consumption by 50 MWh to make up the deferred demand.
        This models real-world DR programs where loads are shifted in time,
        not eliminated — factories delay production runs, HVAC systems
        pre-cool or coast, but the underlying energy need persists.

        ### Recovery Cost Asymmetry

        Recovery costs are typically lower than curtailment costs because
        recovery happens during off-peak hours when energy is cheap. In our
        model, curtailment costs $200/MWh (reflecting the value of deferred
        load) while recovery costs $50/MWh (reflecting the lower off-peak
        energy price).

        ## Bus Placement Rationale

        The choice of where to place BESS and DR resources is driven by
        network topology and congestion patterns:

        - **BESS at bus 25** (224 MW load): A medium-load bus downstream of
          generation-heavy buses 37 and 38 (nuclear). Placing storage here
          lets it absorb excess baseload generation during off-peak hours
          and re-inject during peak, reducing flows on the heavily loaded
          branches connecting the generation pocket to the load center.

        - **DR at bus 20** (680 MW load): One of the highest-load buses in
          the network. Even a modest 25 MW curtailment (3.7% of bus load)
          provides meaningful congestion relief on branches feeding the
          load pocket around buses 15-20 without requiring unrealistic
          demand flexibility.
        """
    )
    return


@app.cell
def _(build_bess_unit, build_dr_bus, mo):
    @mo.cache
    def _load_bess_dr():
        bess = build_bess_unit()
        dr = build_dr_bus()
        return bess, dr

    bess_unit, dr_bus = _load_bess_dr()
    return bess_unit, dr_bus


@app.cell
def _(bess_unit, pd):
    bess_params = pd.DataFrame(
        [
            {
                "Parameter": "Unit ID",
                "Value": bess_unit.unit_id,
            },
            {
                "Parameter": "Bus",
                "Value": str(bess_unit.bus),
            },
            {
                "Parameter": "Power Rating (MW)",
                "Value": f"{bess_unit.power_mw:.0f}",
            },
            {
                "Parameter": "Energy Capacity (MWh)",
                "Value": f"{bess_unit.energy_mwh:.0f}",
            },
            {
                "Parameter": "Duration (hours)",
                "Value": f"{bess_unit.duration_hours:.0f}",
            },
            {
                "Parameter": "Charge Efficiency",
                "Value": f"{bess_unit.charge_eff:.2f}",
            },
            {
                "Parameter": "Discharge Efficiency",
                "Value": f"{bess_unit.discharge_eff:.2f}",
            },
            {
                "Parameter": "Round-Trip Efficiency",
                "Value": f"{bess_unit.round_trip_efficiency:.4f}",
            },
            {
                "Parameter": "Min SoC",
                "Value": f"{bess_unit.min_soc:.0%}",
            },
            {
                "Parameter": "Max SoC",
                "Value": f"{bess_unit.max_soc:.0%}",
            },
            {
                "Parameter": "Initial SoC",
                "Value": f"{bess_unit.init_soc:.0%}",
            },
            {
                "Parameter": "Cyclic SoC",
                "Value": str(bess_unit.cyclic_soc),
            },
            {
                "Parameter": "Spinning Reserve Eligible",
                "Value": str(bess_unit.spinning_eligible),
            },
            {
                "Parameter": "Non-Spinning Reserve Eligible",
                "Value": str(bess_unit.non_spinning_eligible),
            },
        ]
    )
    bess_params
    return (bess_params,)


@app.cell
def _(dr_bus, pd):
    dr_params = pd.DataFrame(
        [
            {
                "Parameter": "Bus",
                "Value": str(dr_bus.bus),
            },
            {
                "Parameter": "Max Curtailment (MW)",
                "Value": f"{dr_bus.max_curtailment_mw:.0f}",
            },
            {
                "Parameter": "Max Recovery (MW)",
                "Value": f"{dr_bus.max_recovery_mw:.0f}",
            },
            {
                "Parameter": "Curtailment Cost ($/MWh)",
                "Value": f"{dr_bus.curtailment_cost:.0f}",
            },
            {
                "Parameter": "Recovery Cost ($/MWh)",
                "Value": f"{dr_bus.recovery_cost:.0f}",
            },
            {
                "Parameter": "Max Duration (hours)",
                "Value": f"{dr_bus.max_hours:.0f}",
            },
            {
                "Parameter": "Energy Neutral",
                "Value": str(dr_bus.energy_neutral),
            },
            {
                "Parameter": "Notification Lead Time (hr)",
                "Value": f"{dr_bus.notification_lead_time_hr:.0f}",
            },
        ]
    )
    dr_params
    return (dr_params,)


@app.cell
def _(alt, bess_unit, pd):
    # Synthesize a conceptual 24h SoC trajectory.
    # Pattern: charge off-peak (HE 1-6), idle (HE 7-8), discharge on-peak
    # (HE 9-14), idle (HE 15-16), recharge (HE 17-20), idle (HE 21-24).
    # SoC must start and end at init_soc (cyclic constraint).
    _init = bess_unit.init_soc
    _min_soc = bess_unit.min_soc
    _max_soc = bess_unit.max_soc

    # Per-hour SoC deltas (fraction of capacity)
    _charge_rate = (_max_soc - _init) / 6  # 6 hours to reach max
    _discharge_rate = (_max_soc - _min_soc) / 6  # 6 hours to drain
    _recharge_rate = (_init - _min_soc) / 4  # 4 hours to recover

    _soc_values = [_init]  # SoC at start of hour 1 (end of hour 0)
    for _h in range(1, 25):
        _prev = _soc_values[-1]
        if 1 <= _h <= 6:
            # Charging off-peak
            _next = min(_prev + _charge_rate, _max_soc)
        elif 7 <= _h <= 8:
            # Idle
            _next = _prev
        elif 9 <= _h <= 14:
            # Discharging on-peak
            _next = max(_prev - _discharge_rate, _min_soc)
        elif 15 <= _h <= 16:
            # Idle
            _next = _prev
        elif 17 <= _h <= 20:
            # Recharging to return to init
            _next = min(_prev + _recharge_rate, _init)
        else:
            # Idle (HE 21-24), holding at init_soc
            _next = _prev
        _soc_values.append(round(_next, 4))

    # Use end-of-hour SoC values (index 1..24 -> HE 1..24)
    _soc_df = pd.DataFrame(
        {
            "Hour Ending": list(range(1, 25)),
            "SoC": _soc_values[1:],
            "Phase": (
                ["Charge"] * 6
                + ["Idle"] * 2
                + ["Discharge"] * 6
                + ["Idle"] * 2
                + ["Recharge"] * 4
                + ["Idle"] * 4
            ),
        }
    )

    # SoC bounds as horizontal rules
    _min_rule = (
        alt.Chart(pd.DataFrame({"y": [_min_soc]}))
        .mark_rule(strokeDash=[4, 4], color="red")
        .encode(y="y:Q")
    )
    _max_rule = (
        alt.Chart(pd.DataFrame({"y": [_max_soc]}))
        .mark_rule(strokeDash=[4, 4], color="red")
        .encode(y="y:Q")
    )
    _init_rule = (
        alt.Chart(pd.DataFrame({"y": [_init]}))
        .mark_rule(strokeDash=[2, 2], color="gray")
        .encode(y="y:Q")
    )

    _phase_colors = alt.Scale(
        domain=["Charge", "Discharge", "Recharge", "Idle"],
        range=["#2ca02c", "#d62728", "#1f77b4", "#999999"],
    )

    soc_chart = (
        alt.Chart(_soc_df)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X(
                "Hour Ending:O",
                title="Hour Ending (HE)",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "SoC:Q",
                title="State of Charge (fraction)",
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.Color(
                "Phase:N",
                title="Operating Phase",
                scale=_phase_colors,
            ),
            tooltip=[
                alt.Tooltip("Hour Ending:O", title="HE"),
                alt.Tooltip("SoC:Q", title="SoC", format=".2f"),
                alt.Tooltip("Phase:N", title="Phase"),
            ],
        )
        .properties(
            title="Conceptual 24h BESS State of Charge Trajectory",
            width=600,
            height=350,
        )
    )
    soc_chart + _min_rule + _max_rule + _init_rule
    return (soc_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Transition: From Resources to Operations

        With BESS and DR resources defined and parameterized, the next step
        is to incorporate them into a **DC Optimal Power Flow (DC OPF)**
        formulation. The OPF will co-optimize generator dispatch, BESS
        charge/discharge schedules, and DR activation decisions subject to:

        - Network power balance at every bus
        - Branch flow limits (enforced via flowgates)
        - BESS energy balance and SoC bounds
        - DR curtailment limits and energy neutrality
        - Reserve requirements

        The following sections of this notebook will build up the DC OPF
        formulation step by step, starting with the flowgate definitions
        that encode network congestion constraints.
        """
    )
    return


if __name__ == "__main__":
    app.run()
