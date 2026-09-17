"""Write drc_summary.txt and lvs_summary.txt beside each cell's own report.

Owner instruction 2026-09-02: both reports live in the cell's own directory, and each carries
a summary giving the number, the title, the description and the count.

    devices/<cell>/drc_report/drc_summary.txt
    devices/<cell>/lvs_report/lvs_summary.txt

The summaries are plain text and small, so .gitignore keeps them while it still drops the
logs and the databases they are derived from. That is the point of writing them: the bulky
inputs are regenerable, the conclusion is what a reader needs months later.

DRC has numbered rules and the number is inside each rule's own description, as in
"5.6. AFil.g: Min. global Activ density [%]: 35.00." It is taken from there rather than kept
in a table here, which would go stale the moment the deck grows a rule.

LVS has no numbered rules. What it has is a cross-reference: X(layout schematic flag) for the
circuit, then N, P and D records for nets, pins and devices, each ending in 1 when the pair
matched and 0 when it did not. Those counts are the summary, and any record ending in 0 is
listed out.
"""
import io
import os
import re
import sys

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
DEV = os.path.join(PROJECT, "designlib", "teg")
RULE_NO = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)*)\.?\s")


def drc_summary(cell, folder):
    dbs = [f for f in os.listdir(folder) if f.endswith("_full.lyrdb")]
    if not dbs:
        return None
    path = os.path.join(folder, dbs[0])
    b = io.open(path, encoding="utf-8", errors="replace").read()
    desc = dict(re.findall(
        r"<name>([A-Za-z0-9_.]+)</name>\s*<description>([^<]*)</description>", b))
    counts = {}
    # Every inline <category>, dot or no dot. Requiring a dot dropped via2_drw_Offgrid,
    # via3_drw_Offgrid and via4_drw_Offgrid, which held 14,628 markers each on the top, so
    # this file reported 11 rules and 3,291 items where the database held 14 and 47,175.
    # See the docstring of sum_drc.py for why matching inline tags alone is safe.
    for k in re.findall(r"<category>'?([A-Za-z0-9_.]+)'?</category>", b):
        counts[k] = counts.get(k, 0) + 1

    rows = []
    for rule in sorted(counts):
        text = desc.get(rule, "")
        m = RULE_NO.match(text)
        num = m.group(1) if m else "-"
        body = text[m.end():].strip() if m else text.strip()
        body = re.sub(r"^%s\s*:\s*" % re.escape(rule), "", body)
        rows.append((num, rule, body, counts[rule]))

    out = ["DRC summary", "cell     : %s" % cell,
           "database : %s" % os.path.basename(path),
           "rules    : %d" % len(rows),
           "items    : %d" % sum(r[3] for r in rows), ""]
    if not rows:
        out.append("No rule reported a violation.")
    else:
        out.append("%-4s %-8s %-14s %8s  %s" % ("#", "NUMBER", "TITLE", "COUNT",
                                                "DESCRIPTION"))
        out.append("-" * 108)
        for i, (num, rule, body, n) in enumerate(rows, start=1):
            out.append("%-4d %-8s %-14s %8d  %s" % (i, num, rule, n, body[:70]))
    return "\n".join(out) + "\n"


def lvs_summary(cell, folder):
    dbs = [f for f in os.listdir(folder) if f.endswith(".lvsdb")]
    log = os.path.join(folder, "run.log")
    if not dbs:
        return None
    path = os.path.join(folder, dbs[0])
    b = io.open(path, encoding="utf-8", errors="replace").read()

    verdict = "unknown"
    if os.path.exists(log):
        t = io.open(log, encoding="utf-8", errors="replace").read().lower()
        if "netlists match" in t:
            verdict = "MATCH"
        elif "netlists don't match" in t or "netlists dont match" in t:
            verdict = "MISMATCH"
        elif "can't find a schematic counterpart" in t:
            verdict = "NO COUNTERPART FOR TOP CELL"

    # The circuit record has no closing bracket on its own line: it reads
    #   X(GSG_open_sealring GSG_OPEN_SEALRING 1
    # with the nets, pins and devices nested under it, so the flag is followed by a
    # newline rather than by ")". Requiring the bracket dropped the row entirely.
    xrefs = re.findall(r"X\((\S+)\s+(\S+)\s+([01])\s", b)
    kinds = {"N": "nets", "P": "pins", "D": "devices"}
    tally = {k: [0, 0] for k in kinds}
    unmatched = []
    for kind, a, c, flag in re.findall(r"\b([NPD])\((\d+) (\d+) ([01])\)", b):
        tally[kind][0 if flag == "1" else 1] += 1
        if flag == "0":
            unmatched.append((kinds[kind], a, c))

    out = ["LVS summary", "cell     : %s" % cell,
           "database : %s" % os.path.basename(path),
           "verdict  : %s" % verdict, ""]
    out.append("%-4s %-10s %-14s %8s  %s" % ("#", "NUMBER", "TITLE", "COUNT",
                                             "DESCRIPTION"))
    out.append("-" * 108)
    i = 1
    for cname, sname, flag in xrefs:
        out.append("%-4d %-10s %-14s %8s  layout %s against schematic %s"
                   % (i, "circuit", "matched" if flag == "1" else "MISMATCH", "1",
                      cname, sname))
        i += 1
    for kind in ("N", "P", "D"):
        good, bad = tally[kind]
        out.append("%-4d %-10s %-14s %8d  %d matched, %d unmatched"
                   % (i, kinds[kind], "matched" if bad == 0 else "MISMATCH",
                      good + bad, good, bad))
        i += 1
    if unmatched:
        out += ["", "Unmatched pairs, given as (layout index, schematic index):"]
        for kind, a, c in unmatched:
            out.append("   %-8s layout %-5s schematic %s" % (kind, a, c))
    return "\n".join(out) + "\n"


def do(cell):
    base = os.path.join(DEV, cell)
    wrote = []
    for sub, fn, name in (("drc_report", drc_summary, "drc_summary.txt"),
                          ("lvs_report", lvs_summary, "lvs_summary.txt")):
        folder = os.path.join(base, sub)
        if not os.path.isdir(folder):
            continue
        text = fn(cell, folder)
        if text is None:
            continue
        io.open(os.path.join(folder, name), "w", encoding="utf-8",
                newline="\n").write(text)
        wrote.append(name)
    return wrote


cells = sys.argv[1:] or sorted(
    d for d in os.listdir(DEV) if os.path.isdir(os.path.join(DEV, d)))
for c in cells:
    w = do(c)
    if w:
        print("%-52s %s" % (c, ", ".join(w)))
