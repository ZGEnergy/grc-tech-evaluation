# Content Rules for Customer-Facing Report

These rules apply to ALL generated content in the report site: MDX pages, the selection
report markdown, and JSON data file descriptions. They are non-negotiable.

## Formatting

### No Em-Dashes
Replace every em-dash (U+2014) and double-hyphen-as-em-dash ("--") with standard
punctuation:
- Use a comma for parenthetical asides: "PyPSA, the selected tool, demonstrated..."
- Use a semicolon for independent clauses: "PyPSA won on expressiveness; PowerModels
  was the runner-up"
- Use a hyphen for compound modifiers: "single-threaded MILP"
- Use parentheses for supplementary information: "PyPSA (the selected tool) demonstrated..."

### Consistent Punctuation
- Oxford comma in lists
- Period after every sentence (no sentence fragments as bullet points)
- Colon before lists, not a dash

## No Internal Process Artifacts

The report is written for someone with no knowledge of the evaluation process internals.
Remove all of the following:

### Protocol Version Numbers
- Do not mention "v4", "v7", "v10", "protocol version", or any internal versioning
- Exception: "PSS/E v31" and similar references to external format versions are fine

### Sweep and Probe References
- No "sweep findings" section or references to sweep analysis
- No "probe results" section or references to spot-check probes
- No "spot check" references
- No links to sweep-themes.json or probe-results.json
- No "cross-tool sweep" language

### Internal Process Notes
Remove any note that requires internal context to understand:
- "The TapPhaseControl bug cascade was identified as artificially inflating the
  apparent gap count; native capabilities warrant a higher baseline than initially
  assessed." -- meaningless to external reader
- "However, 4 of 10 scalability tests lack measured wall-clock times (estimates only)"
  -- evaluator process detail, not reader-useful
- "This was true for v4, but v10 data exists" -- version migration detail
- "Initially assessed as X, corrected to Y after sweep" -- internal calibration detail

### What TO Include
- Tool capabilities and limitations with test ID references
- Comparative findings across tools
- Phase 2 risks and mitigations
- Contract traceability (SOW requirement mapping)

## No Real Grid Names

Never name specific ISOs, RTOs, utilities, or real grid regions.
Scan for the names listed in the verifier prompt's "Real Grid Name Scan" section.
Also check for any specific utility company names or state/regional references tied
to grid operations.

Use instead:
- "the target ISO"
- "the customer's network"
- "the target market"
- "the full network model (FNM)"

"ACTIVSg" is acceptable -- it is a synthetic test case name, not a real grid.

## MATPOWER Exclusion Rationale

The correct rationale: the customer specifically asked in the kickoff call for source
code they can inspect, which precludes a compiled binary like the MATLAB/Octave runtime.

Do NOT use:
- "The MATLAB runtime is a proprietary commercial binary that cannot receive
  authorization for use in restricted environments."
- "disqualified for classified deployment"
- Any language implying we know whether the customer would or would not authorize MATLAB

Do use:
- "The customer requires inspectable source code, which precludes MATLAB's compiled
  runtime."
- "excluded because the customer requires source code they can inspect"

## Bus Counts from Data

Never hardcode bus counts. Derive them from actual MATPOWER .m case files. Common
mappings (verify against actual files):
- TINY: derive from case file (e.g., case5.m)
- SMALL: derive from case file (e.g., case_ACTIVSg2000.m)
- MEDIUM: derive from case file (e.g., case_ACTIVSg10k.m)

When referencing network sizes in prose, use the derived counts.

## Sensitivity Analysis Narrative

Emphasize ranking stability across scenarios over individual scenario wins.

**Good narrative:** "PyPSA holds the #1 position in three of four alternative scenarios.
PowerModels holds #2 in all four scenarios, demonstrating the most stable ranking
across all weighting assumptions."

**Bad narrative:** "GridCal takes #1 in the scalability-first scenario." (GridCal
cannot meet Phase 2 requirements, so this individual win is not meaningful.)

Rule: If a tool tops a single scenario but has blocking limitations for Phase 2,
explicitly note that the scenario win does not reflect real-world applicability.

## Tier-to-Finding Consistency

Tiers must match the severity of underlying findings. The sweep-evaluations skill
calibrates tiers with cross-tool visibility, so the tiers provided should already
be consistent. But verify during writing:

- Blocking architectural limitation (makes Phase 2 infeasible) -> Failing
- Passes fewer than half of tests in a suite -> should not be Adequate or Strong
- "Cannot express" core market-operations problems -> Failing
- Multiple fragile workarounds -> Weak at best
- Tool fails the same test as all others (shared solver limitation) -> should not
  differentiate tools in tier assignment

Workaround durability mapping to tiers:
- `stable` workaround = Adequate
- `fragile` workaround = Weak
- `blocking` limitation = Failing

## Traceability

Every claim about a tool's capabilities must reference a test ID (e.g., "A-3", "B-9")
or a specific synthesis finding. Unsupported assertions undermine the report's
credibility with the contract officer.

## Rebuild from Latest

Always write content from the provided evaluation data. Never carry forward prose from
earlier report versions, copy-paste from old MDX files, or assume previous content is
still accurate. The entire report site is rebuilt from scratch each time.
