---
test_id: E-7
tool: pypsa
dimension: maturity
slug: operational_adoption
network: N/A
protocol_version: v4
status: informational
workaround_class: null
timestamp: 2026-03-06T18:00:00Z
---

# E-7: Operational Adoption

## Summary

| Metric | Value |
|--------|-------|
| GitHub stars | 1,887 |
| GitHub forks | 614 |
| Contributors | 104 |
| Listed institutional users | 50+ organizations |
| TSO/utility users | 4+ confirmed |
| Government/regulatory users | 4+ confirmed |
| Energy company users | 3+ confirmed |
| Academic institutions | 30+ |

## Operational / Production Users

The following organizations use PyPSA or PyPSA-based models for operational planning, regulatory analysis, or production decision support. These are distinguished from purely academic citation-based usage.

### Transmission System Operators & Utilities

| Organization | Country | Use Case | Evidence Level |
|-------------|---------|----------|---------------|
| TransnetBW | Germany | Transmission planning | Listed on official users page |
| Austrian Power Grid (APG) | Austria | Grid planning | Listed on official users page |
| ONTRAS | Germany | Gas network operator, sector coupling | Listed on official users page |
| ENTSO-E | Europe | Pan-European system studies | Listed on official users page; PyPSA-Eur covers full ENTSO-E area |
| ISA | South America | Transmission planning | Listed on official users page |

### Government Agencies & Regulators

| Organization | Country | Use Case | Evidence Level |
|-------------|---------|----------|---------------|
| International Energy Agency (IEA) | International | Global Energy and Climate Model; seasonal variation analysis | Confirmed: IEA 2024 report used PyPSA for electricity system analysis in 2050 scenarios |
| ACER (EU Energy Regulator) | EU | EU-wide flexibility assessment platform | Confirmed: ACER is building a PyPSA solution for flexibility assessment |
| Canada Energy Regulator | Canada | Energy system modeling | Listed on official users page |
| GIZ | Germany | Development cooperation energy planning | Listed on official users page |

### Energy Companies

| Organization | Sector | Use Case | Evidence Level |
|-------------|--------|----------|---------------|
| Shell | Oil & gas major | Energy transition modeling | Listed on official users page |
| Saudi Aramco | Oil & gas | Energy system analysis | Listed on official users page |
| spire | Energy | Listed on official users page | Listed |

### Consultancies & Engineering Firms

| Organization | Use Case |
|-------------|----------|
| d-fine | Quantitative consulting |
| Energynautics GmbH | Power systems engineering |
| Witteveen+Bos | Infrastructure consulting |
| Meridian Economics | Energy economics |

### Non-Profit / Think Tanks

| Organization | Use Case |
|-------------|----------|
| Open Energy Transition | Open-source energy modeling |
| TransitionZero | Clean energy transition analysis |
| Centre for Net Zero | Net-zero pathway modeling |
| Ember | Global electricity transition tracking |
| Agora Energiewende | German energy transition policy |
| Rocky Mountain Institute | Clean energy deployment |
| Climate Analytics | Climate policy analysis |
| RAND Europe | Policy research |

### Research Institutes (Applied, Not Purely Academic)

| Organization | Country |
|-------------|---------|
| Joint Research Centre (JRC) | EU (European Commission) |
| Fraunhofer IEG, ISE, IEE | Germany |
| DLR Institute of Networked Energy Systems | Germany |
| RISE Research Institutes of Sweden | Sweden |
| CSIR | South Africa |
| TERI | India |

### Regional Model Deployments

| Model | Region | Maintained By |
|-------|--------|---------------|
| PyPSA-Eur | Europe (full ENTSO-E area) | TU Berlin + community |
| PyPSA-USA | United States | Stanford + Simon Fraser University |
| PyPSA-GB | Great Britain | Academic |
| PyPSA-Earth | Global | Open Energy Transition |

## Distinguishing Production from Academic Use

**Strong evidence of production/operational use:**
- IEA: Published reports cite PyPSA as the modeling tool for official analyses
- ACER: Building a regulatory platform on PyPSA
- TransnetBW, APG: TSOs using PyPSA for grid planning decisions
- Shell, Saudi Aramco: Corporate energy transition planning

**Moderate evidence (consultancy/policy use, not academic papers):**
- Agora Energiewende, Ember, RMI: Policy recommendations based on PyPSA modeling
- d-fine, Energynautics: Client-facing consulting work

**Weaker evidence (listed but usage details unknown):**
- Several organizations are listed on the official users page without published details on their specific use cases

## Caveats

1. The official users page is self-reported and not independently verified.
2. "Use" may range from exploratory evaluation to production deployment. The distinction is not always clear from public information.
3. No evidence was found of PyPSA being used for real-time operational dispatch by an ISO or utility. Usage appears focused on planning studies, scenario analysis, and policy modeling.
4. No evidence of PyPSA being used for automated trading or real-time market operations.

## Assessment

PyPSA has strong operational adoption for energy system planning and policy analysis, with confirmed use by major international organizations (IEA, ACER, ENTSO-E) and energy companies (Shell, Saudi Aramco). Multiple TSOs use it for grid planning. However, usage is concentrated in the planning/policy domain rather than real-time operations or market dispatch. The project's institutional backing (TU Berlin, German Research Foundation) and the breadth of regional model deployments (PyPSA-Eur, PyPSA-USA, PyPSA-Earth) demonstrate production-grade maturity for its target use case.
