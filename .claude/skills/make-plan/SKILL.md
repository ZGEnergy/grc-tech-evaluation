---
name: make-plan
description: This skill should be used when the user asks to "make a plan", "create a plan", "plan a feature", "research and plan", "start planning", or "run the make-plan workflow". It captures user intent through structured discussion, researches the domain/codebase, stress-tests proposals through adversarial debate, and produces a well-informed executive plan ready for decomposition via /decompose-plan.
---

# Make Plan — Research, Discuss, Debate, Draft

Capture user intent, research the domain and codebase, resolve ambiguities through structured discussion, stress-test the proposal through adversarial debate, and produce an executive plan ready for `/decompose-plan`.

## Invocation

Accept `$ARGUMENTS` as either:
1. A description of what to plan (e.g., "add CIM topology support to power-flow-poc")
2. Empty — ask the user what they want to build

If `$ARGUMENTS` is provided, use it as the starting point for INTAKE. If empty, prompt the user for a description before proceeding.

## Output

The skill has two exit paths, chosen by the user after DEBATE:

- **Executive plan** (default): Produces `<output-dir>/executive-plan.md` using the template from `decompose-plan`'s `artifact-templates.md`. Output directory defaults to `plans/` relative to cwd. On completion, report: "Executive plan ready. Run `/decompose-plan <output-dir>/executive-plan.md` to decompose into phases and PRDs."
- **Native plan mode**: Enters Claude Code's built-in plan mode (`EnterPlanMode`) with accumulated context. Produces an implementation plan for direct approval via `ExitPlanMode`. No files written to disk — the plan lives in the plan mode UI.

## State Machine

```
INTAKE → RESEARCH → DISCUSS → REVIEW → DEBATE → DRAFT
              ^          ^        |        ^  |     |  \
              |          |        v        |  v     |   EnterPlanMode
              |          |   [User sees    | [User  |
              |          |    position     |  sees   |
              |          |    paper]       |  debate  |
              |          |     |           |  results]|
              |          | A. edit plan    |    |     |
              |          |    (loop here)  |    |     |
              |          | B. more research|    |     |
              +-----<----+    (→RESEARCH)  |    |     |
              |          | C. approve      |    |     |
              |          |    (→DEBATE) ───+    |     |
              |          |                      |     |
              |          | Post-DEBATE choices:  |     |
              |          | A. another round ─────+     |
              |          | B. revisit decisions        |
              |          +----<---+  (→DISCUSS)        |
              |                   C. proceed (→DRAFT)──+
```

The workflow includes two explicit user interaction points:
1. **Post-DISCUSS review checkpoint**: After all gray areas are resolved, the user sees a position paper summarizing the plan state and can approve, edit, or request more research before entering DEBATE.
2. **Post-DEBATE branching**: After each debate round, the user sees the results and chooses whether to proceed to DRAFT, run another debate round, or revisit earlier decisions.

After DEBATE, the user chooses the exit path:
- **Executive plan** (default): DRAFT produces `executive-plan.md` for `/decompose-plan` — use for multi-phase, multi-PRD work.
- **Native plan mode**: DRAFT enters Claude Code's built-in plan mode with accumulated context — use for smaller features where the full PRD pipeline is overkill but you still want research/debate value.

Track the current state explicitly and report transitions to the user.

### State 1: INTAKE

Parse the user's description and establish scope.

1. Parse `$ARGUMENTS` (or the user's response if empty).
2. Identify the **target repo(s)** from the description. If ambiguous, ask the user via AskUserQuestion. Use the repo map from the workspace CLAUDE.md to guide identification.
3. Read the target repo's `CLAUDE.md` for architecture context. If multiple repos, read all of them.
4. Produce a **scope statement** (1 paragraph) summarizing:
   - What we're building
   - Which repo(s) it targets
   - How it connects to existing architecture
5. Present the scope statement to the user for confirmation. Revise if requested.
6. Identify **3-5 research questions** that need answering before planning. These should be specific to the scope, not generic. Categories:
   - What existing code/patterns does this build on?
   - What libraries/APIs are involved?
   - What domain constraints apply?
   - What prior art exists in the codebase?
   - What cross-repo dependencies are affected?
7. Present the research questions to the user. Allow them to add, remove, or modify questions.
8. Transition to **RESEARCH**.

### State 2: RESEARCH

Launch parallel research subagents to investigate each question.

1. For each research question, determine the appropriate researcher type:
   - **Codebase researcher**: For questions about existing code, patterns, conventions, and relevant modules in the target repo(s).
   - **Domain researcher**: For questions about external libraries, APIs, domain concepts, or industry patterns.
   - **Dependency researcher**: For multi-repo work — traces the dependency chain to understand upstream interfaces and downstream consumers.
   - **Data researcher**: For questions about what data is available, table schemas, data freshness, column semantics, or what external data sources might be needed. Uses the data-mcp tools (mcp__data__list_tables, mcp__data__describe_table, mcp__data__sample_data, mcp__data__query) to perform exploratory data analysis on internal Hive/Trino tables.

2. Read the appropriate prompt template from this skill's directory:
   - `codebase-researcher-prompt.md` for codebase questions
   - `domain-researcher-prompt.md` for domain/library questions
   - `dependency-researcher-prompt.md` for dependency chain questions
   - `data-researcher-prompt.md` for data availability and schema questions

3. Replace `{{variables}}` in the template. Not all variables apply to every template — substitute only those present:
   - `{{research_question}}`: the specific question to investigate (all researchers)
   - `{{target_repos}}`: comma-separated list of target repo directory names (all researchers)
   - `{{scope_statement}}`: the confirmed scope statement from INTAKE (all researchers)
   - `{{workspace_root}}`: the workspace root path (codebase and dependency researchers)
   - `{{repo_claude_md}}`: contents of the target repo's CLAUDE.md (codebase researchers only)
   - `{{relevant_tables_hint}}`: comma-separated list of table name patterns to investigate (data researchers only — the orchestrator derives this from the scope statement and INTAKE context, e.g., "ercot_da_prices, ercot_rt_prices, ercot_load")

4. Launch all researcher subagents in parallel via a single message with multiple Task tool calls. Use `subagent_type: "general-purpose"`.

5. Collect results. Each researcher returns a structured ~300 word summary.

6. Merge researcher outputs into a **Research Findings** section in working memory. Organize by question, with the researcher type noted.

7. Present a brief summary of research findings to the user (key discoveries, surprises, potential concerns).

8. Transition to **DISCUSS**.

### State 3: DISCUSS

Identify and resolve ambiguities before any plan writing.

1. Analyze the scope statement + research findings to identify **3-5 domain-specific gray areas**. These must be specific trade-offs informed by the research, not generic questions. Each gray area should:
   - Name the specific tension or trade-off
   - Reference research findings that inform the options
   - Affect the plan structure if resolved differently

2. Present gray areas to the user one at a time using the `AskUserQuestion` tool with structured options. For each:
   - Use `header` like "Gray area 1" or a short topic tag
   - Frame the trade-off clearly in the `question` field
   - Provide 2-4 research-informed `options` with `label` and `description` (not generic "A or B")
   - Put the recommended option first with "(Recommended)" appended to its `label` if the research supports one
   - Include context from research findings in each option's `description` field

3. **Lock decisions** into a `DECISIONS` list. Each decision records:
   - The gray area question
   - The chosen option
   - The rationale (from research + user input)
   - Which phase(s) this constrains

4. **Guard against scope creep**: If during discussion the user suggests capabilities beyond the original scope statement, capture them in a **Deferred Ideas** list rather than expanding scope. Acknowledge the idea and explain it's captured for later.

5. **Synthesize Position Paper.** After all gray areas are resolved, synthesize the current state (scope, research findings, locked decisions) into a **position paper** (~500-800 words) that states:
   - What we're building and why
   - Target repo(s) and how this fits in the architecture
   - Key architectural decisions and their rationale
   - Proposed phase structure (rough — names and one-sentence descriptions)
   - Locked decisions from DISCUSS as constraints
   - Non-goals and deferred ideas
   - What success looks like

6. **Present Position Paper for Review.** Display the full position paper to the user. Then use the `AskUserQuestion` tool (header: "Review") with these options:
   - label: "Approve — move to DEBATE (Recommended)", description: "Position paper is ready for adversarial stress-testing."
   - label: "I have edits", description: "Provide corrections or additions to the position paper before proceeding."
   - label: "Need more research", description: "Identify gaps that require additional research before proceeding."
   If "I have edits": apply edits, re-present, loop until approved. If "Need more research": capture new questions, run RESEARCH, return to step 1.

7. Transition to **DEBATE** with the approved position paper.

### State 4: DEBATE

Adversarial review loop that stress-tests the plan proposal. Key principle: **each debate round starts from only the position paper, not the internal state of any previous debate.** This prevents anchoring bias.

#### Step 4.1: Launch Parallel Debate Subagents

**Round 1** uses the position paper approved at the REVIEW checkpoint (end of DISCUSS). **Rounds 2+** re-synthesize the position paper from scratch (scope + research + decisions + fixes from prior triage) to preserve the debate isolation invariant — critics never see prior critiques.

The position paper is the **sole input** to debate subagents. It contains no record of prior debate rounds.

Read the critic prompt templates from this skill's directory:
- `requirements-critic-prompt.md`
- `architecture-critic-prompt.md`
- `domain-critic-prompt.md` (optional — launch only for domain-heavy work)

Replace `{{position_paper}}` with the synthesized position paper.

Launch 2-3 debate subagents in parallel via a single message with multiple Task tool calls. Use `subagent_type: "general-purpose"`. Each critic receives **only the position paper**.

Adversarial lenses:
1. **Requirements Critic**: Missing requirements, unstated assumptions, ambiguous acceptance criteria, uncovered edge cases, ignored failure modes.
2. **Architecture Critic**: Structural weaknesses, wrong abstractions, over/under-engineering, dependency risks, poorly-defined interfaces.
3. **Domain Critic** (optional): Domain-specific risks — data leaking, timezone bugs, hour-ending off-by-ones, credit check failures, stale data assumptions, DST edge cases.

Each critic returns findings in structured format:

```
## Critique: [Critic Role]

### Challenges (things that are wrong or risky)
- [CH-1] <description> — severity: HIGH/MEDIUM/LOW

### Questions (things that are ambiguous)
- [QU-1] <description>

### Missing (things not addressed)
- [MI-1] <description>

### Strengths (things that are good — don't change these)
- [ST-1] <description>
```

#### Step 4.2: Merge and Triage

Collect all critiques and:

1. **Deduplicate**: If two critics flag the same issue, keep the more detailed version.
2. **Categorize** each finding:
   - **Actionable** (clear fix, no user input needed) → apply to position paper directly
   - **Decision-required** (trade-off, needs user input) → present via AskUserQuestion
   - **Out-of-scope** (valid concern but beyond this plan) → add to Deferred Ideas
   - **Disagreed** (critics contradict each other) → present both positions to user
3. Present the categorized findings to the user with a summary of what was found and what actions will be taken.
4. For **decision-required** findings, use the `AskUserQuestion` tool (batches of 1-4 questions per call). Each question must have structured `options` with `label` and `description` fields informed by the critic's analysis.
5. **Update the position paper** with actionable fixes and user decisions.
6. **Update DECISIONS** with any new locked decisions from the user.

#### Step 4.3: User-Driven Branching

After triage (Step 4.2) is complete and the position paper is updated, present a summary of the debate round results to the user:
- Number of findings by severity (HIGH/MEDIUM/LOW)
- Key changes made (actionable fixes applied, decisions locked)
- Remaining open concerns, if any

Then use the `AskUserQuestion` tool (header: "Next step") with options that vary based on context. The "(Recommended)" suffix moves to the first option's label based on which path is most appropriate:

**When no HIGH-severity findings remain** — put "Proceed to draft (Recommended)" first:
- label: "Proceed to draft (Recommended)", description: "Move to debate summary and then draft the plan."
- label: "Another debate round", description: "Re-synthesize position paper and run critics again." *(Only include if < 3 rounds run.)*
- label: "Revisit decisions", description: "Go back to DISCUSS to reconsider earlier decisions."

**When HIGH-severity findings were addressed this round** — put "Another debate round (Recommended)" first:
- label: "Another debate round (Recommended)", description: "Re-synthesize position paper and run critics again." *(Only include if < 3 rounds run.)*
- label: "Proceed to draft", description: "Move to debate summary and then draft the plan."
- label: "Revisit decisions", description: "Go back to DISCUSS to reconsider earlier decisions."

**When round 3 is reached** — remove "Another debate round":
- label: "Proceed to draft (Recommended)", description: "Move to debate summary and then draft the plan."
- label: "Revisit decisions", description: "Go back to DISCUSS to reconsider earlier decisions."

**Critical invariant**: Each new debate round re-synthesizes the position paper from scratch. Debate subagents in round N never see the critiques from round N-1. They see only the improved position paper.

#### Step 4.4: Produce Debate Summary

After exiting the loop, write a brief **Debate Summary** (~200 words) capturing:
- How many rounds were run
- Key challenges that were addressed
- Key decisions that were locked during debate
- Remaining risks acknowledged but accepted

This summary is included in the executive plan for downstream visibility.

#### Step 4.5: Choose Exit Path

After the debate summary is complete, use the `AskUserQuestion` tool (header: "Exit path") with these options:

- label: "Executive plan for /decompose-plan (Recommended)", description: "Produces a structured executive plan file for the full decomposition pipeline. Best for multi-phase work."
- label: "Native Claude Code plan mode", description: "Enters built-in plan mode with all accumulated context. Best for smaller features you'll implement directly."

Record the choice and transition to **DRAFT**.

### State 5: DRAFT

DRAFT has two branches based on the exit path chosen in Step 4.5.

#### Branch A: Executive Plan (for `/decompose-plan`)

Produce the executive plan artifact.

1. Read the executive plan template from `decompose-plan`'s `artifact-templates.md` (at `.claude/skills/decompose-plan/artifact-templates.md`). Use the `## Executive Plan Template` section.

2. Draft the executive plan incorporating:
   - **Vision**: From the scope statement + research context
   - **Objectives**: Derived from the scope, informed by research findings
   - **Constraints**: Locked decisions from DISCUSS and DEBATE, plus any technical constraints from research
   - **Phases**: From the position paper's phase structure, enriched with research findings as context for phase scoping
   - **Phase Dependencies**: Derived from phase structure with dependency analysis
   - **Context — Research Summary**: Brief summary of key research findings (embedded for downstream visibility)
   - **Context — Debate Summary**: The debate summary from Step 4.4
   - **Deferred Ideas**: Explicitly listed as non-goals with brief descriptions

3. Present the draft executive plan to the user for approval. Revise if requested.

4. Ask the user for the output directory (default: `plans/` relative to cwd). Create the directory if it doesn't exist.

5. Write the approved plan to `<output-dir>/executive-plan.md` using the Write tool.

6. Report to the user:
   - Number of phases in the plan
   - Key decisions made (bullet list)
   - Debate rounds completed
   - Deferred ideas count
   - Next step: "Run `/decompose-plan <output-dir>/executive-plan.md` to decompose into phases and PRDs."

#### Branch B: Native Claude Code Plan Mode

Enter Claude Code's built-in plan mode with accumulated context for direct implementation planning.

1. Call `EnterPlanMode` to transition to plan mode.

2. In plan mode, use the accumulated state (scope statement, research findings, locked decisions, position paper, debate summary) to explore the codebase and design an implementation plan. The plan should include:
   - **Goal**: One-sentence summary from the scope statement
   - **Context**: Key research findings and locked decisions that constrain the implementation
   - **Approach**: Specific implementation strategy informed by research (which files to modify, which patterns to follow, which APIs to use)
   - **Steps**: Ordered implementation steps with file paths and descriptions of changes
   - **Risks**: Remaining risks from debate summary that the implementer should watch for
   - **Deferred Ideas**: Listed as explicit non-goals so the implementer doesn't scope-creep

3. The plan should reference specific code locations, function signatures, and patterns discovered during RESEARCH — this is the payoff of the research/debate investment.

4. Call `ExitPlanMode` for user approval. Revise if requested.

5. Report to the user:
   - Key decisions made (bullet list)
   - Debate rounds completed
   - Deferred ideas count
   - Next step: "Plan approved. Ready to implement — approve the plan to begin."

## Subagent Dispatch

To launch a subagent:

1. Read the appropriate prompt template file from this skill's directory using the Read tool.
2. Replace all `{{variable}}` placeholders with actual values.
3. Launch via the Task tool with `subagent_type: "general-purpose"`.
4. Subagents return structured text results directly (no file writing during RESEARCH/DEBATE).
5. Only in DRAFT does the orchestrator write to disk.

When launching multiple independent subagents (e.g., parallel researchers or parallel critics), use a single message with multiple Task tool calls.

## Context Management

Keep the orchestrator's context lean:

- **Research findings**: Store as structured summaries (~300 words per question). Don't paste raw file contents into the orchestrator — subagents do the reading.
- **Position paper**: **Created** at end of DISCUSS (step 5). **Passed as-is** to DEBATE round 1. **Updated** after each debate triage (Step 4.2). **Re-synthesized from scratch** on debate rounds 2+ and after returning from DISCUSS re-entry. **Frozen** when user chooses "Proceed to draft". Maximum ~800 words.
- **Critic outputs**: Read, triage, then discard the raw output. Keep only the categorized findings list and the decisions made.
- **Debate summary**: ~200 words carried forward to DRAFT.
- **Native plan mode**: All accumulated state stays in the conversation context — no serialization needed. Plan mode inherits the full conversation history.

## Integration with Downstream Workflows

### Executive plan path → `/decompose-plan`

- The executive plan output follows `decompose-plan`'s template exactly (from `artifact-templates.md`).
- Locked decisions are written into the `## Constraints` section so `decompose-plan`'s OQ system respects them as pre-resolved.
- Research findings are embedded as a `## Context — Research Summary` section after Constraints for downstream phase-plan writers.
- The debate summary is embedded as a `## Context — Debate Summary` section for downstream visibility into what was stress-tested.
- Deferred ideas appear in a `## Deferred Ideas` section (explicit non-goals for this plan).

### Native plan mode path → direct implementation

- The implementation plan inherits all context from the conversation (scope, research, decisions, debate summary) — no information is lost by choosing this path.
- Locked decisions from DISCUSS and DEBATE become constraints in the plan steps (e.g., "use X pattern because [decision rationale]").
- Research findings translate into specific file paths, function references, and code patterns in the implementation steps.
- Deferred ideas are listed as explicit non-goals so plan mode doesn't scope-creep during implementation.
- The debate summary informs the Risks section of the plan.

## AskUserQuestion Usage

Every user-facing question in this workflow MUST use the `AskUserQuestion` tool with structured `options` so the user can select answers via keypad instead of typing. Never print options as plain text and wait for the user to type or copy/paste a response.

Pattern for every question:
- Use the `questions` array with `options` containing `label` and `description` fields
- Use `header` for a short tag (max 12 chars) like "Gray area", "Next step", "Exit path"
- Put the recommended option first with "(Recommended)" appended to its `label`
- Set `multiSelect: false` unless the question explicitly allows multiple selections
- The user always gets an automatic "Other" option for free-text input, so don't add one manually

This applies to ALL interaction points: INTAKE repo identification, DISCUSS gray areas, REVIEW checkpoint, DEBATE triage decisions, DEBATE branching, and exit path selection.

## Guardrails

- **No artifact writing until DRAFT**: States 1-4 produce only working memory and user interactions. Only DRAFT writes to disk (Branch A) or enters plan mode (Branch B).
- **Scope creep protection**: Any user suggestion that expands beyond the confirmed scope statement goes to Deferred Ideas, not into the plan.
- **Debate isolation**: Each debate round's critics receive only the position paper. No critique history, no "here's what changed" context.
- **Iteration cap**: Maximum 3 debate rounds. After 3, the "Another debate round" option is removed — user may only "Proceed to draft" or "Revisit decisions".
- **User authority**: User decisions override all critic recommendations. Record the rationale but respect the choice.
- **Research before opinions**: The skill never proposes architectural decisions without research backing. Gray areas in DISCUSS must reference specific research findings.

## Supporting Files

Read these files from this skill's directory (`.claude/skills/make-plan/` relative to the workspace root) as needed:

- `codebase-researcher-prompt.md` — Template for codebase research subagents
- `domain-researcher-prompt.md` — Template for domain/library research subagents
- `dependency-researcher-prompt.md` — Template for multi-repo dependency research subagents
- `data-researcher-prompt.md` — Template for data availability and schema research subagents (uses data-mcp tools)
- `requirements-critic-prompt.md` — Template for requirements critique debate subagent
- `architecture-critic-prompt.md` — Template for architecture critique debate subagent
- `domain-critic-prompt.md` — Template for domain-specific critique debate subagent

Also reads from `decompose-plan`'s directory:

- `.claude/skills/decompose-plan/artifact-templates.md` — Executive plan template used in DRAFT
