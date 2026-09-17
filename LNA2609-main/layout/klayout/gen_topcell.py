"""Assemble the fourteen GSG subcells into one sealed top cell.

Arrangement is 4 rows by 4 columns and the sixteen cells fill it exactly, one row per kind:
the four de-embedding standards, then npn13G2V, npn13G2L and npn13G2 in four sizes each.
The 3 by 5 it replaces always left one slot empty.
The UNSEALED cells are instanced, not the *_sealed study copies, because Seal.m allows one
seal ring per chip and Seal.l forbids any structure outside its boundary.

Two distances decide whether this passes, and both were established by measurement rather
than chosen:

    GAP      between neighbouring cells. Pad.bR asks 8.40 um between pad openings, and with
             a pad opening starting 2.10 um inside each cell edge the separation across a gap
             of g is g + 4.20, so g >= 4.20 satisfies it. TM2.b asks 2.00 um of metal space.
             40.00 is taken instead, which also leaves room for a probe to land.

    KEEPOUT  from the outermost cell bbox to the seal ring's inner edge. Pad.d asks 7.50 um
             and Pad.dR 25.00 um from the pad opening to the Activ inside the EdgeSeal, and
             on top of that the ring's corner approaches the corner pads diagonally: a single
             sealed cell still reported Pad.d at 12.00 um of clearance and cleared only at
             20.00. 40.00 is taken to carry the recommendation as well as the rule.

Every cell is centred in its slot, because GSG_thru is 378.80 um wide against the others'
390.00 and a left-aligned array would step out of true.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_label as L

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEV = os.path.join(_ROOT, "designlib", "teg")
NAME = "LNA2609_nofill"
ROWS, COLS = 4, 4
GAP, KEEPOUT = 20.0, 40.0
INNER_OFF, OPEN_MARGIN = 36.40, 22.80

# Owner instruction 2026-09-02: instance the sealed cells, not the bare ones. Each therefore
# brings its own seal ring inside the outer one, which is fifteen rings on a single chip.
# Seal.m allows one per chip and is expected to report this; what it actually reports is
# measured below rather than predicted.
SUFFIX = "_sealring"

# Owner instruction 2026-09-02: every multi-device column is replaced by a single device
# holding the same emitter fingers, m=2 by Nx=20, m=3 by Nx=30 and m=4 by Nx=40. A column of
# m devices at Nx=10 and one device at Nx=10*m carry the same emitter area, but the single
# device puts every finger on one 1.85 um pitch where the column leaves a 6.70 um gap between
# each pair of devices, and it carries one guard ring instead of m. Counted on the built
# cells, emitter window by emitter window:
#
#     m1_Nx20  20 windows  1.2600 um2  span 35.220  one step, 1.85
#     m2_Nx10  20 windows  1.2600 um2  span 40.070  1.85 x18, 6.70 x1
#     m1_Nx30  30 windows  1.8900 um2  span 53.720  one step, 1.85
#     m3_Nx10  30 windows  1.8900 um2  span 63.420  1.85 x27, 6.70 x2
#     m1_Nx40  40 windows  2.5200 um2  span 72.220  one step, 1.85
#     m4_Nx10  40 windows  2.5200 um2  span 86.770  1.85 x36, 6.70 x3
#
# The m columns are not deleted from the repository. They are built and they pass; they are
# simply not the cells this top instances.
# Owner instruction 2026-09-03: the DUT series is the twelve cells of the owner's table,
# four sizes on each of the three flavours, every one a single device at m = 1. Sixteen
# cells fill a 4 by 4 array exactly, where the 3 by 5 it replaces always left one slot
# empty. Row 0 comes out at the top of the layout, gen_topcell placing row r at
# (ROWS - 1 - r), so this list reads the way the chip does.
#
# Every one of the twelve was built and checked before being put here: DRC returned
# density rules and Pad.kR alone and LVS matched, on all twelve. Their emitter arrays are
# uniform, one pitch each, 2.34 um on npn13G2V, 2.80 on npn13G2L and 1.85 on npn13G2.
#
# The ten DUT cells this replaces are kept in the repository. They are built and they
# pass; they are simply not what this chip carries.
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
ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell(NAME)

# read every cell once so the slot pitch can be taken from the widest and tallest
src = {}
for nm in CELLS:
    s = pya.Layout()
    s.read(os.path.join(DEV, nm + SUFFIX, nm + SUFFIX + ".gds"))
    src[nm] = (s, s.top_cell(), s.top_cell().dbbox())

slot_w = max(b.width() for _, _, b in src.values())
slot_h = max(b.height() for _, _, b in src.values())
pitch_x = slot_w + GAP
pitch_y = slot_h + GAP
array_w = COLS * slot_w + (COLS - 1) * GAP
array_h = ROWS * slot_h + (ROWS - 1) * GAP

print("slot %.2f x %.2f, pitch %.2f x %.2f, array %.2f x %.2f"
      % (slot_w, slot_h, pitch_x, pitch_y, array_w, array_h))
print()

for i, nm in enumerate(CELLS):
    r, c = divmod(i, COLS)
    s, stop, bb = src[nm]
    sub = ly.create_cell(nm + SUFFIX)
    sub.copy_tree(stop)
    # centre the cell in its slot: GSG_thru is narrower than the rest
    sx = c * pitch_x + (slot_w - bb.width()) / 2.0 - bb.left
    sy = (ROWS - 1 - r) * pitch_y + (slot_h - bb.height()) / 2.0 - bb.bottom
    top.insert(pya.CellInstArray(sub.cell_index(),
                                 pya.Trans(pya.Trans.R0, int(round(sx * 1000)),
                                           int(round(sy * 1000)))))

    # Each cell's terminal labels are re-emitted at the top level under a name of their own,
    # c<row><col>_<pin>, which is the name the top schematic gives the same node. Two things
    # make this necessary under deep extraction. A label that sits inside a child names a net
    # inside that child and exports nothing upward, so without this the top circuit would come
    # back holding nothing but seal-ring nets. And the names have to differ from cell to cell,
    # because no drawn layer runs between two cells and the extractor therefore returns one
    # ground per cell rather than one shared substrate.
    tr = pya.Trans(pya.Trans.R0, int(round(sx * 1000)), int(round(sy * 1000)))
    # Both pin layers are carried up, and 8/25 matters as much as 134/25. It holds TI and TO
    # on GSG_open and T on GSG_thru, which are pins of those cells. Left unnamed at the top
    # they are single-connection nets, and the simplifier drops a pin whose net has nothing
    # else on it, so those two instances came back with two pins against their schematics'
    # five and four. The symbol says which labels are pins, the same authority gen_sealed.py
    # uses, so the Metal1 stub names of the DUT cells stay internal where they belong.
    symfile = os.path.join(DEV, nm + SUFFIX, nm + SUFFIX + ".sym")
    pins = set()
    if os.path.exists(symfile):
        pins = set(re.findall(r"name=([A-Za-z0-9_!]+) dir=", io.open(symfile).read()))
    # (10, 25) as well since 2026-09-05: the view 2 tower ends on ground Metal1, so the
    # signal port label sits on Metal2.text. Without it the sealed copies lifted two
    # pins where the schematic declares three and LVS returned MISMATCH with every net,
    # pin and device otherwise matched.
    for lay in ((134, 25), (10, 25), (8, 25)):
        jp = ly.layer(*lay)
        for sh in stop.each_shape(s.layer(*lay)):
            if not sh.is_text() or sh.text.string not in pins:
                continue
            t = sh.text.transformed(tr)
            # Every ground carries the one name sub!, because extraction merges them all.
            # Each of the fourteen cells now reaches the p substrate, the DUTs through their
            # guard rings and the four standards through the substrate ties added for that
            # purpose, and the substrate is one piece of silicon. Giving them fourteen names
            # does not separate them; it only makes the extractor print the merged net as
            # fourteen names joined by bars, which is what the first assembled run showed.
            if sh.text.string == "GND":
                t.string = "sub!"
            else:
                t.string = "c%d%d_%s" % (r, c, sh.text.string)
            top.shapes(jp).insert(t)

    print("   r%d c%d  %-40s at (%.2f, %.2f)" % (r, c, nm, sx + bb.left, sy + bb.bottom))

# Only if the grid is bigger than the cell list. With sixteen cells in a 4 by 4 there is
# no empty slot, and printing one anyway was a leftover from the 3 by 5 arrangement.
for i in range(len(CELLS), ROWS * COLS):
    print("   r%d c%d  %-40s" % (i // COLS, i % COLS, "(empty)"))

# klayout -b does not run the technology autorun macro, so the PyCell libraries have to

# be registered here. See gsg_label.bootstrap_pycells for what it repeats and why.

lib = L.bootstrap_pycells()

if lib is None:

    raise SystemExit("gen_topcell: SG13_dev is not registered even after the PyCell "

                     "bootstrap. Check that the PDK submodules are initialised.")
liblay = lib.layout()
pid = liblay.pcell_id("sealring")
decl = liblay.pcell_declaration("sealring")
l = array_w + 2 * KEEPOUT + OPEN_MARGIN
w = array_h + 2 * KEEPOUT + OPEN_MARGIN
D = {p.name: p.default for p in decl.get_parameters()}
D.update({"l": "%.3fu" % l, "w": "%.3fu" % w})
rx = -KEEPOUT - INNER_OFF
ry = -KEEPOUT - INNER_OFF
# The outer ring is made static before it is placed, because a PCell proxy regenerates itself
# from its parameters and would throw the corner surgery below away.
ringidx = ly.convert_cell_to_static(ly.add_pcell_variant(lib, pid, D))
top.insert(pya.CellInstArray(ringidx,
                             pya.Trans(pya.Trans.R0, int(round(rx * 1000)),
                                       int(round(ry * 1000)))))

# Owner instruction 2026-09-05: every one of the outer ring's four corners is a right angle.
#
# The ring carries no orientation mark now, and it does not need one. What tells one corner of
# this chip from another is the sixteen subcells, each of which still has a staircase at its own
# top-left and a right angle at the other three, and those are what a probe operator reads once
# the die is on the chuck. The outer corners had been three squared and one staircase since
# 2026-09-03, when the mark was inverted from three staircases and one square.
#
# Seal.m is the rule to watch across this change. Measured 2026-09-03 on the assembled top,
# squaring the outer top-left corner returned Seal.m 164 where the staircase returned 165, so
# each staircase corner produces one of those markers on its own. Squaring the last corner is
# expected to move Seal.m by about one count and to leave every other rule alone.
bands = L.square_corner(ly, ly.cell(ringidx), corners=L.ALL_CORNERS)
print("")
print("squared all %d corners of the outer ring over %.2f um, %d layers, band widths kept"
      % (len(L.ALL_CORNERS), L.CORNER_EXT, len(bands)))

folder = os.path.join(DEV, NAME)
os.makedirs(folder, exist_ok=True)
ly.write(os.path.join(folder, NAME + ".gds"))
print()
print("ring l x w  %.2f x %.2f" % (l, w))
print("top cell    %s" % top.dbbox())
print("wrote       %s" % os.path.join(folder, NAME + ".gds"))
