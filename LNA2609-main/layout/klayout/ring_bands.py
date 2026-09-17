"""Per-layer inner edge of the seal ring, measured from its own origin.

Pad.d compares the pad opening against the Activ inside the EdgeSeal, not against the metal
ring, and the Activ band reaches further inward than Metal1 does. The offset that decides the
clearance is therefore the Activ one, so every layer's inner edge is measured rather than the
metal one assumed to stand for all of them.
"""
import pya

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
liblay = lib.layout()
pid = liblay.pcell_id("sealring")
decl = liblay.pcell_declaration("sealring")

D = {p.name: p.default for p in decl.get_parameters()}
D.update({"l": "428.800u", "w": "298.800u"})
ly = pya.Layout()
ly.dbu = 0.001
t = ly.create_cell("t")
t.insert(pya.CellInstArray(ly.add_pcell_variant(lib, pid, D), pya.Trans()))
t.flatten(-1, True)

NAMES = {(1, 0): "Activ", (14, 0): "pSD", (39, 0): "EdgeSeal", (39, 4): "EdgeSeal.boundary",
         (9, 0): "Passiv", (8, 0): "Metal1", (10, 0): "Metal2", (30, 0): "Metal3",
         (50, 0): "Metal4", (67, 0): "Metal5", (126, 0): "TopMetal1", (134, 0): "TopMetal2",
         (6, 0): "Cont", (19, 0): "Via1", (125, 0): "TopVia1", (133, 0): "TopVia2"}

print("ring bbox %s   (l=428.80, w=298.80)" % t.dbbox())
print()
print("%-20s %-22s %-22s %s" % ("layer", "outer edge", "inner edge", "band width"))
rows = []
for i in ly.layer_indexes():
    info = ly.get_info(i)
    key = (info.layer, info.datatype)
    r = pya.Region(t.shapes(i)).merged()
    if r.is_empty():
        continue
    ob = r.bbox().to_dtype(ly.dbu)
    inner = None
    for p in r.each():
        if p.holes() > 0:
            hb = pya.Polygon([pya.Point(q.x, q.y)
                              for q in p.each_point_hole(0)]).bbox().to_dtype(ly.dbu)
            inner = hb if inner is None else inner
    if inner is None:
        rows.append((key, ob.left, None, None))
    else:
        rows.append((key, ob.left, inner.left, inner.left - ob.left))

for key, o, i2, w in sorted(rows, key=lambda z: (z[2] is None, z[2] or 0)):
    nm = NAMES.get(key, "%d/%d" % key)
    if i2 is None:
        print("%-20s %-22.3f %-22s %s" % (nm, o, "no hole, solid", "-"))
    else:
        print("%-20s %-22.3f %-22.3f %.3f" % (nm, o, i2, w))
