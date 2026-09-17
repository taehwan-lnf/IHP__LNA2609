"""Build a named set of DUT cells and report what DRC and LVS make of them.

Two sets live here. OWNER_TABLE is the one that runs; AREA_BAND is kept because its numbers
are quoted in the answer that led to the owner's table.

    OWNER_TABLE   the twelve cells of the owner's spreadsheet of 2026-09-03, twelve single
                  devices, four sizes on each of the three flavours, every one at m = 1.
                  The owner asked for them built and checked before deciding whether any of
                  them goes into the top cell.

    AREA_BAND     the ten cells used earlier the same day to answer "what passes between
                  6 and 7 um2". All ten passed DRC and LVS.

THE INCREMENTS AGREE

The spreadsheet's A_E(final) column uses dl and dw that match gsg_frame.DELTA exactly, and the
ratio column is a second check on the same thing:

    npn13G2V  dw +0.060 dl +0.050  ->  0.18 x 2.55   ratio 5.508 / 3.600  = 1.530
    npn13G2L  dw +0.060 dl +0.050  ->  0.13 x 2.55   ratio 5.6355 / 2.975 = 1.894
    npn13G2   dw +0.050 dl +0.060  ->  0.12 x 0.96   ratio 5.5296 / 3.024 = 1.829

Every area below is recomputed from the flavour's own increments and checked against the
spreadsheet figure, so a transcription slip cannot pass silently.

NAMING

The spreadsheet writes npn13g2V_m1_Nx12_le2.5_we0.12. The repository's own convention, which
gen_gsg_duts.py produces and check_duts.sh consumes, is
GSG_dut_npn13g2v_m1_Nx12_le2p5u_we0p12u: lower-case flavour, a GSG_dut_ prefix, and p for the
decimal point so the name is a legal path. The cells are built under the repository name.

Run it with:  klayout -z -nc -r tools/sweep_dut.py
Then:         bash tools/check_duts.sh $(cat /tmp/sweep_dut_names.txt | tr '\\n' ' ')
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsg_frame as F
import gen_gsg_duts as G

# (pcell, symbol folder name, m, Nx, le, we, the spreadsheet's A_E(final))
OWNER_TABLE = [
    ("npn13G2V", "npn13g2v", 1, 12, 2.5, 0.12, 5.508),
    ("npn13G2V", "npn13g2v", 1, 10, 2.5, 0.12, 4.590),
    ("npn13G2V", "npn13g2v", 1, 8, 2.5, 0.12, 3.672),
    ("npn13G2V", "npn13g2v", 1, 6, 2.5, 0.12, 2.754),
    ("npn13G2L", "npn13g2l", 1, 17, 2.5, 0.07, 5.6355),
    ("npn13G2L", "npn13g2l", 1, 14, 2.5, 0.07, 4.641),
    ("npn13G2L", "npn13g2l", 1, 11, 2.5, 0.07, 3.6465),
    ("npn13G2L", "npn13g2l", 1, 8, 2.5, 0.07, 2.652),
    ("npn13G2", "npn13g2", 1, 48, 0.9, 0.07, 5.5296),
    ("npn13G2", "npn13g2", 1, 39, 0.9, 0.07, 4.4928),
    ("npn13G2", "npn13g2", 1, 32, 0.9, 0.07, 3.6864),
    ("npn13G2", "npn13g2", 1, 22, 0.9, 0.07, 2.5344),
]

AREA_BAND = [
    ("npn13G2", "npn13g2", 1, 56, 0.9, 0.07, None),
    ("npn13G2", "npn13g2", 2, 28, 0.9, 0.07, None),
    ("npn13G2", "npn13g2", 4, 14, 0.9, 0.07, None),
    ("npn13G2", "npn13g2", 7, 8, 0.9, 0.07, None),
    ("npn13G2L", "npn13g2l", 1, 20, 2.5, 0.07, None),
    ("npn13G2L", "npn13g2l", 2, 10, 2.5, 0.07, None),
    ("npn13G2L", "npn13g2l", 1, 48, 1.0, 0.07, None),
    ("npn13G2V", "npn13g2v", 1, 7, 5.0, 0.12, None),
    ("npn13G2V", "npn13g2v", 1, 14, 2.5, 0.12, None),
    ("npn13G2V", "npn13g2v", 1, 35, 1.0, 0.12, None),
]

POINTS = OWNER_TABLE


def area_drawn(flavour, m, nx, le, we):
    return m * nx * we * le


def area_final(flavour, m, nx, le, we):
    dwe, dle = F.DELTA[flavour]
    return m * nx * (we + dwe) * (le + dle)


built = []
print("%-9s %-3s %-4s %-6s %-6s %-10s %-10s %-6s %s"
      % ("FLAVOUR", "m", "Nx", "le", "we", "AE(drawn)", "AE(final)", "ratio", "CELL"))
for pcell, sym, m, nx, le, we, expect in POINTS:
    ad = area_drawn(pcell, m, nx, le, we)
    af = area_final(pcell, m, nx, le, we)
    if expect is not None and abs(af - expect) > 5e-4:
        raise SystemExit("%s m=%d Nx=%d le=%g: computed %.4f um2 against the table's %.4f"
                         % (pcell, m, nx, le, af, expect))
    try:
        name = G.build(pcell, sym, m, nx, le, we, allow_nx_over=True)
        built.append(name)
        note = name
    except SystemExit as exc:
        note = "BUILD REFUSED: %s" % exc
    except Exception as exc:
        note = "BUILD FAILED: %r" % exc
    print("%-9s %-3d %-4d %-6.2f %-6.3f %-10.4f %-10.4f %-6.3f %s"
          % (pcell, m, nx, le, we, ad, af, af / ad, note))

print()
print("built %d of %d" % (len(built), len(POINTS)))
with open("/tmp/sweep_dut_names.txt", "w") as fh:
    fh.write("\n".join(built) + "\n" if built else "")
