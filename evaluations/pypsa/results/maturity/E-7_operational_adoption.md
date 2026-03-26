---
test_id: E-7
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: c1355776
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

# E-7: Operational Adoption

## Result: PASS

## Finding

PyPSA has significant operational adoption beyond academia, with documented use by
5+ transmission system operators (including TransnetBW, TenneT, Austrian Power Grid,
ENTSO-E), government agencies (IEA, ACER, Canada Energy Regulator, GIZ), and
commercial entities (Shell, Saudi Aramco, d-fine). The distinction between planning-grade
and real-time operational use is important: PyPSA is used for planning and policy
analysis, not real-time dispatch.

## Evidence

**Sources:**
- PyPSA official users page (https://docs.pypsa.org/latest/home/users/), accessed 2026-03-24
- PyPSA-USA documentation (https://pypsa-usa.readthedocs.io/), accessed 2026-03-24
- GitHub issue tracker (https://github.com/PyPSA/PyPSA/issues), accessed 2026-03-24

### Documented Deployments by Category

#### 1. Transmission System Operators (TSOs)

| Organization | Country | Use Type |
|-------------|---------|----------|
| TransnetBW | Germany | Grid planning |
| TenneT | Netherlands | Grid planning |
| Austrian Power Grid | Austria | Grid planning |
| ONTRAS | Germany (gas) | Gas network planning |
| Austrian Gas Grid Management | Austria (gas) | Gas network planning |
| ENTSO-E | EU coordination body | European grid coordination |

This is the strongest evidence of production-grade operational adoption. TSOs using
PyPSA for grid planning decisions implies the tool's outputs feed into infrastructure
investment decisions worth billions of euros.

#### 2. Government Agencies and Regulators

| Organization | Scope | Use Type |
|-------------|-------|----------|
| International Energy Agency (IEA) | Global | Global Energy and Climate Model |
| EU Agency for Cooperation of Energy Regulators (ACER) | European | Regulatory analysis |
| European Commission Joint Research Centre | European | Policy analysis |
| Canada Energy Regulator | Canada | National energy regulation |
| GIZ (German development agency) | Global | Development energy planning |

#### 3. Commercial and Industry Users

| Organization | Sector | Use Type |
|-------------|--------|----------|
| Shell | Oil & gas major | Energy transition planning |
| Saudi Aramco | Oil & gas major | Energy planning |
| d-fine | Consulting | Energy system modeling (also provides PyPSA support) |
| Witteveen+Bos | Engineering | Infrastructure planning |
| Energynautics | Consulting | Grid analysis (also provides PyPSA support) |
| Tokyo Electric Power Services | Utility | Energy system analysis |
| Serentica | India IPP | Power generation planning |

#### 4. Research Institutions (20+ universities, 10+ research institutes)

Major research institutes include:
- Fraunhofer IEG, ISE, IEE, ISI (Germany)
- RISE Research Institutes of Sweden
- Council for Scientific and Industrial Research (South Africa)
- The Energy and Resources Institute (India)

#### 5. Regional Model Deployments

| Model | Scope | Maintained By |
|-------|-------|---------------|
| PyPSA-Eur | 30+ European countries | TU Berlin / OET |
| PyPSA-Earth | Global | Open Energy Transition |
| PyPSA-USA | United States | Stanford University |
| PyPSA-DE | Germany (high-resolution) | TU Berlin |

#### 6. Non-Profit Policy Organizations

Rocky Mountain Institute, Agora Energiewende, Climate Analytics, Ember, TransitionZero,
Instrat (Poland), ClimateXChange — these organizations use PyPSA outputs for policy
advocacy and analysis.

### Distinction: Production vs Academic

PyPSA's operational adoption falls into the **planning-grade production** category:

- **Production use (planning)**: TSOs (TransnetBW, TenneT), regulators (ACER, IEA),
  and commercial entities use PyPSA for grid planning, investment analysis, and policy
  modeling. These are production workflows where results inform real-world decisions.
- **Not real-time dispatch**: PyPSA is not known to be used by ISOs/TSOs as a primary
  real-time dispatch/SCADA/EMS tool. Its design is oriented toward optimization and
  planning, not sub-second operational control.
- **Beyond academic citation**: The presence of TSOs, regulators, oil majors, and
  engineering consultancies on the documented user list distinguishes PyPSA from
  tools with purely academic adoption. Issue tracker engagement from industry
  practitioners (e.g., #1590: 200 MW BESS congestion study with JAO Static Grid
  Model impedance values for TenneT grid connections) confirms real-world usage.

### Community Scale

- 1,905 GitHub stars, 620 forks (as of 2026-03-24)
- 99 total contributors
- Active Discord community
- Zenodo DOI: 10.5281/zenodo.3946412

## Implications

PyPSA has the broadest documented operational adoption of any open-source Python
power system analysis tool. The user list spans TSOs, government agencies, oil
majors, and engineering consultancies across 6 continents. While the tool is not used
for real-time dispatch, its planning-grade production use by entities making
billion-euro infrastructure decisions represents genuine operational adoption that
transcends academic citation.

## Recorded Metrics

- tso_users: 6 (TransnetBW, TenneT, Austrian Power Grid, ONTRAS, Austrian Gas Grid, ENTSO-E)
- government_users: 5 (IEA, ACER, JRC, Canada Energy Regulator, GIZ)
- commercial_users: 7+ (Shell, Saudi Aramco, d-fine, Witteveen+Bos, Energynautics,
  Tokyo Electric Power Services, Serentica)
- regional_models: 4 (PyPSA-Eur, PyPSA-Earth, PyPSA-USA, PyPSA-DE)
- use_type: planning-grade production (not real-time dispatch)
- github_stars: 1,905
- github_forks: 620
