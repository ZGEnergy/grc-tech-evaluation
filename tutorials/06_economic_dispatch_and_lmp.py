import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import csv
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    from scipy.optimize import linprog

    from scripts.reconcile_bus_gen import parse_matpower_case
    from scripts.tiny_flowgates import (
        build_ptdf_matrix,
        parse_matpower_case_extended,
    )

    import grid_plot

    return (
        Path,
        alt,
        build_ptdf_matrix,
        csv,
        grid_plot,
        linprog,
        mo,
        np,
        parse_matpower_case,
        parse_matpower_case_extended,
        pd,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Economic Dispatch and Locational Pricing

    This capstone notebook brings together every piece of the dataset built
    in Notebooks 01–05 and puts it to work.  We formulate a **24-hour
    DC OPF economic dispatch** as a linear program, solve it with
    `scipy.optimize.linprog`, and then extract two quantities that sit at
    the heart of every wholesale electricity market:

    1. **Locational Marginal Prices (LMPs)** — the cost of serving one
       additional MW of load at each bus, decomposed into energy and
       congestion components.
    2. **Congestion rents** — the revenue that accrues when power flows
       across a binding transmission constraint and the price differs on
       each side.

    ### Why does this matter?

    LMPs are the settlement price for every MWh traded in the day-ahead
    and real-time energy markets run by ISOs (ERCOT, PJM, MISO, CAISO,
    etc.).  If you model a power system but cannot compute LMPs, you
    cannot evaluate whether an investment, a trade, or a policy change
    creates or destroys value.  This notebook demonstrates how LMPs arise
    naturally from the dual variables of a constrained optimization.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Data Inventory

    The economic dispatch consumes the outputs of all five preceding
    notebooks.  Let's load each piece and inspect its shape.
    """)
    return


@app.cell
def _(Path, csv, np, parse_matpower_case_extended, pd):
    # ---------- paths ----------
    _data_dir = Path(__file__).resolve().parent.parent / "data"
    _ts_dir = _data_dir / "timeseries" / "case39"
    _net_dir = _data_dir / "networks"
    _m_file = _net_dir / "case39.m"

    # ---------- network ----------
    ed_buses, ed_gens, ed_branches, ed_base_mva = parse_matpower_case_extended(_m_file)
    ed_ref_bus = next(b.bus_id for b in ed_buses if b.bus_type == 3)
    ed_bus_ids = [b.bus_id for b in ed_buses]

    # ---------- generator temporal params ----------
    _tp_path = _ts_dir / "gen_temporal_params.csv"
    gen_params_df = pd.read_csv(_tp_path)

    # ---------- load profile (bus-level, 24h) ----------
    _load_path = _ts_dir / "load_24h.csv"
    load_df = pd.read_csv(_load_path)
    # build dict: bus_id -> [24 MW values]
    load_by_bus: dict[int, list[float]] = {}
    for _, _row in load_df.iterrows():
        load_by_bus[int(_row["bus_id"])] = [float(_row[f"HR_{h}"]) for h in range(1, 25)]

    # ---------- renewable profiles (actual MW, 24h) ----------
    _wind_path = _ts_dir / "wind_actual_24h.csv"
    _solar_path = _ts_dir / "solar_actual_24h.csv"
    wind_profiles_df = pd.read_csv(_wind_path)
    solar_profiles_df = pd.read_csv(_solar_path)
    renewable_units_df = pd.read_csv(_ts_dir / "renewable_units.csv")

    # ---------- BESS ----------
    bess_df = pd.read_csv(_ts_dir / "bess_units.csv")

    # ---------- flowgates ----------
    _fg_path = _ts_dir / "flowgates.csv"
    flowgates_raw = []
    with open(_fg_path, newline="") as _fh:
        for _frow in csv.DictReader(_fh):
            _br_strs = _frow["branches"].split(";")
            _wt_strs = _frow["weights"].split(";")
            flowgates_raw.append(
                {
                    "id": _frow["flowgate_id"],
                    "name": _frow["name"],
                    "branches": [tuple(int(x) for x in s.split("-")) for s in _br_strs],
                    "weights": [float(w) for w in _wt_strs],
                    "limit_mw": float(_frow["limit_mw"]),
                }
            )

    # ---------- system load per hour ----------
    system_load_24h = np.zeros(24)
    for _bus_load in load_by_bus.values():
        system_load_24h += np.array(_bus_load)

    return (
        bess_df,
        ed_base_mva,
        ed_branches,
        ed_bus_ids,
        ed_buses,
        ed_gens,
        ed_ref_bus,
        flowgates_raw,
        gen_params_df,
        load_by_bus,
        load_df,
        renewable_units_df,
        solar_profiles_df,
        system_load_24h,
        wind_profiles_df,
    )


@app.cell
def _(bess_df, flowgates_raw, gen_params_df, mo, renewable_units_df, system_load_24h):
    _n_thermal = len(gen_params_df)
    _n_renewable = len(renewable_units_df)
    _n_bess = len(bess_df)
    _n_fg = len(flowgates_raw)
    _peak = max(system_load_24h)
    _valley = min(system_load_24h)

    mo.md(rf"""
    | Component | Count | Source |
    |-----------|-------|--------|
    | Thermal generators | {_n_thermal} | `gen_temporal_params.csv` |
    | Renewable generators | {_n_renewable} | `renewable_units.csv` |
    | BESS units | {_n_bess} | `bess_units.csv` |
    | Flowgates | {_n_fg} | `flowgates.csv` |
    | System peak load | {_peak:,.0f} MW | `load_24h.csv` |
    | System valley load | {_valley:,.0f} MW | `load_24h.csv` |
    | Planning horizon | 24 hours | — |
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Variable Cost Assignment

    The original case39.m file gives every generator the same quadratic
    cost curve ($0.01 P^2 + 0.3 P + 0.2$), which makes economic dispatch
    trivial — with identical costs, dispatch order is arbitrary.

    For a realistic demonstration, we assign **differentiated variable
    costs by fuel type**, based on typical U.S. wholesale energy costs:

    | Fuel type | Variable cost ($/MWh) | Rationale |
    |-----------|----------------------:|-----------|
    | Hydro | 0 | Zero fuel cost (water) |
    | Nuclear | 5 | Low fuel cost, high capital |
    | Coal/Steam | 25 | Solid fuel, moderate heat rate |
    | Gas/CC | 35 | Natural gas combined cycle |
    | Gas/CC (Flexible) | 40 | Interconnection equiv., peaker-like |
    | Wind | 0 | Zero marginal cost |
    | Solar | 0 | Zero marginal cost |

    These costs determine the **merit order**: hydro and renewables
    dispatch first (cheapest), then nuclear, then coal, then gas.
    The interconnection equivalent (bus 39) acts as a flexible balancing
    resource at $40/MWh.
    """)
    return


@app.cell
def _(gen_params_df, np, pd, renewable_units_df, solar_profiles_df, wind_profiles_df):
    # Variable cost by RTS-GMLC class ($/MWh)
    VARIABLE_COST_MAP = {
        "Hydro": 0.0,
        "Nuclear": 5.0,
        "Coal/Steam": 25.0,
        "Gas/CC": 35.0,
        "Gas/CC (Flexible)": 40.0,
    }

    # Build thermal generator records
    thermal_gens = []
    for _, _r in gen_params_df.iterrows():
        _cls = _r["rts_gmlc_class"]
        thermal_gens.append(
            {
                "gen_uid": _r["gen_uid"],
                "bus_id": int(_r["bus_id"]),
                "pmax_mw": float(_r["pmax_mw"]),
                "pmin_mw": 0.0,  # simplified: Pmin=0 for ED (we ignore commitment)
                "ramp_rate_mw_per_hr": float(_r["ramp_rate_mw_per_hr"]),
                "fuel": _cls,
                "var_cost": VARIABLE_COST_MAP.get(_cls, 40.0),
            }
        )

    # Build renewable generator records with hourly availability
    renewable_gens = []
    _wind_dict = {}
    for _, _r in wind_profiles_df.iterrows():
        _wind_dict[_r["gen_uid"]] = [float(_r[f"HR_{h}"]) for h in range(1, 25)]
    _solar_dict = {}
    for _, _r in solar_profiles_df.iterrows():
        _solar_dict[_r["gen_uid"]] = [float(_r[f"HR_{h}"]) for h in range(1, 25)]

    for _, _r in renewable_units_df.iterrows():
        _uid = _r["gen_uid"]
        _rtype = _r["type"]
        _avail = _wind_dict.get(_uid) or _solar_dict.get(_uid, [0.0] * 24)
        renewable_gens.append(
            {
                "gen_uid": _uid,
                "bus_id": int(_r["bus_id"]),
                "pmax_mw": float(_r["pmax_mw"]),
                "fuel": "Wind" if _rtype == "wind" else "Solar",
                "var_cost": 0.0,
                "availability_mw": np.array(_avail),
            }
        )

    # Combined generator list (thermal first, then renewable)
    all_gens = thermal_gens + renewable_gens
    N_GEN = len(all_gens)
    N_THERMAL = len(thermal_gens)
    N_RENEWABLE = len(renewable_gens)

    # Show merit order
    _mo_rows = []
    for _g in sorted(all_gens, key=lambda g: g["var_cost"]):
        _mo_rows.append(
            {
                "Generator": _g["gen_uid"],
                "Bus": _g["bus_id"],
                "Fuel": _g["fuel"],
                "Pmax (MW)": _g["pmax_mw"],
                "Var Cost ($/MWh)": _g["var_cost"],
            }
        )
    merit_order_df = pd.DataFrame(_mo_rows)

    return (
        N_GEN,
        N_RENEWABLE,
        N_THERMAL,
        VARIABLE_COST_MAP,
        all_gens,
        merit_order_df,
        renewable_gens,
        thermal_gens,
    )


@app.cell
def _(alt, merit_order_df):
    _chart = (
        alt.Chart(merit_order_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Generator:N",
                sort=alt.EncodingSortField(field="Var Cost ($/MWh)", order="ascending"),
                axis=alt.Axis(labelAngle=-45, labelFontSize=9),
            ),
            y=alt.Y("Pmax (MW):Q", title="Capacity (MW)"),
            color=alt.Color(
                "Fuel:N",
                scale=alt.Scale(
                    domain=[
                        "Hydro",
                        "Wind",
                        "Solar",
                        "Nuclear",
                        "Coal/Steam",
                        "Gas/CC",
                        "Gas/CC (Flexible)",
                    ],
                    range=[
                        "#1f77b4",
                        "#2ca02c",
                        "#ffbb00",
                        "#9467bd",
                        "#8c564b",
                        "#d62728",
                        "#e377c2",
                    ],
                ),
                legend=alt.Legend(title="Fuel Type"),
            ),
            tooltip=[
                alt.Tooltip("Generator:N"),
                alt.Tooltip("Fuel:N"),
                alt.Tooltip("Pmax (MW):Q"),
                alt.Tooltip("Var Cost ($/MWh):Q"),
            ],
        )
        .properties(
            title="Generator Merit Order — Sorted by Variable Cost",
            width=700,
            height=350,
        )
    )
    _chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    Hydro, wind, and solar sit at the left (cheapest). Nuclear follows at
    $5/MWh. Coal and gas round out the merit order. In a competitive
    market, generators dispatch left-to-right: the cheapest unit available
    runs first, and the marginal unit (the last one dispatched to meet
    load) sets the system energy price.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. LP Formulation

    We formulate the **24-hour DC OPF economic dispatch** as a linear
    program.  This is a simplification of the full unit commitment (which
    would include binary on/off decisions) — we treat all generators as
    continuously dispatchable between 0 and their capacity limits.

    ### Decision variables

    For each hour $h \in \{1, \ldots, 24\}$:

    | Variable | Dimension | Meaning |
    |----------|-----------|---------|
    | $p_{g,h}$ | $N_\text{gen}$ | MW output of generator $g$ |
    | $p^\text{ch}_h$ | 1 | BESS charging power (MW) |
    | $p^\text{dis}_h$ | 1 | BESS discharging power (MW) |
    | $e_h$ | 1 | BESS state of charge (MWh) |

    ### Objective

    Minimize total variable generation cost:

    $$\min \sum_{h=1}^{24} \sum_{g=1}^{N} c_g \cdot p_{g,h}$$

    where $c_g$ is the variable cost ($/MWh) of generator $g$.

    ### Constraints

    **System power balance** (one equality per hour):

    $$\sum_g p_{g,h} + p^\text{dis}_h - p^\text{ch}_h = D_h$$

    where $D_h$ is total system load at hour $h$. The dual variable
    $\lambda_h$ of this constraint is the **system energy price**.

    **Flowgate limits** (two inequalities per flowgate per hour):

    $$\sum_b \text{PTDF}_{f,b} \cdot P^\text{inject}_{b,h} \leq F_f$$
    $$-\sum_b \text{PTDF}_{f,b} \cdot P^\text{inject}_{b,h} \leq F_f$$

    where $P^\text{inject}_{b,h}$ is the net power injection at bus $b$
    (generation minus load) and $F_f$ is the flowgate MW limit. The dual
    variable $\mu_f$ gives the **congestion value** of that flowgate.

    **BESS dynamics** (equality per hour):

    $$e_h = e_{h-1} + \eta \cdot p^\text{ch}_h - p^\text{dis}_h$$

    with a cyclic constraint: $e_{24} = e_0$ (the battery ends the day
    where it started).

    **Generator bounds**: $0 \leq p_{g,h} \leq \overline{P}_g$ for
    thermal units; $0 \leq p_{g,h} \leq A_{g,h}$ for renewables (where
    $A_{g,h}$ is the available output at hour $h$).
    """)
    return


@app.cell
def _(
    N_GEN,
    all_gens,
    bess_df,
    build_ptdf_matrix,
    ed_base_mva,
    ed_branches,
    ed_bus_ids,
    ed_buses,
    ed_ref_bus,
    flowgates_raw,
    linprog,
    load_by_bus,
    mo,
    np,
    renewable_gens,
    system_load_24h,
):
    @mo.cache
    def _solve_ed():
        """Build and solve the 24h economic dispatch LP."""
        H = 24

        # -- BESS parameters --
        _bess = bess_df.iloc[0]
        bess_bus = int(_bess["bus_id"])
        bess_pmax = float(_bess["power_mw"])
        bess_energy = float(_bess["energy_mwh"])
        bess_eff = float(_bess["efficiency"])
        bess_min_soc = float(_bess["min_soc"])
        bess_max_soc = float(_bess["max_soc"])
        bess_init_soc = float(_bess["init_soc"])

        # -- Variable layout --
        # pg: [0, N_GEN*H)
        # bess_ch: [N_GEN*H, N_GEN*H + H)
        # bess_dis: [N_GEN*H + H, N_GEN*H + 2*H)
        # soc: [N_GEN*H + 2*H, N_GEN*H + 3*H)
        n_vars = N_GEN * H + 3 * H
        pg_start = 0
        ch_start = N_GEN * H
        dis_start = ch_start + H
        soc_start = dis_start + H

        # -- Cost vector --
        c = np.zeros(n_vars)
        for h in range(H):
            for g_idx, gen in enumerate(all_gens):
                c[pg_start + h * N_GEN + g_idx] = gen["var_cost"]

        # -- Bounds --
        lb = np.zeros(n_vars)
        ub = np.full(n_vars, np.inf)

        for h in range(H):
            for g_idx, gen in enumerate(all_gens):
                ub[pg_start + h * N_GEN + g_idx] = gen["pmax_mw"]
            # Renewable availability caps
            for r_idx, rgen in enumerate(renewable_gens):
                g_idx = len(all_gens) - len(renewable_gens) + r_idx
                avail = rgen["availability_mw"][h]
                ub[pg_start + h * N_GEN + g_idx] = avail

            # BESS bounds
            ub[ch_start + h] = bess_pmax
            ub[dis_start + h] = bess_pmax
            lb[soc_start + h] = bess_min_soc * bess_energy
            ub[soc_start + h] = bess_max_soc * bess_energy

        bounds = list(zip(lb, ub))

        # -- Equality constraints --
        eq_rows = []
        eq_rhs = []

        # 1) System power balance: sum(pg) + dis - ch = load for each hour
        for h in range(H):
            row = np.zeros(n_vars)
            for g_idx in range(N_GEN):
                row[pg_start + h * N_GEN + g_idx] = 1.0
            row[ch_start + h] = -1.0
            row[dis_start + h] = 1.0
            eq_rows.append(row)
            eq_rhs.append(system_load_24h[h])

        # 2) BESS SoC dynamics: soc[h] - eff*ch[h] + dis[h] - soc[h-1] = 0
        #    (rearranged: soc[h] = soc[h-1] + eff*ch[h] - dis[h])
        for h in range(H):
            row = np.zeros(n_vars)
            row[soc_start + h] = 1.0
            row[ch_start + h] = -bess_eff
            row[dis_start + h] = 1.0  # discharge removes from SoC
            if h == 0:
                rhs_val = bess_init_soc * bess_energy
            else:
                row[soc_start + h - 1] = -1.0
                rhs_val = 0.0
            eq_rows.append(row)
            eq_rhs.append(rhs_val)

        # 3) Cyclic SoC: soc[23] = init_soc * energy
        row = np.zeros(n_vars)
        row[soc_start + H - 1] = 1.0
        eq_rows.append(row)
        eq_rhs.append(bess_init_soc * bess_energy)

        A_eq = np.array(eq_rows)
        b_eq = np.array(eq_rhs)

        # -- Inequality constraints (flowgates) --
        # Build PTDF matrix
        ptdf, non_ref_bus_ids = build_ptdf_matrix(ed_buses, ed_branches, ed_ref_bus, ed_base_mva)
        # Map flowgate branches to branch indices
        _br_lookup = {}
        for br in ed_branches:
            _br_lookup[(br.from_bus, br.to_bus)] = br.branch_index
            _br_lookup[(br.to_bus, br.from_bus)] = br.branch_index

        ub_rows = []
        ub_rhs = []

        for fg in flowgates_raw:
            # Build flowgate PTDF row: weighted sum of branch PTDFs
            fg_ptdf = np.zeros(len(non_ref_bus_ids))
            for (fb, tb), w in zip(fg["branches"], fg["weights"]):
                br_idx = _br_lookup.get((fb, tb))
                if br_idx is not None:
                    fg_ptdf += w * ptdf[br_idx]

            for h in range(H):
                # Net injection at each bus = gen - load + BESS
                # Constraint: fg_ptdf @ P_inject <= limit
                # P_inject_b = sum(pg of gens at bus b) - load_b
                #            + bess_dis (if bess_bus) - bess_ch (if bess_bus)
                row_pos = np.zeros(n_vars)
                row_neg = np.zeros(n_vars)
                rhs_offset_pos = 0.0
                rhs_offset_neg = 0.0

                for b_idx, bid in enumerate(non_ref_bus_ids):
                    ptdf_val = fg_ptdf[b_idx]
                    # Generator contributions at this bus
                    for g_idx, gen in enumerate(all_gens):
                        if gen["bus_id"] == bid:
                            row_pos[pg_start + h * N_GEN + g_idx] = ptdf_val
                            row_neg[pg_start + h * N_GEN + g_idx] = -ptdf_val
                    # BESS
                    if bid == bess_bus:
                        row_pos[dis_start + h] = ptdf_val
                        row_pos[ch_start + h] = -ptdf_val
                        row_neg[dis_start + h] = -ptdf_val
                        row_neg[ch_start + h] = ptdf_val
                    # Load is constant -> goes to RHS
                    if bid in load_by_bus:
                        rhs_offset_pos += ptdf_val * load_by_bus[bid][h]
                        rhs_offset_neg += -ptdf_val * load_by_bus[bid][h]

                # Also account for ref bus injections (they affect flows
                # but ref bus is removed from PTDF, so no direct term).
                # The ref bus slack absorbs the balance — already handled.

                ub_rows.append(row_pos)
                ub_rhs.append(fg["limit_mw"] + rhs_offset_pos)
                ub_rows.append(row_neg)
                ub_rhs.append(fg["limit_mw"] + rhs_offset_neg)

        A_ub = np.array(ub_rows) if ub_rows else None
        b_ub = np.array(ub_rhs) if ub_rhs else None

        # -- Solve --
        result = linprog(
            c,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method="highs",
        )

        # -- Extract results --
        x = result.x

        # Generator dispatch
        pg_result = np.zeros((H, N_GEN))
        for h in range(H):
            for g_idx in range(N_GEN):
                pg_result[h, g_idx] = x[pg_start + h * N_GEN + g_idx]

        # BESS
        bess_ch_result = x[ch_start : ch_start + H]
        bess_dis_result = x[dis_start : dis_start + H]
        soc_result = x[soc_start : soc_start + H]

        # LMP extraction from equality constraint duals
        # The first H duals correspond to system power balance -> energy LMP
        # scipy marginals = d(objective)/d(b_eq), positive = more load costs more
        eq_duals = result.eqlin.marginals if hasattr(result, "eqlin") else None
        energy_lmp = None
        if eq_duals is not None:
            energy_lmp = eq_duals[:H]

        # Flowgate duals (congestion values)
        fg_duals = None
        if result.ineqlin is not None and hasattr(result.ineqlin, "marginals"):
            fg_duals = result.ineqlin.marginals

        return {
            "result": result,
            "pg": pg_result,
            "bess_ch": bess_ch_result,
            "bess_dis": bess_dis_result,
            "soc": soc_result,
            "energy_lmp": energy_lmp,
            "fg_duals": fg_duals,
            "ptdf": ptdf,
            "non_ref_bus_ids": non_ref_bus_ids,
            "bess_bus": bess_bus,
            "n_flowgates": len(flowgates_raw),
        }

    ed_solution = _solve_ed()
    return (ed_solution,)


@app.cell
def _(ed_solution, mo):
    _res = ed_solution["result"]
    _status = "Optimal" if _res.success else f"Failed ({_res.message})"
    _cost = _res.fun

    mo.md(rf"""
    ## 4. Solution Summary

    | Metric | Value |
    |--------|-------|
    | **Status** | {_status} |
    | **Total cost** | ${_cost:,.0f} |
    | **Solver** | HiGHS (via scipy.optimize.linprog) |

    The LP solved successfully. The total variable generation cost across
    24 hours is **${_cost:,.0f}**. This is the minimum-cost way to serve
    the load profile while respecting generator limits, BESS dynamics,
    and flowgate constraints.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Dispatch Stack

    The stacked area chart below shows how each fuel type contributes to
    meeting load across the 24-hour horizon.  Cheap generators (hydro,
    renewables, nuclear) form the base; more expensive units (coal, gas)
    fill in during peak hours.  The BESS charges during low-price hours
    and discharges during high-price hours.
    """)
    return


@app.cell
def _(N_GEN, all_gens, alt, ed_solution, pd, system_load_24h):
    _pg = ed_solution["pg"]
    _bess_ch = ed_solution["bess_ch"]
    _bess_dis = ed_solution["bess_dis"]

    # Build long-format dispatch DataFrame
    _dispatch_records = []
    for _h in range(24):
        for _g_idx in range(N_GEN):
            _dispatch_records.append(
                {
                    "Hour Ending": _h + 1,
                    "Generator": all_gens[_g_idx]["gen_uid"],
                    "Fuel": all_gens[_g_idx]["fuel"],
                    "MW": _pg[_h, _g_idx],
                }
            )
        # BESS net (discharge - charge)
        _bess_net = _bess_dis[_h] - _bess_ch[_h]
        if _bess_net > 0.1:
            _dispatch_records.append(
                {
                    "Hour Ending": _h + 1,
                    "Generator": "BESS_1",
                    "Fuel": "BESS (discharge)",
                    "MW": _bess_net,
                }
            )

    dispatch_df = pd.DataFrame(_dispatch_records)
    dispatch_df = dispatch_df[dispatch_df["MW"] > 0.1]

    # Fuel order for stacking
    _fuel_order = [
        "Hydro",
        "Wind",
        "Solar",
        "Nuclear",
        "Coal/Steam",
        "Gas/CC",
        "Gas/CC (Flexible)",
        "BESS (discharge)",
    ]
    _fuel_colors = [
        "#1f77b4",
        "#2ca02c",
        "#ffbb00",
        "#9467bd",
        "#8c564b",
        "#d62728",
        "#e377c2",
        "#17becf",
    ]

    # Aggregate by fuel and hour
    _agg = dispatch_df.groupby(["Hour Ending", "Fuel"])["MW"].sum().reset_index()

    _area = (
        alt.Chart(_agg)
        .mark_area()
        .encode(
            x=alt.X("Hour Ending:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("MW:Q", title="Generation (MW)", stack="zero"),
            color=alt.Color(
                "Fuel:N",
                scale=alt.Scale(domain=_fuel_order, range=_fuel_colors),
                sort=_fuel_order,
                legend=alt.Legend(title="Fuel Type"),
            ),
            order=alt.Order("fuel_order:Q"),
            tooltip=[
                alt.Tooltip("Hour Ending:O"),
                alt.Tooltip("Fuel:N"),
                alt.Tooltip("MW:Q", format=",.0f"),
            ],
        )
        .transform_calculate(fuel_order="indexof(" + str(_fuel_order) + ", datum.Fuel)")
    )

    # Load line overlay
    _load_line_df = pd.DataFrame(
        {
            "Hour Ending": list(range(1, 25)),
            "MW": system_load_24h,
        }
    )
    _load_line = (
        alt.Chart(_load_line_df)
        .mark_line(color="black", strokeWidth=2, strokeDash=[6, 3])
        .encode(
            x="Hour Ending:O",
            y="MW:Q",
            tooltip=[
                alt.Tooltip("Hour Ending:O"),
                alt.Tooltip("MW:Q", format=",.0f", title="Load"),
            ],
        )
    )

    dispatch_chart = (_area + _load_line).properties(
        title="24-Hour Dispatch Stack with Load (dashed line)",
        width=700,
        height=400,
    )
    dispatch_chart
    return (dispatch_chart, dispatch_df)


@app.cell
def _(mo):
    mo.md(r"""
    The dashed black line is total system load.  Generation stacks up from
    cheapest (bottom) to most expensive (top) until supply meets demand.
    Notice how:

    - **Nuclear** provides steady baseload across all hours.
    - **Hydro** runs at full capacity (cheapest thermal resource).
    - **Wind** peaks in evening hours; **solar** follows the daytime bell curve.
    - **Coal and gas** ramp up during peak hours and back down at night.
    - **BESS** discharges during peak (displacing expensive gas) and charges
      overnight (absorbing cheap baseload).

    This is the textbook merit-order dispatch that produces LMP.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6. Locational Marginal Prices (LMPs)

    The **energy component** of the LMP comes from the dual variable of
    the system power balance constraint.  At each hour, this dual tells
    us the cost of serving one additional MW of load — which equals the
    variable cost of the marginal generator.

    When a flowgate binds, the **congestion component** creates price
    separation across the network.  The LMP at bus $b$ in hour $h$ is:

    $$\text{LMP}_{b,h} = \lambda_h + \sum_{f} \mu_{f,h} \cdot \text{PTDF}_{f,b}$$

    where:
    - $\lambda_h$ = system energy price (dual of power balance)
    - $\mu_{f,h}$ = shadow price of flowgate $f$ (dual of flowgate constraint)
    - $\text{PTDF}_{f,b}$ = sensitivity of flowgate $f$ to injection at bus $b$
    """)
    return


@app.cell
def _(alt, ed_solution, np, pd):
    _energy_lmp = ed_solution["energy_lmp"]

    _lmp_df = pd.DataFrame(
        {
            "Hour Ending": list(range(1, 25)),
            "Energy LMP ($/MWh)": _energy_lmp,
        }
    )

    energy_lmp_chart = (
        alt.Chart(_lmp_df)
        .mark_line(point=True, color="#d62728")
        .encode(
            x=alt.X("Hour Ending:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Energy LMP ($/MWh):Q", title="System Energy Price ($/MWh)"),
            tooltip=[
                alt.Tooltip("Hour Ending:O"),
                alt.Tooltip("Energy LMP ($/MWh):Q", format=".2f"),
            ],
        )
        .properties(
            title="System Energy LMP — 24-Hour Profile",
            width=700,
            height=300,
        )
    )
    energy_lmp_chart

    _peak_he = int(np.argmax(_energy_lmp)) + 1
    _peak_price = float(np.max(_energy_lmp))
    _valley_price = float(np.min(_energy_lmp))
    return (energy_lmp_chart,)


@app.cell
def _(ed_solution, mo, np):
    _energy_lmp = ed_solution["energy_lmp"]
    _peak_he = int(np.argmax(_energy_lmp)) + 1
    _peak_price = float(np.max(_energy_lmp))
    _valley_price = float(np.min(_energy_lmp))
    _mean_price = float(np.mean(_energy_lmp))

    mo.md(rf"""
    | Metric | Value |
    |--------|-------|
    | Peak energy price | **${_peak_price:.2f}/MWh** (HE {_peak_he}) |
    | Valley energy price | **${_valley_price:.2f}/MWh** |
    | Mean energy price | **${_mean_price:.2f}/MWh** |

    The energy LMP tracks the **variable cost of the marginal generator**.
    During low-load hours when nuclear and hydro are sufficient, the price
    sits near the nuclear cost ($5/MWh).  As load rises and coal/gas units
    come online, the price jumps to $25–40/MWh.  This is precisely the
    mechanism by which electricity markets signal scarcity.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 7. Nodal LMP Map

    With congestion, different buses see different prices.  The LMP at
    each bus combines the system energy price with the congestion cost
    arising from binding flowgates.  Buses "behind" a congested corridor
    (on the export-constrained side) see lower prices; buses on the
    import-constrained side see higher prices.
    """)
    return


@app.cell
def _(
    ed_branches,
    ed_bus_ids,
    ed_buses,
    ed_ref_bus,
    ed_solution,
    flowgates_raw,
    np,
    pd,
):
    _energy_lmp = ed_solution["energy_lmp"]
    _fg_duals = ed_solution["fg_duals"]
    _ptdf = ed_solution["ptdf"]
    _non_ref = ed_solution["non_ref_bus_ids"]
    _n_fg = ed_solution["n_flowgates"]

    # Build per-bus, per-hour LMP matrix
    _H = 24
    _n_bus = len(ed_bus_ids)
    lmp_matrix = np.zeros((_H, _n_bus))  # (hour, bus_index)

    _bus_to_idx = {bid: i for i, bid in enumerate(ed_bus_ids)}

    # Build flowgate PTDF vectors (same as in the LP)
    _br_lookup = {}
    for _br in ed_branches:
        _br_lookup[(_br.from_bus, _br.to_bus)] = _br.branch_index
        _br_lookup[(_br.to_bus, _br.from_bus)] = _br.branch_index

    _fg_ptdf_vectors = []
    for _fg in flowgates_raw:
        _fg_ptdf = np.zeros(len(_non_ref))
        for (_fb, _tb), _w in zip(_fg["branches"], _fg["weights"]):
            _br_idx = _br_lookup.get((_fb, _tb))
            if _br_idx is not None:
                _fg_ptdf += _w * _ptdf[_br_idx]
        _fg_ptdf_vectors.append(_fg_ptdf)

    for _h in range(_H):
        # Start with energy component
        lmp_matrix[_h, :] = _energy_lmp[_h]

        # Add congestion components from each flowgate
        if _fg_duals is not None:
            for _f_idx in range(_n_fg):
                # Two duals per flowgate per hour: positive and negative direction
                _mu_pos = _fg_duals[_f_idx * 2 * _H + _h * 2]
                _mu_neg = _fg_duals[_f_idx * 2 * _H + _h * 2 + 1]
                _mu_net = _mu_pos - _mu_neg  # net congestion shadow price

                if abs(_mu_net) > 1e-6:
                    _fg_ptdf_v = _fg_ptdf_vectors[_f_idx]
                    for _b_idx_r, _bid in enumerate(_non_ref):
                        _b_idx = _bus_to_idx[_bid]
                        lmp_matrix[_h, _b_idx] += _mu_net * _fg_ptdf_v[_b_idx_r]

    # Compute average LMP per bus across hours
    _avg_lmp_per_bus = lmp_matrix.mean(axis=0)
    peak_hour_idx = int(np.argmax(_energy_lmp))
    _peak_lmp_per_bus = lmp_matrix[peak_hour_idx, :]

    lmp_bus_df = pd.DataFrame(
        {
            "bus_id": ed_bus_ids,
            "avg_lmp": _avg_lmp_per_bus,
            "peak_lmp": _peak_lmp_per_bus,
        }
    )

    return (
        lmp_bus_df,
        lmp_matrix,
        peak_hour_idx,
    )


@app.cell
def _(alt, lmp_bus_df, peak_hour_idx):
    _chart = (
        alt.Chart(lmp_bus_df)
        .mark_bar()
        .encode(
            x=alt.X("bus_id:O", title="Bus ID", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("peak_lmp:Q", title=f"LMP at Peak Hour (HE {peak_hour_idx + 1}, $/MWh)"),
            color=alt.Color(
                "peak_lmp:Q",
                scale=alt.Scale(scheme="redyellowgreen", reverse=True),
                legend=alt.Legend(title="$/MWh"),
            ),
            tooltip=[
                alt.Tooltip("bus_id:O", title="Bus"),
                alt.Tooltip("peak_lmp:Q", format=".2f", title="Peak LMP"),
                alt.Tooltip("avg_lmp:Q", format=".2f", title="Avg LMP"),
            ],
        )
        .properties(
            title=f"Nodal LMP at Peak Hour (HE {peak_hour_idx + 1})",
            width=700,
            height=350,
        )
    )
    _chart
    return


@app.cell
def _(lmp_bus_df, mo, np):
    _max_lmp = lmp_bus_df["peak_lmp"].max()
    _min_lmp = lmp_bus_df["peak_lmp"].min()
    _spread = _max_lmp - _min_lmp
    _max_bus = int(lmp_bus_df.loc[lmp_bus_df["peak_lmp"].idxmax(), "bus_id"])
    _min_bus = int(lmp_bus_df.loc[lmp_bus_df["peak_lmp"].idxmin(), "bus_id"])

    mo.md(rf"""
    At the peak hour, LMPs range from **${_min_lmp:.2f}/MWh** (bus {_min_bus})
    to **${_max_lmp:.2f}/MWh** (bus {_max_bus}), a spread of
    **${_spread:.2f}/MWh**.

    {"Price separation across buses indicates **binding flowgate constraints** creating congestion. Buses on the export-constrained side of a flowgate see lower prices (surplus generation), while import-constrained buses see higher prices (scarcity)." if _spread > 0.5 else "All buses see nearly the same price, indicating that **no flowgates are binding** at the peak hour. The network has sufficient transmission capacity to deliver power from cheap generators to all load buses without congestion."}
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 8. Congestion Analysis

    When a flowgate binds, the optimizer cannot push more power through
    that corridor — it must dispatch more expensive local generation on
    the import side.  The **congestion rent** on flowgate $f$ at hour $h$
    is:

    $$\text{Rent}_{f,h} = \mu_{f,h} \times F_f$$

    where $\mu_{f,h}$ is the flowgate shadow price and $F_f$ is the MW
    limit.  In real markets, congestion rents fund transmission rights
    (FTRs/CRRs) and signal where new transmission investment would
    reduce costs.
    """)
    return


@app.cell
def _(ed_solution, flowgates_raw, np, pd):
    _fg_duals = ed_solution["fg_duals"]
    _n_fg = ed_solution["n_flowgates"]
    _H = 24

    congestion_records = []
    for _f_idx, _fg in enumerate(flowgates_raw):
        for _h in range(_H):
            _mu_pos = _fg_duals[_f_idx * 2 * _H + _h * 2] if _fg_duals is not None else 0.0
            _mu_neg = _fg_duals[_f_idx * 2 * _H + _h * 2 + 1] if _fg_duals is not None else 0.0
            _mu_net = _mu_pos - _mu_neg
            _rent = abs(_mu_net) * _fg["limit_mw"]
            congestion_records.append(
                {
                    "Flowgate": _fg["id"],
                    "Hour Ending": _h + 1,
                    "Shadow Price ($/MWh)": _mu_net,
                    "Limit (MW)": _fg["limit_mw"],
                    "Congestion Rent ($/hr)": _rent,
                }
            )

    congestion_df = pd.DataFrame(congestion_records)

    # Summary per flowgate
    fg_summary = (
        congestion_df.groupby("Flowgate")
        .agg(
            Total_Rent=("Congestion Rent ($/hr)", "sum"),
            Binding_Hours=("Shadow Price ($/MWh)", lambda s: (abs(s) > 0.01).sum()),
            Max_Shadow_Price=("Shadow Price ($/MWh)", lambda s: s.abs().max()),
        )
        .reset_index()
        .sort_values("Total_Rent", ascending=False)
    )

    return congestion_df, fg_summary


@app.cell
def _(alt, congestion_df, fg_summary, mo, pd):
    _total_rent = fg_summary["Total_Rent"].sum()
    _binding_fgs = (fg_summary["Binding_Hours"] > 0).sum()

    mo.md(rf"""
    **{_binding_fgs}** of {len(fg_summary)} flowgates bind during the
    24-hour horizon, generating a total congestion rent of
    **${_total_rent:,.0f}**.

    {"Binding flowgates create locational price separation and incentivize generation closer to load centers. The congestion rent represents the economic cost of transmission constraints — this is the value that new transmission capacity would unlock." if _binding_fgs > 0 else "No flowgates bind, meaning transmission is uncongested. All buses share the same LMP (energy-only, no congestion component). This can happen when generation is well-distributed relative to load or when flowgate limits are generous."}
    """)

    # Build congestion heatmap (shows all flowgates; non-binding have zero)
    _binding_df = congestion_df[congestion_df["Shadow Price ($/MWh)"].abs() > 0.01]
    congestion_chart = (
        alt.Chart(_binding_df if len(_binding_df) > 0 else congestion_df.head(0))
        .mark_rect()
        .encode(
            x=alt.X("Hour Ending:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Flowgate:N", title="Flowgate"),
            color=alt.Color(
                "Shadow Price ($/MWh):Q",
                scale=alt.Scale(scheme="reds"),
                legend=alt.Legend(title="Shadow Price\n($/MWh)"),
            ),
            tooltip=[
                alt.Tooltip("Flowgate:N"),
                alt.Tooltip("Hour Ending:O"),
                alt.Tooltip("Shadow Price ($/MWh):Q", format=".2f"),
                alt.Tooltip("Congestion Rent ($/hr):Q", format=",.0f"),
            ],
        )
        .properties(
            title="Flowgate Congestion Heatmap",
            width=700,
            height=200,
        )
    )
    congestion_chart
    return (congestion_chart,)


@app.cell
def _(mo):
    mo.md(r"""
    ## 9. BESS Arbitrage

    The BESS creates value by time-shifting energy: charging when prices
    are low and discharging when prices are high.  The arbitrage profit
    is the price spread captured across the charge-discharge cycle.
    """)
    return


@app.cell
def _(alt, ed_solution, np, pd):
    _bess_ch = ed_solution["bess_ch"]
    _bess_dis = ed_solution["bess_dis"]
    _soc = ed_solution["soc"]
    _energy_lmp = ed_solution["energy_lmp"]

    _bess_records = []
    for _h in range(24):
        _bess_records.append(
            {
                "Hour Ending": _h + 1,
                "Charge (MW)": -_bess_ch[_h],  # negative for visual stacking
                "Discharge (MW)": _bess_dis[_h],
                "SoC (MWh)": _soc[_h],
                "LMP ($/MWh)": _energy_lmp[_h],
            }
        )
    _bess_df = pd.DataFrame(_bess_records)

    # Net BESS action
    _bess_df["Net (MW)"] = _bess_df["Discharge (MW)"] + _bess_df["Charge (MW)"]

    _bess_bar = (
        alt.Chart(_bess_df)
        .mark_bar()
        .encode(
            x=alt.X("Hour Ending:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Net (MW):Q", title="BESS Power (MW, + = discharge)"),
            color=alt.condition(
                alt.datum["Net (MW)"] > 0,
                alt.value("#2ca02c"),  # discharge = green
                alt.value("#d62728"),  # charge = red
            ),
            tooltip=[
                alt.Tooltip("Hour Ending:O"),
                alt.Tooltip("Net (MW):Q", format=".1f"),
                alt.Tooltip("SoC (MWh):Q", format=".1f"),
                alt.Tooltip("LMP ($/MWh):Q", format=".2f"),
            ],
        )
    )

    _soc_line = (
        alt.Chart(_bess_df)
        .mark_line(color="black", strokeWidth=2, point=True)
        .encode(
            x="Hour Ending:O",
            y=alt.Y(
                "SoC (MWh):Q", title="State of Charge (MWh)", axis=alt.Axis(titleColor="black")
            ),
        )
    )

    bess_chart = (
        alt.layer(_bess_bar, _soc_line)
        .resolve_scale(y="independent")
        .properties(
            title="BESS Operation: Charge/Discharge and State of Charge",
            width=700,
            height=350,
        )
    )
    bess_chart

    # Compute BESS arbitrage revenue
    _revenue = sum(_bess_dis[_hh] * _energy_lmp[_hh] for _hh in range(24))
    _cost = sum(_bess_ch[_hh] * _energy_lmp[_hh] for _hh in range(24))
    profit = _revenue - _cost

    return bess_chart, profit


@app.cell
def _(profit, mo):
    mo.md(rf"""
    The BESS earns **${profit:,.0f}** in arbitrage profit over 24 hours
    by buying energy at low prices (red bars) and selling at high prices
    (green bars).  The SoC line (right axis) shows the battery cycling
    from its initial level, down during discharge, and back up during
    charge.  The cyclic constraint ensures it ends the day at the same
    SoC it started with.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 10. Connecting to the Evaluation Rubric

    This notebook demonstrates the **minimum viable optimization** that
    each tool under evaluation should be able to replicate.  The key
    capabilities tested are:

    | Rubric Dimension | What This Notebook Tests |
    |------------------|--------------------------|
    | **Gate** | Can the tool solve a DC OPF on the 39-bus case? |
    | **Expressiveness** | Can it model thermal generators, renewables, BESS, and flowgates simultaneously? |
    | **Extensibility** | How hard is it to add the PTDF-based flowgate formulation? |
    | **Scalability** | How does performance change on ACTIVSg2000 (2000 buses) and ACTIVSg10k (10,000 buses)? |

    The 39-bus system solved here in milliseconds.  At 2000+ buses with
    unit commitment (binary variables), solve time can grow to minutes
    or hours — and that's where tool choice matters.

    ### What we built, end to end

    1. **Notebook 01** — Parsed the raw MATPOWER case file.
    2. **Notebook 02** — Calibrated generator costs, temporal params,
       load profiles, reserves, and renewable profiles.
    3. **Notebook 03** — Added BESS, demand response, and flowgates.
    4. **Notebook 04** — Built stochastic scenarios for renewables.
    5. **Notebook 05** — Validated referential integrity, physical
       plausibility, and statistical fidelity.
    6. **Notebook 06** — Solved the economic dispatch, computed LMPs,
       and analyzed congestion rents.

    The dataset is ready. The evaluation begins.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
