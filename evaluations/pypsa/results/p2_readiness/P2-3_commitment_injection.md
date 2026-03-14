---
test_id: P2-3
tool: pypsa
dimension: p2_readiness
network: TINY
status: informational
workaround_class: null
timestamp: 2026-03-13T18:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 4a4fe24e
---

# P2-3: Commitment Injection Workflow

## Result: INFORMATIONAL — Capable with moderate friction

## Capability Assessment

The commitment injection workflow has three steps:

1. **External UC produces commitment schedule** — Capable, no friction
2. **Inject commitment into PyPSA** — Capable, moderate friction (manual bound manipulation)
3. **Solve ED with fixed commitment** — Capable, low friction

### Step 1: External UC Produces Commitment Schedule

**Capability: Full. Effort: None.**

Any external system (in-house MILP solver, commercial UC engine, manual schedule)
can produce a commitment schedule as a time-indexed binary matrix: generators x
hours, with 1 = committed and 0 = decommitted. PyPSA imposes no constraints on
the source of this schedule.

The A-5 test demonstrated that PyPSA's own UC produces the commitment schedule
as `n.generators_t.status`, a pandas DataFrame with binary (0/1) values per
generator per hour. This is directly extractable and serializable (CSV, JSON,
pickle).

### Step 2: Inject Commitment into PyPSA

**Capability: Full. Effort: Moderate — requires manual bound manipulation.**

PyPSA has no `fix_commitment()` or `inject_commitment_schedule()` convenience
method. The A-6 evaluation confirmed that injecting a commitment schedule
requires manually translating binary commitment decisions into time-varying
generator bounds:

```python
# For each generator g and each hour t:
if commitment_schedule[t, g] == 1:  # committed
    n.generators_t.p_min_pu.loc[t, g] = 0.3   # min stable generation
    n.generators_t.p_max_pu.loc[t, g] = 1.0   # full capacity available
else:  # decommitted
    n.generators_t.p_min_pu.loc[t, g] = 0.0   # zero output
    n.generators_t.p_max_pu.loc[t, g] = 0.0   # zero output
```

Additionally, `committable` must be set to `False` on all generators to prevent
PyPSA from introducing its own binary commitment variables.

This is approximately 10–15 lines of setup code. The API elements used
(`generators_t.p_min_pu`, `generators_t.p_max_pu`, `committable` attribute)
are all documented public API and have been stable across PyPSA 1.0.x–1.1.x.

**Friction sources:**

- No dedicated method for commitment injection — user must understand the
  internal relationship between `committable`, `p_min_pu`, `p_max_pu`, and
  the commitment binary variable.
- The min stable generation level (`p_min_pu` when committed) must be specified
  by the user; it is not automatically inherited from the generator's UC
  parameters.
- If the external commitment schedule violates min up/down time constraints,
  PyPSA will not warn — it simply enforces the bounds as given. Feasibility
  checking of the injected schedule is the user's responsibility.

### Step 3: Solve ED with Fixed Commitment

**Capability: Full. Effort: Low.**

Once bounds are set, `n.optimize(solver_name='highs')` solves a pure LP
(no binary variables). The A-6 test confirmed:

- ED solves in ~0.5s on the TINY network (39 buses, 10 generators, 24 hours)
- 0 binary variables in the ED formulation (pure LP confirmed)
- Ramp constraints (`ramp_limit_up`, `ramp_limit_down`) are independently
  enforced in the ED stage — they do not require the UC formulation to be active
- Dispatch is extractable from `n.generators_t.p`
- LMPs are available from `n.buses_t.marginal_price`

## Per-Step Summary

| Step | Capability | Effort | API Friction |
|------|-----------|--------|-------------|
| 1. External UC schedule | Full | None | None — any format works |
| 2. Inject commitment | Full | Moderate | No convenience method; manual bound manipulation via `generators_t.p_min_pu`/`p_max_pu` (~15 LOC) |
| 3. Solve ED | Full | Low | Standard `n.optimize()` call; ramp constraints preserved |

## Overall Assessment

The commitment injection workflow is fully achievable in PyPSA but requires
moderate user effort due to the absence of a dedicated commitment injection API.
The A-6 evaluation classified the workaround as **stable** (uses only documented
public API). The main friction point is that the user must manually translate
between the commitment domain (binary on/off) and the dispatch domain
(continuous bounds on p_min/p_max), which is conceptually straightforward but
error-prone without a helper function.

A `fix_commitment(schedule)` convenience method would reduce the injection step
to a single call. PyPSA issue #1281 ("Approximate MILP UC prices with
optimize_and_resolve_fixed_unit_commitment()") suggests the developers are
aware of this workflow but have not yet shipped a public API for it.

## Sources

1. A-5 evaluation result — SCUC on TINY, commitment schedule extraction
2. A-6 evaluation result — SCED with fixed commitment, two-stage workflow
3. A-6 test script (`tests/expressiveness/test_a6_sced_tiny.py`) — implementation details
4. PyPSA issue #1281 — optimize_and_resolve_fixed_unit_commitment (open)
5. PyPSA v1.1.2 API: `generators_t.p_min_pu`, `generators_t.p_max_pu`, `committable`
