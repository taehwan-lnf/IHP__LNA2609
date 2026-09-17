"""Symbols for the fourteen subcells, schematics for their sealed copies, and a top schematic.

Owner instruction 2026-09-02: every subcell must pass LVS, and the top cell needs the
subcells drawn as symbols so its schematic can be hierarchical.

Three things are written.

    <name>.sym                  a symbol for each bare subcell, its pins taken from the
                                .subckt line of that cell's own netlist so the two cannot
                                drift apart
    <name>_sealring.sch/.sym    the sealed copy, one instance of the bare symbol. The seal
                                ring adds no device and no net: extracted, GSG_open_sealring
                                and GSG_open give the same two res_topmetal2 on the same
                                nets, and the same holds for a DUT
    TOP_..._OPENMPW.sch         fourteen instances, each pin on a net of its own, because
                                the fourteen structures share no connection in the layout

Netlisting uses xschem's -f, which flattens the netlist while leaving the drawing
hierarchical. That is what lets the schematic match a layout extracted in flat mode, which is
the mode these cells need: deep mode wraps each device in a PCell subcircuit of its own and
reports we and le the other way round.
"""
import io
import os
import re
import sys

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# tools/ is not on sys.path when KLayout or python runs this file by path, so the shared
# writer would not import. gen_gsg_duts.py and sweep_dut.py do the same for gsg_frame.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
DEV = os.path.join(PROJECT, "designlib", "teg")
LEAF = "G1SG2_pitch100u_lvsres_lauching_metal_cwpg_via_fence"
TOP = "LNA2609_nofill"
# ROWS and COLS are READ from gen_topcell.py, for the same reason CELLS is. Kept here as
# their own literal they went stale the moment the top became 4 by 4: this file carried on
# naming nets on a five-column grid, so the fifth cell was c04 in the schematic and c10 in
# the layout, and the assembled top failed LVS on cells that were themselves sound.
_topgrid = re.search(r"^ROWS, COLS = (\d+), (\d+)",
                     io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "gen_topcell.py"), encoding="utf-8").read(),
                     re.M)
if not _topgrid:
    raise SystemExit("could not read ROWS, COLS out of gen_topcell.py")
ROWS, COLS = int(_topgrid.group(1)), int(_topgrid.group(2))

CELLS = [
    "GSG_open",
    "GSG_short",
    "GSG_thru",
    "GSG_load",
    "GSG_dut_npn13g2v_m1_Nx12_le2p5u_we0p12u",
    "GSG_dut_npn13g2v_m1_Nx10_le2p5u_we0p12u",
    "GSG_dut_npn13g2v_m1_Nx8_le2p5u_we0p12u",
    "GSG_dut_npn13g2v_m1_Nx6_le2p5u_we0p12u",
    "GSG_dut_npn13g2l_m1_Nx17_le2p5u_we0p07u",
    "GSG_dut_npn13g2l_m1_Nx14_le2p5u_we0p07u",
    "GSG_dut_npn13g2l_m1_Nx11_le2p5u_we0p07u",
    "GSG_dut_npn13g2l_m1_Nx8_le2p5u_we0p07u",
    "GSG_dut_npn13g2_m1_Nx48_le0p9u_we0p07u",
    "GSG_dut_npn13g2_m1_Nx39_le0p9u_we0p07u",
    "GSG_dut_npn13g2_m1_Nx32_le0p9u_we0p07u",
    "GSG_dut_npn13g2_m1_Nx22_le0p9u_we0p07u",
]
# Each cell keeps its symbol and its schematic beside its own layout, so every cell folder has
# to be on the library path. The leaf rc adds lib/sym and lib/sch and nothing else, and with a
# symbol it cannot resolve xschem writes "IS MISSING !!!!" into the netlist and carries on
# rather than failing, which is how the first attempt produced an empty subcircuit.
_BASE = io.open(os.path.join(DEV, LEAF, "xschemrc"), encoding="utf-8").read()


def rc_for(cells):
    lines = [_BASE.rstrip(), ""]
    for c in cells:
        lines.append("append XSCHEM_LIBRARY_PATH :$::env(DESIGN_ROOT)/designlib/teg/%s" % c)
        lines.append("append XSCHEM_LIBRARY_PATH :$::env(DESIGN_ROOT)/designlib/teg/%s_sealring" % c)
    lines += ["", "set lvs_netlist 1", ""]
    return "\n".join(lines)


# The top schematic must instance exactly what the top layout holds, and in the same order,
# so the list is READ from gen_topcell.py at run time rather than kept in two places. It was
# kept in two places for one revision and drifted within the hour: gen_topcell.py put
# GSG_dut_npn13g2_m1_Nx20 in the slot where this file still had m2_Nx10, and the assembled
# top failed LVS with a layout instance the schematic did not have. Parsing the other file is
# uglier than a literal list and it is the only form that cannot go stale.
_topsrc = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_topcell.py"),
                  encoding="utf-8").read()
TOPCELLS = re.findall(r'"([^"]+)"',
                      re.search(r"^CELLS = \[.*?^\]", _topsrc, re.S | re.M).group(0))
if not TOPCELLS:
    raise SystemExit("could not read CELLS out of gen_topcell.py")

RC = None      # built per call by rc_for, so the path list cannot go stale

# One writer, in one file, for the symbol and for the wrapper that draws wires onto its pins.
# They were defined here until 2026-09-04, when a hard-coded second copy of the symbol text in
# gen_gsg_duts.py was found to place the pins elsewhere, leaving thirteen sealed schematics
# with their DUT instance on net1, net2 and net3 rather than on IN, OUT and GND.
from gsg_views_lib import ports_of, write_symbol, write_wrapper


made = []
for cell in CELLS:
    pins = ports_of(cell)
    folder = os.path.join(DEV, cell)
    write_symbol(folder, cell, pins,
                 "* Symbol for the bare cell, pins taken from its own .subckt line.\n")

    sealed = cell + "_sealring"
    sfolder = os.path.join(DEV, sealed)
    os.makedirs(sfolder, exist_ok=True)
    write_wrapper(sfolder, sealed, cell, pins)
    write_symbol(sfolder, sealed, pins,
                 "* Symbol for the sealed cell, same pins as the bare one it wraps.\n")
    io.open(os.path.join(sfolder, "xschemrc"), "w", encoding="utf-8",
            newline="\n").write(rc_for(CELLS))
    made.append((cell, sealed, pins))
    print("%-42s pins %s" % (cell, " ".join(pins)))

# --- the top schematic ----------------------------------------------------------------
out = ["""v {xschem version=3.4.4 file_version=1.2
* %s
*
* Fourteen sealed subcells in three rows of five. Nothing connects one to another in the
* layout, so every pin of every instance goes to a net of its own, named c<row><col>_<pin>.
}
G {}
K {}
V {}
S {}
E {}
T {%s} -400 -400 0 0 0.5 0.5 {}
""" % (TOP, TOP)]

# The order is TOPCELLS' and not made's, because the slot a cell sits in is what names its
# nets and gen_topcell.py walks TOPCELLS. Iterating made instead put Nx40 in the layout's r2c0
# and m2_Nx10 in the schematic's, and the compare failed on cells that were sound.
bysealed = {m[0]: m for m in made}
for i, (cell, sealed, pins) in enumerate(bysealed[n] for n in TOPCELLS):
    r, c = divmod(i, COLS)
    ox = c * 420
    oy = r * 420
    out.append("C {%s.sym} %d %d 0 0 {name=X%d}\n" % (sealed, ox, oy, i + 1))
    h = max(60, 30 * ((len(pins) + 1) // 2) + 30)
    for j, pin in enumerate(pins):
        side = -1 if j % 2 == 0 else 1
        y = oy - h + 30 + 30 * (j // 2)
        x = ox + side * 90
        xo = x + side * 70
        # The eleven cells that reach the substrate share one ground net, and the measurement
        # says so: deep extraction of the assembled top returned the ten DUT grounds and
        # GSG_load's joined into a single net, printed as one name with the eleven labels
        # separated by bars. GSG_load joins them because it now carries its own substrate tie,
        # two Activ and pSD strips inside its ground plane. The substrate is one piece of
        # silicon and every guard ring sits on it, so the merge is physical.
        #
        # All four standards now carry substrate ties of their own, so the merge covers the
        # whole of the top cell and not the eleven cells it covered when only GSG_load and
        # the DUTs reached the substrate.
        if pin == "GND":
            net = "sub!"
        else:
            net = "c%d%d_%s" % (r, c, pin)
        out.append("N %g %g %g %g { lab=%s}\n" % (x, y, xo, y, net))
        out.append("C {devices/lab_pin.sym} %g %g 0 0 {name=l%d_%d sig_type=std_logic lab=%s}\n"
                   % (xo, y, i + 1, j + 1, net))

folder = os.path.join(DEV, TOP)
os.makedirs(folder, exist_ok=True)
io.open(os.path.join(folder, TOP + ".sch"), "w", encoding="utf-8",
        newline="\n").write("".join(out))
io.open(os.path.join(folder, "xschemrc"), "w", encoding="utf-8", newline="\n").write(rc_for(CELLS))
print()
print("wrote %s with %d instances" % (TOP, len(TOPCELLS)))
