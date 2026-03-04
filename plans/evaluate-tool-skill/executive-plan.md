# Executive Plan: `/evaluate-tool` Skill

## Context

Contract  requires evaluating 6 power-system modeling tools (PyPSA,
pandapower, GridCal, PowerModels.jl, PowerSimulations.jl, MATPOWER) across 6 rubric
criteria and 1 gate criterion. The protocol specifies 45 tests per tool organized into
7 suites (G, A--F), run against 3 synthetic reference networks (TINY/SMALL/MEDIUM).

The `/evaluate-tool` skill automates this as a Claude Code skill that orchestrates
sub-agents to research, test, and synthesize findings for one tool at a time.

## Problem Statement

Running 45 tests per tool manually is slow and inconsistent. But hard-coding the
evaluation logic into the skill creates a maintenance burden: every rubric revision
requires rewriting prompts and orchestration. We need an approach that is
**methodology-resilient** -- the skill adapts when the rubric changes without
rewriting prompts or the orchestrator.

## Design Decisions

### 1. Config generation, not config authoring

The evaluation guides (`Phase1_Evaluation_Rubric_v1.md` and
`Phase1_Test_Protocol_v2.md`) are the single source of truth. A config-generator
agent reads them and produces `eval-config.yaml` containing:

- Dimensions, test IDs, network tiers, pass conditions
- Test-to-tier mapping (functional network vs grade network)
- Test dependencies (extracted from prose like "Take DC OPF dispatch from A-3")
- Observation tags and routing (cross-cutting quality signals)
- Execution DAG with parallelism opportunities

The generated config is written to disk and presented to the user for review before
evaluation proceeds. When the rubric changes, re-running CONFIGURE regenerates the
config. No prompt files need editing.

### 2. Three agent archetypes, not per-suite prompts

Instead of 10+ prompt files (one per suite x tier), three archetypal agent templates
handle all dimensions:

| Archetype | Prompt | Handles | Method |
|-----------|--------|---------|--------|
| `gate-evaluator` | `gate-evaluator-prompt.md` | Suite G | Pass/fail network ingestion, halt-on-failure |
| `code-evaluator` | `code-evaluator-prompt.md` | Suites A, B, C | Writes test scripts, runs in devcontainer, records results |
| `audit-evaluator` | `audit-evaluator-prompt.md` | Suites D, E, F | Repo/doc/ecosystem audits, web research |

Each template is parameterized by `{{dimension}}`, `{{test_ids}}`,
`{{network_tier}}`, `{{reference_files}}`, `{{observation_tags}}`, and
`{{consumed_observations}}`. The orchestrator reads the config to determine which
archetype handles each dimension and which variables to inject.

### 3. Observation routing via tags

Dimensions declare what observation tags they emit/consume in the config. Any
dimension that emits `api-friction` makes those observations available to any
dimension that consumes it (accessibility in this case). The orchestrator collects
observation files between DAG steps and passes consumed observations to downstream
agents. No hard-coded agent-to-agent wiring.

### 4. Worktree isolation

The orchestrator enters a git worktree (`eval/<tool_name>`) before any evaluation
work begins. All sub-agents inherit the worktree working directory automatically.
This prevents concurrent tool evaluations from interfering with each other or with
work on `main`. Results are committed to the worktree branch and merged via PR.

### 5. Devcontainer execution

All code execution (Python, Julia, Octave) happens inside the devcontainer via
`devcontainer exec --workspace-folder . <command>`. The skill never runs test code
on the host. This matches the repo-level convention in CLAUDE.md.

### 6. Methodology-specific details in reference files

Solver settings, convergence protocols, workaround classification rules, and test
script conventions live in `references/` files, not in prompt templates. This
separates the evaluation methodology from the agent orchestration logic. Reference
files can be updated independently of prompts.

## State Machine

```
[worktree] → CONFIGURE → RESEARCH → GATE → EVALUATE → SYNTHESIZE
```

### Worktree (pre-state)

Enter worktree `eval/<tool_name>` via `EnterWorktree`. Skip if resuming from an
existing worktree.

### CONFIGURE

1. Dispatch config-generator agent with rubric + protocol paths
2. Agent reads both documents, extracts all structure, writes `eval-config.yaml`
3. Present config summary to user for approval
4. Write `.progress.yaml` checkpoint

### RESEARCH

1. Dispatch 3 research agents in parallel:
   - API & Formulations (entry points, data model, solver interfaces)
   - Extensions & Architecture (plugin APIs, graph access, interoperability)
   - Limitations & Ecosystem (known issues, community, releases, docs)
2. Merge into `research-context.md`
3. Flag thin research output as an Accessibility finding

### GATE

1. Dispatch gate-evaluator with G-1, G-2, G-3
2. Post-import network audit (counts, NaN checks, cost data, slack bus)
3. Halt semantics:
   - G-1 fail: tool excluded, evaluation stops
   - G-2 fail: `scale_cap: TINY` (functional tests only)
   - G-3 fail: `scale_cap: SMALL` (no MEDIUM tests)
   - All pass: `scale_cap: MEDIUM`

### EVALUATE

1. Read execution DAG from config
2. For each DAG step, dispatch agents in parallel per step's dimensions
3. Each agent receives: dimension, test IDs, tier, research context, reference files,
   consumed observations
4. Agents produce: result files (per test ID), observation files (tagged), test
   scripts (code evaluator)
5. Checkpoint after each DAG step

Typical DAG flow (but actual steps come from config):

| Step | What | Agents |
|------|------|--------|
| 1 | TINY functional tests | code-evaluator x3 (expressiveness, extensibility, scalability) |
| 2 | Audit dimensions | audit-evaluator x3 (accessibility, maturity, supply_chain) |
| 3 | SMALL grade tests | code-evaluator (A-5, A-6, A-8, B-4, C-4, C-6) |
| 4 | MEDIUM grade tests | code-evaluator (remaining A, B, C tests, C-7 solver swap) |

### SYNTHESIZE

1. Dispatch synthesis agent with all result + observation files
2. Produces per-criterion summary with:
   - Grade recommendation (9-point scale) with confidence level
   - Evidence table linking grades to specific test IDs
   - Workaround inventory with durability classes
   - Items flagged for human spot-check (A-7, A-8, qualified passes)
3. Remind user results are on worktree branch

## File Inventory (19 files)

```
.claude/skills/evaluate-tool/
├── SKILL.md                                    # Orchestrator state machine
├── prompts/
│   ├── config-generator-prompt.md              # Reads eval guides → eval-config.yaml
│   ├── research-prompt.md                      # Parameterized by {{research_focus}}
│   ├── gate-evaluator-prompt.md                # Gate tests, halt-on-failure
│   ├── code-evaluator-prompt.md                # Functional test suites (A, B, C)
│   ├── audit-evaluator-prompt.md               # Audit suites (D, E, F)
│   └── synthesis-prompt.md                     # Compiles all results → synthesis report
├── references/
│   ├── handoff-schema.md                       # YAML frontmatter + structured markdown
│   ├── observation-schema.md                   # Tagged observation file format + tag taxonomy
│   ├── result-template.md                      # Per-test result file template (code + audit)
│   ├── synthesis-template.md                   # Final synthesis output template
│   ├── solver-config.md                        # HiGHS, SCIP, Ipopt, GLPK normalized settings
│   ├── convergence-protocol.md                 # Flat start → DC warm start fallback
│   ├── workaround-classification.md            # Stable/fragile/blocking definitions + decision tree
│   └── test-script-conventions.md              # run() convention, self-documenting header, JSON output
└── templates/
    ├── conftest.py                             # pytest fixtures, network paths, result writers
    ├── runtests.jl                             # Julia test runner with dimension/test discovery
    └── run_tests.m                             # Octave test runner with dimension/test discovery
```

## Evaluation Outputs (per tool)

```
evaluations/<tool>/
├── results/
│   ├── eval-config.yaml                        # Generated evaluation config
│   ├── .progress.yaml                          # Checkpoint for resume
│   ├── research-context.md                     # Merged research findings
│   ├── gate/G-1.md, G-2.md, G-3.md            # Gate results
│   ├── expressiveness/A-1.md ... A-8.md        # Suite A results
│   ├── extensibility/B-1.md ... B-6.md         # Suite B results
│   ├── scalability/C-1.md ... C-7.md           # Suite C results
│   ├── accessibility/D-1.md ... D-5.md         # Suite D results
│   ├── maturity/E-1.md ... E-7.md              # Suite E results
│   ├── supply_chain/F-1.md ... F-9.md          # Suite F results
│   ├── observations/                           # Cross-cutting tagged observations
│   └── synthesis.md                            # Final per-criterion synthesis
└── tests/
    ├── expressiveness/test_a1.py ... test_a8.py
    ├── extensibility/test_b1.py ... test_b6.py
    └── scalability/test_c1.py ... test_c7.py
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

## Resumability

The `.progress.yaml` file tracks:

- `tool`: which tool is being evaluated
- `completed_states`: which states have finished
- `current_state`: where to resume
- `completed_dag_steps`: which EVALUATE steps are done
- `scale_cap`: TINY/SMALL/MEDIUM (set by GATE)

On session restart, the orchestrator reads `.progress.yaml` and resumes from the
last completed state. Sub-agents that were in-flight when the session ended are
re-dispatched.

If context limits are reached mid-evaluation, the orchestrator writes a
`.session-handoff.md` file (per `handoff-schema.md`) containing full state machine
position, completed artifacts, and next action.

## Observation Tag Routing

| Tag | Emitted by | Consumed by | Signal |
|-----|-----------|-------------|--------|
| `api-friction` | expressiveness, extensibility, scalability | accessibility | Unintuitive API, excessive boilerplate |
| `doc-gaps` | expressiveness, extensibility | accessibility, maturity | Had to read source instead of docs |
| `workaround-needed` | expressiveness, extensibility, scalability | extensibility | Test required a workaround |
| `solver-issues` | expressiveness, scalability | scalability | Convergence, performance, compatibility |
| `license-flags` | supply_chain | supply_chain | Licensing concerns |
| `arch-quality` | extensibility | maturity | Architecture observations |

## Verification Checklist

- [x] All 19 files exist in correct locations
- [x] SKILL.md YAML frontmatter parses correctly
- [x] pre-commit passes (markdownlint, ruff, mh_style/mh_lint)
- [x] Worktree isolation added to orchestrator
- [ ] Dry run: CONFIGURE step generates valid eval-config.yaml for one tool
- [ ] Dry run: GATE step runs gate tests for a passing tool (pypsa)
- [ ] Dry run: One functional dimension (expressiveness on TINY) produces result files
- [ ] End-to-end: Full evaluation of one tool produces synthesis.md
