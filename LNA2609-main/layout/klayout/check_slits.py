"""Replicate the placement-dependent slit rules so the geometry can be iterated in seconds.

The full deck takes minutes, which is too slow to steer a slit pattern by. These are the
deck expressions copied out of sg13g2_maximal.drc and density.drc, so a pass here is a fast
filter and not a verdict. The real run still decides.

Only two of the six slit rules depend on where the slits go, and those are the two checked
here:

    Slt.c   sltc = Metal.not(Recog_or_dfpad_all)
            mit  = sltc.not(Metal_slit)
            mit.sized(-3).sized(-12).sized(15)     survives a 15 um shrink, so wider
                                                   than 30 um in both directions
    Slt.i   slit area / plate area, on plates that survive an opening by 17.5 um,
            must be at least 6 percent

The other four hold by construction and are noted rather than measured. Every slit drawn is
the same 5 x 5 um square, which is above the 2.80 um minimum of Slt.a and below the 20 um
maximum of Slt.b. The builder places a slit only where it lies inside metal.sized(-1.5),
which is more enclosure than the 1.00 um Slt.f asks for, and it rejects any candidate that
touches dfpad grown by 1 um, which is what Slt.e is about.
"""
import sys
import pya

PATH = sys.argv[1]
MET = {"M1": (8, 0), "M2": (10, 0), "M3": (30, 0), "M4": (50, 0), "M5": (67, 0),
       "TM1": (126, 0), "TM2": (134, 0)}

ly = pya.Layout()
ly.read(PATH)
top = ly.top_cell()
U = 1.0 / ly.dbu


def reg(layer):
    idx = ly.find_layer(*layer)
    return pya.Region() if idx is None else pya.Region(top.begin_shapes_rec(idx)).merged()


dfpad = reg((41, 0)).join(reg((41, 35))).join(reg((41, 36))).merged()
exempt = dfpad.join(reg((99, 0))).merged()
pad = dfpad.not_outside(reg((9, 0)))

print("%-4s %9s %6s %8s | %-8s | %s"
      % ("", "metal um2", "slits", "on pads", "Slt.c", "Slt.i slit density"))
bad = 0
for k in ("M1", "M2", "M3", "M4", "M5", "TM1", "TM2"):
    m, s = reg(MET[k]), reg((MET[k][0], 24))
    if m.is_empty():
        continue

    on_pad = s.and_(pad).count()                                    # Slt.e
    mit = m.not_(exempt).not_(s)                                    # Slt.c
    c = mit.sized(-3 * U).sized(-12 * U).sized(15 * U).count()

    plates = m.sized(-17.5 * U).sized(17.5 * U)                     # Slt.i
    pa = plates.area() * ly.dbu * ly.dbu
    sa = s.and_(plates).area() * ly.dbu * ly.dbu
    dens = (100.0 * sa / pa) if pa > 0 else None
    i_bad = dens is not None and dens < 6.0

    bad += c + on_pad + (1 if i_bad else 0)
    print("%-4s %9.0f %6d %8d | %-8d | %s"
          % (k, m.area() * ly.dbu * ly.dbu, s.count(), on_pad, c,
             "no plate over 35x35" if dens is None
             else "%.2f%% of %.0f um2%s" % (dens, pa, "   BELOW 6%" if i_bad else "")))

print()
print("placement-dependent slit items outstanding: %d" % bad)
