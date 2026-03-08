# Probe Conventions

Spot-check probes are targeted test scripts that verify extraordinary claims from
evaluation results. They run in the devcontainer against the same tool environment
used in the original evaluation.

## Probe Principles

1. **Probes verify, they don't re-evaluate.** A probe checks a specific claim from a
   specific result file. It does not re-run the full test or re-grade the result.

2. **Frame results as "probe found X", not "original was wrong."** The probe may use
   different methodology, timing, or parameters than the original evaluation. Findings
   are additional data points, not corrections.

3. **Environment parity is mandatory.** Probes must use the same solver versions, tool
   versions, and network files as the original evaluation. Any discrepancy must be
   documented and the result flagged as potentially non-comparable.

## Probe Types

| Type | Purpose | Typical Script Pattern |
|------|---------|----------------------|
| `timing_verification` | Re-time a solve that was originally estimated or suspiciously fast/slow | Run solve N times, report mean/median/stddev wall-clock |
| `convergence_check` | Verify that a claimed-converged solve actually converges | Run solve, check objective value and constraint residuals |
| `formulation_audit` | Verify that claimed formulation features are actually active | Inspect model variables/constraints, check that UC constraints bind |
| `claim_verification` | General-purpose claim check | Depends on claim — may involve running code, checking output, etc. |

## Solver Version Pinning

Before running any probe:

1. **Read the tool's environment.** Check `evaluations/<tool>/pyproject.toml` (Python)
   or `evaluations/<tool>/Project.toml` (Julia) for pinned solver versions.
2. **Read the original result file.** Look for solver version in the Methodology or
   Evidence section.
3. **Verify installed version.** Run the appropriate check in the devcontainer:
   - Python: `.devcontainer/dc-exec -C /workspace/evaluations/<tool> uv run python -c "import highspy; print(highspy.__version__)"`
   - Julia: `.devcontainer/dc-exec -C /workspace/evaluations/<tool> julia --project=. -e 'using Pkg; Pkg.status("HiGHS")'`
4. **Document any discrepancy.** If the installed version differs from what the original
   evaluation used, note it in the probe result and flag the result as `inconclusive`
   with reason "solver version mismatch."

## Timeout and Resource Limits

- **Default timeout:** 300 seconds (5 minutes) per probe
- **Configurable:** The orchestrator can override per-probe via `timeout_seconds`
- **Implementation:** Use `timeout` command wrapper:

  ```bash
  .devcontainer/dc-exec timeout 300 <command>
  ```

- **Timeout handling:** If the probe times out, classify as `inconclusive` with reason
  "timeout after N seconds." Do not retry automatically.

## Probe Result File

Each probe produces a structured result file at
`{{output_dir}}/<probe_id>.md`:

```yaml
---
probe_id: <id>
tool: <tool_name>
source_test: <test_id>
probe_type: <type>
classification: probe_bug|claim_debunked|claim_supported|inconclusive
reason: <1-line explanation of classification>
solver_version: <version used>
solver_version_match: true|false
timeout_seconds: <configured timeout>
wall_clock_seconds: <actual runtime>
timestamp: <ISO 8601>
---
```

```markdown
# Probe {{probe_id}}: {{claim summary}}

## Original Claim

<Quote or paraphrase from the original result file, with path.>

## Probe Methodology

<What the probe did. Include the exact script or commands run.>

## Probe Results

<Raw output, timing data, convergence metrics, etc.>

## Analysis

<Interpretation of results relative to the original claim.
What does this tell us? Does it support or contradict the claim?>

## Classification Rationale

<Why this probe was classified as {{classification}}.
For claim_debunked: what specific evidence contradicts the claim?
For claim_supported: what evidence corroborates?
For inconclusive: what prevented a definitive answer?
For probe_bug: what went wrong with the probe itself?>
```

## Classification Decision Tree

```
Probe script errored or produced no output?
  → probe_bug

Solver version mismatch AND results differ from original?
  → inconclusive (version mismatch may explain difference)

Probe results clearly contradict the original claim?
  (e.g., timing 10x slower than claimed, model has no UC constraints,
   solve doesn't converge)
  → claim_debunked

Probe results clearly support the original claim?
  (e.g., timing within 2x of claimed, constraints verified active,
   convergence confirmed)
  → claim_supported

Results ambiguous or partially support/contradict?
  → inconclusive (explain what's ambiguous)
```

## Sequential Execution Rule

Probes for the **same tool** must run sequentially. The devcontainer has a single
environment per tool, and concurrent probes could interfere (shared solver state,
file locks, memory pressure).

Probes for **different tools** can run in parallel — they use independent environments.
