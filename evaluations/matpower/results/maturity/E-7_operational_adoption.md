---
test_id: E-7
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-7: Operational Adoption

## Academic Use

MATPOWER is one of the most widely cited power systems simulation tools:
- **750+ citations per year** (Google Scholar, based on the 2011 and 2020 papers)
- Primary citation: R.D. Zimmerman, C.E. Murillo-Sanchez, R.J. Thomas,
  "MATPOWER: Steady-State Operations, Planning and Analysis Tools for Power
  Systems Research and Education," *IEEE Trans. Power Systems*, 2011.
- Used in virtually every power systems PhD program worldwide.
- Standard test platform for power systems optimization research.

## Known Production/Operational Use

### Utilities and ISOs

**No confirmed production deployment by a utility or ISO has been identified.**

Evidence searched:
- GitHub issues and discussions: No issues from utility/ISO users describing
  production deployments.
- PSERC membership: PSERC member utilities (AEP, Exelon, PJM, EPRI) may use
  MATPOWER for research/planning studies but not for operational systems.
- Academic literature: Papers cite MATPOWER for simulation studies, not for
  operational deployment.

### Government / National Laboratory Use

- **DOE National Laboratories** (PNNL, ANL, ORNL) use MATPOWER in research
  contexts, particularly for grid resilience studies and renewable integration
  modeling.
- **ARPA-E funded projects** have used MATPOWER as a benchmark platform.
- No evidence of use in operational government energy systems.

### Consulting and Planning

- Power systems consulting firms (e.g., PowerWorld, GE Vernova) have their own
  commercial tools. MATPOWER is used in academic/research contexts, not as a
  consulting delivery tool.
- Some planning studies reference MATPOWER for validation against commercial tools.

### Industry Training

- Used in industry training courses and workshops by PSERC member organizations.
- MathWorks references MATPOWER in power systems education materials.

## Comparison with Commercial Alternatives

| Tool | Operational Use | License |
|------|----------------|---------|
| PSS/E (Siemens) | Widespread ISO/utility production use | Commercial |
| PowerWorld | Widespread planning/training | Commercial |
| PSCAD | EMT simulation, production use | Commercial |
| MATPOWER | Academic/research only | BSD-3 |
| OpenDSS (EPRI) | Distribution analysis, some utility use | BSD |

## Assessment

MATPOWER's adoption is overwhelmingly academic. Despite being the most-cited
open-source power systems tool, there is no evidence of production deployment
by utilities, ISOs, or grid operators. Key barriers to operational adoption:

1. **MATLAB/Octave platform:** Operational systems typically use C/C++, Python,
   or Java. MATLAB licensing costs and Octave performance limitations are barriers.
2. **No commercial support:** No SLA, no vendor relationship, no incident response.
3. **Steady-state only:** No dynamic/transient simulation capability.
4. **Single-developer risk:** Unacceptable for production-critical systems.
5. **No data integration:** No connectors to SCADA, EMS, or market systems.

The tool's strength is as a **research and education platform** — a role it
fills exceptionally well. The distinction between academic citation and
operational adoption is critical for this evaluation.
