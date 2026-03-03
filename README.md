# GRC Tech Evaluation

Reproducible evaluation environments for six power-system modeling packages,
supporting the Contract FA714626C0006 technology assessment.

## Tools Under Evaluation

| Tool | Language | Directory |
|------|----------|-----------|
| [PyPSA](https://pypsa.org/) | Python | `evaluations/pypsa/` |
| [pandapower](https://www.pandapower.org/) | Python | `evaluations/pandapower/` |
| [GridCal](https://www.advancedgridinsights.com/gridcal) | Python | `evaluations/gridcal/` |
| [PowerModels.jl](https://lanl-ansi.github.io/PowerModels.jl/) | Julia | `evaluations/powermodels/` |
| [PowerSimulations.jl](https://nrel-sienna.github.io/PowerSimulations.jl/) | Julia | `evaluations/powersimulations/` |
| [MATPOWER](https://matpower.org/) | MATLAB/Octave | `evaluations/matpower/` |

## Directory Structure

```
grc-tech-evaluation/
├── evaluation_guides/          # Rubric and test protocol
│   ├── Phase1_Evaluation_Rubric_v1.md
│   └── Phase1_Test_Protocol_v2.md
├── data/
│   └── networks/               # Shared MATPOWER .m test cases
├── evaluations/
│   ├── pypsa/                  # Independent uv project
│   ├── pandapower/             # Independent uv project
│   ├── gridcal/                # Independent uv project
│   ├── powermodels/            # Julia project
│   ├── powersimulations/       # Julia project
│   └── matpower/               # Octave + download script
└── README.md
```

## Prerequisites

- **Python 3.12** — via pyenv, system package, or similar
- **[uv](https://docs.astral.sh/uv/)** — Python package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Julia 1.10** — via juliaup or direct download
- **GNU Octave** — for MATPOWER evaluation (`sudo apt install octave`)

## Quick Start

Each evaluation tool has its own isolated environment. To set up any Python tool:

```bash
cd evaluations/<tool>
uv sync
uv run python verify_install.py
```

For Julia tools:

```bash
cd evaluations/<tool>
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. verify_install.jl
```

For MATPOWER:

```bash
cd evaluations/matpower
bash setup.sh
octave verify_install.m
```

## Evaluation Protocol

See `evaluation_guides/` for the full rubric and test protocol:

- **Phase1_Evaluation_Rubric_v1.md** — Scoring criteria across seven dimensions
- **Phase1_Test_Protocol_v2.md** — Specific tests and acceptance criteria

Results for each tool are organized into subdirectories under
`evaluations/<tool>/results/` matching the rubric dimensions.
