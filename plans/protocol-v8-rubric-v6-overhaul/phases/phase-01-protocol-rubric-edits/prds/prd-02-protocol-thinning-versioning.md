# PRD-02: Protocol v8 — Thinning and Version Compatibility

## Overview

Thin the inline notes in `evaluation_guides/Phase1_Test_Protocol.md` by removing
purely agent-facing content, trimming hybrid notes to their evaluator-facing
portions, and inserting forward references to a future `test-methodology-notes.md`
file (created in Phase 2). Add a normative Version Compatibility section after
Results Recording that codifies how mixed-version result sets (v5/v7/v8) coexist.
Update all `protocol_version` references from `"v7"` to `"v8"`. Add the v8 entry
to the Revision History table. Target a net reduction of approximately 50 lines.

This PRD edits a markdown document (the protocol). "Data Structures" defines the
note classification taxonomy and version compatibility rules. "API" defines
verification functions for checking the edits. "Success Criteria" lists the checks
that confirm correctness.

## Goals

1. **Remove purely agent-facing notes.** Six notes whose content is exclusively
   implementation guidance for the evaluate-tool agent are removed from the
   protocol body. Each removal site gets a one-line forward reference:
   `*See test-methodology-notes.md for implementation guidance.*`

2. **Trim hybrid notes.** Six notes that contain both evaluator-facing and
   agent-facing content are trimmed to retain only the evaluator-facing portion.
   The removed agent-facing portion is marked with an HTML comment
   `<!-- PHASE2: move to test-methodology-notes.md -->` at the removal site so
   Phase 2 can extract it cleanly.

3. **Preserve evaluator-facing notes.** Eight notes that are entirely
   evaluator-facing (grading guidance, criterion definitions, acceptance
   criteria) are left unchanged.

4. **Version Compatibility section.** Add a new normative section after Results
   Recording that defines rules for mixed-version result sets: which protocol
   versions are valid for which suites, what happens to results produced under
   older versions, and when re-evaluation is required.

5. **Protocol version bump.** Update all `protocol_version` string references
   from `"v7"` to `"v8"`. This includes the Recording paragraph for Suite G
   and the Results Recording section.

6. **Revision History v8 row.** Add a v8 entry summarizing: note thinning,
   version compatibility section, protocol version bump. This row also
   incorporates PRD-01 changes (G-FNM input path, formulation_difference tag)
   since both PRDs contribute to v8.

## Non-Goals

1. **No creation of `test-methodology-notes.md`.** That file is created in
   Phase 2. This PRD only inserts forward references to it.

2. **No changes to test definitions (Suites A-G tables).** Test descriptions,
   pass conditions, and parameters in the table rows are not modified. Only the
   inline notes below the tables are affected.

3. **No changes to the rubric.** Rubric edits are PRD-03.

4. **No changes to Suite G test descriptions or `pass_conditions.json`.** Those
   are PRD-01.

5. **No removal of the Recording paragraphs.** The `**Recording for each
   X-test:**` lines are evaluator-facing and are retained. Only
   `protocol_version` values within them are updated.

6. **No content rewriting.** Evaluator-facing portions of hybrid notes are kept
   verbatim. Trimming means removing agent-facing sentences/paragraphs, not
   rewriting the remaining content.

## Data Structures

### Note Classification Taxonomy

Every `**Note on ...**` block (and un-headed continuation paragraphs in the
Suite G notes section) is classified into one of three categories:

| Category | Definition | Action |
|----------|-----------|--------|
| `purely_agent` | Content is exclusively implementation guidance for the evaluate-tool agent (how to run code, what to clone, runtime decisions). No evaluator-relevant grading or acceptance information. | Remove body. Insert forward reference line. |
| `hybrid` | Contains both evaluator-facing content (grading guidance, criterion definitions, acceptance parameters) and agent-facing content (execution instructions, calibration steps, runtime decisions). | Trim to evaluator-facing content only. Mark removed portion with `<!-- PHASE2: move to test-methodology-notes.md -->`. |
| `evaluator` | Content is entirely evaluator-facing: grading guidance, criterion distinctions, acceptance criteria, domain context that informs grade assignment. | No change. |

### Note Classification Table

The protocol contains 20 distinct note blocks. Classification:

| # | Line | Note ID | Category | Rationale |
|---|------|---------|----------|-----------|
| 1 | 183 | Note on TINY verification | `evaluator` | Grading guidance: defines TINY pass semantics and failure attribution. |
| 2 | 185 | Note on A-7 | `hybrid` | Evaluator: algorithm spec, what is tested, pass parameters. Agent: step-by-step execution procedure (graph-distance enumeration, pruning loop). |
| 3 | 187 | Note on A-5 cycling requirement | `hybrid` | Evaluator: cycling requirement rationale, acceptance threshold (2 generators). Agent: three augmentation recipes (PMIN, peakers, load range). |
| 4 | 189 | Note on A-8 | `evaluator` | Criterion distinction: native stochastic vs. loop-wrapped. Grading boundary. |
| 5 | 191 | Note on A-9 | `evaluator` | Criterion distinction: SCOPF vs. post-hoc contingency analysis. Domain context. |
| 6 | 193 | Note on A-10 | `evaluator` | Acceptance criteria: lists valid loss methods, defines internal consistency checks. |
| 7 | 195 | Note on A-11 | `evaluator` | Domain context: ISO slack practices. Grading guidance for LMP comparison. |
| 8 | 197 | Note on A-9 feasibility on case39 | `hybrid` | Evaluator: thermal limits may cause infeasibility (data finding context). Agent: specific relaxation recipe (150%, escalate to 200%). |
| 9 | 199 | Note on resource type classification | `purely_agent` | Implementation detail: how to classify generators by cost tier for stochastic perturbations. No grading or acceptance content. |
| 10 | 201 | Note on performance loops | `purely_agent` | Execution instruction: clone vs. reload, record per-unit metrics. No grading content. |
| 11 | 203 | Note on generator cost curves | `evaluator` | Recording requirement: document cost model, piecewise-linear support finding. |
| 12 | 225 | Note on TINY for B-3 | `evaluator` | Explains parameter choice (46 branches vs. 50). Grading context. |
| 13 | 227 | Note on B-4 | `hybrid` | Evaluator: what B-4 tests, key evaluation factors. Agent: calibration instructions (infeasibility threshold, sigma reduction), slack variable guidance. |
| 14 | 334 | Note on G-FNM-1 | `hybrid` | Evaluator: manifest is source of truth, not PSS/E header. Agent: implementation detail on record-type merging verification. |
| 15 | 336 | Note on G-FNM-2 | `evaluator` | Defines "present" for field coverage. Distinguishes structural vs. numerical fidelity. |
| 16 | 338 | Note on G-FNM-3 and G-FNM-4 | `evaluator` | Input clarification: cleaned case vs. raw intermediate format. Scope for each test. |
| 17 | 340 | G-FNM-4 reframing (continuation) | `evaluator` | Evaluator context: why G-FNM-4 is a convergence capability test. |
| 18 | 342 | Pass conditions runtime (continuation) | `purely_agent` | Agent runtime instructions: load JSON, apply thresholds programmatically, timeout handling. |
| 19 | 344 | Note on G-FNM-5 | `hybrid` | Evaluator: what the test bridges, why discrepancies matter. Agent: implementation detail on analytical vs. empirical classification comparison. |
| 20 | 346 | Note on failure attribution | `purely_agent` | Agent decision procedure: how to attribute failures to Scalability vs. Expressiveness. No evaluator grading content (evaluator makes this call independently). |

**Summary:** 8 evaluator, 6 hybrid, 6 purely_agent.

Note: Notes #16 and #17 are on separate lines but form a single logical note
block. Note #18 is a separate paragraph with distinct (purely agent-facing)
content. The line numbers above reflect the current v7 protocol; PRD-01 edits
may shift them before this PRD executes.

### Purely Agent-Facing Notes — Removal Targets

The 6 notes removed are replaced with:

```markdown
*See test-methodology-notes.md for implementation guidance.*
```

For notes #18 and #20 (in the Suite G notes section), the forward reference is
placed at the removal site to preserve reading order. If two adjacent removals
would produce duplicate forward references, they are collapsed into a single
reference line.

Removed notes (body relocated in Phase 2):

1. **#9 — Note on resource type classification (A-8, B-4):** Full text removed.
2. **#10 — Note on performance loops:** Full text removed.
3. **#18 — Pass conditions runtime (continuation):** Full paragraph removed.
4. **#20 — Note on failure attribution:** Full text removed.
5. **#4 (re-evaluated):** — See hybrid classification; if after closer inspection
   during implementation the evaluator portion is empty, reclassify as
   purely_agent. The classification table above is the authority.

Note: Only 4 notes are definitively purely_agent from the table above. The
design decision specifies ~6. During implementation, the implementer must
confirm each classification against the taxonomy and may reclassify up to 2
borderline cases. The classification table is updated in the commit to reflect
final decisions. The target of ~6 removals and ~6 trims is approximate.

### Hybrid Notes — Trimming Targets

For each hybrid note, the retained (evaluator-facing) and removed (agent-facing)
portions are:

**#2 — Note on A-7:**
- Retain: "The contingency sweep is an escalating, pruned search — not a flat
  N-1 loop." + what is tested (graph-distance scoping, efficient re-solve,
  programmability) + scale parameters (TINY: x=3, m=3; MEDIUM: x=5, m=2) +
  N-3/N-4 informational-only statement.
- Remove (PHASE2): Step-by-step algorithm description (steps 1-5).

**#3 — Note on A-5 cycling requirement:**
- Retain: Rationale (capacity-to-load ratio makes decommitment uneconomical) +
  requirement (at least 2 generators cycling).
- Remove (PHASE2): Three augmentation recipes (a), (b), (c).

**#8 — Note on A-9 feasibility on case39:**
- Retain: "The IEEE 39-bus case has tight thermal limits that may make preventive
  SCOPF infeasible on TINY." + "This is a data finding, not a tool limitation."
- Remove (PHASE2): Relaxation recipe (scale rateA to 150%, escalate to 200%).

**#13 — Note on B-4:**
- Retain: What B-4 tests (effort to wrap a tool for stochastic analysis) + key
  evaluation factors (timeseries injection, model re-solve, results collection) +
  temporal correlation requirement.
- Remove (PHASE2): Perturbation bound calibration instructions (infeasibility
  threshold, sigma reduction), slack variable alternative.

**#14 — Note on G-FNM-1:**
- Retain: "The manifest is the source of truth for record counts — it is not the
  PSS/E header record count" + why counts may differ (parser handling).
- Remove (PHASE2): Implementation detail on how to verify merged record types.

**#19 — Note on G-FNM-5:**
- Retain: "This test bridges data model assessment and extensibility assessment"
  + what the 7 supplemental CSVs carry + discrepancies are valuable findings.
- Remove (PHASE2): Implementation detail on analytical vs. empirical
  classification comparison procedure.

### Version Compatibility Rules

A new section titled **"Version Compatibility"** is inserted after the Results
Recording section and before "From Test Results to Grades". It is normative
(binding on evaluators and agents).

Content:

```markdown
## Version Compatibility

This section defines how results produced under different protocol versions
coexist in a single evaluation.

### Valid Protocol Versions by Suite

| Suite | Valid Versions | Notes |
|-------|---------------|-------|
| A-F (Gate, Expressiveness, Extensibility, Scalability, Accessibility, Maturity, Supply Chain) | v5, v7, v8 | v5 test definitions for Suites A-F are unchanged in v7 and v8. Results produced under v5 remain valid and do not require re-evaluation. |
| G (FNM Ingestion) | v7, v8 | Suite G was introduced in v6 and stabilized in v7. v6 results (before cleaned case export and G-FNM-4 reframing) should be re-evaluated under v7 or v8. |

### Version-Specific Notes

- **v7 → v8 for G-FNM-3 and G-FNM-4:** v8 introduces the `input_path`
  frontmatter field and the `formulation_difference` tag for G-FNM-3/4. Existing
  v7 results for G-FNM-3/4 that lack `input_path` remain valid but should be
  annotated with the input path used when the information is recoverable. v7
  results for G-FNM-1, G-FNM-2, and G-FNM-5 are fully valid under v8 without
  modification.

- **New results use v8.** All results produced after this protocol version is
  adopted must use `protocol_version: "v8"` in YAML frontmatter.

- **Mixed-version result sets are expected.** A tool evaluation may contain v5
  results for Suites A-F and v7 or v8 results for Suite G. This is the normal
  case, not an error. When comparing results across tools, ensure the same
  protocol version was used for the tests being compared.

- **Re-evaluation triggers.** A result must be re-evaluated under the current
  protocol version only when the current version changes the test definition,
  pass condition, or required frontmatter for that specific test. Version bumps
  that do not alter a test's definition do not invalidate existing results.
```

### Revision History v8 Row

The v8 row in the Revision History table. This row covers both PRD-01 and
PRD-02 changes since both contribute to the v8 release:

```markdown
| v8 | 2026-03-10 | Protocol thinning: removed purely agent-facing notes (forward references to test-methodology-notes.md), trimmed hybrid notes to evaluator-facing content. Added Version Compatibility section (mixed v5/v7/v8 result set rules). G-FNM-3/4 input path: intermediate CSVs as primary input with cleaned MATPOWER .m as fallback; added `input_path` frontmatter field. Added `formulation_difference` tag with 6-step decision procedure for G-FNM-3/4. Added `formulation_difference_max_abs` threshold key to pass_conditions.json. Updated LARGE reference network row. All protocol_version references updated to "v8". | GRC |
```

## API

### Protocol document validation functions

These are verification functions that check the updated protocol document
content. They operate on the markdown text, not on runtime data.

#### `validate_note_removals(protocol_text: str) -> list[str]`

Scan for the bodies of the 6 purely agent-facing notes (identified by their
opening phrases). Return validation errors. Checks:

- None of the 6 removed note bodies appear in the protocol text.
- For each removal site, a forward reference line containing
  `test-methodology-notes.md` exists within 2 lines of where the note was.
- No duplicate adjacent forward reference lines (collapsed if consecutive).

#### `validate_hybrid_trims(protocol_text: str) -> list[str]`

For each of the 6 hybrid notes, verify trimming. Checks:

- The evaluator-facing portion (identified by key phrases from the "Retain"
  specs above) is still present.
- The agent-facing portion (identified by key phrases from the "Remove" specs
  above) is absent from the visible markdown.
- An HTML comment containing `PHASE2` exists at each trim site.

#### `validate_evaluator_notes_unchanged(protocol_text: str, original_text: str) -> list[str]`

Compare the 8 evaluator-facing notes between the original and updated protocol.
Checks:

- Each evaluator-facing note is byte-identical between original and updated
  protocol (no accidental edits).

#### `validate_version_compatibility_section(protocol_text: str) -> list[str]`

Check the new Version Compatibility section. Checks:

- A section headed `## Version Compatibility` exists.
- It appears after `## Results Recording` and before `## From Test Results to Grades`.
- It contains a table with columns for Suite, Valid Versions, and Notes.
- Suites A-F row lists v5, v7, v8 as valid.
- Suite G row lists v7, v8 as valid (not v6).
- A bullet point states that new results use `protocol_version: "v8"`.
- A bullet point states that mixed-version result sets are expected.

#### `validate_protocol_version_refs(protocol_text: str) -> list[str]`

Check all `protocol_version` string references. Checks:

- No occurrence of `protocol_version: "v7"` remains in the protocol text.
- At least one occurrence of `protocol_version: "v8"` exists.
- The Results Recording section references `"v8"`.
- The Suite G Recording paragraph references `"v8"`.

#### `validate_revision_history_v8(protocol_text: str) -> list[str]`

Check the Revision History table. Checks:

- A v8 row exists.
- The v8 row mentions note thinning or test-methodology-notes.
- The v8 row mentions version compatibility.
- The v8 row mentions G-FNM input path or intermediate CSV.
- The v8 row mentions `formulation_difference`.
- The v8 row mentions `protocol_version` updated to v8.

#### `validate_line_reduction(original_text: str, updated_text: str) -> list[str]`

Compare line counts. Checks:

- The updated protocol has fewer lines than the original.
- Net reduction is between 30 and 70 lines (approximate target: 50).
- The reduction comes from note removal/trimming, not from deleting test
  definitions or other structural content.

## Success Criteria

Each criterion is a verifiable check on the updated protocol document. They
are grouped by the aspect they verify.

### Note thinning — removals (3 checks)

1. **SC-01: Purely agent-facing note bodies removed.** None of the 6 purely
   agent-facing note bodies (identified by their distinctive opening phrases)
   appear in the updated protocol. Specifically:
   - "Note on resource type classification" body absent
   - "Note on performance loops" body absent
   - Pass conditions runtime paragraph (L342) absent
   - "Note on failure attribution" body absent
   - Plus up to 2 additional notes reclassified from the borderline set

2. **SC-02: Forward references inserted.** Each removal site contains a forward
   reference line mentioning `test-methodology-notes.md`. Adjacent removals
   share a single forward reference (no duplicates).

3. **SC-03: No orphaned context.** No forward reference appears without a
   preceding or following evaluator-facing note — the forward references are
   placed in context, not floating.

### Note thinning — trims (3 checks)

4. **SC-04: Hybrid note evaluator content retained.** For each of the 6 hybrid
   notes, the evaluator-facing portion (as specified in the Retain column of the
   Data Structures section) is present in the updated protocol verbatim.

5. **SC-05: Hybrid note agent content removed.** For each of the 6 hybrid notes,
   the agent-facing portion (as specified in the Remove column) does not appear
   in the visible markdown text.

6. **SC-06: PHASE2 markers present.** Each hybrid note trim site contains an
   HTML comment matching `<!-- PHASE2: move to test-methodology-notes.md -->` (or
   a close variant with the same semantics).

### Note thinning — preservation (1 check)

7. **SC-07: Evaluator-facing notes unchanged.** All 8 evaluator-facing notes are
   byte-identical between the original v7 protocol and the updated v8 protocol.
   No accidental edits, no whitespace changes.

### Version Compatibility section (3 checks)

8. **SC-08: Section exists and is correctly positioned.** A `## Version
   Compatibility` section exists in the protocol, positioned after `## Results
   Recording` and before `## From Test Results to Grades`.

9. **SC-09: Suite validity table is correct.** The version compatibility table
   lists Suites A-F as valid under v5, v7, and v8. Suite G is valid under v7
   and v8 only (v6 explicitly excluded with re-evaluation guidance).

10. **SC-10: Mixed-version and re-evaluation rules stated.** The section states
    that (a) new results use `protocol_version: "v8"`, (b) mixed-version result
    sets are expected, and (c) re-evaluation is triggered only when a version
    changes the specific test's definition or pass condition.

### Protocol version bump (2 checks)

11. **SC-11: No v7 protocol_version references remain.** The string
    `protocol_version: "v7"` does not appear anywhere in the updated protocol.

12. **SC-12: v8 protocol_version references present.** The string
    `protocol_version: "v8"` appears in at least: (a) the Suite G Recording
    paragraph, (b) the Results Recording section's frontmatter guidance.

### Revision History (2 checks)

13. **SC-13: v8 row exists with correct date.** The Revision History table
    contains a v8 row dated 2026-03-10.

14. **SC-14: v8 row content is comprehensive.** The v8 revision history row
    references all of: note thinning, version compatibility section,
    `protocol_version` update to v8, G-FNM input path changes (PRD-01),
    `formulation_difference` tag (PRD-01).

### Line reduction (1 check)

15. **SC-15: Net line reduction is approximately 50.** The updated protocol has
    30-70 fewer lines than the original v7 protocol (before PRD-01 edits). The
    reduction comes from note removal and trimming, not from deleting test
    definitions or structural content.

### Structural integrity (1 check)

16. **SC-16: No test definition alterations.** The test tables for Suites A
    through G (the `| ID | ... |` rows) are byte-identical between the original
    and updated protocol. Only the inline notes, Recording paragraphs (version
    string only), and new sections are changed.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `evaluation_guides/Phase1_Test_Protocol.md` | Edit | Remove purely agent-facing notes, trim hybrid notes, add PHASE2 markers, add Version Compatibility section, update protocol_version to v8, add v8 revision history row |

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

- **PRD-01 (must be applied first).** PRD-01 modifies the Suite G section
  (G-FNM-3/4 descriptions, formulation_difference notes, LARGE row) and writes
  the initial v8 revision history row. This PRD builds on that state: it thins
  the notes (including any PRD-01 additions that are agent-facing), updates the
  v8 revision history row to also cover thinning and version compatibility, and
  bumps all remaining `protocol_version: "v7"` references to `"v8"`. If PRD-01
  has not been applied, the note classification line numbers will be off and the
  revision history row will be incomplete.

- **PRD-03 (independent).** PRD-03 edits the rubric, not the protocol. No
  ordering dependency in either direction.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Two-step thinning (Phase 1 marks, Phase 2 extracts): confirmed.
- ~6 purely agent-facing removals, ~6 hybrid trims: confirmed (exact count may
  vary by +/-2 based on final classification judgment).
- Version compatibility as normative section: confirmed.
- v5 results valid for A-F, v7 results valid for G: confirmed.
- Net line reduction target ~50: confirmed.
