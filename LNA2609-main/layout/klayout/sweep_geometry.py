"""Find how large an HBT the PCell, DRC and LVS will actually accept, per flavour.

Owner question of 2026-09-03: what is the maximum geometry, in m and Nx and le and we, that
DRC and LVS allow for npn13G2, npn13G2L and npn13G2V?

The question has three separate answers and they are worth keeping apart, because each has a
different kind of authority.

    The COMPACT MODEL states a validity range in its own header, and that is a statement about
    measured silicon rather than about rules. From
    libs.tech/ngspice/models/sg13g2_hbt_mod.lib:

        npn13G2    Nx = 1 - 10                       emitter 0.07 x 0.90 fixed
        npn13G2L   Nx = 1 - 4,  El = 1 - 2.5
        npn13G2V   Nx = 1 - 4,  El = 1 - 5

    The PCELL enforces nothing outside its parameter dialog. A script may ask for any Nx and
    any le, and the question this file answers first is whether what comes back is still the
    geometry that was asked for: Nx windows, each we by le, on one uniform pitch.

    DRC and LVS are what the owner asked about, and they are measured here rather than
    reasoned about.

This is stage one, the device on its own. It builds every point of the sweep into one layout,
spaced far enough apart that no two interact, checks the geometry of each, and runs a single
DRC over the whole layout. Each marker is then attributed to the device it lands on. Density
rules are reported apart, because a sweep layout's density means nothing.

Stage two is tools/sweep_dut.py, which takes the points that survive here, wraps each in the
full GSG frame and runs DRC and LVS on the finished cell. The frame has limits of its own that
the bare device cannot show: the guard-ring tie, the launching fixture and the ground rails.

Run it with:  klayout -z -nc -r tools/sweep_geometry.py
"""
import collections
import io
import os
import re
import subprocess
import sys

import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROOT = _ROOT
OUT = os.path.join(ROOT, "designlib", "teg", "SWEEP_geometry")
PITCH = 120.0            # far enough apart that no two devices see one another
EMWIND = {"npn13G2": (33, 0), "npn13G2L": (33, 0), "npn13G2V": (156, 0)}

# The model's own stated range, carried here so the report can say where each point stands.
MODEL_RANGE = {
    "npn13G2":  {"Nx": (1, 10), "le": (0.90, 0.90), "we": (0.07, 0.07)},
    "npn13G2L": {"Nx": (1, 4), "le": (1.0, 2.5), "we": (0.07, 0.07)},
    "npn13G2V": {"Nx": (1, 4), "le": (1.0, 5.0), "we": (0.12, 0.12)},
}

# What to try. Nx is pushed well past anything the model claims, because the owner asked for
# the rule limit and not for the model limit. le is swept only where the flavour has one:
# npn13G2 fixes its emitter at 0.90 and is swept in Nx alone.
SWEEP = {
    "npn13G2":  {"Nx": [1, 10, 40, 100, 200, 500, 1000],
                 "le": [0.90], "we": [0.07]},
    "npn13G2L": {"Nx": [1, 4, 40, 200, 500],
                 "le": [1.0, 2.5, 20.0, 100.0], "we": [0.07]},
    "npn13G2V": {"Nx": [1, 4, 40, 200, 500],
                 "le": [1.0, 5.0, 40.0, 200.0], "we": [0.12]},
}


def is_density(rule, text):
    """Density is decided by the marker's own text, not by the shape of the rule name.

    Guessing from the name was wrong. TM1.c and TM2.c look like enclosure rules and read as
    such in the rule list, but every marker they produced here carries the text
    'Global Density Violation' and covers the whole layout bounding box, from -3.35,-130.44 to
    2059.45,3.78. Attributing one of those to a device would have blamed the first cell in the
    sweep for a property of the sweep itself.
    """
    return "Global Density Violation" in text or bool(re.search(r"Fil\.", rule))


def build(flavour, points):
    """Put every point of one flavour's sweep into a single layout, on a wide grid."""
    lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
    liblay = lib.layout()
    pid = liblay.pcell_id(flavour)
    decl = liblay.pcell_declaration(flavour)

    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("SWEEP_%s" % flavour)
    placed = []
    cols = 8
    for i, (nx, le, we) in enumerate(points):
        D = {p.name: p.default for p in decl.get_parameters()}
        D.update({"Nx": nx, "le": "%.4fu" % le, "we": "%.4fu" % we})
        try:
            var = ly.add_pcell_variant(lib, pid, D)
        except Exception as exc:                       # a PCell that refuses is an answer too
            placed.append((nx, le, we, None, "PCell refused: %s" % exc))
            continue
        cell = ly.cell(ly.convert_cell_to_static(var))
        r, c = divmod(i, cols)
        # rows are spaced by the tallest device so nothing overlaps at large Nx
        x = c * (PITCH + cell.dbbox().width())
        y = -r * (PITCH + max(cl.dbbox().height() for cl in [cell]))
        inst = top.insert(pya.CellInstArray(
            cell.cell_index(), pya.Trans(pya.Trans.R0, int(round(x * 1000)),
                                       int(round(y * 1000)))))
        placed.append((nx, le, we, inst.bbox().to_dtype(ly.dbu), cell))
    return ly, top, placed


def geometry(ly, cell, flavour, nx, le, we):
    """Is what the PCell drew the geometry that was asked for?"""
    j = ly.find_layer(*EMWIND[flavour])
    if j is None:
        return "no emitter window layer at all"
    reg = pya.Region(cell.begin_shapes_rec(j)).merged()
    boxes = sorted((p.bbox().to_dtype(ly.dbu) for p in reg.each()),
                   key=lambda b: (b.bottom, b.left))
    if not boxes:
        return "no emitter windows"
    sizes = set((round(b.width(), 4), round(b.height(), 4)) for b in boxes)
    steps = set(round(boxes[i + 1].bottom - boxes[i].bottom, 4)
                for i in range(len(boxes) - 1))
    notes = []
    if len(boxes) != nx:
        notes.append("%d windows, not %d" % (len(boxes), nx))
    if len(sizes) != 1:
        notes.append("%d different window sizes" % len(sizes))
    else:
        w, h = sizes.pop()
        # the drawn window is the emitter as the PCell lays it out; the two are compared
        # against what was asked so a PCell that quietly ignores a parameter is caught
        if abs(w - we) > 0.0005 or abs(h - le) > 0.0005:
            notes.append("window %.3f x %.3f, asked %.3f x %.3f" % (w, h, we, le))
    if len(steps) > 1:
        notes.append("pitch not uniform: %s" % sorted(steps))
    return "; ".join(notes) if notes else "as asked"


def run_drc(path, topcell, rundir):
    env = os.environ
    py = env.get("PDK_PY", "python3")
    deck = env.get("PDK_DRC", "")
    if not deck:
        raise SystemExit("PDK_DRC is not set; source env.sh first")
    os.makedirs(rundir, exist_ok=True)
    with open(os.path.join(rundir, "run.log"), "w") as log:
        subprocess.call([py, os.path.join(deck, "run_drc.py"),
                         "--path=%s" % path, "--topcell=%s" % topcell,
                         "--run_dir=%s" % rundir, "--run_mode=deep", "--mp=4"],
                        stdout=log, stderr=log)
    db = os.path.join(rundir, "%s_%s_full.lyrdb" % (topcell, topcell))
    return db if os.path.exists(db) else None


def markers(db):
    """Every marker as (rule, bbox in microns), read straight out of the results database."""
    txt = io.open(db, encoding="utf-8", errors="replace").read()
    out = []
    for item in re.findall(r"<item>.*?</item>", txt, re.S):
        m = re.search(r"<category>.?([A-Za-z0-9_]+\.[A-Za-z0-9_]+).?</category>", item)
        if not m:
            continue
        pts = [(float(a), float(b))
               for a, b in re.findall(r"\(([-0-9.]+),([-0-9.]+)\)", item)]
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out.append((m.group(1), pya.DBox(min(xs), min(ys), max(xs), max(ys)), item))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for flavour, sw in SWEEP.items():
        points = [(nx, le, we) for le in sw["le"] for we in sw["we"] for nx in sw["Nx"]]
        ly, top, placed = build(flavour, points)
        gds = os.path.join(OUT, "SWEEP_%s.gds" % flavour)
        ly.write(gds)

        db = run_drc(gds, top.name, os.path.join(OUT, "drc_%s" % flavour))
        hits = collections.defaultdict(collections.Counter)
        density = collections.Counter()
        if db:
            for rule, box, item in markers(db):
                if is_density(rule, item):
                    density[rule] += 1
                    continue
                owner = None
                for nx, le, we, bb, cell in placed:
                    if bb is not None and bb.enlarged(2.0, 2.0).overlaps(box):
                        owner = (nx, le, we)
                        break
                hits[owner][rule] += 1

        lo, hi = MODEL_RANGE[flavour]["Nx"]
        lel, leh = MODEL_RANGE[flavour]["le"]
        print("=== %s ===  model says Nx %g-%g, le %g-%g" % (flavour, lo, hi, lel, leh))
        print("   %-5s %-7s %-6s %-34s %s" % ("Nx", "le", "we", "geometry", "DRC beyond density"))
        for nx, le, we, bb, cell in placed:
            if bb is None:
                print("   %-5d %-7.2f %-6.3f %s" % (nx, le, we, cell))
                continue
            g = geometry(ly, cell, flavour, nx, le, we)
            rules = hits.get((nx, le, we), {})
            txt = ", ".join("%s %d" % (k, v) for k, v in sorted(rules.items())) or "clean"
            flag = "" if nx <= hi and lel - 1e-9 <= le <= leh + 1e-9 else "   [model range 밖]"
            print("   %-5d %-7.2f %-6.3f %-34s %s%s" % (nx, le, we, g, txt, flag))
        if density:
            print("   density rules over the whole sweep layout, ignored: %s"
                  % ", ".join("%s %d" % (k, v) for k, v in sorted(density.items())))
        unowned = hits.get(None)
        if unowned:
            print("   markers not attributable to any device: %s"
                  % ", ".join("%s %d" % (k, v) for k, v in sorted(unowned.items())))
        print()


main()
