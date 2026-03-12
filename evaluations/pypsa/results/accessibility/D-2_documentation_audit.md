---
test_id: D-2
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 52df27b8
status: qualified_pass
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

# D-2: Documentation Audit (documentation_audit)

## Result: QUALIFIED PASS

## Finding

PyPSA documentation (https://pypsa.readthedocs.io/) covers the standard workflow well for 9 of 12 test types. Three test types have significant documentation gaps: contingency sweep (`lpf_contingency` bug undocumented), shadow price access (fragile workaround undocumented), and lossy OPF (deprecated `transmission_losses` syntax with poor migration guidance).

## Evidence

**Documentation coverage by Suite A test type:**

| Test | API Entry Point | Documented? | Notes |
|------|----------------|-------------|-------|
| A-1 DCPF | `n.lpf()` | Yes | Examples in "Linear Power Flow" docs; `.values` ppc requirement NOT documented |
| A-2 ACPF | `n.pf()` | Yes | Newton-Raphson docs present; convergence dict structure only discoverable from source |
| A-3 DC OPF | `n.optimize()` + HiGHS | Yes | Optimization tutorial present; `mu_upper`/`mu_lower` emptiness NOT documented |
| A-4 AC feasibility | `n.optimize.optimize_and_run_non_linear_powerflow()` | Partial | Function exists in API ref; Ipopt dependency for AC OPF not prominently flagged |
| A-5 SCUC | Committable generators in `n.optimize()` | Yes | UC tutorial with `committable=True`, startup/shutdown costs documented |
| A-6 SCED | Multi-period `n.optimize()` | Yes | Two-stage dispatch mentioned; not a dedicated SCED tutorial |
| A-7 Contingency sweep | `n.lpf_contingency()` | Yes/Broken | API reference documents the function; **BUG in v1.1.2 not documented anywhere** |
| A-8 Stochastic | Multi-period with scenario snapshots | Partial | Multi-period OPF documented; stochastic scenario construction not shown in docs |
| A-9 SCOPF | `n.optimize_security_constrained()` | Yes | Dedicated docs section present |
| A-10 Lossy OPF | `transmission_losses` param | Partial | Dict syntax `{'mode': 'tangents', 'segments': 3}` poorly documented; deprecation notice vague |
| A-11 Distributed slack | `slack_weightings` param in `n.optimize()` | Yes | Documented with examples |
| A-12 Multi-period BESS | `StorageUnit` + time series snapshots | Yes | StorageUnit tutorial with `cyclic_state_of_charge`, charging/discharging efficiency documented |

**Key documentation gaps (from consumed observations):**

1. **`n.lpf_contingency()` bug (A-7):** The function is documented with correct signature and description, but the Python 3.12 compatibility bug (`pd.Index` not recognized as `collections.abc.Sequence`) is not mentioned in any changelog, GitHub issue tracker prominent warning, or docs. A user following the docs would hit this bug with no guidance.

2. **Shadow prices / `mu_upper` empty (A-3):** The PyPSA docs show `n.buses_t.marginal_price` for LMPs but do not document that `n.lines_t.mu_upper` is empty after `n.optimize()`. The workaround via `n.model.constraints["Line-fix-s-upper"].dual` requires reading linopy source code.

3. **`transmission_losses` deprecation (A-10):** The v1.1.2 docs mention the dict syntax but the deprecation warning in the code (`FutureWarning`) is more informative than the docs themselves. No migration guide is present.

4. **PYPOWER ppc `.values` requirement (A-1):** `import_from_pypower_ppc` documentation does not state that array fields must be numpy arrays (not DataFrames). This is a silent failure — DataFrames cause wrong results, not an error.

**Strengths:**
- Comprehensive "Components" reference docs for all PyPSA component types
- Good optimization tutorial with worked examples (AC vs DC formulations)
- API reference auto-generated from docstrings is mostly complete
- Official examples on GitHub cover most standard use cases
- `StorageUnit` multi-period BESS (A-12) is well-documented with examples

## Implications

Documentation is B-level: strong fundamentals with notable gaps on advanced features and compatibility issues. The undocumented `lpf_contingency` bug is the most significant gap — it causes a test to fail with no documented workaround. Shadow price access and `transmission_losses` deprecation are secondary gaps. A new user could achieve ~75% of the Suite A tests from docs alone.
