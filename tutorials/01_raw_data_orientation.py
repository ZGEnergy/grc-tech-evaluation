import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import re
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd

    # Ensure the data package is importable (installed via uv as grc-data-augmentation)
    from scripts.reconcile_bus_gen import parse_matpower_case
    from scripts.tiny_cleanup_classify import clean_and_classify_case39

    import grid_plot

    return (
        Path,
        alt,
        clean_and_classify_case39,
        grid_plot,
        mo,
        parse_matpower_case,
        pd,
        re,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Raw Data Orientation: The IEEE 39-Bus System

    This notebook introduces the **raw data** that every power-system modeling tool
    in our evaluation consumes. By the end you will understand:

    1. What a **MATPOWER** case file contains and how it encodes a power network.
    2. What the **IEEE 39-bus "New England"** test system represents physically.
    3. The difference between a **power-flow snapshot** and a
       **power-flow optimization** problem.
    4. What data the raw case file **has** — and critically, what it **lacks**.

    All six tools we evaluate (PyPSA, pandapower, GridCal, PowerModels.jl,
    PowerSimulations.jl, and MATPOWER/Octave) can ingest this same `.m` file format,
    making it the natural common starting point for comparison.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## What is MATPOWER?

    **MATPOWER** is an open-source MATLAB/Octave package for solving power flow and
    optimal power flow problems. It has been the de facto standard for academic
    power-systems research since its first release in 1997.

    The most important artifact MATPOWER gives us is its **case file format** (`.m`
    files). A case file is a plain-text MATLAB function that returns a struct `mpc`
    with matrices describing the network:

    | Matrix | Rows represent | Key columns |
    |--------|---------------|-------------|
    | `mpc.bus` | Buses (nodes) | bus ID, type, real/reactive demand, base voltage |
    | `mpc.gen` | Generators | bus ID, real/reactive output, capacity limits |
    | `mpc.branch` | Branches (lines and transformers) | from/to bus, impedance, thermal ratings |
    | `mpc.gencost` | Generator cost curves | cost model type, coefficients |

    Each row is a semicolon-terminated list of numbers. The column order follows the
    MATPOWER Case Format Version 2 specification. Comments (lines starting with `%`)
    document the column layout.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## The IEEE 39-Bus "New England" Test System

    The IEEE 39-bus system is a simplified model of the **New England 345 kV
    transmission network**. It was first published in 1970 by researchers at New
    England Electric System and General Electric, and has since become one of the
    most widely used benchmark cases in power-systems research.

    **Physical structure:**

    - **39 buses** (nodes) connected by **46 branches** (transmission lines and
      transformers) operating at 345 kV.
    - **10 generators** representing the major generation plants in the region:
      hydro, nuclear, fossil (coal and gas), plus one large equivalent generator
      (bus 39) representing the interconnection to the rest of the Eastern
      Interconnect.
    - **19 load buses** drawing a combined ~6,100 MW of real power demand.
    - **1 reference (slack) bus** (bus 31) that balances supply and demand.

    The system is small enough to inspect by hand yet large enough to exhibit
    realistic phenomena like voltage regulation, line congestion, and generator
    dispatch tradeoffs.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Power-Flow Snapshot vs. Power-Flow Optimization

    The data in `case39.m` is a **power-flow snapshot**: a single instant in time
    where every bus voltage, generator output, and line flow is fully specified
    (or solvable). Think of it as a photograph of the grid at one moment.

    Power-system problems form a **hierarchy**, each requiring progressively more
    data:

    | Problem | Time scope | Decides | Data needed beyond topology |
    |---------|-----------|---------|----------------------------|
    | **PF** (Power Flow) | Single instant | Voltages & flows | Bus injections (Pd, Pg) |
    | **OPF** (Optimal Power Flow) | Single instant | Least-cost dispatch | + generator costs, limits |
    | **SCUC** (Security-Constrained UC) | 24-168 hours | On/off + dispatch per hour | + ramp rates, min up/down, startup costs, hourly loads |
    | **SCED** (Security-Constrained ED) | Single hour (real-time) | Re-dispatch given commitments | + SCUC solution as input |

    A MATPOWER `.m` file contains enough data for **PF** and **OPF** — but not
    SCUC or SCED. Our later tutorials will augment this snapshot with the temporal
    data (hourly load profiles, ramp rates, startup costs) needed to climb this
    hierarchy.
    """)
    return


@app.cell
def _(Path, mo, parse_matpower_case, pd):
    @mo.cache
    def load_bus_gen_data():
        """Parse case39.m and convert buses and generators to DataFrames."""
        case_file = Path(__file__).parent.parent / "data" / "networks" / "case39.m"
        case_data = parse_matpower_case(case_file)

        bus_df = pd.DataFrame(
            [
                {
                    "bus_id": b.bus_id,
                    "bus_type": b.bus_type.value,
                    "bus_type_name": b.bus_type.name,
                    "pd_mw": b.pd,
                    "qd_mvar": b.qd,
                    "base_kv": b.base_kv,
                }
                for b in case_data.buses
            ]
        )

        gen_df = pd.DataFrame(
            [
                {
                    "gen_bus": g.gen_bus,
                    "pg_mw": g.pg,
                    "qg_mvar": g.qg,
                    "pmax_mw": g.pmax,
                    "pmin_mw": g.pmin,
                    "fuel_type": g.fuel_type,
                }
                for g in case_data.generators
            ]
        )

        return bus_df, gen_df

    bus_df, gen_df = load_bus_gen_data()
    return bus_df, gen_df


@app.cell
def _(bus_df, gen_df, mo):
    mo.md(
        f"""
        ### Parsed Bus and Generator Data

        The parser extracted **{len(bus_df)} buses** and **{len(gen_df)} generators**
        from `case39.m`. These DataFrames are the foundation for all visualizations
        and analyses in subsequent cells.

        **Bus DataFrame** (first 10 rows):
        """
    )
    return


@app.cell
def _(bus_df):
    bus_df.head(10)
    return


@app.cell
def _(bus_df, grid_plot, mo):
    # Topology diagram: buses color-coded by type (PQ=blue, PV=orange, Ref=red)
    import plotly.graph_objects as _go
    import networkx as _nx

    _G_bus_only = _nx.Graph()
    for _, _r in bus_df.iterrows():
        _bid = int(_r["bus_id"])
        _G_bus_only.add_node(
            _bid,
            pos=grid_plot.BUS_POSITIONS[_bid],
            pd_mw=_r["pd_mw"],
            bus_type_name=_r["bus_type_name"],
        )

    _type_colors = {"PQ": "#4c78a8", "PV": "#ff7f0e", "Ref": "#d62728"}
    _node_x, _node_y, _colors, _hover, _ids = [], [], [], [], []
    for _n in _G_bus_only.nodes():
        _x, _y = grid_plot.BUS_POSITIONS[_n]
        _node_x.append(_x)
        _node_y.append(_y)
        _ids.append(_n)
        _btype = _G_bus_only.nodes[_n]["bus_type_name"]
        _pd = _G_bus_only.nodes[_n]["pd_mw"]
        _colors.append(_type_colors.get(_btype, "#4c78a8"))
        _hover.append(f"Bus {_n}<br>Type: {_btype}<br>Load: {_pd:.0f} MW")

    _fig_buses = _go.Figure()
    # Add one trace per bus type for proper legend
    for _tname, _tcol in _type_colors.items():
        _mask = [
            i for i, _n in enumerate(_ids) if _G_bus_only.nodes[_ids[i]]["bus_type_name"] == _tname
        ]
        if not _mask:
            continue
        _fig_buses.add_trace(
            _go.Scatter(
                x=[_node_x[i] for i in _mask],
                y=[_node_y[i] for i in _mask],
                mode="markers+text",
                marker=dict(size=14, color=_tcol, line=dict(width=1, color="white")),
                text=[str(_ids[i]) for i in _mask],
                textposition="top center",
                textfont=dict(size=8),
                hovertext=[_hover[i] for i in _mask],
                hoverinfo="text",
                name=_tname,
            )
        )
    _fig_buses.update_layout(
        title="IEEE 39-Bus System: Bus Locations by Type",
        **grid_plot._LAYOUT_DEFAULTS,
    )
    mo.ui.plotly(_fig_buses)
    return


@app.cell
def _(mo):
    mo.md(r"""
    The map above shows all 39 buses placed at their canonical one-line diagram
    positions. **PQ buses** (blue) are pure load/transfer buses. **PV buses** (orange)
    have generators that regulate voltage. The single **Ref bus** (red, bus 31) is the
    slack bus that balances the system. Notice the generators are concentrated on the
    perimeter — the interior buses form the transmission backbone.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    **Generator DataFrame:**
    """)
    return


@app.cell
def _(gen_df):
    gen_df
    return


@app.cell
def _(branch_df, bus_df, gen_df, grid_plot, mo):
    # Topology diagram: generators on their buses, colored by fuel, sized by Pmax
    _G = grid_plot.build_graph(bus_df, branch_df)
    _fig_gens = grid_plot.plot_base_topology(
        _G,
        title="Generators on the IEEE 39-Bus Network",
        bus_size=8,
        bus_color="#ccc",
    )
    grid_plot.add_generator_markers(_fig_gens, gen_df)
    mo.ui.plotly(_fig_gens)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Each **square marker** represents a generator, colored by fuel type and sized by
    maximum capacity (Pmax). The large hydro unit (bus 30, 1040 MW) and the
    interconnection equivalent (bus 39, 1000 MW) dominate the left side of the
    network. Nuclear units are spread across multiple buses, while the two coal
    plants and single gas unit cluster in the center-right.
    """)
    return


@app.cell
def _(Path, pd, re):
    # Parse branch data directly from raw .m file text using regex.
    # The existing parse_matpower_case() returns buses and generators but not branches,
    # so we extract mpc.branch inline to keep the notebook self-contained.

    _case_file = Path(__file__).parent.parent / "data" / "networks" / "case39.m"
    _raw_text = _case_file.read_text()

    _branch_match = re.search(
        r"mpc\.branch\s*=\s*\[([^\]]*)\]",
        _raw_text,
        re.DOTALL,
    )
    assert _branch_match is not None, "Could not locate mpc.branch block in case39.m"

    _branch_rows: list[list[float]] = []
    for _line in _branch_match.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _branch_rows.append([float(v) for v in _line.split()])

    branch_df = pd.DataFrame(
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
    # Convert bus IDs to integers for consistency with bus_df
    branch_df["fbus"] = branch_df["fbus"].astype(int)
    branch_df["tbus"] = branch_df["tbus"].astype(int)
    branch_df["status"] = branch_df["status"].astype(int)
    return (branch_df,)


@app.cell
def _(branch_df, mo):
    mo.md(
        f"""
        ### Branch Data

        Extracted **{len(branch_df)} branches** (transmission lines and transformers)
        from `mpc.branch`. Each row specifies the from-bus, to-bus, series impedance
        (r + jx in per-unit), shunt susceptance (b), thermal ratings (MVA), and
        transformer tap ratio.

        **How to tell lines from transformers:** In MATPOWER, a nonzero `ratio` column
        indicates a **transformer** — the ratio is the off-nominal tap setting. A
        `ratio` of 0 means a plain transmission line (MATPOWER treats 0 as "no
        transformer, use ratio = 1.0 implicitly"). For example, the branch from
        bus 2 to bus 30 has `ratio = 1.025` — this is a generator step-up
        transformer with a tap 2.5% above nominal, connecting the hydro generator
        at bus 30 to the 345 kV backbone at bus 2.

        **Branch DataFrame** (first 10 rows):
        """
    )
    return


@app.cell
def _(branch_df):
    branch_df.head(10)
    return


@app.cell
def _(branch_df, bus_df, gen_df, grid_plot, mo):
    # Full connected topology: buses + branches + generators + loads
    _G_full = grid_plot.build_graph(bus_df, branch_df)
    _fig_full = grid_plot.plot_base_topology(
        _G_full,
        title="Complete IEEE 39-Bus Network: Topology, Generators, and Loads",
        bus_size=8,
        bus_color="#ccc",
    )
    grid_plot.add_generator_markers(_fig_full, gen_df, show_label=False)
    grid_plot.add_load_markers(_fig_full, bus_df)
    mo.ui.plotly(_fig_full)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Now the full picture: **46 branches** connect the buses into a meshed network.
    Generator squares sit on the perimeter, load triangles (sized by MW demand)
    concentrate in the interior. The largest loads are at buses 3 (322 MW),
    8 (522 MW), 15 (320 MW), 20 (680 MW), and 39 (1104 MW — the interconnect).
    Hover over any element for details.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## Raw Data Exploration

    The cells below visualize the **raw (pre-cleanup) data** parsed from
    `case39.m`. These charts reveal the structure of the IEEE 39-bus system
    and highlight important artifacts in the snapshot data that must be
    understood before any modeling work begins.
    """)
    return


@app.cell
def _(alt, gen_df):
    generator_pmax_bar_chart = (
        alt.Chart(gen_df, title="Generator Pmax by Bus")
        .mark_bar()
        .encode(
            x=alt.X("gen_bus:N", title="Generator Bus", sort="ascending"),
            y=alt.Y("pmax_mw:Q", title="Pmax (MW)"),
            color=alt.Color(
                "gen_bus:N",
                title="Bus",
                legend=None,
            ),
            tooltip=["gen_bus:N", "pmax_mw:Q", "fuel_type:N"],
        )
        .properties(width=600, height=350)
    )
    return (generator_pmax_bar_chart,)


@app.cell
def _(generator_pmax_bar_chart):
    generator_pmax_bar_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    **What to notice:** ~50% of generator capacity is heavily concentrated on a
    few buses. Bus 30 and 39 account for 33% of system capacity. The
    remaining nine generators range from roughly 250 MW to 830 MW. This
    uneven distribution is typical of real transmission systems where a
    handful of large plants account for most of the installed capacity.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Bus Type Distribution & Voltage Profile

    Every bus in a power-flow model has a **type** that determines what is known
    vs. what must be solved:

    - **PQ (Load) bus** — Real (P) and reactive (Q) demand are specified; voltage
      magnitude and angle are solved by the power flow.
    - **PV (Generator) bus** — Real power output (P) and voltage magnitude (V) are
      specified; reactive power and voltage angle are solved.
    - **Ref (Slack) bus** — Voltage magnitude and angle are fixed (the reference
      point); real and reactive power are solved to balance the system.

    The IEEE 39-bus system has 29 PQ buses, 9 PV buses (one per non-slack
    generator), and 1 Ref bus (bus 31).
    """)
    return


@app.cell
def _(alt, bus_df):
    _type_chart = (
        alt.Chart(bus_df, title="Bus Type Distribution")
        .mark_bar()
        .encode(
            x=alt.X("bus_type_name:N", title="Bus Type"),
            y=alt.Y("count():Q", title="Count"),
            color=alt.Color(
                "bus_type_name:N",
                title="Type",
                legend=None,
            ),
            tooltip=["bus_type_name:N", "count():Q"],
        )
        .properties(width=300, height=300)
    )

    bus_type_chart = _type_chart
    return (bus_type_chart,)


@app.cell
def _(Path, pd, re):
    # Parse Vm (voltage magnitude) from raw case39.m since the parser
    # dataclass does not include it. MATPOWER bus format column 8 is Vm.
    _case_path = Path(__file__).parent.parent / "data" / "networks" / "case39.m"
    _raw = _case_path.read_text()
    _bus_match = re.search(r"mpc\.bus\s*=\s*\[([^\]]*)\]", _raw, re.DOTALL)
    assert _bus_match is not None, "Could not find mpc.bus in case39.m"

    _vm_rows: list[dict] = []
    for _line in _bus_match.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _vals = _line.split()
        _vm_rows.append({"bus_id": int(float(_vals[0])), "vm_pu": float(_vals[7])})

    bus_vm_df = pd.DataFrame(_vm_rows)
    return (bus_vm_df,)


@app.cell
def _(alt, bus_vm_df):
    _vm_chart = (
        alt.Chart(bus_vm_df, title="Bus Voltage Magnitudes (Vm)")
        .mark_circle(size=80)
        .encode(
            x=alt.X("bus_id:O", title="Bus ID", sort="ascending"),
            y=alt.Y(
                "vm_pu:Q",
                title="Vm (p.u.)",
                scale=alt.Scale(zero=False),
            ),
            tooltip=["bus_id:O", "vm_pu:Q"],
        )
        .properties(width=600, height=300)
    )

    bus_voltage_chart = _vm_chart
    return (bus_voltage_chart,)


@app.cell
def _(bus_type_chart, bus_voltage_chart, mo):
    bus_type_and_voltage_charts = mo.hstack([bus_type_chart, bus_voltage_chart])
    return (bus_type_and_voltage_charts,)


@app.cell
def _(bus_type_and_voltage_charts):
    bus_type_and_voltage_charts
    return


@app.cell
def _(mo):
    mo.md(r"""
    **What to notice:** The voltage magnitudes are **not** all 1.0 p.u. because
    this is a **solved snapshot**: the values reflect the converged power-flow
    solution, not flat-start initial conditions. Generator buses tend to have
    voltages above 1.0 p.u. because they regulate voltage, while load buses sag
    slightly below.

    **What is per-unit (p.u.)?** The per-unit system normalizes electrical
    quantities relative to a chosen base value. For voltage, the base is the
    nominal voltage (345 kV here), so `Vm = 1.0 p.u.` means exactly 345 kV.
    Normal operating range is **0.95-1.05 p.u.** Values outside **0.90-1.10 p.u.**
    indicate serious voltage problems that would trigger protective relay action.
    The p.u. system makes it easy to compare values across different voltage levels
    and simplifies impedance calculations.
    """)
    return


@app.cell
def _(branch_df, mo):
    _n_xfmr = (branch_df["ratio"] != 0).sum()
    _n_line = (branch_df["ratio"] == 0).sum()
    mo.md(
        f"""
        ### Branch Summary

        The 46 branches comprise **{_n_line} transmission lines** (`ratio = 0`)
        and **{_n_xfmr} transformers** (`ratio != 0`). Transformers connect
        generator buses to the 345 kV backbone — each generator bus in the IEEE
        39-bus system connects to the transmission network through a single
        step-up transformer.

        The branch from bus 2 to bus 30 (`ratio = 1.025`) is a good example:
        it is the generator step-up transformer connecting the hydro plant at
        bus 30 to the transmission backbone at bus 2. The tap setting of 1.025
        means the transformer ratio is 2.5% above nominal — a typical value
        used for voltage regulation at the generator terminals.
        """
    )
    return


@app.cell
def _(branch_df):
    branch_summary_table = branch_df
    return (branch_summary_table,)


@app.cell
def _(branch_summary_table):
    branch_summary_table
    return


@app.cell
def _(branch_df, bus_df, gen_df, mo):
    _n_buses = len(bus_df)
    _n_gens = len(gen_df)
    _n_branches = len(branch_df)
    _total_pmax = gen_df["pmax_mw"].sum()
    _total_pd = bus_df["pd_mw"].sum()
    _total_pg = gen_df["pg_mw"].sum()
    _reserve = _total_pmax - _total_pg

    system_summary_markdown = mo.md(
        f"""
        ## System Snapshot Status

        | Metric | Value |
        |--------|-------|
        | Buses | {_n_buses} |
        | Generators | {_n_gens} |
        | Branches | {_n_branches} |
        | Total Pmax (capacity) | {_total_pmax:.0f} MW |
        | Total Pg (current dispatch) | {_total_pg:.0f} MW |
        | Total Load (Pd) | {_total_pd:.1f} MW |
        | Reserve headroom (Pmax - Pg) | {_reserve:.0f} MW |
        """
    )
    return (system_summary_markdown,)


@app.cell
def _(system_summary_markdown):
    system_summary_markdown
    return


@app.cell
def _(alt, bus_df, gen_df, mo, pd):
    # Snapshot status visualization: stacked bar showing Pg (serving load) and headroom
    _total_pg = gen_df["pg_mw"].sum()
    _total_pmax = gen_df["pmax_mw"].sum()
    _total_pd = bus_df["pd_mw"].sum()
    _headroom = _total_pmax - _total_pg

    _status_df = pd.DataFrame(
        [
            {"category": "Generation", "segment": "Serving Load (Pg)", "mw": _total_pg},
            {"category": "Generation", "segment": "Reserve Headroom", "mw": _headroom},
            {"category": "Demand", "segment": "Total Load (Pd)", "mw": _total_pd},
        ]
    )

    _bars = (
        alt.Chart(_status_df[_status_df["category"] == "Generation"])
        .mark_bar(width=80)
        .encode(
            x=alt.X("category:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("mw:Q", title="MW", stack=True),
            color=alt.Color(
                "segment:N",
                title="",
                scale=alt.Scale(
                    domain=["Serving Load (Pg)", "Reserve Headroom"],
                    range=["#4c78a8", "#a8d8a8"],
                ),
            ),
            order=alt.Order("segment:N", sort="descending"),
            tooltip=["segment:N", alt.Tooltip("mw:Q", format=",.0f")],
        )
    )

    _load_rule = (
        alt.Chart(pd.DataFrame({"y": [_total_pd]}))
        .mark_rule(color="black", strokeWidth=2, strokeDash=[6, 4])
        .encode(y="y:Q")
    )
    _load_label = (
        alt.Chart(pd.DataFrame({"y": [_total_pd], "label": [f"Load = {_total_pd:,.0f} MW"]}))
        .mark_text(align="left", dx=50, dy=-8, fontSize=12, fontWeight="bold")
        .encode(y="y:Q", text="label:N")
    )

    snapshot_chart = (_bars + _load_rule + _load_label).properties(
        title="Snapshot Status: 2024-01-15 14:00 EST (simulated)",
        width=300,
        height=400,
    )

    mo.md(
        f"""
        This is **one frozen instant**. The system is generating {_total_pg:,.0f} MW
        to serve {_total_pd:,.0f} MW of load, with {_headroom:,.0f} MW of reserve
        headroom. The snapshot tells us nothing about what happened an hour ago or
        what will happen next.
        """
    )
    return (snapshot_chart,)


@app.cell
def _(snapshot_chart):
    snapshot_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## Snapshot Cleanup: Why Raw Data Can't Be Used Directly

    The `case39.m` file is a **converged power-flow snapshot** — every value
    reflects the solved operating point at a single instant. Several fields
    must be modified before the data can serve as input to an optimization
    (OPF or unit commitment). The cleanup rules below explain what changes
    are needed and why.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Cleanup Rule 1: Zero Out Pg and Qg

    The snapshot's `Pg` (real power output) and `Qg` (reactive power output)
    columns contain the **solved dispatch** from the original power-flow run.
    If left in place, an optimizer might interpret them as initial conditions
    or warm-start hints, biasing the solution toward the snapshot's operating
    point instead of finding the true optimum. Zeroing both columns forces the
    optimizer to determine dispatch from scratch using only the cost curves
    and constraints.

    ### Cleanup Rule 2: Normalize Vm and Va

    Bus voltage magnitudes (`Vm`) and angles (`Va`) in the snapshot reflect
    the converged network state. Generator buses show voltages above 1.0 p.u.
    (voltage regulation), while load buses sag below. For AC-OPF, these
    non-flat values act as a **warm start** that can trap the solver in a
    local optimum near the snapshot's operating point. Resetting all `Vm` to
    1.0 p.u. and all `Va` to 0 degrees provides a neutral flat start.

    ### Cleanup Rule 3: Hydro Pmin Special Treatment

    Generator 0 (bus 30) is a large hydro reservoir unit with Pmax = 1,040 MW.
    Unlike thermal plants that can idle near zero output, reservoir hydro units
    typically have **minimum flow requirements** for downstream water management.
    The cleanup sets Pmin to **25% of Pmax** (260 MW) for hydro generators
    above a capacity threshold, while all other generators get Pmin = 0.

    ### Cleanup Rule 4: Fuel Classification

    The standard `case39.m` file lacks a `genfuel` field — there is no
    machine-readable fuel type. However, the file header comments document
    the intended generator types (hydro, nuclear, fossil). The cleanup
    pipeline reads the **CASE39_FUEL_MAP** hardcoded mapping to assign each
    generator a `FuelCategory` (hydro, nuclear, coal, gas) and then maps
    those to **RTS-GMLC technology classes** that determine which operational
    parameter templates (ramp rates, min up/down times, startup costs) are
    applied in later tutorials.
    """)
    return


@app.cell
def _(Path, clean_and_classify_case39, mo):
    @mo.cache
    def run_cleanup():
        """Execute cleanup and classification pipeline for case39."""
        networks_dir = Path(__file__).parent.parent / "data" / "networks"
        output_dir = Path(__file__).parent.parent / "data" / "timeseries"
        return clean_and_classify_case39(networks_dir, output_dir)

    cleanup_result = run_cleanup()
    return (cleanup_result,)


@app.cell
def _(cleanup_result, mo, pd):
    _rows = [
        {
            "gen_index": c.gen_index,
            "bus": c.bus_id,
            "fuel_category": c.fuel_category,
            "rts_gmlc_class": c.rts_gmlc_class.value,
            "pmax_mw": c.pmax_mw,
            "pmin_mw": c.pmin_mw,
        }
        for c in cleanup_result.classifications
    ]
    classification_df = pd.DataFrame(_rows)

    mo.md(
        f"""
        ### Generator Classification Table

        The table below shows all **{len(classification_df)} generators** with
        their fuel category (from header comments), RTS-GMLC technology class,
        and post-cleanup Pmin values. Note that only the hydro unit (gen 0,
        bus 30) retains a nonzero Pmin.
        """
    )
    return (classification_df,)


@app.cell
def _(classification_df):
    classification_df
    return


@app.cell
def _(branch_df, bus_df, classification_df, grid_plot, mo):
    # Topology diagram: generators colored by classified fuel type
    _G = grid_plot.build_graph(bus_df, branch_df)
    _fig_fuel = grid_plot.plot_base_topology(
        _G,
        title="After Classification: Generators by Fuel Type",
        bus_size=8,
        bus_color="#ccc",
    )
    # Build gen_df-like frame from classification for the marker function
    _gen_fuel_df = classification_df.rename(
        columns={"bus": "gen_bus", "pmax_mw": "pmax_mw", "fuel_category": "fuel_type"}
    )
    grid_plot.add_generator_markers(_fig_fuel, _gen_fuel_df, fuel_col="fuel_type")
    mo.ui.plotly(_fig_fuel)
    return


@app.cell
def _(mo):
    mo.md(r"""
    The same network, now enriched with fuel metadata: **blue** = hydro (bus 30),
    **red** = nuclear (buses 31-32, 35, 37-38), **charcoal** = coal (buses 33-34),
    **amber** = gas (buses 36, 39). Before cleanup, all generators were
    undifferentiated — the case file had no machine-readable fuel type, only
    comments. This classification is the foundation for everything that follows:
    technology-specific ramp rates, startup costs, and reserve eligibility.
    """)
    return


@app.cell
def _(Path, mo, pd):
    import json as _json

    _manifest_path = (
        Path(__file__).parent.parent / "data" / "timeseries" / "case39" / "cleanup_manifest.json"
    )
    _manifest = _json.loads(_manifest_path.read_text())

    # Aggregate rule_summary from the first (only) network in the manifest
    _network = _manifest["networks"][0]
    _rule_summary = pd.DataFrame(_network["rule_summary"])

    manifest_summary_df = _rule_summary.rename(
        columns={"rule": "Cleanup Rule", "modification_count": "Modifications"}
    )

    mo.md(
        """
        ### Cleanup Manifest Summary

        The manifest records every individual field modification made during
        cleanup. Below is the count of modifications grouped by rule type:
        """
    )
    return (manifest_summary_df,)


@app.cell
def _(manifest_summary_df):
    manifest_summary_df
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## The Missing Data Reveal

    The cleanup above fixed bias and added fuel labels, but the deeper problem
    is what the case file **never had in the first place**. A MATPOWER `.m` file
    is a single-instant photograph — it has topology and a converged operating
    point, but **zero temporal data**, no fuel metadata (until we added it), and
    critically, **no cost differentiation** between generators.
    """)
    return


@app.cell
def _(Path, mo, pd, re):
    # Extract gencost data to prove all generators have identical cost curves
    _case_path = Path(__file__).parent.parent / "data" / "networks" / "case39.m"
    _raw = _case_path.read_text()
    _gc_match = re.search(r"mpc\.gencost\s*=\s*\[([^\]]*)\]", _raw, re.DOTALL)
    assert _gc_match is not None, "Could not find mpc.gencost in case39.m"

    _gc_rows: list[list[float]] = []
    for _line in _gc_match.group(1).split(";"):
        _line = _line.strip()
        if "%" in _line:
            _line = _line[: _line.index("%")]
        _line = _line.strip()
        if not _line:
            continue
        _gc_rows.append([float(v) for v in _line.split()])

    gencost_df = pd.DataFrame(
        _gc_rows,
        columns=["model", "startup", "shutdown", "ncost", "c2", "c1", "c0"],
    )
    gencost_df.index.name = "gen_index"

    # Check if all cost curves are identical
    _unique_curves = gencost_df[["c2", "c1", "c0"]].drop_duplicates()
    _all_identical = len(_unique_curves) == 1

    if _all_identical:
        _c2, _c1, _c0 = _unique_curves.iloc[0]
        _cost_msg = (
            f"All **{len(gencost_df)} generators** have the **exact same** quadratic "
            f"cost curve: `{_c2}*P^2 + {_c1}*P + {_c0}`. "
        )
    else:
        _cost_msg = f"There are **{len(_unique_curves)}** distinct cost curves."

    mo.md(
        f"""
        ### Generator Cost Curves

        {_cost_msg}

        An optimizer asked to dispatch this system has **no economic basis** for
        choosing one generator over another — the 1040 MW hydro plant costs
        the same per MWh as a 250 MW gas turbine. This is the case file's most
        fundamental limitation for optimization.
        """
    )
    return (gencost_df,)


@app.cell
def _(gencost_df):
    gencost_df
    return


@app.cell
def _(mo, pd):
    # "What's missing for optimization" table
    missing_data_df = pd.DataFrame(
        [
            {
                "Data Element": "Ramp rates (MW/min)",
                "Status": "Missing",
                "Impact": "Cannot model generator flexibility",
            },
            {
                "Data Element": "Min up/down times (hours)",
                "Status": "Missing",
                "Impact": "Cannot enforce commitment logic",
            },
            {
                "Data Element": "Startup costs ($)",
                "Status": "Missing",
                "Impact": "No penalty for cycling generators",
            },
            {
                "Data Element": "Hourly load profiles",
                "Status": "Missing",
                "Impact": "Single instant, no temporal dimension",
            },
            {
                "Data Element": "Reserve requirements",
                "Status": "Missing",
                "Impact": "No ancillary service modeling",
            },
            {
                "Data Element": "Fuel types",
                "Status": "In comments only",
                "Impact": "No technology-specific parameters",
            },
            {
                "Data Element": "Cost differentiation",
                "Status": "None (all identical)",
                "Impact": "No economic dispatch signal",
            },
            {
                "Data Element": "Wind/solar profiles",
                "Status": "Missing",
                "Impact": "No renewable integration",
            },
        ]
    )

    mo.md(
        """
        ### What's Missing for SCUC/SCED

        The table below catalogues every data element needed for security-constrained
        unit commitment that is absent from the raw case file:
        """
    )
    return (missing_data_df,)


@app.cell
def _(missing_data_df):
    missing_data_df
    return


@app.cell
def _(mo):
    mo.md(r"""
    This is the real story of the raw data: **topology is complete, but the
    operating parameters are either absent or undifferentiated.** The remaining
    notebooks in this series will systematically fill each gap — assigning
    fuel-specific costs, adding temporal parameters, synthesizing load and
    renewable profiles, and defining storage and demand response resources.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## Before vs. After: Voltage Cleanup

    The cleanup normalized all bus voltages to 1.0 p.u. (flat start). The chart
    below compares the raw snapshot voltages against the cleaned values.
    """)
    return


@app.cell
def _(bus_vm_df, pd):
    # Build before/after voltage comparison.
    # Before: raw Vm from the solved snapshot (bus_vm_df).
    # After: all buses normalized to 1.0 p.u. (flat start).
    _vm_before = bus_vm_df.copy()
    _vm_before["stage"] = "Raw Snapshot"
    _vm_after = pd.DataFrame(
        {"bus_id": bus_vm_df["bus_id"], "vm_pu": 1.0, "stage": "After Cleanup"}
    )
    vm_compare_long = pd.concat([_vm_before, _vm_after], ignore_index=True)
    return (vm_compare_long,)


@app.cell
def _(alt, vm_compare_long):
    voltage_comparison_chart = (
        alt.Chart(
            vm_compare_long,
            title="Bus Voltage Magnitude: Raw Snapshot vs. After Cleanup",
        )
        .mark_circle(size=60)
        .encode(
            x=alt.X("bus_id:O", title="Bus ID", sort="ascending"),
            y=alt.Y(
                "vm_pu:Q",
                title="Vm (p.u.)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "stage:N",
                title="Stage",
                scale=alt.Scale(
                    domain=["Raw Snapshot", "After Cleanup"],
                    range=["#e45756", "#4c78a8"],
                ),
            ),
            tooltip=["bus_id:O", "stage:N", "vm_pu:Q"],
        )
        .properties(width=650, height=300)
    )
    voltage_comparison_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    **What changed:** The raw snapshot voltages range from ~0.98 to
    ~1.08 p.u. — the result of the converged power-flow solution where
    generator buses regulate voltage upward and load buses sag. After
    cleanup, every bus is reset to 1.0 p.u. (flat start), eliminating
    the warm-start bias that could trap an AC-OPF solver in a local
    optimum near the snapshot's operating point.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## Summary: From Snapshot to Optimization-Ready

    This notebook walked through the raw IEEE 39-bus MATPOWER case file
    and revealed two categories of issues:

    1. **Snapshot bias** — Solved bus voltages encode the snapshot's
       operating point. Keeping them biases AC-OPF toward a local optimum.
       The cleanup normalizes Vm/Va and zeros Pg/Qg for a neutral start.

    2. **Missing operational data** — The raw `.m` file lacks fuel-specific
       costs, ramp rates, startup costs, hourly load profiles, and reserve
       requirements. Without these, no unit commitment optimization is
       possible. The cleanup added fuel classification; the remaining
       gaps are filled in Notebooks 02-04.

    The cleanup pipeline zeroed Pg/Qg, normalized Vm/Va, set realistic
    Pmin values, and classified every generator by fuel type and RTS-GMLC
    technology class. The result is a **clean, classified network** —
    but one that still lacks the temporal dimension needed for optimization.

    **Next up — Notebook 02: Generator Calibration.** With the network
    cleaned, the next step is to assign temporal operational parameters
    (ramp rates, minimum up/down times, startup costs, heat rates) to
    each generator based on its RTS-GMLC class, and attach hourly load
    and renewable time-series profiles to build a complete 24-hour unit
    commitment input dataset.
    """)
    return


@app.cell
def _(branch_df, bus_df, classification_df, grid_plot, mo):
    # Final topology: the "blank canvas" — generators grayed out (Pg=0), flat voltages
    _G = grid_plot.build_graph(bus_df, branch_df)
    _fig_ready = grid_plot.plot_base_topology(
        _G,
        title="Clean Grid State: Ready for Optimization",
        bus_size=10,
        bus_color="#b0b0b0",
        branch_color="#ccc",
    )

    # Show generators as hollow/faded squares — dispatch is zero
    _gen_ready = classification_df.rename(
        columns={"bus": "gen_bus", "fuel_category": "fuel_type"}
    ).copy()
    import plotly.graph_objects as _go

    for _, _r in _gen_ready.iterrows():
        _bx, _by = grid_plot.BUS_POSITIONS[int(_r["gen_bus"])]
        _color = grid_plot.FUEL_COLORS.get(_r["fuel_type"], "#888")
        _fig_ready.add_trace(
            _go.Scatter(
                x=[_bx],
                y=[_by],
                mode="markers+text",
                marker=dict(
                    size=18,
                    color="white",
                    symbol="square",
                    line=dict(width=2.5, color=_color),
                ),
                text=["Pg=0"],
                textposition="bottom center",
                textfont=dict(size=7, color="#888"),
                hovertext=f"Gen @ Bus {int(_r['gen_bus'])}<br>{_r['fuel_type']}<br>Pmax={_r['pmax_mw']:.0f} MW<br>Pg=0 (awaiting optimizer)",
                hoverinfo="text",
                showlegend=False,
            )
        )

    mo.ui.plotly(_fig_ready)
    return


@app.cell
def _(mo):
    mo.md(r"""
    The grid is now a **blank canvas** — topology and constraints are set, but all
    decision variables (dispatch, commitment) are zeroed out. The hollow generator
    markers show that no unit is dispatched: `Pg = 0` everywhere, voltages are flat
    at 1.0 p.u., and the fuel classifications are assigned but idle. This is the
    starting point that an optimizer will fill in.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
