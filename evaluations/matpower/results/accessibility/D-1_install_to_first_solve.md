---
test_id: D-1
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "6e8ee849"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-1: Install to First Solve

## Result: INFORMATIONAL

## Finding

MATPOWER installation requires 3 manual steps and encounters significant friction from a non-scriptable installer. Time from clean environment to first successful DCPF solve is approximately 2-3 minutes of human effort, with the majority spent diagnosing path configuration.

## Evidence

### Install Process

1. **Download:** `curl -L -o matpower8.1.zip <GitHub release URL>` -- straightforward, ~46 MB download
2. **Extract:** `unzip -q matpower8.1.zip` -- standard
3. **Path configuration:** This is where friction occurs

**setup.sh** (`evaluations/matpower/setup.sh`) automates steps 1-2 with SHA256 checksum verification. However, the checksum had to be computed manually -- MATPOWER does not publish checksums alongside releases.

### Path Configuration Friction

MATPOWER ships `install_matpower.m` which calls `input()` to prompt the user interactively for one of three path configuration options. This function is **unusable in batch mode** (Octave `--eval`, Docker, CI) because `input()` blocks on stdin.

The required manual path setup is 5 `addpath` calls:

```matlab
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
```

A user who only adds `lib/` and `data/` (the obvious directories) will encounter a cryptic error: `'have_feature' undefined`. The dependency on `mips/lib/` and `mp-opt-model/lib/` is not documented outside the interactive installer script. This is a trap for new users.

Source: `evaluations/matpower/notes/install-findings.md`

### First Solve

Once paths are configured, a first solve requires 3 lines:

```matlab
mpc = loadcase('case9');
results = runpf(mpc);
% results.success == 1
```

This is minimal and well-documented in the User's Manual Chapter 3.

### Issue Summary

| Issue | Severity | Description |
|-------|----------|-------------|
| Interactive installer | High | `install_matpower.m` blocks on `input()`, unusable in CI/Docker/batch |
| Hidden path dependencies | Medium | `mips/lib` and `mp-opt-model/lib` must be added but are not documented outside interactive installer |
| No package manager | Medium | No `pkg install`, no `apt`, no `pip` equivalent -- manual download and extract only |
| No published checksums | Low | SHA256 not published alongside GitHub release |

### Consumed Observations

- [api-friction: MATPOWER cannot ingest intermediate CSV tables](../observations/api-friction-fnm_ingestion-G-FNM-1_fnm_ingestion_gate.md) -- data ingestion limited to `.m`/`.mat`/PSS/E RAW formats
- [api-friction: No DataFrame or structured export](../observations/api-friction-extensibility-B-5_interoperability.md) -- results are bare numeric matrices

## Implications

The install-to-first-solve experience has moderate friction. The core API (`runpf`, `loadcase`) is simple and well-documented, but the packaging and path setup create unnecessary obstacles. Modern tools with package manager support (PyPSA via `pip`, PowerModels via Julia `Pkg`) have a significant advantage in onboarding speed and CI/CD integration.
