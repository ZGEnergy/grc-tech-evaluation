---
probe_id: probe-010
tool: powermodels
source_test: F-3
probe_type: claim_verification
classification: claim_supported
reason: "F-3 correctly classifies SCIP_jll v0.2.1 (wrapping SCIP 8.0.0) as ZIB Academic License. F-8 is incorrect: it states SCIP 8.0 is Apache 2.0, but the Apache 2.0 switch happened at SCIP 8.0.3 (December 2022). SCIP 8.0.0 (April 2022, wrapped by SCIP_jll v0.2.1+0) remains under ZIB Academic. F-8's supply chain score upgrade is unwarranted for the pinned version."
solver_version: "SCIP_jll v0.2.1"
solver_version_match: true
timeout_seconds: 120
wall_clock_seconds: 0
timestamp: "2026-03-14T00:00:00Z"
---

# Probe 010: SCIP_jll v0.2.1 License — ZIB Academic vs Apache 2.0

## Verdict: CLAIM SUPPORTED (F-3 is correct; F-8 contains a material error)

## Evidence Gathered

### 1. Manifest.toml confirms SCIP_jll v0.2.1+0

From `evaluations/powermodels/Manifest.toml`:
```toml
[[deps.SCIP_jll]]
deps = ["Artifacts", "Bzip2_jll", ...]
git-tree-sha1 = "4a23f926d711535640963aea90a3f5d931ae52c7"
uuid = "e5ac4fe4-a920-5659-9bf8-f9f73e9e79ce"
version = "0.2.1+0"
```

### 2. SCIP_jll v0.2.1 wraps SCIP 8.0.0

The `SCIP-v0.2.1+0` tag on the JuliaBinaryWrappers/SCIP_jll.jl GitHub repository contains a README identifying the source tarball as:
```
https://scipopt.org/download/release/scipoptsuite-8.0.0.tgz
```

This is confirmed by the commit timeline: SCIP_jll v0.2.1+0 was built on **April 28, 2022**, which is contemporaneous with the SCIP 8.0.0 release (November 2021). The next SCIP_jll version using the new versioning scheme (800.0.300+0) was built on **December 14, 2022** and wraps SCIP 8.0.3.

### 3. SCIP 8.0.0 is under ZIB Academic License — not Apache 2.0

From the official SCIP website (scipopt.org):

> "Since version **8.0.3**, SCIP is licensed under the Apache 2.0 License. Releases up to and including Version **8.0.2** remain under the ZIB Academic License."

The license switch happened at **SCIP 8.0.3** (December 2022), not at SCIP 8.0.0.

### 4. SCIP_jll versioning scheme change

The JuliaBinaryWrappers project changed the versioning scheme for SCIP_jll around the 8.0.3 release:

| SCIP_jll version | SCIP version | Date | License |
|-----------------|--------------|------|---------|
| 0.1.0+0 | pre-8.x | Aug 2020 | ZIB Academic |
| 0.2.0+0 | 8.0.0 (beta) | Dec 2021 | ZIB Academic |
| **0.2.1+0** | **8.0.0** | **Apr 2022** | **ZIB Academic** |
| 800.0.300+0 | 8.0.3 | Dec 2022 | Apache 2.0 |
| 800.0.400+0 | 8.0.4 | Sep 2023 | Apache 2.0 |
| 800.100.0+0 | 8.1.0 | Dec 2023 | Apache 2.0 |
| 900.0.0+1 | 9.0.0 | Apr 2024 | Apache 2.0 |

## Discrepancy Analysis

### F-3 Assessment (correct)

F-3 states: "SCIP binary (SCIP 8.0.0 via SCIP_jll v0.2.1) uses the ZIB Academic License, which restricts use to non-commercial academic institutions."

This is **accurate**. F-3 even notes correctly: "SCIP 9.x (released 2024) moved to Apache 2.0, but the version pinned in this manifest is SCIP 8.0.0 and remains under ZIB Academic."

### F-8 Assessment (incorrect)

F-8 states: "SCIP v8.0 (November 2021) switched from the ZIB Academic License to Apache 2.0, making it fully permissive for commercial use. The SCIP_jll v0.2.1 in this manifest wraps SCIP 8.0, confirmed by `SCIP.SCIPversion()` returning `8.0` in the devcontainer."

This contains two errors:
1. **Wrong version for license switch**: The switch to Apache 2.0 happened at 8.0.3, not 8.0 (8.0.0). The official SCIP documentation is unambiguous on this point.
2. **`SCIPversion()` returns "8.0" but this means SCIP 8.0.0**: The version string "8.0" corresponds to 8.0.0 (pre-Apache switch), not to 8.0.3+ (post-Apache switch). F-8 treats "8.0" as confirming Apache 2.0, but 8.0.0 is still ZIB Academic.

F-8's conclusion that SCIP_jll v0.2.1 carries Apache 2.0 is **factually wrong**.

## Implications for Supply Chain Scoring

F-8 was used to upgrade the F-8 score from `qualified_pass` (v9) to `pass`, citing the "correction" that SCIP 8.0 is Apache 2.0. This upgrade is not warranted:

- The pinned version (SCIP_jll v0.2.1 = SCIP 8.0.0) is ZIB Academic, non-commercial only
- F-3's `qualified_pass` (commercial deployments must exclude SCIP) remains the correct assessment
- F-8's `pass` status overstates the permissiveness of the pinned solver stack

The correct supply chain picture: SCIP in this manifest is **not** commercially usable. To use SCIP commercially, the manifest would need to be updated to SCIP_jll 800.0.300+0 or newer (wrapping SCIP 8.0.3+).

## SCIP_jll Package vs. Binary License (Secondary Question)

The SCIP_jll Julia wrapper package itself carries a permissive license (the JLL wrapper code is MIT). However, SCIP_jll bundles the SCIP binary directly as a Julia artifact — it is not downloaded separately at runtime. The binary's license (ZIB Academic for SCIP 8.0.0) governs the artifact as distributed. The distinction between wrapper license and bundled binary license is exactly the kind of nuance that makes this a material discrepancy: the wrapper is MIT, the binary is ZIB Academic, and the binary is what runs.

## Summary

| Source | SCIP_jll version | SCIP version | License claimed | Correct? |
|--------|-----------------|--------------|----------------|---------|
| F-3 | v0.2.1 | 8.0.0 | ZIB Academic | **Yes** |
| F-8 | v0.2.1 | 8.0.0 | Apache 2.0 | **No** |
| Ground truth | v0.2.1 | 8.0.0 | ZIB Academic | — |

F-3's claim is supported. F-8 contains a material factual error that inflated the supply chain score.
