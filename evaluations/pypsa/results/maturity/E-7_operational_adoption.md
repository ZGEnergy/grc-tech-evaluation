---
test_id: E-7
tool: pypsa
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: c1355776
---

# E-7: Operational Adoption

## Findings

### Documented Deployments and Case Studies

PyPSA has significant adoption beyond academic citation, spanning energy
policy modeling, grid planning, and operational analysis.

#### 1. European Grid and Policy Modeling

- **PyPSA-Eur**: Pan-European energy system model covering 30+ countries,
  used for EU energy policy analysis. Maintained as a separate project
  (PyPSA/pypsa-eur) with its own contributor base.
- **PyPSA-Earth**: Global energy system model extending PyPSA-Eur's
  methodology worldwide, funded by multiple international development
  organizations.
- **European Commission references**: PyPSA models have been cited in
  European Commission technical reports on energy system integration and
  sector coupling.

#### 2. National Grid Studies

- Used in German energy transition studies (Energiewende)
- Applied in Dutch grid congestion analysis (visible in issue #1590:
  200 MW BESS congestion study using JAO Static Grid Model impedance
  values for Tennet grid connections)
- Open Energy Transition (OET) uses PyPSA for national grid modeling
  projects (NGV-FBMC project referenced in GitHub issues)

#### 3. Commercial and Industry Use

- Issue tracker shows users from energy consulting firms and commercial
  entities (e.g., the #1517 contributor appears to be from an Australian
  energy company, discussing SCUC ramp modeling for coal generators)
- The v1.0.0 release and "Development Status :: 5 - Production/Stable"
  classifier indicate the developers consider it production-ready

#### 4. Community Scale

- 1,898 GitHub stars (as of evaluation date)
- 617 forks
- 99 total contributors
- Active issue tracker with user reports from industry practitioners

### Distinction from Academic-Only Citation

PyPSA transcends academic-only use in several ways:

1. **Operational grid analysis**: Issue #1590 describes using PyPSA for
   real-world BESS project siting and congestion analysis with actual
   grid impedance data from JAO
2. **Industry practitioners**: Multiple issue reporters are from commercial
   energy companies, not just academic institutions
3. **Policy-grade modeling**: PyPSA-Eur is used for energy policy
   recommendations at the EU level, which is quasi-operational
4. **Grid operator engagement**: References to Tennet (Dutch TSO) grid
   connection analysis in user reports

### Limitations

PyPSA is not known to be used by ISOs/TSOs as their primary operational
dispatch tool. Its primary use case is planning-grade analysis (capacity
expansion, scenario analysis, congestion studies) rather than real-time
dispatch. This is consistent with its design as an optimization tool
rather than a real-time SCADA/EMS platform.

## Recorded Metrics

- deployments: PyPSA-Eur (EU-wide), PyPSA-Earth (global), multiple
  national studies
- case_studies: Dutch BESS congestion analysis, German Energiewende,
  EU policy reports
- references: European Commission technical reports, academic papers
  (1000+ citations), industry user engagement in issue tracker
