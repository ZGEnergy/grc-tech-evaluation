# GridCal Evaluation

[GridCal](https://www.advancedgridinsights.com/gridcal) — cross-platform
power systems solver with a focus on research and consulting applications.
This evaluation uses the `GridCalEngine` package (computational engine without GUI).

## Setup

```bash
uv sync
```

No additional system dependencies required.

## Verify Installation

```bash
uv run python verify_install.py
```

## Data Loading

GridCalEngine reads MATPOWER `.m` files via `open_file`:

```python
import GridCalEngine as gce

grid = gce.open_file("../../data/networks/case39.m")
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
