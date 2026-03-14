---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-2
tool: powermodels
severity: high
timestamp: "2026-03-13T23:15:00Z"
---

# Observation: MATPOWER PPC format loses 92% of ACPF-critical fields

## Finding

PowerModels' MATPOWER fallback ingestion path preserves all 19 DCPF-critical fields but
only 19 of 237 ACPF-critical fields (8.0%). The MATPOWER PPC format cannot represent 10 of
the 17 intermediate schema record types (HVDC, VSC DC, FACTS, impedance correction,
multi-terminal DC, multi-section line, switched shunt discrete steps, area interchange,
zone, and owner tables).

## Context

G-FNM-2 audited field coverage after loading the MATPOWER fallback case
(`fnm_main_island.m`) via `PowerModels.parse_file`. The MATPOWER PPC format flattens
transformer data into the branch table, losing 42 of 44 ACPF-critical transformer fields
(control modes, tap limits, magnetizing admittance, winding I/O codes, all winding 2/3
details). ZIP load components (IP, IQ, YP, YQ) and generator remote regulation bus (IREG)
are also lost.

## Implications

For G-FNM-4 (ACPF convergence verification), the absence of transformer tap control
parameters, switched shunt discrete steps, and ZIP load models means the ACPF solution
will differ from a full PSS/E model solution. The tool cannot reproduce the original PSS/E
solved case voltages at buses where these missing fields would affect the solution.

For Expressiveness grading, the MATPOWER-only ingestion path is a structural limitation
that caps the tool's FNM fidelity at DCPF-level accuracy. Full ACPF fidelity would
require either native PSS/E v31 parsing (currently broken) or a user-written CSV-to-JSON
converter that maps all 17 intermediate tables to PowerModels' internal format.
