# CLAUDE.md — grc-tech-evaluation

## Repo Overview

Standalone evaluation workspace for comparing six power-system modeling tools.
This is NOT an installable Python package — each `evaluations/<tool>/` directory
is an independent project with its own virtualenv and dependency set.

No ZGE internal dependencies. No connection to the trading platform repos.

## Directory Layout

- `evaluation_guides/` — Rubric and test protocol (read-only reference)
- `data/networks/` — Shared MATPOWER .m case files used by all tools
- `evaluations/<tool>/` — One directory per tool under evaluation
- `evaluations/<tool>/results/<dimension>/` — Test outputs organized by rubric dimension

## Per-Tool Setup

### Python tools (pypsa, pandapower, gridcal)

```bash
cd evaluations/<tool>
uv sync
uv run python verify_install.py
```

Do NOT use `pip install` — these are uv-managed projects.

### Julia tools (powermodels, powersimulations)

```bash
cd evaluations/<tool>
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. verify_install.jl
```

**Julia startup is slow by design.** `Pkg.instantiate()` compiles packages to native code on first run
(can take many minutes). Subsequent runs reuse the precompiled cache but still pay a 5–15s load
tax per invocation to deserialize it.

For repeated evaluation runs, stay in the REPL and `include()` your script instead of re-launching:

```julia
# start once
julia --project=.

# then inside the REPL, re-run without restart overhead:
julia> include("my_eval_script.jl")
```

### MATPOWER (Octave)

```bash
cd evaluations/matpower
bash setup.sh        # downloads MATPOWER 8.1
octave verify_install.m
```

## Conventions

- Python 3.12, Julia 1.10
- Ruff for Python linting (line-length = 100)
- Conventional commits enforced by pre-commit
- Each tool has isolated dependencies — no shared virtualenv
- Results go in `evaluations/<tool>/results/<dimension>/`
- The seven rubric dimensions: gate, expressiveness, extensibility, scalability, accessibility, maturity, supply_chain
