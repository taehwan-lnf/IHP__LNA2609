"""Orientation marks: a TopMetal2 label inside the seal ring, and a squared top-left corner.

Both were asked for by the owner on 2026-09-03, because the four-fold symmetry of a GSG cell
makes it impossible to tell which way a die or a cell is turned. They answer different
questions and are used together. The label says WHICH cell is under the probe and, being
readable one way up only, which way up it is. The odd corner says which way the whole die is
turned, at a magnification where no text can be read: three corners are right angles and the
top-left keeps the PCell's staircase.

Both were measured through DRC before being adopted. On
GSG_dut_npn13g2_m1_Nx20_le0p9u_we0p07u_sealring, whose baseline is AFil.g 1, GFil.g 1 and
Pad.kR 192, each variant came back with exactly those three and nothing else. On the top cell
the squared corner returned Seal.m 164 where the staircase returned 165, so the staircase was
itself producing one marker.


THE LABEL

It sits in the band between the cell's own TopMetal2 and the ring's. Measured on the built
cell that band is 26.00 um: the cell reaches y = 130.00 and the ring's TopMetal2 hole begins
at y = 156.00. Two clearances are taken out of it. TM2.bR asks 5.00 um from wide TopMetal2,
which the cell's ground plane is, and TM2.b asks 2.00 um from the ring. That leaves 19.00 um.

KLayout's built-in std_font was measured first and rejected. Its glyphs hold a stroke-to-
height ratio near one to fourteen, so a stroke meeting TopMetal2's 2.00 um minimum width needs
a 28.00 um glyph, which does not fit 19.00 um. Cut down to fit, it reported hundreds of
violations:

    mag 16 bias 0.5   191.40 x 12.20 um   width < 2.00: 1   space < 2.00: 131
    mag 20 bias 0.8   239.60 x 15.60 um   width < 2.00: 0   space < 2.00: 129

So the font below is a 5 by 7 bitmap drawn on a PIXEL um grid. Every stroke is exactly one
pixel wide and every gap is at least one pixel, so both TM2.a and TM2.b are met with equality
at PIXEL = 2.00 and with room to spare at the 2.50 used here.

The letterforms are SQUARE, and that is a measured decision rather than a style. A rounded
5 by 7 font was drawn first and every rounded glyph had pixels meeting only at a corner. A
kissing vertex is read as a neck of zero width, so on the four strings the cells carry the
unfilled bitmaps reported 48, 58, 36 and 50 violations of both the width and the space rule.

Filling the joining pixel removes those violations, and _close_corners below still does it, but
it also flattens the roundings: measured per glyph, O gained four pixels, V four, S six and 8
seven, and in the rendered cell V then read as U and N as M. Square glyphs need no filling at
all, which _close_corners reports and which tools/gsg_label_selftest.py asserts. At a 2.50 um
pixel the rounding was a single pixel that a microscope renders as a chamfer either way, so
nothing is lost by squaring.

Look-alike pairs are kept apart on purpose, and one round of that was not enough. 0 carries a
centre dot where O is a plain box and 8 a full centre bar, and B, D, P and R use a narrower
bowl so none collides with 8. S and 5 were at first left identical, written down as accepted;
2 and Z were identical too and that was simply missed. tools/verify_labels.py found both by
reading the label back off the layout, where every DUT decoded as NPN13GZ. Both pairs now
differ: Z breaks its diagonal with a single centre pixel where 2 has a full bar, and S loses
the right end of its top bar and the left end of its bottom bar where 5 keeps both full.

No two glyphs in the font share a bitmap now, and tools/gsg_label_selftest.py asserts it.


THE ODD CORNER

The PCell draws all four corners as staircases of 4.20 um steps running 16.80 um from the
corner, measured on the built cell: the TopMetal2 hull steps
32.200,335.800 -> 36.400,335.800 -> 36.400,340.000 and on up to 49.000,352.600.

THREE corners are squared and the TOP-LEFT is left as the PCell drew it, so the staircase is
the odd corner among three right angles. Owner instruction of 2026-09-03, which reverses the
arrangement adopted earlier the same day; the mark reads the same way round either way, and
this one leaves the PCell's own geometry in place at the corner that carries the meaning.

EVERY layer of the ring is squared at those three, not the metals alone. Seal.f asks 1.00 um
between the Passiv ring outside the seal ring and each seal metal, so squaring the metals
while leaving the Passiv staircase would close that gap at the corner.

Each layer is squared against its own outer and inner bounding box, which keeps every band's
width exactly what it was. That is not a nicety: the deck checks the via rings against fixed
figures rather than minima, EdgeSeal-Cont ring width = 0.16 and EdgeSeal-TopVia2 ring
width = 0.90 among them, so filling the corner with a solid square would widen them there and
fail.
"""
import pya


def bootstrap_pycells():
    """Register the PDK's PyCell libraries, as the technology's autorun pymacro would.

    klayout -b does not run technology autorun macros, so in a batch run SG13_dev is absent and
    pya.Library.library_by_name returns None. This repeats what
    ihp-sg13g2/libs.tech/klayout/tech/pymacros/autorun.lym does: put the PDK python directory and
    the pycell4klayout-api source directory on sys.path, then import every module whose name
    starts with sg13 so that each registers its libraries. Calling it twice does nothing the
    second time, because importing an imported module is a no-op.

    Returns the SG13_dev library, or None if it still cannot be found.
    """
    import importlib
    import os
    import pkgutil
    import sys
    lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
    if lib is not None:
        return lib
    tech = os.environ.get("PDK_TECH")
    tech = os.path.join(tech, "klayout") if tech else os.path.join(
        os.environ.get("PDK_ROOT", ""), os.environ.get("PDK", ""), "libs.tech", "klayout")
    for p in (os.path.join(tech, "python"),
              os.path.join(tech, "python", "pycell4klayout-api", "source", "python")):
        if os.path.isdir(p) and p not in sys.path:
            sys.path.append(p)
    for _finder, modname, _ispkg in pkgutil.iter_modules():
        if modname.startswith("sg13"):
            importlib.import_module(modname)
    return pya.Library.library_by_name("SG13_dev", "sg13g2")

U = 1000.0

PIXEL = 2.50        # one pixel of the label; TM2.a and TM2.b both ask 2.00
GLYPH_W, GLYPH_H = 5, 7
ADVANCE = 6         # pixels from one glyph origin to the next: five wide plus one blank
GAP_CELL = 5.00     # TM2.bR, the space to the cell's wide ground plane
GAP_RING = 2.00     # TM2.b, the space to the ring
CORNER_EXT = 25.0   # how far the squaring reaches; the staircase runs 16.80

FONT = {
    " ": ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
    "-": ("     ", "     ", "     ", "#####", "     ", "     ", "     "),
    ".": ("     ", "     ", "     ", "     ", "     ", ".##..", ".##.."),
    "=": ("     ", "     ", "#####", "     ", "#####", "     ", "     "),
    "0": ("#####", "#...#", "#...#", "#.#.#", "#...#", "#...#", "#####"),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": ("#####", "....#", "....#", "#####", "#....", "#....", "#####"),
    "3": ("#####", "....#", "....#", "#####", "....#", "....#", "#####"),
    "4": ("#...#", "#...#", "#...#", "#####", "....#", "....#", "....#"),
    "5": ("#####", "#....", "#....", "#####", "....#", "....#", "#####"),
    "6": ("#####", "#....", "#....", "#####", "#...#", "#...#", "#####"),
    "7": ("#####", "....#", "....#", "....#", "....#", "....#", "....#"),
    "8": ("#####", "#...#", "#...#", "#####", "#...#", "#...#", "#####"),
    "9": ("#####", "#...#", "#...#", "#####", "....#", "....#", "#####"),
    "A": ("#####", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#..#.", "#..#.", "####.", "#..#.", "#..#.", "####."),
    "C": ("#####", "#....", "#....", "#....", "#....", "#....", "#####"),
    "D": ("####.", "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": ("#####", "#....", "#....", "#..##", "#...#", "#...#", "#####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("....#", "....#", "....#", "....#", "#...#", "#...#", "#####"),
    "K": ("#..#.", "#..#.", "#..#.", "####.", "#..#.", "#..#.", "#..#."),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "#####", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "###.#", "#.###", "#..##", "#...#", "#...#"),
    "O": ("#####", "#...#", "#...#", "#...#", "#...#", "#...#", "#####"),
    "P": ("####.", "#..#.", "#..#.", "####.", "#....", "#....", "#...."),
    "Q": ("#####", "#...#", "#...#", "#...#", "#.###", "#..#.", "#####"),
    "R": ("####.", "#..#.", "#..#.", "####.", "#.#..", "#.##.", "#..#."),
    "S": ("####.", "#....", "#....", "#####", "....#", "....#", ".####"),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", "#####"),
    "V": ("#...#", "#...#", "#...#", "#...#", "#####", ".###.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#####", "#...#"),
    "X": ("#...#", "#...#", "#####", "..#..", "#####", "#...#", "#...#"),
    "Y": ("#...#", "#...#", "#####", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "....#", "..#..", "#....", "#....", "#####"),
}


def _bitmap(text):
    on = set()
    for k, ch in enumerate(text.upper()):
        rows = FONT.get(ch)
        if rows is None:
            raise SystemExit("gsg_label: no glyph for %r; add it to FONT" % ch)
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v == "#":
                    on.add((k * ADVANCE + c, GLYPH_H - 1 - r))
    return on


def _close_corners(on):
    """Fill the pixel that joins two diagonally touching pixels along an edge.

    Two pixels meeting at a corner leave a point contact, and a width check can read that
    point as a neck of zero width. Filling the pixel beside one of them turns the contact into
    a shared edge. The horizontal neighbour is taken, so a letter thickens sideways rather
    than growing taller and eating into the clearance above and below.
    """
    added = 0
    changed = True
    while changed:
        changed = False
        for (x, y) in sorted(on):
            for dx in (1, -1):
                if (x + dx, y + 1) in on and (x + dx, y) not in on and (x, y + 1) not in on:
                    on.add((x + dx, y))
                    added += 1
                    changed = True
    return added


def text_size(text):
    """Width and height in microns of the label this text would draw."""
    return (len(text) * ADVANCE - 1) * PIXEL, GLYPH_H * PIXEL


def text_region(text, x0, y0):
    """Draw the text as PIXEL-micron squares with the lower left of the string at (x0, y0)."""
    on = _bitmap(text)
    fixed = _close_corners(on)
    r = pya.Region()
    for (px, py) in on:
        r.insert(pya.Box(int(round((x0 + px * PIXEL) * U)), int(round((y0 + py * PIXEL) * U)),
                         int(round((x0 + (px + 1) * PIXEL) * U)),
                         int(round((y0 + (py + 1) * PIXEL) * U))))
    return r.merged(), fixed


def check_label(reg, name):
    """Refuse to write a label that breaks TopMetal2's own width or space rule.

    Checked here rather than left to the DRC run, because a label is added to fourteen cells
    at once and a glyph added later could break one of them quietly.
    """
    w = reg.width_check(int(2.00 * U)).count()
    s = reg.space_check(int(2.00 * U)).count()
    if w or s:
        raise SystemExit("gsg_label: %s violates TopMetal2 rules, width %d space %d"
                         % (name, w, s))


SQUARE_CORNERS = ("bottom-left", "bottom-right", "top-right")

# Every corner, for a ring that carries no orientation mark at all. The chip's own outer
# ring took this on the owner's instruction of 2026-09-05; the subcells keep
# SQUARE_CORNERS above, so their top-left staircase still says which way a cell faces.
ALL_CORNERS = SQUARE_CORNERS + ("top-left",)


def _corner_box(o, e, which):
    """One corner of a layer's bounding box, e microns on a side."""
    if which == "top-left":
        return pya.Box(o.left, o.top - e, o.left + e, o.top)
    if which == "top-right":
        return pya.Box(o.right - e, o.top - e, o.right, o.top)
    if which == "bottom-left":
        return pya.Box(o.left, o.bottom, o.left + e, o.bottom + e)
    if which == "bottom-right":
        return pya.Box(o.right - e, o.bottom, o.right, o.bottom + e)
    raise SystemExit("gsg_label: no corner named %r" % which)


def square_corner(ly, cell, ext=CORNER_EXT, corners=SQUARE_CORNERS):
    """Square the named corners of every layer of a seal ring cell, leaving the rest alone.

    The default squares three and leaves the top-left staircase standing, which is the mark
    the owner asked for on 2026-09-03.

    Returns the list of (layer, band width) so the caller can show that no band changed.
    """
    done = []
    e = int(round(ext * U))
    for j in ly.layer_indexes():
        r = pya.Region(cell.begin_shapes_rec(j)).merged()
        if r.is_empty():
            continue
        holes = r.holes()
        if holes.is_empty():
            continue
        o, h = r.bbox(), holes.bbox()
        squared = pya.Region(o) - pya.Region(h)
        clip = pya.Region()
        for which in corners:
            clip.insert(_corner_box(o, e, which))
        cell.shapes(j).clear()
        cell.shapes(j).insert((r - clip) | (squared & clip))
        done.append((str(ly.get_info(j)), (h.left - o.left) / U))
    return done
