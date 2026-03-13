# pypsa — Research: API & Formulations

> **Note:** The dedicated API research agent stalled on a WebFetch call and did not complete.
> Key API findings are consolidated here from the Version Capabilities and Extensions research,
> which together provide comprehensive coverage of this focus area.

## Key Findings

- **Installed version:** 1.1.2 (latest as of 2026-02-23)
- **Primary power flow entry points:** `n.pf()` (Newton-Raphson AC PF), `n.lpf()` (linear/DC PF), `n.lpf_contingency()` (N-1 DC contingency)
- **Optimization entry point:** `n.optimize()` (unified LP/MILP/UC via linopy + HiGHS); supports DC OPF, SCUC, SCED, multi-period, BESS, rolling horizon
- **AC OPF:** `n.optimize.optimize_and_run_non_linear_powerflow()` — requires Ipopt; **Ipopt not installed in devcontainer → AC OPF tests will fail with `unsupported_in_installed_version`**
- **Data model:** All components (Bus, Line, Transformer, Generator, StorageUnit, Store, Load, Link, ShuntImpedance) stored as pandas DataFrames in `n.c.<component>.static` (static) and `n.c.<component>.dynamic` (time-series)
- **Result access:** `n.buses_t.v_ang`, `n.buses_t.marginal_price`, `n.lines_t.p0`, etc. via `_t` accessors
- **Custom constraints:** `extra_functionality(n, snapshots)` callable passed to `n.optimize()`, called after model build, before solve — full linopy model accessible as `n.model`
- **PTDF:** `sub_network.calculate_PTDF()` → `sub_network.PTDF` (dense numpy array, branches × buses)
- **Solver interface:** `solver_name` and `solver_options` kwargs on `n.optimize()`; only HiGHS available
- **Pre-v1.0 API removed:** `n.madd()`, `n.lopf()`, `n.iplot()` all gone — legacy scripts must be updated

## Detailed Notes

### Power Flow API

| Method | Description | Key Parameters |
|--------|-------------|----------------|
| `n.pf(snapshots)` | Full Newton-Raphson AC PF | `x_tol=1e-6`, `distribute_slack`, `slack_weights` |
| `n.lpf(snapshots)` | Linear (DC) PF | `skip_pre` |
| `n.lpf_contingency(snapshots, branch_outages)` | N-1 DC contingency sweep | `branch_outages` = list of branch names |
| `n.sub_networks.c.calculate_PTDF()` | PTDF matrix per subnetwork | Stored at `sub_network.PTDF` |

Results allocated to `n.buses_t`, `n.lines_t`, `n.transformers_t` after solve.

### Optimization API

```python
# Basic DC OPF
status, condition = n.optimize(solver_name="highs")

# Unit commitment (linearized)
n.optimize(linearized_unit_commitment=True, solver_name="highs")

# Multi-period time-series
n.optimize(snapshots=n.snapshots, solver_name="highs")

# Custom constraints
def extra(n, snapshots):
    m = n.model
    # add linopy constraints here
n.optimize(extra_functionality=extra, solver_name="highs")

# Security-constrained OPF
n.optimize.optimize_security_constrained(snapshots, branch_outages=outage_list)
```

### Data Model

- **Network components** are registered via `pypsa.components.types` and stored as `ComponentsStore`
- **Static data:** `n.<component_name>` or `n.c.<component_name>.static` (DataFrame, one row per asset)
- **Time-series data:** `n.<component_name>_t` or `n.c.<component_name>.dynamic` (dict of DataFrames)
- **Network object:** `pypsa.Network(import_name=None)` — empty or loaded from file

### Input/Output Formats

| Format | Read | Write | Notes |
|--------|------|-------|-------|
| netCDF4 | yes | yes | Recommended (xarray-backed) |
| CSV folder | yes | yes | Human-readable |
| HDF5 | yes | yes | Legacy |
| PyPower/MATPOWER | yes (via `import_from_pypower_ppc`) | no | Type-4 bus crash; no gencost |
| pandapower | yes (beta, `import_from_pandapower_net`) | no | Beta quality |

### Solver Interface

Only HiGHS is available in the devcontainer (via `highspy 1.13.1`). Ipopt is absent.
Gurobi, CPLEX, MOSEK are supported by linopy but not installed.

## Sources

1. Version Capabilities research: `evaluations/pypsa/results/research-version.md`
2. Extensions & Architecture research: `evaluations/pypsa/results/research-extensions.md`
3. PyPSA source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/`
4. PyPSA docs: https://pypsa.readthedocs.io/en/latest/

## Gaps and Uncertainties

- Detailed ACPF convergence behavior (tolerance handling, non-convergence codes) — verify during A-2 testing
- Exact `buses_t.marginal_price` units (MW vs pu) — verify during OPF testing (unit-mismatch watch)
- `n.statistics()` output format — verify during expressiveness testing
