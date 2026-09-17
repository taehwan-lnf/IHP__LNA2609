"""Build the launch leaf cell: G1SG2_pitch100u_lvsres_lauching_metal_cwpg_via_fence.

Settled over the twenty-question pass, 2026-08-28. This is the second construction; what
the first one got wrong is recorded at the bottom of this note.

Frame: the S pad outer edge is x = 0 and the signal runs toward +x. The three pads stack
in y at a 100 um pitch, and both pad cells are drawn 80 um tall about their own origin, so
they are instanced rotated 90 degrees to put that 80 um along x.

    S pad   S_w40u_l80u_top_probpad_fill_dfpad   x 0..80,  y -20..+20
    G pads  G_w60u_l80u_top_to_m1_bondpad_fill   x 0..80,  y +-70..+-130
    signal  TopMetal2 19 um wide, x 80..180, stepping down from the 40 um pad in one step
    CPWG    coplanar ground on TopMetal2, inner edge at y +-19.5, so the gap is 10 um
    ground  Metal1 as one continuous plane under everything, plus M2..TM1 under the rails
    lvsres  a 134/29 marker across the signal; the deck reads that as res_topmetal2 and
            splits the net, which is what lets LVS see two named nets with a device between
    fence   via stacks TM2 down to M1 through the ground, on a 5 um grid
    slits   7 um squares on a 20 um grid, which the deck requires on wide metal

Z0 is 49.43 ohm for W=19 S=10 on this stack (h=9.77 um to Metal1, er=4.1).

Three things the first construction had wrong.

1.  The ground began at x = 85 on every row. That was put in to stop the ground touching
    the S pad, whose half-width of 20 um met the ground inner edge at 19.5 um, and it did
    stop the short. But the G pads end at x = 80, so it also left a 5 um gap between the
    coplanar ground and the pads that are supposed to feed it, and the ground was left
    floating. The ground now steps instead of starting late. It keeps y >= 25 while it
    passes the S pad, which is 5 um of clearance and satisfies TM2.bR for two wide
    conductors running parallel for more than 50 um, and it drops to y >= 19.5 only past
    x = 82, where the pad has ended and the 10 um CPWG gap is what sets the impedance.

2.  Metal1 existed only as a strip under the signal, disconnected from the Metal1 in the
    rails. The owner instruction is that the backing ground under the S pad and its launch
    is Metal1, which makes Metal1 a ground layer, so it should be one plane rather than a
    strip with a 4.5 um slot beside it. A slot in a return path is exactly what an RF
    ground plane must not have.

3.  Nothing was slitted. Slt.c flags any un-slitted metal region that survives a 15 um
    shrink, which means wider than 30 um in both directions, and the rails and the Metal1
    plane are far past that. The pads themselves are exempt because sltc_* subtracts
    Recog_or_dfpad_all and both pad cells carry a DfPad marker, which is why the pad cells
    alone showed no Slt.c while this cell did.

The slit pattern. Squares of 7 um on a 20 um grid. 7 um is above the 2.80 um minimum in
Slt.a and far below the 20 um maximum in Slt.b. The size was raised from 5 um after
measuring: 5 um squares are 6.25 percent of the grid cell, which looks like it clears the 6
percent floor Slt.i sets for plates over 35 x 35 um, but the pads carry no slits and neither
does the corridor under the signal, so the figure the rule actually computes came out at 3.9
to 4.2 percent per layer. At 7 um it measures 7.7 to 8.3 percent, which has real margin.

Rows sit at |y| = 14 and every 20 um outward from there, leaving a solid 28 um corridor
centred under the 19 um signal. That corridor is wide enough that the return current under
the line sees continuous metal, and still narrow enough that its centre lies 14 um from a
slit edge and so does not survive the Slt.c shrink. Slits are kept off the pads, which Slt.e
requires, and away from vias, which Slt.h requires.

Slits are placed before the fence, not after. The fence grid is 5 um and covers the whole
rail, so vias first leaves nowhere a slit can hold its clearance: the first run of this
script placed 875 vias and then managed 10 slits out of 108 offered. Reversed, the slits
take the coarser grid they need and the fence fills what is left, at 799 stacks.
"""
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
NAME = "G1SG2_pitch100u_lvsres_lauching_metal_cwpg_via_fence"
U = 1000.0

PITCH   = 100.0     # G1 - S - G2 centre spacing
PAD_L   = 80.0      # pad length along x, after the 90 degree rotation
S_W     = 40.0      # S pad width across
G_W     = 60.0      # G pad width across
LAUNCH  = 30.0      # launching metal length, cut from 100.0 on 2026-09-02
SIG_W   = 19.0      # CPWG signal width
GAP     = 10.0      # CPWG gap
SHIELD  = 0.0       # Metal1 plane beyond the pad edge on the probe side.
                    #
                    # This number moved twice. The owner first asked for 5 um. At 5 the deck
                    # raised Pad.fR_M1 once per pad row, on the strip x -7..-5, because it
                    # recommends that metal leaving a pad run at least 7 um, so it went to 7.
                    # On seeing it drawn the owner asked for the Metal1 edge to line up with
                    # the pads instead, which is 0.
                    #
                    # That does not bring Pad.fR_M1 back. The rule measures metal that exits
                    # a pad, and at 0 none does: the plane stops on the pad edge. The G pad
                    # cell on its own is the evidence, since its Metal1 is coincident with
                    # its pad and it reports no Pad.f item at all. Re-running the full deck
                    # after this change confirmed it rather than leaving it as an argument.
                    #
                    # It also squares the cell off at x 0..180, so the left edge of the leaf
                    # is one straight line across all three pads. That matters for the
                    # mirrored instance and for placing an HFSS port on a clean boundary.
RES_L   = 10.0      # length of the .res marker along the signal
PAD_CLR = 5.0       # TM2.bR: two wide conductors parallel over 50 um need 5 um of space

SLIT      = 7.0     # slit side; the pads and the signal corridor carry none, so the
                    # 49/400 = 12.25 percent of the grid lands near 8 percent overall,
                    # which is what Slt.i needs against its 6 percent floor
SLIT_GRID = 15.0    # 20.0 left too few slits once the leaf shortened, and Slt.i fired
CORRIDOR  = 14.0    # no slits within this of y=0, leaving 28 um solid under the signal
SLIT_ENC  = 1.5     # keep slits this far inside the metal edge; Slt.f asks for 1.0
SLIT_VIA  = 1.2     # Slt.h1 asks 0.30 but Slt.h3 and Slt.h4 ask 1.00, so 1.2 clears all three
SLIT_PAD  = 1.0     # keep slits off the pads, which Slt.e requires

VIA_PITCH = 5.0     # 1-16 GHz needs nothing finer, since lambda/20 is over 500 um

S_CELL = "S_w40u_l80u_top_probpad_fill_dfpad"
G_CELL = "G_w60u_l80u_top_to_m1_bondpad_fill"

TM2, TM2_RES, TM2_TXT = (134, 0), (134, 29), (134, 25)
M1, DFPAD = (8, 0), (41, 0)
# The slit marker shares the metal layer number, on datatype 24.
SLIT_DT = {(8, 0): (8, 24), (10, 0): (10, 24), (30, 0): (30, 24), (50, 0): (50, 24),
           (67, 0): (67, 24), (126, 0): (126, 24), (134, 0): (134, 24)}
# Via sizes are given in the rules as "min. and max.", so they are fixed, not chosen.
VIA = [("Via1", (19, 0), 0.19), ("Via2", (29, 0), 0.19), ("Via3", (49, 0), 0.19),
       ("Via4", (66, 0), 0.19), ("TopVia1", (125, 0), 0.42), ("TopVia2", (133, 0), 0.90)]
# Layers that exist only under the ground rails, so the fence has something to land on.
RAIL_MET = [(10, 0), (30, 0), (50, 0), (67, 0), (126, 0)]

ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell(NAME)


def L(layer):
    return ly.layer(*layer)


def dbox(x0, y0, x1, y1):
    return pya.Box(int(round(x0 * U)), int(round(y0 * U)),
                   int(round(x1 * U)), int(round(y1 * U)))


def put(layer, x0, y0, x1, y1):
    top.shapes(L(layer)).insert(dbox(x0, y0, x1, y1))


def region(layer):
    return pya.Region(top.begin_shapes_rec(L(layer)))


def place(cellname, xc, yc):
    """Instance a pad cell rotated 90 degrees about the given centre."""
    sub = ly.cell(cellname)
    if sub is None:
        sub = ly.create_cell(cellname)
        src = pya.Layout()
        src.read(os.path.join(PROJECT, "designlib", "teg", cellname, cellname + ".gds"))
        sub.copy_tree(src.top_cell())
    top.insert(pya.CellInstArray(
        sub.cell_index(), pya.Trans(pya.Trans.R90, int(xc * U), int(yc * U))))


place(S_CELL, PAD_L / 2, 0.0)
place(G_CELL, PAD_L / 2, +PITCH)
place(G_CELL, PAD_L / 2, -PITCH)

x0, x1 = PAD_L, PAD_L + LAUNCH          # launch runs x 80..180
gi = SIG_W / 2 + GAP                    # CPWG ground inner edge, y = 19.5
y_out = PITCH + G_W / 2                 # outer edge of the ground, y = 130
x_step = PAD_L + 2.0                    # where the ground drops from y=25 to y=19.5
y_near = S_W / 2 + PAD_CLR              # 25.0

# ---- signal, stepping from the 40 um pad to the 19 um line in one step -------------
put(TM2, x0, -SIG_W / 2, x1, SIG_W / 2)

# ---- the lvsres marker, centred in the launch -------------------------------------
xr = (x0 + x1) / 2.0
put(TM2_RES, xr - RES_L / 2, -SIG_W / 2, xr + RES_L / 2, SIG_W / 2)

# ---- ground on TopMetal2: holds off to y=25 over the pad, then drops to y=19.5 -----
for s in (+1, -1):
    for (a, b, lo) in ((0.0, x_step, y_near), (x_step, x1, gi)):
        put(TM2, a, min(s * lo, s * y_out), b, max(s * lo, s * y_out))

# ---- Metal1: one continuous ground plane under the whole cell ----------------------
put(M1, -SHIELD, -y_out, x1, y_out)

# ---- M2..TM1 under the ground rails only, never under the signal -------------------
for lay in RAIL_MET:
    for s in (+1, -1):
        for (a, b, lo) in ((0.0, x_step, y_near), (x_step, x1, gi)):
            put(lay, a, min(s * lo, s * y_out), b, max(s * lo, s * y_out))

# ---- slits first, then the via fence around them -----------------------------------
# Order matters here. A 5 um via grid covers the whole rail, so if the vias go down first
# there is no position left where a slit can keep its 0.3 um clearance and every slit is
# rejected. The slit grid is the coarser of the two and is what the deck requires, so it
# is placed first and the fence fills what remains.
dfpad = region(DFPAD).merged()
dfpad_keepout = dfpad.sized(int(SLIT_PAD * U))
rails = region((126, 0)).merged()        # TopMetal1 exists only under the rails

slit_rows, slit_cols = [], []
k = 0
while CORRIDOR + SLIT_GRID * k + SLIT <= y_out:
    lo = CORRIDOR + SLIT_GRID * k
    slit_rows += [(lo, lo + SLIT), (-lo - SLIT, -lo)]
    k += 1
k = 0
while True:
    lo = -SHIELD + SLIT_GRID / 2.0 + SLIT_GRID * k
    if lo + SLIT > x1:
        break
    slit_cols.append((lo, lo + SLIT))
    k += 1

candidates = [(sx0, sy0, sx1, sy1)
              for (sy0, sy1) in slit_rows for (sx0, sx1) in slit_cols]

n_slit = {}
for met, slit_layer in SLIT_DT.items():
    r = region(met).merged()
    if r.is_empty():
        continue
    inner = r.sized(-int(SLIT_ENC * U))
    made = 0
    for (sx0, sy0, sx1, sy1) in candidates:
        b = pya.Region(dbox(sx0, sy0, sx1, sy1))
        if b.inside(inner).count() != 1:
            continue
        if b.interacting(dfpad_keepout).count():
            continue
        top.shapes(L(slit_layer)).insert(dbox(sx0, sy0, sx1, sy1))
        made += 1
    n_slit[slit_layer] = made

# The fence must clear every candidate position, not only the ones that ended up drawn on
# a given layer, so that one grid of vias is legal against all seven slit layers at once.
slit_keepout = pya.Region([dbox(a - SLIT_VIA, b - SLIT_VIA, c + SLIT_VIA, d + SLIT_VIA)
                           for (a, b, c, d) in candidates]).merged()

n_via = 0
gx = 0.0
while gx <= x1:
    gy = -y_out
    while gy <= y_out:
        span = pya.Region(dbox(gx, gy, gx + 0.90, gy + 0.90))   # TopVia2 bounds the stack
        if (span.sized(int(0.5 * U)).inside(rails).count() == 1
                and span.interacting(dfpad).count() == 0
                and span.interacting(slit_keepout).count() == 0):
            for (_, lay, sz) in VIA:
                put(lay, gx, gy, gx + sz, gy + sz)
            n_via += 1
        gy += VIA_PITCH
    gx += VIA_PITCH

# ---- net labels: pad side, device side, and the ground -----------------------------
for text, tx, ty in (("S1", PAD_L / 2, 0.0), ("T1", x1 - 2.0, 0.0), ("GND", 20.0, PITCH)):
    top.shapes(L(TM2_TXT)).insert(pya.DText(text, pya.DTrans(pya.DVector(tx, ty))))

folder = os.path.join(PROJECT, "designlib", "teg", NAME)
os.makedirs(folder, exist_ok=True)
out = os.path.join(folder, NAME + ".gds")
ly.write(out)

bb = top.bbox()
print("wrote %s" % out)
print("  bbox        %.2f x %.2f um  (x %.1f..%.1f, y %.1f..%.1f)"
      % (bb.width() * ly.dbu, bb.height() * ly.dbu,
         bb.left * ly.dbu, bb.right * ly.dbu, bb.bottom * ly.dbu, bb.top * ly.dbu))
print("  signal      W=%.1f um over x %.0f..%.0f, one step down from the %.0f um pad"
      % (SIG_W, x0, x1, S_W))
print("  CPWG        gap %.1f um; ground inner edge y=%.1f past x=%.0f, y=%.1f before it"
      % (GAP, gi, x_step, y_near))
print("  lvsres      134/29, %.0f um long, centred at x=%.0f" % (RES_L, xr))
print("  via fence   %d stacks on a %.1f um grid" % (n_via, VIA_PITCH))
print("  slits       %.1f um squares on a %.1f um grid, %d rows and %d columns offered"
      % (SLIT, SLIT_GRID, len(slit_rows), len(slit_cols)))
for lay in sorted(n_slit):
    print("              %3d/%-3d %4d placed" % (lay[0], lay[1], n_slit[lay]))
