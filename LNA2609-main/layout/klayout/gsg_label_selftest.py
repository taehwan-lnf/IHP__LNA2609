"""Check the label font before it is drawn into fourteen cells at once.

Three things are asserted, and each of them was a real failure at some point in the day rather
than a hypothetical one.

    No two glyphs share a bitmap. S and 5 were identical and so were 2 and Z, and neither was
    caught until tools/verify_labels.py read the label back off the layout and every DUT
    decoded as NPN13GZ.

    No glyph needs corner filling. The filling rule still exists and still works, but a glyph
    that trips it comes out a different shape from the one drawn here, and that is how V came
    to read as U and N as M in the first build.

    Every string the cells carry meets TopMetal2's own width and space rules, 2.00 um each.

    Every string fits the band. The band is 26.00 um, TM2.bR takes 5.00 um off the inner side
    and TM2.b 2.00 um off the outer, so a label may be at most 19.00 um tall, and it may be at
    most as wide as the narrowest cell, GSG_thru at 238.80 um.

Run it with:  wsl python3 tools/gsg_label_selftest.py     (needs klayout on the path for pya)
or under klayout:  klayout -z -nc -r tools/gsg_label_selftest.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsg_label as L

NARROWEST_CELL = 238.80

STRINGS = [
    "OPEN", "SHORT", "THRU", "LOAD", "DEEMBED STD", "50 OHM RPPD",
    "NPN13G2", "NPN13G2L", "NPN13G2V",
    "AE=0.6630UM2", "AE=0.9216UM2", "AE=0.9945UM2", "AE=1.3260UM2",
    "AE=2.3040UM2", "AE=2.7270UM2", "AE=3.4560UM2", "AE=3.6360UM2",
    "AE=4.5450UM2", "AE=4.6080UM2",
]

fails = []

# No two glyphs may share a bitmap. A reader at the microscope cannot tell them apart, and the
# whole point of the label is to be read.
seen = {}
for ch in sorted(L.FONT):
    key = tuple("".join("#" if c == "#" else "." for c in row) for row in L.FONT[ch])
    if key in seen:
        fails.append("glyphs %r and %r are drawn identically" % (seen[key], ch))
    seen[key] = ch

for ch in sorted(L.FONT):
    on = L._bitmap(ch)
    n = L._close_corners(on)
    if n:
        fails.append("glyph %r needs %d corner fills, so it will not come out as drawn"
                     % (ch, n))

room = 26.00 - L.GAP_CELL - L.GAP_RING
print("%-14s %-16s %-8s %-8s %s" % ("STRING", "SIZE um", "WIDTH", "SPACE", "FITS"))
for t in STRINGS:
    reg, fixed = L.text_region(t, 0.0, 0.0)
    w, h = L.text_size(t)
    wv = reg.width_check(2000).count()
    sv = reg.space_check(2000).count()
    fits = w <= NARROWEST_CELL and h <= room
    print("%-14s %6.1f x %-7.1f %-8d %-8d %s"
          % (t, w, h, wv, sv, "yes" if fits else "NO"))
    if fixed:
        fails.append("%r needed %d corner fills" % (t, fixed))
    if wv or sv:
        fails.append("%r breaks TopMetal2: width %d, space %d" % (t, wv, sv))
    if not fits:
        fails.append("%r is %.1f x %.1f and the room is %.1f x %.1f"
                     % (t, w, h, NARROWEST_CELL, room))

print()
if fails:
    for f in fails:
        print("FAIL  %s" % f)
    raise SystemExit(1)
print("all %d glyphs and %d strings pass" % (len(L.FONT), len(STRINGS)))
