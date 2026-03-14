---
test_id: E-7
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "772bf97b"
timestamp: "2026-03-13T23:00:00Z"
---

# E-7: Operational Adoption

## Finding

GridCal/VeraGrid claims operational adoption by several major utilities and equipment manufacturers, including Redeia (Spanish TSO), Schneider Electric, and GE Vernova. However, direct verification of these claims from public sources is limited — the eRoots website does not list clients publicly, and the evidence comes primarily from the project's own research context documentation and presentations.

## Evidence

**Claimed operational users (from research-context.md):**
- Redeia (Spanish TSO, operator of Red Electrica de Espana)
- Schneider Electric
- GE Vernova
- Navitasoft (has contributed code via `peterkulik-navitasoft` and `jozsefgorcs-navitasoft`, 52 combined commits)

**Verifiable adoption signals:**
- **Navitasoft integration:** 52 commits from two Navitasoft developers, confirming active code-level engagement by an external organization
- **eRoots commercial use:** The tool is the core product of eRoots Analytics, meaning it is used commercially in consulting engagements
- **Academic adoption:** Zenodo DOI for citation; project started in 2015 at an academic institution
- **Community indicators:**
  - GitHub stars: visible but not queried (repo exists since January 2016)
  - Discord community: active server linked from README
  - PyPI downloads: pepy.tech badge in README (API requires authentication to query)

**LF Energy landscape:** Issue #453 references "Update LF Energy Landscape record," indicating the project is listed in the Linux Foundation Energy landscape directory.

**Documentation quality as adoption barrier:**
- ReadTheDocs documentation covers up to v5.0.2 only (current is 5.6.x)
- Getting Started link reported broken by user (#416, closed 2026-01-07)
- Tutorial links broken (#347, closed 2026-01-07)
- These documentation gaps may limit broader adoption

**Windows installer:** Available at https://www.eroots.tech/software, indicating targeting of non-developer users (utility engineers, planners).

## Implications

The claimed adoption by Redeia and Schneider Electric would be significant if independently verified. The Navitasoft code contributions provide concrete evidence of at least one external organization investing development effort. The eRoots commercial backing confirms the tool is used in real consulting projects, but the scale and criticality of these deployments is uncertain. The documentation gaps and broken links suggest adoption may be concentrated among users with direct eRoots support relationships rather than self-service community adoption.
