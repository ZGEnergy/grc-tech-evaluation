---
test_id: E-7
tool: pypsa
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-7: Operational Adoption (Utility/ISO/Government)

## Finding

PyPSA is widely adopted for energy system planning and policy analysis by TSOs, government agencies, and energy companies. However, no evidence of ISO/RTO operational (real-time) deployment exists. Adoption is concentrated in planning/research/policy use cases.

## Evidence

**Transmission System Operators (TSOs):**
- **TransnetBW** (Germany): Grid requirements study for 90% CO2 reduction
- **ENTSO-E**: Open-source tool development for scenario building
- **TenneT** (Netherlands): Ancillary services acquisition research
- **Austrian Power Grid (APG)**: Austrian energy system vision to 2050
- **AGGM** (Austrian gas TSO): Sector-coupled energy model
- **ISA** (South America): Colombian power system modeling
- **ONTRAS** (Germany, gas TSO): Energy system decarbonization

**Government/Regulatory Agencies:**
- **IEA**: Global Energy and Climate Model; seasonal variability studies
- **ACER** (EU regulator): EU-wide flexibility assessment
- **Canada Energy Regulator (CER)**: Canada's Energy Future 2023
- **GIZ** (Germany): Renewable integration studies (Vietnam, Thailand, Indonesia, Brazil)
- **JRC** (EU Commission): METIS/PRIMES scenario conversion

**Energy Companies:**
- **Saudi Aramco**: Renewables integration assessment
- **Shell**: European electricity market simulations
- **Serentica** (India IPP): Round-the-clock PPA assessment
- **TEPSCO** (Tokyo Electric Power Services): Engineering and energy planning

**Research Institutes:**
- **TERI** (India), **CSIR** (South Africa), **DLR**, **Fraunhofer ISE/IEE/IEG/ISI**, **RMI** (USA), **RAND Europe**, and many more

**Universities:** 27+ listed including Stanford, Oxford, DTU, Kyoto, Korea University

**Notable absences:**
- No evidence of use in ISO/RTO real-time operations (ERCOT, PJM, MISO, CAISO, etc.)
- No evidence of use in real-time market clearing or operational dispatch
- All identified uses are planning, policy, research, or offline analysis

Source: `docs/home/users.md` in PyPSA repository (<https://github.com/PyPSA/PyPSA>)

## Implications

PyPSA has exceptionally broad adoption in the energy planning/policy ecosystem, including multiple TSOs and government agencies. The absence of ISO/RTO operational deployment is expected -- PyPSA is a planning tool, not a real-time operations platform. For this evaluation's context (planning and analysis use case), the adoption evidence is strong. Qualified pass because adoption is planning-focused rather than operational.
