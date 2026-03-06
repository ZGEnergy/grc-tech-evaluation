"""Shared topology visualization helpers for IEEE 39-bus tutorial notebooks.

Provides interactive plotly network diagrams with overlay functions for
generators, loads, branch loading, and flexible resource markers.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Hand-curated bus positions matching the canonical IEEE 39-bus one-line diagram.
# Coordinates are in an arbitrary (x, y) space designed for visual clarity.
# Generator buses sit on the perimeter; backbone buses 1-29 form the interior mesh.
# ---------------------------------------------------------------------------
BUS_POSITIONS: dict[int, tuple[float, float]] = {
    # --- Backbone buses (1-29) ---
    1: (1.5, 5.0),
    2: (2.5, 7.0),
    3: (4.0, 6.0),
    4: (5.5, 6.0),
    5: (7.0, 6.5),
    6: (8.0, 6.0),
    7: (9.0, 7.0),
    8: (8.0, 8.0),
    9: (1.0, 3.5),
    10: (9.5, 5.0),
    11: (8.5, 5.5),
    12: (9.5, 4.0),
    13: (8.5, 3.5),
    14: (6.5, 4.5),
    15: (5.5, 4.0),
    16: (4.5, 3.0),
    17: (3.5, 4.0),
    18: (3.5, 5.0),
    19: (5.5, 2.0),
    20: (6.5, 1.5),
    21: (3.5, 2.0),
    22: (2.5, 1.0),
    23: (4.0, 0.5),
    24: (5.0, 1.5),
    25: (2.0, 8.5),
    26: (3.5, 9.0),
    27: (3.0, 7.0),
    28: (5.0, 9.5),
    29: (6.5, 9.5),
    # --- Generator buses (30-39, perimeter) ---
    30: (1.0, 8.5),  # Hydro — top-left, transformer to bus 2
    31: (9.5, 7.0),  # Nuclear (Ref/Slack) — right, transformer to bus 6
    32: (10.5, 5.5),  # Nuclear — far right, transformer to bus 10
    33: (6.5, 2.5),  # Coal — lower right, transformer to bus 19
    34: (7.5, 0.5),  # Coal — bottom right, transformer to bus 20
    35: (1.5, 0.5),  # Nuclear — bottom left, transformer to bus 22
    36: (5.0, -0.5),  # Gas — bottom center, transformer to bus 23
    37: (1.0, 9.5),  # Nuclear — top left, transformer to bus 25
    38: (7.5, 10.0),  # Nuclear — top right, transformer to bus 29
    39: (0.0, 4.0),  # Interconnect — far left, lines to buses 1 & 9
}

# ---------------------------------------------------------------------------
# Shared fuel-type color palette (used by both plotly and Altair charts)
# ---------------------------------------------------------------------------
FUEL_COLORS: dict[str, str] = {
    "Hydro": "#2196f3",
    "Nuclear": "#e04040",
    "Coal": "#4a4a4a",
    "Gas": "#e8a838",
    "Wind": "#66bb6a",
    "Solar": "#fdd835",
}

# Default layout settings for all topology figures
_LAYOUT_DEFAULTS = dict(
    showlegend=True,
    hovermode="closest",
    plot_bgcolor="white",
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
    margin=dict(l=20, r=20, t=50, b=20),
    width=800,
    height=600,
)


def build_graph(bus_df: pd.DataFrame, branch_df: pd.DataFrame) -> nx.Graph:
    """Construct a networkx graph from bus and branch DataFrames.

    Validates that every bus in the DataFrame has a curated position.
    """
    bus_ids = set(bus_df["bus_id"].astype(int))
    pos_ids = set(BUS_POSITIONS)
    assert bus_ids == pos_ids, (
        f"Bus ID mismatch — in data but not in BUS_POSITIONS: {bus_ids - pos_ids}, "
        f"in BUS_POSITIONS but not in data: {pos_ids - bus_ids}"
    )

    G = nx.Graph()
    for _, row in bus_df.iterrows():
        bid = int(row["bus_id"])
        G.add_node(
            bid,
            pos=BUS_POSITIONS[bid],
            pd_mw=row.get("pd_mw", 0),
            bus_type_name=row.get("bus_type_name", ""),
        )

    for _, row in branch_df.iterrows():
        fb, tb = int(row["fbus"]), int(row["tbus"])
        is_xfmr = row.get("ratio", 0) != 0
        G.add_edge(
            fb,
            tb,
            r_pu=row.get("r_pu", 0),
            x_pu=row.get("x_pu", 0),
            rate_a_mva=row.get("rate_a_mva", 0),
            is_transformer=is_xfmr,
        )
    return G


def plot_base_topology(
    G: nx.Graph,
    title: str = "IEEE 39-Bus Network",
    bus_color: str = "#4c78a8",
    bus_size: int = 12,
    branch_color: str = "#aaa",
    branch_width: float = 1.5,
) -> go.Figure:
    """Render the base topology — buses as circles, branches as lines."""
    edge_traces = _make_edge_traces(G, branch_color, branch_width)

    # Bus scatter
    node_x, node_y, hover, ids = [], [], [], []
    for n in G.nodes():
        x, y = BUS_POSITIONS[n]
        node_x.append(x)
        node_y.append(y)
        ids.append(n)
        pd_mw = G.nodes[n].get("pd_mw", 0)
        btype = G.nodes[n].get("bus_type_name", "")
        hover.append(f"Bus {n}<br>Type: {btype}<br>Load: {pd_mw:.0f} MW")

    bus_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(size=bus_size, color=bus_color, line=dict(width=1, color="white")),
        text=[str(i) for i in ids],
        textposition="top center",
        textfont=dict(size=8),
        hovertext=hover,
        hoverinfo="text",
        name="Buses",
    )

    fig = go.Figure(data=[*edge_traces, bus_trace])
    fig.update_layout(title=title, **_LAYOUT_DEFAULTS)
    return fig


def add_generator_markers(
    fig: go.Figure,
    gen_df: pd.DataFrame,
    size_col: str = "pmax_mw",
    fuel_col: str = "fuel_type",
    bus_col: str = "gen_bus",
    min_size: int = 14,
    max_size: int = 40,
    show_label: bool = True,
) -> go.Figure:
    """Overlay square markers at generator buses, colored by fuel type, sized by capacity."""
    if gen_df.empty:
        return fig

    sizes = gen_df[size_col]
    sz_min, sz_max = sizes.min(), sizes.max()
    if sz_max == sz_min:
        norm_sizes = [int((min_size + max_size) / 2)] * len(sizes)
    else:
        norm_sizes = [
            int(min_size + (max_size - min_size) * (v - sz_min) / (sz_max - sz_min)) for v in sizes
        ]

    # Group by fuel type for legend
    fuels = gen_df[fuel_col].unique()
    for fuel in fuels:
        mask = gen_df[fuel_col] == fuel
        sub = gen_df[mask]
        sub_sizes = [norm_sizes[i] for i in sub.index]
        gx = [BUS_POSITIONS[int(b)][0] for b in sub[bus_col]]
        gy = [BUS_POSITIONS[int(b)][1] for b in sub[bus_col]]
        hover = [
            f"Gen @ Bus {int(r[bus_col])}<br>{r[fuel_col]}<br>{r[size_col]:.0f} MW"
            for _, r in sub.iterrows()
        ]
        color = FUEL_COLORS.get(fuel, "#888")
        fig.add_trace(
            go.Scatter(
                x=gx,
                y=gy,
                mode="markers+text" if show_label else "markers",
                marker=dict(
                    size=sub_sizes,
                    color=color,
                    symbol="square",
                    line=dict(width=1.5, color="white"),
                ),
                text=[f"{int(r[size_col])} MW" for _, r in sub.iterrows()] if show_label else None,
                textposition="bottom center",
                textfont=dict(size=7),
                hovertext=hover,
                hoverinfo="text",
                name=fuel,
                legendgroup=fuel,
            )
        )
    return fig


def add_load_markers(
    fig: go.Figure,
    bus_df: pd.DataFrame,
    min_size: int = 8,
    max_size: int = 28,
) -> go.Figure:
    """Overlay triangle-down markers at load buses, sized by Pd."""
    loads = bus_df[bus_df["pd_mw"] > 0].copy()
    if loads.empty:
        return fig

    sizes = loads["pd_mw"]
    sz_min, sz_max = sizes.min(), sizes.max()
    if sz_max == sz_min:
        norm = [int((min_size + max_size) / 2)] * len(sizes)
    else:
        norm = [
            int(min_size + (max_size - min_size) * (v - sz_min) / (sz_max - sz_min)) for v in sizes
        ]

    lx = [BUS_POSITIONS[int(b)][0] for b in loads["bus_id"]]
    ly = [BUS_POSITIONS[int(b)][1] for b in loads["bus_id"]]
    hover = [f"Bus {int(r['bus_id'])}<br>Load: {r['pd_mw']:.0f} MW" for _, r in loads.iterrows()]

    fig.add_trace(
        go.Scatter(
            x=lx,
            y=ly,
            mode="markers",
            marker=dict(
                size=norm,
                color="#ff7f0e",
                symbol="triangle-down",
                line=dict(width=1, color="white"),
                opacity=0.7,
            ),
            hovertext=hover,
            hoverinfo="text",
            name="Load",
        )
    )
    return fig


def add_branch_loading(
    fig: go.Figure,
    G: nx.Graph,
    branch_flows: pd.DataFrame,
    fbus_col: str = "fbus",
    tbus_col: str = "tbus",
    loading_col: str = "loading_pct",
) -> go.Figure:
    """Color and thicken branches by loading percentage (green->yellow->red)."""
    for _, row in branch_flows.iterrows():
        fb, tb = int(row[fbus_col]), int(row[tbus_col])
        loading = row[loading_col]
        x0, y0 = BUS_POSITIONS.get(fb, (0, 0))
        x1, y1 = BUS_POSITIONS.get(tb, (0, 0))

        if loading >= 80:
            color = "#d62728"
            width = 4
        elif loading >= 50:
            color = "#ff7f0e"
            width = 3
        else:
            color = "#2ca02c"
            width = 2

        fig.add_trace(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(color=color, width=width),
                hovertext=f"{fb}-{tb}: {loading:.1f}%",
                hoverinfo="text",
                showlegend=False,
            )
        )
    return fig


def add_resource_markers(
    fig: go.Figure,
    resources: list[dict],
) -> go.Figure:
    """Add BESS/DR/Wind/Solar markers at specified buses.

    Each resource dict should have: bus (int), type (str), label (str),
    and optionally mw (float).
    """
    symbols = {"BESS": "diamond", "DR": "hexagon", "Wind": "star", "Solar": "star-triangle-up"}
    colors = {"BESS": "#9c27b0", "DR": "#00bcd4", **FUEL_COLORS}

    # Group by type for legend
    by_type: dict[str, list[dict]] = {}
    for r in resources:
        by_type.setdefault(r["type"], []).append(r)

    for rtype, items in by_type.items():
        rx = [BUS_POSITIONS[it["bus"]][0] for it in items]
        ry = [BUS_POSITIONS[it["bus"]][1] for it in items]
        hover = [f"{it['type']} @ Bus {it['bus']}<br>{it.get('label', '')}" for it in items]
        fig.add_trace(
            go.Scatter(
                x=rx,
                y=ry,
                mode="markers+text",
                marker=dict(
                    size=20,
                    color=colors.get(rtype, "#888"),
                    symbol=symbols.get(rtype, "circle"),
                    line=dict(width=1.5, color="white"),
                ),
                text=[it.get("label", "") for it in items],
                textposition="bottom center",
                textfont=dict(size=8),
                hovertext=hover,
                hoverinfo="text",
                name=rtype,
            )
        )
    return fig


def add_flowgate_highlights(
    fig: go.Figure,
    flowgates: list[dict],
) -> go.Figure:
    """Highlight flowgate branches in distinct colors.

    Each flowgate dict: name (str), branches (list of (from, to) tuples), color (str).
    """
    for fg in flowgates:
        xs, ys = [], []
        for fb, tb in fg["branches"]:
            x0, y0 = BUS_POSITIONS.get(fb, (0, 0))
            x1, y1 = BUS_POSITIONS.get(tb, (0, 0))
            xs.extend([x0, x1, None])
            ys.extend([y0, y1, None])
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=fg["color"], width=5),
                name=fg["name"],
                hoverinfo="name",
            )
        )
    return fig


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _make_edge_traces(
    G: nx.Graph,
    color: str = "#aaa",
    width: float = 1.5,
) -> list[go.Scatter]:
    """Create line traces for all edges (single trace with None separators)."""
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = BUS_POSITIONS[u]
        x1, y1 = BUS_POSITIONS[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    return [
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=width, color=color),
            hoverinfo="none",
            showlegend=False,
        )
    ]
