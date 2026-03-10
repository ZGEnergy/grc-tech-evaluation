"""Example: 24h multi-period DCOPF with the augmented case39 dataset using PyPSA.

Demonstrates loading the base network, applying differentiated costs, adding
renewables/storage/DR from the CSV files, and running progressively harder
OPF analyses.  Intended as a reference implementation for other tools.

Requirements:
    pip install pypsa matpowercaseframes pandas highs
    pip install matplotlib  # only needed for chart subcommand

Usage:
    cd data/timeseries/case39
    python example_pypsa_dcopf.py                # run all examples
    python example_pypsa_dcopf.py test            # run as pytest (requires pytest)
    python example_pypsa_dcopf.py chart           # generate congestion/BESS chart
    python example_pypsa_dcopf.py chart out.png   # save chart to custom path
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

# Paths — resolved relative to this script (lives alongside the CSV data)
HERE = Path(__file__).resolve().parent
NETWORK_DIR = HERE.parent.parent / "networks"

# Tech class → marginal cost ($/MWh), from README
TECH_CLASS_COST: dict[str, float] = {
    "hydro": 5.0,
    "nuclear": 10.0,
    "coal_large": 25.0,
    "gas_CC": 40.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_base_network(*, quadratic: bool = False) -> pypsa.Network:
    """Load case39.m and apply differentiated marginal costs.

    Args:
        quadratic: If True, also set marginal_cost_quadratic = c1 * 0.001.
            Quadratic costs make the marginal cost rise with dispatch level,
            producing hour-varying LMPs needed for BESS arbitrage (see README).
    """
    cf = CaseFrames(str(NETWORK_DIR / "case39.m"))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)

    gen_params = pd.read_csv(HERE / "gen_temporal_params.csv")
    for i, gen_name in enumerate(net.generators.index):
        if i < len(gen_params):
            tech_key = gen_params.iloc[i]["tech_class_key"]
            c1 = TECH_CLASS_COST.get(tech_key, 50.0)
            net.generators.loc[gen_name, "marginal_cost"] = c1
            if quadratic:
                net.generators.loc[gen_name, "marginal_cost_quadratic"] = c1 * 0.001

    return net


def set_snapshots_and_loads(net: pypsa.Network) -> None:
    """Set 24-hour snapshots and time-varying bus loads."""
    net.set_snapshots(range(24))
    load_df = pd.read_csv(HERE / "load_24h.csv")
    for load_name in net.loads.index:
        bus_id = int(net.loads.loc[load_name, "bus"])
        row = load_df[load_df["bus_id"] == bus_id]
        if not row.empty:
            net.loads_t.p_set.loc[:, load_name] = [
                float(row.iloc[0][f"HR_{h}"]) for h in range(1, 25)
            ]


def add_renewables(
    net: pypsa.Network,
    scenario_id: int | None = None,
    solar_scale: float = 1.0,
) -> dict[str, list[float]]:
    """Add renewable generators and set time-varying p_max_pu.

    Args:
        solar_scale: Multiplier on solar p_nom.  Values > 1 increase midday
            generation, creating a price dip that enables BESS arbitrage.

    Returns base forecast MW values keyed by gen_uid (before scenario adjustment).
    """
    units = pd.read_csv(HERE / "renewable_units.csv")
    wind_fc = pd.read_csv(HERE / "wind_forecast_24h.csv")
    solar_fc = pd.read_csv(HERE / "solar_forecast_24h.csv")

    base_forecasts: dict[str, list[float]] = {}

    for _, unit in units.iterrows():
        gen_uid = unit["gen_uid"]
        bus_id = str(unit["bus_id"])
        pmax = float(unit["pmax_mw"])
        rtype = unit["type"]

        effective_pnom = pmax * solar_scale if rtype == "solar" else pmax
        net.add("Generator", gen_uid, bus=bus_id, p_nom=effective_pnom, marginal_cost=0.0)

        if rtype == "wind":
            fc_row = wind_fc[wind_fc["gen_uid"] == gen_uid]
        else:
            fc_row = solar_fc[solar_fc["gen_uid"] == gen_uid]

        if not fc_row.empty:
            hourly_mw = [float(fc_row.iloc[0][f"HR_{h}"]) for h in range(1, 25)]
        else:
            hourly_mw = [0.0] * 24

        base_forecasts[gen_uid] = hourly_mw
        p_max_pu = [min(mw / pmax, 1.0) if pmax > 0 else 0.0 for mw in hourly_mw]
        net.generators_t.p_max_pu.loc[:, gen_uid] = p_max_pu

    if scenario_id is not None:
        _apply_scenario_multipliers(net, base_forecasts, scenario_id)

    return base_forecasts


def _apply_scenario_multipliers(
    net: pypsa.Network,
    base_forecasts: dict[str, list[float]],
    scenario_id: int,
) -> None:
    """Apply scenario multipliers to renewable p_max_pu profiles."""
    scenario_df = pd.read_csv(HERE / "scenarios" / "scenario_multipliers_50x24.csv")
    scen_rows = scenario_df[scenario_df["scenario"] == scenario_id]

    units = pd.read_csv(HERE / "renewable_units.csv")
    pmax_map = {row["gen_uid"]: float(row["pmax_mw"]) for _, row in units.iterrows()}

    for _, row in scen_rows.iterrows():
        gen_uid = row["gen_uid"]
        if gen_uid not in base_forecasts:
            continue
        base_fc = base_forecasts[gen_uid]
        pmax = pmax_map.get(gen_uid, 1.0)
        mults = [float(row[f"HR_{h}"]) for h in range(1, 25)]
        adjusted = [min(fc * m, pmax) / pmax if pmax > 0 else 0.0 for fc, m in zip(base_fc, mults)]
        net.generators_t.p_max_pu.loc[:, gen_uid] = adjusted


def add_bess(net: pypsa.Network, bus_override: str | None = None) -> None:
    """Add BESS StorageUnit from bess_units.csv.

    Args:
        bus_override: If set, place the BESS at this bus instead of the CSV default.
    """
    bess_df = pd.read_csv(HERE / "bess_units.csv")
    for _, row in bess_df.iterrows():
        bus = bus_override if bus_override else str(int(row["bus_id"]))
        net.add(
            "StorageUnit",
            row["unit_id"],
            bus=bus,
            p_nom=float(row["power_mw"]),
            max_hours=float(row["energy_mwh"]) / float(row["power_mw"]),
            efficiency_store=0.92,
            efficiency_dispatch=0.95,
            cyclic_state_of_charge=True,
            state_of_charge_initial=float(row["init_soc"]),
        )


def add_dr(net: pypsa.Network) -> None:
    """Add demand response as an expensive generator from dr_buses.csv."""
    dr_df = pd.read_csv(HERE / "dr_buses.csv")
    for _, row in dr_df.iterrows():
        bus_id = str(int(row["bus_id"]))
        net.add(
            "Generator",
            f"DR_bus{bus_id}",
            bus=bus_id,
            p_nom=float(row["max_curtailment_mw"]),
            marginal_cost=float(row["curtailment_cost"]),
        )


def derate_branches(net: pypsa.Network, factor: float) -> None:
    """Scale all line thermal ratings by factor (e.g. 0.70 for 70% derating)."""
    net.lines["s_nom"] *= factor


def optimize(net: pypsa.Network) -> str:
    """Run DCOPF and return status string."""
    status, _ = net.optimize(
        solver_name="highs",
        solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        assign_all_duals=True,
    )
    return status


# ---------------------------------------------------------------------------
# Example functions (also usable as pytest tests)
# ---------------------------------------------------------------------------


def test_01_dcopf_differentiated_costs():
    """Single-snapshot DCOPF with differentiated generator costs."""
    net = load_base_network()
    status = optimize(net)

    assert status == "ok", f"Solver failed: {status}"

    prices = net.buses_t.marginal_price.loc[net.snapshots[0]]
    lmp_spread = prices.max() - prices.min()
    assert lmp_spread > 0, "LMP spread is zero — costs may not be differentiated"

    dispatch = net.generators_t.p.loc[net.snapshots[0]]
    hydro_gen = net.generators.index[0]
    hydro_pmax = net.generators.loc[hydro_gen, "p_nom"]
    hydro_dispatch = dispatch[hydro_gen]
    assert hydro_dispatch > 0.8 * hydro_pmax, (
        f"Hydro dispatch {hydro_dispatch:.1f} MW < 80% of Pmax {hydro_pmax:.1f} MW"
    )
    print(f"  PASS: LMP spread = ${lmp_spread:.2f}/MWh, hydro at {hydro_dispatch:.0f} MW")


def test_02_multiperiod_dcopf_24h():
    """24-hour multi-period DCOPF with renewables and time-varying load."""
    net = load_base_network()
    set_snapshots_and_loads(net)
    add_renewables(net)
    status = optimize(net)

    assert status == "ok", f"Solver failed: {status}"

    gen_dispatch = net.generators_t.p
    conv_gens = [g for g in net.generators.index if not g.startswith(("WIND_", "SOLAR_", "DR_"))]
    conv_std = gen_dispatch[conv_gens].std()
    assert (conv_std > 0).any(), "No conventional generator varies across 24 hours"

    solar_gens = [g for g in net.generators.index if g.startswith("SOLAR_")]
    if solar_gens:
        night_solar = gen_dispatch.loc[:5, solar_gens]
        assert (night_solar.abs() < 0.1).all().all(), "Solar should be ~zero at night (HR_1-HR_6)"

    total_gen = gen_dispatch.sum(axis=1)
    total_load = net.loads_t.p_set.sum(axis=1)
    balance_error = (total_gen - total_load).abs()
    assert (balance_error < total_load * 0.05 + 1.0).all(), (
        f"Power balance error too large: max {balance_error.max():.1f} MW"
    )
    print(f"  PASS: 24h solved, objective = ${net.objective:,.0f}")


def test_03_bess_charges_and_discharges():
    """24h DCOPF with BESS co-located at solar bus — charges midday, discharges evening.

    Uses quadratic costs (c2 = c1 * 0.001) so marginal cost rises with dispatch,
    plus 3x solar nameplate.  BESS is placed at bus 5 (SOLAR_1) where the midday
    solar surplus depresses LMPs to ~$27/MWh while evening peak reaches ~$60/MWh.
    """
    solar_mult = 3.0

    net_base = load_base_network(quadratic=True)
    set_snapshots_and_loads(net_base)
    add_renewables(net_base, solar_scale=solar_mult)
    status_base = optimize(net_base)
    assert status_base == "ok"
    obj_without_bess = net_base.objective

    net = load_base_network(quadratic=True)
    set_snapshots_and_loads(net)
    add_renewables(net, solar_scale=solar_mult)
    add_bess(net)

    status = optimize(net)
    assert status == "ok", f"Solver failed with BESS: {status}"
    obj_with_bess = net.objective

    bess_p = net.storage_units_t.p
    assert not bess_p.empty, "No BESS dispatch results"

    bess_name = net.storage_units.index[0]
    bess_series = bess_p[bess_name]

    assert (bess_series > 0.01).any(), "BESS never discharges"
    assert (bess_series < -0.01).any(), "BESS never charges"

    soc = net.storage_units_t.state_of_charge[bess_name]
    energy_mwh = (
        net.storage_units.loc[bess_name, "p_nom"] * net.storage_units.loc[bess_name, "max_hours"]
    )
    assert (soc >= -0.01).all(), f"SoC goes below 0: min={soc.min():.2f}"
    assert (soc <= energy_mwh * 1.01).all(), f"SoC exceeds capacity: max={soc.max():.2f}"

    assert obj_with_bess <= obj_without_bess * 1.001, (
        f"BESS should reduce cost: with={obj_with_bess:.2f}, without={obj_without_bess:.2f}"
    )
    savings = obj_without_bess - obj_with_bess
    print(f"  PASS: BESS saves ${savings:,.0f} ({savings / obj_without_bess * 100:.2f}%)")


def test_04_demand_response():
    """24h DCOPF with DR — DR should dispatch sparingly at high prices."""
    net = load_base_network()
    set_snapshots_and_loads(net)
    add_renewables(net)
    add_bess(net)
    add_dr(net)
    status = optimize(net)

    assert status == "ok", f"Solver failed with DR: {status}"

    dr_gens = [g for g in net.generators.index if g.startswith("DR_")]
    if dr_gens:
        dr_dispatch = net.generators_t.p[dr_gens].sum(axis=1)
        hours_dispatched = (dr_dispatch > 0.01).sum()
        assert hours_dispatched < 24, "DR dispatches every hour — cost may be too low"

        if hours_dispatched > 0:
            prices = net.buses_t.marginal_price.mean(axis=1)
            dr_hours = dr_dispatch[dr_dispatch > 0.01].index
            non_dr_hours = dr_dispatch[dr_dispatch <= 0.01].index
            if len(non_dr_hours) > 0:
                avg_price_dr = prices.loc[dr_hours].mean()
                avg_price_non_dr = prices.loc[non_dr_hours].mean()
                assert avg_price_dr >= avg_price_non_dr, (
                    f"DR dispatches in cheaper hours: DR avg={avg_price_dr:.2f}, "
                    f"non-DR avg={avg_price_non_dr:.2f}"
                )
    print(f"  PASS: DR dispatches in {hours_dispatched} of 24 hours")


def test_05_congestion_70pct_derating():
    """24h DCOPF with 70% branch derating — should produce binding constraints."""
    net = load_base_network()
    set_snapshots_and_loads(net)
    add_renewables(net)
    add_bess(net)
    add_dr(net)

    derate_factor = 0.70
    derate_branches(net, derate_factor)
    status = optimize(net)

    if status != "ok":
        net = load_base_network()
        set_snapshots_and_loads(net)
        add_renewables(net)
        add_bess(net)
        add_dr(net)
        derate_factor = 0.80
        derate_branches(net, derate_factor)
        status = optimize(net)

    assert status == "ok", f"Solver failed even at {derate_factor:.0%} derating: {status}"

    has_mu_upper = hasattr(net.lines_t, "mu_upper") and not net.lines_t.mu_upper.empty
    has_mu_lower = hasattr(net.lines_t, "mu_lower") and not net.lines_t.mu_lower.empty

    binding_upper = (net.lines_t.mu_upper.abs() > 1e-6).any() if has_mu_upper else pd.Series()
    binding_lower = (net.lines_t.mu_lower.abs() > 1e-6).any() if has_mu_lower else pd.Series()

    n_binding_upper = binding_upper.sum() if len(binding_upper) > 0 else 0
    n_binding_lower = binding_lower.sum() if len(binding_lower) > 0 else 0
    n_binding = n_binding_upper + n_binding_lower

    assert n_binding >= 2, (
        f"Expected >=2 binding lines with {derate_factor:.0%} derating, got {n_binding}"
    )

    prices = net.buses_t.marginal_price
    lmp_spread_per_hour = prices.max(axis=1) - prices.min(axis=1)
    hours_with_spread = (lmp_spread_per_hour > 1.0).sum()
    assert hours_with_spread > 0, "No hours with LMP spread > $1/MWh under congestion"
    print(f"  PASS: {n_binding} binding lines, LMP spread in {hours_with_spread} hours")


def test_06_scenario_variation():
    """3 scenarios with different renewable multipliers produce different outcomes."""
    scenario_ids = [1, 25, 50]
    objectives: list[float] = []
    lmp_matrices: list[pd.DataFrame] = []

    for sid in scenario_ids:
        net = load_base_network()
        set_snapshots_and_loads(net)
        add_renewables(net, scenario_id=sid)
        add_bess(net)
        derate_branches(net, 0.70)
        status = optimize(net)

        assert status == "ok", f"Scenario {sid} failed: {status}"
        objectives.append(float(net.objective))
        lmp_matrices.append(net.buses_t.marginal_price.copy())

    unique_objs = len(set(round(o, 2) for o in objectives))
    assert unique_objs > 1, f"All {len(scenario_ids)} scenarios have same objective: {objectives}"

    bus_lmp_differs = False
    for bus in lmp_matrices[0].columns:
        vals = [lmp_df[bus].mean() for lmp_df in lmp_matrices]
        if len(set(round(v, 4) for v in vals)) > 1:
            bus_lmp_differs = True
            break
    assert bus_lmp_differs, "No bus has different average LMPs across scenarios"
    print(f"  PASS: objectives = {['${:,.0f}'.format(o) for o in objectives]}")


# ---------------------------------------------------------------------------
# Charting — congestion / BESS arbitrage timeseries
# ---------------------------------------------------------------------------


def plot_congestion_results(
    net: pypsa.Network,
    bess_bus: str | None = None,
    output_path: str | Path | None = None,
    title: str = "24h DCOPF — Congestion & BESS Arbitrage",
) -> None:
    """Generate a 3-panel timeseries chart: LMP spread, BESS dispatch, SoC.

    Args:
        net: Solved PyPSA network (must have buses_t.marginal_price populated).
        bess_bus: Bus ID for the BESS (highlighted in LMP panel). Auto-detected
            from storage_units if not given.
        output_path: Save chart to this path. If None, calls plt.show().
        title: Chart suptitle.

    Requires matplotlib: ``pip install matplotlib``
    """
    import matplotlib.pyplot as plt

    hours = list(range(len(net.snapshots)))
    prices = net.buses_t.marginal_price

    # Auto-detect BESS bus
    if bess_bus is None and not net.storage_units.empty:
        bess_bus = str(net.storage_units.iloc[0]["bus"])

    # Find the two buses with the largest average LMP spread from the BESS bus
    if bess_bus and bess_bus in prices.columns:
        bess_lmp = prices[bess_bus]
        spreads = {b: (prices[b] - bess_lmp).abs().mean() for b in prices.columns if b != bess_bus}
        top_buses = sorted(spreads, key=spreads.get, reverse=True)[:2]  # type: ignore[arg-type]
    else:
        mean_lmps = prices.mean()
        top_buses = [mean_lmps.idxmax(), mean_lmps.idxmin()]

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    # --- Panel 1: LMPs ---
    ax1 = axes[0]
    for bus in top_buses:
        ax1.plot(hours, prices[bus].values, label=f"Bus {bus}", linewidth=1.5)
    if bess_bus and bess_bus in prices.columns:
        ax1.plot(
            hours,
            prices[bess_bus].values,
            label=f"Bus {bess_bus} (BESS)",
            linewidth=2,
            linestyle="--",
            color="black",
        )
    ax1.set_ylabel("LMP ($/MWh)")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_title("Locational Marginal Prices")

    # --- Panel 2: BESS charge/discharge ---
    ax2 = axes[1]
    if not net.storage_units_t.p.empty:
        bess_name = net.storage_units.index[0]
        bess_p = net.storage_units_t.p[bess_name].values
        colors = ["#2ca02c" if v > 0 else "#d62728" for v in bess_p]
        ax2.bar(hours, bess_p, color=colors, width=0.8, alpha=0.8)
        ax2.axhline(0, color="black", linewidth=0.5)
        ax2.set_ylabel("MW (+ discharge, − charge)")
        ax2.set_title("BESS Dispatch")
    else:
        ax2.text(0.5, 0.5, "No BESS in network", transform=ax2.transAxes, ha="center")
    ax2.grid(True, alpha=0.3)

    # --- Panel 3: State of Charge ---
    ax3 = axes[2]
    if not net.storage_units_t.state_of_charge.empty:
        bess_name = net.storage_units.index[0]
        soc = net.storage_units_t.state_of_charge[bess_name].values
        energy_cap = (
            net.storage_units.loc[bess_name, "p_nom"]
            * net.storage_units.loc[bess_name, "max_hours"]
        )
        soc_pct = soc / energy_cap * 100
        ax3.fill_between(hours, soc_pct, alpha=0.4, color="#1f77b4")
        ax3.plot(hours, soc_pct, color="#1f77b4", linewidth=1.5)
        ax3.set_ylabel("SoC (%)")
        ax3.set_ylim(0, 100)
        ax3.set_title("BESS State of Charge")
    else:
        ax3.text(0.5, 0.5, "No SoC data", transform=ax3.transAxes, ha="center")
    ax3.set_xlabel("Hour")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Chart saved to {output_path}")
    else:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_01_dcopf_differentiated_costs,
    test_02_multiperiod_dcopf_24h,
    test_03_bess_charges_and_discharges,
    test_04_demand_response,
    test_05_congestion_70pct_derating,
    test_06_scenario_variation,
]

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        import pytest

        sys.exit(pytest.main([__file__, "-v"]))

    if len(sys.argv) > 1 and sys.argv[1] == "chart":
        # Build the congested network with BESS and generate the chart
        out_path = sys.argv[2] if len(sys.argv) > 2 else "congestion_chart.png"
        print("Building 24h network with BESS, 3x solar, 70% derating...")
        net = load_base_network(quadratic=True)
        set_snapshots_and_loads(net)
        add_renewables(net, solar_scale=3.0)
        add_bess(net)
        add_dr(net)
        derate_branches(net, 0.70)
        status = optimize(net)
        assert status == "ok", f"Solver failed: {status}"
        plot_congestion_results(net, output_path=out_path)
        sys.exit(0)

    passed = 0
    failed = 0
    for fn in ALL_TESTS:
        name = fn.__name__
        print(f"\n{'=' * 60}\n{name}: {fn.__doc__.strip().splitlines()[0]}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    sys.exit(1 if failed else 0)
