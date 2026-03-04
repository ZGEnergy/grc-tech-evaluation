# Context Monitoring Reference

Shared procedures for implement-plan, decompose-plan, and edit-plan. Each skill reads this file when it first receives a degradation signal or detects a handoff file during INIT.

## Warning Recognition

The Phase 1 PostToolUse hook delivers severity warnings via `additionalContext`. Recognize by prefix:

| Prefix | Severity |
|--------|----------|
| `CONTEXT MONITOR [CAUTION]:` | CAUTION |
| `CONTEXT MONITOR [WARNING]:` | WARNING |
| `CONTEXT MONITOR [CRITICAL]:` | CRITICAL |

**Escalation rule:** Severity only increases (null → CAUTION → WARNING → CRITICAL). Once at WARNING, it never reverts to CAUTION even if a later message reports CAUTION. Always apply rules for the highest severity ever reached. Check for warnings after each atomic operation.

## Handoff Envelope Format

Every handoff file uses this common envelope:

```markdown
# Session Handoff

**Skill:** <skill-name>
**Timestamp:** <ISO 8601 with timezone> (epoch: <unix_seconds>)
**Session ID:** <session_id>
**Plan Directory:** <absolute_path>
**Current State:** <STATE_NAME>
**Context Remaining:** <percentage>%
```

Optional fields (skill-specific): `**Current Phase:**`, `**Current Tier:**`, `**Notes:**`

The envelope is followed by a `## Snapshot` section with five required subsections:
- `### Completed Work` — what has been done
- `### In-Progress Work` — what was interrupted
- `### Pending Work` — what remains
- `### Artifact Inventory` — every relevant file with status (complete/partial/not started)
- `### Key Decisions` — user decisions, scope parameters, degradation history

Skills may add additional subsections after the five required ones.

## Handoff Write Procedure

When CRITICAL fires:

1. **Finish the current atomic operation** (one subagent batch, one file edit, one scan — never leave work half-collected).
2. **Check for existing handoff.** If `.session-handoff.md` exists, inform user which skill wrote it and when. Offer Overwrite / Skip. If Skip, note the handoff was not written.
3. **Write** `<plan_directory>/.session-handoff.md` with envelope + snapshot in a single Write tool call. If write fails, print the handoff content in chat so the user can save manually.
4. **Report** to the user: what was completed, what remains, and the resume command.
5. **End the response.** No new tool calls, no new work. Do NOT output completion signals, promise tags, success markers, or any text that a calling wrapper could interpret as task completion — the *task* is not finished, only this *session's context* is exhausted. If running inside an iterative wrapper (e.g., Ralph Loop), simply end the response and let the wrapper re-invoke with fresh context. If user asks anything after stopping, respond: "This session has reached its context limit. Please start a new session to continue."

## Resume: Envelope Validation

When a skill starts, check for `<plan_directory>/.session-handoff.md` before any other INIT work.

1. **Read the file.** If missing or unreadable, proceed with fresh start.
2. **Validate envelope.** Verify `# Session Handoff` on line 1 and all six required fields present. If malformed, warn user with the specific invalid field and proceed with fresh start.
3. **Check skill match.** If `**Skill:**` does not match the invoking skill, inform user ("invoke /{other_skill} to resume that session") and proceed with fresh start. Do NOT delete the file.
4. **Check staleness.** If older than 24 hours, flag it in the confirmation prompt.
5. **Confirm with user.** Present handoff summary (skill, timestamp, state, context remaining, optional fields). If stale, add a warning about potential artifact drift. Offer Resume / Start Fresh. On "Start Fresh," preserve the file and proceed with fresh start.

## Resume: Snapshot Parsing

After user confirms resume:

1. Locate `## Snapshot`. If missing, warn user and attempt minimal resume from envelope alone.
2. Parse the five required subsections using `###` heading boundaries. Missing subsections are treated as empty with a soft warning.
3. Parse any skill-specific subsections.

## Handoff Lifecycle

- **Delete after successful resume** — after all restoration steps succeed, before the state transition.
- **Preserve on decline, failure, or skill mismatch** — never delete a handoff the user didn't resume from.
- **Deletion failure** — warn user ("please remove manually to prevent re-prompting"), but proceed with resume.

## PreToolUse Agent Gate

A PreToolUse hook on `Agent` calls runs the watchdog with `HOOK_EVENT=PreToolUse`. This mode **blocks** Agent launches when context is at CRITICAL severity, preventing orchestrators from spawning expensive subagents when context is nearly exhausted.

- **CRITICAL**: The hook returns `{"decision": "block", "reason": "..."}`, preventing the Agent call.
- **Below CRITICAL**: The hook returns `{}` (silent) — informational warnings are handled by the PostToolUse hook.

When an Agent call is blocked, orchestrators should treat the remaining work as deferred and proceed to handoff. Do not retry the blocked Agent call.

## Subagent Context Exhaustion

When a subagent hits CRITICAL context pressure, it returns `CONTEXT_EXHAUSTED` status instead of `FAILED`. The orchestrator re-launches a fresh subagent with a scoped-down continuation prompt. This is separate from the orchestrator's own context monitoring.

### CONTEXT_EXHAUSTED vs FAILED

| Aspect | CONTEXT_EXHAUSTED | FAILED |
|--------|-------------------|--------|
| Cause | Subagent ran out of context before finishing | Bug, test failure, unrecoverable error |
| Partial progress | Preserved in fragment handoff file | May or may not exist |
| Orchestrator action | Re-launch with scoped continuation prompt | Retry once with error context, then mark FAILED |
| Budget | Max 2 continuations (3 total attempts) | Max 1 retry (2 total attempts) |
| Counters | `continuation_count` per unit | `retry_count` per unit — independent counter |

### Fragment Handoff File

Subagents write `.fragment-handoff.md` in their working directory (worktree for implementers, plan directory for writers/checkers) before returning `CONTEXT_EXHAUSTED`. Format:

```markdown
# Fragment Handoff

**Subagent Type:** <type>
**Unit:** <prd_id | phase_number | edge_id | file_path>
**Timestamp:** <ISO 8601>
**Progress:** <fraction, e.g., "steps 1-5 of 9" or "categories 1-4 of 8">

## Completed
- <completed items with enough detail to skip on continuation>

## Remaining
- <remaining items — the continuation prompt targets only these>

## Artifacts on Disk
- <files written/committed so far with status>
```

### Continuation Protocol

When the orchestrator receives `CONTEXT_EXHAUSTED` from a subagent:

1. **Read** `.fragment-handoff.md` from the subagent's working directory.
2. **Build continuation prompt**: reference completed work (to skip), list only remaining items, and pass any on-disk artifacts as context. The continuation prompt must be strictly smaller in scope than the original.
3. **Re-launch** a fresh subagent in the same working directory (same worktree, same output paths). Pass `continuation: true` and the scoped-down prompt.
4. **Budget enforcement**: Track `continuation_count` per unit. If count reaches 2 (meaning 3 total attempts), do not re-launch — mark the unit's status based on partial progress (e.g., partial artifact, partial findings) and report to the user.
5. **Merge results**: Combine the original partial result with the continuation result. For text output (checkers, analyzers), concatenate findings. For file output (writers, implementers), the continuation builds on disk state.

### Interaction with Orchestrator Context Monitoring

Subagent continuations are permitted even when the orchestrator is at WARNING severity, as long as the continuation is for an already-in-flight unit (not new work). At CRITICAL, no new continuations — treat outstanding `CONTEXT_EXHAUSTED` as partial results and include them in the orchestrator's own handoff.
