# Release v.1.0.0

The layout submitted to the IHP Open Source SG13G2 multi-project wafer with tape-in on
29 September 2026.

| Item | Value |
|---|---|
| Top cell | `LNA2609` |
| Die size | 1.712 mm x 1.752 mm |
| GDS | `gds/LNA2609.gds` |
| Netlist | `netlist/LNA2609_extracted.cir`, extracted from the layout by KLayout LVS |
| Checksums | `doc/CHECKSUMS.txt` |

The GDS in this release is byte for byte the file submitted to the foundry portal. Its md5
checksum is `11402988cdbb86f763eac0eb32c7519a`.

## Verification

| Check | Result |
|---|---|
| Foundry tape-in check | passed, including the dimension check against the registered area |
| Pre-check DRC, KLayout | clean |
| Full DRC, `sg13g2_maximal` | `Seal.m` 68 and `Pas.c` 64, both caused by the inner seal rings |
| LVS, KLayout | PASS, netlists match |

The inner seal rings are intentional. Every block carries its own so that it can be diced
out and handled separately, which the rule `Seal.m` reports because it permits only one
seal ring per chip. The foundry was informed in the submission remark and a waiver was
requested. Neither `Seal.m` nor `Pas.c` belongs to the pre-check list that the foundry
applies as a rejection criterion.

## Contents of the layout

Four ground-signal-ground de-embedding standards, OPEN, SHORT, THRU and LOAD, and twelve
SiGe HBT devices under test across the `npn13g2`, `npn13g2l` and `npn13g2v` flavours. See
`doc/Specification.md` for the full table.
