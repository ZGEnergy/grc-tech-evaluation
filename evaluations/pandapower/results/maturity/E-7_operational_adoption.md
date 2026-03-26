---
test_id: E-7
tool: pandapower
dimension: maturity
network: N/A
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
protocol_version: "v11"
skill_version: "v2"
test_hash: "38476a38"
---

# E-7: Operational Adoption Evidence

## Result: INFORMATIONAL

## Finding

pandapower has strong evidence of operational adoption by European utilities, DSOs, and
TSOs, including confirmed production deployments at Netze BW (System TAZAN), 50Hertz
Transmission GmbH (MCCS real-time grid calculation), and UK Power Networks. Multiple
government-commissioned grid planning studies use pandapower as their calculation engine.

## Evidence

### Confirmed Production Deployments

**1. Netze BW GmbH -- System TAZAN**
- **Organization:** Netze BW GmbH (German distribution system operator, subsidiary of EnBW)
- **Nature:** Production grid planning system ("TAZAN") integrated into Netze BW's existing
  IT landscape with interfaces to their GIS, grid calculation, and ERP systems
- **Use:** Automated creation, calculation, and evaluation of solution variants for daily
  grid planning tasks
- **Source:** https://www.iee.fraunhofer.de/en/application-fields/energy-grids/pandapowerpro.html
  (accessed 2026-03-24)
- **Classification:** Confirmed production DSO deployment

**2. 50Hertz Transmission GmbH -- MCCS Project**
- **Organization:** 50Hertz Transmission GmbH (German TSO, one of four German TSOs)
- **Nature:** The MCCS team at 50Hertz uses pandapower as "an integral part" for real-time
  grid calculation and analysis, particularly for optimization challenges
- **Source:** https://www.iee.fraunhofer.de/en/presse-infothek/press-media/2024/pandapower-open-source-tool-for-modelling-analyzing-power-grids.html
  (accessed 2026-03-24)
- **Classification:** Confirmed production TSO deployment

**3. UK Power Networks**
- **Organization:** UK Power Networks (UK distribution network operator serving 8.4M customers)
- **Nature:** Uses pandapower to "unlock network data and information to facilitate independent
  network analysis" and for "detailed network performance simulations"
- **Source:** Fraunhofer IEE press release (2024), cited above
- **Classification:** Confirmed operational DSO use

**4. Bayernwerk Netz GmbH**
- **Organization:** Bayernwerk Netz GmbH (largest German DSO by area, subsidiary of E.ON)
- **Nature:** Grid planning studies conducted with pandapower
- **Source:** Fraunhofer IEE pandapowerPro page, cited above
- **Classification:** Confirmed DSO use for grid planning

**5. Romande Energie SA**
- **Organization:** Romande Energie SA (Swiss electric utility)
- **Nature:** Grid planning studies conducted with pandapower
- **Source:** Fraunhofer IEE pandapowerPro page, cited above
- **Classification:** Confirmed utility use

### Government-Commissioned Studies

**Verteilnetzstudie Hessen (Hessen Distribution Network Study)**
- **Commissioners:** Hessian state government
- **Conducted by:** BearingPoint GmbH and Fraunhofer IEE
- **Scope:** 8 HV grid groups, 60 MV grids, 670 LV grids from 10 different distribution
  grid operators across the state of Hesse
- **Planning horizon:** 2024-2034
- **Role:** pandapower used as the central calculation and analysis tool
- **Reference:** https://www.energieland.hessen.de/verteilnetzstudie_hessen
- **Classification:** Government-commissioned grid planning (operational, not academic)

### TSO Validation (Research Platform)

**RTE France (via Grid2Op)**
- **Organization:** RTE (Reseau de Transport d'Electricite), France's TSO
- **Nature:** RTE developed Grid2Op (413+ GitHub stars), which uses pandapower as its default
  power flow backend for the L2RPN (Learning to Run a Power Network) competition series
- **Caveat:** Grid2Op is a research/competition platform, not a production SCADA/EMS system.
  However, selection by a major TSO validates pandapower's accuracy for transmission-scale
  networks.

### DSO Ecosystem Integration

**Power Grid Model (LF Energy / Alliander)**
- **Organization:** Alliander (Dutch DSO), now an LF Energy project
- **Nature:** C++ high-performance backend integrated with pandapower as an alternative
  solver. Listed in pandapower's README as a supported solver.
- **Significance:** A production DSO built interoperability with pandapower, recognizing its
  data model as a de facto standard.

**Retoflow (Commercial Spin-off)**
- **Organization:** Retoflow GmbH, founded 2021 by Fraunhofer IEE and University of Kassel
  employees
- **Nature:** Develops commercial interactive network editors and integrated solutions built
  on pandapower for gas, water, heating, and EV charging applications
- **Significance:** Commercial viability validated by spin-off formation

### Institutional Backing

- **University of Kassel** -- Department for Sustainable Electrical Energy Systems (e2n)
- **Fraunhofer IEE** -- Germany's largest applied research institute for energy systems

### Scale Indicators (2026-03-24)

- **PyPI downloads:** 500,000+ total (per Fraunhofer IEE 2024 press release); ~232,000/month
- **GitHub stars:** 1,128
- **GitHub forks:** 558
- **GitHub dependents:** 487 repositories, 53 packages
- **Academic citations:** 952+ (Thurner et al., IEEE Trans. Power Systems, 2018)
- **Geographic reach:** Confirmed use in Germany, UK, Switzerland, France, USA, China

### IEC Standards Compliance

pandapower implements IEC 60909 for short-circuit calculations, a regulatory requirement
in European grid planning, validated against commercial software results.

## Implications

pandapower has the strongest operational adoption evidence among the tools under evaluation
for European distribution grid planning:

- **3 confirmed production DSO/TSO deployments** (Netze BW, 50Hertz, UK Power Networks)
- **2 additional DSO grid planning engagements** (Bayernwerk, Romande Energie)
- **1 government-commissioned study** (Hessen state-level grid planning)
- **1 commercial spin-off** (Retoflow) validating commercial viability

The adoption profile is strongest in European distribution grid planning. There is no
evidence of adoption by North American independent system operators, likely because
pandapower's primary focus is distribution-level analysis and European grid standards.
