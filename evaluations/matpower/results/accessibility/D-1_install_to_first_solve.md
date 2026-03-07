---
test_id: D-1
tool: matpower
dimension: accessibility
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T12:30:00Z"
---

# D-1: Install-to-First-Solve

## Result: INFORMATIONAL

## Finding

MATPOWER installation requires a manual multi-step process with no package manager support. From clean environment to first successful DCPF solve takes approximately 5-10 minutes, but the process has significant friction points that would trip up a new user unfamiliar with MATLAB/Octave path management.

## Evidence

### Installation Process

The devcontainer evaluation uses a custom `setup.sh` script:

1. **Download** (automated): `curl` downloads `matpower8.1.zip` (46 MB) from GitHub Releases.
2. **Checksum verification** (automated): SHA256 hash verified against known value.
3. **Extraction** (automated): `unzip` extracts to `matpower8.1/` directory.
4. **Path setup** (manual): Must `addpath` for 5+ subdirectories:

   ```matlab
   addpath(fullfile(mp_root, 'lib'));
   addpath(fullfile(mp_root, 'data'));
   addpath(fullfile(mp_root, 'mips', 'lib'));
   addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
   addpath(fullfile(mp_root, 'mptest', 'lib'));
   ```

### Friction Points

1. **No package manager.** MATPOWER is not in `apt`, `pip`, Julia Registry, or Octave Forge. The official download is a zip from GitHub Releases. The `matpower` PyPI package is a third-party oct2py wrapper, not an official distribution.

2. **Interactive installer unusable in batch mode.** `install_matpower.m` uses `input()` prompts, making it unusable in Docker, CI, or scripted environments. The evaluator had to reverse-engineer the required `addpath` calls from the installer source.

3. **Undocumented sub-package dependencies.** The need to add `mips/lib`, `mp-opt-model/lib`, and `mptest/lib` to the path is not documented outside the interactive installer. A new user following the README would not know these paths are required.

4. **No version pinning mechanism.** There is no lockfile, manifest, or reproducible install mechanism. The only version guarantee is the zip filename.

5. **No `savepath` by default.** `addpath` changes are session-local. Every new Octave session requires re-running the path setup unless the user manually calls `savepath` — which modifies a system-level file.

### Time-to-First-Solve

| Step | Time | Notes |
|------|------|-------|
| Download zip | ~10s | 46 MB from GitHub CDN |
| Extract | ~5s | |
| Figure out addpath | ~5 min (first time) | Requires reading installer source or trial-and-error |
| Write verify script | ~2 min | `loadcase` + `rundcpf` is 5 lines |
| Run DCPF | 0.17s | Solves instantly once paths are correct |
| **Total (experienced)** | **~2 min** | With known addpath list |
| **Total (new user)** | **~10 min** | Including path discovery |

### Positive Notes

- Once paths are set, the API is clean: `mpc = loadcase('case39'); results = rundcpf(mpc);` — two lines to first solve.
- The `verify_install.m` script in the evaluation directory demonstrates the minimal setup.
- MATPOWER's `mpver()` function confirms version immediately.
- Error messages when paths are missing are clear: "undefined function 'loadcase'" makes it obvious what's wrong.

## Implications

The install experience is a **B-** to **C+** for accessibility:
- No package manager support is a meaningful barrier for government/institutional deployment
- Path management friction is an Octave/MATLAB ecosystem issue, not unique to MATPOWER
- Once installed, the tool is immediately productive (strong first-solve experience)
- The lack of batch-mode installation is a specific pain point for Docker/CI environments
- Compared to `uv sync` (Python tools) or `Pkg.instantiate()` (Julia tools), this is significantly more manual
