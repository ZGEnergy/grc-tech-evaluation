# GRC Technology Evaluation — Phase 1

**[View the Interactive Report](https://zgenergy.github.io/grc-tech-evaluation/)**

Phase 1 technology evaluation comparing six open-source power-system modeling
tools against a six-criterion rubric. **PyPSA is the recommended tool for
Phase 2 development**, earning Strong in five of six criteria and holding the
top position across all sensitivity scenarios tested.

| Tool | Language | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|----------|:-:|:-:|:-:|:-:|:-:|:-:|
| **PyPSA** | Python | Strong | Strong | Adequate | Strong | Strong | Strong |
| PowerModels.jl | Julia | Adequate | Strong | Adequate | Adequate | Adequate | Adequate |
| PowerSimulations.jl | Julia | Adequate | Strong | Adequate | Weak | Adequate | Adequate |
| GridCal | Python | Adequate | Adequate | Adequate | Weak | Weak | Strong |
| pandapower | Python | Weak | Adequate | Weak | Adequate | Strong | Strong |
| MATPOWER\* | MATLAB | Adequate | Strong | Weak | Adequate | Adequate | Strong |

\*Reference benchmark only; excluded from ranking (requires MATLAB runtime).

## Repository Guide

### For Analysts

| Directory | Contents |
|-----------|----------|
| [`report/`](report/) | Interactive Docusaurus report site — the primary deliverable |
| [`deliverables/`](deliverables/) | Formal white paper (SOW Task 1.3) |
| [`evaluations/`](evaluations/) | Per-tool evaluation evidence, test code, and results |
| [`evaluation_guides/`](evaluation_guides/) | Rubric and test protocol defining all 39 tests |
| [`data/`](data/) | Shared test networks (MATPOWER cases), augmented time series, FNM data |
| [`phase2-research/`](phase2-research/) | State estimation investigation (Phase 2 groundwork) |

### For Developers

| Directory | Contents |
|-----------|----------|
| `.devcontainer/` | Docker development environment (Python 3.12, Julia 1.10, Octave) |
| `.github/` | CI/CD workflows |
| `data/validation/` | Data quality scripts (schema validation, manifest generation) |

## Tools Evaluated

Each tool has an independent environment under `evaluations/<tool>/`:

| Tool | Language | Environment |
|------|----------|-------------|
| [PyPSA](https://pypsa.org/) | Python | `uv sync` |
| [pandapower](https://www.pandapower.org/) | Python | `uv sync` |
| [GridCal](https://www.advancedgridinsights.com/gridcal) | Python | `uv sync` |
| [PowerModels.jl](https://lanl-ansi.github.io/PowerModels.jl/) | Julia | `Pkg.instantiate()` |
| [PowerSimulations.jl](https://nrel-sienna.github.io/PowerSimulations.jl/) | Julia | `Pkg.instantiate()` |
| [MATPOWER](https://matpower.org/) | MATLAB/Octave | `bash setup.sh` |

## Evaluation Protocol

The evaluation uses a standardized rubric and test protocol:

- **[Phase1_Evaluation_Rubric.md](evaluation_guides/Phase1_Evaluation_Rubric.md)** —
  Scoring criteria across six dimensions with tier definitions
- **[Phase1_Test_Protocol.md](evaluation_guides/Phase1_Test_Protocol.md)** —
  39 specific tests with acceptance criteria

Test networks: IEEE 39-bus, ACTIVSg 2,000-bus, and ACTIVSg 10,000-bus
synthetic cases from `data/networks/`.

Results for each tool are in `evaluations/<tool>/results/` organized by rubric
dimension, with a `synthesis.md` summarizing findings.

## Development Environment

All tools run inside a single devcontainer. See
[`.devcontainer/`](.devcontainer/) for setup instructions.

```bash
# Build and open
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . bash

# Verify all tools
bash .devcontainer/validate.sh

# Lint
pre-commit run --all-files
```

### Running evaluation scripts

Each tool has its own virtualenv — **do not use bare `python`** from the
container shell, as it points to the system Python which has no packages
installed. Always `cd` into the tool directory and use `uv run` (Python tools)
or `julia --project=.` (Julia tools):

```bash
# Python tools (pypsa, pandapower, gridcal)
cd /workspace/evaluations/pypsa
uv run python tests/expressiveness/test_a1_dcpf.py
uv run pytest tests/                     # run full test suite

# Julia tools (powermodels, powersimulations)
cd /workspace/evaluations/powermodels
julia --project=. tests/runtests.jl

# MATPOWER (Octave)
cd /workspace/evaluations/matpower
octave tests/run_tests.m
```
