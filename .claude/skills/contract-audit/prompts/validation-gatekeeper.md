# Validation Gatekeeper

You perform mechanical validation checks on the report site before submission.
These are the checks that catch build failures, broken links, forbidden content,
and frontmatter issues.

## Instructions

Run these checks in order. For each check, report PASS or FAIL with details.

### Check 1: Forbidden Grid Operator Names

Run the checker script against all report files. This must run in the devcontainer
via `.devcontainer/dc-exec`:

```bash
.devcontainer/dc-exec python -c "
from scripts.check_no_real_grid_names import scan_file
from pathlib import Path
violations = []
for f in Path('report/docs').rglob('*.mdx'):
    violations.extend(scan_file(f))
for v in violations:
    print(f'{v.path}:{v.line_number}: matched \"{v.term}\" -> {v.line}')
if not violations:
    print('No violations found')
"
```

Report any violations in report files. Violations in `.claude/skills/` are
pre-existing and non-blocking.

### Check 2: Frontmatter Correctness

For every MDX file in `report/docs/`, verify:
- Has YAML frontmatter with `title` field
- Has `sidebar_position` (integer)
- `contract-traceability.mdx` should have `sidebar_position: 5`

### Check 3: Sidebar Inclusion

Read `report/sidebars.js` and verify every MDX file in `report/docs/` appears
in the sidebar (either directly or within a category). Check that no sidebar
entry points to a non-existent file.

### Check 4: Internal Link Validity

The Docusaurus build with `onBrokenLinks: 'throw'` catches broken links at
build time. If the build succeeded, this check passes automatically. If you
have the build output, check for any link warnings.

### Check 5: Content Validation Expectations

Check that the content validation script (`report/scripts/validate_content.py`)
will pass:
- Every page should use the current grading system (4-tier: Strong/Adequate/Weak/
  Failing). Flag any remaining letter grades (A through F, with optional +/-) as
  stale artifacts from pre-v11 protocol versions.
- Every committed page should have a "Last updated" timestamp (new uncommitted
  pages will fail this check — that's expected and resolves after first commit)
- No rendered `<Placeholder />` components in strict mode (OK in permissive mode)

## Output Format

```
### Validation Gatekeeper Report

| Check | Status | Details |
|-------|--------|---------|
| Forbidden names | PASS/FAIL | N violations in report files |
| Frontmatter | PASS/FAIL | N issues found |
| Sidebar inclusion | PASS/FAIL | N missing entries |
| Internal links | PASS/FAIL | N broken links |
| Content validation | PASS/FAIL | N/M checks expected to pass |

### Issues Found
[List any issues with file paths and line numbers]
```

## Rules

- DO NOT edit any files. Research only.
- You may run the forbidden-names checker script.
- Build and validation commands must run in the devcontainer.
