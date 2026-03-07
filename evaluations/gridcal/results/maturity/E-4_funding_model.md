---
test_id: E-4
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# E-4: Bus Factor

## Criteria

Assess the project's resilience to the loss of key contributors. A bus factor of 1
means the project depends critically on a single individual.

## Result: FAIL

GridCal has a **bus factor of 1**. The project is critically dependent on Santiago
Penate Vera (SanPen).

### Evidence

- **SanPen**: 9,522 of ~13,523 total commits (70.3%). Sole author of the core
  numerical engine, power flow solvers, OPF formulation, and most infrastructure code.
- **Code ownership**: SanPen is the only contributor who has touched all major
  subsystems (power flow, OPF, state estimation, CIM import, GUI, CI configuration).
- **Review authority**: SanPen is the sole maintainer with merge authority on the
  GitHub repository.
- **Release authority**: All PyPI releases are published by SanPen.
- **Issue triage**: SanPen responds to the majority of GitHub issues personally.

### Secondary Contributors

- JosepFanals (9.0%) and Carlos-Alegre (3.5%) contribute meaningfully but in
  specialized areas, not across the full codebase. Neither appears to have release
  authority or the breadth of knowledge to maintain the project independently.

### Impact

If SanPen becomes unavailable:
1. No one can publish releases to PyPI
2. No one has demonstrated ability to maintain the core numerical engine
3. Bug fixes and security patches would stall
4. The project would likely fork or go dormant

### Mitigation

eRoots Analytics (the sponsoring company) employs several contributors, which provides
some institutional backstop. However, the knowledge concentration in a single individual
remains the primary risk. The MPL-2.0 license ensures the code remains forkable.
