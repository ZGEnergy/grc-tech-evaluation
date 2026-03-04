# PRD Parser — Subagent Prompt Template

Extract structured metadata from all PRDs in Phase {{phase_number}}: {{phase_name}}.

**Detail level:** `{{detail_level}}`

## PRD Files

Read each of the following PRD files using the Read tool:

{{prd_file_list}}

## Extraction Rules

{% if detail_level == "task_card" %}

The input file is a `task-cards.md` containing multiple task cards in a single file. Parse each `### TC-<NN>` section as a separate entry.

### `prd_id`
The two-digit task card number from the `### TC-<NN>` heading (e.g., `### TC-01` → `"01"`).

### `phase`
The phase number: `"{{phase_number}}"` (always `"01"` for Tier 1).

### `title`
The task card title from the `### TC-<NN>: <title>` heading.

### `slug`
Derive from the title: lowercase, spaces to hyphens, strip special chars.

{% else %}

For each PRD file, extract the following fields:

### `prd_id`
The two-digit PRD number from the filename (e.g., `prd-01-schema.md` → `"01"`).

### `phase`
The phase number: `"{{phase_number}}"`.

### `title`
The PRD title from the `# PRD: <title>` heading on the first line.

### `slug`
Derive from the filename: `prd-01-schema.md` → `"schema"`. Take the part after `prd-NN-` and before `.md`.

{% endif %}

### `source_file`
{% if detail_level == "task_card" %}
From the **File locations:** field, extract the `Source:` backtick-wrapped path.
{% else %}
From the `## File Location` section, extract the first backtick-wrapped path. This is the path to the source module (e.g., `src/zge_ercot_power_flow/scenario/schema.py`).
{% endif %}

### `test_file`
{% if detail_level == "task_card" %}
From the **File locations:** field, extract the `Test:` backtick-wrapped path. If not listed, derive from `source_file`.
{% else %}
From the `## File Location` section, extract the second backtick-wrapped path if listed. Otherwise, derive it from `source_file` using this rule:
{% endif %}
- `src/<package>/<subpackage>/<file>.py` → `tests/<subpackage>/test_<file>.py`
- Example: `src/zge_ercot_power_flow/scenario/schema.py` → `tests/scenario/test_schema.py`

### `internal_deps`
{% if detail_level == "task_card" %}
From the **Dependencies:** field, extract task card numbers. Format: `TC-NN` → extract `NN` as two-digit strings. `None` → `[]`.
{% else %}
From the `## Dependencies` → `### Internal Dependencies` section, extract the PRD numbers. Each internal dependency line looks like:
- `PRD <NN> (<title>) — <description>`

Extract just the PRD numbers as two-digit strings. Return as an array: `["01", "04"]`.
{% endif %}

If no internal dependencies, return `[]`.

### `external_deps`
{% if detail_level == "task_card" %}
Task cards do not list external dependencies. Return `[]`.
{% else %}
From the `## Dependencies` → `### External Dependencies` section, extract library names. Each line looks like:
- `<library> — <description>`

Extract just the library names. Return as an array: `["numpy", "pandas"]`.

If no external dependencies, return `[]`.
{% endif %}

### `repo`
{% if detail_level == "task_card" %}
From the **Repository:** field, extract the backtick-wrapped repository directory name. If not present, return `null`.
{% else %}
From the `## Repository` section, extract the backtick-wrapped repository
directory name. If no `## Repository` section exists, return `null`.
{% endif %}

### `test_count`
{% if detail_level == "task_card" %}
Count the numbered items in the **Acceptance criteria:** list. Each criterion counts as one test.
{% elif detail_level == "lean_prd" %}
Count the numbered items in the `## Acceptance Criteria` section. Each named test entry (`**test_<name>**`) counts as one test.
{% else %}
Count the numbered items in the `## Success Criteria` → `### Unit Tests` section. Each test is a numbered entry like:

```
1. **test_<name>**
   - <description>
```

Count these entries. If there is also an `### Integration Tests` section, add those tests to the count.
{% endif %}

## Output Format

Return a single JSON array containing one object per PRD. Use this exact schema:

```json
[
  {
    "prd_id": "01",
    "phase": "{{phase_number}}",
    "title": "StandardizedForecast Schema",
    "slug": "schema",
    "source_file": "src/zge_ercot_power_flow/scenario/schema.py",
    "test_file": "tests/scenario/test_schema.py",
    "repo": "ercot-power-flow-poc",
    "internal_deps": [],
    "external_deps": ["numpy", "pandas"],
    "test_count": 13
  },
  {
    "prd_id": "02",
    "phase": "{{phase_number}}",
    "title": "Forecast Adapters",
    "slug": "adapters",
    "source_file": "src/zge_ercot_power_flow/scenario/adapters.py",
    "test_file": "tests/scenario/test_adapters.py",
    "repo": "ercot-power-flow-poc",
    "internal_deps": ["01"],
    "external_deps": ["pandas"],
    "test_count": 18
  }
]
```

## Important

- Output ONLY the JSON array. No prose, no markdown fences, no explanation.
- Sort entries by `prd_id` (ascending).
- If a field cannot be extracted (e.g., the PRD is missing a `## File Location` section), use `null` for that field and note it in a `"warnings"` array field on that entry.
- If `repo` is `null` for all PRDs, this is a single-repo plan.
- Do not read any files other than the PRD files listed above.
- Do not modify any files.
- **CONTEXT_EXHAUSTED:** If you receive a CRITICAL context warning before parsing all PRDs, return a partial JSON array containing only the PRDs parsed so far, and add `"partial": true` as a field on the last entry. The orchestrator will re-launch for the remaining PRDs.
