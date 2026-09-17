"""How do the sealring PCell's l and w map onto what it draws?

Needed before any ring can be sized to a cell. Three sizes are built and the four things
that matter are read back each time: the EdgeSeal.boundary that Seal.l measures against, the
Passiv ring, the outer metal ring and its inner edge, which is what the cell's own metal has
to keep clear of.

Two sizes would give the offsets; three is cheap and catches a term that is not linear.
"""
import pya

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
liblay = lib.layout()
pid = liblay.pcell_id("sealring")
decl = liblay.pcell_declaration("sealring")

print("%-16s %-22s %-22s %-22s %s"
      % ("l x w", "boundary 39/4", "Passiv 9/0", "metal 8/0 outer", "metal 8/0 inner hole"))
for l, w in ((400.0, 400.0), (300.0, 200.0), (500.0, 350.0)):
    D = {p.name: p.default for p in decl.get_parameters()}
    D.update({"l": "%gu" % l, "w": "%gu" % w})
    ly = pya.Layout()
    ly.dbu = 0.001
    t = ly.create_cell("t")
    t.insert(pya.CellInstArray(ly.add_pcell_variant(lib, pid, D), pya.Trans()))
    t.flatten(-1, True)

    def box(spec):
        j = ly.find_layer(*spec)
        if j is None:
            return None
        r = pya.Region(t.shapes(j)).merged()
        return r.bbox().to_dtype(ly.dbu) if not r.is_empty() else None

    bnd, pas, met = box((39, 4)), box((9, 0)), box((8, 0))
    # the hole in the metal ring, which is the usable inside
    r = pya.Region(t.shapes(ly.layer(8, 0))).merged()
    hole = None
    for p in r.each():
        if p.holes() > 0:
            hb = pya.Polygon([pya.Point(q.x, q.y)
                              for q in p.each_point_hole(0)]).bbox().to_dtype(ly.dbu)
            hole = hb
    def s(b):
        return "-" if b is None else "%.2f..%.2f x %.2f" % (b.left, b.right, b.height())
    print("%-16s %-22s %-22s %-22s %s"
          % ("%g x %g" % (l, w), s(bnd), s(pas), s(met), s(hole)))
    print("   cell bbox %s" % t.dbbox())
