---
test_id: E-3
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# E-3: Contributor Breadth

## Criteria

Assess the diversity and breadth of the contributor base beyond a single maintainer.

## Result: QUALIFIED PASS

GridCal has 30 lifetime contributors, but contribution is heavily concentrated in a
small group affiliated with a single organization.

### Contributor Distribution

| Contributor | Commits | Share | Affiliation |
|-------------|---------|-------|-------------|
| SanPen (Santiago Penate Vera) | 9,522 | 70.3% | eRoots Analytics (CTO) |
| JosepFanals | 1,223 | 9.0% | eRoots Analytics |
| Carlos-Alegre | 478 | 3.5% | eRoots Analytics |
| Other eRoots employees | ~1,000 | ~7% | eRoots Analytics |
| External contributors | ~1,300 | ~10% | Various |

### Analysis

- **30 total contributors** over the project lifetime is a meaningful number
- The top 3 contributors account for ~83% of commits, all from the same company
- Several additional eRoots employees appear in the contributor list
- External (non-eRoots) contributors exist but are predominantly one-off or
  small-volume contributors
- Some academic contributors from CIRCE and UPC

### Qualification Reason

While the total contributor count (30) is respectable, the effective contributor base
is a small team at a single company. This creates organizational concentration risk --
if eRoots pivots or loses funding, the contributor pipeline narrows to near zero.
The project does have a history of accepting external contributions, which partially
mitigates this concern.
