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


if __name__ == "__main__":
    app.run()
