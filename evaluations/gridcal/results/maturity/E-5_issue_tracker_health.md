---
test_id: E-5
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "530e2bdd"
timestamp: "2026-03-13T23:00:00Z"
---

# E-5: Issue Tracker Health

## Finding

The issue tracker shows moderate engagement with a median time-to-close of 115 days. Issues are batch-closed periodically rather than addressed individually as they arrive. Many issues are internal project management items (in Spanish) rather than external user reports.

## Evidence

**Sample: 17 closed issues (most recently updated):**

| Metric | Value |
|--------|-------|
| Sample size | 17 closed issues |
| Median time-to-close | 115 days |
| Mean time-to-close | 126 days |
| Fastest close | 0 days (2 issues) |
| Slowest close | 304 days |

**Closing pattern:** A large batch of issues (7 issues) was closed on 2026-01-07, and another batch (5 issues) on 2025-12-10. This suggests periodic triage rather than continuous issue management.

**Issue characteristics (closed sample):**
- Internal feature tracking in Spanish: "Reduccion de Casos en Series Temporales de Simulacion" (#365), "Crear subestaciones desde un nudo" (#439)
- User-reported bugs: "Wrong split of reactive power in the power flow" (#400), "Failed building wheel for VeraGrid" (#450)
- Documentation issues: "Getting Started Link is not working" (#416), "Link on tutorials is broken" (#347)

**Open issues (10 most recent):**
- 7 open issues found in sample
- Oldest open: #337 "Issue with reading PSSE transformers" (created 2025-02-17, 389 days old)
- Most recent: #459 "Consider using lxml for RDF/XML parsing" (created 2026-03-02)
- Mixed internal feature requests and external user reports

**Acknowledged ratio:** Of the 7 open issues sampled, all have at least one comment or label, giving an acknowledged ratio of approximately 100%. However, the slow median resolution time (115 days) suggests acknowledgment does not translate to timely resolution.

**Label usage:** Minimal — only a few issues have labels (primarily "bug"). No structured triage workflow (no priority labels, milestones, or assignees visible).

## Implications

The issue tracker is functional but loosely managed. The batch-closing pattern and mix of internal/external issues make it difficult for external users to track their reports. The 115-day median time-to-close is slow relative to the project's rapid release cadence (2 releases/week), suggesting that user-reported issues may not feed directly into the release cycle.
