---
test_id: B-5
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "3d423124"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.1184
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 176
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-5: Export DCPF results to DataFrame and write to CSV

## Result: QUALIFIED PASS

## Approach

Solved DCPF via `rundcpf()`, then exported results to three CSV files (bus, branch, generator) using Octave's `csvwrite()`/`dlmwrite()` functions.

**Minimal export (no column headers):**
```matlab
csvwrite('bus.csv', [results.bus(:,BUS_I), results.bus(:,VA), results.bus(:,PD)]);
```
This is 3 lines of code (one per table) — fewer than 5 lines.

**With column headers** (production-quality): requires `fopen/fprintf/fclose/dlmwrite` pattern — 4 lines per table (12 lines total).

## Output

| File | Rows | Size |
|------|------|------|
| `B-5_bus_results.csv` | 39 | 1,583 bytes |
| `B-5_branch_results.csv` | 46 | 2,796 bytes |
| `B-5_gen_results.csv` | 10 | 323 bytes |

All files verified by readback (`dlmread()`) — row counts match expected values.

### Bus CSV columns
`bus_id, voltage_angle_deg, P_load_MW, Q_load_MW`

### Branch CSV columns
`from_bus, to_bus, PF_MW, QF_MVAr, PT_MW, QT_MVAr`

### Generator CSV columns
`gen_bus, PG_MW, QG_MVAr`

## Workarounds

- **What:** Octave's `csvwrite()` cannot write column headers (text). Writing headers requires `fopen`/`fprintf`/`fclose` followed by `dlmwrite` with `'-append'` — 4 lines per table instead of 1.
- **Why:** Octave has no DataFrame concept. Results are numeric matrices with no attached metadata.
- **Durability:** stable — `csvwrite()` and `dlmwrite()` are standard Octave/MATLAB functions.
- **Grade impact:** The minimal export (3 lines, no headers) meets the "<5 lines" criterion. With headers, it's 12 lines — still straightforward but not trivial.

## Timing

- **Wall-clock:** 0.1184 s (including DCPF solve + CSV write + readback verification)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b5_interoperability.m`
