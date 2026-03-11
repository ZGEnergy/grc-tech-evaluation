# Purpose

Phase 1 updated the two authoritative guide documents (protocol v7 to v8, rubric v5 to v6), establishing the *what*: intermediate CSV input paths for Suite G, formulation_difference tag decision procedures, version compatibility rules, the 5a/5b maturity split, and reviewer/approval concentration metrics. But the evaluate-tool skill machinery — the prompts, references, and orchestrator that agents follow during an actual evaluation run — still reflects v7/v5 semantics. Without updating the skill layer, the v8 protocol would be a dead letter: the config-generator would parse v8 but the code-evaluator would not know how to apply formulation_difference tags, the research agents would not gather version-specific capability data, and the audit-evaluator would not assess reviewer concentration.

Phase 2 bridges the gap by updating every skill file that implements protocol or rubric semantics. The core changes are: (1) a new `test-methodology-notes.md` reference file that receives the agent-facing implementation notes factored out of the protocol during Phase 1 thinning (completing the two-step extraction), (2) expanded `cross-tool-watchpoints.md` with new sections covering Suite G format context, formulation sophistication, post-ingestion fidelity checks, and tool-specific pitfalls discovered during prior rounds, (3) a 4th research agent focused on version-awareness that produces a structured capability report, (4) code-evaluator prompt updates for the intermediate CSV input path, ingestion count verification gate, and formulation_difference tag procedure, (5) audit-evaluator prompt updates for reviewer/approval concentration in E-3, and (6) SKILL.md orchestrator updates to dispatch the 4th research agent and wire the version capability report into the code-evaluator's context.

The downstream consumer of this phase's outputs is Phase 3 (Validation), which verifies that all updated artifacts are internally consistent, that config generation succeeds against the v8 protocol, and that every protocol test ID has corresponding handling in the skill prompts with no dangling references to moved or deleted content. Phase 3 also verifies that the `<!-- PHASE2 -->` markers left in the protocol by Phase 1 Deliverable 2 have been addressed (the extracted content now lives in `test-methodology-notes.md`, so Phase 3 can confirm the markers are removable).

---

# What This Phase Produces

**Output:** Updates to 6 existing files and 1 new file in `.claude/skills/evaluate-tool/`:

1. **New file:** `references/test-methodology-notes.md` — contains 6 purely agent-facing notes extracted from the protocol plus agent-facing portions of 6 hybrid notes marked with `<!-- PHASE2 -->` in Phase 1.
2. **Updated:** `references/cross-tool-watchpoints.md` — 5 new sections added.
3. **Updated:** `prompts/research-prompt.md` — 4th version-awareness research agent with capability report schema.
4. **Updated:** `prompts/code-evaluator-prompt.md` — intermediate CSV input path, ingestion count gate, formulation_difference tag procedure.
5. **Updated:** `prompts/audit-evaluator-prompt.md` — reviewer/approval concentration in E-3.
6. **Updated:** `SKILL.md` — 4th research agent dispatch in RESEARCH state, version capability report consumer contract.

Estimated total: ~300 lines of new or changed content across these 7 files.

**Downstream consumer:** Phase 3 (Validation) uses these outputs along with the Phase 1 protocol/rubric to verify cross-artifact consistency and run a config generation smoke test.

---

# Design Decisions

## `test-methodology-notes.md` as a single reference file (not per-note files)

The 12 notes (6 purely agent-facing, 6 agent-facing portions of hybrid notes) are short (5-20 lines each) and topically interleaved — a SCUC cycling note relates to both expressiveness and scalability test methodology. Splitting them into individual files would create a proliferation of small references that evaluator agents must each discover and read. A single file with section anchors keeps the reference set compact while allowing the code-evaluator and audit-evaluator prompts to cite specific sections via `test-methodology-notes.md#section-anchor`.

The file is organized by protocol suite (A through G) so that agents evaluating a specific suite can scan the relevant section without reading the entire document. Each note preserves the test IDs it applies to in a header annotation for traceability back to the protocol.

## Version-awareness research agent produces a structured capability report

The 3 existing research agents produce free-form markdown. The 4th agent (version-awareness) must produce a structured capability report because its output is consumed programmatically by the code-evaluator: when a test exercises a capability that was added or changed in a specific version, the code-evaluator needs to check whether the installed version supports it.

The capability report schema includes: installed version string, release date, a capability table mapping protocol-relevant features (e.g., "SCUC formulation", "PTDF extraction", "CSV import") to {supported: bool, since_version: string, notes: string}, and a breaking changes list for versions between the installed version and the latest release. The schema is defined in `research-prompt.md` (Agent 4 section) and referenced by `code-evaluator-prompt.md` via the consumer contract in `SKILL.md`.

## Formulation_difference tag procedure in code-evaluator (not watchpoints)

The formulation_difference decision procedure is evaluator-facing methodology — it tells the code-evaluator agent exactly what steps to follow when a DCPF deviation cluster is detected. This belongs in the code-evaluator prompt (where it is actionable) rather than in cross-tool-watchpoints (which provides background context). However, the *background* context (why formulation differences arise, which tools are known to use more sophisticated B-matrix construction) does belong in watchpoints.

The split is: `cross-tool-watchpoints.md` gets a "Formulation Sophistication Catalog" section explaining the technical background, and `code-evaluator-prompt.md` gets the step-by-step decision procedure that references the watchpoints catalog for context.

## G-FNM input path update scoped to code-evaluator only

The intermediate CSV input path change affects only Suite G code tests (G-FNM-1 through G-FNM-5), which are dispatched exclusively via the code-evaluator agent. The audit-evaluator, gate-evaluator, and synthesis prompts do not reference FNM input paths directly — they consume the results produced by the code-evaluator. Therefore, only `code-evaluator-prompt.md` and `SKILL.md` (which passes FNM reference files to the code-evaluator) require updates for the input path change.

## Reviewer/approval concentration scoped to E-3 in audit-evaluator

The rubric v6 adds reviewer/approval concentration as a sub-metric under E-3 in Criterion 5b. The audit-evaluator prompt already has an E-3 section ("Contributor concentration"). The update extends E-3's methodology to include sampling the last 50 merged PRs for reviewer concentration, making it a sibling metric to commit concentration rather than a separate test ID. This keeps the test ID count stable while expanding the evidence gathered.

## SKILL.md changes are minimal and structural

The SKILL.md orchestrator is the highest-risk file to edit because it controls agent dispatch for the entire evaluation. The changes are confined to two locations: (1) the RESEARCH state gains a 4th parallel agent dispatch with the version-awareness focus string, and (2) the EVALUATE state's code-evaluator variable replacement gains a `{{version_capability_report}}` variable populated from the 4th research agent's output. No state machine logic, error handling, or observation routing changes are required.

---

# Deliverables

### 1. New Reference: test-methodology-notes.md
- **Description:** Create `references/test-methodology-notes.md` containing the agent-facing implementation notes extracted from the protocol during Phase 1's thinning pass. This includes the 6 purely agent-facing notes that were replaced with forward references in the protocol, plus the agent-facing portions of 6 hybrid notes that were marked with `<!-- PHASE2: move to test-methodology-notes.md -->` comments in the v8 protocol. Each note is organized under a suite-level section header (Suites A through G) with test ID annotations. The file also includes a preamble explaining its relationship to the protocol (agents read this file for implementation guidance; the protocol is authoritative for pass conditions and grading).
- **Estimated tests:** 14
- **Dependencies:** Phase 1 Deliverable 2 (protocol thinning must be complete so the `<!-- PHASE2 -->` markers and forward references exist)

### 2. Updated Reference: cross-tool-watchpoints.md
- **Description:** Add 5 new sections to `references/cross-tool-watchpoints.md`: (1) **Suite G Format Context** — explains the intermediate CSV format, the baseMVA sidecar, the transformer vs. line distinction, and why tools should prefer the CSV path over the MATPOWER `.m` fallback; (2) **Formulation Sophistication Catalog** — documents which tools use simplified vs. full B-matrix construction, how transformer tap ratios and phase-shifter angles produce systematic DCPF deviations, and expected deviation magnitudes; (3) **Post-Ingestion Fidelity Checks** — lists verification steps after CSV ingestion (bus count, branch count, transformer count, baseMVA, slack bus identification, tap ratio preservation); (4) **baseMVA and Q-Limit Pitfalls** — documents the baseMVA unit convention in the intermediate CSVs and the Q-limit representation that can cause false ACPF failures; (5) **PowerModels solve_dc_pf Pitfall** — documents that PowerModels.jl's `solve_dc_pf` may silently return a trivial solution under certain conditions, requiring result validation.
- **Estimated tests:** 10
- **Dependencies:** None (watchpoints content is factual background, not dependent on other deliverables)

### 3. Updated Prompt: research-prompt.md (Version-Awareness Agent)
- **Description:** Add a 4th research agent specification to `prompts/research-prompt.md`. Agent 4 focuses on version-awareness: it identifies the installed version of the tool, researches the changelog and release notes for that version and adjacent versions, and produces a structured capability report. The report schema is defined inline in the prompt: installed version, release date, a capability table (feature name, supported boolean, since_version, notes), and a breaking changes list. The focus-specific guidance section gains a new block for "version" or "capability" focus. The output path uses `research-version.md` as the focus slug.
- **Estimated tests:** 10
- **Dependencies:** None (prompt content is self-contained)

### 4. Updated Prompt: code-evaluator-prompt.md
- **Description:** Three updates to `prompts/code-evaluator-prompt.md`: (1) **G-FNM intermediate CSV input path** — update the FNM Ingestion (Suite G) Methodology section to specify intermediate CSVs at `$FNM_PATH/intermediate/` as the primary input path, with the cleaned MATPOWER `.m` as fallback; update G-FNM-1 guidance to load from CSVs and verify record counts against manifest; update G-FNM-3/4 guidance to prefer the CSV path and record `input_path` in result frontmatter. (2) **Ingestion count verification gate** — add a post-ingestion verification step to G-FNM-1 that explicitly checks each table's record count against the manifest and fails the gate if any mismatch is detected, with structured error reporting. (3) **Formulation_difference tag procedure** — add a new Methodology Guardrails subsection with the step-by-step decision procedure for applying the `formulation_difference` tag to DCPF deviation clusters in G-FNM-3, referencing the Formulation Sophistication Catalog in watchpoints for background context. (4) **Version capability report consumption** — add a `{{version_capability_report}}` input variable and a guardrail that the code-evaluator checks installed version capabilities before attempting tests that depend on version-specific features.
- **Estimated tests:** 16
- **Dependencies:** 2 (references the formulation sophistication catalog in watchpoints), 3 (references the version capability report schema)

### 5. Updated Prompt: audit-evaluator-prompt.md
- **Description:** Update `prompts/audit-evaluator-prompt.md` to expand the E-3 methodology for Criterion 5b's reviewer/approval concentration sub-metric. The current E-3 section covers commit concentration (top 3 contributors by commits, bus factor). The update adds: sample the last 50 merged PRs via GitHub API or `gh` CLI, record the percentage approved by the top reviewer, record the percentage approved by the top 3 reviewers, flag if top reviewer approved >60% of PRs as a concentration risk. The finding is reported as a sibling metric to commit concentration within the same E-3 result file, with a dedicated "Reviewer Concentration" subsection in the Evidence section. Also add a note that E-3 now contributes to both 5a (commit activity as maturity evidence) and 5b (concentration as sustainability risk), consistent with the rubric v6 5a/5b split.
- **Estimated tests:** 8
- **Dependencies:** None (audit prompt changes are self-contained)

### 6. Updated Orchestrator: SKILL.md
- **Description:** Two updates to `SKILL.md`: (1) **RESEARCH state — 4th agent dispatch.** Add Agent 4 to the parallel research dispatch with focus string `"Version-specific capabilities: installed version identification, changelog analysis, capability mapping to protocol test requirements, breaking changes between installed and latest versions"`. Set output path to `{{RESULTS_DIR}}/research-version.md`. Update the merge step to concatenate 4 research files instead of 3. Update the thin-research warning to cover 4 files. (2) **EVALUATE state — version capability report consumer contract.** In the variable replacement list for code-evaluator agents, add `{{version_capability_report}}` mapped to the contents of `{{RESULTS_DIR}}/research-version.md`. Add a note that if the version capability report indicates a feature is unsupported in the installed version, the code-evaluator should record the test as `fail` with `failure_reason: unsupported_in_installed_version` rather than attempting it and producing a misleading error.
- **Estimated tests:** 10
- **Dependencies:** 3 (the capability report schema must be defined in research-prompt.md before SKILL.md can reference its output contract), 4 (the code-evaluator must accept the `{{version_capability_report}}` variable)

### 7. Updated Prompt: config-generator-prompt.md
- **Description:** Update `prompts/config-generator-prompt.md` to reflect v8 protocol changes: add `formulation_difference` to the observation tag vocabulary with correct emit/consume wiring, set `protocol_version: "v8"` in generated config headers, encode the 5a/5b Criterion 5 sub-criteria split in the maturity dimension structure, and update the LARGE network tier to reference intermediate CSV paths at `$FNM_PATH/intermediate/` with manifest and MATPOWER fallback.
- **Estimated tests:** 14
- **Dependencies:** Phase 1 (protocol v8 and rubric v6 define the content this prompt must encode)

---

# Deliverable Dependencies

| # | Deliverable | Depends On | Enables |
|---|-------------|-----------|---------|
| 1 | test-methodology-notes.md | Phase 1 D2 | Phase 3 |
| 2 | cross-tool-watchpoints.md | — | 4 |
| 3 | research-prompt.md | — | 4, 6 |
| 4 | code-evaluator-prompt.md | 2, 3 | 6 |
| 5 | audit-evaluator-prompt.md | — | Phase 3 |
| 6 | SKILL.md | 3, 4 | Phase 3 |
| 7 | config-generator-prompt.md | Phase 1 | Phase 3 |

**Implementation tiers:**

- **Tier 1:** Deliverables 1, 2, 3, 5, 7 (no intra-phase dependencies; can proceed in parallel)
- **Tier 2:** Deliverable 4 (depends on watchpoints and research-prompt from Tier 1)
- **Tier 3:** Deliverable 6 (depends on research-prompt and code-evaluator from Tiers 1-2)

---

# Open Questions

None — all decisions resolved.
