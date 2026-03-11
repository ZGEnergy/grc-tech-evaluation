# PRD-01: New Reference — test-methodology-notes.md

## Overview

Create `.claude/skills/evaluate-tool/references/test-methodology-notes.md` containing
agent-facing implementation notes extracted from the protocol during Phase 1's thinning
pass (PRD-02 of Phase 1). The protocol v8 thinning classified 20 inline notes into three
categories: 8 evaluator-facing (retained in protocol), 6 purely agent-facing (removed
from protocol, replaced with forward references), and 6 hybrid (trimmed to
evaluator-facing content, agent-facing portions marked with `<!-- PHASE2 -->`). This
deliverable receives the removed and marked content and organizes it into a single
reference file that evaluate-tool agents read at runtime.

This PRD creates a markdown reference file, not executable code. "Data Structures"
defines the section schema and note format. "API" defines validation functions for
checking the file's structure and completeness. "Success Criteria" lists the checks
that confirm correct extraction and organization.

## Goals

1. **Extract purely agent-facing notes.** The 6 notes whose bodies were removed from
   the protocol and replaced with `*See test-methodology-notes.md for implementation
   guidance.*` are reproduced in full in this file, organized by suite.

2. **Extract agent-facing portions of hybrid notes.** The agent-facing portions of 6
   hybrid notes — marked with `<!-- PHASE2: move to test-methodology-notes.md -->`
   in the v8 protocol — are extracted and placed in this file. The evaluator-facing
   portions remain in the protocol; this file contains only the agent-facing content.

3. **Preserve test ID traceability.** Every note in this file carries a header
   annotation listing the test IDs it applies to, enabling agents to find relevant
   guidance when evaluating a specific test.

4. **Provide a preamble explaining the relationship to the protocol.** Agents must
   understand that the protocol is authoritative for pass conditions and grading, and
   that this file provides supplementary implementation guidance for how to execute
   tests and make runtime decisions.

5. **Organize by suite with section anchors.** Notes are grouped under suite-level
   headers (Suite A, Suite B, Suite G) so agents evaluating a specific suite can
   navigate directly to the relevant section. Each section header produces a stable
   anchor for cross-referencing from prompts.

## Non-Goals

1. **No modification of the protocol.** The protocol was already thinned in Phase 1
   Deliverable 2. This PRD only creates the receiving file. It does not edit
   `Phase1_Test_Protocol.md`.

2. **No content rewriting.** The extracted notes are reproduced verbatim from their
   original protocol text (before removal/trimming). No editorial changes, no
   reformatting beyond the structural framing (headers, test ID annotations).

3. **No evaluator-facing content.** This file must not duplicate evaluator-facing
   content that remains in the protocol. Each note here is strictly agent-facing
   implementation guidance.

4. **No new implementation guidance.** This PRD extracts existing content. New
   guidance (e.g., formulation_difference procedure, CSV ingestion steps) is added
   by other Phase 2 PRDs in the code-evaluator prompt or watchpoints.

5. **No per-note files.** The design decision is a single file with section anchors,
   not a directory of individual note files.

## Data Structures

### File location

```
.claude/skills/evaluate-tool/references/test-methodology-notes.md
```

### Document schema

The file follows this structure:

```markdown
# Test Methodology Notes

<preamble paragraph>

---

## Suite A: Expressiveness

### <Note title> `[<test-IDs>]`

<note body>

### <Note title> `[<test-IDs>]`

<note body>

---

## Suite B: Extensibility

### <Note title> `[<test-IDs>]`

<note body>

---

## Suite G: FNM Ingestion

### <Note title> `[<test-IDs>]`

<note body>
```

### Preamble specification

The preamble paragraph must contain all of the following semantic elements:

| Element | Required content |
|---------|-----------------|
| Authority statement | The protocol (`Phase1_Test_Protocol.md`) is authoritative for test definitions, pass conditions, and grading standards. |
| Role statement | This file provides agent-facing implementation guidance: how to execute tests, runtime decision procedures, and calibration recipes. |
| Relationship | These notes were extracted from the protocol during the v7-to-v8 thinning pass to separate "what is tested and graded" (protocol) from "how tests are executed" (this file). |
| Usage instruction | Evaluate-tool agents should read the relevant suite section before executing tests in that suite. |

### Note format specification

Each note follows this format:

```markdown
### <Note title> `[<comma-separated test IDs>]`

<note body — verbatim from protocol>
```

**Header rules:**
- The note title is a concise descriptive name (e.g., "A-7 contingency sweep algorithm",
  "Resource type classification").
- Test IDs are enclosed in backtick-wrapped square brackets after the title.
- Multiple test IDs are comma-separated: `[A-8, B-4]`.
- Test IDs must use the exact format from the protocol (e.g., `A-7`, `G-FNM-1`).

### Note extraction inventory

The following table defines exactly which notes are extracted and where they come from.
The "Source" column references the Note Classification Table from Phase 1 PRD-02.

#### Purely agent-facing notes (full extraction)

| # | PRD-02 Note # | Title | Test IDs | Source content |
|---|---------------|-------|----------|----------------|
| 1 | #9 | Resource type classification | A-8, B-4 | Full body of "Note on resource type classification (A-8, B-4)": generator classification by cost curve slope (baseload, intermediate, peaker, wind/solar). |
| 2 | #10 | Performance loop methodology | C-1 through C-10 | Full body of "Note on performance loops": clone vs. reload, per-unit metrics recording. |
| 3 | #18 | Pass conditions runtime application | G-FNM-3, G-FNM-4 | Full paragraph on loading `pass_conditions.json` at runtime, applying thresholds programmatically, timeout handling. |
| 4 | #20 | Failure attribution procedure | G-FNM-1 through G-FNM-5 | Full body of "Note on failure attribution": decision procedure for attributing Suite G failures to Scalability vs. Expressiveness based on MEDIUM-scale performance. |

Note: Phase 1 PRD-02 specifies "~6 purely agent-facing" with up to 2 borderline
reclassifications. The classification table in PRD-02 definitively identifies 4 notes
(#8, #9, #10, #14, #16, #18). All 6 purely agent-facing notes are now confirmed.

#### Hybrid note agent-facing portions (partial extraction)

| # | PRD-02 Note # | Title | Test IDs | Extracted (agent-facing) content |
|---|---------------|-------|----------|----------------------------------|
| 5 | #2 | A-7 contingency sweep algorithm | A-7 | Steps 1-5 of the escalating pruned search algorithm (graph-distance enumeration, N-1 solve, pruning, N-2 combinations, escalation). |
| 6 | #3 | A-5 cycling augmentation recipes | A-5 | Three augmentation recipes: (a) increase PMIN to 30% of PMAX, (b) add 2-3 peaker generators with high startup cost, (c) widen load profile range to 40% minimum. |
| 7 | #8 | A-9 feasibility relaxation recipe | A-9 | Relaxation recipe: scale rateA to 150%, escalate to 200% if insufficient. |
| 8 | #13 | B-4 perturbation calibration | B-4 | Perturbation bound calibration instructions: infeasibility threshold (20%), sigma reduction procedure, slack variable alternative. |
| 9 | #14 | G-FNM-1 record-type merge verification | G-FNM-1 | Implementation detail on how to verify that merged record types produce the correct summed count against the manifest. |
| 10 | #19 | G-FNM-5 classification comparison | G-FNM-5 | Implementation detail on analytical vs. empirical representability classification comparison procedure. |

### Suite organization

Notes are placed under the following suite sections based on their primary test IDs:

| Suite section | Anchor | Notes (by inventory #) |
|---------------|--------|----------------------|
| Suite A: Expressiveness | `#suite-a-expressiveness` | #1, #5, #6, #7 |
| Suite B: Extensibility | `#suite-b-extensibility` | #8 |
| Suite C: Scalability | `#suite-c-scalability` | #2 |
| Suite G: FNM Ingestion | `#suite-g-fnm-ingestion` | #3, #4, #9, #10 |

Note #1 (Resource type classification, test IDs A-8 and B-4) is placed under Suite A
because A-8 is the primary test that defines the classification; B-4 references it.
A cross-reference note in Suite B points to the Suite A entry.

Note #2 (Performance loop methodology) applies to all C-tests but is agent-facing
execution methodology, so it is placed under Suite C.

## API

### File structure validation functions

These are verification functions that check the created file's structure and content.
They operate on the markdown text.

#### `validate_file_exists(references_dir: str) -> list[str]`

Check that the file exists at the expected location. Checks:

- `references/test-methodology-notes.md` exists in the evaluate-tool skill references
  directory.
- The file is non-empty (more than 20 lines).

#### `validate_preamble(file_text: str) -> list[str]`

Check the preamble section. Checks:

- The file starts with `# Test Methodology Notes`.
- A preamble paragraph exists before the first `## Suite` header.
- The preamble contains the word "authoritative" or "authority" in reference to
  the protocol.
- The preamble references `Phase1_Test_Protocol.md` by name.
- The preamble uses the phrase "implementation guidance" or equivalent.
- The preamble mentions the v7-to-v8 thinning or extraction.

#### `validate_suite_sections(file_text: str) -> list[str]`

Check the suite-level organization. Checks:

- At least 3 `## Suite` headers exist (A, B or C, G at minimum).
- Suite headers appear in protocol order (A before B/C before G).
- Each suite section contains at least one `### ` note header.
- No suite section is empty (contains only the header with no notes).

#### `validate_note_headers(file_text: str) -> list[str]`

Check that all note headers follow the format specification. Checks:

- Every `### ` header within a suite section contains a backtick-wrapped bracket
  annotation with test IDs (e.g., `` `[A-7]` ``).
- Test IDs use the protocol's format: letter-number or letter-prefix-number
  (e.g., `A-7`, `G-FNM-1`).
- No duplicate test IDs appear in the same note header.
- Every test ID referenced in a note header exists in the protocol's test tables.

#### `validate_note_count(file_text: str) -> list[str]`

Check completeness of extraction. Checks:

- The file contains at least 12 `### ` note headers (6 purely agent-facing +
  6 hybrid agent portions = 12).
- No more than 14 `### ` note headers exist (prevents accidental inclusion of
  evaluator-facing content).

#### `validate_purely_agent_content(file_text: str, protocol_v7_text: str) -> list[str]`

Cross-check that purely agent-facing notes are present. Checks:

- For each of the 6 confirmed purely agent-facing notes (#8, #9, #10, #14, #16, #18),
  verify that a distinguishing phrase from the note body appears in the file.
  Distinguishing phrases:
  - #8: "scale rateA" or "thermal limits" (A-9 feasibility relaxation)
  - #9: "cost curve slope as a proxy"
  - #10: "clone the base network object" or "per-unit metrics"
  - #14: "manifest file" and "source of truth" (G-FNM-1 record count)
  - #16: "pre-cleaned MATPOWER case" (G-FNM-3/4 routing)
  - #18: "loads the JSON at runtime" or "applies the thresholds programmatically"
- For each purely agent-facing note, verify that the corresponding forward
  reference (`test-methodology-notes.md`) exists in the v8 protocol at the
  original note location.

#### `validate_hybrid_content(file_text: str) -> list[str]`

Cross-check that hybrid note agent-facing portions are present. Checks:

- For each of the 6 hybrid notes (#2, #3, #8, #13, #14, #19), verify that a
  distinguishing phrase from the agent-facing portion appears in the file.
  Distinguishing phrases:
  - #2: "graph distance" and one of: "enumerate", "N-1 contingencies", "pruning"
  - #3: "PMIN to 30%" or "peaker generators with high startup cost"
  - #8: "scale rateA to 150%" or "escalate to 200%"
  - #13: "infeasibility threshold" or "sigma reduction" or "slack variable"
  - #14: "merged record types" or "summed count" or "constituent"
  - #19: "analytical vs. empirical" or "classification comparison"

#### `validate_no_evaluator_content(file_text: str) -> list[str]`

Verify that evaluator-facing content was NOT included. Checks:

- None of the 8 evaluator-facing notes' distinctive phrases appear in this file.
  Spot-check phrases:
  - #1 (TINY verification): should NOT contain "Scalability finding, not an
    Expressiveness failure" (this is evaluator grading guidance)
  - #4 (A-8 distinction): should NOT contain "native stochastic support.*loop
    over deterministic" (evaluator criterion boundary)
  - #5 (A-9 distinction): should NOT contain "SCOPF and post-hoc contingency
    analysis.*is critical" (evaluator criterion boundary)
  - #11 (generator cost curves): should NOT contain "evaluator documents which
    cost model" (evaluator recording requirement)
  - #12 (TINY for B-3): should NOT contain "46 branches.*full N-1" (evaluator
    parameter context)
- The evaluator-facing retained portions of hybrid notes should NOT be duplicated
  here. Spot-check:
  - #2 evaluator portion: should NOT contain "The contingency sweep is an
    escalating, pruned search" as a standalone sentence (that is the evaluator
    framing, not the algorithm steps)
  - #3 evaluator portion: should NOT contain "capacity-to-load ratio" as the
    opening phrase of a note (that is the evaluator rationale)

## Success Criteria

Each criterion is a verifiable check on the created file. They are grouped by the
aspect they verify.

### File creation and location (2 checks)

1. **SC-01: File exists at correct path.** The file
   `.claude/skills/evaluate-tool/references/test-methodology-notes.md` exists and
   is non-empty (at least 20 lines).

2. **SC-02: File is discoverable alongside existing references.** The file is in
   the same directory as the other reference files (`solver-config.md`,
   `cross-tool-watchpoints.md`, etc.) and follows the same kebab-case naming
   convention.

### Preamble (2 checks)

3. **SC-03: Preamble establishes protocol authority.** The preamble paragraph
   explicitly states that the protocol is authoritative for test definitions, pass
   conditions, and grading. This file provides supplementary implementation
   guidance only.

4. **SC-04: Preamble explains extraction origin.** The preamble explains that these
   notes were extracted from the protocol during the v7-to-v8 thinning pass, and
   references `Phase1_Test_Protocol.md` by filename.

### Structure and organization (3 checks)

5. **SC-05: Suite sections present and ordered.** The file contains `## Suite A`,
   `## Suite B` or `## Suite C`, and `## Suite G` sections (at minimum), in protocol
   order.

6. **SC-06: Note headers carry test ID annotations.** Every `###` note header
   includes a backtick-wrapped bracket annotation listing the applicable test IDs
   (e.g., `` `[A-7]` ``, `` `[A-8, B-4]` ``).

7. **SC-07: Section anchors are stable and referenceable.** Suite section headers
   produce valid markdown anchors (`#suite-a-expressiveness`, etc.) that can be
   referenced from prompt files via
   `test-methodology-notes.md#suite-a-expressiveness`.

### Content completeness — purely agent-facing (2 checks)

8. **SC-08: All purely agent-facing note bodies present.** The file contains the
   full body text of each purely agent-facing note that was removed from the
   protocol. At minimum, notes #9 (resource type classification), #10 (performance
   loops), #18 (pass conditions runtime), and #20 (failure attribution) are present.
   If Phase 1 reclassified additional borderline notes as purely agent-facing, those
   are also present.

9. **SC-09: Purely agent-facing notes are verbatim.** The extracted note bodies
   match the original v7 protocol text. No editorial rewriting, no semantic changes.
   Minor formatting adjustments (e.g., converting inline bold to headers) are
   acceptable; content changes are not.

### Content completeness — hybrid agent portions (2 checks)

10. **SC-10: All hybrid note agent-facing portions present.** The file contains the
    agent-facing portions of all 6 hybrid notes (#2, #3, #8, #13, #14, #19). Each
    is identifiable by its test ID annotation and contains the specific content
    listed in the "Extracted content" column of the hybrid extraction inventory.

11. **SC-11: Hybrid portions are the agent-facing content only.** For each hybrid
    note, only the agent-facing portion (marked with `<!-- PHASE2 -->` in the
    protocol) appears in this file. The evaluator-facing portion that remains in
    the protocol is not duplicated here.

### Content exclusion (1 check)

12. **SC-12: No evaluator-facing content included.** None of the 8 evaluator-facing
    notes (#1, #4, #5, #6, #7, #11, #12, and the evaluator portions of #15, #16,
    #17) appear in this file. The file contains zero grading guidance, criterion
    boundary definitions, or acceptance criteria language.

### Cross-reference integrity (2 checks)

13. **SC-13: Forward references in protocol point to this file.** Each removal site
    in the v8 protocol contains a forward reference line mentioning
    `test-methodology-notes.md`. This check is a cross-file verification against
    the Phase 1 PRD-02 output — if the forward references are already present from
    Phase 1, this check confirms they resolve to an existing file.

14. **SC-14: Test IDs in note headers are valid protocol test IDs.** Every test ID
    used in a note header annotation exists in the protocol's test tables (Suites
    A through G). No invented or misspelled test IDs.

### Consistency with existing references (1 check)

15. **SC-15: No content duplication with cross-tool-watchpoints.md.** Content that
    already exists in `cross-tool-watchpoints.md` (e.g., the Resource Type
    Classification section) is not duplicated in this file. If a topic appears in
    both files, the watchpoints version provides cross-tool context while this file
    provides the per-test execution procedure. A brief cross-reference note is
    acceptable; wholesale duplication is not.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `.claude/skills/evaluate-tool/references/test-methodology-notes.md` | Create | New reference file containing extracted agent-facing implementation notes organized by suite |

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

- **Phase 1 Deliverable 2 (protocol thinning) — must be complete.** The v8 protocol
  must have: (a) the 6 purely agent-facing notes removed and replaced with forward
  references to `test-methodology-notes.md`, and (b) the 6 hybrid notes trimmed with
  `<!-- PHASE2: move to test-methodology-notes.md -->` markers at the trim sites. This
  PRD reads the original v7 note text (from git history or the Phase 1 PRD-02
  specification) and the `<!-- PHASE2 -->` markers to determine what to extract.

- **cross-tool-watchpoints.md (exists).** The existing watchpoints file already contains
  a "Resource Type Classification" section. This PRD must avoid duplicating that content;
  the note in this file should provide the per-test execution procedure while the
  watchpoints section provides cross-tool context.

- **No downstream intra-phase dependencies.** This deliverable is Tier 1 within Phase 2
  and does not block any other Phase 2 deliverable. It is consumed by Phase 3 validation.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Single file with section anchors (not per-note files): confirmed.
- Organized by suite (A through G): confirmed.
- Test ID annotations in note headers: confirmed.
- Preamble explaining protocol relationship: confirmed.
- Verbatim extraction (no content rewriting): confirmed.
- 4 confirmed purely agent-facing + up to 2 reclassified: confirmed (implementer
  checks final v8 protocol for actual count).
