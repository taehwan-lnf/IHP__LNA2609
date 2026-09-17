"""Build all ten GSG DUT cells on the butt scheme: layout, schematic and symbol each.

Generalised from the single npn13G2V cell. What varies between the ten:

    flavour   npn13G2, npn13G2L, npn13G2V, each with its own terminal geometry
    multi     1 for L and V, and 4, 3, 2, 1 for npn13G2, stacked in y
    Nx, le    checked against BOTH limit sources before anything is drawn, because
              Nx is bounded only by the PCell declaration and le only by the DRC deck

Devices are stacked abutting, at a pitch equal to the cell height. The tighter 22.000 um
pitch was measured clean too, but it is the exact limit: 21.000 raises pSD.d and below that
the CntB rules follow. Abutting costs 4 um on the tallest column and keeps margin for any
later edit.

The joint between strap and terminal rail is left at zero overlap on owner instruction: a
shift that opened a gap would be caught by LVS, which is where a missing connection shows
up. That is not a guess. Earlier in this work a dropped TopVia2 column left the base
unreachable and neither the geometry nor DRC showed anything, while LVS failed at once.

Pad.kR is accepted rather than cleared, on owner instruction 2026-09-01: the G pads carry a
full TopVia2 grid, which puts 96 vias under each pad opening.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_frame as F
import gsg_views_lib as V

M1, M2, M3, M4, M5, TM1 = (8, 0), (10, 0), (30, 0), (50, 0), (67, 0), (126, 0)
CONT_LAY = (6, 0)

UP = [M1, M2, M3, M4, M5, TM1, F.TM2]
UP_VIA = [((19, 0), 0.19, 0.6), ((29, 0), 0.19, 0.6), ((49, 0), 0.19, 0.6),
          ((66, 0), 0.19, 0.6), ((125, 0), 0.42, 1.2), ((133, 0), 0.90, 2.2)]
VIA_INSET, EPS = 0.8, 1e-6
STACK_W, STACK_GAP, CLEAR = 3.0, 3.0, 8.0
LE_LIMITS = {"npn13G2": (0.9, 0.9), "npn13G2L": (1.0, 2.5), "npn13G2V": (1.0, 5.0)}

SPECS = [
    ("npn13G2V", "npn13g2v", 1, 5, 5.0, 0.12),
    ("npn13G2V", "npn13g2v", 1, 4, 5.0, 0.12),
    ("npn13G2V", "npn13g2v", 1, 3, 5.0, 0.12),
    ("npn13G2L", "npn13g2l", 1, 4, 2.5, 0.07),
    ("npn13G2L", "npn13g2l", 1, 3, 2.5, 0.07),
    ("npn13G2L", "npn13g2l", 1, 2, 2.5, 0.07),
    ("npn13G2",  "npn13g2",  4, 10, 0.9, 0.07),
    ("npn13G2",  "npn13g2",  3, 10, 0.9, 0.07),
    ("npn13G2",  "npn13g2",  2, 10, 0.9, 0.07),
    ("npn13G2",  "npn13g2",  1, 8, 0.9, 0.07),
]

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
if lib is None:
    raise SystemExit("SG13_dev not found. Run under: klayout -z -nc -r <script>")
liblay = lib.layout()


def num(v, places):
    return ("%.*f" % (places, v)).replace(".", "p")


def measure(pcell, nx, le, we):
    D = {p.name: p.default for p in liblay.pcell_declaration(pcell).get_parameters()}
    D.update({"Nx": nx, "le": "%gu" % le, "we": "%gu" % we})
    ly = pya.Layout(); ly.dbu = 0.001
    t = ly.create_cell("t")
    t.insert(pya.CellInstArray(ly.add_pcell_variant(lib, liblay.pcell_id(pcell), D),
                               pya.Trans(pya.Trans.R270, 0, 0)))
    t.flatten(-1, True)
    g = {}
    for s in t.shapes(ly.find_layer(8, 0)).each():
        d = s.dbbox()
        k = (round(d.left, 3), round(d.right, 3))
        v = g.setdefault(k, [1e9, -1e9])
        v[0] = min(v[0], d.bottom); v[1] = max(v[1], d.top)
    w = sorted((l, r, v[0], v[1]) for (l, r), v in g.items())
    m2 = pya.Region(t.shapes(ly.find_layer(10, 0))).merged().bbox().to_dtype(ly.dbu)

    # The substrate ring is the one Activ polygon with a hole in it. It carries pSD, so it
    # is a p+ ring around the device, and in all three flavours it carries no Cont and no
    # Metal1 at all: the PCell draws the diffusion and leaves the tie to the user.
    ring = None
    for p in pya.Region(t.shapes(ly.find_layer(1, 0))).merged().each():
        if p.holes() > 0:
            ring = p
    if ring is None:
        raise SystemExit("%s has no Activ ring, so there is nothing to tie" % pcell)
    outer = ring.bbox().to_dtype(ly.dbu)
    pts = [pya.Point(q.x, q.y) for q in ring.each_point_hole(0)]
    hole = pya.Polygon(pts).bbox().to_dtype(ly.dbu)
    return D, t.dbbox(), w[0], w[-1], m2, outer, hole


def tie_substrate_ring(f, ox, oy, multi, pitch, base, coll, ring_out, ring_hole, yg,
                       ry0, ry1, cy0, cy1):
    """Contact the p+ substrate ring on its top and bottom bands and run it to ground.

    The PCell draws the ring on Activ and pSD and stops there. Measured on all three
    flavours, zero Cont and zero Metal1 touch it, so the fourth terminal comes out of
    extraction on an auto-named net rather than on GND. Nothing in DRC objects, because a
    diffusion ring with no contact breaks no geometric rule; the only place it shows is the
    extracted netlist, and there only if you read the pin list.

    Only the top and bottom bands are usable. The left and right bands run underneath the
    base and collector straps, which have to cross the ring to reach the terminals inside
    it, and putting ring metal there would short the ring to whichever strap crosses it.
    So the contacts go on the horizontal bands and the tie runs out in y.

    Contact size and pitch are copied from the PCell's own array, 0.16 um square on a
    0.34 um pitch, rather than read off a rule: the deck states Cnt.g, Cnt.h, M1.c = 0.00
    and M1.c1 = 0.05 in its text but keeps the width and spacing in a table it loads, and
    the PCell's array is already clean.

    Width, on owner instruction 2026-09-01: as wide as it will go, decided per y segment
    rather than once for the whole run. The base and collector straps are bars over one y
    range each, [ry0, ry1] and [cy0, cy1], so a segment that does not share y with them has
    nothing to keep clear of and takes the ring's full outer width. Only the segments that
    do share y get pulled in to CLR from the strap edge. For a single device that means the
    whole tie is full width, since both straps sit inside the device core; in a stacked
    column the two outer runs are full width and only the runs between devices narrow.

    The joint to the ground bridge is butted at exactly +/-yg, again on owner instruction:
    no overlap, the same rule the base and collector straps already follow.

    In a stacked column the rings chain: each device's top band is joined to the next
    device's bottom band across the 0.40 um gap between them, and only the two outermost
    bands need to reach the ground bridge.
    """
    CONT, PITCH, CLR, ENDCAP = 0.16, 0.34, 0.30, 0.10

    def window(y0, y1):
        """The widest x this y range can use without coming near either strap."""
        lo, hi = ring_out.left + ox, ring_out.right + ox
        if not (y1 <= ry0 or y0 >= ry1):
            lo = max(lo, base[0] + ox + CLR)
        if not (y1 <= cy0 or y0 >= cy1):
            hi = min(hi, coll[1] + ox - CLR)
        return lo, hi

    bands = []
    for k in range(multi):
        dy = oy + k * pitch
        bands.append((ring_out.bottom + dy, ring_hole.bottom + dy))
        bands.append((ring_hole.top + dy, ring_out.top + dy))

    n_cont = 0
    for b0, b1 in bands:
        x_lo, x_hi = window(b0, b1)
        n = int((x_hi - x_lo - 2 * ENDCAP - CONT) / PITCH) + 1
        if n < 1:
            raise SystemExit("no room on the ring band for a substrate contact")
        x_first = (x_lo + x_hi - ((n - 1) * PITCH + CONT)) / 2.0
        cy = (b0 + b1 - CONT) / 2.0
        for i in range(n):
            cx = x_first + i * PITCH
            f.put(CONT_LAY, cx, cy, cx + CONT, cy + CONT)
        f.put(M1, x_lo, b0, x_hi, b1)
        n_cont += n

    # One vertical Metal1 run per corridor, each as wide as its own y range allows. A run
    # covers the gap between two bands, or at the two ends the reach out to the ground
    # bridge, where it stops flush at +/-yg. The device core between a device's own two
    # bands is deliberately skipped: the emitter, base and collector Metal1 live there.
    prev = -yg
    for k in range(multi):
        nxt = bands[2 * k][1]
        x_lo, x_hi = window(prev, nxt)
        f.put(M1, x_lo, prev, x_hi, nxt)
        prev = bands[2 * k + 1][0]
    x_lo, x_hi = window(prev, yg)
    f.put(M1, x_lo, prev, x_hi, yg)

    return n_cont


def build(pcell, sym, multi, nx, le, we, allow_nx_over=False):
    """allow_nx_over lets Nx exceed the range the PCell declares.

    The declared maximum is 10 and the parameter dialog is what enforces it; a script asking
    for more gets it, and gets it correctly. Measured at Nx=20, the PCell lays 20 emitter
    windows on the same 1.85 um pitch it uses at Nx=10, which is what tiling two Nx=10 cores
    would have produced. The device is then flattened into a plain cell rather than left as a
    PCell instance, because a PCell carrying an out-of-range parameter would be re-evaluated,
    and possibly clamped, by whatever opens the file next.
    """
    for p in liblay.pcell_declaration(pcell).get_parameters():
        if p.name == "Nx" and not (p.min_value <= nx <= p.max_value) and not allow_nx_over:
            raise SystemExit("%s Nx=%d outside [%s, %s]" % (pcell, nx, p.min_value, p.max_value))
    lo, hi = LE_LIMITS[pcell]
    if not (lo <= le <= hi):
        raise SystemExit("%s le=%gu outside the deck's [%gu, %gu]" % (pcell, le, lo, hi))

    D, bb, base, coll, em2, ring_out, ring_hole = measure(pcell, nx, le, we)
    name = "GSG_dut_%s_m%d_Nx%d_le%su_we%su" % (sym, multi, nx, num(le, 1), num(we, 2))
    pitch = bb.height()                      # abutting

    # centre the column on y=0, using the emitter Metal2 as the reference
    span_lo = em2.bottom
    span_hi = em2.top + (multi - 1) * pitch
    oy = -(span_lo + span_hi) / 2.0
    ox = F.XC - bb.width() / 2.0 - bb.left

    ry0 = base[2] + oy
    ry1 = base[3] + oy + (multi - 1) * pitch
    cy0 = coll[2] + oy
    cy1 = coll[3] + oy + (multi - 1) * pitch
    half = max(abs(bb.bottom + oy), abs(bb.top + oy + (multi - 1) * pitch))
    yg = max(F.GI, half + CLEAR)

    f = F.Frame(name, yg=yg)
    f.ground_bridge()
    if allow_nx_over:
        # A flattened copy, so that nothing re-evaluates an out-of-range PCell parameter.
        src = pya.Layout()
        src.dbu = 0.001
        tmp = src.create_cell("t")
        tmp.insert(pya.CellInstArray(
            src.add_pcell_variant(lib, liblay.pcell_id(pcell), D), pya.Trans()))
        tmp.flatten(-1, True)
        flat = f.ly.create_cell("%s_Nx%d_flat" % (pcell, nx))
        flat.copy_tree(tmp)
        cid = flat.cell_index()
    else:
        cid = f.ly.add_pcell_variant(lib, liblay.pcell_id(pcell), D)
    for k in range(multi):
        f.top.insert(pya.CellInstArray(
            cid, pya.Trans(pya.Trans.R270, int(round(ox * F.U)),
                           int(round((oy + k * pitch) * F.U)))))

    # The launch is no longer drawn here. It is the shared fixture from gsg_frame, the same
    # one OPEN, SHORT, THRU and LOAD use, so that the five differ only in what sits between
    # its two end planes. Owner instruction of 2026-09-02. What this file still draws is
    # everything from an end plane inward to a device terminal, which is DUT metal and
    # rightly varies with the flavour and with multi.
    # The tower goes at the terminal, as close to the device as the room allows, so its
    # inner edge is device dependent while its size and layers are not. Owner instruction
    # 2026-09-05.
    xi, xo = f.fixture((ring_hole.left + ox + F.D1, base[0] + ox),
                       (ring_hole.right + ox - F.D1, coll[1] + ox), "B", "C")

    # No Metal1 strap from the tower to the terminal any more. In view 2 the Metal1 outboard
    # of the guard ring is the cpwg backing ground, so the signal cannot travel on it: it comes
    # in on TopMetal2, drops to Metal2 in the tower, and touches Metal1 only at the tip inside
    # the ring. Owner instruction 2026-09-05.

    # The emitter strap on Metal2 to Metal5, drawn by the one shared routine in gsg_frame so
    # that the four de-embedding standards of the GSG kit can draw the same thing. Owner
    # instruction 2026-09-05: three via columns, and Metal5 is the top, both because npn13G2 is
    # the narrowest emitter and the owner took it as the constraint on what all of them share.
    em_col, em_row, em_w = F.emitter_strap(f, em2.left + ox, em2.right + ox, yg)
    print("    emitter strap %.3f um wide, %d via column(s) x %d row(s)"
          % (em_w, em_col, em_row))
    # The ground, the ring and the join between them, in one fill. See Frame.backing_ground.
    rings, holes = [], []
    for k in range(multi):
        dy = oy + k * pitch
        rings.append(((ring_out.left + ox, ring_out.bottom + dy,
                       ring_out.right + ox, ring_out.top + dy),
                      (ring_hole.left + ox, ring_hole.bottom + dy,
                       ring_hole.right + ox, ring_hole.top + dy)))
        holes.append(rings[-1][1])
    # A slot outboard of the guard ring on each of the two sides a tip faces, so the metal the
    # tip sees is a narrow band rather than the wide fill. See Frame.backing_ground.
    slots = []
    for k in range(multi):
        dy = oy + k * pitch
        ylo = min(base[2], coll[2]) + dy - F.M1_SLOT_OVER
        yhi = max(base[3], coll[3]) + dy + F.M1_SLOT_OVER
        slots.append((ring_out.left + ox - F.M1_SLOT, ylo, ring_out.left + ox, yhi))
        slots.append((ring_out.right + ox, ylo, ring_out.right + ox + F.M1_SLOT, yhi))
    gnd_area = f.backing_ground(holes, slots)
    n_cont = f.ring_contacts(rings)

    # One signal tip per terminal per device, each butting its terminal with no overlap and
    # keeping D1 from the ring Metal1 on the other side.
    tips = []
    for k in range(multi):
        dy = oy + k * pitch
        tips.append(f.tip(ring_hole.left + ox + F.D1, base[0] + ox,
                          base[2] + dy, base[3] + dy))
        tips.append(f.tip(coll[1] + ox, ring_hole.right + ox - F.D1,
                          coll[2] + dy, coll[3] + dy))
    print("    backing ground %.1f um2, ring contacts %d, tip %d col x %d row"
          % (gnd_area, n_cont, tips[0][0], tips[0][1]))

    # Geometry annotation inside the guard ring, on TEXT.drawing, owner request 2026-09-02.
    # It goes in the ring of the lowest device in the column, because the numbers are for the
    # cell as a whole and repeating them per device would say the same thing multi times.
    # TEXT.drawing is read by the LVS deck, but only against fixed strings: inductor2*,
    # isolbox, LA, LB, LC, nmoscl_2, nmoscl_4, rfnmos, rfnmosHV, rfpmos, rfpmosHV, sub!,
    # SVaricap and well. None of these lines can collide with those.
    tx = ring_hole.left + ox + 0.3
    ty = ring_hole.top + oy - 0.6
    for line in F.area_lines(pcell, multi, nx, le, we):
        f.top.shapes(f.L(F.TEXT_DRW)).insert(
            pya.DText(line, pya.DTrans(pya.DVector(tx, ty)), 350, -1))
        ty -= 0.55

    # Pads are named at their own centres and B and C on the fixture's end planes, both by
    # the frame, so nothing is passed here. The old call put B and C on TopMetal2 at the
    # middle of each strap, which is neither an edge nor a pad.
    f.pad_labels()
    f.finish([])

    folder = os.path.join(F.PROJECT, "designlib", "teg", name)
    write_views(folder, name, pcell, sym, multi, nx, le, we)
    print("    column %d x %.2f -> %.2f um, ground from |y| = %.1f, %d substrate contact(s)"
          % (multi, pitch, span_hi - span_lo, yg, n_cont))
    return name


# The symbol basename is not the lowercase tag used in cell names. The files carry the
# PDK's own capitalisation, and xschem reports 'IS MISSING !!!!' rather than failing
# when it cannot resolve one, so a wrong name here yields a netlist that looks complete.
# Owner instruction 2026-09-02: the set moves to deep extraction, so the stock PDK
# symbols are used and the *_lvsfix copies are no longer needed. Those copies swap le
# and we, which was right for flat extraction of an R270 placement and wrong for deep,
# where the device is reported as drawn. The stock formats already say what deep wants:
#
#   npn13G2   le=900e-9 we=70.0n Nx=@Nx     the fixed device, only Nx from the instance
#   npn13G2l  le=[El*1e-6] we=70.0n Nx=@Nx
#   npn13G2v  le=[El*1e-6] we=120.0n Nx=@Nx
SYMFILE = {"npn13G2": "npn13G2", "npn13G2L": "npn13G2l", "npn13G2V": "npn13G2v"}

# The model string is not the lowercase tag either. It is what each symbol's own template
# carries, and the extractor writes the same spelling, so a lowercase model would compare
# two device classes that differ only in case.
MODEL = {"npn13G2": "npn13G2", "npn13G2L": "npn13G2l", "npn13G2V": "npn13G2v"}

DEVLINE = {
    # The stock npn13G2 symbol carries le and we in its own format string, since this
    # is the flavour the deck pins to one size, so the instance sets only Nx.
    "npn13G2": "Nx=%(nx)d",
    "npn13G2L": "Nx=%(nx)d\nEl=%(le)g",
    "npn13G2V": "Nx=%(nx)d\nEl=%(le)g",
}


def write_views(folder, name, pcell, sym, multi, nx, le, we):
    os.makedirs(folder, exist_ok=True)
    out = ["""v {xschem version=3.4.4 file_version=1.2
* %s
*
* Two launch leaves with %d %s in the 30 um slot between them. Common emitter: base to the
* input launch, collector to the output launch, emitter to the coplanar ground.
*
* The two res_topmetal2 come from the 134/29 markers inside the leaves, which is what gives
* each launch a named net either side of the marker.
}
G {}
K {}
V {}
S {}
E {}
T {%s} -300 -220 0 0 0.4 0.4 {}
C {res_topmetal2.sym} 0 0 0 0 {name=R1
model=res_topmetal2
spiceprefix=R
w=19u
l=10u
}
N 0 -60 0 -30 { lab=IN}
N 0 30 0 60 { lab=B}
C {res_topmetal2.sym} 200 0 0 0 {name=R2
model=res_topmetal2
spiceprefix=R
w=19u
l=10u
}
N 200 -60 200 -30 { lab=OUT}
N 200 30 200 60 { lab=C}
C {devices/ipin.sym} 0 -60 0 0 {name=p1 lab=IN}
C {devices/ipin.sym} 200 -60 0 0 {name=p2 lab=OUT}
C {devices/lab_pin.sym} 0 60 0 0 {name=lb sig_type=std_logic lab=B}
C {devices/lab_pin.sym} 200 60 0 0 {name=lc sig_type=std_logic lab=C}
C {devices/iopin.sym} 460 30 0 0 {name=p3 lab=GND}
N 460 0 460 30 { lab=GND}
""" % (name, multi, pcell, name)]

    for k in range(multi):
        y = 200 + k * 140
        out.append("""C {%s.sym} 400 %d 0 0 {name=Q%d
model=%s
spiceprefix=X
%s
mm_ok=1}
N 420 %d 470 %d { lab=C}
N 380 %d 330 %d { lab=B}
N 420 %d 470 %d { lab=GND}
N 420 %d 510 %d { lab=GND}
C {devices/lab_pin.sym} 470 %d 0 0 {name=lc%d sig_type=std_logic lab=C}
C {devices/lab_pin.sym} 330 %d 0 0 {name=lb%d sig_type=std_logic lab=B}
C {devices/lab_pin.sym} 470 %d 0 0 {name=le%d sig_type=std_logic lab=GND}
C {devices/lab_pin.sym} 510 %d 0 0 {name=ls%d sig_type=std_logic lab=GND}
""" % (SYMFILE[pcell], y, k + 1, MODEL[pcell],
       DEVLINE[pcell] % {"nx": nx, "le": le, "we": we},
       y - 30, y - 30, y, y, y + 30, y + 30, y, y,
       y - 30, k + 1, y, k + 1, y + 30, k + 1, y, k + 1))

    io.open(os.path.join(folder, name + ".sch"), "w", encoding="utf-8",
            newline="\n").write("".join(out))

    # The symbol comes from the one writer, in gsg_views_lib, which is also where the sealed
    # schematic's wires are drawn. This file used to hold its own copy of the symbol text, and
    # on 2026-09-04 that copy was found to put IN, OUT and GND 20 to 70 units away from where
    # write_wrapper draws the wires that have to meet them. Thirteen sealed cells netlisted
    # their DUT onto net1, net2 and net3 as a result, and LVS reported MATCH throughout.
    V.write_symbol(folder, name, ["IN", "OUT", "GND"],
                   "* Symbol for the bare cell, pins taken from its own .subckt line.\n")

    # xschem writes its generic subcircuit format unless lvs_netlist is on. With it off two
    # things go wrong at once and neither announces itself: the netlist carries a commented
    # **.subckt, which the deck reports as no schematic counterpart for the top cell, and the
    # device line ignores the symbol's lvs_format, which is the entire reason the *_lvsfix
    # symbols exist. Setting it in the cell's own rc keeps the folder reproducible on its
    # own rather than depending on a flag someone has to remember on the command line.
    io.open(os.path.join(folder, "xschemrc"), "w", encoding="utf-8", newline="\n").write(
        io.open(os.path.join(F.PROJECT, "designlib", "teg", F.LEAF, "xschemrc"),
                encoding="utf-8").read()
        + "\nset lvs_netlist 1\n")


# Nx=20 is out of the range the PCell declares, so it is asked for explicitly. It is the
# owner's substitute for the m=2 column of Nx=10: after R270 it measures 7.11 x 41.85 against
# the column's 7.11 x 46.70, the same width and 4.85 um shorter, with one guard ring in place
# of two and the terminal rails at the same x, so the butt straps land unchanged.
EXTRA = [("npn13G2", "npn13g2", 1, 20, 0.9, 0.07),
         ("npn13G2", "npn13g2", 1, 30, 0.9, 0.07),
         ("npn13G2", "npn13g2", 1, 40, 0.9, 0.07)]

# Guarded so the file can be imported for its build() without building the whole set. Under
# klayout -r this module IS __main__, so running it behaves exactly as before; importing it
# from tools/sweep_dut.py gets the function and none of the seventeen cells.
if __name__ == "__main__":
    made = []
    for spec in SPECS:
        made.append(build(*spec))
    for spec in EXTRA:
        made.append(build(*spec, allow_nx_over=True))
    print()
    print("built %d cell(s)" % len(made))
    io.open("/tmp/dut_names.txt", "w").write("\n".join(made) + "\n")
