---
test_id: E-4
tool: gridcal
dimension: maturity
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "60671c3b"
timestamp: "2026-03-13T23:00:00Z"
---

# E-4: Funding Model

## Finding

GridCal/VeraGrid is commercially backed by eRoots Analytics (Barcelona, Spain), a power systems consultancy that uses VeraGrid as its core software product. The project has an open-core business model with the engine published under MPL-2.0 and proprietary compute engines (Bentayga, NewtonPA) available commercially.

## Evidence

**Commercial entity:** eRoots Analytics, S.L. (Barcelona, Spain)
- Website: https://www.eroots.tech
- Author email on PyPI: `spenate@eroots.tech`
- Offers commercial support, custom development, and Windows installers
- Multiple eRoots employees contribute to the public repository (alexblancoeroots, mmutto, mrosesgh, Carlos-Alegre, JosepFanals, etc.)

**Business model:**
- **Open-source engine** (`veragridengine`): MPL-2.0 licensed, freely available on PyPI
- **GUI application** (`veragrid`): MPL-2.0 licensed, includes Qt-based graphical interface
- **Commercial add-ons:** Proprietary compute backends (Bentayga, NewtonPA, PGM, GSLV engines) for parallel computation
- **Commercial services:** Consulting, custom development, training
- **Windows installer:** Available at https://www.eroots.tech/software

**Institutional backing:**
- No visible venture capital or grant funding
- Revenue appears to come from consulting contracts with utilities (research-context.md mentions Redeia, Schneider Electric, GE Vernova as listed clients)
- eRoots team has ~15 identifiable contributors in the GitHub history
- Zenodo DOI for academic citation: https://www.zenodo.org/badge/latestdoi/49583206

**Academic connection:**
- Creator Santiago Penate Vera has published academic papers on the algorithms used in GridCal
- The project is registered on Zenodo for academic citation tracking

## Implications

The eRoots commercial backing provides more sustainable funding than a purely volunteer-driven project, but the company is small and the project's sustainability is closely tied to eRoots' commercial viability. The open-core model means the most advanced features (parallel compute engines) are proprietary, though the core engine remains fully open-source.
