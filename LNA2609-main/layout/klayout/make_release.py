"""Collect only the cells the chip actually carries into one release directory.

Owner instruction of 2026-09-04: keep the cells that go to IHP, meaning the top cell and every
instance beneath it, in a directory of their own.

WHERE IT GOES, AND WHY NOT A NEW FOLDER

README.md already reserves out/<date>_<rev>/ for "what was actually submitted, plus its
reports and MANIFEST", and that directory is still empty. This writes there rather than
inventing a second convention beside it. <rev> is the short git commit, so the path names
exactly which state of the repository the release was cut from, and cutting the same commit
twice overwrites the same folder instead of piling up near-copies.

WHAT IS COPIED, AND WHAT IS NOT

    the top GDS, at the root      the one file IHP receives, and the only copy of it in the
                                  release. It is self-contained: the assembly copies each
                                  subcell's whole tree into it, so it needs nothing else in
                                  this folder to be read.
    cells/<name>/                 for each cell the chip reaches, its layout and its
                                  schematic side and the two summaries. This is provenance
                                  for us, not part of the submission. The top's own directory
                                  holds no GDS, only a note pointing at the root copy, because
                                  two identical files of the same name in one release is a
                                  question and not a safeguard.

The DRC and LVS databases and logs are NOT copied. They run to hundreds of megabytes, they
are regenerable from the sources beside them, and .gitignore already drops them for the same
reason. The summaries that name every rule and its count ARE copied, those being the part a
person reads.

WHICH CELLS

Decided by walking the top cell's own hierarchy, never by reading a generator's list, so a
cell that fell out of the design cannot ride along on a stale list. KLayout rename suffixes
such as $3 are stripped, those being copies of one cell rather than cells of their own.

Run it with:  klayout -z -nc -r tools/make_release.py
"""
import hashlib
import io
import os
import shutil
import subprocess
import time

import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROOT = _ROOT
DEV = os.path.join(ROOT, "designlib", "teg")
TOP = "LNA2609_nofill"

# per cell: what is source or evidence, and what is regenerable bulk
KEEP_FILES = (".gds", ".sch", ".sym", ".spice")
KEEP_NAMED = ("xschemrc",)
KEEP_REPORT = ("drc_summary.txt", "lvs_summary.txt")
KEEP_REPORT_SUFFIX = ("_extracted.cir",)


def git(*args):
    try:
        return subprocess.check_output(("git",) + args, cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reached_cells():
    """Every cell directory the top's hierarchy actually reaches."""
    ly = pya.Layout()
    ly.read(os.path.join(DEV, TOP, TOP + ".gds"))
    names = {TOP}

    def walk(cell):
        for inst in cell.each_inst():
            child = ly.cell(inst.cell_index)
            names.add(child.name.split("$")[0])
            walk(child)

    walk(ly.top_cell())
    return sorted(n for n in names if os.path.isdir(os.path.join(DEV, n)))


def verdicts(cell):
    """The DRC rule list and the LVS verdict as the summaries record them."""
    drc = lvs = "no report"
    p = os.path.join(DEV, cell, "drc_report", "drc_summary.txt")
    if os.path.exists(p):
        rows = []
        for line in io.open(p, encoding="utf-8", errors="replace"):
            parts = line.split()
            if len(parts) > 3 and parts[0].isdigit():
                rows.append("%s %s" % (parts[2], parts[3]))
        drc = ", ".join(rows) or "clean"
    p = os.path.join(DEV, cell, "lvs_report", "lvs_summary.txt")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if line.startswith("verdict"):
                lvs = line.split(":", 1)[1].strip()
                break
    return drc, lvs


def copy_cell(cell, dest):
    """Copy one cell's sources and summaries.

    The top cell's GDS is skipped here, because the same bytes are already at the root of the
    release as the deliverable. Copying it twice cost 18.3 MB and, worse, put two files of the
    same name in one directory with nothing to say which was which; the owner hit exactly that
    on 2026-09-04. A note is left in its place so the absence reads as deliberate.
    """
    os.makedirs(dest)
    n = 0
    for f in sorted(os.listdir(os.path.join(DEV, cell))):
        src = os.path.join(DEV, cell, f)
        if cell == TOP and f.endswith(".gds"):
            io.open(os.path.join(dest, "WHERE_IS_THE_GDS.txt"), "w",
                    encoding="utf-8", newline="\n").write(
                "The top cell's GDS is not here. It is the one file at the root of this\n"
                "release, ../../%s.gds, which is what IHP receives and what MANIFEST.md\n"
                "names with its md5. It was in both places until 2026-09-04 and that only\n"
                "made it unclear which of two identical files to use.\n" % TOP)
            n += 1
            continue
        if os.path.isfile(src) and (f.endswith(KEEP_FILES) or f in KEEP_NAMED):
            shutil.copy2(src, os.path.join(dest, f))
            n += 1
    for rep in ("drc_report", "lvs_report"):
        srcd = os.path.join(DEV, cell, rep)
        if not os.path.isdir(srcd):
            continue
        for f in sorted(os.listdir(srcd)):
            if f in KEEP_REPORT or f.endswith(KEEP_REPORT_SUFFIX):
                os.makedirs(os.path.join(dest, rep), exist_ok=True)
                shutil.copy2(os.path.join(srcd, f), os.path.join(dest, rep, f))
                n += 1
    return n


def tree_size(path):
    return sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(path) for f in fs)


def main():
    cells = reached_cells()
    sha = git("rev-parse", "--short", "HEAD")
    dirty = git("status", "--porcelain")
    stamp = time.strftime("%Y-%m-%d")
    out = os.path.join(ROOT, "out", "%s_%s" % (stamp, sha))
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "cells"))

    topgds = os.path.join(DEV, TOP, TOP + ".gds")
    shutil.copy2(topgds, os.path.join(out, TOP + ".gds"))

    rows = []
    for c in cells:
        n = copy_cell(c, os.path.join(out, "cells", c))
        drc, lvs = verdicts(c)
        g = os.path.join(DEV, c, c + ".gds")
        rows.append((c, os.path.getsize(g) if os.path.exists(g) else 0, n, drc, lvs))

    pdk = git("-C", os.environ.get("PDK_ROOT", ""), "rev-parse", "--short", "HEAD")
    lines = []
    lines.append("# MANIFEST  %s  %s\n" % (stamp, sha))
    lines.append("\nWhat IHP receives is the single file at the root of this directory:\n\n")
    lines.append("    %s.gds   %.1f MB   md5 %s\n"
                 % (TOP, os.path.getsize(topgds) / 1e6, md5(topgds)))
    lines.append("\nThat file is self-contained. The assembly copies each subcell's whole tree\n"
                 "into it, so nothing else here is needed to read it. Everything under cells/ is\n"
                 "provenance for us.\n")
    lines.append("\n## How this set was chosen\n\n"
                 "By walking the top cell's own hierarchy in the GDS, not by reading any\n"
                 "generator's list, so a cell that fell out of the design cannot ride along on a\n"
                 "stale list. %d of the %d directories under devices/ are reached.\n"
                 % (len(cells), len([d for d in os.listdir(DEV)
                                     if os.path.isdir(os.path.join(DEV, d))])))
    lines.append("\n## Provenance\n\n")
    lines.append("| item | value |\n|---|---|\n")
    lines.append("| design commit | `%s` |\n" % git("rev-parse", "HEAD"))
    lines.append("| working tree | %s |\n" % ("clean" if not dirty else "NOT CLEAN at cut time"))
    lines.append("| PDK commit | `%s` |\n" % pdk)
    lines.append("| cut on | %s |\n" % time.strftime("%Y-%m-%d %H:%M:%S %z"))
    lines.append("\n## Cells\n\n")
    lines.append("| cell | GDS MB | files | DRC | LVS |\n|---|---|---|---|---|\n")
    for c, sz, n, drc, lvs in rows:
        lines.append("| `%s` | %.2f | %d | %s | %s |\n"
                     % (c, sz / 1e6, n, drc, lvs))
    io.open(os.path.join(out, "MANIFEST.md"), "w", encoding="utf-8",
            newline="\n").write("".join(lines))

    print("release  %s" % out)
    print("cells    %d of %d directories under devices/"
          % (len(cells), len([d for d in os.listdir(DEV)
                              if os.path.isdir(os.path.join(DEV, d))])))
    print("size     %.1f MB, against %.1f MB for the same cells in devices/"
          % (tree_size(out) / 1e6,
             sum(tree_size(os.path.join(DEV, c)) for c in cells) / 1e6))
    if dirty:
        print("WARNING  the working tree was not clean when this was cut")


main()
