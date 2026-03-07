---
test_id: F-1
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-1: Core License

## License

BSD 3-Clause License

## Verification

License file located at `/workspace/evaluations/matpower/matpower8.1/LICENSE`.

```
The code in MATPOWER is distributed under the 3-clause BSD license
below. The MATPOWER case files distributed with MATPOWER are not covered
by the BSD license. In most cases, the data has either been included
with permission or has been converted from data available from a
public source.

Copyright (c) 1996-2025, Power Systems Engineering Research Center (PSERC)
and individual contributors (see AUTHORS file for details).
All rights reserved.
```

Full BSD 3-Clause text follows (standard template).

## Key Provisions

1. **Permissive:** Free to use, modify, and redistribute (including commercially).
2. **No copyleft:** Derivatives need not be open-source.
3. **Attribution required:** Must retain copyright notice and license.
4. **No endorsement:** Cannot use PSERC/contributor names to endorse products.

## Case File Carve-Out

The LICENSE file explicitly notes that **case files (network data) are NOT
covered by the BSD license.** Most case files are from public sources or
included with permission, but the license status of each case file varies.
This is a minor concern for using MATPOWER code but could matter if
redistributing case data.

## GitHub License Detection

GitHub's license detection reports `NOASSERTION` rather than `BSD-3-Clause`,
likely due to the case file carve-out preamble in the LICENSE file. The
actual license text is standard BSD 3-Clause.

## Assessment

**PASS.** BSD 3-Clause is among the most permissive OSS licenses. No
restrictions on commercial use, modification, or distribution. The case
file carve-out is clearly documented and does not affect code usage.
