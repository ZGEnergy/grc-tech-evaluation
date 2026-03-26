---
test_id: E-4
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "60671c3b"
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

# E-4: Funding Model

## Result: INFORMATIONAL

## Finding

GridCal/VeraGrid is commercially backed by eRoots Analytics (Barcelona, Spain), a small power systems consultancy founded in 2022. The project follows an open-core business model with the engine under MPL-2.0 and proprietary compute engines available commercially. An LF Energy incubation application was withdrawn in January 2025 in favor of retaining ownership within eRoots.

## Evidence

**Commercial entity:** eRoots Analytics, S.L. (Barcelona, Spain)
- Website: https://www.eroots.tech
- Founded: 2022
- CTO/Founder: Santiago Penate Vera (GridCal creator since 2015)
- Origin: CITCEA-UPC (Universitat Politecnica de Catalunya)
- PyPI publisher email: `spenate@eroots.tech`

**Business model:**
- **Open-source engine** (`veragridengine`): MPL-2.0 licensed, freely available on PyPI
- **GUI application** (`veragrid`): MPL-2.0 licensed, Qt-based graphical interface
- **Proprietary compute backends:** Bentayga, NewtonPA, PGM, GSLV engines for parallel computation (commercial license from eRoots)
- **Commercial services:** Consulting, custom plugin development, training subscriptions, data migration
- **Windows installer:** Available via eRoots website

**Claimed client list (from eRoots website, accessed 2026-03-24):**
18+ organizations listed including:
- **Utilities/TSOs:** Redeia, RTE, Elewit, Nidec
- **Energy companies:** Acciona Energia, Engie, GE Vernova, Hyosung
- **Technology/Industrial:** Schneider Electric
- **Academic/Research:** ETH Zurich, Barcelona Supercomputing Center (BSC)
- **Consultancies:** Aiguasol, teknoCEA, Azimut 360, TTA Energy, CRESYM, iGrid

**Testimonials (from eRoots website):**
- Redeia reference: "eRoots has demonstrated their excellence in one of the most technically challenging projects tackled by Redeia in recent years."
- DSO project reference: support for dynamic voltage regulator specification and sizing

**LF Energy incubation (GitHub issue lf-energy/tac#187):**
- Applied: July 12, 2024
- Placed on hold: August 23, 2024
- Withdrawn: January 6, 2025
- Reason: "Project has decided to retain the ownership of GridCal within eRoots Analytics."
- The withdrawal indicates a strategic preference for commercial control over foundation governance.

**Grant/VC funding:** No visible venture capital funding, government grants, or foundation sponsorship. Revenue appears to derive from consulting contracts and commercial license sales.

**License history:**
- Pre-2022: GPLv3
- Jan 2022 (v4.4.2): LGPL
- Nov 2024 (v5.2.0): MPL-2.0 (current)

The progressive license relaxation (GPLv3 -> LGPL -> MPL-2.0) aligns with the commercial strategy of enabling proprietary downstream use.

Sources:
- [eRoots Analytics VeraGrid page](https://www.eroots.tech/veragrid-download) (accessed 2026-03-24)
- [LF Energy TAC issue #187](https://github.com/lf-energy/tac/issues/187) (closed 2025-01-06)
- [FOSDEM 2026 talk](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/)
- [PyPI veragridengine](https://pypi.org/project/veragridengine/)

## Implications

The eRoots commercial backing provides more sustainable funding than a volunteer project, but the company is small and young (founded 2022). The project's sustainability is closely tied to eRoots' commercial viability. The withdrawn LF Energy application means there is no foundation-level governance or long-term stewardship beyond eRoots. The open-core model means the most performant compute engines are proprietary, creating a dependency on eRoots for production-grade parallel computation. For maturity grading, this is a "small company backing" model -- stronger than unfunded open source, but weaker than foundation-backed or large-company-sponsored projects.
