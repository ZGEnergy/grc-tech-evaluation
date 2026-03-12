---
test_id: D-5
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v9
skill_version: v1
test_hash: b33f27ef
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# D-5: Code Volume (code_volume)

## Result: INFORMATIONAL

## Finding

PyPSA test scripts range from 114 to 259 LOC across the five sampled tests. The contingency sweep (A-7) required the most code at 259 LOC, driven by the `lpf_contingency` bug workaround (BODF-based N-1 sweep) and N-2 manual loop. OPF tests (A-3, A-10) required 200–239 LOC due to manual cost assignment and shadow price extraction workarounds.

## Evidence

**LOC summary from existing result files:**

| Test | Description | LOC | Notes |
|------|-------------|-----|-------|
| A-1 | DC Power Flow (dcpf) | 114 | Baseline; simple pipeline. Most compact. |
| A-2 | AC Power Flow (acpf) | 185 | Higher due to convergence verification code |
| A-3 | DC OPF with shadow prices | 209 | Fragile shadow price workaround adds ~30 LOC |
| A-7 | N-M Contingency Sweep | 259 | Highest; BODF workaround + N-2 manual loop |
| A-10 | Lossy DC OPF + LMP decomp | 239 | LMP decomposition logic adds volume |

**Relative comparison:**
- Median: 209 LOC (A-3)
- Range: 145 LOC (114–259)
- A-7 is 2.3× larger than A-1 — disproportionate due to bug workaround

**Factors driving higher LOC:**
1. **No native MATPOWER reader:** Each script includes boilerplate for `CaseFrames` → ppc dict construction (~15 LOC).
2. **Shadow price access (A-3, A-10):** The `n.model.constraints[...]` fragile workaround requires ~20 LOC of constraint introspection code that would be replaced by `n.lines_t.mu_upper` if the API worked as documented.
3. **N-1 contingency workaround (A-7):** BODF-based contingency sweep requires explicit `sub_network.calculate_PTDF()` + `calculate_BODF()` calls and manual flow computation (~50 LOC) that `n.lpf_contingency()` would handle in 5 LOC.
4. **Convergence verification (A-2):** The non-obvious `pf_result["n_iter"].values[0, 0]` accessor pattern adds verbose extraction code.

**Benchmark context:** For a DCPF test, 114 LOC is moderate. Simple PyPSA DCPF can be written in ~20 LOC (see `verify_install.py`); the test scripts include comprehensive output extraction, assertions, and logging that inflate the count appropriately.

## Implications

Code volume is consistent with a capable but slightly verbose API. The two primary LOC drivers are addressable: (a) fixing `n.lines_t.mu_upper` would eliminate the shadow price workaround, and (b) fixing the `lpf_contingency` Python 3.12 bug would eliminate the BODF boilerplate. The underlying PyPSA API is concise when working; workarounds dominate the excess volume.
