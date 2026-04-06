# Data

Shared test data consumed by all six evaluation environments.

## Directory Structure

| Directory | Contents |
|-----------|----------|
| `networks/` | MATPOWER `.m` case files (IEEE 39-bus, ACTIVSg 2k, ACTIVSg 10k) |
| `fnm/` | Foundational Network Model — parsed hydro network data with intermediate schemas |
| `timeseries/` | Augmented time-series data (load profiles, gen costs, reserves, scenarios) |
| `reference/` | Reference data (RTS-GMLC technology classes, calibration outputs) |
| `scripts/` | Data augmentation pipeline (generates timeseries/ and reference/ outputs) |
| `validation/` | Data quality scripts (schema validation, manifest generation, doc generation) |
| `whitepaper_proposal.md` | SOW contract proposal document |

## Data Flow

```
networks/ (raw MATPOWER cases)
    │
    ├── scripts/ (augmentation pipeline) ──→ timeseries/ + reference/
    │
    └── fnm/ (parsed network model) ──→ fnm/reference/ (cleaned data + DCPF solutions)
```

The `Makefile` orchestrates the augmentation pipeline stages in dependency order.

## Important

`networks/` and `timeseries/` paths are hard-coded in evaluation test suites
across all six tools. **Do not move or rename these directories.**
