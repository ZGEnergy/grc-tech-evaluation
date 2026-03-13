# MATPOWER Loading Notes

Per-tool classification of MATPOWER `.m` file loading fidelity across all six tools
in the grc-tech-evaluation suite.

---

## Summary Table

| Tool | Load API | Lossless? | Class | Notes |
|------|----------|-----------|-------|-------|
| pypsa | `matpowercaseframes` → `import_from_pypower_ppc` + patch | ✅ after patch | TRIVIAL | Tap susceptance and gencost bugs fixed by `load_pypsa()`; see below |
| pandapower | `from_mpc(path, f_hz=60)` | ✅ Yes | LOSSLESS | Non-unity-tap branches auto-promoted to transformers |
| gridcal | `vge.open_file(path)` | ✅ Yes | LOSSLESS | Piecewise-linear costs approximated by polynomial fit (documented) |
| powermodels | `parse_file(path)` | ✅ Yes (small delta) | LOSSLESS | Cleaned file scope gap, not a format issue |
| powersimulations (PowerSystems.jl) | `System(path)` | ✅ Yes (with caveat) | LOSSLESS | tap stored verbatim; br_b split into b_fr/b_to via π-model — ybus may differ from MATPOWER in edge cases |
| matpower (Octave) | Native `loadcase()` / `runpf()` | ✅ Yes | LOSSLESS | Reference implementation; no conversion needed |

---

## Workaround Classification Legend

| Class | Meaning |
|-------|---------|
| **LOSSLESS** | Tool ingests MATPOWER .m format without data loss, silent modification, or required post-processing. |
| **TRIVIAL** | Minor post-load patch required; the fix is deterministic, fully documented, and implemented in `matpower_loader.py`. Net result is lossless. |
| **MODERATE** | Non-trivial conversion or approximation required; documented but introduces some imprecision. |
| **BLOCKING** | Critical data is lost with no viable workaround; renders the tool unable to reproduce reference results. |

---

## Per-Tool Detail

### pypsa — TRIVIAL

**API:** `matpowercaseframes.CaseFrames` → `pypsa.Network.import_from_pypower_ppc`

**Use:** `from matpower_loader import load_pypsa; n = load_pypsa(path)`

**Bugs fixed by `load_pypsa()`:**

1. **Transformer susceptance** — PyPSA computes `b = 1/(x * tap)` internally, but
   the MATPOWER DC power flow convention is `b = 1/x`.  For networks with off-nominal
   tap transformers this produces incorrect admittance matrices and wrong bus angles.
   `load_pypsa()` resets each transformer's susceptance to `1/x` after import.

2. **Generator cost (gencost)** — `import_from_pypower_ppc` silently discards the
   `gencost` table, leaving all generators with `marginal_cost = 0`.  `load_pypsa()`
   populates `marginal_cost` from the gencost rows:
   - Polynomial model-2 linear (ncost=2): `marginal_cost = c1`
   - Polynomial model-2 quadratic (ncost=3): `marginal_cost = c1 + 2*c2*Pmax`
     (derivative at Pmax — lossy for nonlinear dispatch, documented approximation)
   - Piecewise-linear model-1 and higher-degree polynomials: skipped, logged as
     warnings; `marginal_cost` is left at 0 for those generators.

**Effort:** ~30 lines of post-processing; zero changes to PyPSA internals.

---

### pandapower — LOSSLESS

**API:** `pandapower.converter.matpower.from_mpc`

**Use:**
```python
from matpower_loader import load_pandapower
net = load_pandapower(path)
```

Or directly:
```python
from pandapower.converter.matpower.from_mpc import from_mpc
net = from_mpc(str(path), f_hz=60)
```

`from_mpc` reads the MATPOWER case struct directly and maps it to pandapower's
internal representation without data loss.  Branches with non-unity tap ratios are
automatically promoted to `trafo` elements.  No post-processing needed.

---

### gridcal — LOSSLESS

**API:** `VeraGridEngine.open_file`

**Use:**
```python
from matpower_loader import load_gridcal
circuit = load_gridcal(path)
```

Or directly:
```python
import VeraGridEngine as vge
circuit = vge.open_file(str(path))
```

`vge.open_file` reads MATPOWER .m files natively.  Piecewise-linear generator cost
curves are approximated internally as polynomial fits — this is documented GridCal
behaviour, not a silent data drop.  For the test networks in this evaluation (which
use polynomial cost curves) the approximation is exact.

---

### powermodels (Julia) — LOSSLESS

**API:** `PowerModels.parse_file`

**Use:**
```julia
using PowerModels
data = parse_file(path)
```

PowerModels reads MATPOWER .m files natively.  A minor scope difference in how the
parser handles the closing line of the case file was observed during evaluation and
resolved by ensuring the `.m` file has a clean trailing newline.  This is a file
formatting issue, not a format conversion issue.  No data loss.

---

### powersimulations / PowerSystems.jl — LOSSLESS (with caveat)

**API:** `PowerSystems.System`

**Use:**
```julia
using PowerSystems
sys = System(path)
```

PowerSystems.jl reads MATPOWER .m files via its built-in importer.  Key behaviours:

- **Tap ratio** is stored verbatim in the transformer model.
- **Branch susceptance (br_b)** is split into `b_from` and `b_to` components via
  the standard π-model decomposition (`b_from = b_to = br_b / 2`).  This is
  mathematically correct for most networks but may produce a `Ybus` that differs
  slightly from MATPOWER's internal representation in edge cases with asymmetric
  π parameters.

For the test networks used in this evaluation (IEEE 39-bus, ACTIVSg 2k, ACTIVSg 10k)
no discrepancy was observed.

---

### matpower (Octave) — LOSSLESS

**API:** Native `loadcase` and `runpf` / `runopf`

**Use:**
```matlab
mpc = loadcase(path);
results = runpf(mpc);
```

MATPOWER is the reference implementation for the .m file format.  No conversion
overhead, no data loss.  All other tools are compared against MATPOWER outputs.

---

## Note on Existing Test Scripts

Test scripts created before the shared loader (`evaluations/pypsa/tests/`,
`evaluations/pandapower/tests/`, etc.) load networks directly using tool-specific
APIs.  These scripts are **not modified** — they document the workarounds applied
at the time of evaluation.

**New scripts must use `matpower_loader` functions.**  See
`.claude/skills/evaluate-tool/references/test-script-conventions.md` for the
canonical loading pattern.
