"""Build the owner's custom Nx=20 cell, and a we=0.07u twin to keep two questions apart.

The sketch builds it by tiling two Nx=10 cores and drawing a bigger guard ring round the
pair. Measuring first showed that is unnecessary: the PCell declares Nx max = 10, but that
range is enforced by the parameter dialog, not by the generator, and asking a script for
Nx=20 produces 20 fingers on the same 1.85 um pitch, which is exactly what tiling gives.

    Nx=10   EmWind x -0.035..16.685, 10 fingers, pitch 1.85
    Nx=20   EmWind x -0.035..35.185, 20 fingers, pitch 1.85

The result is flattened into a plain cell rather than left as a PCell instance, because a
PCell carrying an out-of-range parameter would be re-evaluated, and possibly clamped, by
anything that opens it. Flattened, it is a custom layout cell in the sense the sketch means.

Two cells are built, differing only in we:

    ..._we0p08u   what the owner asked for
    ..._we0p07u   the control, so that if LVS fails it is clear whether the cause is the
                  20 fingers or the emitter width

Metal1 net labels go on B, C and E so extraction has names to report.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_frame as F

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUT = os.path.join(_ROOT, "designlib", "teg")
M1_TXT = (8, 25)
lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
liblay = lib.layout()
decl = liblay.pcell_declaration("npn13G2")


def build(nx, we, name, le="0.9u"):
    D = {p.name: p.default for p in decl.get_parameters()}
    D.update({"Nx": nx, "le": le, "we": we})
    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name)
    top.insert(pya.CellInstArray(ly.add_pcell_variant(lib, liblay.pcell_id("npn13G2"), D),
                                 pya.Trans()))
    top.flatten(-1, True)

    # name the three terminals from the Metal1 windows: leftmost is the base, rightmost the
    # collector, and the emitter is the one Metal2 strap, contacted down on Metal1 between
    # Unrotated, this device stacks its terminals in y, not in x: base at the bottom,
    # the emitter strap in the middle and the collector on top. Grouping by x returns the
    # full-width bars instead, which is what a first attempt did.
    groups = {}
    for s in top.shapes(ly.layer(8, 0)).each():
        b = s.dbbox()
        k = (round(b.bottom, 3), round(b.top, 3))
        v = groups.setdefault(k, [1e9, -1e9])
        v[0] = min(v[0], b.left)
        v[1] = max(v[1], b.right)
    wins = sorted((lo, hi, g[0], g[1]) for (lo, hi), g in groups.items())
    m2 = pya.Region(top.shapes(ly.layer(10, 0))).merged().bbox().to_dtype(ly.dbu)

    for nm, (lo, hi, l, r) in (("B", wins[0]), ("C", wins[-1])):
        top.shapes(ly.layer(*M1_TXT)).insert(
            pya.DText(nm, pya.DTrans(pya.DVector((l + r) / 2.0, (lo + hi) / 2.0))))
    # The emitter strap is Metal2, so its name goes on Metal2.text. Putting it on
    # Metal1.text left the emitter as an unnamed net and extraction returned
    # "Q$1 C B \\$6 \\$1", with only the base and collector named.
    top.shapes(ly.layer(10, 25)).insert(
        pya.DText("E", pya.DTrans(pya.DVector(m2.center().x, m2.center().y))))

    # Contact the p+ guard ring on all four bands and name it. The PCell draws the ring on
    # Activ and pSD and stops there, in this flavour as in the other two, so without this
    # the fourth terminal extracts onto an auto-named net. Standing alone the cell has no
    # straps crossing the ring, so unlike the DUT cells all four bands are usable.
    ring = None
    for p in pya.Region(top.shapes(ly.layer(1, 0))).merged().each():
        if p.holes() > 0:
            ring = p
    if ring is not None:
        ob = ring.bbox().to_dtype(ly.dbu)
        hb = pya.Polygon([pya.Point(q.x, q.y)
                          for q in ring.each_point_hole(0)]).bbox().to_dtype(ly.dbu)
        top.shapes(ly.layer(8, 0)).insert(ring)
        CONT, PITCH = 0.16, 0.34
        bands = [(ob.left, ob.bottom, ob.right, hb.bottom),
                 (ob.left, hb.top, ob.right, ob.top),
                 (ob.left, hb.bottom, hb.left, hb.top),
                 (hb.right, hb.bottom, ob.right, hb.top)]
        n = 0
        for x0, y0, x1, y1 in bands:
            cy = y0 + (y1 - y0 - CONT) / 2.0
            if x1 - x0 > y1 - y0:                       # a horizontal band
                cx = x0 + 0.17
                while cx + CONT <= x1 - 0.17:
                    top.shapes(ly.layer(6, 0)).insert(
                        pya.DBox(cx, cy, cx + CONT, cy + CONT))
                    cx += PITCH
                    n += 1
            else:                                       # a vertical one
                cx = x0 + (x1 - x0 - CONT) / 2.0
                gy = y0 + 0.17
                while gy + CONT <= y1 - 0.17:
                    top.shapes(ly.layer(6, 0)).insert(
                        pya.DBox(cx, gy, cx + CONT, gy + CONT))
                    gy += PITCH
                    n += 1
        top.shapes(ly.layer(*M1_TXT)).insert(
            pya.DText("SUB", pya.DTrans(pya.DVector((ob.left + hb.left) / 2.0,
                                                    (ob.bottom + hb.bottom) / 2.0))))
        print("     guard ring contacted with %d Cont on all four bands" % n)

        # Geometry annotation inside the ring, on TEXT.drawing, owner request 2026-09-02.
        # Only what the PCell does not already write: it puts an Ae= string carrying m, Nx,
        # le and we but never evaluates the product and never mentions the final area.
        for i, line in enumerate(F.area_lines("npn13G2", 1, nx, float(le.rstrip("u")),
                                              float(we.rstrip("u")))):
            top.shapes(ly.layer(*F.TEXT_DRW)).insert(
                pya.DText(line, pya.DTrans(pya.DVector(hb.left + 0.3,
                                                       hb.top - 0.6 - 0.55 * i)), 350, -1))

    folder = os.path.join(OUT, name)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".gds")
    ly.write(path)
    ew = pya.Region(top.shapes(ly.layer(33, 0))).merged()
    fw = sorted(set(round(p.bbox().to_dtype(ly.dbu).width(), 4) for p in ew.each()))
    print("%-38s bbox %.2f x %-6.2f  EmWind %d finger(s), width %s"
          % (name, top.dbbox().width(), top.dbbox().height(), ew.count(), fw))
    print("     base y %.3f..%-8.3f collector y %.3f..%-8.3f emitter M2 y %.3f..%.3f"
          % (wins[0][0], wins[0][1], wins[-1][0], wins[-1][1], m2.bottom, m2.top))
    return path


# we=0.08u was built here as a test on 2026-09-02 and removed the same day on owner
# instruction. It draws cleanly and passes DRC, but the LVS deck extracts no device from it
# at all: npn13G2_e_pin tests with_bbox_min(0.07), with_bbox_max(0.9) and with_area(0.063),
# three equalities, under the deck's own comment that npn13G2 is a fixed device. we=0.09u
# behaved the same way on 2026-09-01. It is readable at commit f1491ba, the last one that
# carries it. Restore it by adding back:
#
#     build(20, "0.08u", "npn13g2_m1_Nx20_le0p9u_we0p08u")
#
build(20, "0.07u", "npn13g2_m1_Nx20_le0p9u_we0p07u")
