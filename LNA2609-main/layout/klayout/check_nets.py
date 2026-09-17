"""Extract the nets of a cell directly, to see how many pieces the ground is actually in.

LVS passing tells us the layout and the schematic agree. It does not by itself say the
ground plane is one connected piece rather than several that happen to carry the same
label, because a label sits on whichever piece it lands on and the others stay unnamed.
That distinction matters here: the first construction of the launch leaf left the coplanar
ground 5 um clear of the G pads, so the rails were floating even though a GND label existed.

Corrected 2026-08-31. The first version of this file connected the drawn metal on datatype
0 and ignored the slit layer on datatype 24, which was wrong. Both PDK decks derive the
metal that actually exists as

    metal1 = metal1_drw.join(metal1_filler).not(metal1_slit)

in lvs/rule_decks/layers_definitions.lvs line 166 and in drc/rule_decks/density.drc line
609, identically. A slit is a hole in the metal, not an annotation on top of it, so a tool
that skips the subtraction reports a plane as whole even where slits have cut it apart.
That is the one failure this file exists to catch, so it was checking on the wrong geometry.

The same three datatypes are combined here: drawing on 0, filler on 22, slit subtracted
on 24.
"""
import sys
import pya

PATH = sys.argv[1]
TOP = sys.argv[2] if len(sys.argv) > 2 else None

STACK = [("Metal1", 8), ("Metal2", 10), ("Metal3", 30), ("Metal4", 50),
         ("Metal5", 67), ("TopMetal1", 126), ("TopMetal2", 134)]
VIAS = [("Via1", (19, 0), "Metal1", "Metal2"), ("Via2", (29, 0), "Metal2", "Metal3"),
        ("Via3", (49, 0), "Metal3", "Metal4"), ("Via4", (66, 0), "Metal4", "Metal5"),
        ("TopVia1", (125, 0), "Metal5", "TopMetal1"),
        ("TopVia2", (133, 0), "TopMetal1", "TopMetal2")]
LABELS = (134, 25)

ly = pya.Layout()
ly.read(PATH)
top = ly.cell(TOP) if TOP else ly.top_cell()


def raw(layer, datatype):
    idx = ly.find_layer(layer, datatype)
    return pya.Region() if idx is None else pya.Region(top.begin_shapes_rec(idx)).merged()


l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(ly, top, []))
l2n.dbu = ly.dbu

lay = {}
cut = []
for name, num in STACK:
    drw, filler, slit = raw(num, 0), raw(num, 22), raw(num, 24)
    eff = drw.join(filler).not_(slit)
    cut.append((name, drw.area() * ly.dbu * ly.dbu, slit.count(),
                eff.area() * ly.dbu * ly.dbu))
    # register() both names the region and makes it known to the extractor, so calling
    # make_layer() first would claim the name and then reject the region.
    l2n.register(eff, name)
    lay[name] = eff

for name, spec, _, _ in VIAS:
    idx = ly.find_layer(*spec)
    lay[name] = (l2n.make_polygon_layer(idx, name) if idx is not None
                 else l2n.make_layer(name))

tidx = ly.find_layer(*LABELS)
if tidx is not None:
    l2n.make_text_layer(tidx, "labels")
    l2n.connect(lay["TopMetal2"], l2n.layer_by_name("labels"))

for name, _ in STACK:
    l2n.connect(lay[name])
for name, _, a, b in VIAS:
    l2n.connect(lay[name])
    l2n.connect(lay[a], lay[name])
    l2n.connect(lay[name], lay[b])

l2n.extract_netlist()
circuit = l2n.netlist().circuit_by_name(top.name)

print("%-11s %12s %7s %12s" % ("layer", "drawn um2", "slits", "after cut"))
for name, a_drw, n_slit, a_eff in cut:
    if a_drw:
        print("%-11s %12.0f %7d %12.0f" % (name, a_drw, n_slit, a_eff))

rows = []
for net in circuit.each_net():
    area = 0.0
    for name, _ in STACK:
        try:
            area += l2n.shapes_of_net(net, lay[name], True).area() * ly.dbu * ly.dbu
        except Exception:
            pass
    rows.append((area, net.expanded_name()))

rows.sort(reverse=True)
print()
print("%-14s %12s" % ("net", "metal um2"))
for area, name in rows:
    print("%-14s %12.0f" % (name, area))
print()
print("%d net(s) total" % len(rows))
