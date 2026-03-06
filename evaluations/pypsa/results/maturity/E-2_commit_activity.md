---
test_id: E-2
tool: pypsa
dimension: maturity
status: pass
timestamp: 2026-03-05
---

# E-2: Commit Activity (Last 12 Months)

## Finding

PyPSA has 327 commits in the last 12 months (March 2025 - March 2026), with daily activity as recently as the day of this evaluation.

## Evidence

Commit count query: `gh api "repos/PyPSA/PyPSA/commits?since=2025-03-05T00:00:00Z&per_page=100"` across 4 pages:
- Page 1: 100
- Page 2: 100
- Page 3: 100
- Page 4: 27
- **Total: 327 commits**

Most recent commits (as of 2026-03-05):
- `2e22ebd6` 2026-03-04: "Fix statistics map transmission flows with bus_carrier and add groupby option (#1592)"
- `a21ba06c` 2026-03-04: "Update users.md (#1597)"
- `c45f7508` 2026-03-04: "fix: Fix groupby() call for pandas 3.0 (#1596)"

This averages approximately 27 commits per month, or roughly one commit per day.

## Implications

Very healthy commit activity. The project shows sustained, daily-level development effort with no gaps or dormancy periods. The commit messages indicate a mix of features, bug fixes, documentation updates, and dependency maintenance.
