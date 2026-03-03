# PyPSA Evaluation

[PyPSA](https://pypsa.org/) (Python for Power System Analysis) — open-source
toolbox for simulating and optimizing modern power and energy systems.

## Setup

```bash
uv sync
```

### System Prerequisites (optional solvers)

For the full solver suite beyond HiGHS:

```bash
# GLPK
sudo apt install libglpk-dev

# Ipopt (via coinor)
sudo apt install coinor-libipopt-dev
```

These are optional — HiGHS is included as a pip dependency and sufficient for
most evaluation tests.

## Verify Installation

```bash
uv run python verify_install.py
```

## Data Loading

PyPSA does not natively read MATPOWER `.m` files. The evaluation uses
pandapower as an intermediary:

```python
import pandapower as pp
import pandapower.converter as pc

net_pp = pp.converter.from_mpc("../../data/networks/case39.m")
net_pypsa = pc.to_pypsa(net_pp)
```

## Results

Test outputs are organized by rubric dimension:

```
results/
├── gate/            # Pass/fail gate criteria
├── expressiveness/  # Modeling capability tests
├── extensibility/   # Custom component and integration tests
├── scalability/     # Performance benchmarks
├── accessibility/   # Documentation and API quality
├── maturity/        # Community and maintenance metrics
└── supply_chain/    # Dependency and license analysis
```
