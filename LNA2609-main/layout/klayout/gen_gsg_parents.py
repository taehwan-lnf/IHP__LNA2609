"""Build the de-embedding standards: GSG_open, GSG_short, GSG_thru and GSG_load.

Rebuilt on the owner's sketches of 2026-09-02. The change of principle is that the signal
launching fixture, meaning both its metal-layer composition and its length, is now FIXED
across dut, open, short, thru and load, and lives in gsg_frame.Frame.fixture. Only what sits
between its two end planes differs, and that is the whole content of this file:

    OPEN    nothing between them
    SHORT   the whole slot taken to the coplanar ground, so both end planes are on
            ground rather than on each other
    THRU    the two end planes joined on Metal1, which is the layer the DUT crosses on
    LOAD    a 50 ohm rppd from each end plane to a central ground island

What the earlier THRU got wrong, and why it matters: it bridged the slot with TopMetal2
running unbroken from 140 to 250, while the DUT stops TopMetal2 at 186.40, drops through a
via stack and crosses on Metal1. So the THRU did not contain the DUT's via stack or its
Metal1 run, and subtracting it left both behind. Measured before the change:

    GSG_thru  TopMetal2 140.00..250.00 unbroken, Metal1 only 140..180 and 210..250
    GSG_dut   TopMetal2 140..186.40 and 203.60..250, then TopVia2, then Metal1

LOAD is new. Each port sees 50 ohm to ground, from rppd at w=10u l=1.655u. The length is not
the 1.92u a sheet-resistance calculation gives, because the PDK symbol's own value expression
carries a contact term as well as the sheet term:

    R = 70.0e-6 / w + 260.0 * l / (w + 6.0e-9)

which at w=10u is 7.00 ohm before any length at all. So 1.92u lands on 56.89 ohm and 1.655u
on 50.00 ohm. The 7 ohm was missed in the first proposal to the owner and is corrected here.

Each resistor is placed R90, because w runs along x in the drawn cell while current flows
along l. Rotated, one costs 3.14 um of the 11.20 um between the end planes, which leaves
room for the ground island between the two.

All four take the ground bridge down to the coplanar edge at 19.5 um, because nothing is in
the way. A DUT cannot, and passes its own value.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_frame as F

RPPD_W, RPPD_L = "10u", "1.655u"
ISLAND = 3.0        # half-width of the central ground island in SHORT and LOAD
PILLAR = 2.2        # width of each LOAD ground pillar, leaving a gap between the two
LOAD_ROOM = 4.00    # how much wider the LOAD cuts its ground hole, to seat the two rppd


ACTIV, PSD, CONT = (1, 0), (14, 0), (6, 0)
# The two pitches differ on purpose. Cnt.b asks 0.18 um between contacts and Cnt.b1 raises
# that to 0.20 um once an array has more than four rows AND more than four columns, in one
# direction only. A 0.34 um pitch on both axes leaves 0.18 um both ways and reported Cnt.b1
# twice; 0.36 um in y leaves 0.20 um there and satisfies it, while x keeps the tighter
# pitch and the denser tie.
TIE_PSD, TIE_CONT, TIE_SIZE = 0.20, 0.215, 0.16
TIE_PITCH_X, TIE_PITCH_Y = 0.34, 0.36


def substrate_tie(f, x0, y0, x1, y1):
    """Tie the p substrate to the ground plane with an Activ and pSD strip and its contacts.

    GSG_load is the only standard that needs this, and it needs it because rppd is extracted
    with three terminals rather than two: the two ends and the body it sits on. With nothing
    holding that body the extractor returns it on a net of its own, and the net is not local
    to the cell, because the substrate continues past the cell boundary. In the bare cell that
    is harmless, the net being internal to the only circuit there is. In the sealed cell the
    same net crosses into the parent and is promoted to a pin, so the sealed layout came back
    with four pins against the schematic's three and the compare failed on it.

    The strip is placed inside the coplanar ground Metal1, which is solid over
    x 115.00..135.00 and |y| 15.00..45.00, so no Metal1 of its own is needed and the tie joins
    the ground plane where it stands. The enclosures are copied from what the npn13G2 PCell
    draws for its own guard ring, measured on GSG_dut_npn13g2_m1_Nx8: pSD 0.200 um beyond
    Activ on every side and the contact row inset 0.215 um from the Activ edge.

    The DUT cells need nothing of the kind. Their guard ring already ties the substrate to
    ground, which is why the transistor's fourth terminal comes back as GND rather than as an
    unnamed net.
    """
    f.put(ACTIV, x0, y0, x1, y1)
    f.put(PSD, x0 - TIE_PSD, y0 - TIE_PSD, x1 + TIE_PSD, y1 + TIE_PSD)
    cx0, cx1 = x0 + TIE_CONT, x1 - TIE_CONT
    cy0, cy1 = y0 + TIE_CONT, y1 - TIE_CONT
    nx = int((cx1 - cx0 - TIE_SIZE) / TIE_PITCH_X) + 1
    ny = int((cy1 - cy0 - TIE_SIZE) / TIE_PITCH_Y) + 1
    bx = (cx0 + cx1 - ((nx - 1) * TIE_PITCH_X + TIE_SIZE)) / 2.0
    by = (cy0 + cy1 - ((ny - 1) * TIE_PITCH_Y + TIE_SIZE)) / 2.0
    for i in range(nx):
        for k in range(ny):
            x, y = bx + i * TIE_PITCH_X, by + k * TIE_PITCH_Y
            f.put(CONT, x, y, x + TIE_SIZE, y + TIE_SIZE)
    return nx * ny


def slot_ground(f, x0, x1):
    """Take a block in the slot up and down to the coplanar ground, on Metal1 alone.

    Metal1 alone, not TopMetal2 as well. The ground bridge carries Metal1 from |y| = 19.5
    outwards, so Metal1 reaches ground on its own, and adding TopMetal2 here would put metal
    in the slot that the other three standards do not have. A first attempt did exactly that
    and SHORT came back with TopMetal2 running to 189.40 while OPEN stopped at 186.40, which
    is the fixture no longer being identical.
    """
    f.put(F.M1, x0, -F.SIG_W / 2, x1, F.SIG_W / 2)
    for s in (+1, -1):
        lo, hi = sorted((s * F.SIG_W / 2, s * F.GI))
        f.put(F.M1, x0, lo, x1, hi)


def check_tie(f, x0, y0, x1, y1):
    """Confirm the tie lands on solid ground Metal1 and keeps 0.30 um from every Metal1 slit.

    Written as a check and not as a comment because the four standards do not share a ground
    layout: GSG_thru is 238.80 um wide where the others are 250.00. A tie that fell outside
    the ground plane would leave the substrate floating and a tie that came within 0.30 um of
    a slit marker would report Slt.h1, and both would be found only after a DRC run.
    """
    box = f.dbox(x0, y0, x1, y1)
    m1 = pya.Region(f.top.begin_shapes_rec(f.L(F.M1))).merged()
    if not (pya.Region(box) - m1).is_empty():
        raise SystemExit("substrate tie at %s is not covered by ground Metal1" % box)
    slit = pya.Region(f.top.begin_shapes_rec(f.L(F.SLIT_DT[F.M1]))).merged()
    near = slit.sized(int(round(0.30 * F.U))) & pya.Region(box)
    if not near.is_empty():
        raise SystemExit("substrate tie at %s is within 0.30 um of a Metal1 slit" % box)


def place_at(f, cid, target_x, side):
    """Put a PCell instance so that its outermost Metal1 terminal lands on target_x.

    The offsets are read back from the instance rather than written down. rppd placed R90
    spans x -2.53..0.61 about its origin today, but that is a PCell's business and not a
    contract, so the code measures where the terminals actually are and translates from
    there. side is +1 for the input resistor, whose outer terminal is its left edge, and -1
    for the output one.
    """
    # The Metal1 of the instance itself, taken from its own cell under the same R90 the
    # instance gets, and nothing else. The docstring has always said the outermost Metal1
    # terminal lands on target_x, and the Metal1 was always read here into a variable that was
    # then ignored while the bounding box was aligned instead. An rppd bbox is wider than its
    # heads, so on 2026-09-05 the head came to rest 0.180 um inside the tip it was meant to
    # butt, which is both M1.e and an open circuit.
    #
    # It must NOT be read off the top cell. backing_ground has already filled the ground band by
    # the time this runs, and that fill interacts with everything, so a first correction that
    # measured the top cell put the resistor at x -129.52.
    rot = pya.Trans(pya.Trans.R90, 0, 0)
    m1 = pya.Region(f.ly.cell(cid).begin_shapes_rec(f.L(F.M1))).transformed(rot)
    box = m1.bbox().to_dtype(f.ly.dbu)

    dx = target_x - (box.left if side > 0 else box.right)
    dy = -box.center().y
    return f.top.insert(pya.CellInstArray(
        cid, pya.Trans(pya.Trans.R90, int(round(dx * F.U)), int(round(dy * F.U)))))


# The edge port carries the name of the net it is actually on, which is not always TI and
# TO. In THRU the two end planes and the centre are one net, and in SHORT both end planes are
# ground. Labelling them TI and TO regardless put three names on one net and LVS came back
# with "T|TI|TO" against a schematic that declared T, which is a mismatch even though the
# connectivity was right.
EDGE = {"GSG_open": ("TI", "TO"), "GSG_short": ("GND", "GND"),
        "GSG_thru": ("T", "T"), "GSG_load": ("TI", "TO")}


# THRU is the one standard whose two sides meet at the centre rather than at the end plane
# 5.60 um short of it, so left alone its launch would be 5.60 um longer than everyone else's.
# The owner's sketch of 2026-09-02 compensates with an indent, and after seeing the built
# cell they chose that scheme on 2026-09-02: keep the sketch, restore the indent, and release
# the fixed-fixture rule for THRU alone.
#
# The indent moves the whole leaf, pads included, not just the signal trace. Measured on the
# leaf, the signal TopMetal2 is one piece from x 0 to 180 while the passivation opening the
# probe lands in starts at x 2.10, so shortening the trace by 5.60 would take metal out from
# under the probe window. Moving the leaf keeps the three tips on one line.
# No cell indents any more. The indent existed because the THRU's two end planes met at
# the centre while the others stopped 5.60 um short, and in view 2 the signal ends at the
# npn13G2 tip in every standard, so the four are the same width and nothing has to be
# compensated. Owner instruction 2026-09-05.
INDENT = {}


def build(kind):
    ind = INDENT.get(kind, 0.0)
    f = F.Frame(kind, yg=F.GI, indent=ind)
    f.ground_bridge()
    # A standard has no device, so it takes the npn13G2 tip positions, npn13G2 being the
    # flavour the owner made the constraint on the common dimensions. xi and xo come back as the
    # inner ends of the signal, which is where the four standards differ from one another.
    xi, xo = f.fixture((F.REF_TIP[0][0], F.REF_TIP[0][1]),
                       (F.REF_TIP[1][1], F.REF_TIP[1][0]), *EDGE[kind])

    # The same ground fill the DUTs get, with a hole where the tips and the kind-specific Metal1
    # live. The hole is D1 taller than the tips on each side so they do not touch the ground.
    # The LOAD alone cuts its hole wider, because its two rppd sit between the ground and the
    # tips and the instance spans about 3.14 um in x. The other three keep the DUT figure.
    grow = LOAD_ROOM if kind == "GSG_load" else 0.0
    gx0, gx1 = F.REF_HOLE[0] - grow, F.REF_HOLE[1] + grow
    f.backing_ground([(gx0, -(F.FIX_H / 2 + F.REF_D1), gx1, F.FIX_H / 2 + F.REF_D1)])
    tip_i = f.tip(F.REF_TIP[0][0], F.REF_TIP[0][1], -F.FIX_H / 2, F.FIX_H / 2)
    tip_o = f.tip(F.REF_TIP[1][0], F.REF_TIP[1][1], -F.FIX_H / 2, F.FIX_H / 2)
    print("    tips %d x %d and %d x %d" % (tip_i[0], tip_i[1], tip_o[0], tip_o[1]))

    if kind == "GSG_open":
        pass

    elif kind == "GSG_short":
        # The whole slot goes to the coplanar ground in one piece.
        #
        # It used to be two 3.00 um arms, one reaching inward from each end plane, with a
        # 5.20 um gap left between them. That gap came from over-reading the correction of
        # 2026-08-28, which said that taking the two end planes to EACH OTHER instead of to
        # ground makes a THRU. It did, and it does; but it never asked for the grounded region
        # to be broken. The owner pointed that out on 2026-09-04: what makes a THRU is the two
        # stubs shorting to one another WITHOUT meeting ground, and here both meet ground.
        #
        # The extracted netlists are the evidence. GSG_short lands both launches on GND while
        # GSG_thru lands both on T, a net that never touches ground, so metal added between two
        # already-grounded arms joins one net to itself and cannot change the netlist.
        #
        # Closing it is also the better standard. A SHORT is meant to present the lowest
        # impedance it can from the reference plane to ground, since open-short de-embedding
        # reads what is left as the lead's series term, and a slot down the middle of that
        # ground only adds inductance between the two shorts.
        slot_ground(f, xi, xo)

    elif kind == "GSG_thru":
        # With the indent applied the two end planes land on the centre together, so the two
        # Metal1 runs already butt there and nothing needs adding. The earlier build, without
        # the indent, filled the 11.20 um between the planes with a Metal1 rectangle, which
        # is what the owner spotted: the DUT taken out and a block put in its place.
        if abs(xo - xi) > 1e-6:
            f.put(F.M1, xi, -F.FIX_H / 2, xo, F.FIX_H / 2)

    elif kind == "GSG_load":
        lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
        liblay = lib.layout()
        D = {p.name: p.default for p in liblay.pcell_declaration("rppd").get_parameters()}
        # Calculate says which of R, l and w is the DERIVED one, and its default is "l",
        # meaning the length is computed from R. The PDK on WSL ignores the field and uses
        # the l it is given; the newer one on the Rocky VM honours it and rebuilds the body
        # at 15.630 um from the default R=397 instead of the 1.655 um that makes 50 ohm.
        # Saying "R" states what this code has always meant: w and l are the inputs.
        D.update({"w": RPPD_W, "l": RPPD_L, "Calculate": "R"})
        rid = f.ly.add_pcell_variant(lib, liblay.pcell_id("rppd"), D)

        # Both resistors go in R90 so the current runs along x, between the end planes.
        # Where they land is measured back from the instance rather than written down.
        ri = place_at(f, rid, F.REF_TIP[0][0], -1)
        ro = place_at(f, rid, F.REF_TIP[1][1], +1)
        bi = ri.bbox().to_dtype(f.ly.dbu)
        bo = ro.bbox().to_dtype(f.ly.dbu)

        # Each resistor sits OUTBOARD of its tip, between the cpwg backing ground and the
        # tip, on the owner's instruction of 2026-09-05 that it need not sit dead centre. Each
        # port therefore still sees a shunt load to ground, which is what this standard is for,
        # and the launch stays identical to the other three because nothing between the tips
        # changed. It had to move: view 2 pulls the tips in to the npn13G2 terminals, which
        # leaves 2.720 um between them against the 2.87 um one rppd instance needs.
        f.put(F.M1, gx0, -F.FIX_H / 2, bi.left + 0.6, F.FIX_H / 2)
        f.put(F.M1, bo.right - 0.6, -F.FIX_H / 2, gx1, F.FIX_H / 2)
        print("    rppd at x %.2f..%.2f and %.2f..%.2f, ground edges %.2f and %.2f"
              % (bi.left, bi.right, bo.left, bo.right, gx0, gx1))

    # Every standard gets the same pair of substrate ties, one above the slot and one below,
    # so the four stay symmetric about y = 0 and identical to one another. Two things ask for
    # this and they agree.
    #
    # The measurement reason is that the ten DUT cells tie their guard ring to the p substrate
    # and the standards did not, so the standards did not reproduce the DUT's ground-to-
    # substrate path and subtracting them left that path in the result. The de-embedding set
    # is only subtractive if the standard carries what the DUT carries.
    #
    # The extraction reason is what showed it. Assembled into the top cell, GSG_open and
    # GSG_thru came back with their sealed subcircuits stripped down to two pins, the ground
    # among the missing ones, because a net that carries no device anywhere in its subtree is
    # removed by the simplifier and its pins go with it. Their ground planes carried nothing.
    # Tied to the substrate they join the same net the transistors sit on, so they survive and
    # the fourteen instances compare pin for pin.
    #
    # The y band is 21.00..27.50 and not 23.00..29.00, which was the first attempt and
    # reported Slt.h1 thirty-eight times. Slt.h1 asks 0.30 um between a Metal1 slit and any
    # Cont, and the slit markers on 8/24 begin at y = 29.00 in rows 7.00 um deep, measured at
    # x 112.50..119.50 and 127.50..134.50. The tie stays below that first row, its topmost
    # contact edge landing at 27.285, which is 1.715 um clear. The metal itself is solid over
    # x 115.00..135.00 and |y| 15.00..45.00, the slits being markers and not holes, so the tie
    # meets the ground plane where it stands. Both claims are checked below rather than
    # trusted, because GSG_thru is 238.80 um wide against the others' 250.00 and its ground
    # need not be laid out the same way.
    # 21.06 and not 21.00. Measured on the first view 2 build, 38 of these contacts came
    # 0.290 um from a Metal1 slit marker where Slt.h1 asks 0.30, because the backing ground
    # fill enlarged the Metal1 the slit grid is laid on and a slit row now reaches y 21.000.
    # Moving the band out by 0.06 puts the first contact at 21.350.
    nc = substrate_tie(f, 118.0, 21.06, 132.0, 27.5)
    nc += substrate_tie(f, 118.0, -27.5, 132.0, -21.06)
    check_tie(f, 118.0, 21.06, 132.0, 27.5)
    check_tie(f, 118.0, -27.5, 132.0, -21.06)
    print("    substrate tie contacts %d" % nc)

    # --- the emitter strap, the same one the DUTs carry ------------------------------------
    # Owner instruction 2026-09-05. A de-embedding standard corrects only what it contains, and
    # every DUT carries this strap across the slot, so the four standards carry it too.
    #
    # It is drawn at the npn13G2 emitter Metal2 position because a standard has no device of its
    # own to take a width from, and npn13G2 is the narrowest of the three flavours, which the
    # owner took as the constraint on the common dimensions. The strap therefore matches npn13G2
    # exactly and is narrower than what npn13G2L and npn13G2V carry, 1.555 um against 2.900 and
    # 3.060; that mismatch is accepted rather than hidden, because one shared standard cannot
    # match three different devices at once.
    #
    # Metal2 upward only, never Metal1. In GSG_thru the Metal1 across the slot is net T and in
    # GSG_load the Metal1 pieces are the resistor terminals, so a strap on Metal1 would short T
    # to ground in the one and short the resistor out in the other. The strap is on GND, since
    # it butts the ground bridge at both ends.
    em_col, em_row, em_w = F.emitter_strap(f, F.EM_REF[0], F.EM_REF[1], f.yg)
    print("    emitter strap %.3f um wide, %d via column(s) x %d row(s)"
          % (em_w, em_col, em_row))

    f.pad_labels()
    f.finish([])


for kind in ("GSG_open", "GSG_short", "GSG_thru", "GSG_load"):
    build(kind)
