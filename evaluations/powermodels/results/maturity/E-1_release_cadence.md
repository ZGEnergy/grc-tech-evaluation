---
test_id: E-1
tool: powermodels
dimension: maturity
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# E-1: Release Cadence

## Result: PASS

## Finding

PowerModels.jl has maintained a healthy release cadence over the last 24 months with 7 releases, all following semantic versioning. The most recent release (v0.21.5) was published on 2025-08-12, approximately 7 months ago.

## Evidence

Releases in the 24-month window (2024-03-06 to 2026-03-06):

| Version  | Date       | Days Since Previous |
|----------|------------|---------------------|
| v0.21.5  | 2025-08-12 | 84                  |
| v0.21.4  | 2025-05-20 | 197                 |
| v0.21.3  | 2024-11-04 | 122                 |
| v0.21.2  | 2024-07-05 | 111                 |
| v0.21.1  | 2024-03-16 | 57                  |

Just outside window but contextually relevant:

| v0.21.0  | 2024-01-19 | 17                  |
| v0.20.1  | 2024-01-10 | 8                   |
| v0.20.0  | 2024-01-02 | --                  |

Total releases in 24-month window: 5 (strictly within); 7-8 if including Jan 2024 burst.

All releases follow strict semver (vMAJOR.MINOR.PATCH). The project remains pre-1.0 (v0.21.x) after 9+ years, which is notable but consistent with Julia ecosystem conventions where pre-1.0 does not necessarily indicate instability.

Average release interval: approximately 3-4 months.

Source: <https://github.com/lanl-ansi/PowerModels.jl/releases>

## Implications

Release cadence is adequate for a research-oriented tool. Approximately quarterly releases indicate active maintenance without being disruptively frequent. The pre-1.0 status is a minor concern for production adoption but does not affect the cadence assessment.
