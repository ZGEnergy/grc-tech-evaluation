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

    import grid_plot

    return (
        BessUnit,
        DrBus,
        FlowgateDefinition,
        FlowgateResult,
        Path,
        alt,
        build_bess_unit,
        build_dr_bus,
        grid_plot,
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

        *The chart below shows an **illustrative** SoC trajectory based on
        a stylized charge/discharge pattern — not an optimization result.
        The actual optimal schedule depends on the unit commitment solution.*
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
def _(Path, grid_plot, mo, pd):
    # Topology diagram: BESS and DR placement on the network
    import re as _re
    from scripts.reconcile_bus_gen import parse_matpower_case as _parse

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = _parse(_case_file)
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
        title="BESS and DR Placement on IEEE 39-Bus Network",
        bus_size=8,
        bus_color="#ccc",
    )
    grid_plot.add_load_markers(_fig, _bus_df)
    grid_plot.add_resource_markers(
        _fig,
        [
            {"bus": 25, "type": "BESS", "label": "50 MW / 200 MWh"},
            {"bus": 20, "type": "DR", "label": "25 MW curtailment"},
        ],
    )
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    The **BESS** (purple diamond, bus 25) sits downstream of the nuclear generation
    pocket at buses 37-38, positioned to absorb excess baseload during off-peak hours.
    The **DR** resource (teal hexagon, bus 20) targets the network's heaviest load bus
    (680 MW). Load triangles are sized by demand — notice how bus 20 dominates.
    """)
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
        formulation step by step: first the power flow physics, then
        congestion analysis at three load levels, and finally the
        flowgate definitions that encode network congestion constraints.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## DC Optimal Power Flow and Transmission Congestion

        With BESS and DR resources defined, we now turn to the **network
        physics** that determine where congestion occurs and where those
        resources can provide the most relief. The workhorse tool for this
        analysis is the **DC Optimal Power Flow (DC OPF)**.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### What is DC OPF?

        DC OPF is a **linearized, lossless** approximation of the full AC
        power flow equations. It makes three simplifying assumptions:

        1. **Voltage magnitudes are fixed at 1.0 p.u.** — no reactive power
           modeled.
        2. **Angle differences across branches are small** — so
           $\sin(\theta_i - \theta_j) \approx \theta_i - \theta_j$.
        3. **Line losses are neglected** — power in equals power out on every
           branch.

        These assumptions reduce the nonlinear AC power flow to a **linear
        system** $B \cdot \theta = P_{\text{inject}}$, where $B$ is the bus
        susceptance matrix and $\theta$ is the vector of bus voltage angles.
        Branch flows follow directly:

        $$P_{ij} = \frac{\theta_i - \theta_j}{x_{ij}} \cdot S_{\text{base}}$$

        DC OPF is the standard tool for **congestion analysis**, **LMP
        decomposition**, and **flowgate identification** in ISO/RTO market
        operations because it is fast, convex, and captures the dominant
        physics of real-power flow on high-voltage transmission networks.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Three Load Levels: Peak, Shoulder, and Valley

        A single power-flow snapshot tells us what happens at one operating
        point. But congestion patterns shift dramatically across the daily
        load cycle. We analyze three representative load levels derived from
        the system load profile:

        | Level | Scale Factor | Description |
        |-------|-------------|-------------|
        | **Peak** | 1.00 | Highest system load hour — maximum stress on transmission |
        | **Shoulder** | 0.75 | Mid-range load (morning ramp or evening decline) |
        | **Valley** | 0.55 | Overnight minimum — light loading, different flow patterns |

        These scale factors multiply every bus load proportionally, then
        generators are re-dispatched to balance. This reveals which branches
        congest only at peak versus those that are stressed even at moderate
        load levels.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Branch Utilization and the 80% Threshold

        For each branch, we compute **loading percentage**:

        $$\text{Loading \%} = \frac{|P_{\text{branch}}|}{\text{Rate A}} \times 100$$

        where Rate A is the branch's thermal MVA limit from the case file.

        Branches loaded above **80%** are flagged as **congestion candidates**.
        This threshold is standard in transmission planning — it provides a
        safety margin below the hard thermal limit while identifying branches
        that are operationally stressed. These candidates become the basis
        for flowgate definitions in the next section.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### DC vs AC OPF: Tradeoffs

        | Aspect | DC OPF | AC OPF |
        |--------|--------|--------|
        | **Variables** | Real power, angles | Real & reactive power, voltages, angles |
        | **Losses** | Neglected | Modeled |
        | **Voltage limits** | Not enforced | Enforced |
        | **Solution method** | Linear (LP/QP) | Nonlinear (NLP) |
        | **Solve time** | Milliseconds | Seconds to minutes |
        | **Accuracy** | ~95% for real-power flows | Full fidelity |
        | **Use case** | Market clearing, congestion screening | Detailed planning, voltage studies |

        For congestion identification on a 39-bus system, DC OPF is more than
        adequate. The ~5% error in branch flows is well within the margin
        provided by the 80% congestion threshold. We would switch to AC OPF
        only if voltage stability or reactive power limits were the binding
        constraints — which they rarely are in day-ahead energy market clearing.
        """
    )
    return


@app.cell
def _(Path, mo):
    from scripts.tiny_flowgates import (
        CONGESTION_THRESHOLD as _CONG_THRESHOLD,
        LOAD_LEVELS as _LOAD_LEVELS,
        main as _run_flowgate_analysis,
    )

    @mo.cache
    def _execute_dcopf():
        """Run DC OPF at three load levels via tiny_flowgates."""
        case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
        load_csv = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "timeseries"
            / "case39"
            / "load_24h.csv"
        )
        output_dir = Path(__file__).resolve().parent.parent / "data" / "timeseries" / "case39"
        return _run_flowgate_analysis(
            m_file_path=case_file,
            load_csv_path=load_csv,
            output_dir=output_dir,
        )

    opf_result = _execute_dcopf()
    opf_load_levels = _LOAD_LEVELS
    opf_cong_threshold = _CONG_THRESHOLD
    return opf_cong_threshold, opf_load_levels, opf_result


@app.cell
def _(alt, opf_cong_threshold, opf_result, pd):
    # Build a DataFrame of branch loading at peak for the sorted bar chart.
    _peak_flows = opf_result.branch_flows["peak"]
    _peak_df = pd.DataFrame(
        [
            {
                "Branch": f"{bf.from_bus}-{bf.to_bus}",
                "Loading (%)": round(bf.loading_pct, 1),
                "Congested": bf.loading_pct >= opf_cong_threshold * 100,
            }
            for bf in sorted(_peak_flows, key=lambda x: x.loading_pct, reverse=True)
        ]
    )

    _threshold_pct = opf_cong_threshold * 100

    _color_scale = alt.Scale(
        domain=[True, False],
        range=["#d62728", "#1f77b4"],
    )

    _bars = (
        alt.Chart(_peak_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Branch:N",
                sort=alt.EncodingSortField(field="Loading (%)", order="descending"),
                axis=alt.Axis(labelAngle=-60, labelFontSize=9),
                title="Branch (from-to)",
            ),
            y=alt.Y(
                "Loading (%):Q",
                title="Branch Loading (%)",
                scale=alt.Scale(domain=[0, 120]),
            ),
            color=alt.Color(
                "Congested:N",
                scale=_color_scale,
                legend=alt.Legend(title="Above 80%"),
            ),
            tooltip=[
                alt.Tooltip("Branch:N"),
                alt.Tooltip("Loading (%):Q", format=".1f"),
                alt.Tooltip("Congested:N"),
            ],
        )
    )

    _threshold_rule = (
        alt.Chart(pd.DataFrame({"y": [_threshold_pct]}))
        .mark_rule(strokeDash=[6, 3], color="black", strokeWidth=2)
        .encode(y="y:Q")
    )

    _threshold_label = (
        alt.Chart(pd.DataFrame({"y": [_threshold_pct], "label": ["80% threshold"]}))
        .mark_text(align="left", dx=5, dy=-8, fontSize=11, fontWeight="bold")
        .encode(y="y:Q", text="label:N")
    )

    peak_loading_chart = (_bars + _threshold_rule + _threshold_label).properties(
        title="Branch Loading at Peak — Congestion Candidates Highlighted",
        width=700,
        height=400,
    )
    peak_loading_chart
    return (peak_loading_chart,)


@app.cell
def _(mo):
    mo.md(
        r"""
        The chart above reveals the **dramatic concentration of congestion**
        in a handful of branches. At peak load, only a few branches exceed
        the 80% threshold (shown in red), but these are the critical
        bottlenecks that constrain power delivery across the network. The
        long tail of lightly loaded branches confirms that congestion in
        the IEEE 39-bus system is **localized**, not systemic — a pattern
        typical of meshed transmission networks where a few key corridors
        carry disproportionate flow.
        """
    )
    return


@app.cell
def _(Path, grid_plot, mo, opf_result, pd):
    # Congestion heatmap: branches colored/thickened by loading at peak
    import re as _re
    from scripts.reconcile_bus_gen import parse_matpower_case as _parse

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = _parse(_case_file)
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
        title="Branch Congestion Heatmap at Peak Load",
        bus_size=8,
        bus_color="#ccc",
        branch_color="#eee",
        branch_width=1,
    )

    # Build branch loading DataFrame from peak results
    _peak_flows = opf_result.branch_flows.get("peak", [])
    if _peak_flows:
        _flow_df = pd.DataFrame(
            [
                {"fbus": bf.from_bus, "tbus": bf.to_bus, "loading_pct": bf.loading_pct}
                for bf in _peak_flows
            ]
        )
        grid_plot.add_branch_loading(_fig, _G, _flow_df)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Congestion is **spatial**: the red/thick branches are the few corridors carrying
    disproportionate flow at peak. Green branches have ample headroom. This map
    makes visible what the bar chart above showed numerically — congestion concentrates
    in specific corridors, not uniformly across the network.
    """)
    return


@app.cell
def _(alt, opf_cong_threshold, opf_load_levels, opf_result, pd):
    # Build a combined DataFrame across all load levels.
    _rows = []
    for _level, _scale in opf_load_levels.items():
        for _bf in opf_result.branch_flows[_level]:
            _rows.append(
                {
                    "Branch": f"{_bf.from_bus}-{_bf.to_bus}",
                    "Loading (%)": round(_bf.loading_pct, 1),
                    "Load Level": _level.capitalize(),
                    "Scale Factor": _scale,
                }
            )
    _multi_df = pd.DataFrame(_rows)

    # Keep only the top-loaded branches at peak (top 15) to avoid clutter.
    _peak_top = (
        _multi_df[_multi_df["Load Level"] == "Peak"].nlargest(15, "Loading (%)")["Branch"].tolist()
    )
    _multi_filtered = _multi_df[_multi_df["Branch"].isin(_peak_top)]

    _level_order = ["Valley", "Shoulder", "Peak"]

    multi_level_chart = (
        alt.Chart(_multi_filtered)
        .mark_bar()
        .encode(
            x=alt.X(
                "Load Level:N",
                sort=_level_order,
                title="Load Level",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "Loading (%):Q",
                title="Branch Loading (%)",
            ),
            color=alt.Color(
                "Load Level:N",
                sort=_level_order,
                scale=alt.Scale(
                    domain=_level_order,
                    range=["#2ca02c", "#ff7f0e", "#d62728"],
                ),
                legend=alt.Legend(title="Load Level"),
            ),
            column=alt.Column(
                "Branch:N",
                sort=alt.EncodingSortField(field="Loading (%)", order="descending"),
                header=alt.Header(
                    labelAngle=-60,
                    labelFontSize=9,
                    titleOrient="bottom",
                ),
                title="Branch",
            ),
            tooltip=[
                alt.Tooltip("Branch:N"),
                alt.Tooltip("Load Level:N"),
                alt.Tooltip("Loading (%):Q", format=".1f"),
            ],
        )
        .properties(
            title="Branch Loading Across Load Levels (Top 15 at Peak)",
            width=30,
            height=300,
        )
    )
    multi_level_chart
    return (multi_level_chart,)


@app.cell
def _(opf_cong_threshold, opf_load_levels, opf_result, pd):
    # Identify branches exceeding the congestion threshold at ANY load level.
    _threshold_pct = opf_cong_threshold * 100
    _candidates: dict[str, dict] = {}

    for _level in opf_load_levels:
        for _bf in opf_result.branch_flows[_level]:
            _key = f"{_bf.from_bus}-{_bf.to_bus}"
            if _bf.loading_pct >= _threshold_pct:
                if _key not in _candidates:
                    _candidates[_key] = {
                        "Branch": _key,
                        "From Bus": _bf.from_bus,
                        "To Bus": _bf.to_bus,
                        "Rate A (MW)": _bf.rate_a_mw,
                        "Peak (%)": 0.0,
                        "Shoulder (%)": 0.0,
                        "Valley (%)": 0.0,
                        "Max Loading (%)": 0.0,
                        "Binding Level": "",
                    }

    # Fill in loading percentages for all levels.
    for _level in opf_load_levels:
        _col = f"{_level.capitalize()} (%)"
        for _bf in opf_result.branch_flows[_level]:
            _key = f"{_bf.from_bus}-{_bf.to_bus}"
            if _key in _candidates:
                _candidates[_key][_col] = round(_bf.loading_pct, 1)
                if _bf.loading_pct > _candidates[_key]["Max Loading (%)"]:
                    _candidates[_key]["Max Loading (%)"] = round(_bf.loading_pct, 1)
                    _candidates[_key]["Binding Level"] = _level.capitalize()

    congestion_candidates_df = pd.DataFrame(
        sorted(_candidates.values(), key=lambda r: r["Max Loading (%)"], reverse=True)
    )
    congestion_candidates_df
    return (congestion_candidates_df,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Transition: From Branch Loading to Flowgates

        Individual branch overloads are useful for spotting bottlenecks, but
        ISOs and RTOs manage congestion through **flowgates** — groups of
        related branches whose combined flow is monitored against a single
        limit. A flowgate might represent a transmission corridor, an
        interface between control areas, or a set of parallel paths that
        share load.

        The next section will show how the congestion candidates identified
        above are **grouped into flowgate definitions** by topological
        adjacency, assigned MW limits (derated to 95% of the binding branch's
        thermal rating), and prepared for use in the unit commitment
        formulation.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Flowgate Definition and Congestion Monitoring

        With congestion candidates identified, we now formalize them into
        **flowgates** — the standard mechanism ISOs and RTOs use to monitor
        and manage transmission congestion in real-time and day-ahead markets.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### What Is a Flowgate?

        A flowgate is a **monitored constraint** defined as a weighted sum of
        power flows on one or more transmission branches, subject to a MW
        limit:

        $$\sum_{k \in \mathcal{B}} w_k \cdot P_k \;\leq\; F^{\max}$$

        where $\mathcal{B}$ is the set of branches in the flowgate, $w_k$ is
        the weight (direction coefficient) for branch $k$, $P_k$ is the real
        power flow on branch $k$, and $F^{\max}$ is the flowgate MW limit.

        Flowgates are a **NERC/ISO standard** for congestion management. Every
        ISO in North America (ERCOT, MISO, PJM, CAISO, SPP, NYISO, ISO-NE)
        publishes flowgate definitions that market participants use to
        understand binding transmission constraints and their impact on
        locational marginal prices (LMPs).

        Key properties:

        - **Single-branch flowgates** monitor one critical branch (e.g., a
          tie line between regions).
        - **Multi-branch flowgates** monitor a transmission corridor where
          parallel paths share load — the weighted sum captures the aggregate
          flow across the corridor.
        - **Weights** are typically +1 or -1, indicating whether each branch's
          flow adds to or subtracts from the aggregate (depending on the
          direction convention relative to the monitored flow direction).
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Calibration from DC OPF Results

        Our flowgate identification pipeline works as follows:

        1. **Run DC OPF** at three load levels (peak, shoulder, valley) to
           compute branch flows across representative operating conditions.
        2. **Flag congested branches** — any branch loaded above 80% of its
           Rate A thermal limit at any load level.
        3. **Group by adjacency** — congested branches sharing a common bus
           are grouped into a single multi-branch flowgate (they likely form
           a transmission corridor or interface).
        4. **Set the flowgate limit** — the minimum Rate A across branches
           in the group, **derated to 95%**. The 5% derating provides
           operating margin for:
           - DC OPF approximation error (~2-3%)
           - Ambient temperature derating
           - Relay protection margins

        This 95% derating is consistent with standard ISO practice. ERCOT,
        for example, uses System Operating Limit (SOL) values that are
        typically 95-97% of the Facility Rating to account for these factors.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Branch Weights: Direction Convention

        For the TINY (IEEE 39-bus) network, all flowgate branch weights are
        **+1.0**. This means every branch in the flowgate contributes
        positively to the aggregate flow in the monitored direction.

        In larger networks, weights of **-1** appear when a branch's "from-to"
        convention runs opposite to the flowgate's monitored direction. For
        example, if a flowgate monitors northbound flow on a corridor and one
        branch has its from-bus at the north end, that branch would receive
        weight -1 so that its southbound (positive) flow subtracts from the
        northbound aggregate.

        For our 39-bus case, the adjacency-based grouping produces flowgates
        where all constituent branches flow in the same direction through the
        corridor, so uniform +1 weights are correct.
        """
    )
    return


@app.cell
def _(opf_result, pd):
    # Extract flowgate definitions from the OPF result.
    # The FlowgateResult already contains fully constructed FlowgateDefinition
    # records produced by tiny_flowgates.main().
    _fg_rows = []
    for _fg in opf_result.flowgates:
        _branch_strs = [f"{fb}-{tb}" for fb, tb in zip(_fg.from_buses, _fg.to_buses)]
        _fg_rows.append(
            {
                "Flowgate ID": _fg.flowgate_id,
                "Name": _fg.name,
                "Branches": "; ".join(_branch_strs),
                "Weights": "; ".join(f"{w:+.0f}" for w in _fg.weights),
                "Limit (MW)": round(_fg.limit_mw, 1),
                "Binding Level": _fg.binding_load_level.capitalize(),
                "Max Loading (%)": round(_fg.max_loading_pct, 1),
            }
        )

    flowgate_defs_df = pd.DataFrame(_fg_rows)
    flowgate_defs_df
    return (flowgate_defs_df,)


@app.cell
def _(alt, flowgate_defs_df, pd):
    # Flowgate summary table rendered as an Altair heatmap-style table.
    _table_data = flowgate_defs_df.copy()
    _table_data["row_index"] = range(len(_table_data))

    # Melt into long form for the text-table approach.
    _cols = [
        "Flowgate ID",
        "Branches",
        "Weights",
        "Limit (MW)",
        "Binding Level",
        "Max Loading (%)",
    ]
    _melted = _table_data.melt(
        id_vars=["row_index"],
        value_vars=_cols,
        var_name="Column",
        value_name="Value",
    )
    _melted["Value"] = _melted["Value"].astype(str)

    flowgate_summary_table = (
        alt.Chart(_melted)
        .mark_text(fontSize=12)
        .encode(
            x=alt.X(
                "Column:N",
                sort=_cols,
                title=None,
                axis=alt.Axis(
                    orient="top",
                    labelAngle=0,
                    labelFontWeight="bold",
                    labelFontSize=12,
                ),
            ),
            y=alt.Y(
                "row_index:O",
                title=None,
                axis=alt.Axis(labels=False, ticks=False),
            ),
            text="Value:N",
            color=alt.condition(
                alt.datum.Column == "Max Loading (%)",
                alt.value("#d62728"),
                alt.value("#333333"),
            ),
        )
        .properties(
            title="Flowgate Summary",
            width=650,
            height=max(60, len(flowgate_defs_df) * 30),
        )
    )
    flowgate_summary_table
    return (flowgate_summary_table,)


@app.cell
def _(Path, grid_plot, mo, opf_result, pd):
    # Topology diagram: flowgate corridors highlighted in distinct colors
    import re as _re
    from scripts.reconcile_bus_gen import parse_matpower_case as _parse

    _case_file = Path(__file__).resolve().parent.parent / "data" / "networks" / "case39.m"
    _case_data = _parse(_case_file)
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
        title="Flowgate Corridors on IEEE 39-Bus Network",
        bus_size=8,
        bus_color="#ccc",
    )

    _fg_colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628"]
    _fg_data = []
    for _i, _fg in enumerate(opf_result.flowgates):
        _branches = list(zip(_fg.from_buses, _fg.to_buses))
        _fg_data.append(
            {
                "name": _fg.flowgate_id,
                "branches": _branches,
                "color": _fg_colors[_i % len(_fg_colors)],
            }
        )
    grid_plot.add_flowgate_highlights(_fig, _fg_data)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Each flowgate is highlighted as a colored corridor through the network. These are
    the transmission bottlenecks identified by the congestion analysis — the branches
    that hit or approach their thermal limits at peak load. Flowgate constraints in the
    SCUC formulation will limit aggregate flow through these corridors.
    """)
    return


@app.cell
def _(alt, opf_load_levels, opf_result, pd):
    # Flow vs limit per flowgate at each load level.
    _fg_flow_rows = []
    for _fg in opf_result.flowgates:
        for _level, _scale in opf_load_levels.items():
            _level_flows = opf_result.branch_flows[_level]
            _flow_map = {f.branch_index: f for f in _level_flows}
            # Aggregate weighted flow across flowgate branches.
            _agg_flow = sum(
                w * abs(_flow_map[bi].flow_mw)
                for bi, w in zip(_fg.branches, _fg.weights)
                if bi in _flow_map
            )
            _fg_flow_rows.append(
                {
                    "Flowgate": _fg.flowgate_id,
                    "Load Level": _level.capitalize(),
                    "Flow (MW)": round(_agg_flow, 1),
                    "Limit (MW)": round(_fg.limit_mw, 1),
                }
            )

    _fg_flow_df = pd.DataFrame(_fg_flow_rows)

    _level_sort = ["Valley", "Shoulder", "Peak"]

    _flow_bars = (
        alt.Chart(_fg_flow_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Load Level:N",
                sort=_level_sort,
                title="Load Level",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "Flow (MW):Q",
                title="Aggregate Flow (MW)",
            ),
            color=alt.Color(
                "Load Level:N",
                sort=_level_sort,
                scale=alt.Scale(
                    domain=_level_sort,
                    range=["#2ca02c", "#ff7f0e", "#d62728"],
                ),
                legend=alt.Legend(title="Load Level"),
            ),
            tooltip=[
                alt.Tooltip("Flowgate:N"),
                alt.Tooltip("Load Level:N"),
                alt.Tooltip("Flow (MW):Q", format=".1f"),
                alt.Tooltip("Limit (MW):Q", format=".1f"),
            ],
        )
    )

    # Add limit line per flowgate using a rule mark.
    _limit_rule = (
        alt.Chart(_fg_flow_df)
        .mark_rule(color="black", strokeDash=[6, 3], strokeWidth=2)
        .encode(
            y="Limit (MW):Q",
        )
    )

    # Layer first, then facet (Altair doesn't allow layering faceted charts).
    flow_vs_limit_chart = (
        alt.layer(_flow_bars, _limit_rule)
        .properties(
            title="Flowgate Flow vs Limit by Load Level",
            width=100,
            height=300,
        )
        .facet(
            column=alt.Column(
                "Flowgate:N",
                header=alt.Header(
                    labelFontSize=11,
                    labelFontWeight="bold",
                    titleOrient="bottom",
                ),
                title="Flowgate",
            ),
        )
    )
    flow_vs_limit_chart
    return (flow_vs_limit_chart,)


@app.cell
def _(alt, opf_cong_threshold, opf_result, pd):
    # Branch-flowgate overlay: branch loading at peak, annotated with
    # flowgate membership.
    _peak_flows = opf_result.branch_flows["peak"]

    # Build a mapping from branch_index to flowgate ID(s).
    _branch_to_fg: dict[int, str] = {}
    for _fg in opf_result.flowgates:
        for _bi in _fg.branches:
            _branch_to_fg[_bi] = _fg.flowgate_id

    _overlay_rows = []
    for _bf in sorted(_peak_flows, key=lambda x: x.loading_pct, reverse=True):
        _fg_label = _branch_to_fg.get(_bf.branch_index, "None")
        _overlay_rows.append(
            {
                "Branch": f"{_bf.from_bus}-{_bf.to_bus}",
                "Loading (%)": round(_bf.loading_pct, 1),
                "Flowgate": _fg_label,
                "In Flowgate": _fg_label != "None",
            }
        )

    _overlay_df = pd.DataFrame(_overlay_rows)

    # Keep top 20 branches for readability.
    _overlay_top = _overlay_df.head(20)

    _fg_ids = sorted({r["Flowgate"] for r in _overlay_rows if r["Flowgate"] != "None"})
    _fg_domain = _fg_ids + ["None"]
    _fg_colors = [
        "#e41a1c",
        "#377eb8",
        "#4daf4a",
        "#984ea3",
        "#ff7f00",
        "#a65628",
        "#f781bf",
        "#999999",
    ][: len(_fg_ids)] + ["#cccccc"]

    _overlay_bars = (
        alt.Chart(_overlay_top)
        .mark_bar()
        .encode(
            x=alt.X(
                "Branch:N",
                sort=alt.EncodingSortField(field="Loading (%)", order="descending"),
                axis=alt.Axis(labelAngle=-60, labelFontSize=9),
                title="Branch (from-to)",
            ),
            y=alt.Y(
                "Loading (%):Q",
                title="Branch Loading (%)",
                scale=alt.Scale(domain=[0, 120]),
            ),
            color=alt.Color(
                "Flowgate:N",
                scale=alt.Scale(
                    domain=_fg_domain,
                    range=_fg_colors,
                ),
                legend=alt.Legend(title="Flowgate"),
            ),
            tooltip=[
                alt.Tooltip("Branch:N"),
                alt.Tooltip("Loading (%):Q", format=".1f"),
                alt.Tooltip("Flowgate:N"),
            ],
        )
    )

    _threshold_pct_overlay = opf_cong_threshold * 100
    _overlay_rule = (
        alt.Chart(pd.DataFrame({"y": [_threshold_pct_overlay]}))
        .mark_rule(strokeDash=[6, 3], color="black", strokeWidth=2)
        .encode(y="y:Q")
    )

    branch_flowgate_overlay = (_overlay_bars + _overlay_rule).properties(
        title=("Branch Loading at Peak — Colored by Flowgate Membership"),
        width=700,
        height=400,
    )
    branch_flowgate_overlay
    return (branch_flowgate_overlay,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Flowgate Enforcement in UC/SCED

        In the unit commitment (UC) and security-constrained economic dispatch
        (SCED) formulations used by ISOs, flowgate constraints enter as
        **linear inequality constraints** on the dispatch variables:

        $$\sum_{k \in \mathcal{B}} w_k \cdot \text{PTDF}_k \cdot P_g
        \;\leq\; F^{\max}$$

        where $\text{PTDF}_k$ is the Power Transfer Distribution Factor
        mapping generator $g$'s output to flow on branch $k$. This means
        flowgates constrain the **dispatch decisions** — generators on the
        "sending" side of a congested corridor are backed down, while
        generators on the "receiving" side are dispatched up, creating the
        LMP separation that signals congestion cost to the market.

        When a flowgate binds (flow equals the limit), the **shadow price**
        of that constraint becomes the **congestion component** of the LMP
        at every bus, weighted by each bus's PTDF sensitivity to the
        flowgate. This is the mechanism by which transmission congestion
        creates price differences across the network.

        In Notebook 06, we will implement these flowgate constraints in an
        economic dispatch formulation and observe the resulting LMP separation.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Infrastructure Summary

        This notebook has built up the complete **augmented IEEE 39-bus
        network** that will serve as the foundation for power system
        optimization in the remaining tutorials. Here is what we have
        assembled:

        | Component | Source | Key Parameters |
        |-----------|--------|----------------|
        | **Network topology** | `case39.m` (MATPOWER) | 39 buses, 10 generators, 46 branches |
        | **Load profiles** | `load_24h.csv` | 24-hour bus-level MW demand |
        | **BESS** | `tiny_bess_dr.py` | 50 MW / 200 MWh at bus 25, 4-hour duration |
        | **Demand Response** | `tiny_bess_dr.py` | 25 MW curtailment at bus 20, energy-neutral |
        | **Flowgates** | `tiny_flowgates.py` | Identified from DC OPF, 95% derated limits |
        | **DC OPF results** | Computed in-notebook | Branch flows at peak/shoulder/valley |

        ### What Comes Next

        Before we can run optimization, we need an **uncertainty model**
        for renewable output. Notebook 04 builds stochastic scenarios
        from forecast error distributions. Notebook 05 validates the
        complete dataset for referential integrity and physical
        plausibility. Then Notebook 06 (*Economic Dispatch and
        Locational Pricing*) brings everything together:

        1. **Formulate a 24-hour economic dispatch** as a linear program
        2. **Co-optimize BESS** alongside conventional generation
        3. **Enforce flowgate constraints** using the PTDF-based formulation
        4. **Compute locational marginal prices (LMPs)** from dual variables
        5. **Analyze congestion rents** — the revenue from price separation
           across flowgates

        The augmented network defined here ensures that Notebook 06 has
        realistic flexibility resources and binding transmission constraints
        to produce meaningful market-clearing results.
        """
    )
    return


if __name__ == "__main__":
    app.run()
