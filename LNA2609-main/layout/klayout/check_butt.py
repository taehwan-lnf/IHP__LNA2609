"""Verify the butt joint from the raw shapes, with yg read off the layout exactly.

The previous pass used yg values copied from the build log, which prints to one decimal.
Two cells came out 0.02 um short of their true edge and looked like overlaps. yg is now
taken from the ground bridge itself: the Metal1 rectangle that fills the whole slot, x
180..210, and reaches the frame edge at |y| = 130. Its inner edge is yg.

A butted joint merges into one polygon, so merged geometry cannot tell butting from
overlapping. The test therefore runs on shapes as drawn, and only on shapes inside the
slot: a shape whose bottom is below yg and whose top is above it crosses the edge.
"""
import glob
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEV = os.path.join(_ROOT, "designlib", "teg")
X0, X1, Y_OUT = 180.0, 210.0, 130.0
LAYERS = (("Metal1", (8, 0)), ("Metal2", (10, 0)))
EPS = 1e-6

print("%-40s %-7s %-24s %s" % ("CELL", "yg", "tie width / ring width", "crossing the edge"))
for d in sorted(glob.glob(os.path.join(DEV, "GSG_dut_npn13g2*"))):
    name = os.path.basename(d)
    ly = pya.Layout()
    ly.read(os.path.join(d, name + ".gds"))
    top = ly.top_cell()

    def raw(spec):
        j = ly.find_layer(*spec)
        if j is None:
            return []
        return [s.shape().bbox().transformed(s.trans()).to_dtype(ly.dbu)
                for s in top.begin_shapes_rec(j).each()]

    m1 = raw((8, 0))
    yg = None
    for b in m1:
        if (abs(b.left - X0) < EPS and abs(b.right - X1) < EPS
                and abs(b.top - Y_OUT) < EPS):
            yg = b.bottom if yg is None else min(yg, b.bottom)
    if yg is None:
        print("%-40s could not find the ground bridge" % name)
        continue

    ring_w = 0.0
    j = ly.find_layer(1, 0)
    if j is not None:
        for p in pya.Region(top.begin_shapes_rec(j)).merged().each():
            if p.holes() > 0:
                ring_w = max(ring_w, p.bbox().to_dtype(ly.dbu).width())

    tie_w, crossing = 0.0, []
    for nm, spec in LAYERS:
        for b in raw(spec):
            if b.right <= X0 + EPS or b.left >= X1 - EPS:
                continue                      # launch-cell metal, not a joint of ours
            for edge in (yg, -yg):
                if b.bottom < edge - EPS and b.top > edge + EPS:
                    crossing.append((nm, b))
            if nm == "Metal1" and abs(b.top - yg) < EPS and b.bottom < yg - 1.0:
                tie_w = max(tie_w, b.width())

    if crossing:
        detail = "; ".join("%s x %.2f..%.2f y %.2f..%.2f"
                           % (n, b.left, b.right, b.bottom, b.top) for n, b in crossing[:3])
    else:
        detail = "none"
    print("%-40s %-7.3f %5.2f of %5.2f um        %s" % (name, yg, tie_w, ring_w, detail))
