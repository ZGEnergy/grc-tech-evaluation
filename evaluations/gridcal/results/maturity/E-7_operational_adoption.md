---
test_id: E-7
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "772bf97b"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# E-7: Operational Adoption

## Result: INFORMATIONAL

## Finding

GridCal/VeraGrid has credible claims of operational adoption by several major utilities and equipment manufacturers. The eRoots Analytics website lists 18+ client organizations including Redeia (Spanish TSO), Schneider Electric, and GE Vernova, supported by named testimonials. Independent verification is limited but code contributions from at least one external organization (Navitasoft) confirm commercial engagement beyond the developer's own company.

## Evidence

**eRoots Analytics client list (from website, accessed 2026-03-24):**

| Category | Organizations |
|----------|---------------|
| Utilities/TSOs | Redeia, RTE, Elewit, Nidec |
| Energy companies | Acciona Energia, Engie, GE Vernova, Hyosung |
| Technology/Industrial | Schneider Electric |
| Academic/Research | ETH Zurich, Barcelona Supercomputing Center (BSC) |
| Consultancies | Aiguasol, teknoCEA, Azimut 360, TTA Energy, CRESYM, iGrid |

**Named testimonials (from eRoots website):**
- Redeia: "eRoots has demonstrated their excellence in one of the most technically challenging projects tackled by Redeia in recent years. I recommend their services."
- DSO reference: Support for dynamic voltage regulator specification and sizing using static and dynamic models.

Note: These testimonials refer to eRoots Analytics' consulting services, which use VeraGrid as their core platform. They do not necessarily confirm that these organizations run VeraGrid independently in their own operations.

**Verifiable adoption signals:**
- **Navitasoft integration:** Contributors `peterkulik-navitasoft` and `jozsefgorcs-navitasoft` have committed code to the repository, confirming code-level engagement by an external company.
- **eRoots commercial use:** VeraGrid is the core product of eRoots Analytics -- it is deployed in real consulting engagements.
- **FOSDEM 2026 talk:** Santiago Penate-Vera presented "Making of a modern power systems software" at FOSDEM 2026 (Energy track), describing VeraGrid as bridging "research, operational applications, and long-term infrastructure planning."
- **LF Energy landscape:** The project is listed in the LF Energy landscape directory (issue #453 references updating the entry).

**Community indicators (accessed 2026-03-24):**

| Metric | Value |
|--------|-------|
| GitHub stars | 519 |
| GitHub forks | 124 |
| All-time contributors | 34 |
| PyPI downloads (gridcalengine, lifetime) | ~200k |
| PyPI downloads (veragridengine, since late 2025) | ~23k+ |
| Stack Overflow tag | None |
| Third-party ecosystem packages | None found |
| Discord server | Active (linked from README) |
| GitHub Discussions | 4 total |

**Academic adoption:**
- Zenodo DOI for citation tracking
- Referenced in the `ModelicaGridData` paper (ScienceDirect)
- Creator has published academic papers on the HELM algorithm used in GridCal

**Documentation as adoption barrier:**
- ReadTheDocs documentation covers up to v5.0.2; current version is 5.6.x
- Getting Started and Tutorial links were reported broken (issues #416, #347; both closed 2026-01-07)
- GitHub wiki pages return loading errors
- gridcal.org shows "under construction"
- These gaps likely limit self-service community adoption

**Consumed observation -- doc-gaps (A-3, A-6, B-2):**
Multiple documentation gaps were identified during code evaluation. The API documentation lags significantly behind the installed version (docs cover v5.0.2, installed v5.6.28). OPF options naming inconsistencies, undocumented soft constraints, and undocumented SCED workflow patterns all required source code reading to discover. These gaps are consistent with a project whose adoption relies on direct commercial support from eRoots rather than self-service documentation.

Sources:
- [eRoots Analytics VeraGrid page](https://www.eroots.tech/veragrid-download) (accessed 2026-03-24)
- [FOSDEM 2026 talk](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/)
- [GitHub SanPen/GridCal](https://github.com/SanPen/GridCal) (repo stats, accessed 2026-03-24)
- [LF Energy Summit recap](https://lfenergy.org/lf-energy-summit-recap-and-video-vision-for-power-systems-planning-the-gridcal-example/)
- [PyPI veragridengine](https://pypi.org/project/veragridengine/)

## Implications

The operational adoption evidence is credible but concentrated in the eRoots consulting ecosystem. The Redeia testimonial is the strongest signal -- Redeia is Spain's TSO and a major European grid operator. However, it is unclear whether Redeia runs VeraGrid independently or only through eRoots-mediated consulting engagements. The absence of Stack Overflow presence, third-party packages, or independent community resources suggests the tool's user base is narrow and closely tied to eRoots' commercial relationships. For maturity grading, this represents "niche operational adoption" rather than broad community-driven deployment.
