"""Isolate what flips GSG_open_sealed from clean to thousands of violations.

GSG_open_sealed comes back with density plus seven Pad.fR recommendations. Every other sealed
cell returns M2.c1 through M5.c1 and V1.c1 through V4.c1 in the thousands. Compared layer by
layer the two differ by six Metal1 shapes in the slot and nothing else, which should not be
able to do that, so one variable is changed at a time here.

    t1   GSG_open_sealed as it stands, the control
    t2   plus one Metal1 rectangle in the slot, nothing else
    t3   the same rectangle but no seal ring, to show the rectangle is harmless on its own
"""
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEV = os.path.join(_ROOT, "designlib", "teg")
OUT = os.path.join(_ROOT, "designlib", "teg")


def load(name):
    ly = pya.Layout()
    ly.read(os.path.join(DEV, name, name + ".gds"))
    return ly, ly.top_cell()


def save(ly, top, tag):
    folder = os.path.join(OUT, tag)
    os.makedirs(folder, exist_ok=True)
    top.name = tag
    ly.write(os.path.join(folder, tag + ".gds"))
    print("   wrote %s, bbox %s" % (tag, top.dbbox()))


BOX = (189.40, -5.0, 200.60, 5.0)          # the slot rectangle THRU uses

ly, top = load("GSG_open_sealed")
save(ly, top, "flip_t1_sealed_only")

ly, top = load("GSG_open_sealed")
top.shapes(ly.layer(8, 0)).insert(pya.DBox(*BOX))
save(ly, top, "flip_t2_sealed_plus_box")

ly, top = load("GSG_open")
top.shapes(ly.layer(8, 0)).insert(pya.DBox(*BOX))
save(ly, top, "flip_t3_box_no_ring")
