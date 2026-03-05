import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import re
    import sys
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd

    # Ensure the data package is importable (installed via uv as grc-data-augmentation)
    from scripts.reconcile_bus_gen import parse_matpower_case
    from scripts.tiny_cleanup_classify import clean_and_classify_case39

    return Path, alt, clean_and_classify_case39, mo, parse_matpower_case, pd, re, sys


@app.cell
def _(mo):
    mo.md(
        r"""
        # Raw Data Orientation: The IEEE 39-Bus System

        This notebook introduces the **raw data** that every power-system modeling tool
        in our evaluation consumes. By the end you will understand:

        1. What a **MATPOWER** case file contains and how it encodes a power network.
        2. What the **IEEE 39-bus "New England"** test system represents physically.
        3. The difference between a **power-flow snapshot** and a
           **unit commitment optimization** input.
        4. What **Optimal Power Flow (OPF)** means and why it matters.

        All six tools we evaluate (PyPSA, pandapower, GridCal, PowerModels.jl,
        PowerSimulations.jl, and MATPOWER/Octave) can ingest this same `.m` file format,
        making it the natural common starting point for comparison.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
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
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
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
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Power-Flow Snapshot vs. Unit Commitment

        The data in `case39.m` is a **power-flow snapshot**: a single instant in time
        where every bus voltage, generator output, and line flow is fully specified
        (or solvable). Think of it as a photograph of the grid at one moment.

        A power-flow snapshot tells you:

        - How much power each generator is producing **right now**
        - The voltage magnitude and angle at every bus
        - The real and reactive power flowing on every branch
        - Whether any equipment limits are violated

        **Unit commitment (UC)**, by contrast, is an optimization problem that spans
        **multiple time periods** (typically 24-168 hours). UC decides:

        - Which generators to turn on/off in each hour (the "commitment" decision)
        - How much power each committed generator should produce (the "dispatch" decision)
        - Subject to constraints like ramp rates, minimum up/down times, and fuel costs

        A single MATPOWER `.m` file does **not** contain the temporal data (hourly load
        profiles, wind/solar forecasts, ramp rates, startup costs) needed for UC. Our
        later tutorials will augment this snapshot with time-series data to build a
        full UC input dataset.

        ## What is Optimal Power Flow (OPF)?

        **Optimal Power Flow** sits between a simple power-flow solve and full unit
        commitment. OPF finds the **least-cost generator dispatch** for a **single time
        period** while respecting:

        - Generator capacity limits (Pmin/Pmax, Qmin/Qmax)
        - Transmission line thermal ratings
        - Bus voltage limits
        - Network power balance (Kirchhoff's laws)

        The `mpc.gencost` matrix in `case39.m` provides quadratic cost curves for each
        generator, making the file a complete OPF input. OPF answers "what is the cheapest
        way to serve this load?" without worrying about startup/shutdown dynamics across
        time.
        """
    )
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
    return bus_df, gen_df, load_bus_gen_data


@app.cell
def _(mo, bus_df, gen_df):
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
def _(mo):
    mo.md(r"""**Generator DataFrame:**""")
    return


@app.cell
def _(gen_df):
    gen_df
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
def _(mo, branch_df):
    mo.md(
        f"""
        ### Branch Data

        Extracted **{len(branch_df)} branches** (transmission lines and transformers)
        from `mpc.branch`. Each row specifies the from-bus, to-bus, series impedance
        (r + jx in per-unit), shunt susceptance (b), thermal ratings (MVA), and
        transformer tap ratio (nonzero ratio indicates a transformer).

        **Branch DataFrame** (first 10 rows):
        """
    )
    return


@app.cell
def _(branch_df):
    branch_df.head(10)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ---

        ## Raw Data Exploration

        The cells below visualize the **raw (pre-cleanup) data** parsed from
        `case39.m`. These charts reveal the structure of the IEEE 39-bus system
        and highlight important artifacts in the snapshot data that must be
        understood before any modeling work begins.
        """
    )
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
    mo.md(
        r"""
        **What to notice:** Generator capacity is heavily concentrated on a
        few buses. Bus 39 (the "equivalent generator" representing the
        external interconnection) dominates with 1,000 MW of Pmax. The
        remaining nine generators range from roughly 250 MW to 830 MW. This
        uneven distribution is typical of real transmission systems where a
        handful of large plants account for most of the installed capacity.
        """
    )
    return


@app.cell
def _(alt, gen_df):
    _melted = gen_df.melt(
        id_vars=["gen_bus"],
        value_vars=["pmin_mw", "pmax_mw"],
        var_name="limit",
        value_name="mw",
    )
    _melted["limit"] = _melted["limit"].map({"pmin_mw": "Pmin", "pmax_mw": "Pmax"})

    pmin_pmax_grouped_bar = (
        alt.Chart(_melted, title="Pmin vs Pmax per Generator")
        .mark_bar()
        .encode(
            x=alt.X("gen_bus:N", title="Generator Bus", sort="ascending"),
            y=alt.Y("mw:Q", title="MW"),
            color=alt.Color(
                "limit:N",
                title="Limit",
                scale=alt.Scale(
                    domain=["Pmin", "Pmax"],
                    range=["#e45756", "#4c78a8"],
                ),
            ),
            xOffset="limit:N",
            tooltip=["gen_bus:N", "limit:N", "mw:Q"],
        )
        .properties(width=600, height=350)
    )
    return (pmin_pmax_grouped_bar,)


@app.cell
def _(pmin_pmax_grouped_bar):
    pmin_pmax_grouped_bar
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        **What to notice — the Pmin artifact:** In this snapshot, Pmin values
        are **not** true engineering minimums. They mirror the **current
        dispatch** (Pg) rather than the generator's physical minimum stable
        output. MATPOWER case files store the solved operating point, so the
        Pmin column often reflects the last converged power-flow solution
        rather than a meaningful lower bound. Any optimization that treats
        these Pmin values as real constraints will be artificially constrained
        to the snapshot's dispatch point. Later tutorials will replace these
        with realistic minimum stable output levels.
        """
    )
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
    mo.md(
        r"""
        **What to notice:** The bus type distribution shows 29 PQ (load) buses,
        9 PV (generator) buses, and 1 reference (slack) bus — this matches
        the 10 generators (9 PV + 1 Ref). The voltage magnitudes are **not**
        all 1.0 p.u. because this is a **solved snapshot**: the values
        reflect the converged power-flow solution, not flat-start initial
        conditions. Generator buses tend to have voltages above 1.0 p.u.
        because they regulate voltage, while load buses sag slightly below.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Branch Summary

        The full 46-row branch table is displayed below. Key columns include
        the from/to bus IDs, series impedance (r, x in per-unit), shunt
        susceptance (b), thermal ratings (MVA), and transformer tap ratio
        (a nonzero `ratio` indicates a transformer rather than a line).
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

    system_summary_markdown = mo.md(
        f"""
        ## System Summary

        | Metric | Value |
        |--------|-------|
        | Buses | {_n_buses} |
        | Generators | {_n_gens} |
        | Branches | {_n_branches} |
        | Total Pmax | {_total_pmax:.0f} MW |
        | Total Load (Pd) | {_total_pd:.1f} MW |

        The system has **{_n_gens} generators** with a combined maximum
        capacity of **{_total_pmax:.0f} MW** serving **{_total_pd:.1f} MW**
        of load across **{_n_buses} buses** connected by
        **{_n_branches} branches**.
        """
    )
    return (system_summary_markdown,)


@app.cell
def _(system_summary_markdown):
    system_summary_markdown
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ---

        ## Snapshot Cleanup: Why Raw Data Can't Be Used Directly

        The `case39.m` file is a **converged power-flow snapshot** — every value
        reflects the solved operating point at a single instant. Several fields
        must be modified before the data can serve as input to an optimization
        (OPF or unit commitment). The cleanup rules below explain what changes
        are needed and why.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
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
        """
    )
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


if __name__ == "__main__":
    app.run()
