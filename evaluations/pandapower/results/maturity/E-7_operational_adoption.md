---
test_id: E-7
tool: pandapower
dimension: maturity
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# E-7: Operational Adoption

## Result: PASS

## Finding

pandapower has documented use by European distribution grid operators (DSOs) for grid planning studies, and its commercial variant (pandapowerpro) is deployed at 10+ DSOs as a central calculation tool. A US national laboratory (Lawrence Berkeley) has built a regulatory prototype on it. However, no evidence of adoption by ISOs, RTOs, or transmission system operators was found. Adoption is concentrated in distribution-level planning rather than real-time operations.

## Evidence

**Grid operator deployments (documented by Fraunhofer IEE):**

- **Bayernwerk Netz GmbH** -- grid planning studies (German DSO, E.ON subsidiary)
- **Netze BW GmbH** -- grid planning studies (German DSO, EnBW subsidiary)
- **Romande Energie SA** -- grid planning studies (Swiss DSO)
- **10+ unnamed DSOs** -- using pandapowerpro as "central calculation and analysis tool" for automated grid planning

**National laboratory use:**

- **Lawrence Berkeley National Laboratory (LBNL)** -- developed an "Integrated Modeling Tool for Regulators" prototype using pandapower

**Academic/research citations:**

- 500,000+ PyPI downloads as of February 2024 (per Fraunhofer/University press release)
- ~3,600 weekly PyPI downloads (current)
- Referenced in IEEE publications and used in university research worldwide
- University of Split (Croatia), National University of Singapore among documented users

**What was NOT found:**

- No evidence of use by any ISO/RTO (ERCOT, PJM, CAISO, MISO, etc.)
- No evidence of use in real-time grid operations (EMS/SCADA integration)
- No evidence of transmission-level operational deployment
- No evidence of use by US utilities for operational purposes

**Sources:**
- [Fraunhofer IEE pandapowerpro](https://www.iee.fraunhofer.de/en/application-fields/energy-grids/pandapowerpro.html) (accessed 2026-03-06)
- [pandapower references](https://www.pandapower.org/references/) (accessed 2026-03-06)
- [University of Kassel press release](https://www.uni-kassel.de/uni/en/aktuelles-aus-der-universitaet/sitemap-detail-news/2024/02/14/pandapower-tool-zur-optimierung-von-stromnetzen-erreicht-500000-downloads.html) (accessed 2026-03-06)

## Implications

pandapower has meaningful operational adoption at the distribution grid operator level in Europe, primarily for planning studies rather than real-time operations. The commercial spin-off (pandapowerpro/Retoflow) with 10+ DSO customers validates the tool's production readiness for planning workflows. The LBNL prototype adds a US government laboratory credential. However, the absence of ISO/RTO or transmission-level adoption means the tool's operational track record is limited to distribution planning -- a narrower scope than tools like MATPOWER or PowerWorld that have broader utility adoption.
