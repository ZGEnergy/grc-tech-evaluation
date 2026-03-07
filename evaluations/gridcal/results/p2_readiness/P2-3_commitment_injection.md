---
test_id: P2-3
tool: gridcal
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# P2-3: Commitment Injection (UC -> ED -> AC PF Pipeline)

## Result: FAIL

## Pipeline Assessment

The target pipeline is: SCUC (commit) -> DCOPF/ED (dispatch) -> AC PF (feasibility check).

### Step 1: SCUC -- FAIL

A-5 demonstrated that:

- **Snapshot UC** works for a single time step (`OpfDispatchMode.UnitCommitment`) but has no inter-temporal coupling.
- **Time-series UC** crashes with `ValueError: 0 is not a valid TapPhaseControl` on case39.m.
- **Inter-temporal constraints** (ramp rates, min up/down time, startup costs) exist as generator attributes and OPF options but are reported non-functional (GitHub issue #397) and cannot be tested due to the time-series crash.

No 24-hour commitment schedule was produced.

### Step 2: Commitment Injection into ED -- NOT POSSIBLE

GridCal does not provide an API to:

- Pass a fixed binary commitment vector to the OPF solver
- Lock specific generators on/off for an ED solve
- Solve ED-only with a pre-determined commitment schedule

The `must_run` generator attribute is the closest mechanism, but it only prevents decommitment -- it cannot express a time-indexed commitment schedule.

**Workaround attempted:** Setting `gen.Pmin = 0` and `gen.Pmax = 0` for decommitted generators, then running DC OPF. This produces a dispatch but is fragile -- it permanently modifies generator limits and does not preserve the UC/ED separation.

### Step 3: AC PF Feasibility Check -- PASS (independent of UC/ED)

A-4 demonstrated that the OPF-to-PF pipeline works for a single snapshot:

```python
# After DC OPF, inject dispatch into generators and run AC PF
for i, gen in enumerate(grid.generators):
    gen.P = opf_results.generator_power[i]
results = vge.power_flow(grid)
```

This step works independently of how the dispatch was obtained.

## Capability Per Step

| Step | Capability | Effort Level | API Friction |
|------|-----------|--------------|--------------|
| SCUC (24h) | Blocked | N/A | Time-series OPF crash, constraints not enforced |
| Commitment injection | Not possible | N/A | No API for fixing commitment schedule |
| ED with fixed commitment | Workaround only | High | Must manually zero out Pmin/Pmax |
| AC PF feasibility | Yes | Low | Clean API via generator P injection |

## Overall Assessment

The UC -> ED -> AC PF pipeline is **not functional** in GridCal. The blocking issues are:

1. Time-series OPF crash prevents multi-period UC.
2. No API for commitment injection into ED.
3. UC constraint enforcement is reportedly broken (GitHub #397).

Step 3 (AC PF check) works in isolation, but steps 1 and 2 are blocked.
