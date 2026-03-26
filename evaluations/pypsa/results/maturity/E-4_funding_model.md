---
test_id: E-4
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 5b74387a
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T23:50:00Z
---

# E-4: Funding Model

## Result: PASS

## Finding

PyPSA has durable multi-channel institutional backing through TU Berlin (tenured
academic leadership), Open Energy Transition (non-profit), EU research grants
(Horizon Europe, CETPartnership), and a large downstream ecosystem. The project
would survive the loss of any single funding source.

## Evidence

**Sources:**
- PyPSA website (https://pypsa.org/), accessed 2026-03-24
- Open Energy Transition (https://openenergytransition.org/), accessed 2026-03-24
- TU Berlin ENSYS department (https://www.tu.berlin/en/ensys), accessed 2026-03-24
- PyPSA docs user page (https://docs.pypsa.org/latest/home/users/), accessed 2026-03-24

### Institutional Affiliations

1. **TU Berlin (Technische Universitat Berlin)** — Department of Digital
   Transformation in Energy Systems. Tom Brown (nworbmot, project founder) is a
   professor at TU Berlin. This is the primary institutional home and development
   hub since 2021 (previously at Karlsruhe Institute of Technology, 2018-2021).

2. **Open Energy Transition (OET)** — Non-profit founded 2023, co-maintainer of
   PyPSA ecosystem tools (Linopy, Atlite, Technology Data, PyPSA-Eur, PyPSA-Earth).
   Funded by Sequoia Climate Foundation. Provides commercial support services.

3. **Stanford University** — Maintains PyPSA-USA, a US-focused energy system model
   built on PyPSA, developed by the INES Research Group.

### Funding Sources

- **European Commission grants**: PyPSA-Eur funded through Horizon Europe programs.
  CETPartnership project RESILIENT (stochastic optimization for PyPSA-Eur) provides
  direct funding for core library development.
- **Sequoia Climate Foundation**: Funds Open Energy Transition, which co-maintains
  PyPSA ecosystem.
- **TU Berlin academic positions**: Core maintainers hold permanent academic
  positions, providing salary funding independent of individual grants.
- **Breakthrough Energy**: TU Berlin partnered with Breakthrough Energy to
  accelerate Europe's net-zero transition using PyPSA models.
- **Commercial support**: Paid support available through OET, d-fine, Energynautics,
  and CLIMACT, creating revenue diversification.

### Downstream Ecosystem Scale

The PyPSA ecosystem includes major regional models that drive continued core
library development:
- **PyPSA-Eur**: Pan-European energy system model (30+ countries)
- **PyPSA-Earth**: Global energy system model
- **PyPSA-USA**: US energy system model (Stanford University)
- **PyPSA-DE**: High-resolution German energy system model

### Community Scale

- 1,905 GitHub stars, 620 forks (as of 2026-03-24)
- 99 total contributors
- Active Discord community
- Cited by European Commission Joint Research Centre, ACER, IEA

### Durability Assessment

**High durability.** The combination of:
1. Tenured academic leadership at a major European university (TU Berlin)
2. Dedicated non-profit organizational support (OET, funded by Sequoia Climate Foundation)
3. Large downstream user base spanning TSOs, government agencies, and companies
4. Multiple EU research grants providing project-specific funding
5. Commercial support revenue from 4+ consultancies
6. US institutional backing via Stanford University (PyPSA-USA)

provides at least 5 independent funding channels. The project would survive the
departure of any single contributor, the end of any single grant, or the dissolution
of any single supporting organization.

## Implications

PyPSA's funding model is among the strongest in the open-source power systems tool
landscape. The combination of permanent academic positions, philanthropic backing,
government grants, and commercial support creates a resilient funding structure. The
successful transition from KIT to TU Berlin (2021) and the founding of OET (2023)
demonstrate institutional adaptability.

## Recorded Metrics

- funding_sources: TU Berlin (academic), Sequoia Climate Foundation (philanthropic),
  EU grants (research), OET (non-profit), commercial support (consulting)
- funding_channels: 5+
- durability: high
