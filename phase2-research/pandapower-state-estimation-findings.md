# pandapower State Estimation Investigation

## Summary

pandapower provides the most full-featured open-source Python state estimation module
available, with four algorithm families, bad data detection, zero-injection handling,
and a novel AF-WLS estimator for non-observable distribution grids. However, it remains
primarily an academic/research tool: the documentation itself warns that bad data
removal "is not very robust at this time," convergence problems surface on networks
above ~90 buses, there are no known production deployments, and three-phase SE is
unsupported.

## Algorithms

| Algorithm | Key | Description | Added |
|-----------|-----|-------------|-------|
| Weighted Least Squares | `wls` | Classical Newton-Gauss WLS. Baseline algorithm. Supports zero-injection constraints and current magnitude measurements. | v1.x |
| Iteratively Reweighted WLS | `irwls` | Robust estimator supporting WLS and SHGM (Schweppe-Huber Generalized M-estimator) weighting. Based on Mili et al. (1996). | v2.0.1 |
| Linear Programming | `lp` | LAV (Least Absolute Value) estimator. Independent of measurement weights, making it more robust to poorly scaled data. | v2.0.1 |
| Scipy Optimization | `opt` | Flexible framework supporting WLS, LAV, QL, and QC estimators via scipy.optimize. Documentation warns it "could collapse in some cases with flat start." | v2.0.1 |
| Allocation Factor WLS | `af-wls` | Designed specifically for non-observable distribution grids with sparse metering. Uses allocation factors to avoid pseudo-measurements. Based on IEEE paper by e2nIEE authors (IEEE TPWRS, 2024). | v3.0.0 |

The default optimization method was changed from `OptAlgorithm` to `"Newton-CG"` in
v3.1.x. Most algorithms follow Abur & Exposito, *Power System State Estimation:
Theory and Implementation* (CRC Press, 2004).

## Bad Data Detection

Two complementary methods, combined in a single wrapper:

1. **Chi-squared test** (`chi2_analysis()`): Detects *presence* of bad data in the
   measurement set. Returns a boolean. Default false alarm probability: 0.05.

2. **Largest normalized residual test** (`remove_bad_data()`): Identifies and removes
   *specific* faulty measurements. Default threshold: `rn_max = 3.0`.

**Maturity warning**: The documentation explicitly states:
> "The bad data removal is not very robust at this time. Please treat the results
> with caution!"

Known issues:
- [#1451](https://github.com/e2nIEE/pandapower/issues/1451) (open since 2022-01):
  `remove_bad_data()` fails with "linear algebra methods" error on some measurement
  sets where `estimate()` alone succeeds.
- The chi-squared test can also fail when the underlying WLS estimation does not
  converge, since it depends on a successful estimation run first.

## Observability Analysis

pandapower implements a basic observability check:

- **Minimum measurement rule**: `m_min = 2n - k` (n = bus count, k = slack buses).
  This is necessary but not sufficient -- isolated branches/islands can still make
  the system unobservable even if the count is met.
- **Practical recommendation**: ~4n measurements for robust performance.
- **No formal topological observability analysis** (island detection,
  observable island identification) exists as a standalone function.
- **AF-WLS workaround** (v3.0.0+): For distribution grids that fail the
  observability criterion, AF-WLS can produce estimates without pseudo-measurements
  by using allocation factors derived from the network topology and available
  upstream measurements.
- **Ill-conditioning detection** (v3.0.0+): Matrix conditioning is now computed,
  with a warning issued for ill-conditioned Jacobians -- a common symptom of
  observability problems.

## Scalability

**Tested network sizes from documentation and community reports:**

| Network | Buses | Result |
|---------|-------|--------|
| case9 | 9 | Converges correctly |
| case30 | 30 | Converges correctly |
| case39 | 39 | Converges correctly |
| case89pegase | 89 | Convergence problems reported (wrong solution point, ~4-5% voltage error, >50% reactive power error) |
| SimBench networks | ~1000+ | Failures reported ([#923](https://github.com/e2nIEE/pandapower/issues/923), [#2364](https://github.com/e2nIEE/pandapower/issues/2364)) |

**Performance improvements in v3.1.2** (2025-06-16):
- Sparse matrix conversion for internal SE matrices
- Optimized Jacobian creation (skips computations for non-existing measurements)
- Reduced RAM usage
- Optimized merge computations for co-located measurements

**Known scaling problems:**
- Measurement weight scaling across MW-to-kW ranges causes numerical ill-conditioning
  ([openmod forum discussion](https://forum.openmod.org/t/convergence-problems-on-large-net-models-in-pandapower-state-estimation-module/2706))
- Even with correct power flow results as warm start, the estimator can iterate
  away from the correct solution on larger networks
- LAV estimator reported as "extremely slow" ([#1210](https://github.com/e2nIEE/pandapower/issues/1210))

No published benchmarks exist for SE execution time vs. network size. The power flow
solver handles 10,000+ bus networks, but SE appears untested beyond a few hundred buses
in practice.

## Measurement Support

### Conventional SCADA measurements

| Type code | Measurement | Elements | Unit |
|-----------|-------------|----------|------|
| `v` | Voltage magnitude | bus | p.u. |
| `p` | Active power injection/flow | bus, line, trafo, trafo3w | MW |
| `q` | Reactive power injection/flow | bus, line, trafo, trafo3w | MVar |
| `i` | Current magnitude | line, trafo, trafo3w | kA |

### PMU / phasor measurements

| Type code | Measurement | Elements |
|-----------|-------------|----------|
| `va` | Voltage angle | bus |
| `ia` | Current angle | line, trafo, trafo3w |

PMU-type measurements (`va`, `ia`) are supported through the same `create_measurement()`
API. There is a dedicated test file `test_pmu.py` in the test suite, though issue
[#2524](https://github.com/e2nIEE/pandapower/issues/2524) noted that `test_pmu_case14`
was incorrectly implemented (using case9 data instead of case14). This was closed but
suggests limited PMU testing rigor.

### Three-phase SE

**Not supported.** pandapower has three-phase power flow (`runpp_3ph`) for unbalanced
networks, but the state estimation module operates on the single-phase positive-sequence
equivalent only. There is no documented plan or open issue tracking three-phase SE
development.

### Real SCADA data handling

The `create_measurement()` function accepts arbitrary numeric values and standard
deviations, so real SCADA data can be fed in. The CIM/CGMES converter (v3.0.0+) can
extract measurements from CIM data models into `net.measurement`, providing a path
from utility data formats. However, no purpose-built SCADA ingestion pipeline or
real-time measurement interface exists.

## Known Limitations

### Open bugs (as of 2026-03-27)

| Issue | Status | Description |
|-------|--------|-------------|
| [#2700](https://github.com/e2nIEE/pandapower/issues/2700) | Open | `zero_injection="no_inj_bus"` produces IndexError |
| [#1451](https://github.com/e2nIEE/pandapower/issues/1451) | Open (since 2022) | `remove_bad_data()` fails with linear algebra errors |
| [#2918](https://github.com/e2nIEE/pandapower/issues/2918) | Closed | numpy 1/2 compatibility in SE (fixed) |

### Structural limitations

1. **No topological observability analysis** -- only a measurement count heuristic
2. **No three-phase state estimation** -- single-phase positive-sequence only
3. **No DC state estimation** -- issue [#95](https://github.com/e2nIEE/pandapower/issues/95) requested this in 2018, never implemented
4. **Zero-injection handling is fragile** -- historically required "fake" zero measurements with high weights ([#243](https://github.com/e2nIEE/pandapower/issues/243)); automatic creation added in v3.0.0/v3.1.2 but still has bugs ([#2700](https://github.com/e2nIEE/pandapower/issues/2700))
5. **Bus-bus switch handling** -- SE merges switched buses automatically but can lose measurements in the process ([#253](https://github.com/e2nIEE/pandapower/issues/253))
6. **Disabled branch handling** -- branch mapping changes when branches are disabled, causing SE errors ([#248](https://github.com/e2nIEE/pandapower/issues/248))
7. **Scaling sensitivity** -- measurement weight imbalances across orders of magnitude cause convergence failures on real-world-sized networks
8. **Bad data detection fragility** -- explicitly documented as "not very robust"

## Recent Development Activity

### v3.0.0 (2025-03-06) -- Major SE additions
- AF-WLS for non-observable distribution grids
- Zero-injection measurement creation in WLS
- Ill-conditioning detection and warning
- WLS flat-start divergence fix for highly loaded grids
- Current magnitude measurement handling fix
- Shunt element estimation results
- Power injection results fix
- CIM converter measurement extraction (`load`, `sgen`, `gen`, `shunt`, `ext_grid`, `ward`, `xward`)

### v3.1.0-v3.1.2 (2025-05-26 to 2025-06-16) -- SE optimization focus
- Sparse matrix conversion for internal SE matrices
- RAM usage optimization
- Calculation speed-up
- Jacobian creation optimization (skip non-existing measurements)
- Debug mode for WLS iterations
- Multiple options for automatic zero-injection measurement creation
- AF-WLS bug fixes
- Automatic test creation bug fixes
- Default optimization method changed to Newton-CG

### v3.2.0-v3.4.0 (2025-10-08 to 2026-02-09) -- No SE-specific changes
The v3.2.0, v3.3.0, and v3.4.0 releases focused on other areas (plotting, converters,
FACTS, lightsim2grid). One SE-adjacent fix: numpy 1/2 compatibility in SE ([#2918](https://github.com/e2nIEE/pandapower/issues/2918), closed 2026-03-14).

### Development trajectory
SE received concentrated attention in v3.0.0-v3.1.2 (March-June 2025) but development
appears to have paused since. The AF-WLS paper and implementation represent the most
novel contribution. Core robustness issues (bad data detection fragility, large-network
convergence) remain unaddressed.

## Production Readiness Assessment

**Verdict: Research/prototyping tool, not production-ready for utility-grade SE.**

| Criterion | Assessment |
|-----------|------------|
| Algorithm breadth | Strong -- 5 algorithm families covering classical and robust approaches |
| AF-WLS innovation | Notable -- addresses real distribution grid observability gap |
| Bad data detection | Weak -- docs self-describe as "not very robust" |
| Scalability | Weak -- convergence problems reported above ~90 buses |
| PMU support | Basic -- measurement types exist, testing is thin |
| Three-phase SE | Absent |
| DC SE | Absent |
| Production deployments | None known |
| Real SCADA integration | Possible via CIM converter, but no turnkey pipeline |
| Active maintenance | Moderate -- SE got focused development in mid-2025, now stalled |
| Test coverage | Moderate -- test suite exists but has known gaps (PMU test bug) |

For Phase 2 Stage 2 evaluation purposes: pandapower SE is the strongest Python-native
SE implementation available in the open-source ecosystem, suitable for research,
education, and small-network prototyping. It would require significant hardening
(scaling fixes, robust bad data detection, observability analysis) before use in
an operational control center or real-time monitoring context.

## Sources

- [pandapower SE documentation (v3.3.0/latest)](https://pandapower.readthedocs.io/en/latest/estimation.html)
- [pandapower SE documentation (v3.4.0/stable)](https://pandapower.readthedocs.io/en/stable/estimation.html)
- [GitHub doc/estimation.rst (develop branch)](https://github.com/e2nIEE/pandapower/blob/develop/doc/estimation.rst)
- [GitHub CHANGELOG.rst](https://github.com/e2nIEE/pandapower/blob/develop/CHANGELOG.rst)
- [GitHub releases page](https://github.com/e2nIEE/pandapower/releases)
- [OpenMod forum: Convergence problems on large net models](https://forum.openmod.org/t/convergence-problems-on-large-net-models-in-pandapower-state-estimation-module/2706)
- [AF-WLS IEEE paper (IEEE TPWRS, 2024)](https://ieeexplore.ieee.org/document/10497141/)
- [About pandapower](https://www.pandapower.org/about/)
- GitHub issues: [#2700](https://github.com/e2nIEE/pandapower/issues/2700), [#1451](https://github.com/e2nIEE/pandapower/issues/1451), [#2524](https://github.com/e2nIEE/pandapower/issues/2524), [#1269](https://github.com/e2nIEE/pandapower/issues/1269), [#253](https://github.com/e2nIEE/pandapower/issues/253), [#248](https://github.com/e2nIEE/pandapower/issues/248), [#243](https://github.com/e2nIEE/pandapower/issues/243), [#923](https://github.com/e2nIEE/pandapower/issues/923), [#2364](https://github.com/e2nIEE/pandapower/issues/2364), [#1210](https://github.com/e2nIEE/pandapower/issues/1210), [#95](https://github.com/e2nIEE/pandapower/issues/95), [#2918](https://github.com/e2nIEE/pandapower/issues/2918), [#277](https://github.com/e2nIEE/pandapower/issues/277)
