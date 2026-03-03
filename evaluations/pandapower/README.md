# pandapower Evaluation

[pandapower](https://www.pandapower.org/) — open-source tool for automated
static power system modeling, analysis, and optimization with a focus on
distribution networks.

## Setup

```bash
uv sync
```

No additional system dependencies required. The `[performance]` extra
installs optional acceleration libraries.

## Verify Installation

```bash
uv run python verify_install.py
```

## Data Loading

pandapower natively reads MATPOWER `.m` files:

```python
import pandapower as pp

net = pp.converter.from_mpc("../../data/networks/case39.m")
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
