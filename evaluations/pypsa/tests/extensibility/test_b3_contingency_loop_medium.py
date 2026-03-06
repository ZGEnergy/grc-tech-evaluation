"""B-3 (contingency_loop) -- N-1 DCPF loop on ACTIVSg10k (MEDIUM), 100-branch subset."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg10k.m")
N_CONTINGENCIES = 100


def load_network(filepath):
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    return n


def run():
    errors = []
    workarounds = []
    details = {}
    try:
        n = load_network(CASE_FILE)
        details["total_lines"] = len(n.lines)
        details["total_transformers"] = len(n.transformers)
        contingency_lines = list(n.lines.index[:N_CONTINGENCIES])
        details["contingency_count"] = len(contingency_lines)
        n.lpf()
        base_line_flows = n.lines_t.p0.iloc[0].copy()
        s_nom = n.lines.s_nom.replace(0, np.inf)
        base_max_loading = float((base_line_flows.abs() / s_nom).max())
        details["base_max_loading"] = round(base_max_loading, 4)

        t0 = time.perf_counter()
        results = []
        failed_cases = []
        for branch_name in contingency_lines:
            orig_active = n.lines.loc[branch_name, "active"]
            n.lines.loc[branch_name, "active"] = False
            try:
                n.lpf()
                line_flows = n.lines_t.p0.iloc[0]
                active_mask = n.lines["active"] & (n.lines.s_nom > 0)
                loading = (line_flows.abs() / n.lines.s_nom)[active_mask]
                max_loading = float(loading.max()) if len(loading) > 0 else 0.0
                max_branch = loading.idxmax() if len(loading) > 0 else "N/A"
                results.append(
                    {
                        "contingency": branch_name,
                        "max_loading": round(max_loading, 4),
                        "max_loading_branch": max_branch,
                    }
                )
            except Exception as e:
                failed_cases.append({"contingency": branch_name, "error": str(e)})
            n.lines.loc[branch_name, "active"] = orig_active

        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["contingencies_run"] = len(results)
        details["contingencies_failed"] = len(failed_cases)
        details["per_contingency_avg_seconds"] = round(wall_clock / N_CONTINGENCIES, 4)
        if results:
            worst = max(results, key=lambda r: r["max_loading"])
            details["worst_contingency"] = worst
            details["top_5_contingencies"] = sorted(
                results, key=lambda r: r["max_loading"], reverse=True
            )[:5]
        details["api_method"] = "Toggle n.lines.loc[name, 'active'], call n.lpf(), restore."
        details["loc"] = 20
        assert len(results) > 0
        status = "PASS"
    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
    return {
        "test_id": "B-3",
        "slug": "contingency_loop",
        "tier": "MEDIUM",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
