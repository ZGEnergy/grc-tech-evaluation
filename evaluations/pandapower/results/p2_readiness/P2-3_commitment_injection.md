---
test_id: P2-3
tool: pandapower
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "13cd0a8f"
---

# P2-3: Commitment Injection Workflow

## Question

Can you fix generator commitment (on/off) and then run economic dispatch?

## Finding

**Yes.** Although pandapower has no native SCUC solver (test A-5 confirmed this),
manual commitment injection is straightforward via the `in_service` column on
the `net.gen` DataFrame. Setting `in_service = False` fully removes the generator
from the OPF formulation.

### Workflow

```python
import pandapower as pp

# Set commitment vector (e.g., from external UC solver)
net.gen.at[1, 'in_service'] = False   # decommit gen 1
net.gen.at[0, 'in_service'] = True    # keep gen 0 online

# Run economic dispatch (OPF with fixed commitment)
pp.rundcopp(net)   # DC OPF
# or pp.runopp(net)  # AC OPF
```

### Test performed

Using the IEEE 9-bus case (`case9`) with 2 generators + 1 ext_grid (slack) and
existing polynomial costs:

| Scenario | Gen 0 (MW) | Gen 1 (MW) | Ext Grid (MW) | Cost (EUR) |
|----------|-----------|-----------|---------------|------------|
| All in service | 134.4 | 94.1 | 86.6 | 5216.0 |
| Gen 1 decommitted | 187.4 | 0.0 | 127.6 | 6388.9 |
| Gen 0 decommitted | 0.0 | 157.6 | 157.4 | 7197.4 |

Results confirm:

1. Decommitted generators produce exactly 0 MW and are excluded from dispatch.
2. Remaining generators and ext_grid re-dispatch optimally to meet load.
3. Cost increases as expected when cheaper generators are removed.

### API friction assessment

**Low friction.** The `in_service` boolean column is a standard pandapower pattern
used across all element types (gen, load, line, trafo, etc.). Key observations:

- **Direct DataFrame mutation**: no setter method needed — just assign to
  `net.gen.at[idx, 'in_service']`. This is idiomatic pandapower.
- **Batch operations**: commitment vectors can be applied in one line:
  `net.gen['in_service'] = [True, False, True, ...]`
- **No state leakage**: results for decommitted generators show 0.0 in all
  `res_gen` columns; no phantom power injection.
- **Reversible**: toggling `in_service` back to `True` fully restores the
  generator for subsequent solves.
- **Works with all solvers**: `runpp`, `rundcpp`, `runopp`, `rundcopp` all
  respect the `in_service` flag.

### Phase 2 integration pattern

For a SCUC-then-SCED pipeline:

1. Solve unit commitment externally (e.g., with a MIP solver via Pyomo or JuMP).
2. Map the binary commitment decision to pandapower's `in_service` column.
3. Run `runopp()` or `rundcopp()` for economic dispatch with fixed topology.

This is a clean separation of concerns and requires no pandapower extensions.
