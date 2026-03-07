"""
Test A-9: Solve DC OPF with N-1 contingency flow constraints embedded in the optimization

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Solves. Base-case dispatch respects all contingency flow limits simultaneously.
    Dispatch and cost differ from unconstrained DC OPF (A-3). Contingency constraints are part
    of the optimization, not checked post-hoc.
Tool: pandapower v3.4.0

APPROACH: pandapower has NO native SCOPF. Attempt to use PYPOWER userfcn callback
system to add N-1 contingency constraints via PTDF/LODF matrices as linear constraints
in the OPF formulation. This is a significant workaround.
"""

import json
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Attempt SCOPF test via PTDF/LODF workaround and document results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)

        # Count branches (lines + trafos)
        n_lines = len(net.line)
        n_trafos = len(net.trafo)
        n_branches = n_lines + n_trafos
        results["details"]["n_lines"] = n_lines
        results["details"]["n_trafos"] = n_trafos
        results["details"]["n_branches_contingency_set"] = n_branches

        # 2. First solve base DC OPF (for comparison with A-3 results)
        pp.rundcopp(net)
        if not net["OPF_converged"]:
            results["errors"].append("Base DC OPF did not converge")
            return results

        base_objective = float(net.res_cost)
        base_dispatch = net.res_gen["p_mw"].copy()
        results["details"]["base_dcopf_objective"] = base_objective
        results["details"]["base_dcopf_dispatch_mw"] = base_dispatch.to_dict()

        # 3. Attempt SCOPF via PYPOWER userfcn with PTDF/LODF
        # pandapower has no native SCOPF. The PYPOWER userfcn system is the only
        # path to add custom linear constraints to the OPF.

        # 3a. Try to compute PTDF
        try:
            from pandapower.pypower.makePTDF import makePTDF

            results["details"]["ptdf_available"] = True
        except ImportError:
            results["details"]["ptdf_available"] = False
            results["errors"].append("makePTDF not importable from pandapower.pypower")
            return results

        # 3b. Get internal PYPOWER case structure
        # Need to run a DC power flow first to populate _ppc
        pp.rundcpp(net)
        ppc = net._ppc

        from pandapower.pypower.idx_brch import BR_STATUS, F_BUS, RATE_A, T_BUS
        from pandapower.pypower.idx_bus import BUS_TYPE, REF

        baseMVA = ppc["baseMVA"]
        bus = ppc["bus"]
        branch = ppc["branch"]
        n_br = branch.shape[0]

        # Find slack bus
        slack_idx = np.where(bus[:, BUS_TYPE] == REF)[0]
        results["details"]["slack_bus_internal"] = int(slack_idx[0]) if len(slack_idx) > 0 else None

        # 3c. Compute PTDF matrix
        ptdf = makePTDF(baseMVA, bus, branch, slack_idx[0] if len(slack_idx) > 0 else 0)
        results["details"]["ptdf_shape"] = list(ptdf.shape)

        # 3d. Compute LODF matrix from PTDF
        # LODF(l, k) = PTDF(l, from_k) - PTDF(l, to_k)) / (1 - PTDF(k, from_k) + PTDF(k, to_k))
        # This gives the line outage distribution factor: change in flow on line l
        # when line k is outaged
        lodf = np.zeros((n_br, n_br))
        for k in range(n_br):
            if branch[k, BR_STATUS] == 0:
                continue
            f_bus_k = int(branch[k, F_BUS])
            t_bus_k = int(branch[k, T_BUS])
            denom = 1.0 - (ptdf[k, f_bus_k] - ptdf[k, t_bus_k])
            if abs(denom) < 1e-10:
                # Radial branch - outage disconnects part of network
                lodf[:, k] = np.inf
            else:
                for br in range(n_br):
                    lodf[br, k] = (ptdf[br, f_bus_k] - ptdf[br, t_bus_k]) / denom
                lodf[k, k] = -1.0  # Convention

        results["details"]["lodf_computed"] = True
        results["details"]["lodf_shape"] = list(lodf.shape)

        # 3e. Now try to inject these as constraints into the OPF
        # pandapower's rundcopp() calls PYPOWER's opf(), which supports userfcn
        # callbacks. However, pandapower does NOT expose an API to pass userfcn
        # to rundcopp(). The userfcn system requires modifying the ppc dict before
        # passing it to the solver.

        # Try the internal PYPOWER OPF directly
        try:
            from pandapower.pypower.opf import opf as pypower_opf  # noqa: F401

            results["details"]["pypower_opf_importable"] = True
        except ImportError:
            results["details"]["pypower_opf_importable"] = False

        # Check for userfcn support
        try:
            from pandapower.pypower.add_userfcn import add_userfcn  # noqa: F401

            results["details"]["add_userfcn_importable"] = True
        except ImportError:
            try:
                # Try alternate import path
                from pandapower.pypower import add_userfcn as auf_module  # noqa: F401

                results["details"]["add_userfcn_importable"] = True
            except ImportError:
                results["details"]["add_userfcn_importable"] = False

        # Even if userfcn is importable, using it requires:
        # 1. Building the PYPOWER case (ppc) manually from pandapower net
        # 2. Adding userfcn callbacks to inject A*x <= b constraints
        # 3. Running PYPOWER opf directly (bypassing pandapower API)
        # 4. Mapping results back to pandapower format
        # This is a very fragile workaround.

        # 3f. Try direct PYPOWER OPF with contingency constraints
        # Formulate: for each contingency k (outaging branch k),
        # post-contingency flow on line l = base flow on l + LODF(l,k) * base flow on k
        # Must respect: |post_contingency_flow_l| <= RATE_A_l for all l, k

        # Get branch ratings
        ratings = branch[:, RATE_A].copy()
        # Replace zero ratings with large number (unconstrained)
        ratings[ratings == 0] = 9999.0
        results["details"]["branches_with_ratings"] = int(np.sum(branch[:, RATE_A] > 0))
        results["details"]["branches_without_ratings"] = int(np.sum(branch[:, RATE_A] == 0))

        # The fundamental problem: pandapower's rundcopp() does not accept custom
        # linear constraints. The PYPOWER userfcn system exists in theory but
        # pandapower does not expose it, and using it directly means bypassing
        # pandapower entirely.

        results["details"]["scopf_native_support"] = False
        results["details"]["scopf_via_userfcn_feasible"] = False
        results["details"]["scopf_assessment"] = (
            "pandapower has no native SCOPF. The theoretical path via PYPOWER userfcn "
            "callbacks exists but: (1) pandapower does not expose userfcn to rundcopp(), "
            "(2) using PYPOWER opf directly bypasses pandapower entirely (must manually "
            "construct ppc, run opf, map results back), (3) the userfcn API for adding "
            "linear constraints (A*x <= b) requires understanding PYPOWER's internal "
            "variable ordering. This would be a very fragile workaround requiring deep "
            "knowledge of PYPOWER internals."
        )

        # 3g. Alternative: iterative post-hoc approach (NOT true SCOPF)
        # Run DC OPF, check contingencies, add binding constraints, re-solve.
        # This does not meet the pass condition (constraints must be embedded in
        # optimization, not checked post-hoc).
        results["details"]["iterative_approach_note"] = (
            "An iterative cutting-plane approach (solve OPF, check contingencies, "
            "add violated constraints, re-solve) could approximate SCOPF but is NOT "
            "true SCOPF as specified in the pass condition. pandapower's contingency "
            "analysis (run_contingency) is screening only, not optimization."
        )

        # 4. Document contingency screening capability (what pandapower CAN do)
        try:
            from pandapower.contingency import run_contingency  # noqa: F401

            results["details"]["contingency_screening_available"] = True
            results["details"]["contingency_note"] = (
                "pandapower.contingency.run_contingency exists for N-1 contingency "
                "screening (running PF for each contingency). This is post-hoc "
                "analysis, not embedded optimization constraints."
            )
        except ImportError:
            results["details"]["contingency_screening_available"] = False

        # FAIL: SCOPF not achievable
        results["errors"].append(
            "pandapower does not support SCOPF (security-constrained OPF). "
            "No mechanism exists to embed N-1 contingency flow constraints "
            "in the optimization. The PYPOWER userfcn path is theoretically "
            "possible but extremely fragile and requires bypassing pandapower entirely."
        )

        results["workarounds"].append(
            "SCOPF via PYPOWER userfcn is theoretically possible but classified as "
            "blocking: it requires bypassing pandapower's API entirely, manually "
            "constructing PYPOWER ppc structures, understanding internal variable "
            "ordering, and mapping results back. This is not a viable workaround."
        )

        results["status"] = "fail"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
