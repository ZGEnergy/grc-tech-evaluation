# Protocol v8 & Rubric v6 Overhaul — Executive Plan

## Vision

The evaluation framework has systematic issues that penalize tools for being more sophisticated than MATPOWER, produce false failures from incorrect test setup, and conflate project maturity with sustainability risk. Eight open GitHub issues (#43, #48, #49, #54, #55, #56, #57, #59) document these problems. Left unfixed, the next evaluation sweep will reproduce the same distortions.

This plan coordinates updates across the protocol (v7→v8), rubric (v5→v6), and evaluate-tool skill machinery to eliminate these issues. It also thins the protocol document — moving agent-facing implementation detail to skill reference files, eliminating multi-way content duplication, and tightening language throughout — so the protocol is scannable by a human evaluator.

A prerequisite data pipeline (Phase 0) materializes the FNM intermediate-format CSVs that the updated protocol references, since these files do not yet exist.

## Objectives

1. Eliminate MATPOWER format bias in Suite G by providing main-island-filtered intermediate CSVs as the primary G-FNM-3/4 input path, with the cleaned MATPOWER `.m` as documented fallback.
2. Establish a concrete decision procedure for distinguishing formulation differences from bugs in DCPF and ACPF comparisons, with bounded tolerances and systematic-deviation requirements.
3. Add version-awareness to the evaluation pipeline so tests exercise capabilities of the installed version, not a stale understanding of the tool.
4. Split Criterion 5 into Demonstrated Maturity (5a) and Sustainability Risk (5b) with an explicit 3×3 grade matrix, and add reviewer/approval concentration as a 5b sub-metric.
5. Reduce protocol document size by ~11% and eliminate 3-4 way content duplication between protocol, watchpoints, and prompts, with zero information loss.
6. Validate that all changes are internally consistent and that config generation produces correct output from the v8 protocol.

## Constraints

- The protocol and rubric are contract deliverables — criterion count must remain at 6 (the 5a/5b split is internal to Criterion 5, not a new criterion).
- No tool re-evaluation in this plan. This fixes the framework; re-evaluation is a separate step.
- All code execution happens inside the devcontainer. Phase 0 pipeline scripts run via `dc-exec`.
- Existing v5/v7 results remain valid for Suites A-F. The protocol must document version compatibility rules for mixed-version result sets.
- The intermediate CSV schema is already defined in `data/fnm/docs/intermediate-schema.md` — Phase 0 implements it, it does not redesign it.
- The `formulation_difference` tag requires deviations to be systematic (correlated with transformer/phase-shifter branches) and within a maximum absolute threshold. Scattered or large deviations cannot be tagged without explicit justification.
- The intermediate CSVs must encode baseMVA as sidecar metadata, pre-convert tap=0 to 1.0, use explicit transformer vs. line distinction, and preserve MATPOWER bus_type encoding (1/2/3/4).
- The 5a/5b grade matrix must be fully defined in the rubric (not deferred to evaluator judgment).
- Protocol content rule: the protocol defines *what* is tested and *how results are graded*. Implementation details for *how tests are executed* belong in skill reference files.

## Phases

### Phase 0: FNM Intermediate CSV Export & Validation
- **Objective:** Materialize main-island-filtered, cleaned intermediate-format CSVs from the FNM data so the v8 protocol can reference them.
- **Key deliverables:** Export pipeline script, main-island intermediate CSVs committed to `data/fnm/reference/cleaned/intermediate/`, baseMVA sidecar metadata file, updated `dcpf_reference.py` accepting separate branch/transformer tables, validation that DCPF reference solution is reproducible from the new CSV path.
- **Target repository:** grc-tech-evaluation
- **Dependencies:** FNM_PATH must be available in devcontainer. Existing intermediate schema, cleaning manifest, and excluded_buses.json are inputs.
- **Estimated scope:** 1 pipeline script (~200 lines), 1 update to dcpf_reference.py, ~8 output CSV files (one per non-empty PSS/E record type) plus manifest.json, validation checks.

### Phase 1: Protocol & Rubric Edits
- **Objective:** Update the two authoritative guide documents to v8 protocol and v6 rubric, incorporating all 8 issue fixes and protocol thinning.
- **Key deliverables:** `Phase1_Test_Protocol.md` v8 (G-FNM input path change, formulation sophistication annotations, protocol thinning with `<!-- PHASE2 -->` markers for two-step extraction, version compatibility notes), `Phase1_Evaluation_Rubric.md` v6 (Criterion 5 split into 5a/5b with grade matrix, reviewer concentration sub-metric).
- **Target repository:** grc-tech-evaluation
- **Dependencies:** Phase 0 (CSV paths must exist to reference in protocol).
- **Estimated scope:** ~100 lines changed in protocol, ~60 lines changed in rubric. Net protocol reduction ~50 lines.

### Phase 2: Skill Machinery Updates
- **Objective:** Update evaluate-tool prompts, references, and orchestrator to implement the v8 protocol and v6 rubric changes.
- **Key deliverables:** Updated `cross-tool-watchpoints.md` (new sections: Suite G format context, formulation sophistication catalog, post-ingestion fidelity checks, baseMVA/Q-limit pitfalls, PowerModels solve_dc_pf pitfall), new `test-methodology-notes.md` (6 factored agent-facing notes + extracted agent portions from 6 hybrid notes), updated `research-prompt.md` (4th version-awareness agent with defined capability report schema), updated `code-evaluator-prompt.md` (G-FNM intermediate CSV input path, ingestion count verification gate, formulation_difference tag procedure), updated `audit-evaluator-prompt.md` (reviewer/approval concentration in E-3), updated `SKILL.md` (4th research agent dispatch in RESEARCH state, version capability report consumer contract in code-evaluator).
- **Target repository:** grc-tech-evaluation
- **Dependencies:** Phase 1 (skill files implement what the protocol specifies).
- **Estimated scope:** ~9 files modified (including config-generator prompt), ~350 lines of new/changed content across prompts and references.

### Phase 3: Validation
- **Objective:** Verify internal consistency across all updated artifacts and confirm the evaluation pipeline can consume them.
- **Key deliverables:** Config generation smoke test (v8 protocol → eval-config.yaml succeeds for at least one tool), cross-reference checklist (each of the 8 issues mapped to its fix location in protocol, rubric, and skill files), protocol-to-skill traceability audit (every test ID in protocol has corresponding handling in skill prompts, no dangling references to moved/deleted content).
- **Target repository:** grc-tech-evaluation
- **Dependencies:** Phases 1 and 2 complete.
- **Estimated scope:** Audit and verification, no new code. ~1 checklist document.

## Phase Dependencies

| Phase | Depends On | Enables |
|-------|-----------|---------|
| Phase 0 | — | Phase 1 |
| Phase 1 | Phase 0 | Phase 2 |
| Phase 2 | Phase 1 | Phase 3 |
| Phase 3 | Phase 1, Phase 2 | — |

**Implementation tiers** (phases within a tier have no mutual dependencies):

- **Tier 1:** Phase 0
- **Tier 2:** Phase 1
- **Tier 3:** Phase 2
- **Tier 4:** Phase 3

## Complexity

- **Tier:** 3 (Full PRDs)
- **Rationale:** 4 phases exceeds the ≥3 threshold, with ~15 estimated files and complex cross-artifact consistency requirements across protocol, rubric, and skill machinery.

## Context — Research Summary

Five parallel research threads investigated: (1) protocol bloat anatomy — 20 inline notes cataloged, 6 purely agent-facing, 6 hybrid, 8 evaluator-facing, with 3-4 way duplication between protocol/watchpoints/prompts; (2) reference solution inventory — only G-FNM-3 uses a MATPOWER-derived numerical reference (via independent Python script, not MATPOWER solver), Suites A-F use self-consistent pass conditions, the real bias is the input data path (MATPOWER `.m`); (3) PSS/E RAW parsing — only 3/6 tools have parsers, comma-delimited RAW helps only GridCal marginally, intermediate CSVs are the better neutral format; (4) evaluate-tool prompt chain — zero version awareness exists anywhere, config-generator reads static protocol text, G-FNM-1 prompt instructions are correct but unenforced; (5) maturity frameworks — CHAOSS and OpenSSF both separate backward-looking maturity from forward-looking sustainability risk, reviewer concentration is a genuine gap in all frameworks.

Critical data finding: the intermediate-format CSVs referenced by this plan do not yet exist. The `data/fnm/intermediate/` directory is an empty placeholder. The schema, manifest, cleaning spec, and exclusion list all exist, but no CSV files have been materialized. This necessitated adding Phase 0.

## Context — Debate Summary

One debate round with three critics (requirements, architecture, domain). Five HIGH-severity findings were identified and resolved: (1) `formulation_difference` tag lacked a decision procedure — added bounded-tolerance and systematic-deviation requirements; (2) intermediate CSVs risked losing transformer data — added CSV schema contract with explicit tap/transformer/baseMVA requirements; (3) Phase 3 was underspecified — strengthened to config generation smoke test + cross-reference checklist; (4) bus count was hardcoded — changed to runtime loading from cleaning manifest; (5) 5a/5b matrix was undefined — constrained to be defined in rubric, not deferred. Four MEDIUM findings were also resolved (version agent consumer contract, per-unit base risk in watchpoints, Q-limit false failure risk, protocol vs reference file classification rule). No HIGH findings remain after triage.

## Deferred Ideas

- **Multiple DCPF reference solutions per formulation type**: Decided annotate-and-explain instead. Could upgrade later without invalidating results.
- **Comma-delimited PSS/E RAW conversion**: Low value — only helps GridCal marginally, and even then requires version spoofing.
- **Criterion 5 as two fully independent criteria**: Would change the 6-criterion contract deliverable structure. The 5a/5b internal split achieves the same goal.
- **Numerical reference solutions for Suites A-F**: Currently self-consistent (convergence + output structure). No demonstrated need.
- **Backward compatibility matrix for mixed-version results**: Useful documentation but belongs in the selection report, not the protocol.
- **Semantic versioning for skill reference files**: Valid concern but git history provides sufficient traceability for now.
- **Re-evaluation of any tool**: This plan fixes the framework. Re-evaluation is a separate workflow.
