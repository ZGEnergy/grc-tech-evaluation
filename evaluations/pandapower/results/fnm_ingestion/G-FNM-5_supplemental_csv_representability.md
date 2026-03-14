---
test_id: G-FNM-5
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "0bf44f12"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 196
solver: null
timestamp: 2026-03-13T12:00:00Z
---

# G-FNM-5: Supplemental CSV Representability Assessment

## Result: INFORMATIONAL

pandapower achieves 34% native, 23% extension, and 43% external field
coverage across all 44 supplemental CSV fields. This places pandapower
at the lower end of native coverage among the six evaluated tools, tied
with PyPSA. The high external percentage reflects pandapower's scope as
a power flow tool with no market-layer abstractions (hubs, distribution
factors) or operational scheduling concepts (outages, contingency
definitions).

## Per-CSV Representability

### LINE_AND_TRANSFORMER.csv (10 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| FROM_BUS | N | `line.from_bus` / `trafo.hv_bus` |
| TO_BUS | N | `line.to_bus` / `trafo.lv_bus` |
| CKT | E | Custom column on line/trafo DataFrame |
| ELEMENT_TYPE | E | Custom column on line/trafo DataFrame |
| RATE_A | N | `line.max_i_ka` (converted from MVA via voltage); `trafo.sn_mva` |
| RATE_B | E | Custom column on line/trafo DataFrame |
| RATE_C | E | Custom column on line/trafo DataFrame |
| RATE_D | E | Custom column on line/trafo DataFrame |
| STATUS | N | `line.in_service` / `trafo.in_service` (bool) |
| EFFECTIVE_DATE | E | Custom column on line/trafo DataFrame |

**Summary:** 4 N (40%), 6 E (60%), 0 X (0%)

pandapower stores only one thermal rating tier natively (RATE_A). The
additional tiers (RATE_B/C/D) can be stored as custom DataFrame columns
but are not consumed by any built-in analysis function. The RATE_A
representation uses current (kA) rather than power (MVA), requiring a
voltage-level conversion at ingestion time.

### CONTINGENCY.csv (6 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| CONTINGENCY_NAME | X | No contingency definition model |
| ELEMENT_TYPE | X | No contingency definition model |
| ELEMENT_FROM_BUS | N | `line.from_bus` / `trafo.hv_bus` |
| ELEMENT_TO_BUS | N | `line.to_bus` / `trafo.lv_bus` |
| ELEMENT_CKT | E | Custom column on element DataFrames |
| ELEMENT_BUS | N | `gen.bus` |

**Summary:** 3 N (50%), 1 E (17%), 2 X (33%)

pandapower's `run_contingency()` and `run_contingency_ls2g()` functions
perform N-1 analysis but accept element indices as input, not named
contingency objects. There is no native data structure for contingency
definitions. Contingency metadata (names, element types) must be
maintained in an external DataFrame and mapped to element indices
before each analysis run.

### INTERFACE.csv (5 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| INTERFACE_ID | X | No interface/flowgate model |
| INTERFACE_NAME | X | No interface/flowgate model |
| NORMAL_LIMIT_MW | X | No interface/flowgate model |
| EMERGENCY_LIMIT_MW | X | No interface/flowgate model |
| DIRECTION | X | No interface/flowgate model |

**Summary:** 0 N (0%), 0 E (0%), 5 X (100%)

pandapower has no native concept of a transmission interface or flowgate.
An interface is a named group of branches with aggregate flow limits and
direction coefficients — this concept has no structural analog in
pandapower's data model. Interface flow monitoring would require external
post-processing: compute branch flows, aggregate by interface definition
from an external data structure, and compare against limits. Interface
flow limits cannot be enforced within pandapower's native OPF formulation.

### INTERFACE_ELEMENT.csv (6 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| INTERFACE_ID | X | No interface model |
| FROM_BUS | N | `line.from_bus` |
| TO_BUS | N | `line.to_bus` |
| CKT | E | Custom column on line DataFrame |
| DIRECTION_COEFF | X | No interface model |
| WEIGHT_FACTOR | X | No interface model |

**Summary:** 2 N (33%), 1 E (17%), 3 X (50%)

The interface element fields that map to physical branch identifiers
(FROM_BUS, TO_BUS) are natively representable, but the interface-specific
fields (INTERFACE_ID, DIRECTION_COEFF, WEIGHT_FACTOR) have no home in
pandapower.

### GEN_DISTRIBUTION_FACTOR.csv (5 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| GEN_BUS | N | `gen.bus` |
| GEN_ID | E | Custom column on gen DataFrame |
| HUB_NAME | X | No trading hub / distribution factor concept |
| PARTICIPATION_FACTOR | X | No hub-based allocation model |
| GEN_NAME | N | `gen.name` |

**Summary:** 2 N (40%), 1 E (20%), 2 X (40%)

Generator distribution factors are a market settlement concept with no
analog in pandapower's power flow domain. The physical generator
identifiers (bus, name) are natively representable, but hub association
and participation factors must be maintained externally.

### TRADING_HUB.csv (4 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| HUB_NAME | X | No hub model |
| BUS_NUMBER | N | Bus index (integer bus number) |
| DISTRIBUTION_FACTOR | X | No hub model |
| HUB_TYPE | X | No hub model |

**Summary:** 1 N (25%), 0 E (0%), 3 X (75%)

Trading hubs are a market-layer abstraction entirely outside pandapower's
domain. Only the physical bus number is natively representable. Hub names,
distribution factors, and hub types must all be maintained in external
data structures. Hub-level LMP computation (PTDF-weighted bus LMP
averaging) is feasible as external post-processing but requires custom
code and external hub definition storage.

### OUTAGE.csv (8 fields)

| Field | Class | pandapower Mechanism |
|-------|-------|---------------------|
| ELEMENT_TYPE | X | No outage schedule model |
| ELEMENT_FROM_BUS | N | `line.from_bus` / `trafo.hv_bus` |
| ELEMENT_TO_BUS | N | `line.to_bus` / `trafo.lv_bus` |
| ELEMENT_CKT | E | Custom column on element DataFrames |
| ELEMENT_BUS | N | `gen.bus` |
| OUTAGE_START | X | No temporal outage model |
| OUTAGE_END | X | No temporal outage model |
| OUTAGE_TYPE | X | No outage classification model |

**Summary:** 3 N (38%), 1 E (12%), 4 X (50%)

pandapower can set elements out of service (`in_service=False`) but has
no temporal outage scheduling. Outage application across time periods
requires external scripting: read outage definitions from an external
DataFrame, modify `in_service` flags per time step, and solve each
snapshot independently. The `timeseries` module can automate the solve
loop via controllers, but outage definitions themselves remain external.

## Cross-CSV Summary

| CSV | Fields | N | E | X | N% | E% | X% |
|-----|--------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER | 10 | 4 | 6 | 0 | 40% | 60% | 0% |
| CONTINGENCY | 6 | 3 | 1 | 2 | 50% | 17% | 33% |
| INTERFACE | 5 | 0 | 0 | 5 | 0% | 0% | 100% |
| INTERFACE_ELEMENT | 6 | 2 | 1 | 3 | 33% | 17% | 50% |
| GEN_DISTRIBUTION_FACTOR | 5 | 2 | 1 | 2 | 40% | 20% | 40% |
| TRADING_HUB | 4 | 1 | 0 | 3 | 25% | 0% | 75% |
| OUTAGE | 8 | 3 | 1 | 4 | 38% | 12% | 50% |
| **Totals** | **44** | **15** | **10** | **19** | **34%** | **23%** | **43%** |

## Comparison Against Analytical Reference

The field-level classifications above match the analytical reference
in `data/fnm/docs/supplemental-csv-representability.md` exactly for
pandapower. The reference reports 34% native, 23% extension, 43%
external — identical to the values computed here.

## Extension Mechanism: Custom DataFrame Columns

All E-classified fields use the same extension mechanism: adding custom
columns to pandapower's element DataFrames. For example:

```python
# Store RATE_B as a custom column on the line DataFrame
net.line["rate_b_mva"] = rate_b_values

# Store CKT as a custom column on the line DataFrame
net.line["ckt"] = ckt_values
```

Custom columns are preserved through JSON serialization (`pp.to_json` /
`pp.from_json`) and survive copy operations (`net.deepcopy()`). They
are not consumed by any built-in analysis function — custom
post-processing code is required to use them.

This extension mechanism is documented and stable. It is the standard
pattern for user-defined data in pandapower.

## Market Solution Fidelity Summary

| Market Concept | Classification | Notes |
|----------------|----------------|-------|
| N-1/N-2 contingency enforcement | achievable | `run_contingency()` supports N-1 sweeps with DCPF/ACPF. N-2 requires custom scripting. No SCOPF (no contingency constraints in OPF). |
| Interface flow limits | complex | No native interface model. Requires external definition storage, post-solve aggregation, and manual limit checking. Cannot enforce in OPF. |
| Aggregate hub pricing (PTDF-weighted LMP) | complex | No hub model. Requires external hub definitions, OPF LMP extraction, and external PTDF-weighted averaging. |
| Outage scheduling | achievable | `in_service=False` for point-in-time outages. Temporal scheduling via external scripting + `timeseries` module controllers. |

### Justification for "complex" Classifications

**Interface flow limits:** The absence of any native interface concept
means the entire workflow — defining interfaces, computing aggregate
flows, checking limits, enforcing limits in dispatch — must be
implemented externally. For monitoring-only use cases, this is
"achievable" (post-processing branch flows). For enforcement within
dispatch optimization, it requires either the PandaModels.jl Julia
bridge (which supports custom constraints via JuMP) or a fully external
optimization model. The monitoring case is achievable; the enforcement
case is complex, pushing the overall classification to "complex."

**Aggregate hub pricing:** Hub LMP computation is feasible as
post-processing: extract bus LMPs from OPF, apply PTDF-weighted
averaging using external hub definitions. However, the entire hub
concept — defining hubs, associating buses with distribution factors,
computing hub prices — sits outside pandapower. The computation itself
is straightforward; the complexity lies in maintaining the parallel
data structures and ensuring consistency between bus indices in
pandapower and bus numbers in the hub definition.

## Test Script

**Path:** `evaluations/pandapower/tests/fnm_ingestion/test_g_fnm_5_supplemental_csv_representability.py`
