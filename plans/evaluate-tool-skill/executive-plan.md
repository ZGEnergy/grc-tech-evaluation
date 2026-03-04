# Executive Plan: `/evaluate-tool` Skill

## Overview

The `/evaluate-tool` skill automates Phase 1 evaluation of power-system modeling tools
under contract FA714626C0006. It evaluates one tool at a time across 6 rubric criteria
(45 tests per tool) using a data-driven state machine that adapts to the canonical
evaluation guides.

## Design Principles

### Config Generation, Not Config Authoring

The evaluation guides (`Phase1_Evaluation_Rubric_v1.md` and `Phase1_Test_Protocol_v2.md`)
are the single source of truth. A **config-generator agent** reads them and produces
`eval-config.yaml` containing dimensions, test IDs, network tiers, dependencies,
observation tags, and the execution DAG. The generated config is saved for human review
before the evaluation proceeds.

This means: when the rubric or protocol changes, re-running CONFIGURE regenerates the
config. No prompt files need editing.

### Three Agent Archetypes

Instead of per-suite prompt files, three archetypal agent templates handle all dimensions:

| Archetype | Handles | Method |
|-----------|---------|--------|
| `code-evaluator` | Expressiveness, Extensibility, Scalability | Writes and runs test scripts |
| `audit-evaluator` | Accessibility, Maturity, Supply Chain | Performs repo/doc/ecosystem audits |
| `gate-evaluator` | Gate tests | Pass/fail network ingestion with halt semantics |

Each is parameterized by dimension, test IDs, network tier, and reference files.

### Observation Routing

Dimensions declare what observation tags they emit/consume in the config. Findings
flow between agents via tagged observation files — no hard-coded agent-to-agent wiring.

## State Machine

```
CONFIGURE → RESEARCH → GATE → EVALUATE → SYNTHESIZE
```

1. **CONFIGURE** — Generate eval-config.yaml from guides, present for review
2. **RESEARCH** — 3 parallel research agents gather tool context
3. **GATE** — Gate tests with halt-on-failure (G-1 fail = excluded)
4. **EVALUATE** — Execute DAG: TINY → SMALL → MEDIUM, code + audit agents in parallel
5. **SYNTHESIZE** — Compile per-criterion summaries with grade recommendations

## File Structure

```
.claude/skills/evaluate-tool/
├── SKILL.md                          # Orchestrator state machine
├── prompts/
│   ├── config-generator-prompt.md    # Reads guides → eval-config.yaml
│   ├── research-prompt.md            # Parameterized by research_focus
│   ├── gate-evaluator-prompt.md      # Gate tests with halt-on-failure
│   ├── code-evaluator-prompt.md      # Functional test suites
│   ├── audit-evaluator-prompt.md     # Audit suites
│   └── synthesis-prompt.md           # Compiles results → synthesis report
├── references/
│   ├── handoff-schema.md             # Tier/session handoff format
│   ├── observation-schema.md         # Tagged observation file format
│   ├── result-template.md            # Per-test result file template
│   ├── synthesis-template.md         # Final synthesis output template
│   ├── solver-config.md              # Normalized solver settings
│   ├── convergence-protocol.md       # Flat start → DC warm start fallback
│   ├── workaround-classification.md  # Stable/fragile/blocking definitions
│   └── test-script-conventions.md    # run() convention, script format
└── templates/
    ├── conftest.py                   # pytest fixtures for Python tools
    ├── runtests.jl                   # Julia test runner
    └── run_tests.m                   # Octave test runner
```

## Invocation

```
/evaluate-tool pypsa
/evaluate-tool pandapower
/evaluate-tool gridcal
/evaluate-tool powermodels
/evaluate-tool powersimulations
/evaluate-tool matpower
```

## Outputs

Per tool, the skill produces:
- `evaluations/<tool>/results/eval-config.yaml` — Generated evaluation config
- `evaluations/<tool>/results/research-context.md` — Merged research findings
- `evaluations/<tool>/results/<dimension>/<test_id>.md` — Per-test result files
- `evaluations/<tool>/results/observations/` — Cross-cutting observation files
- `evaluations/<tool>/tests/<dimension>/` — Test scripts (code evaluator)
- `evaluations/<tool>/results/synthesis.md` — Final synthesis with grade recommendations
