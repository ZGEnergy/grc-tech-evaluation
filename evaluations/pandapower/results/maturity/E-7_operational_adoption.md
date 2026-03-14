---
test_id: E-7
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "38476a38"
---

# E-7: Operational Adoption Evidence — pandapower

## Sub-criterion
5a (Demonstrated Maturity)

## Method
Searched pandapower.org references page, GitHub dependents, Fraunhofer IEE project pages,
Semantic Scholar citation data, PyPI download statistics, and downstream project
documentation for evidence of operational/production deployment by utilities, ISOs, or
government agencies. Carefully distinguished documented production use from academic
citations.

## Institutional Backing

pandapower is jointly developed by:
- **University of Kassel** — Department for Sustainable Electrical Energy Systems (e2n)
- **Fraunhofer IEE** — Department for Distribution System Operation, Kassel

Fraunhofer IEE is Germany's largest applied research institute for energy systems. Its
involvement signals that pandapower is designed for and used in applied grid planning work,
not purely academic research.

## Evidence of Operational/Production Use

### 1. Verteilnetzstudie Hessen (Hessen Distribution Network Study)
- **Organizations:** BearingPoint GmbH and Fraunhofer IEE
- **Nature:** State-level distribution grid planning study for the German state of Hesse,
  covering the planning horizon 2024-2034
- **Significance:** This is a government-commissioned grid planning study — not a research
  paper. It uses pandapower for actual load flow and network analysis calculations that
  inform investment decisions by distribution system operators. This is the strongest
  evidence of operational use.

### 2. RTE France (via Grid2Op)
- **Organization:** RTE (Réseau de Transport d'Électricité), France's transmission system
  operator
- **Nature:** RTE developed Grid2Op (413 GitHub stars), a platform for "sequential decision
  making in power systems," which uses pandapower as its default power flow backend. Grid2Op
  is used for the L2RPN (Learning to Run a Power Network) competition series, which applies
  reinforcement learning to grid operations.
- **Caveat:** Grid2Op is described as a research/competition platform, not a production
  SCADA/EMS system. However, the fact that a major TSO selected pandapower as its default
  backend for grid simulation validates pandapower's accuracy and API quality for
  transmission-scale networks.

### 3. Lawrence Berkeley National Laboratory
- **Organization:** LBNL (US Department of Energy national laboratory)
- **Nature:** Developed an "Integrated Modeling Tool for Regulators — Proof of Concept and
  Prototype" using pandapower (Cardoso, Heleno, Mashayekh et al., 2017).
- **Caveat:** Described as a "proof of concept" — not confirmed as a production deployment.

### 4. SimBench (German Federal Ministry-funded benchmark)
- **Organizations:** Fraunhofer IEE, funded by BMWi (German Federal Ministry for Economic
  Affairs and Energy)
- **Nature:** SimBench provides standardized benchmark grid models across all voltage levels,
  built on and for pandapower. Network operators participated in project workshops.
- **Significance:** Government-funded infrastructure that uses pandapower as its native
  platform, suggesting DSO involvement in its design.

### 5. Power Grid Model (LF Energy / Alliander)
- **Organization:** Power Grid Model is an LF Energy project originally developed by
  Alliander (Dutch DSO)
- **Nature:** Power Grid Model provides a C++ high-performance backend that integrates with
  pandapower as an alternative solver. pandapower's README lists PowerGridModel as a
  supported solver for "fast steady-state distribution power system analysis."
- **Significance:** A production DSO (Alliander) built interoperability with pandapower,
  indicating pandapower's data model is recognized as a de facto standard.

## Academic Citation Impact

- **Main paper citation count:** 952 (Semantic Scholar, as of March 2026)
  - Thurner et al., "pandapower — An Open-Source Python Tool for Convenient Modeling,
    Analysis, and Optimization of Electric Power Systems," IEEE Trans. Power Systems, 2018.
- **Publication venue:** IEEE Transactions on Power Systems (top-tier power systems journal)
- pandapower is one of the most-cited open-source power system tools.

## Ecosystem and Download Scale

- **PyPI downloads:** 2.23 million total; ~232,000/month; ~8,000/day
- **GitHub dependents:** 487 repositories, 53 packages
- **GitHub stars:** 1,118
- **GitHub forks:** 556
- **Notable dependents:** Grid2Op (RTE France), pandapipes (Fraunhofer IEE), simbench
  (Fraunhofer IEE), EV2Gym

## IEC Standards Compliance

pandapower implements the **IEC 60909 standard** for short-circuit calculations, which is a
regulatory requirement in European grid planning. This implementation is validated against
commercial software results, indicating suitability for compliance-grade analysis.

## Assessment

pandapower has moderate-to-strong evidence of operational adoption:

- **Confirmed operational use:** The Verteilnetzstudie Hessen is a government-commissioned
  DSO planning study — genuine operational/production use, not academic research.
- **TSO validation:** RTE France's selection of pandapower as Grid2Op's default backend
  validates its accuracy for transmission-scale networks, though Grid2Op itself is a
  research platform.
- **DSO ecosystem integration:** Alliander's Power Grid Model provides interoperability
  with pandapower, confirming recognition by a production DSO.
- **Scale indicators:** 232k monthly downloads, 952 citations, 487 dependent repos.

The adoption profile is strongest in European distribution grid planning (German DSOs,
Fraunhofer consulting projects). There is no evidence of adoption by North American ISOs
(major North American ISOs) or utilities, likely because pandapower's primary focus is
distribution-level analysis and European grid standards (IEC 60909).
