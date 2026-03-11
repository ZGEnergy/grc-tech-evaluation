# Purpose

Phases 0 through 2 produced a coordinated set of changes across four artifact layers: intermediate CSV data files (Phase 0), authoritative guide documents (Phase 1: protocol v8, rubric v6), and skill machinery (Phase 2: prompts, references, orchestrator). These changes touch 15+ files across three directory trees (`data/fnm/`, `evaluation_guides/`, `.claude/skills/evaluate-tool/`) and implement fixes for eight GitHub issues. The artifacts reference each other extensively: the protocol defines test IDs that skill prompts implement, the rubric defines grading criteria that the synthesis prompt consumes, the code-evaluator prompt references watchpoint sections by name, and the SKILL.md orchestrator wires research agent outputs into evaluator agent inputs. Any inconsistency between these layers would cause silent evaluation failures — a dangling test ID reference, a missing `<!-- PHASE2 -->` marker cleanup, or a config-generator that cannot parse the v8 protocol structure.

Phase 3 is a pure verification phase. It produces no new code, no document edits, and no schema changes. Its sole purpose is to confirm that the changes from Phases 0-2 are internally consistent, that the evaluation pipeline can consume the updated artifacts, and that every GitHub issue has a traceable fix location. The three deliverables correspond to the three verification dimensions: pipeline functionality (config generation smoke test), issue-to-fix traceability (cross-reference checklist), and artifact-to-artifact consistency (protocol-to-skill traceability audit).

The verification checks in this phase are manual audits and structured checklists, not pytest unit tests. Each "test" is a specific verification condition that the auditor evaluates as pass/fail with evidence. If any check fails, the fix belongs in the artifact produced by an earlier phase — Phase 3 does not modify those artifacts, it identifies what needs to be fixed and routes the fix back to the responsible phase.

---

# What This Phase Produces

**Output:** Three verification artifacts in `plans/protocol-v8-rubric-v6-overhaul/phases/phase-03-validation/`:

1. `config-generation-smoke-test.md` — Evidence that the evaluate-tool skill's config-generator agent can parse the v8 protocol and produce a structurally valid `eval-config.yaml` for at least one tool.
2. `cross-reference-checklist.md` — A table mapping each of the 8 GitHub issues (#43, #48, #49, #54, #55, #56, #57, #59) to its fix location(s) in protocol, rubric, and skill files, with pass/fail status for each mapping.
3. `traceability-audit.md` — A structured audit confirming that every test ID in the v8 protocol has corresponding handling in skill prompts, that no skill prompts reference test IDs or sections that do not exist in the v8 protocol, and that all `<!-- PHASE2 -->` markers from Phase 1 have been consumed by Phase 2.

**Downstream consumer:** The project maintainer, who uses these artifacts to confirm the overhaul is complete and internally consistent before merging to main. No further automated phases consume these outputs.

---

# Design Decisions

## Config generation smoke test runs inside the devcontainer against one tool

The config-generator agent parses the protocol and rubric to produce an `eval-config.yaml`. A full config generation for all six tools would be a re-evaluation activity, which is out of scope. The smoke test runs config generation for a single tool (pypsa, chosen because it exercises all suites including G-FNM when FNM_PATH is available) and validates the output structure: correct YAML syntax, all protocol test IDs present, DAG steps parseable, observation tags declared. This is sufficient to confirm that the v8 protocol structure is machine-readable by the skill pipeline.

The smoke test does not execute the generated config (no gate tests, no evaluator agents). It only confirms that config generation succeeds and the output is structurally valid. The generated config is written to a temporary location (not the tool's results directory) to avoid polluting evaluation state.

## Cross-reference checklist is issue-centric, not file-centric

Each GitHub issue describes a specific problem. The checklist maps each issue to the set of files that implement its fix, organized as {issue -> protocol location, rubric location, skill file location(s)}. This structure makes it easy to verify that no issue was partially addressed (e.g., fixed in the protocol but not propagated to the skill prompt). Issues that do not require changes in all three layers have explicit "N/A" entries with justification.

## Traceability audit covers both directions

A one-directional check (protocol test IDs -> skill references) would miss orphaned references in the opposite direction — skill prompts that reference test IDs removed or renumbered in v8. The audit checks both directions: (1) for every test ID in the v8 protocol, at least one skill prompt or reference file handles it, and (2) for every test ID referenced in skill prompts, the ID exists in the v8 protocol. This bidirectional check catches both gaps and dangling references.

## `<!-- PHASE2 -->` marker verification is part of the traceability audit

Phase 1 Deliverable 2 inserted `<!-- PHASE2: move to test-methodology-notes.md -->` markers in the protocol to flag agent-facing content for extraction. Phase 2 Deliverable 1 created `test-methodology-notes.md` with the extracted content. The traceability audit verifies that: (a) no `<!-- PHASE2 -->` markers remain in the v8 protocol (they should have been removed or their content extracted), and (b) every note referenced by a forward reference in the protocol (`See test-methodology-notes.md`) actually exists in that file. This is a natural extension of the traceability audit rather than a separate deliverable.

## No code changes in this phase

If verification checks fail, this phase documents the failure and identifies the responsible artifact. Fixes are applied by revisiting the relevant phase (1 or 2), not by Phase 3 editing those artifacts directly. This preserves the phase dependency chain: Phase 3 depends on Phases 1 and 2 but does not feed back into them within the same execution.

---

# Deliverables

### 1. Config Generation Smoke Test
- **Description:** Run the evaluate-tool skill's config-generator agent against the v8 protocol and v6 rubric for a single tool (pypsa). Validate that config generation completes without error and produces a structurally valid `eval-config.yaml`. Structural validation checks: valid YAML syntax, all v8 protocol test IDs present in the config (cross-referenced against the protocol's test ID inventory), DAG steps are well-formed (each step references valid dimensions and test IDs), observation tags declared in the config match the protocol's tag definitions, network tiers map correctly to the protocol's Reference Networks table, the `formulation_difference` tag appears in the config's tag vocabulary, the 5a/5b criterion split is reflected in the config's dimension structure (if the config encodes rubric criteria), and `protocol_version` field reads `v8`. The generated config is written to a scratch location and included as an appendix to the smoke test report. Any structural validation failure is documented with the specific check that failed and the config section involved.
- **Estimated tests:** 12
- **Dependencies:** Phase 1 (protocol v8 and rubric v6 must be finalized), Phase 2 (config-generator prompt must be current)

### 2. Cross-Reference Checklist
- **Description:** A structured table mapping each of the 8 GitHub issues to its fix location(s) across the three artifact layers (protocol, rubric, skill files). For each issue, the checklist records: issue number and title, the specific problem described, the protocol section(s) where the fix was applied (or N/A with justification), the rubric section(s) where the fix was applied (or N/A), the skill file(s) where the fix was applied (or N/A), and a pass/fail assessment of whether the fix addresses the issue's requirements. The 8 issues are: #43 (MATPOWER format bias in Suite G), #48 (formulation_difference tag needed), #49 (protocol thinning / agent-facing note duplication), #54 (Criterion 5 conflates maturity and sustainability), #55 (version-awareness gap), #56 (reviewer/approval concentration missing), #57 (intermediate CSV input path), #59 (formulation_difference decision procedure). Each row requires reading the actual file content at the cited location to confirm the fix is present — not just checking that the file was modified. Issues where the fix spans multiple files must have all locations verified independently.
- **Estimated tests:** 16
- **Dependencies:** Phase 1 (protocol and rubric artifacts), Phase 2 (skill file artifacts)

### 3. Protocol-to-Skill Traceability Audit
- **Description:** A bidirectional traceability audit between the v8 protocol and the skill machinery files. The audit has four sub-checks: (A) **Forward traceability** — extract every test ID from the v8 protocol (Suites A through G, including G-FNM-1 through G-FNM-5) and verify that each ID appears in at least one skill prompt (`code-evaluator-prompt.md`, `audit-evaluator-prompt.md`, `gate-evaluator-prompt.md`) or reference file (`test-methodology-notes.md`, `cross-tool-watchpoints.md`), either by literal mention or by config-driven dispatch that covers the ID's suite. (B) **Reverse traceability** — extract every test ID referenced in skill prompts and reference files and verify each exists in the v8 protocol. Flag any IDs that reference deleted or renumbered tests. (C) **PHASE2 marker cleanup** — scan the v8 protocol for any remaining `<!-- PHASE2 -->` HTML comments and verify none remain. For each forward reference in the protocol that points to `test-methodology-notes.md`, verify the referenced section exists in that file. (D) **Cross-reference integrity** — verify that skill prompts referencing watchpoint sections by name (e.g., "Formulation Sophistication Catalog") point to sections that actually exist in `cross-tool-watchpoints.md`, and that the SKILL.md orchestrator's variable replacement list includes all variables referenced in evaluator prompts (e.g., `{{version_capability_report}}`). Each sub-check produces a pass/fail result with evidence. Failures are categorized as "gap" (missing coverage), "dangling" (reference to nonexistent target), or "stale" (reference to moved/renamed content).
- **Estimated tests:** 18
- **Dependencies:** Phase 1 (protocol v8), Phase 2 (all skill files)

---

# Deliverable Dependencies

| # | Deliverable | Depends On | Enables |
|---|-------------|-----------|---------|
| 1 | Config Generation Smoke Test | Phase 1, Phase 2 | — |
| 2 | Cross-Reference Checklist | Phase 1, Phase 2 | — |
| 3 | Protocol-to-Skill Traceability Audit | Phase 1, Phase 2 | — |

**Implementation tiers:**

- **Tier 1:** Deliverables 1, 2, 3 (all three are independent verification activities with no intra-phase dependencies; they can proceed in parallel)

---

# Open Questions

None — all decisions resolved.
