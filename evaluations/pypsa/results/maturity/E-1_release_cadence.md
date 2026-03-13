---
test_id: E-1
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 3684d0d2
status: pass
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

# E-1: Release Cadence (release_cadence)

## Result: PASS

## Finding

PyPSA shows an extremely active release cadence: 11 releases in the 5 months from October 2025 to February 2026, following the major v1.0.0 rewrite. Semver compliance is observed. The project is in an active stabilization phase post-v1.0.

## Evidence

**PyPI release history** (https://pypi.org/project/pypsa/#history):
- Latest: v1.1.2 (2026-02-23)
- v1.1.1 (2026-02-xx)
- v1.1.0 (2026-01-xx)
- v1.0.x series: multiple patch releases (Oct–Dec 2025)
- **11 releases in Oct 2025 – Feb 2026** (5-month window)

**Last 24 months release count:**
- Pre-v1.0 (2024–early 2025): consistent minor/patch releases (approximately monthly)
- Post-v1.0 (Oct 2025+): accelerated release cadence (~2 releases/month)
- Estimated 24-month total: ~20+ releases

**Semver compliance:**
- v1.0.0 was the major API rewrite (backward-incompatible changes documented in migration guide)
- v1.1.x series: new features with backward compatibility
- v1.x.y: bug fixes only
- Semver followed correctly; deprecation warnings used for breaking changes (e.g., `transmission_losses` integer form)

**Date of last release:** 2026-02-23 (v1.1.2) — 16 days before this evaluation (2026-03-11).

**Post-v1.0 release pattern:**
The high release frequency in the v1.0.x/v1.1.x period reflects active bug fixing and feature refinement following the major rewrite. This is expected and healthy — rapid iteration post-major-version is normal.

**Known bugs present in v1.1.2:** The `lpf_contingency` Python 3.12 bug (#A-7) and `n.lines_t.mu_upper` emptiness (#A-3) have not been addressed in the 11 post-v1.0 releases, suggesting either they are not yet in the issue tracker as high-priority items or are backlogged.

## Implications

Release cadence is excellent — well above the threshold for a healthy open-source project. The post-v1.0 acceleration demonstrates active maintenance and a responsive team. The remaining known bugs (lpf_contingency, mu_upper) are concerning given the high release frequency — they appear to be known but not yet prioritized. Overall grade: A-level release cadence.
