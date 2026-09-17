# LNA2609-main

The top cell of the die.

| Path | Contents |
|---|---|
| `layout/klayout/` | the Python and Ruby scripts that generate the standards, the devices under test and the assembled top cell, together with the DRC and LVS run scripts |
| `netlist/layout/` | the netlist extracted from the layout by KLayout LVS |
| `verification/drc/` | the DRC reports for the released GDS |
| `verification/lvs/` | the LVS reports for the released GDS |

The released GDS itself is under `release/v.1.0.0/gds/` at the top of the repository, so
that the delivery stays in one immutable place.
