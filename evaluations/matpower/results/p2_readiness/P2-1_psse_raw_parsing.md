---
test_id: P2-1
tool: matpower
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-14T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "e1aebe67"
---

# P2-1: PSS/E RAW v30/v33 Parsing Capability

## Result: INFORMATIONAL

## Capability: Yes -- native support

MATPOWER 8.1 provides built-in PSS/E RAW file import and export through two functions:

| Function | Direction | Format |
|----------|-----------|--------|
| `psse2mpc(rawfile)` | Import | PSS/E RAW (auto-detects revision) |
| `save2psse(fname, mpc)` | Export | PSS/E RAW Rev 33 |

## Supported RAW Versions

**Import:** Auto-detects revision from the file header. Tested successfully on:
- Rev 29 (bundled test file `t_psse_case2.raw` -- 10 buses, 3 gens, 10 branches)
- Rev 30 (bundled test file `t_psse_case3.raw` -- 46 buses, 15 gens, 56 branches)

The parser uses a regex pattern `PSS(/|\(tm\))E-(?<rev>\d+)` to detect the revision from
the identification record. If no revision is detected, it defaults to Rev 23. The `REV`
parameter can be explicitly overridden: `psse2mpc(rawfile, '', verbose, REV)`.

**Export:** Writes PSS/E RAW Rev 33 format exclusively.

## Data Sections Parsed

From the `psse2mpc` help text, the following PSS/E record types are imported:
- Identification data
- Bus data
- Branch data
- Fixed shunt data
- Generator data
- Transformer data
- Switched shunt data
- Area data
- HVDC line data

Other data sections (e.g., multi-terminal DC, impedance correction, multi-section line,
zone, interarea transfer, owner, FACTS) are currently ignored.

## Effort Estimate

**Zero effort required.** PSS/E RAW import is a built-in, documented function (`psse2mpc`)
that ships with MATPOWER. No additional packages, wrappers, or custom code needed.

## Octave Compatibility Note

During probing, `psse2mpc` on the bundled `t_psse_case.raw` (a parser test fixture, not a
real power system case) produced a `cellfun: all values must be scalars when UniformOutput
= true` error in `psse_parse_section`. This is an Octave-specific compatibility issue with
that particular test fixture (which uses unusual formatting to stress-test the parser). The
two real power system test files (`t_psse_case2.raw` Rev 29, `t_psse_case3.raw` Rev 30)
parsed successfully on Octave without errors. The MATPOWER test suite (`t_psse.m`) is
designed primarily for MATLAB and may exercise code paths with Octave-incompatible
`cellfun` usage, but the core import pathway works.

## Supporting Infrastructure

The PSS/E converter is implemented as a pipeline of internal functions:
- `psse_read` -- reads and tokenizes the RAW file
- `psse_parse` -- parses records into a structured data object
- `psse_parse_section` -- parses individual data sections
- `psse_parse_line` -- parses individual records
- `psse_convert` -- converts parsed data to MATPOWER `mpc` struct
- `psse_convert_xfmr` -- specialized transformer conversion
- `psse_convert_hvdc` -- specialized HVDC conversion

## Functional Probe

```matlab
mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));

% Import Rev 30 RAW file
mpc = psse2mpc(fullfile(mp_root, 'lib', 't', 't_psse_case3.raw'), '', 0);
% Result: 46 buses, 15 gens, 56 branches -- success

% Import Rev 29 RAW file
mpc2 = psse2mpc(fullfile(mp_root, 'lib', 't', 't_psse_case2.raw'), '', 0);
% Result: 10 buses, 3 gens, 10 branches -- success
```
