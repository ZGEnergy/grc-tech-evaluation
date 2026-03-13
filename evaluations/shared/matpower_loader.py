"""
Shared MATPOWER loader utilities for power-system tool evaluation.

Each `load_<tool>(path)` function provides a standardized, patched entry point
for loading MATPOWER .m case files into the corresponding tool's native format.

Lossiness classifications (see LOADING_NOTES.md for full detail):
  LOSSLESS  — tool ingests .m format without data loss or silent modification
  TRIVIAL   — minor post-load patch required; documented and deterministic
  MODERATE  — non-trivial conversion or approximation; documented
  BLOCKING  — critical data lost with no viable workaround
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# pypsa  (TRIVIAL — two patches applied post-load)
# ---------------------------------------------------------------------------


def load_pypsa(
    path: str | Path,
    overwrite_zero_s_nom: bool | float = True,
) -> object:  # pypsa.Network — imported lazily inside function body
    """Load a MATPOWER .m file into a PyPSA Network with correctness patches.

    Classification: TRIVIAL — two patches applied post-load; see LOADING_NOTES.md

    The raw ``matpowercaseframes → import_from_pypower_ppc`` bridge has two bugs
    that this function corrects:

    1. **Transformer susceptance** — PyPSA computes ``b = 1/(x * tap)`` but the
       MATPOWER DC convention is ``b = 1/x``.  This function resets every
       transformer's susceptance to ``1/x`` after loading.

    2. **Generator cost (gencost)** — ``import_from_pypower_ppc`` ignores the
       ``gencost`` table in the ppc dict, so all generators get ``marginal_cost=0``.
       This function populates ``marginal_cost`` from the gencost data.  For
       polynomial (model-2) entries the marginal cost is approximated as the
       first derivative at ``Pmax``: ``c1 + 2*c2*Pmax``.  Piecewise-linear
       (model-1) entries and higher-order polynomials are skipped (logged as
       warnings).

    Args:
        path: Path to a MATPOWER .m case file.
        overwrite_zero_s_nom: Passed directly to ``import_from_pypower_ppc``.
            ``True`` sets S_nom to 9999 MVA for branches that have 0 rating.
            Pass a float (e.g. ``100000.0``) for very large AC networks.

    Returns:
        A ``pypsa.Network`` with transformer susceptances and generator marginal
        costs corrected.
    """
    import numpy as np
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(str(path))

    ppc: dict = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
        "gencost": cf.gencost.values,
    }

    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=overwrite_zero_s_nom)

    # --- Patch 1: Transformer susceptance ---
    # PyPSA uses b = 1/(x*tap); MATPOWER DC convention is b = 1/x.
    for t_id in n.transformers.index:
        x = n.transformers.at[t_id, "x"]
        if x != 0:
            n.transformers.at[t_id, "b"] = 1.0 / x

    # --- Patch 2: Generator marginal costs from gencost ---
    gencost = cf.gencost
    if gencost is None or len(gencost) == 0:
        logger.warning(
            "load_pypsa: no gencost data in %s; marginal_cost left at 0", path
        )
        return n

    gen_names = n.generators.index.tolist()

    for i, gen_name in enumerate(gen_names):
        if i >= len(gencost):
            break

        row = gencost.iloc[i]

        # gencost columns: MODEL, STARTUP, SHUTDOWN, NCOST, c(n)...c1, c0
        model = int(row.iloc[0])
        ncost = int(row.iloc[3])

        if model == 2:
            # Polynomial: coefficients in descending order (c_n, ..., c1, c0)
            coeff_start = 4
            coeffs = row.iloc[coeff_start : coeff_start + ncost].values.astype(float)

            if ncost == 2:
                # Linear: c1*p + c0  → marginal cost = c1
                marginal_cost = coeffs[0]
            elif ncost == 3:
                # Quadratic: c2*p^2 + c1*p + c0  → MC at Pmax = c1 + 2*c2*Pmax
                c2, c1 = coeffs[0], coeffs[1]
                pmax = float(n.generators.at[gen_name, "p_nom"])
                marginal_cost = c1 + 2.0 * c2 * pmax
            else:
                logger.warning(
                    "load_pypsa: generator %s has polynomial degree %d; "
                    "only linear/quadratic supported — skipping marginal_cost",
                    gen_name,
                    ncost - 1,
                )
                continue

            if not np.isfinite(marginal_cost) or marginal_cost < 0:
                logger.warning(
                    "load_pypsa: generator %s computed marginal_cost=%g is "
                    "non-finite or negative; skipping",
                    gen_name,
                    marginal_cost,
                )
                continue

            n.generators.at[gen_name, "marginal_cost"] = marginal_cost

        elif model == 1:
            # Piecewise-linear: not collapsed to a scalar — skip
            logger.warning(
                "load_pypsa: generator %s uses piecewise-linear (model-1) cost; "
                "marginal_cost not set",
                gen_name,
            )
        else:
            logger.warning(
                "load_pypsa: generator %s has unknown gencost model %d; skipping",
                gen_name,
                model,
            )

    return n


# ---------------------------------------------------------------------------
# pandapower  (LOSSLESS)
# ---------------------------------------------------------------------------


def load_pandapower(path: str | Path) -> object:  # pandapower.auxiliary.pandapowerNet
    """Load a MATPOWER .m file into a pandapower network.

    Classification: LOSSLESS — pandapower's ``from_mpc`` ingests MATPOWER .m
    files directly with no data loss.  Non-unity-tap branches are automatically
    promoted to transformers.

    Args:
        path: Path to a MATPOWER .m case file.

    Returns:
        A ``pandapowerNet`` object.
    """
    from pandapower.converter.matpower.from_mpc import from_mpc

    return from_mpc(str(path), f_hz=60)


# ---------------------------------------------------------------------------
# gridcal  (LOSSLESS)
# ---------------------------------------------------------------------------


def load_gridcal(path: str | Path) -> object:  # VeraGridEngine.MultiCircuit
    """Load a MATPOWER .m file into a GridCal MultiCircuit.

    Classification: LOSSLESS — ``vge.open_file`` reads MATPOWER .m files
    natively.  Piecewise-linear generator costs are approximated as a polynomial
    fit (documented behaviour, not a silent data drop).

    Args:
        path: Path to a MATPOWER .m case file.

    Returns:
        A ``VeraGridEngine.MultiCircuit`` object.
    """
    import VeraGridEngine as vge

    return vge.open_file(str(path))
