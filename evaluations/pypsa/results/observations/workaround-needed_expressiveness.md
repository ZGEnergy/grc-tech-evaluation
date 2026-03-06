# Observation: workaround-needed (expressiveness)

## Source Tests
A-3, A-6, A-7, A-8

## Workarounds Cataloged

### 1. Manual Gencost Assignment (Stable)
- **Test:** A-3 (dcopf), A-5 (scuc), A-9 (scopf), A-10 (lossy_dcopf)
- **Issue:** `import_from_pypower_ppc()` ignores gencost
- **Workaround:** Parse `CaseFrames.gencost` and set `n.generators.marginal_cost` / `marginal_cost_quadratic` manually
- **Durability:** Stable — uses documented public API attributes
- **LOC impact:** +5 lines per test

### 2. Manual N-M Contingency Sweep (Stable)
- **Test:** A-7 (contingency_sweep)
- **Issue:** No built-in N-M sweep function
- **Workaround:** Implement sweep loop using `n.lines.active` flag + `n.lpf()` + NetworkX graph
- **Durability:** Stable — uses documented `active` attribute and standard `n.lpf()` / `n.graph()`
- **LOC impact:** +120 lines

### 3. Manual UC/ED Two-Stage Separation (Stable)
- **Test:** A-6 (sced)
- **Issue:** No built-in method to fix commitment and re-dispatch as LP
- **Workaround:** Set `committable=False`, encode commitment schedule via time-varying `p_min_pu` (status x min_stable) and `p_max_pu` (status x 1.0)
- **Durability:** Stable -- uses documented time-series override mechanism on public attributes
- **LOC impact:** +10 lines

### 4. Stochastic Optimization on Imported Networks (Fragile)
- **Test:** A-8 (stochastic_timeseries)
- **Issue:** `set_scenarios()` crashes with pypower-imported networks
- **Workaround options:**
  - Rebuild network via `n.add()` instead of `import_from_pypower_ppc()` (fragile — high effort, must replicate all import logic)
  - Use deterministic scenario loop (stable — loses joint optimization)
- **Durability:** Fragile — relies on PyPSA fixing the MultiIndex bug

### 5. Zero-Rated Branch Fix for OPF (Stable)
- **Test:** A-3 MEDIUM, A-4 MEDIUM, B-1 MEDIUM, B-7 MEDIUM
- **Issue:** ACTIVSg10k has 2,459 lines and 3 transformers with s_nom=0 (MATPOWER "unlimited" convention). PyPSA treats s_nom=0 as a 0 MW thermal limit, causing OPF infeasibility.
- **Workaround:** Set `n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0` and same for transformers
- **Durability:** Stable — this is a documented issue. PyPSA 2.0 will add an `overwrite_zero_s_nom` parameter to the importer.

### 6. Zero-Impedance Branch Fix for B Matrix (Stable)
- **Test:** A-3 MEDIUM, B-1 MEDIUM, B-7 MEDIUM, B-9 MEDIUM
- **Issue:** 3 transformers in ACTIVSg10k have x=0, causing singular B matrix in PTDF calculation and SVD failure in post-processing
- **Workaround:** Set `n.transformers.loc[n.transformers.x == 0, "x"] = 1e-4`
- **Durability:** Stable — documented edge case. Physical meaning: zero-impedance transformers are jumpers/bus-ties that should be modeled differently.
