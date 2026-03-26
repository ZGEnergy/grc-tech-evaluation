---
test_id: E-7
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "c1355776"
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
timestamp: 2026-03-24T00:00:00Z
---

# E-7: Operational Adoption

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl is developed and used operationally at NREL (a U.S. DOE national laboratory) for production cost modeling, integrated resource planning, and market simulation research. It is promoted through the DOE-backed Global Power System Transformation (G-PST) Consortium for use by utilities and system operators. However, no specific utility, ISO, or commercial entity has been publicly identified as running PowerSimulations.jl in a production operational setting. Adoption evidence is strongest in the government research and international development context, weaker for commercial/utility deployment.

## Evidence

### NREL / DOE Internal Use

- PowerSimulations.jl was developed under the Scalable Integrated Infrastructure Planning (SIIP) initiative at NREL, funded by the U.S. Department of Energy (DOE). Software Record SWR-23-104.
- NREL uses Sienna (the ecosystem containing PowerSimulations.jl) for internal power system analysis, including production cost modeling and renewable integration studies.
- The NREL Sienna page (`https://www.nrel.gov/analysis/sienna`) states: "To plan and design clean energy systems, more researchers, utilities, and operators are turning to Sienna."
- However, no specific utilities or operators are named on the page.

### G-PST Consortium

- The G-PST Consortium (`https://globalpst.org/sienna-modeling-framework/`) features Sienna as a recommended open-source modeling framework for power system transformation.
- G-PST is a practitioner-driven initiative engaging power system operators, research institutes, and governments globally.
- A USAID-NREL G-PST webinar series presented Sienna tools alongside SAM and RE Data Explorer for production cost modeling in developing nations.
- This indicates institutional backing for adoption but does not confirm specific operational deployments.

### Academic and Research Use

- The 2024 arXiv paper (2404.03074) describes PowerSimulations.jl's architecture in an academic context (UC Berkeley + NREL authors).
- The paper compares PowerSimulations.jl to commercial tools (PLEXOS, PROMOD, GE-MAPS) but does not document any utility or ISO adopting it as a replacement.
- GitHub metrics: 312 stars, 79 forks (as of 2026-03-24), indicating moderate community interest. Marginal increase from 311/78 observed 10 days prior.

### What Was NOT Found

Despite targeted searches, the following could not be confirmed:
- No specific ISO publicly using PowerSimulations.jl
- No named utility company deploying it in operations
- No commercial entity citing it as a production tool
- No case studies documenting real-world operational deployment outside NREL

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl` (accessed 2026-03-24)
- NREL Sienna page, G-PST consortium page, arXiv paper 2404.03074 (accessed 2026-03-14, re-confirmed 2026-03-24)

## Implications

1. **Government lab adoption is strong:** NREL uses Sienna internally for DOE-funded research, which provides a baseline of institutional commitment and real-world validation against large-scale test systems.
2. **Pathway to broader adoption exists:** The G-PST consortium and USAID partnerships create a pipeline for utility and operator adoption, particularly in developing countries pursuing renewable integration.
3. **No confirmed commercial/utility production use:** The absence of named utility or ISO deployments means PowerSimulations.jl remains primarily a research and planning tool. This is common for open-source power system tools but distinguishes it from commercial products like PLEXOS or PROMOD that have documented utility customer bases.
4. **Risk for operational reliance:** An organization adopting PowerSimulations.jl for production operations would be an early mover without peer references to validate the operational workflow.
