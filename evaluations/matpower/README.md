# MATPOWER Evaluation

[MATPOWER](https://matpower.org/) — open-source MATLAB/GNU Octave package
for solving power flow and optimal power flow problems. The reference
implementation for many power systems algorithms.

## Prerequisites

```bash
sudo apt install octave
```

## Setup

```bash
bash setup.sh
```

This downloads MATPOWER 8.1 from GitHub releases, verifies the SHA256
checksum, and extracts to `matpower-8.1/`. The extracted directory is
git-ignored.

## Verify Installation

```bash
octave verify_install.m
```

## Data Loading

MATPOWER natively reads `.m` case files:

```matlab
mpc = loadcase('../../data/networks/case39.m');
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
