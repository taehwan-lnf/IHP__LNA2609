# IHP__LNA2609

A test and characterisation vehicle for SiGe HBT modelling, submitted to the IHP Open
Source SG13G2 multi-project wafer with tape-in on 29 September 2026.

The die carries a ground-signal-ground de-embedding kit of four standards and twelve SiGe
HBT devices under test, arranged on a four by four grid inside one die seal ring. Each
individual block additionally carries its own seal ring, so that a block can be diced out
and handled on its own.

| | |
|---|---|
| Top cell | `LNA2609` |
| Die size | 1.712 mm x 1.752 mm |
| Process | IHP SG13G2, open-source PDK |
| MPW run | Open Source SG13G2, tape-in 2026-09-29 |
| Foundry test field | T623 |
| Licence | Apache-2.0 |

## A note on the repository name

The Open-Silicon MPW naming rule is `IHP__<subcategory abbreviation><4 digits>`, and the
published category table carries no abbreviation for a test structure or a characterisation
vehicle. `LNA` was chosen as the nearest available entry, because this die exists to
characterise the transistors of a low noise amplifier rather than to be one. A request
for a dedicated abbreviation has been raised as an issue on Open-Silicon-MPW. If it is
granted after tape-in, the name here stays as it is, since the foundry has already
registered the top cell as `LNA2609`.

The four digits encode the MPW run, 2026-09, instead of being drawn at random by
`gen_structure.py`.

## Layout of this repository

| Path | Contents |
|---|---|
| `doc/` | metadata, specification, datasheet and the TRL self-assessment |
| `release/v.1.0.0/` | the immutable delivery: GDS, extracted netlist, checksums |
| `LNA2609-main/layout/klayout/` | the scripts that generate the layout |
| `LNA2609-main/netlist/layout/` | the netlist extracted from the layout |
| `LNA2609-main/verification/` | the DRC and LVS reports for the released GDS |
| `measurements/v.1.0.0/` | post-silicon measurement data, published after the samples arrive |
| `dependencies/` | none; this design has no submodule dependencies |

## Verification status of the release

| Check | Tool | Result |
|---|---|---|
| Pre-check DRC | KLayout, IHP-Open-PDK sg13g2 deck | clean, zero violations |
| Full DRC | KLayout, `sg13g2_maximal` | `Seal.m` 68 and `Pas.c` 64, both from the inner seal rings |
| LVS | KLayout, IHP-Open-PDK sg13g2 deck | PASS, netlists match |

The two full-deck items are a deliberate consequence of giving every block its own seal
ring, which the rule `Seal.m` forbids because it allows only one seal ring per chip. The
foundry has been told about this in the submission remark and a waiver has been requested.
Neither rule appears in the pre-check list that the foundry uses as a rejection criterion.

## Licence

Apache License 2.0. See `LICENSE`.
