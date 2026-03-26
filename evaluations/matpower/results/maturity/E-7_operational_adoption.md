---
test_id: E-7
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "a6a6a5f7"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# E-7: Operational Adoption

## Result: INFORMATIONAL

## Finding

MATPOWER is overwhelmingly an academic/research tool with no confirmed production operational deployments at utilities or ISOs. It is the most widely cited open-source power systems simulation tool in academic literature, with over 800,000 downloads. Government lab usage exists but is limited to research and simulation, not real-time grid operations.

## Evidence

### Academic adoption (strong)

- **Downloads:** Over 800,000 total downloads (per matpower.org, accessed 2026-03-14)
- **GitHub metrics:** 539 stars, 173 forks, 29 watchers (accessed 2026-03-14)
- **Citations:** The foundational paper (Zimmerman, Murillo-Sanchez, Thomas, "MATPOWER: Steady-State Operations, Planning, and Analysis Tools for Power Systems Research and Education," IEEE Trans. Power Syst., 2011) is one of the most cited papers in power systems engineering
- **Ecosystem:** Multiple derived tools and wrappers exist (MATPOWER-wrapper by GMLC-TDC, matpower-pip by yasirroni, numerous MATLAB File Exchange contributions)

### Government/national lab usage (research context)

- **ARPA-E GRID DATA program:** MATPOWER format was used as a standard interchange format for synthetic grid data (DOE-funded). This is format adoption, not operational deployment.
- **RTE France:** Provided real network data that was converted to MATPOWER format for academic use (iTesla/PEGASE snapshots). RTE's operational grid management uses their own "Convergence" platform, not MATPOWER.
- **GMLC-TDC (Grid Modernization Lab Consortium):** Developed a MATPOWER-wrapper for HELICS cosimulation, including ISO-DSO interaction modeling. This is research simulation infrastructure, not production grid operations.
- **Argonne National Lab:** Uses MATPOWER for grid modeling research. No evidence of operational deployment.

### Utility/ISO operational use (none confirmed)

No evidence was found of MATPOWER being used in production operational settings by:
- Any Independent System Operator (ISO/RTO)
- Any transmission utility
- Any distribution utility
- Any government regulatory body for real-time or day-ahead operations

Web searches for "MATPOWER operational deployment," "MATPOWER utility production use," and "MATPOWER ISO deployment" returned no relevant results beyond academic and research contexts.

### Self-description

MATPOWER's own website describes it as "intended as a simulation tool for researchers and educators that is easy to use and modify" (matpower.org/about). The project does not claim or target operational deployment.

### Format influence (significant)

While MATPOWER itself is not deployed operationally, the MATPOWER case file format (.m) has become a de facto standard interchange format for power system test cases. Many other tools (PyPSA, pandapower, PowerModels.jl, GridCal) can import MATPOWER format, making it an industry data standard independent of the tool itself.

## Implications

MATPOWER's value proposition is as a research and education platform, not as operational infrastructure. This is consistent with its design philosophy (MATLAB/Octave scripting environment, batch-mode analysis, no real-time interfaces). For the GRC evaluation context, MATPOWER's adoption strength is in its academic ubiquity and format standardization rather than operational track record. The absence of operational deployments is not a deficiency relative to the tool's stated purpose, but it means there is no evidence of production-grade reliability validation from real grid operations.
