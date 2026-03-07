---
test_id: F-7
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-7: Provenance Verification

## Criteria

Assess whether published releases can be cryptographically verified (signed tags,
GPG-signed packages, SLSA provenance, reproducible builds).

## Result: FAIL

GridCal provides no cryptographic provenance for any release artifact. There is no
mechanism to verify that a PyPI package was built from a specific source commit.

### Evidence

- **Git tags**: Tags exist on GitHub but are not GPG-signed. `git tag -v` fails with
  no signature.
- **PyPI packages**: No GPG signatures (`.asc` files) accompany any release on PyPI.
  No Sigstore/cosign attestations published.
- **SLSA provenance**: No SLSA provenance metadata. No in-toto attestations.
- **Reproducible builds**: No reproducibility documentation or build attestation.
  Builds are not performed via GitHub Actions with provenance (no `--provenance` flag
  in publish workflow).
- **SBOM**: No Software Bill of Materials (SBOM) published in CycloneDX or SPDX format.

### Impact

Without provenance verification, an evaluator cannot cryptographically confirm that:
1. A PyPI release corresponds to a specific source commit
2. The release was not tampered with between build and publish
3. The build environment was not compromised

This is a gap shared by many academic open-source projects but is relevant for
government or regulated deployments requiring supply chain attestation (e.g., EO 14028,
NIST SSDF).

### Mitigation

Organizations can pin to specific commit hashes and build from source to establish
their own provenance chain, but this shifts the burden to the consumer.
