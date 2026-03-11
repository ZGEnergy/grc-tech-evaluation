# Protocol-to-Skill Traceability Audit

**Audit date:** 2026-03-10T00:00:00Z
**Protocol version:** v8
**Overall verdict:** PASS
**Total findings:** 7
**Findings by category:** gap: 1, dangling: 0, stale: 6

## Files Audited

- `evaluation_guides/Phase1_Test_Protocol.md`
- `.claude/skills/evaluate-tool/prompts/code-evaluator-prompt.md`
- `.claude/skills/evaluate-tool/prompts/audit-evaluator-prompt.md`
- `.claude/skills/evaluate-tool/prompts/gate-evaluator-prompt.md`
- `.claude/skills/evaluate-tool/prompts/research-prompt.md`
- `.claude/skills/evaluate-tool/prompts/config-generator-prompt.md`
- `.claude/skills/evaluate-tool/references/test-methodology-notes.md`
- `.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md`
- `.claude/skills/evaluate-tool/SKILL.md`

---

## Sub-Check A: Forward Traceability

**Verdict:** PASS
**Items checked:** 62 test IDs

All test IDs are covered via config-driven dispatch. The config-generator-prompt.md
extracts ALL test IDs from the protocol into `eval-config.yaml`, and the orchestrator
(SKILL.md) dispatches them to the appropriate agent archetype via the `{{test_ids}}`
variable. Individual test IDs are also referenced literally in reference files for
methodology guidance.

### Coverage Mechanism

The skill system uses a two-stage traceability model:

1. **Config-generator** (config-generator-prompt.md) reads the protocol and extracts
   every test ID into a structured YAML config. It is explicitly instructed: "Extract
   ALL test IDs from the protocol. Do not skip or summarize."
2. **Orchestrator** (SKILL.md) reads the config and dispatches test IDs to agents via
   `{{test_ids}}` in each DAG step. The dispatch loop covers all dimensions and tiers.

| Test ID | Found in | Coverage type | Status |
|---------|----------|---------------|--------|
| G-1 | config-generator-prompt.md, gate-evaluator-prompt.md | config-driven dispatch + literal | OK |
| G-2 | config-generator-prompt.md, gate-evaluator-prompt.md | config-driven dispatch + literal | OK |
| G-3 | config-generator-prompt.md, gate-evaluator-prompt.md | config-driven dispatch + literal | OK |
| A-1 | config-generator-prompt.md, code-evaluator-prompt.md, result-template.md, observation-schema.md, synthesis-prompt.md, test-script-conventions.md | config-driven dispatch + literal | OK |
| A-2 | code-evaluator-prompt.md, cross-tool-watchpoints.md, convergence-protocol.md | config-driven dispatch + literal | OK |
| A-3 | config-generator-prompt.md, cross-tool-watchpoints.md, synthesis-template.md | config-driven dispatch + literal | OK |
| A-4 | config-generator-prompt.md, code-evaluator-prompt.md | config-driven dispatch + literal | OK |
| A-5 | config-generator-prompt.md, code-evaluator-prompt.md, cross-tool-watchpoints.md, test-methodology-notes.md | config-driven dispatch + literal | OK |
| A-6 | config-generator-prompt.md | config-driven dispatch | OK |
| A-7 | test-methodology-notes.md | config-driven dispatch + literal | OK |
| A-8 | code-evaluator-prompt.md, result-template.md, test-methodology-notes.md | config-driven dispatch + literal | OK |
| A-9 | cross-tool-watchpoints.md, test-methodology-notes.md | config-driven dispatch + literal | OK |
| A-10 | cross-tool-watchpoints.md | config-driven dispatch + literal | OK |
| A-11 | cross-tool-watchpoints.md | config-driven dispatch + literal | OK |
| B-1 | code-evaluator-prompt.md, synthesis-template.md | config-driven dispatch + literal | OK |
| B-2 | observation-schema.md | config-driven dispatch + literal | OK |
| B-3 | config-generator-prompt.md | config-driven dispatch + literal | OK |
| B-4 | code-evaluator-prompt.md, test-methodology-notes.md | config-driven dispatch + literal | OK |
| B-5 | config-generator-prompt.md | config-driven dispatch | OK |
| B-6 | config-generator-prompt.md | config-driven dispatch | OK |
| B-7 | code-evaluator-prompt.md | config-driven dispatch + literal | OK |
| B-8 | cross-tool-watchpoints.md | config-driven dispatch + literal | OK |
| B-9 | code-evaluator-prompt.md, cross-tool-watchpoints.md, result-template.md | config-driven dispatch + literal | OK |
| C-1 | test-methodology-notes.md | config-driven dispatch + literal | OK |
| C-2 | test-methodology-notes.md | config-driven dispatch + literal | OK |
| C-3 | cross-tool-watchpoints.md, observation-schema.md, test-methodology-notes.md | config-driven dispatch + literal | OK |
| C-4 | code-evaluator-prompt.md | config-driven dispatch + literal | OK |
| C-5 | config-generator-prompt.md, test-methodology-notes.md | config-driven dispatch + literal | OK |
| C-6 | test-methodology-notes.md | config-driven dispatch + literal | OK |
| C-7 | solver-config.md | config-driven dispatch + literal | OK |
| C-8 | test-methodology-notes.md | config-driven dispatch + literal | OK |
| C-9 | code-evaluator-prompt.md, cross-tool-watchpoints.md | config-driven dispatch + literal | OK |
| C-10 | cross-tool-watchpoints.md | config-driven dispatch + literal | OK |
| D-1 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| D-2 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| D-3 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| D-4 | audit-evaluator-prompt.md, observation-schema.md | config-driven dispatch + literal | OK |
| D-5 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| E-1 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| E-2 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| E-3 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| E-4 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| E-5 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| E-6 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| E-7 | audit-evaluator-prompt.md, config-generator-prompt.md | config-driven dispatch + literal | OK |
| F-1 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-2 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-3 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-4 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-5 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-6 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-7 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-8 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| F-9 | audit-evaluator-prompt.md | config-driven dispatch + literal | OK |
| G-FNM-1 | code-evaluator-prompt.md, config-generator-prompt.md, SKILL.md, cross-tool-watchpoints.md, test-methodology-notes.md, synthesis-template.md | config-driven dispatch + literal | OK |
| G-FNM-2 | code-evaluator-prompt.md, config-generator-prompt.md, SKILL.md, cross-tool-watchpoints.md, test-methodology-notes.md, synthesis-template.md | config-driven dispatch + literal | OK |
| G-FNM-3 | code-evaluator-prompt.md, cross-tool-watchpoints.md, test-methodology-notes.md, synthesis-prompt.md, synthesis-template.md | config-driven dispatch + literal | OK |
| G-FNM-4 | code-evaluator-prompt.md, cross-tool-watchpoints.md, test-methodology-notes.md, synthesis-prompt.md, synthesis-template.md | config-driven dispatch + literal | OK |
| G-FNM-5 | code-evaluator-prompt.md, config-generator-prompt.md, cross-tool-watchpoints.md, test-methodology-notes.md, synthesis-prompt.md, synthesis-template.md | config-driven dispatch + literal | OK |
| P2-1 | config-generator-prompt.md (via p2_readiness dimension), SKILL.md (Phase 2 readiness handling) | config-driven dispatch | OK |
| P2-2 | config-generator-prompt.md (via p2_readiness dimension), SKILL.md (Phase 2 readiness handling) | config-driven dispatch | OK |
| P2-3 | config-generator-prompt.md (via p2_readiness dimension), SKILL.md (Phase 2 readiness handling) | config-driven dispatch | OK |

### Findings

No gaps. All 62 test IDs are covered via config-driven dispatch through `{{test_ids}}`.

---

## Sub-Check B: Reverse Traceability

**Verdict:** PASS
**Items checked:** 62 unique test IDs referenced across skill files

All test ID references found in skill files correspond to valid test IDs in the v8 protocol.
No dangling or stale references detected.

### Test ID References by Skill File

| File | Test IDs Referenced | Status |
|------|-------------------|--------|
| code-evaluator-prompt.md | A-2, A-3, A-4, A-5, A-6, A-8, B-1, B-4, B-7, B-9, C-4, C-9, G-FNM-1 through G-FNM-5 | All valid in v8 |
| audit-evaluator-prompt.md | D-1 through D-5, E-1 through E-7, F-1 through F-9 | All valid in v8 |
| gate-evaluator-prompt.md | G-1 (via `{{test_ids}}` dispatch) | Valid in v8 |
| config-generator-prompt.md | G-1, A-1, A-3, A-4, A-5, A-6, B-3, B-5, C-5, E-1 through E-7, G-FNM-1 through G-FNM-5 | All valid in v8 |
| synthesis-prompt.md | A-1, A-3, G-FNM-1 through G-FNM-5 | All valid in v8 |
| test-methodology-notes.md | A-5, A-7, A-8, A-9, B-4, C-1 through C-10, G-FNM-1 through G-FNM-5 | All valid in v8 |
| cross-tool-watchpoints.md | A-2, A-3, A-5, A-9, A-10, A-11, B-8, B-9, C-3, C-9, C-10, G-FNM-1 through G-FNM-5 | All valid in v8 |
| convergence-protocol.md | A-2 | Valid in v8 |
| result-template.md | A-1, A-8, B-9 | All valid in v8 |
| synthesis-template.md | A-1, A-3, B-1, G-FNM-1 through G-FNM-5 | All valid in v8 |
| observation-schema.md | A-1, B-2, C-3, D-4 | All valid in v8 |
| solver-config.md | A-5, C-7 | All valid in v8 |
| test-script-conventions.md | A-1, B-3, C-5 | All valid in v8 |

### Findings

No dangling or stale test ID references found. All referenced test IDs exist in the v8 protocol.

---

## Sub-Check C: PHASE2 Marker Cleanup

**Verdict:** FAIL
**PHASE2 markers found:** 6
**Forward references found:** 5
**Forward references resolved:** 5/5

### PHASE2 HTML Comment Markers

The protocol contains 6 remaining `<!-- PHASE2 -->` HTML comment markers:

| Line | Context | Content |
|------|---------|---------|
| 186 | Suite A notes (A-7 contingency sweep) | `<!-- PHASE2: move to test-methodology-notes.md -->` |
| 189 | Suite A notes (A-5 cycling augmentation) | `<!-- PHASE2: move to test-methodology-notes.md -->` |
| 200 | Suite A notes (A-9 feasibility relaxation) | `<!-- PHASE2: move to test-methodology-notes.md -->` |
| 231 | Suite B notes (B-4 perturbation calibration) | `<!-- PHASE2: move to test-methodology-notes.md -->` |
| 339 | Suite G notes (pass conditions runtime) | `<!-- PHASE2: move to test-methodology-notes.md -->` |
| 350 | Suite G notes (failure attribution) | `<!-- PHASE2: move to test-methodology-notes.md -->` |

All 6 markers indicate content that should be moved to `test-methodology-notes.md`. The
content HAS already been moved (the file exists at
`.claude/skills/evaluate-tool/references/test-methodology-notes.md` with the corresponding
sections), but the PHASE2 markers in the protocol were not removed after the move. These
are stale markers -- the migration is complete but the cleanup step was not performed.

### Forward References to test-methodology-notes.md

All forward references in the protocol resolve to the existing file:

| Line | Forward Reference | Resolves? |
|------|------------------|-----------|
| 202 | "Note on resource type classification (A-8, B-4): See test-methodology-notes.md" | YES -- Section "Resource Type Classification [A-8, B-4]" exists |
| 204 | "Note on performance loops: See test-methodology-notes.md" | YES -- Section "Performance Loop Methodology [C-1 through C-10]" exists |
| 347 | "See test-methodology-notes.md for implementation guidance" (pass conditions) | YES -- Section "Pass Conditions Runtime Application [G-FNM-3, G-FNM-4]" exists |
| 352 | "Note on failure attribution: See test-methodology-notes.md" | YES -- Section "Failure Attribution Procedure [G-FNM-1 through G-FNM-5]" exists |
| 513 | Revision history entry (descriptive text, not a forward reference) | N/A |

### Findings

| # | Sub-check | Category | Source File | Source Location | Target File | Target Entity | Description | Responsible Phase |
|---|-----------|----------|-------------|-----------------|-------------|---------------|-------------|-------------------|
| 1 | C | stale | evaluation_guides/Phase1_Test_Protocol.md | Line 186 | references/test-methodology-notes.md | A-7 section | PHASE2 marker not removed after content migration | Phase 02 (protocol-v8) |
| 2 | C | stale | evaluation_guides/Phase1_Test_Protocol.md | Line 189 | references/test-methodology-notes.md | A-5 section | PHASE2 marker not removed after content migration | Phase 02 (protocol-v8) |
| 3 | C | stale | evaluation_guides/Phase1_Test_Protocol.md | Line 200 | references/test-methodology-notes.md | A-9 section | PHASE2 marker not removed after content migration | Phase 02 (protocol-v8) |
| 4 | C | stale | evaluation_guides/Phase1_Test_Protocol.md | Line 231 | references/test-methodology-notes.md | B-4 section | PHASE2 marker not removed after content migration | Phase 02 (protocol-v8) |
| 5 | C | stale | evaluation_guides/Phase1_Test_Protocol.md | Line 339 | references/test-methodology-notes.md | G-FNM-3/4 section | PHASE2 marker not removed after content migration | Phase 02 (protocol-v8) |
| 6 | C | stale | evaluation_guides/Phase1_Test_Protocol.md | Line 350 | references/test-methodology-notes.md | G-FNM failure attribution | PHASE2 marker not removed after content migration | Phase 02 (protocol-v8) |

---

## Sub-Check D: Cross-Reference Integrity

**Verdict:** PASS (with 1 advisory finding)

### Pass 1: Watchpoint Section References

All 5 new sections required by the PRD exist as H2 headings in
`.claude/skills/evaluate-tool/references/cross-tool-watchpoints.md`:

| Required Section | Heading in File | Line | Status |
|-----------------|-----------------|------|--------|
| Suite G Format Context | `## Suite G Format Context` | 157 | PRESENT |
| Formulation Sophistication Catalog | `## Formulation Sophistication Catalog` | 195 | PRESENT |
| Post-Ingestion Fidelity Checks | `## Post-Ingestion Fidelity Checks` | 242 | PRESENT |
| baseMVA and Q-Limit Pitfalls | `## baseMVA and Q-Limit Pitfalls` | 274 | PRESENT |
| PowerModels solve_dc_pf Pitfall | `## PowerModels solve_dc_pf Pitfall` | 313 | PRESENT |

The code-evaluator-prompt.md references `cross-tool-watchpoints.md#formulation-sophistication-catalog`
(line 286), which resolves correctly to the H2 heading "Formulation Sophistication Catalog".

All other prompt references to `cross-tool-watchpoints.md` are file-level (no section anchor),
which resolve correctly since the file exists.

### Pass 2: SKILL.md Variable Completeness

Verified all `{{variable}}` placeholders in each prompt against SKILL.md's variable
replacement instructions for the corresponding state/archetype.

#### config-generator-prompt.md (State: CONFIGURE)

| Variable | Documented in SKILL.md | Status |
|----------|----------------------|--------|
| `{{rubric_path}}` | Line 123 | OK |
| `{{protocol_path}}` | Line 124 | OK |
| `{{output_path}}` | Line 125 | OK |
| `{{tool_name}}` | Line 126 | OK |

#### research-prompt.md (State: RESEARCH)

| Variable | Documented in SKILL.md | Status |
|----------|----------------------|--------|
| `{{tool_name}}` | Line 168 | OK |
| `{{research_focus}}` | Lines 162-165 | OK |
| `{{output_path}}` | Line 169 | OK |

#### gate-evaluator-prompt.md (State: GATE)

| Variable | Documented in SKILL.md | Status |
|----------|----------------------|--------|
| `{{tool_name}}` | Line 196 (SKILL.md GATE section) | OK |
| `{{tool_dir}}` | Line 196 | OK |
| `{{test_ids}}` | Line 197 | OK |
| `{{reference_solutions}}` | Line 198 | OK |
| `{{results_dir}}` | Line 199 | OK |

#### code-evaluator-prompt.md (State: EVALUATE, archetype: code-evaluator)

| Variable | Documented in SKILL.md | Status |
|----------|----------------------|--------|
| `{{dimension}}` | Line 233 | OK |
| `{{test_ids}}` | Line 234 | OK |
| `{{network_tier}}` | Line 235 | OK |
| `{{tool_name}}` | Line 236 | OK |
| `{{tool_dir}}` | Line 237 | OK |
| `{{results_dir}}` | Line 238 | OK |
| `{{research_context}}` | Line 239 | OK |
| `{{reference_files}}` | Line 240 | OK |
| `{{observation_tags}}` | Line 244 | OK |
| `{{consumed_observations}}` | Line 245 | OK |
| `{{version_capability_report}}` | Line 248 | OK |
| `{{fnm_reference_files}}` | NOT in variable list | ADVISORY (see finding below) |

#### audit-evaluator-prompt.md (State: EVALUATE, archetype: audit-evaluator)

| Variable | Documented in SKILL.md | Status |
|----------|----------------------|--------|
| `{{dimension}}` | Line 233 | OK |
| `{{test_ids}}` | Line 234 | OK |
| `{{tool_name}}` | Line 236 | OK |
| `{{tool_dir}}` | Line 237 | OK |
| `{{results_dir}}` | Line 238 | OK |
| `{{consumed_observations}}` | Line 245 | OK |
| `{{reference_files}}` | Line 240 | OK |

#### synthesis-prompt.md (State: SYNTHESIZE)

| Variable | Documented in SKILL.md | Status |
|----------|----------------------|--------|
| `{{tool_name}}` | Line 339 | OK |
| `{{results_dir}}` | Line 340 | OK |
| `{{observations_dir}}` | Line 341 | OK |
| `{{skill_dir}}` | Line 342 | OK |

### Findings

| # | Sub-check | Category | Source File | Source Location | Target File | Target Entity | Description | Responsible Phase |
|---|-----------|----------|-------------|-----------------|-------------|---------------|-------------|-------------------|
| 7 | D | gap | code-evaluator-prompt.md | Line 16 (`{{fnm_reference_files}}`) | SKILL.md | EVALUATE variable list | `{{fnm_reference_files}}` is declared as an input in code-evaluator-prompt.md but is not listed in SKILL.md's variable replacement section (lines 232-248). SKILL.md handles FNM reference files separately in the Suite G dispatch section (lines 277-283) by passing "additional reference files" but does not use the `{{fnm_reference_files}}` variable name. The orchestrator likely passes them via `{{reference_files}}` concatenation rather than a separate variable. Functional impact is low (the files get passed), but the variable name mismatch could cause an unreplaced placeholder if the orchestrator follows the variable list literally. | Phase 02 (skill-overhaul) |

---

## Recommended Actions

### Must-Fix (blocks clean PASS on Sub-Check C)

1. **Remove 6 stale PHASE2 markers** from `evaluation_guides/Phase1_Test_Protocol.md` at
   lines 186, 189, 200, 231, 339, 350. The content migration to
   `test-methodology-notes.md` is already complete. These are leftover HTML comments
   that serve no further purpose.

### Advisory (does not block PASS)

1. **Reconcile `{{fnm_reference_files}}` variable** -- Either:
   (a) Add `{{fnm_reference_files}}` to SKILL.md's EVALUATE variable replacement list
   with the FNM reference file paths, OR
   (b) Remove the `{{fnm_reference_files}}` input declaration from
   code-evaluator-prompt.md and document that FNM reference files are concatenated into
   `{{reference_files}}` for Suite G dispatches.
   Current behavior likely works because the orchestrator's Suite G section explicitly
   lists the files to pass, but the variable name gap creates ambiguity.
