"""The frame every GSG parent shares: two launch leaves, and ground carried across the slot.

Pulled out of gen_gsg_parents.py so the DUT cells can use the same frame instead of a
second copy of it. The ground bridge, the slit pattern and the via fence are the parts most
likely to need a correction later, and having them in two files would mean fixing them
twice or, worse, once.

The frame is two instances of the launch leaf, the second mirrored about x = 195, giving

    input launch   x   0..180
    DUT slot       x 180..210
    output launch  x 210..390

and the ground bridged across the slot so the two ports share a return path. Where that
bridge starts in y is the one thing a caller changes: OPEN, SHORT and THRU can take it
right down to the coplanar edge at 19.5 um, while a DUT has a device column in the way and
has to push it outward.
"""
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
LEAF = "G1SG2_pitch100u_lvsres_lauching_metal_cwpg_via_fence"
U = 1000.0

# The leaf shortened from 180.00 to 110.00 on 2026-09-02, owner instruction. The launching
# TopMetal2 measured 106.40 from the right edge of dfpad at x 80.00 to where the fixture ends
# its TopMetal2; taking 70.00 off leaves 36.40. A shorter signal run leaves less parasitic
# behind that de-embedding cannot reach, which matters when the structure is used in a hybrid.
LEAF_W = 110.0
SLOT = 30.0
TOTAL = LEAF_W * 2 + SLOT      # 250
X0, X1 = LEAF_W, LEAF_W + SLOT # the slot, x 110..140
XC = (X0 + X1) / 2.0           # 125

SIG_W = 19.0
GAP = 10.0
GI = SIG_W / 2 + GAP           # 19.5
Y_OUT = 130.0

SLIT = 7.0
SLIT_GRID = 15.0
CORRIDOR = 14.0
SLIT_ENC = 1.5
SLIT_VIA = 1.2
VIA_PITCH = 5.0

TM2, TM2_TXT = (134, 0), (134, 25)
M1, M2, DFPAD = (8, 0), (10, 0), (41, 0)
M1_TXT = (8, 25)               # LVS reads net names from <layer>/25

# The launching fixture, fixed across all five standards. See Frame.fixture.
# Written relative to the slot edge rather than as absolute numbers, so that shortening the
# leaf carries the fixture with it. They were 186.40, 183.40 and 189.40 when the slot began
# at 180.00, and the offsets from that edge are what actually matter.
FIX_TM2 = X0 + 6.40            # where TopMetal2 stops
FIX_STK = X0 + 3.40            # where the via stack starts
FIX_END = X0 + 9.40            # the end plane, and the edge the port label sits on
FIX_H = 19.00                  # height of the tower and of a standard's signal tip
                               # Owner instruction 2026-09-05: 3 by 19 in top view, 19
                               # being SIG_W, so the descent carries twice the vias it
                               # did at 10.00 and correspondingly less resistance.

# Per-layer via size and pitch for the fixture stack, and the inset from the metal edge.
# NOT the single 1.5 um pitch and 0.4 um inset that via_stack uses. Those are fine for the
# small vias but not for the top two: TopVia2 is 0.90 across and TV2.b asks 1.06 of space,
# so a 1.5 pitch leaves 0.60, and TV2.c/d ask 0.5 of enclosure where 0.4 was given. The
# first fixture build came back with TV1.d 16, TV2.b 10, TV2.c 14 and TV2.d 6 for exactly
# that. These numbers are the ones the DUT straps already use and pass on.
FIX_VIA = [((19, 0), 0.19, 0.6), ((29, 0), 0.19, 0.6), ((49, 0), 0.19, 0.6),
           ((66, 0), 0.19, 0.6), ((125, 0), 0.42, 1.2), ((133, 0), 0.90, 2.2)]
FIX_INSET = 0.8

# --- view 2: the descent tower, the backing ground and the signal tip -------------------------
# Owner instruction 2026-09-05. The tower drops the signal from TopMetal2 to Metal2 in one
# vertical stack; Via1 is deliberately absent, because the Metal1 under the tower is the cpwg
# backing ground and a Via1 there would short the signal to it.
TOWER_W = 3.00
TOWER_MET = [TM2, (126, 0), (67, 0), (50, 0), (30, 0), M2]
TOWER_VIA = [((133, 0), 0.90, 2.2), ((125, 0), 0.42, 1.2), ((66, 0), 0.19, 0.6),
             ((49, 0), 0.19, 0.6), ((29, 0), 0.19, 0.6)]

# d1 in the owner's figures: the clearance from the guard ring Metal1 to the signal tip. M1.b
# alone would allow 0.18, but the ground Metal1 beside the tip is far wider than the 0.30 that
# M1.e keys on and the two run parallel for the whole device length, so 0.22 governs.
D1 = 0.22
# The slot that keeps a narrow band of ground against the tip. 0.60 is M1.f, which is
# what the band has to keep from the wide fill behind it; 1.00 is how far the slot
# runs past each end of the tip, so the junction where band and fill meet again is
# too short a parallel run for M1.f to key on.
M1_SLOT, M1_SLOT_OVER = 0.60, 1.00
# 0.05 and not 0.01. V1.c asks 0.01 on the sides of a via but M1.c1 and M2.c1 ask 0.05 at
# an endcap, and the first build inset by 0.01 all round and reported M2.c1 184 times.
TIP_VIA, TIP_VIA_SP, TIP_ENC = 0.19, 0.22, 0.05     # V1.a, V1.b, M1.c1 and M2.c1
RING_CT, RING_CT_SP, RING_CT_ENC = 0.16, 0.18, 0.07  # Cnt.a, Cnt.b, Cnt.c

# The npn13G2 reference, measured on the built cell and cross-checked two ways. A de-embedding
# standard has no device, so it takes these: the owner chose npn13G2 as the constraint on the
# common dimensions because its emitter is the narrowest of the three flavours.
#
# The guard ring Activ of npn13G2 runs x 121.645..128.355 outer with a 0.500 um band, so the hole
# is 122.145..127.855. Its terminal Metal1 reaches 123.515 on the input side and 126.235 on the
# output side, which leaves the 1.370 and 1.620 um of room measured on the bare PCell.
REF_HOLE = (122.145, 127.855)
# REF_D1 is 0.60 and not D1. M1.f asks 0.60 once a line is wider than 10.0 um and the two
# run parallel for more than 10.0, and a standard has no guard ring band to break up the
# wide edge of its ground fill the way a DUT does, so the rule fires there at 0.22. The
# DUTs cannot use 0.60: it would leave a 0.150 um tip where Via1 needs 0.21.
REF_D1 = 0.60
REF_TIP = ((REF_HOLE[0] + REF_D1, 123.515), (126.235, REF_HOLE[1] - REF_D1))

# Pad centres, measured from the passivation openings rather than assumed.
PAD_X, PAD_Y = 40.0, 100.0

# Emitter increments from drawn to final, per flavour, and they are NOT the same for all
# three. IHP's dut_setup.htm gives npn13G2 an Area (final) of 0.1152 um2 per cell, which is
# 0.12 x 0.96, so its drawn 0.07 x 0.90 grows +0.050 in width and +0.060 in length. Reading
# the same documents' area slopes for the other two gives the increments the other way round,
# +0.060 in width and +0.050 in length: npn13G2L goes 0.07 -> 0.130 and npn13G2V 0.12 ->
# 0.180. IHP does not say why the pair is transposed for npn13G2, so this is the table read
# back and not a rule anyone has written down; wiki/components/sg13g2-device-geometries.md
# carries the working and the open question.
TEXT_DRW = (63, 0)
DELTA = {"npn13G2": (0.050, 0.060), "npn13G2L": (0.060, 0.050),
         "npn13G2V": (0.060, 0.050)}


def area_lines(pcell, multi, nx, le, we):
    """The three annotation lines, holding only what the PCell does not already write.

    Each PCell already puts an Ae= string on TEXT.drawing carrying m, Nx, le and we, though
    inconsistently: npn13G2 writes Nx*m*we*le, npn13G2L writes Nx*m*le*we, and npn13G2V
    omits m altogether. None of the three evaluates the product, and none mentions the final
    area at all. The m in those strings is also always 1, because a multi-device cell here
    is multi instances rather than one instance with m set.

    So these lines give the two areas as numbers, with the multiplication spelled out so the
    cell-level m and Nx can be read off, and the increments that produced the final one.
    """
    dwe, dle = DELTA[pcell]
    return ["A_E(drawn) %d x %d x %.3f x %.3f = %.4f um2"
            % (multi, nx, we, le, multi * nx * we * le),
            "A_E(final) %d x %d x %.3f x %.3f = %.4f um2"
            % (multi, nx, we + dwe, le + dle, multi * nx * (we + dwe) * (le + dle)),
            "dWe +%.3f  dLe +%.3f" % (dwe, dle)]
SLIT_DT = {(8, 0): (8, 24), (10, 0): (10, 24), (30, 0): (30, 24), (50, 0): (50, 24),
           (67, 0): (67, 24), (126, 0): (126, 24), (134, 0): (134, 24)}
VIA = [((19, 0), 0.19), ((29, 0), 0.19), ((49, 0), 0.19), ((66, 0), 0.19),
       ((125, 0), 0.42), ((133, 0), 0.90)]
RAIL_MET = [(10, 0), (30, 0), (50, 0), (67, 0), (126, 0)]
STACK = [M1] + RAIL_MET + [TM2]


# --- the emitter strap, shared by the DUTs and by the four de-embedding standards -------------
# Owner instruction 2026-09-05. It used to live in gen_gsg_duts.py, which meant the standards
# could not have it without a second copy of the code.
#
# EM_REF is the npn13G2 emitter Metal2, x 123.990 to 125.545, measured on the built cell. It is
# the narrowest of the three flavours, and the owner chose it as the common reference: a
# standard has no device to take a width from, so it takes this one.
EM_REF = (123.990, 125.545)
EM_UP = [((29, 0), (30, 0)),        # Via2 -> Metal3
         ((49, 0), (50, 0)),        # Via3 -> Metal4
         ((66, 0), (67, 0))]        # Via4 -> Metal5
EM_W = 0.20                 # M*.a, and the floor for a strap whose device is narrower
EM_VIA = 0.19               # V*.a
EM_VIA_SP = 0.22            # V*.b
EM_VIA_SP_B1 = 0.29         # V*.b1, once the array passes EM_B1_N in rows AND in columns
EM_B1_N = 3
EM_ENC = 0.05               # M*.c1, the endcap at the two ends of the strap
EM_ENC_SIDE = 0.005         # V*.c, the metal a via needs on its side
EM_COLS = 3                 # owner instruction 2026-09-05, down from 5
EM_GRID = 0.005             # the manufacturing grid, stated by 3_1_offgrid.drc itself:
                            # all features are on a drawing grid of 5 nm


def emitter_strap(f, x0, x1, yg):
    """Draw the emitter strap on Metal2 to Metal5 across the slot, with its via array.

    x0 and x1 are the Metal2 edges the strap takes verbatim, so the four layers stack with no
    offset and no rounding of their own. A device whose emitter Metal2 came out under the 0.20 um
    of M*.a would break that rule, so that case falls back to a centred minimum-width strap.

    The strap runs the full -yg to +yg, butting the ground bridge at both ends exactly where
    Frame.ground_bridge starts every layer of the stack. It carries no Metal1 and no Via1, and
    that is not an omission: in GSG_thru the Metal1 across the slot is net T and in GSG_load the
    Metal1 pieces are the resistor terminals, so Metal1 here would short T to ground in the one
    and short the resistor out in the other.

    Returns (ncol, nrow, width) so the caller can print what it got rather than assume it.
    """
    # Rounded to the 5 nm MANUFACTURING grid, not to the 1 nm database grid. It was rounded
    # to 1 nm until 2026-09-08, and on npn13G2 the emitter Metal2 runs 123.990 to 125.545,
    # so the true centre 124.7675 became 124.768, which is 3 nm off. Every via column is
    # placed from xc, so all of them were off, and the four standards inherited it by taking
    # npn13G2 as their common-dimension reference. The assembled top reported 14,628 markers
    # on each of via2, via3 and via4, and the DRC summary never showed them because its
    # pattern skipped rule names without a dot.
    #
    # Only xc needs this. vx0 subtracts (410(ncol-1) + 190)/2 nm and vy0 subtracts
    # (410(nvia-1) + 190)/2 nm, and both are exact multiples of 5 nm for any count, so the
    # columns follow xc and the rows were already on grid.
    xc = round(((x0 + x1) / 2.0) / EM_GRID) * EM_GRID
    if x1 - x0 >= EM_W:
        sx0, sx1 = x0, x1
    else:
        sx0, sx1 = xc - EM_W / 2.0, xc + EM_W / 2.0

    # How many columns fit, and at what spacing. The two answers depend on each other, because
    # a fourth column puts the array past V*.b1 in columns while it is already far past it in
    # rows, and the spacing of the whole array then jumps to 0.29. Widening can therefore make
    # an array that no longer fits, so each candidate count is tested against its own spacing.
    #
    # The allowance is a grid allowance, not slop: xc is the centre rounded to the 5 nm
    # manufacturing grid, so the array can sit up to 2.5 nm off centre and one side
    # enclosure comes out that much thinner than the other. At three columns the array is
    # 1.01 um across against the 1.555 um npn13G2 strap, so each side keeps about 0.270 um
    # against the 0.005 um of V*.c, and the narrow fallback derives its own edges from xc so
    # both move together and its 0.005 is exact.
    room = (sx1 - sx0) - 2.0 * EM_ENC_SIDE - EM_GRID
    ncol, via_sp = 1, EM_VIA_SP
    for n in range(1, EM_COLS + 1):
        sp = EM_VIA_SP_B1 if n > EM_B1_N else EM_VIA_SP
        if n * EM_VIA + (n - 1) * sp <= room + 1e-9:
            ncol, via_sp = n, sp

    via_pitch = EM_VIA + via_sp
    nvia = int((2.0 * yg - 2.0 * EM_ENC - EM_VIA) / via_pitch) + 1
    vy0 = -((nvia - 1) * via_pitch + EM_VIA) / 2.0
    vx0 = xc - ((ncol - 1) * via_pitch + EM_VIA) / 2.0
    f.put(M2, sx0, -yg, sx1, yg)
    for via, met in EM_UP:
        f.put(met, sx0, -yg, sx1, yg)
        for j in range(ncol):
            x = vx0 + j * via_pitch
            for k in range(nvia):
                y = vy0 + k * via_pitch
                f.put(via, x, y, x + EM_VIA, y + EM_VIA)
    return ncol, nvia, sx1 - sx0


class Frame(object):
    """Two launch leaves plus the ground bridge, with helpers for drawing into the slot."""

    def __init__(self, name, yg=GI, indent=0.0):
        """indent moves BOTH launches inward by that much, pads and all.

        It exists for THRU, which is the one standard whose two sides meet at the centre
        rather than at the end plane 5.60 um short of it. Left alone its launch would be
        5.60 um longer than every other standard's, and the owner's sketch of 2026-09-02
        compensates by indenting it at the outer end.

        The whole leaf has to move, not just the signal trace. Measured on the leaf, the
        signal TopMetal2 is one piece from x 0 to 180 and the passivation opening that the
        probe lands in starts at x 2.10, so cutting 5.60 um off the trace would take metal
        out from under the probe window. Moving the leaf takes the pad with it, which keeps
        the three probe tips on one line and simply shifts where they land.

        The cost is that this cell is narrower than the others, since the outer 5.60 um at
        each end is now empty, and its slot narrows by twice the indent. Neither matters for
        a standard with no device in the slot, and the length that does matter is equal:
        pad centre to meeting point is 195.00 - 45.60 = 149.40, the same as OPEN's pad centre
        to end plane, 189.40 - 40.00.
        """
        self.name = name
        self.yg = yg                 # ground bridge inner edge inside the slot
        self.ind = indent
        self.x0 = X0 + indent        # the slot, after any indent
        self.x1 = X1 - indent
        self.ly = pya.Layout()
        self.ly.dbu = 0.001
        self.top = self.ly.create_cell(name)

        src = pya.Layout()
        src.read(os.path.join(PROJECT, "designlib", "teg", LEAF, LEAF + ".gds"))
        leaf = self.ly.create_cell(LEAF)
        leaf.copy_tree(src.top_cell())
        # The leaf carries S1, T1 and GND. Instanced twice that would put two nets called
        # T1 in one cell, so the parent names its own nets and the leaf's labels go.
        leaf.clear(self.L(TM2_TXT))
        self.top.insert(pya.CellInstArray(
            leaf.cell_index(), pya.Trans(pya.Trans.R0, int(round(indent * U)), 0)))
        self.top.insert(pya.CellInstArray(leaf.cell_index(),
                                          pya.Trans(pya.Trans.M90,
                                                    int(round((TOTAL - indent) * U)), 0)))

    # -- primitives ---------------------------------------------------------------
    def L(self, spec):
        return self.ly.layer(*spec)

    def dbox(self, x0, y0, x1, y1):
        return pya.Box(int(round(x0 * U)), int(round(y0 * U)),
                       int(round(x1 * U)), int(round(y1 * U)))

    def put(self, spec, x0, y0, x1, y1):
        self.top.shapes(self.L(spec)).insert(self.dbox(x0, y0, x1, y1))

    def region(self, spec):
        return pya.Region(self.top.begin_shapes_rec(self.L(spec)))

    def label(self, text, x, y, spec=TM2_TXT):
        self.top.shapes(self.L(spec)).insert(
            pya.DText(text, pya.DTrans(pya.DVector(x, y))))

    # -- the signal launching fixture ----------------------------------------------
    def fixture(self, x_in_i, x_in_o, name_in="TIN", name_out="TOUT"):
        """Draw the launch and its descent tower, and return where the signal ends on Metal2.

        Owner instruction 2026-09-05, the view 2 arrangement. The signal stays on TopMetal2 until
        x_in_i on the input side and x_in_o on the output side, and drops there through a tower
        3.00 um in x by FIX_H in y, carrying TopVia2, TopVia1, Via4, Via3 and Via2. Via1 is not
        in the tower: the Metal1 beneath it is the cpwg backing ground, so a Via1 would short the
        signal into it. The one Via1 per side lives in the tip, inside the guard ring.

        This replaces the fixed 3.00 by 10.00 tower that used to sit at x 113.40..116.40 and hand
        the signal to a Metal1 run reaching the end plane at 119.40. Two things drove the change.
        The tower is taller, 19.00 instead of 10.00, so it holds nearly twice the vias. And it is
        pulled in to the terminal, so the signal spends its last micrometres on TopMetal2 at
        0.011 ohm per square rather than on Metal1 at 0.110.

        x_in_i and x_in_o are the callers, because they depend on the device: a wider device puts
        its terminal further out and shortens the TopMetal2 run, which is the L1 against L1' of
        the owner's second figure. The layer composition and the tower size do not depend on the
        device and are the same in all sixteen cells.

        The port label goes on Metal2.text rather than Metal1.text, because the Metal1 at the
        end of the tower is now ground. The deck declares metal2_text = labels(10, 25).
        """
        out = []
        for s_, pair, nm in ((+1, x_in_i, name_in), (-1, x_in_o, name_out)):
            x_in, x_m2 = pair
            edge = self.x0 if s_ > 0 else self.x1
            self.put(TM2, min(edge, x_in), -SIG_W / 2, max(edge, x_in), SIG_W / 2)
            a = x_in - TOWER_W if s_ > 0 else x_in
            b = x_in if s_ > 0 else x_in + TOWER_W
            # Metal2 alone runs on to the terminal; everything above it stops at the tip.
            # That is the owner's figure, where d4 exceeds d3, and it keeps TopMetal2 and
            # TopMetal1 about a micrometre further from the device than the Metal2 is.
            # Every tower layer over the same rectangle now. Metal2 used to be stretched on to
            # the terminal from here, which is where the tip gets its Metal2 in the owner's
            # figure, but the tip is taller than FIX_H and needs Metal2 over its whole height,
            # so the tip draws its own and the two abut at the tip outer edge.
            for spec in TOWER_MET:
                self.put(spec, a, -FIX_H / 2, b, FIX_H / 2)
            for spec, sz, pch in TOWER_VIA:
                gy = -FIX_H / 2 + FIX_INSET
                while gy + sz <= FIX_H / 2 - FIX_INSET + 1e-6:
                    gx = a + FIX_INSET
                    while gx + sz <= b - FIX_INSET + 1e-6:
                        self.put(spec, gx, gy, gx + sz, gy + sz)
                        gx += pch
                    gy += pch
            self.label(nm, (a + b) / 2.0, 0.0, (10, 25))
            out.append(x_m2)
        return out[0], out[1]

    def backing_ground(self, holes, slots=()):
        """Fill the ground band on Metal1 and take only the guard ring holes out of it.

        This one fill is three things the owner asked for at once. It is the cpwg backing ground
        outboard of the ring. It is the guard ring Metal1, because the ring band lies between the
        ring outer edge and the ring hole, so filling everything and subtracting the hole leaves
        the band filled. And it is the join between them, in x and in y both, because the band is
        part of the same polygon as the ground around it.

        holes is the list of ring holes in micrometres, one per device, as (x0, y0, x1, y1). What
        stays inside a hole is the PCell's own terminals and emitter plus the signal tip, and the
        tip keeps D1 of clearance because it starts D1 inside the hole edge.
        """
        band = pya.Region(self.dbox(self.x0, -self.yg, self.x1, self.yg))
        for h in holes:
            band -= pya.Region(self.dbox(*h))
        # The slots keep a narrow strip of ground against each tip. Without them the fill puts a
        # wide straight edge at d1 and M1.f asks 0.60 there, which d1 cannot give: 0.60 in a DUT
        # would leave a 0.150 um tip where Via1 needs 0.21. A narrow strip is deleted by the
        # 5.0 um opening the rule performs first, so the wide metal it measures against is the
        # fill on the far side of the slot.
        for sl in slots:
            band -= pya.Region(self.dbox(*sl))
        self.top.shapes(self.L(M1)).insert(band)
        return band.area() / (U * U)

    def ring_contacts(self, rings):
        """Contact the substrate guard ring on all four of its bands.

        All four, not the two the earlier tie_substrate_ring could reach. That routine had to
        leave the bands running along y bare because the base and collector Metal1 straps crossed
        them on their way to the terminals; in view 2 the signal crosses on Metal2 and above, so
        nothing on Metal1 crosses the ring any more.

        rings is a list of (out, hole) box pairs in micrometres. Contacts are 0.16 um square on a
        0.34 um pitch, centred in the band, which leaves 0.170 um of Activ on each side against
        the 0.07 of Cnt.c. One row per band, so Cnt.b1 does not apply.
        """
        n = 0
        for (ox0, oy0, ox1, oy1), (hx0, hy0, hx1, hy1) in rings:
            bw = hx0 - ox0
            if bw < RING_CT + 2 * RING_CT_ENC:
                raise SystemExit("guard ring band is %.3f um, too narrow for a %.2f contact"
                                 % (bw, RING_CT))
            off = (bw - RING_CT) / 2.0
            # The two runs along x stop one band width short at each end so that the four
            # corners belong to the runs along y alone. Sweeping all four runs end to end wrote
            # the corner squares twice, and two 0.16 squares merging into an L stop being
            # Cont_SQ, which is Cont.ext_rectangles with both sides exactly 0.16; the deck then
            # calls them ContBar and CntB.a, CntB.a1, CntB.b2 and Cnt.b all fire together.
            inset = bw + RING_CT_SP
            runs = [(ox0 + inset, oy0 + off, ox1 - inset, oy0 + off, +1, 0),
                    (ox0 + inset, oy1 - off - RING_CT, ox1 - inset, 0, +1, 0),
                    (ox0 + off, oy0 + RING_CT_ENC, 0, oy1 - RING_CT_ENC, 0, +1),
                    (ox1 - off - RING_CT, oy0 + RING_CT_ENC, 0, oy1 - RING_CT_ENC, 0, +1)]
            for r in runs:
                if r[4]:
                    x, y, xe = r[0], r[1], r[2]
                    while x + RING_CT <= xe + 1e-6:
                        self.put((6, 0), x, y, x + RING_CT, y + RING_CT)
                        x += RING_CT + RING_CT_SP
                        n += 1
                else:
                    x, y, ye = r[0], r[1], r[3]
                    while y + RING_CT <= ye + 1e-6:
                        self.put((6, 0), x, y, x + RING_CT, y + RING_CT)
                        y += RING_CT + RING_CT_SP
                        n += 1
        return n

    def tip(self, x0, x1, y0, y1):
        """The one piece of signal Metal1, inside the guard ring, with its Via1 column.

        It butts the terminal with no overlap, on the owner's instruction, and keeps D1 from the
        ring Metal1 on the other side. The tower Metal2 above covers it, so this is the only
        place the signal changes layer below Metal2.
        """
        # Metal1 AND Metal2, over the same rectangle. The tip is as tall as the terminal it
        # butts, which on npn13G2 Nx48 is 93 um, while the Metal2 coming off the tower is FIX_H
        # tall and no more. Taking the Metal2 from the tower left every Via1 outside that band
        # with nothing above it, which is what made ten of sixteen cells fail LVS on the first
        # view 2 build. The tip joins the tower by abutting it on Metal2 at x0.
        self.put(M1, x0, y0, x1, y1)
        self.put(M2, x0, y0, x1, y1)
        room = (x1 - x0) - 2 * TIP_ENC
        ncol = 1
        while (ncol + 1) * TIP_VIA + ncol * TIP_VIA_SP <= room + 1e-9:
            ncol += 1
        pch = TIP_VIA + TIP_VIA_SP
        vx0 = (x0 + x1) / 2.0 - ((ncol - 1) * pch + TIP_VIA) / 2.0
        vx0 = round(vx0 * 1000.0) / 1000.0
        span = (y1 - y0) - 2 * TIP_ENC - TIP_VIA
        nrow = int(span / pch) + 1
        vy0 = (y0 + y1) / 2.0 - ((nrow - 1) * pch + TIP_VIA) / 2.0
        vy0 = round(vy0 * 1000.0) / 1000.0
        for j in range(ncol):
            for k in range(nrow):
                self.put((19, 0), vx0 + j * pch, vy0 + k * pch,
                         vx0 + j * pch + TIP_VIA, vy0 + k * pch + TIP_VIA)
        return ncol, nrow


    def pad_labels(self, sig_in="IN", sig_out="OUT", gnd="GND"):
        """Name every pad at its own dead centre, which is the owner's internal-port rule.

        Measured from the passivation openings, the six centres are (40, 0), (40, +/-100)
        and their mirrors at x = 350. The previous labelling put GND at (20, 100), which is
        neither a pad centre nor on more than one of the four ground pads.
        """
        for x, nm in ((PAD_X + self.ind, sig_in),
                      (TOTAL - PAD_X - self.ind, sig_out)):
            self.label(nm, x, 0.0)
        for x in (PAD_X + self.ind, TOTAL - PAD_X - self.ind):
            for y in (PAD_Y, -PAD_Y):
                self.label(gnd, x, y)

    def via_stack(self, x0, y0, x1, y1, layers=None, pitch=1.5):
        """Fill a window with a via stack and the metal patches that carry it.

        Every via size here is fixed by the rules as both a minimum and a maximum, so the
        only freedom is how many and where. They go on a grid inside the window with the
        patches drawn to the window, which gives each via far more enclosure than the
        0.01 um V1.c asks for.
        """
        for spec in (layers or STACK):
            self.put(spec, x0, y0, x1, y1)
        n = 0
        for spec, sz in VIA:
            gy = y0 + 0.4
            while gy + sz + 0.4 <= y1:
                gx = x0 + 0.4
                while gx + sz + 0.4 <= x1:
                    self.put(spec, gx, gy, gx + sz, gy + sz)
                    gx += pitch
                    n += 1
                gy += pitch
        return n

    # -- the ground bridge, then slits and fence over whatever got drawn ------------
    def ground_bridge(self):
        for s in (+1, -1):
            lo, hi = sorted((s * self.yg, s * Y_OUT))
            for spec in STACK:
                self.put(spec, self.x0, lo, self.x1, hi)
        # Remember the bridge as it stands now, before a caller draws anything else into
        # the slot. finish() fills this and only this with the via fence.
        #
        # Capturing it here rather than re-reading TopMetal1 at finish() time is not a
        # tidiness point. A DUT puts its own via stacks in the slot, and those stacks carry
        # TopMetal1; re-reading the layer would let the 5 um fence grid treat them as rail
        # and drop its own vias on top of theirs. That produced 8 counts each of V1.b
        # through V4.b, plus TV1.b, TV2.a and TV2.b, on the first npn13G2V build. The
        # four-device cell escaped it only because its stack happened to fall between two
        # grid points.
        self.bridge = self.region((126, 0)).merged()

    def finish(self, labels):
        dfpad_keep = self.region(DFPAD).merged().sized(int(1.0 * U))

        cands = []
        k = 0
        while True:
            cx = SLIT_GRID / 2.0 + SLIT_GRID * k
            if cx + SLIT > TOTAL:
                break
            if self.x0 - SLIT_GRID <= cx and cx + SLIT <= self.x1 + SLIT_GRID:
                j = 0
                while CORRIDOR + SLIT_GRID * j + SLIT <= Y_OUT:
                    b = CORRIDOR + SLIT_GRID * j
                    cands.append((cx, b, cx + SLIT, b + SLIT))
                    cands.append((cx, -b - SLIT, cx + SLIT, -b))
                    j += 1
            k += 1

        n_slit = 0
        for spec, slit_spec in SLIT_DT.items():
            inner = self.region(spec).merged().sized(-int(SLIT_ENC * U))
            if inner.is_empty():
                continue
            for (a, b, c, d) in cands:
                r = pya.Region(self.dbox(a, b, c, d))
                if r.inside(inner).count() != 1 or r.interacting(dfpad_keep).count():
                    continue
                self.top.shapes(self.L(slit_spec)).insert(self.dbox(a, b, c, d))
                n_slit += 1

        keep = pya.Region([self.dbox(a - SLIT_VIA, b - SLIT_VIA, c + SLIT_VIA, d + SLIT_VIA)
                           for (a, b, c, d) in cands]).merged()
        rails = getattr(self, "bridge", None)
        if rails is None:
            rails = self.region((126, 0)).merged()

        n_via = 0
        gx = self.x0
        while gx <= self.x1:
            gy = -Y_OUT
            while gy <= Y_OUT:
                span = pya.Region(self.dbox(gx, gy, gx + 0.90, gy + 0.90))
                if (span.sized(int(0.5 * U)).inside(rails).count() == 1
                        and span.interacting(keep).count() == 0):
                    for spec, sz in VIA:
                        self.put(spec, gx, gy, gx + sz, gy + sz)
                    n_via += 1
                gy += VIA_PITCH
            gx += VIA_PITCH

        for text, tx, ty in labels:
            self.label(text, tx, ty)

        folder = os.path.join(PROJECT, "designlib", "teg", self.name)
        os.makedirs(folder, exist_ok=True)
        out = os.path.join(folder, self.name + ".gds")
        self.ly.write(out)
        bb = self.top.bbox()
        print("%-34s bbox %7.2f x %-7.2f  ground from |y|=%-6.1f  slits +%-3d vias +%d"
              % (self.name, bb.width() * self.ly.dbu, bb.height() * self.ly.dbu,
                 self.yg, n_slit, n_via))
        return out
