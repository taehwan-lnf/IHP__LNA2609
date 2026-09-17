"""Put a seal ring round each standard and DUT, as tight to the cell as the rules allow.

The sealring PCell maps its l and w onto what it draws exactly linearly, measured at three
sizes:

    EdgeSeal.boundary  0 .. l + 50.00          edgeBox 25.00 on each side
    Passiv            25.00 .. l + 25.00
    metal ring outer  32.20 .. l + 17.80
    metal ring inner  36.40 .. l + 13.60       the opening a cell has to fit in

so the opening is l - 22.80 across, and l = opening + 22.80.

The clearance from the cell's own metal to the ring's is set by the widest minimum space of
the layers involved: TM2_b at 2.00 um, against TM1_b 1.64, pSD_b 0.31, Act_b 0.21 and M1_b
0.18. CLEAR is 3.00, which leaves a micron over the binding rule.

Seal.b is the one that could bite instead, since it asks 4.90 um from any Activ to the seal
ring's layers and CLEAR is only 3.00. Every cell's Activ is measured here before anything is
built, so that if a cell has Activ near its edge it is known now rather than after a DRC run.

The sealed cells are written as <name>_sealring and the originals are left alone. Each carries
its own ring, which Seal.m forbids at chip level, one ring per chip; that is a top-level
matter and these are subcells, as the owner said when asking for this.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_frame as F
import gsg_label as L

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEV = os.path.join(_ROOT, "designlib", "teg")
EDGEBOX, INNER_OFF, OPEN_MARGIN = 25.0, 36.40, 22.80
CLEAR = 26.0
TM2 = (134, 0)

# Owner instruction 2026-09-04: no filler of any kind inside a sealed cell. Dummy metal near a
# launching fixture or a de-embedding standard changes what the standard measures, and the
# whole set is only subtractive if the standard carries what the DUT carries.
#
# These are the nine layers the NoFillerStack PCell draws, and the three filler macros subtract
# every one of them. NoMetFiller (160/0) is left out on purpose: it is redundant for the metals
# and it does not reach Activ or GatPoly, which are the two the macros exclude by .nofill
# alone.
NOFILL = [(1, 23),      # Activ
          (5, 23),      # GatPoly
          (8, 23), (10, 23), (30, 23), (50, 23), (67, 23),   # Metal1 to Metal5
          (126, 23), (134, 23)]                              # TopMetal1, TopMetal2
GFIL_I = 400.0          # max side of one GatPoly:nofill shape

# Where the I and the O go in x, relative to the cell's own left edge. These are the
# centres of the upper G pad openings, read off Passiv 9/0 on the built cells on
# 2026-09-13 as x 2.100..77.900 and x 172.100..247.900, whose midpoints are these.
G_PAD_IN_X = 40.0       # the input side, which is always the left in x
G_PAD_OUT_X = 210.0     # the output side
NOFILL_MARGIN = 20.0    # how far the exclusion reaches past everything it has to cover,
                        # above and below. Owner instruction 2026-09-14 raised this from the
                        # 5.0 of 2026-09-08, at the same time as the thing being covered grew
                        # from the signal pad alone to the signal pad and the transistor.
                        # 46.825 for the Nx48 device plus 20.000 gives y +-66.825.

# The transistor a DUT instantiates arrives as a cell whose name ends _flat, one per cell. The
# four de-embedding standards instantiate none, which is why a cell matching nothing here is
# not an error.
DEVICE_RE = re.compile(r"npn13G2[A-Za-z]*_Nx\d+_flat\Z")

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
# The list held 29 entries between 2026-09-13 and 2026-09-14. The 13 that were not on the chip
# were archived on the owner's instruction, to
# /project/ihp_sg13g2/backups/mpw202609_offchip_cells_2026-09-14_170213.tar.gz, and their
# directories removed, so naming them here would stop the run at the first missing input.
# Restoring that archive and putting the names back is all it takes to build them again.
# Owner instruction 2026-09-03: every sealed cell carries two orientation marks, because the
# four-fold symmetry of a GSG cell leaves no way to tell which way it is turned. The marks
# answer different questions and are used together. The TopMetal2 label says which cell is
# under the probe and, being readable one way up only, which way up it is. The squared corner
# says which way the die is turned, at a magnification where no text can be read. Both were
# run through DRC before adoption and each returned the cell's own baseline exactly,
# AFil.g 1 and GFil.g 1 and Pad.kR 192 and nothing more. See tools/gsg_label.py for how they
# are drawn and for the rules that fixed their dimensions.
#
# The label is left electrically floating rather than joined to the ground plane, on the
# owner's instruction of 2026-09-03. It sits under passivation and carries no device.
STANDARD_TEXT = {
    "GSG_open":  ("OPEN",  "DEEMBED STD"),
    "GSG_short": ("SHORT", "DEEMBED STD"),
    "GSG_thru":  ("THRU",  "DEEMBED STD"),
    "GSG_load":  ("LOAD",  "50 OHM RPPD"),
}

# The folder name is lower case while the PCell and the delta table are not, so the flavour
# is mapped rather than upper-cased in place.
FLAVOUR = {"npn13g2": "npn13G2", "npn13g2l": "npn13G2L", "npn13g2v": "npn13G2V"}


def label_lines(name):
    """The two lines a cell carries: what it is on top, and its final emitter area below.

    The figures are recomputed from the cell name with the same increments gsg_frame uses for
    the annotation inside the guard ring, so the two can never disagree. Recomputing rather
    than reading the drawn text also means a cell built before the annotation existed still
    gets a correct label.
    """
    if name in STANDARD_TEXT:
        return STANDARD_TEXT[name]
    m = re.match(r"GSG_dut_(npn13g2[lv]?)_m(\d+)_Nx(\d+)_le([0-9p]+)u_we([0-9p]+)u\Z", name)
    if not m:
        raise SystemExit("gen_sealed: cannot read a label out of %r" % name)
    flav, multi, nx = FLAVOUR[m.group(1)], int(m.group(2)), int(m.group(3))
    le = float(m.group(4).replace("p", "."))
    we = float(m.group(5).replace("p", "."))
    dwe, dle = F.DELTA[flav]
    return flav.upper(), "AE=%.4fUM2" % (multi * nx * (we + dwe) * (le + dle))


lib = L.bootstrap_pycells()
if lib is None:
    raise SystemExit("gen_sealed: SG13_dev is not registered even after the PyCell "
                     "bootstrap. Check that the PDK submodules are initialised.")
liblay = lib.layout()
pid = liblay.pcell_id("sealring")
decl = liblay.pcell_declaration("sealring")

def signal_and_device(name):
    """The signal span and the transistor extent of one cell, both in cell coordinates.

    The signal is found as it has been since 2026-09-08: in the source cell the only TopMetal2
    crossing y = 0 is the signal itself, because the coplanar ground stops at |y| = 25 and the
    seal ring is not on the source at all. Measuring it rather than writing it down means the
    exclusion follows the fixture if the fixture ever moves.

    The transistor is found by cell name. A de-embedding standard has none and gets None for
    that half, which is not an error: a standard still receives the exclusion, it simply does
    not contribute to how large it has to be.
    """
    src = pya.Layout()
    src.read(os.path.join(DEV, name, name + ".gds"))
    sc = src.top_cell()

    sig = pya.Region(sc.begin_shapes_rec(src.layer(*TM2))).merged().select_interacting(
        pya.Region(pya.Box(-10 ** 9, -1, 10 ** 9, 1)))
    if sig.is_empty():
        raise SystemExit("%s: nothing on TopMetal2 crosses y=0, so the signal span cannot be "
                         "measured and the exclusion cannot be placed" % name)
    sb = sig.bbox().to_dtype(src.dbu)

    def find_device(cell, depth=0):
        """The transistor's box in this cell's coordinates, or None if it holds none."""
        if depth > 6:
            return None
        for inst in cell.each_inst():
            child = src.cell(inst.cell_index)
            if DEVICE_RE.match(child.name.split("$")[0]):
                return child.dbbox().transformed(inst.dtrans)
            deeper = find_device(child, depth + 1)
            if deeper is not None:
                return deeper.transformed(inst.dtrans)
        return None

    return sb, find_device(sc)


def common_exclusion(cells):
    """The one rectangle every cell gets, measured over all of them at once.

    x is deliberately not grown by the margin. The signal already runs the full width of the
    cell, from 0.000 to 250.000, so growing x would push the exclusion outside the cell it
    belongs to. Only y grows.
    """
    box = None
    tallest = (0.0, None)
    for nm in cells:
        sb, dev = signal_and_device(nm)
        for b in (sb, dev):
            if b is not None:
                box = b if box is None else box + b
        if dev is not None and dev.height() > tallest[0]:
            tallest = (dev.height(), nm)
    if box is None:
        raise SystemExit("gen_sealed: there is nothing to measure the exclusion from")

    nb = pya.DBox(box.left, box.bottom - NOFILL_MARGIN,
                  box.right, box.top + NOFILL_MARGIN)
    # GFil.i is the only rule in the deck that limits the size of a nofill shape. Checked
    # against the deck on 2026-09-14: every other with_bbox_max is about filler shapes or LBE,
    # and AFil.i is a spacing to PWell:block rather than a size.
    if max(nb.width(), nb.height()) > GFIL_I:
        raise SystemExit("the exclusion is %.2f x %.2f um, which breaks GFil.i's %.0f"
                         % (nb.width(), nb.height(), GFIL_I))
    print("exclusion measured once over all %d cells" % len(cells))
    print("  signal and devices  x %8.3f..%8.3f  y %8.3f..%8.3f" % (box.left, box.right, box.bottom, box.top))
    print("  tallest device      %.3f um in %s" % (tallest[0], tallest[1]))
    print("  plus %.3f um in y   x %8.3f..%8.3f  y %8.3f..%8.3f   (%.3f x %.3f um)"
          % (NOFILL_MARGIN, nb.left, nb.right, nb.bottom, nb.top, nb.width(), nb.height()))
    print()
    return nb


NOFILL_BOX = common_exclusion(CELLS)

print("%-40s %-18s %-16s %-16s %s"
      % ("cell", "bbox", "l x w", "Activ to edge", "orientation labels"))
for name in CELLS:
    src = pya.Layout()
    src.read(os.path.join(DEV, name, name + ".gds"))
    sc = src.top_cell()
    bb = sc.dbbox()

    j = src.find_layer(1, 0)
    act = pya.Region() if j is None else pya.Region(sc.begin_shapes_rec(j)).merged()
    if act.is_empty():
        gap = "no Activ at all"
    else:
        ab = act.bbox().to_dtype(src.dbu)
        d = min(ab.left - bb.left, bb.right - ab.right,
                ab.bottom - bb.bottom, bb.top - ab.top)
        gap = "%.2f um" % d

    l = bb.width() + 2 * CLEAR + OPEN_MARGIN
    w = bb.height() + 2 * CLEAR + OPEN_MARGIN

    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name + "_sealring")
    inner = ly.create_cell(name)
    inner.copy_tree(sc)
    top.insert(pya.CellInstArray(inner.cell_index(), pya.Trans()))

    # The terminal labels are carried up to the sealed cell's own top level, and without them
    # deep-mode LVS fails. Deep extraction keeps the child cell as its own circuit, so a label
    # that sits inside the child names a net inside the child and nothing is exported upward:
    # the sealed circuit came out holding one unnamed seal-ring net while its schematic
    # declared IN, OUT and GND. Copying the TopMetal2 pin text to the parent names the same
    # three nets there and promotes the child's pins to match. Under flat extraction the
    # question never arose, because the whole tree collapsed into one circuit.
    #
    # Only layer 134/25 is copied. The Metal1 pin text on 8/25 names the base and collector
    # stubs, which are internal nets, and lifting those would export two pins the schematic
    # does not declare.
    # Which labels get carried up is decided by the cell's own symbol, because that is what
    # the schematic declares as pins. Carrying every label would be wrong: the Metal1 pin
    # text on 8/25 holds TI and TO on GSG_open and GSG_load and T on GSG_thru, all of which
    # are pins, but on the DUT cells the same layer holds B and C, which are internal nodes
    # between the launching fixture and the transistor. Lifting B and C would export two pins
    # the schematic does not have.
    symfile = os.path.join(DEV, name, name + ".sym")
    pins = set(re.findall(r"name=([A-Za-z0-9_!]+) dir=", io.open(symfile).read()))         if os.path.exists(symfile) else set()
    # (10, 25) as well since 2026-09-05: the view 2 tower ends on ground Metal1, so the
    # signal port label sits on Metal2.text. Without it the sealed copies lifted two
    # pins where the schematic declares three and LVS returned MISMATCH with every net,
    # pin and device otherwise matched.
    for lay in ((134, 25), (10, 25), (8, 25)):
        for sh in sc.each_shape(src.layer(*lay)):
            if sh.is_text() and sh.text.string in pins:
                top.shapes(ly.layer(*lay)).insert(sh.text)

    D = {p.name: p.default for p in decl.get_parameters()}
    D.update({"l": "%.3fu" % l, "w": "%.3fu" % w})
    rx = bb.left - CLEAR - INNER_OFF
    ry = bb.bottom - CLEAR - INNER_OFF
    # The PCell variant is turned into a static cell before it is placed. A PCell proxy
    # regenerates itself from its parameters, so shapes written into one do not survive, and
    # the corner squaring below writes into exactly those shapes.
    ringidx = ly.convert_cell_to_static(ly.add_pcell_variant(lib, pid, D))
    top.insert(pya.CellInstArray(ringidx,
                                 pya.Trans(pya.Trans.R0, int(round(rx * 1000)),
                                           int(round(ry * 1000)))))

    # --- orientation mark one: the TopMetal2 label in the band round the cell -------------
    # The band runs from the cell's own edge to the ring's TopMetal2 hole, 26.00 um on this
    # geometry. GAP_CELL comes off the inner side for TM2.bR, which asks 5.00 um from wide
    # TopMetal2, and GAP_RING off the outer side for TM2.b at 2.00 um. The first line goes
    # above the cell and the second below it, so both read the same way up and the pair says
    # which way up the cell is even when only one edge is in view.
    hole = pya.Region(top.begin_shapes_rec(ly.layer(*TM2))).merged().holes().bbox()
    hole = hole.to_dtype(ly.dbu)
    lines = label_lines(name)
    room = (hole.top - bb.top) - L.GAP_CELL - L.GAP_RING
    if L.text_size(lines[0])[1] > room:
        raise SystemExit("%s: label is %.2f um tall and the band leaves %.2f"
                         % (name, L.text_size(lines[0])[1], room))
    marks = []
    for line, side in zip(lines, (+1, -1)):
        lw, lh = L.text_size(line)
        x0 = bb.left + (bb.width() - lw) / 2.0
        y0 = (bb.top + L.GAP_CELL) if side > 0 else (bb.bottom - L.GAP_CELL - lh)
        reg, fixed = L.text_region(line, x0, y0)
        L.check_label(reg, "%s %r" % (name, line))
        top.shapes(ly.layer(*TM2)).insert(reg)
        marks.append("%s %.1fx%.1f" % (line, lw, lh))

    # --- orientation mark: I over the input G pad and O over the output G pad --------------
    # Owner instruction 2026-09-13. The input is always the left side in x: every DUT netlist
    # reads RR1 IN B and RR2 OUT C, so IN reaches the base and OUT the collector, and all 16
    # instances sit in the top cell at rotation 0 with no mirroring, so left is input on the
    # chip as well as inside the cell.
    #
    # The x centres are the upper G pad openings themselves, measured on Passiv 9/0 as 40.000
    # and 210.000, so each letter lands over the middle of the pad the prober is looking at.
    # The y is the same band and the same height as the name plate above, which keeps one
    # clearance calculation rather than two.
    for letter, xc in (("I", G_PAD_IN_X), ("O", G_PAD_OUT_X)):
        lw, lh = L.text_size(letter)
        reg, _ = L.text_region(letter, bb.left + xc - lw / 2.0, bb.top + L.GAP_CELL)
        L.check_label(reg, "%s %r" % (name, letter))
        top.shapes(ly.layer(*TM2)).insert(reg)
        marks.append("%s at x=%.3f" % (letter, xc))

    # --- every corner of the ring squared -------------------------------------------------
    # Until 2026-09-13 three corners were squared and the top-left kept the PCell's staircase,
    # so that the odd corner said which way the cell faced. That mark is withdrawn on the
    # owner's instruction, and the reason is that it had stopped being reliable: measured over
    # all 29 sealring cells, 16 carried the staircase at the top-left as intended while 13
    # carried the exact inverse, square at the top-left and stepped at the other three. The
    # direction is now said by the I and O letters below, which cannot be built inside out.
    L.square_corner(ly, ly.cell(ringidx), corners=L.ALL_CORNERS)

    # --- no filler over the signal path or the transistor, and only there -------------------
    # Owner instruction 2026-09-14, widening what 2026-09-08 drew. The rectangle used to cover
    # the signal alone, which came out 0.000..250.000 by -25.000..25.000, and the transistor of
    # four cells stuck out of it: Nx48 by 21.825 um above and below, Nx39 by 13.500, Nx32 by
    # 7.025 and the npn13G2L Nx17 by 1.300. The three conditions the owner set are that this
    # rectangle be the same in all 16 cells, that it be a rectangle, and that it contain the
    # transistor, and the third was not being met.
    #
    # The rectangle is now measured once over the whole list, before this loop starts, so every
    # cell gets the identical one. Each cell is still tested against it here, because this is
    # the only place that knows which cell is being written and a cell that did not fit would
    # otherwise be written out silently wrong.
    #
    # inner is instanced with an identity transform, so the source cell's coordinates are the
    # sealed cell's and no offset enters.
    nb = NOFILL_BOX
    for what, b in zip(("signal", "transistor"), signal_and_device(name)):
        if b is None:
            continue
        if not (nb.left <= b.left and nb.right >= b.right
                and nb.bottom <= b.bottom and nb.top >= b.top):
            raise SystemExit("%s: the %s runs x %.3f..%.3f y %.3f..%.3f, which the exclusion "
                             "x %.3f..%.3f y %.3f..%.3f does not contain"
                             % (name, what, b.left, b.right, b.bottom, b.top,
                                nb.left, nb.right, nb.bottom, nb.top))
    for lay in NOFILL:
        top.shapes(ly.layer(*lay)).insert(
            pya.Box(int(round(nb.left * 1000)), int(round(nb.bottom * 1000)),
                    int(round(nb.right * 1000)), int(round(nb.top * 1000))))

    folder = os.path.join(DEV, name + "_sealring")
    os.makedirs(folder, exist_ok=True)
    ly.write(os.path.join(folder, name + "_sealring.gds"))
    print("%-40s %-18s %-16s %-16s %s"
          % (name, "%.2f x %.2f" % (bb.width(), bb.height()),
             "%.2f x %.2f" % (l, w), gap,
             " | ".join(marks) + "  nofill %.1f x %.1f" % (nb.width(), nb.height())))
