"""Read the TopMetal2 label back off the layout and check it against what the cell contains.

Owner instruction of 2026-09-03. The point of the check is that it must not lean on the cell
name. gen_sealed.py builds the label BY PARSING THE NAME, so comparing the label with the name
would only prove that one function agrees with itself. A wrong name would produce a wrong
label and a clean report.

So this reads two independent things and compares them.

    WHAT IS ON THE CHIP.  The label is drawn as 2.50 um squares of TopMetal2, not as text, so
    it cannot be queried as a string. It is rasterised back instead: the sealed cell's OWN
    shapes on 134/0 are exactly the label, the ring and the inner cell being instances whose
    shapes belong to their own cells, so the grid is read straight off them and each 5 by 7
    slot is matched against gsg_label.FONT. What comes out is what a microscope would read.

    WHAT THE CELL CONTAINS.  Taken from lvs_report/*_extracted.cir, which is the LVS
    extractor's own reading of the layout: the device model name and its we, le and Nx, or the
    rppd pair for LOAD, or the absence of any device for OPEN, SHORT and THRU. Nx there is
    counted from emitter shapes rather than read from a parameter, so it is a measurement of
    the drawn geometry.

A_E(final) is then recomputed from the EXTRACTED we, le and Nx with gsg_frame.DELTA and
compared against the number the label carries. Nothing in that path passes through the cell
name.

Run it with:  klayout -z -nc -r tools/verify_labels.py
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_frame as F
import gsg_label as L

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROOT = _ROOT
DEV = os.path.join(ROOT, "designlib", "teg")
TM2 = (134, 0)

# what each standard's label claims, against what its extraction must show
STANDARD_TRUTH = {
    "OPEN":  ("no device between the two launches", lambda d: d["npn"] == 0 and d["rppd"] == 0),
    "SHORT": ("no device, launches taken to ground", lambda d: d["npn"] == 0 and d["rppd"] == 0),
    "THRU":  ("no device, launches joined", lambda d: d["npn"] == 0 and d["rppd"] == 0),
    "LOAD":  ("two rppd", lambda d: d["npn"] == 0 and d["rppd"] == 2),
}

def _canon(rows):
    """One spelling for a glyph, so the font and the raster can be compared.

    The font writes an off pixel as a full stop in the letters and digits but as a space in the
    blank, the hyphen, the full stop and the equals sign. Comparing the raw strings therefore
    matched only the four that happen to use spaces, and every other glyph decoded as a
    question mark. That the equals sign alone came through was the clue. Both sides are
    normalised here.
    """
    return tuple("".join("#" if ch == "#" else "." for ch in row) for row in rows)


GLYPHS = {_canon(rows): ch for ch, rows in L.FONT.items()}


def read_label(path, name):
    """Rasterise the sealed cell's own TopMetal2 back into strings, one per line of text.

    The raster is built from the POLYGONS, never from their bounding boxes. The label is stored
    merged, so one polygon can be an L or a ring, and its bounding box covers pixels that are
    not filled. Building the raster from bounding boxes filled in the inside of every letter
    and left only the equals sign and the full stop legible, those two being the only glyphs
    whose shape is its own bounding box.
    """
    ly = pya.Layout()
    ly.read(path)
    top = ly.top_cell()
    reg = pya.Region(top.shapes(ly.layer(*TM2))).merged()   # own shapes, not the instances'
    if reg.is_empty():
        return []

    polys = sorted(reg.each(), key=lambda q: q.bbox().bottom)
    groups, cur = [], [polys[0]]
    span = int(round(L.GLYPH_H * L.PIXEL / ly.dbu))
    for q in polys[1:]:
        if q.bbox().bottom - cur[-1].bbox().bottom > span:
            groups.append(cur)
            cur = [q]
        else:
            cur.append(q)
    groups.append(cur)

    out = []
    pix = int(round(L.PIXEL / ly.dbu))
    half = pix // 4
    for grp in groups:
        sub = pya.Region()
        for q in grp:
            sub.insert(q)
        bb = sub.bbox()
        ncol = int(round(bb.width() / float(pix)))
        on = set()
        for c in range(ncol):
            for r in range(L.GLYPH_H):
                cx = bb.left + int((c + 0.5) * pix)
                cy = bb.bottom + int((r + 0.5) * pix)
                probe = pya.Region(pya.Box(cx - half, cy - half, cx + half, cy + half))
                if not (probe & sub).is_empty():
                    on.add((c, r))
        text = ""
        for k in range(0, ncol, L.ADVANCE):
            rows = tuple("".join("#" if (k + c, L.GLYPH_H - 1 - r) in on else "."
                                 for c in range(L.GLYPH_W))
                         for r in range(L.GLYPH_H))
            text += GLYPHS.get(rows, "?")
        out.append(text.rstrip())
    return out


def read_extraction(cell):
    """What the LVS extractor found: the device model and its measured geometry."""
    hits = glob.glob(os.path.join(DEV, cell, "lvs_report", "*_extracted.cir"))
    if not hits:
        return None
    txt = io.open(hits[0], encoding="utf-8", errors="replace").read()
    d = {"npn": 0, "rppd": 0, "model": None, "we": None, "le": None, "nx": None, "m": None}
    for line in txt.splitlines():
        m = re.search(r"\b(npn13G2[lv]?)\s+we=([0-9.]+)n\s+le=([0-9.]+)n\s+Nx=(\d+)\s+m=(\d+)",
                      line)
        if m:
            d["npn"] += 1
            d["model"] = m.group(1)
            d["we"] = float(m.group(2)) / 1000.0
            d["le"] = float(m.group(3)) / 1000.0
            d["nx"] = int(m.group(4))
            d["m"] = int(m.group(5))
        if re.search(r"\brppd\b", line):
            d["rppd"] += 1
    return d


def flavour_of(model):
    return {"npn13G2": "npn13G2", "npn13G2l": "npn13G2L", "npn13G2v": "npn13G2V"}[model]


cells = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DEV, "*_sealring")))
bad = []
print("%-48s %-11s %-14s %-30s %s"
      % ("CELL", "LABEL 1", "LABEL 2", "EXTRACTED", "VERDICT"))
print("-" * 126)
for cell in cells:
    gds = os.path.join(DEV, cell, cell + ".gds")
    lines = read_label(gds, cell)
    if len(lines) != 2:
        bad.append("%s: read %d label lines, expected 2" % (cell, len(lines)))
        print("%-48s %s" % (cell, lines))
        continue
    bottom, topline = lines[0], lines[1]      # sorted by y, so the first is the lower line
    d = read_extraction(cell)
    if d is None:
        bad.append("%s: no extracted netlist to check against" % cell)
        print("%-48s %-11s %-14s %s" % (cell, topline, bottom, "(no LVS report)"))
        continue

    if topline in STANDARD_TRUTH:
        desc, ok = STANDARD_TRUTH[topline]
        got = "npn %d, rppd %d" % (d["npn"], d["rppd"])
        verdict = "OK" if ok(d) else "MISMATCH, label says %s" % desc
    elif d["model"] is None:
        got = "no device found"
        verdict = "MISMATCH, label names a transistor"
    else:
        flav = flavour_of(d["model"])
        dwe, dle = F.DELTA[flav]
        ae = d["m"] * d["nx"] * (d["we"] + dwe) * (d["le"] + dle)
        got = "%s we=%.3f le=%.3f Nx=%d m=%d" % (d["model"], d["we"], d["le"], d["nx"], d["m"])
        want = "AE=%.4fUM2" % ae
        problems = []
        if topline != flav.upper():
            problems.append("flavour: label %s, extracted %s" % (topline, flav.upper()))
        if bottom != want:
            problems.append("area: label %s, recomputed %s" % (bottom, want))
        verdict = "OK" if not problems else "MISMATCH, " + "; ".join(problems)
    if not verdict.startswith("OK"):
        bad.append("%s: %s" % (cell, verdict))
    print("%-48s %-11s %-14s %-30s %s" % (cell, topline, bottom, got, verdict))

print()
if bad:
    print("불일치 %d 건" % len(bad))
    for b in bad:
        print("   %s" % b)
    raise SystemExit(1)
print("셀 %d 개 모두 각인과 실제 내용이 일치한다" % len(cells))
