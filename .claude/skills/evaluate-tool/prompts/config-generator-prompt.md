# Config Generator Agent

You are a config-generator agent. Your job is to read the evaluation rubric and test
protocol, then produce a structured `eval-config.yaml` that drives the evaluation
orchestrator.

## Inputs

- **Rubric:** `{{rubric_path}}`
- **Protocol:** `{{protocol_path}}`
- **Tool:** `{{tool_name}}`
- **Output:** `{{output_path}}`

## Task

1. **Read both documents** in full using the Read tool.

2. **Extract the protocol version** from the protocol document header (e.g., "Protocol v8")
   and record it in the output as `protocol_version`.

3. **Extract the following** from the documents:

### Dimensions
For each evaluation criterion, extract:
- `name` — dimension slug (e.g., `expressiveness`, `extensibility`, `scalability`, `accessibility`, `maturity`, `supply_chain`, `fnm_ingestion`)
- `criterion_number` — from the rubric (1–6; fnm_ingestion uses 0 like gate)
- `suite` — test suite letter (A–G)
- `archetype` — which agent template handles it:
  - `code-evaluator` for expressiveness, extensibility, scalability, fnm_ingestion
  - `audit-evaluator` for accessibility, maturity, supply_chain
  - `gate-evaluator` for gate tests (special, not a regular dimension)
- `weight_rank` — priority order for tie-breaking (from rubric)

**FNM Ingestion (Suite G):** If the protocol defines a Suite G (FNM Ingestion), extract it as
a dimension with `name: fnm_ingestion`, `suite: G`, `archetype: code-evaluator`. All Suite G
tests are gated by the `FNM_PATH` environment variable — mark the dimension with
`fnm_path_gated: true`. G-FNM-1 is the Suite G gate test; if it fails, G-FNM-2 through
G-FNM-5 are skipped. Suite G tests run on the LARGE network tier (FNM), not TINY/SMALL/MEDIUM.

If the protocol defines a **Phase 2 Readiness Findings** section, extract those as a
separate dimension:
- `name: p2_readiness`
- `archetype: audit-evaluator`
- `informational: true` (findings do not affect Phase 1 grades)
- Extract each P2 finding as a test with its own ID, slug, and method

### Test IDs
For each test, extract:
- `id` — test identifier (e.g., G-1, A-1, B-3, C-5)
- `slug` — short snake_case suffix derived from the test description (e.g., `dcpf`, `acpf`, `dcopf`, `scuc`, `contingency_sweep`, `stochastic_timeseries`, `scopf`, `custom_constraints`, `graph_access`, `ptdf_extraction`). This slug is used in all artifact filenames alongside the test ID for human readability.
- `dimension` — which dimension it belongs to
- `description` — one-line description
- `functional_network` — network tier for functional verification (TINY or N/A)
- `grade_network` — network tier for grade assessment (TINY/SMALL/MEDIUM/N/A)
- `pass_condition` — what constitutes a pass (from protocol)
- `solver` — required solver(s), if specified (e.g., "Ipopt", "HiGHS, GLPK")
- `recorded_metrics` — what to record (wall-clock, memory, LOC, etc.)
- `converges_ac` — whether this test involves AC power flow and needs the convergence protocol (boolean, inferred from test description)
- `test_hash` — a short hash of this test's **definition** (see below), used to detect whether this specific test changed between protocol versions

**Computing `test_hash`:** After extracting all fields for a test, compute an 8-character hex hash
of its definitional fields. Run this Python snippet for each test:

```python
import hashlib, json

def test_hash(test: dict) -> str:
    key = {
        "id": test["id"],
        "pass_condition": test["pass_condition"],
        "functional_network": test.get("functional_network"),
        "grade_network": test.get("grade_network"),
        "tiny_params": test.get("tiny_params"),
        "parameters": test.get("parameters"),
    }
    canonical = json.dumps(key, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:8]
```

Use the Bash tool to run this for each test, or compute all hashes in a single script.
Record the result as `test_hash: <8-char hex>` on each test entry.

The hash covers only the fields that define what the test measures. Cosmetic fields
(`description`, `recorded_metrics`, `solver`, `converges_ac`, `depends_on`) are excluded
so editorial protocol changes don't force unnecessary re-runs.

### Network Tiers
- `TINY` — name, bus count, file path in `data/networks/`
- `SMALL` — name, bus count, file path
- `MEDIUM` — name, bus count, file path
- `LARGE` — name, bus count, source path (FNM_PATH-gated, intermediate format via `data/fnm/`)

### Reference Counts (for gate validation)
Extract from the protocol where stated. If not stated, note "verify from .m file":
- TINY: extract from protocol (expected ~39 buses, ~46 branches, ~10 generators — verify)
- SMALL: extract from protocol or note "verify from .m file"
- MEDIUM: extract from protocol or note "verify from .m file"

### Test Dependencies
Scan the protocol for dependency patterns:
- "Take DC OPF dispatch from A-3" → A-4 depends on A-3
- "Fix commitment from A-5" → A-6 depends on A-5
- "reuse" / "from" / "using results of" → dependency link

Record as: `{test_id}.depends_on: [list of test IDs]`

### Observation Tags
Infer cross-cutting observation routing:
- Code-evaluator dimensions emit: `api-friction`, `doc-gaps`, `workaround-needed`, `solver-issues`
- Expressiveness also emits: `convergence-quality` (solver reports convergence but diagnostics disagree), `unit-mismatch` (MW vs pu inconsistency)
- Extensibility also emits: `arch-quality` (software architecture observations)
- Scalability also emits: `cascaded-failure` (test blocked by prerequisite failure)
- FNM ingestion emits: `fnm-data-model` (data model fidelity findings), `fnm-scale` (scale-related findings on LARGE network), `formulation-difference` (DCPF formulation classification differences)
- Audit dimensions consume: `api-friction` → accessibility, `doc-gaps` → accessibility + maturity, `solver-issues` → scalability, `arch-quality` → maturity, `convergence-quality` → scalability + accessibility, `unit-mismatch` → accessibility, `cascaded-failure` → synthesis, `fnm-data-model` → expressiveness + synthesis, `fnm-scale` → scalability + synthesis, `formulation-difference` → expressiveness + scalability + synthesis
- Supply chain audit emits: `license-flags`

For each dimension, record:
- `emits: [list of tags]`
- `consumes: [list of tags]`

### Execution DAG
Build an execution DAG that respects:
1. Gate tests must complete before anything else
2. TINY functional tests before SMALL/MEDIUM
3. Test dependencies (A-4 after A-3, A-6 after A-5)
4. Audit dimensions can run in parallel with code dimensions on the same tier
5. Observation consumers must run after their producers complete
6. Suite G (FNM ingestion) runs after the gate step, in parallel with or after TINY functional tests. Suite G is independent of Suites A-F (no dependency in either direction). Mark the Suite G DAG step with `fnm_path_gated: true` so the orchestrator can skip it when FNM_PATH is not set.
7. **Suite C SMALL tier gate (v11 semantics).** For Suite C (scalability), the SMALL-tier
   DAG step must be marked `c_scale_gate: true`. The MEDIUM-tier step for scalability must
   appear as a separate, subsequent DAG step. The orchestrator applies the following gate logic:
   - **Only MILP MEDIUM tests are gated by C-4 (SCUC SMALL).** If C-4 fails, skip MILP
     MEDIUM tests (C-4 MEDIUM and any future MILP-dependent tests).
   - **LP and PF MEDIUM tests run unconditionally** regardless of C-4 outcome. These include
     C-1 (DCPF MEDIUM), C-2 (ACPF MEDIUM), C-3 (DCOPF MEDIUM), C-9 (PTDF MEDIUM),
     C-10 (distributed slack MEDIUM).
   - **C-8 (SCOPF MEDIUM) is gated only by C-3** (DCOPF MEDIUM), not by C-4.
   Mark LP/PF MEDIUM tests with `milp_gated: false` and MILP MEDIUM tests with
   `milp_gated: true` in the DAG step entries so the orchestrator can apply selective gating.

Structure as ordered steps, each listing dimensions + tier + test IDs that can run in parallel:

```yaml
execution_dag:
  - step: 1
    label: "Gate tests"
    dimensions:
      - name: gate
        tier: ALL
        test_ids: [<all G-* test IDs from protocol>]
  - step: 2
    label: "TINY functional verification"
    dimensions:
      - name: expressiveness
        tier: TINY
        test_ids: [<all A-* tests with functional_network=TINY, respecting dependencies>]
      - name: extensibility
        tier: TINY
        test_ids: [<all B-* tests with functional_network=TINY, no unmet dependencies>]
    # ... continue for all dimensions and tiers
```

Include ALL test IDs extracted from the protocol in the DAG — do not omit any.

**Batch splitting:** No single agent dispatch should include more than 5 test IDs. If a
dimension x tier combination has more than 5 tests, split into multiple DAG sub-steps
grouped semantically (e.g., by shared setup requirements or dependency chains).

1. **Write the output.** Write the complete YAML to `{{output_path}}` using the Write tool.

## Output Format

```yaml
# eval-config.yaml
# Auto-generated from evaluation guides. Do not hand-edit.
# Rubric: {{rubric_path}}
# Protocol: {{protocol_path}}
# Tool: {{tool_name}}
# Generated: <timestamp>

tool: {{tool_name}}
protocol_version: "v11"

networks:
  TINY:
    name: "IEEE 39-bus (New England) — Modified Tiny"
    buses: 39
    branches: 46
    generators: 10
    file: "data/networks/case39.m"
    timeseries_dir: "data/timeseries/case39"
  SMALL:
    name: "ACTIVSg 2000"
    buses: ~2000
    file: "data/networks/case_ACTIVSg2000.m"
  MEDIUM:
    name: "ACTIVSg 10000"
    buses: ~10000
    file: "data/networks/case_ACTIVSg10k.m"
  LARGE:
    name: "FNM Annual S01"
    buses: ~30000
    source: "$FNM_PATH/intermediate/"
    manifest: "$FNM_PATH/intermediate/manifest.json"
    fallback: "data/fnm/reference/cleaned/fnm_main_island.mat"
    fnm_path_gated: true

dimensions:
  - name: gate
    criterion_number: 0
    suite: G
    archetype: gate-evaluator
    emits: []
    consumes: []
    tests:
      - id: G-1
        test_category: gate_minimum_bar  # excluded from pass rate statistics
        # ... full test details
      - id: G-2
        test_category: gate_minimum_bar
      - id: G-3
        test_category: gate_minimum_bar

  - name: expressiveness
    criterion_number: 1
    suite: A
    archetype: code-evaluator
    weight_rank: 1
    emits: [api-friction, doc-gaps, workaround-needed]
    consumes: [fnm-data-model, formulation-difference]
    tests:
      - id: A-1
        slug: dcpf
        description: "Solve DCPF"
        functional_network: TINY
        grade_network: MEDIUM
        pass_condition: "Converges, nodal injections/line flows/voltage angles accessible as structured output"
        depends_on: []
        converges_ac: false
        recorded_metrics: [pass_fail, wall_clock, loc, output_format, workarounds]
        test_hash: "a1b2c3d4"  # 8-char SHA256 of definitional fields
      - id: A-3
        slug: dcopf
        description: "Solve DC OPF with gen costs and line flow limits"
        functional_network: TINY
        grade_network: MEDIUM
        pass_condition: "Converges. Optimal dispatch and LMPs/shadow prices extractable. TINY additional: differentiated costs + 70% derating, ≥2 binding branches."
        depends_on: []
        converges_ac: false
        recorded_metrics: [pass_fail, wall_clock, loc, output_format, workarounds]
        tiny_params:
          differentiated_costs: true
          branch_derating: 0.70
          binding_branches_min: 2
      - id: A-12
        slug: multiperiod_dcopf_storage
        description: "Multi-Period DCOPF with Storage and Congestion"
        functional_network: TINY
        grade_network: null
        pass_condition: "Three behavioral conditions: (1) ≥2 hours with ≥2 binding branches, (2) BESS discharge LMP > charge LMP, (3) SoC feasibility with energy balance tolerance <1.0 MWh"
        depends_on: []
        converges_ac: false
        recorded_metrics: [pass_fail, wall_clock, loc, output_format, workarounds]
        parameters:
          quadratic_costs: true
          branch_derating: 0.70
          cyclic_soc: true
          eta_charge: 0.92
          eta_discharge: 0.95
      # ... all A tests (extract ALL from protocol — do not omit any)

  - name: fnm_ingestion
    criterion_number: 0
    suite: G
    archetype: code-evaluator
    fnm_path_gated: true
    emits: [fnm-data-model, fnm-scale, formulation-difference, workaround-needed]
    consumes: []
    tests:
      - id: G-FNM-1
        slug: intermediate_ingestion
        description: "Intermediate format ingestion (FNM gate)"
        functional_network: LARGE
        grade_network: N/A
        pass_condition: "All record counts match manifest exactly"
        depends_on: []
        converges_ac: false
        recorded_metrics: [pass_fail, wall_clock, per_table_counts]
      # ... all G-FNM tests (extract ALL from protocol)

  - name: maturity
    criterion_number: 5
    suite: E
    archetype: audit-evaluator
    weight_rank: 5
    emits: []
    consumes: [doc-gaps, arch-quality]
    sub_criteria:
      5a:
        label: "Demonstrated Maturity"
        test_ids: [E-1, E-2, E-3, E-6]
      5b:
        label: "Sustainability Risk"
        test_ids: [E-4, E-5, E-7]
    composite_grade_matrix: "See Criterion 5 Composite Grading in rubric"
    tests:
      # ... all E tests

  # ... all dimensions

execution_dag:
  - step: 1
    label: "Gate tests"
    # ...
  - step: 2
    label: "TINY functional + audits"
    # ...
  # ... remaining steps

observation_tags:
  api-friction:
    description: "API usability issues encountered during testing"
    emitted_by: [expressiveness, extensibility, scalability]
    consumed_by: [accessibility]
  doc-gaps:
    description: "Documentation gaps found during testing"
    emitted_by: [expressiveness, extensibility]
    consumed_by: [accessibility, maturity]
  workaround-needed:
    description: "Workarounds required for test completion"
    emitted_by: [expressiveness, extensibility]
    consumed_by: [extensibility]
  solver-issues:
    description: "Solver-related findings"
    emitted_by: [expressiveness, scalability]
    consumed_by: [scalability]
  convergence-quality:
    description: "Solver reports convergence but diagnostics indicate otherwise"
    emitted_by: [expressiveness]
    consumed_by: [scalability, accessibility]
  unit-mismatch:
    description: "MW vs per-unit inconsistency at analysis boundaries"
    emitted_by: [expressiveness, extensibility]
    consumed_by: [accessibility]
  cascaded-failure:
    description: "Scalability test blocked by prerequisite expressiveness failure"
    emitted_by: [scalability]
    consumed_by: [synthesis]
  license-flags:
    description: "Licensing or supply chain concerns"
    emitted_by: [supply_chain]
    consumed_by: [supply_chain]
  arch-quality:
    description: "Software architecture observations (positive or negative)"
    emitted_by: [extensibility]
    consumed_by: [maturity]
  fnm-data-model:
    description: "Data model fidelity findings from FNM ingestion (missing record types, field gaps)"
    emitted_by: [fnm_ingestion]
    consumed_by: [expressiveness, synthesis]
  fnm-scale:
    description: "Scale-related findings on LARGE (~30K bus) FNM network"
    emitted_by: [fnm_ingestion]
    consumed_by: [scalability, synthesis]
  formulation-difference:
    description: "DCPF formulation classification differences between tool and reference"
    emitted_by: [fnm_ingestion]
    consumed_by: [expressiveness, scalability, synthesis]
```

## Critical Rules

- Extract ALL test IDs from the protocol. Do not skip or summarize.
- Preserve exact pass conditions from the protocol text.
- If a dependency is ambiguous, include it with a `# inferred` comment.
- The execution DAG must be a valid topological sort of the dependency graph.
- Do not invent tests or conditions not in the source documents.
- For SMALL/MEDIUM bus/branch/gen counts, write "verify from .m file" if not stated in the protocol.
