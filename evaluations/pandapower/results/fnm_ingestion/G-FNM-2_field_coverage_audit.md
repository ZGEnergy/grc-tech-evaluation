---
test_id: G-FNM-2
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "2941efff"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.79
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 427
solver: null
timestamp: 2026-03-14T04:00:00Z
---

# G-FNM-2: Field Coverage Audit vs Criticality Matrix

## Result: PASS

All 19 DCPF-critical fields are present in pandapower's data model after
MATPOWER/PYPOWER PPC ingestion. ACPF-critical coverage is 55.8% (29/52),
and informational coverage is approximately 27.6% (24/87).

## Approach

1. Loaded the FNM MATPOWER `.mat` case file into pandapower using the same
   `scipy.io.loadmat` + `from_ppc` approach as G-FNM-1.
2. For each of the 19 DCPF-critical fields defined in the field-criticality-matrix
   (v10), checked whether the field maps to an existing column or index in
   pandapower's DataFrame-based data model.
3. Computed coverage percentages per criticality tier.

## Output

### DCPF-Critical Fields (19/19 = 100%)

| # | Intermediate Field | pandapower Mapping | Present |
|---|-------------------|-------------------|---------|
| 1 | bus.I | `net.bus.index` (bus number as DataFrame index) | YES |
| 2 | bus.IDE | `net.bus['type']` (mapped from PPC bus_type) | YES |
| 3 | bus.VA | `net.res_bus['va_degree']` (populated after `rundcpp`) | YES |
| 4 | load.I | `net.load['bus']` | YES |
| 5 | load.STATUS | `net.load['in_service']` | YES |
| 6 | load.PL | `net.load['p_mw']` (total: 177,345 MW) | YES |
| 7 | gen.I | `net.gen['bus']`, `net.sgen['bus']`, `net.ext_grid['bus']` | YES |
| 8 | gen.PG | `net.gen['p_mw']`, `net.sgen['p_mw']` (total: 171,939 MW) | YES |
| 9 | gen.STAT | `net.gen['in_service']`, `net.sgen['in_service']`, `net.ext_grid['in_service']` | YES |
| 10 | branch.I | `net.line['from_bus']` | YES |
| 11 | branch.J | `net.line['to_bus']` | YES |
| 12 | branch.X | `net.line['x_ohm_per_km']` (converted from per-unit X) | YES |
| 13 | branch.ST | `net.line['in_service']` | YES |
| 14 | trafo.I | `net.trafo['hv_bus']`, `net.impedance['from_bus']` | YES |
| 15 | trafo.J | `net.trafo['lv_bus']`, `net.impedance['to_bus']` | YES |
| 16 | trafo.STAT | `net.trafo['in_service']`, `net.impedance['in_service']` | YES |
| 17 | trafo.X1_2 | `net.trafo['vk_percent']`, `net.impedance['xft_pu']` | YES |
| 18 | trafo.WINDV1 | `net.trafo['tap_pos']`; impedance elements embed tap in pu values | YES |
| 19 | trafo.ANG1 | `net.trafo['shift_degree']`; impedance elements embed shift in asymmetric pu | YES |

### ACPF-Critical Fields (29/52 = 55.8%)

Fields present: bus.BASKV (vn_kv), load.QL (q_mvar), load.IP/IQ/YP/YQ (const_*_percent),
gen.QT/QB (max/min_q_mvar), gen.VS (vm_pu), branch.R (r_ohm_per_km), branch.B (c_nf_per_km),
trafo.MAG1 (pfe_kw), trafo.MAG2 (i0_percent), trafo.R1_2 (vkr_percent/rft_pu),
trafo.SBASE1_2 (sn_mva), trafo.NOMV1/NOMV2 (vn_hv_kv/vn_lv_kv),
trafo.COD1 (tap_changer_type), trafo.RMA1/RMI1 (tap_max/tap_min),
trafo.NTP1 (tap_step_percent), trafo.RATA1 (sn_mva),
switched_shunt.I (bus), switched_shunt.STAT (in_service),
switched_shunt.BINIT/B1 (q_mvar), switched_shunt.N1 (max_step).

Missing fields (23): bus.VM (solved state only), gen.IREG (remote regulation bus),
branch.GI/BI/GJ/BJ (asymmetric line shunts), trafo.CW/CZ/CM (I/O codes consumed
during PPC conversion), trafo.ANG2 (winding 2 phase shift), trafo.CONT1 (controlled bus),
trafo.VMA1/VMI1 (control targets), area.ISW/PDES/PTOL (area interchange),
switched_shunt.MODSW/ADJM/VSWHI/VSWLO/SWREM/RMPCT/RMIDNT (control parameters).

### Coverage Summary

| Tier | Total | Present | Coverage |
|------|-------|---------|----------|
| DCPF-critical | 19 | 19 | 100.0% |
| ACPF-critical | 52 | 29 | 55.8% |
| Informational | 87 | ~24 | ~27.6% |
| Discardable | 0 | 0 | N/A |

### Notes on Coverage Gaps

The ACPF-critical gaps are inherent to the MATPOWER/PYPOWER PPC import path:
- **Transformer I/O codes (CW, CZ, CM):** Consumed during MATPOWER's conversion
  to the PPC branch format; the numerical values are not preserved but their
  effects are embedded in the converted impedance values.
- **Area interchange fields:** PPC format does not carry area interchange data
  (ISW, PDES, PTOL). pandapower has no separate area table.
- **Switched shunt control parameters:** PPC format aggregates shunts into the
  bus Bs column, losing discrete step information and control mode parameters.
- **Remote regulation (IREG):** Not carried through PPC conversion.
- **Asymmetric line shunts (GI, BI, GJ, BJ):** PPC branch format uses symmetric
  total charging B; asymmetric end shunts are not preserved.

These gaps do not affect DCPF accuracy. They would affect ACPF accuracy for
networks with significant switched shunt control, area interchange regulation,
or asymmetric line charging.

## Workarounds

None required beyond the G-FNM-1 ingestion workarounds (missing version field fix,
zero RATE_A fix). The field coverage audit itself requires no workarounds.

## Timing

- **Wall-clock:** 0.79 s (load + field audit)
- **Timing source:** measured (time.perf_counter)
- **Peak memory:** not measured
- **Solver iterations:** N/A
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/fnm_ingestion/test_g_fnm_2_field_coverage_audit.py`
