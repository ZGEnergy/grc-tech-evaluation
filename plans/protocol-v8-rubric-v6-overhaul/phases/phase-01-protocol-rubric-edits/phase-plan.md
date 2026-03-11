# Purpose

The evaluation framework's two authoritative guide documents — the Phase 1 Test Protocol (v7) and the Phase 1 Evaluation Rubric (v5) — contain systematic issues documented across eight GitHub issues (#43, #48, #49, #54, #55, #56, #57, #59). The protocol penalizes tools for using more sophisticated formulations than MATPOWER by treating any DCPF deviation as a potential bug, even when the deviation is systematic and attributable to transformer/phase-shifter modeling that MATPOWER's simplified B-matrix construction ignores. The protocol also carries substantial agent-facing implementation detail that belongs in skill reference files, creating multi-way duplication between the protocol, watchpoints, and evaluator prompts. The rubric conflates demonstrated project maturity with forward-looking sustainability risk in a single criterion, making it impossible to distinguish a well-maintained project with concentrated governance from a broadly-governed project with poor engineering discipline.

Phase 1 updates both documents in a coordinated edit. The protocol moves from v7 to v8: Suite G's G-FNM-3/4 input path changes to reference the intermediate CSVs produced by Phase 0 as the primary path (with the cleaned MATPOWER `.m` as documented fallback), a formulation sophistication annotation system is added with a concrete `formulation_difference` tag decision procedure, agent-facing implementation notes are thinned from the protocol body (moved to skill reference files in Phase 2), and version compatibility rules are documented for mixed v5/v7/v8 result sets. The rubric moves from v5 to v6: Criterion 5 splits internally into 5a (Demonstrated Maturity) and 5b (Sustainability Risk) with a fully-defined 2x2 grade matrix, and reviewer/approval concentration is added as a 5b sub-metric.

The downstream consumer of this phase's outputs is Phase 2 (Skill Machinery Updates), which updates evaluator prompts and reference files to implement the protocol and rubric changes. Phase 2 cannot proceed until the authoritative documents are finalized because skill files must faithfully implement what the protocol specifies — changing both simultaneously would create circular dependencies.

---

# What This Phase Produces

**Output:** Two updated markdown documents in `evaluation_guides/`:

1. `Phase1_Test_Protocol.md` v8 — with G-FNM intermediate CSV input path, formulation sophistication annotations and `formulation_difference` tag decision procedure, protocol thinning (agent-facing notes removed or marked for Phase 2 extraction), version compatibility section for mixed-version result sets, and version bump in revision history.

2. `Phase1_Evaluation_Rubric.md` v6 — with Criterion 5 split into 5a (Demonstrated Maturity) and 5b (Sustainability Risk), a fully-defined 5a/5b grade matrix, reviewer/approval concentration as a sub-metric under 5b E-1 (contributor concentration), and version bump in revision history.

Net effect: ~100 lines changed in the protocol with ~50 lines net reduction (agent-facing content removed exceeds new content added). ~60 lines changed in the rubric (5a/5b split adds structure but the criterion count stays at 6).

**Downstream consumer:** Phase 2 (Skill Machinery Updates) reads both documents to update evaluator prompts, watchpoints, and the evaluate-tool skill orchestrator.

---

# Design Decisions

## G-FNM-3/4 intermediate CSV as primary input, MATPOWER `.m` as fallback

The v7 protocol specifies the cleaned MATPOWER case (`data/fnm/reference/cleaned/fnm_main_island.mat`) as the sole input for G-FNM-3 and G-FNM-4. This creates format bias: tools without a MATPOWER/pypower import path must build one as a prerequisite to power flow verification, and the merged branch/transformer table in MATPOWER format loses transformer-specific parameters that some tools model natively.

The v8 protocol changes the primary input path to the intermediate CSVs produced by Phase 0 (`data/fnm/reference/cleaned/intermediate/`). Tools load buses, branches, and transformers from separate CSV tables with explicit column names matching the intermediate schema. The cleaned MATPOWER `.m` remains as a documented fallback for tools that already have a working MATPOWER import path and prefer it. Both paths lead to the same DCPF reference solution (validated in Phase 0, Deliverable 4).

The protocol specifies that the result frontmatter must record which input path was used (`input_path: csv` or `input_path: matpower`), so cross-tool comparisons can account for any path-dependent differences.

## Formulation sophistication annotations with `formulation_difference` tag

Some tools use more accurate formulations than the MATPOWER-derived DCPF reference solution. For example, a tool that models transformer tap ratios in its B-matrix construction will produce systematically different bus angles and branch flows on branches connected to transformers with non-unity taps. Under v7, these deviations trigger the same outlier classification as genuine bugs, which penalizes the tool for being more accurate.

The v8 protocol adds a `formulation_difference` tag that the evaluator can apply to deviations meeting two criteria simultaneously: (1) the deviations are **systematic** — correlated with transformer or phase-shifter branches, not scattered randomly across the network, and (2) the deviations are **bounded** — within a maximum absolute threshold defined in `pass_conditions.json` (to be added as a new key). Deviations that are large or scattered cannot receive the tag without explicit written justification.

Tagged deviations are reported in the result file but do not count against the aggregate pass thresholds. This is not a blanket tolerance increase — it is a structured annotation that preserves the deviation data while preventing false failures from formulation sophistication.

The decision procedure is specified in the protocol as a numbered checklist that the evaluator follows for each deviation cluster, producing a deterministic tag/no-tag outcome.

## Protocol thinning: mark agent-facing notes for Phase 2 extraction

The v7 protocol contains ~20 inline notes, of which ~6 are purely agent-facing (implementation guidance for the evaluate-tool skill) and ~6 are hybrid (contain both evaluator-facing grading context and agent-facing implementation detail). Moving this content in Phase 1 would break the skill machinery before Phase 2 updates it.

The v8 protocol takes a two-step approach: (1) purely agent-facing notes are removed from the protocol body and replaced with a one-line forward reference (`See test-methodology-notes.md for implementation guidance`), and (2) hybrid notes are trimmed to retain only the evaluator-facing grading context, with the agent-facing portion marked as `<!-- PHASE2: move to test-methodology-notes.md -->` comments. Phase 2 then completes the extraction by creating `test-methodology-notes.md` and removing the HTML comments.

This approach achieves the net ~50 line reduction in the protocol while maintaining a working skill pipeline between Phase 1 and Phase 2.

## Version compatibility rules for mixed-version result sets

The evaluation has already produced results under protocol v5 (Suites A-F) and v7 (Suite G). The v8 protocol adds a Version Compatibility section that codifies the rules already implicit in v7's revision history:

- Results produced under v5 for Suites A-F remain valid and do not require re-evaluation.
- Results produced under v7 for Suite G remain valid for G-FNM-1, G-FNM-2, and G-FNM-5. G-FNM-3/4 results produced under v7 remain valid but the evaluator should note if the intermediate CSV path would have changed the outcome.
- Results produced under v8 use `protocol_version: "v8"` in frontmatter.
- The version compatibility section is normative — it is the authoritative source for which result-version combinations are valid.

## Criterion 5 split: 5a (Demonstrated Maturity) vs 5b (Sustainability Risk)

The v5 rubric treats maturity and sustainability as a single dimension. Research into CHAOSS and OpenSSF frameworks confirms that these are distinct concerns: a project can have strong demonstrated maturity (regular releases, good test coverage, active issue triage) but concentrated governance that creates sustainability risk, or vice versa. The current rubric's sub-questions (E-1 through E-7) mix backward-looking maturity evidence (release cadence, CI health, test coverage) with forward-looking risk indicators (contributor concentration, funding stability, governance model).

The v6 rubric splits Criterion 5 internally into two sub-criteria:

- **5a — Demonstrated Maturity:** Release engineering discipline, test coverage and CI health, issue responsiveness, operational adoption. These are backward-looking, evidence-based assessments of what the project has demonstrated.
- **5b — Sustainability Risk:** Contributor concentration, funding stability, governance model, reviewer/approval concentration. These are forward-looking risk assessments of what could go wrong.

The criterion count remains at 6 (contractual constraint). The 5a/5b split is internal — the final Criterion 5 grade is derived from the 5a and 5b sub-grades via a fully-defined grade matrix. The matrix handles the four quadrant cases: high maturity + low risk (A range), high maturity + high risk (B+ to B), low maturity + low risk (B to B-), low maturity + high risk (C range).

## Reviewer/approval concentration as a 5b sub-metric

GitHub's default branch protection allows a single reviewer to approve all PRs. A project where 90% of merges are approved by one person has a governance bottleneck that compounds the bus-factor risk already captured by commit concentration. The v6 rubric adds reviewer/approval concentration under 5b E-1 (contributor concentration, formerly original E-4): the evaluator samples the last 50 merged PRs and records what percentage were approved by the top reviewer. This is distinct from commit concentration (also in 5b E-1) — a project can have diverse committers but a single gatekeeper.

## 5a/5b grade matrix fully defined in rubric

The executive plan constraint requires the grade matrix to be defined in the rubric, not deferred to evaluator judgment. The matrix maps {5a grade band, 5b grade band} to a Criterion 5 composite grade:

| | 5b: A range | 5b: B range | 5b: C range |
|---|---|---|---|
| **5a: A range** | A/A- | B+/B | B/B- |
| **5a: B range** | B+/B | B/B- | C+/C |
| **5a: C range** | B-/C+ | C+/C | C/C- |

Within each cell, the evaluator selects from the two-grade range based on proximity to the boundary, justified by evidence. This is the same judgment mechanism used for +/- modifiers throughout the rubric, not a new discretionary mechanism.

---

# Deliverables

### 1. Protocol v8 — G-FNM Input Path and Formulation Annotations
- **Description:** Update the Suite G section of `Phase1_Test_Protocol.md` to specify intermediate CSVs as the primary G-FNM-3/4 input path with the cleaned MATPOWER `.m` as fallback. Add the `formulation_difference` tag definition and decision procedure to the Suite G notes. Add the `formulation_difference` maximum absolute threshold key to the pass conditions contract (the protocol specifies the key name and semantics; the actual threshold value lives in `pass_conditions.json`). Update the LARGE reference network row in the Reference Networks table to mention intermediate CSVs. Update G-FNM-3 and G-FNM-4 test descriptions to reference both input paths and require `input_path` in result frontmatter.
- **Estimated tests:** 12
- **Dependencies:** Phase 0 complete (intermediate CSVs must exist at the paths referenced)

### 2. Protocol v8 — Thinning and Version Compatibility
- **Description:** Remove purely agent-facing notes from the protocol body (replace with forward references to `test-methodology-notes.md`). Trim hybrid notes to evaluator-facing content only, marking agent-facing portions with `<!-- PHASE2 -->` comments. Add a Version Compatibility section after the Results Recording section that codifies rules for mixed v5/v7/v8 result sets. Update `protocol_version` references from `"v7"` to `"v8"`. Add v8 entry to the Revision History table. Verify net line reduction is approximately 50 lines.
- **Estimated tests:** 14
- **Dependencies:** 1 (the v8 revision history entry must include all v8 changes, so the G-FNM and formulation edits must be finalized first)

### 3. Rubric v6 — Criterion 5 Split (5a/5b) and Grade Matrix
- **Description:** Restructure Criterion 5 in `Phase1_Evaluation_Rubric.md` from a single section into 5a (Demonstrated Maturity) and 5b (Sustainability Risk). Reassign existing sub-questions E-1 through E-7 to the appropriate sub-criterion. Add reviewer/approval concentration as a new sub-metric under 5b E-1 (contributor concentration). Define separate grading standards for 5a and 5b. Add the composite grade matrix that maps {5a grade band, 5b grade band} to a Criterion 5 grade. Update the Quick Reference table footnote for Criterion 5. Update the Overview section's weighted criteria list to show the internal split. Add v6 entry to the Revision History table.
- **Estimated tests:** 14
- **Dependencies:** None (rubric edits are independent of protocol edits)

---

# Deliverable Dependencies

| # | Deliverable | Depends On | Enables |
|---|-------------|-----------|---------|
| 1 | Protocol v8 — G-FNM Input Path and Formulation Annotations | Phase 0 | 2 |
| 2 | Protocol v8 — Thinning and Version Compatibility | 1 | Phase 2 |
| 3 | Rubric v6 — Criterion 5 Split (5a/5b) and Grade Matrix | — | Phase 2 |

**Implementation tiers** (deliverables within a tier have no mutual dependencies):

- **Tier 1:** 1. Protocol v8 — G-FNM Input Path and Formulation Annotations, 3. Rubric v6 — Criterion 5 Split (5a/5b) and Grade Matrix
- **Tier 2:** 2. Protocol v8 — Thinning and Version Compatibility

---

# Open Questions

None — all decisions resolved.
