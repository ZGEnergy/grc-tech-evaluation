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

## Dev Environment

All six tools run inside a single **devcontainer** that ships Python 3.12, uv,
Julia 1.10, and GNU Octave with all dependencies pre-installed.

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| [Docker](https://docs.docker.com/get-docker/) | Docker Desktop or Docker Engine |
| [VS Code](https://code.visualstudio.com/) + [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) | Recommended for interactive development |
| *or* [devcontainer CLI](https://github.com/devcontainers/cli) | `npm install -g @devcontainers/cli` — for headless/CI use |

### Building and Opening the Container

**VS Code (recommended):**

1. Open this repo in VS Code.
2. When prompted, click **Reopen in Container** (or run the command
   `Dev Containers: Reopen in Container` from the palette).
3. The first build takes a few minutes while it installs all runtimes and
   dependencies. Subsequent opens reuse the cached image and start in seconds.

**CLI:**

```bash
# Build and start the container (first time or after Dockerfile changes)
devcontainer up --workspace-folder .

# Open an interactive shell inside the running container
devcontainer exec --workspace-folder . bash

# Or run a one-off command
devcontainer exec --workspace-folder . uv run --project evaluations/pypsa python -c "import pypsa; print(pypsa.__version__)"
```

### What's Inside the Image

The Dockerfile (`.devcontainer/Dockerfile`) installs everything at build time
so the container is ready to use immediately:

- **Python 3.12** + **uv** — each Python tool (`pypsa`, `pandapower`,
  `gridcal`) has its own `.venv` created by `uv sync` during the build.
- **Julia 1.10.7** (pinned LTS) — Julia packages for `powermodels` and
  `powersimulations` are instantiated and precompiled during the build.
- **GNU Octave** — MATPOWER 8.1 is downloaded by `setup.sh` during the build.
### Verifying the Install

Smoke-test all six tools at once:

```bash
bash .devcontainer/validate.sh
```

Or verify a single tool:

```bash
# Python tools (pypsa, pandapower, gridcal)
cd evaluations/<tool> && uv run python verify_install.py

# Julia tools (powermodels, powersimulations)
cd evaluations/<tool> && julia --project=. verify_install.jl

# MATPOWER
cd evaluations/matpower && octave verify_install.m
```

### Day-to-Day Development

All work happens inside the container. Run scripts with the tool's own runtime:

```bash
# Run a Python evaluation script
cd evaluations/pypsa
uv run python results/gate/ac_power_flow.py

# Run a Julia evaluation script
cd evaluations/powermodels
julia --project=. results/gate/ac_power_flow.jl

# Run an Octave evaluation script
cd evaluations/matpower
octave results/gate/ac_power_flow.m

# Lint Python files
pre-commit run --all-files
```

If you need to add a Python dependency to a tool, update its `pyproject.toml`
and run `uv sync` inside that tool's directory — do not use `pip install`.
For Julia, edit `Project.toml` and run
`julia --project=. -e 'using Pkg; Pkg.instantiate()'`.

## Evaluation Protocol

See `evaluation_guides/` for the full rubric and test protocol:

- **Phase1_Evaluation_Rubric_v1.md** — Scoring criteria across seven dimensions
- **Phase1_Test_Protocol_v2.md** — Specific tests and acceptance criteria

Results for each tool are organized into subdirectories under
`evaluations/<tool>/results/` matching the rubric dimensions.
