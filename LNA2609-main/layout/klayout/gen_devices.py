# Build one folder per PDK device, each holding a schematic and a layout that instantiate
# that device once. The shape mirrors Cadence: folder = cell, and the two files are its
# schematic and layout views.
#
# Run under KLayout so the PCell library is available:
#     klayout -z -r tools/gen_devices.py
#
# Only devices that have BOTH a KLayout PCell and an xschem symbol are built, because a
# folder with one empty view would be misleading. That is 14 of the 32 PCells.
#
# Folder name = PCell name + the primary sizing parameters at their default values.
# The parameter list is a per-device whitelist rather than a heuristic: KLayout exposes
# roughly twenty parameters per device, most of them display or derived-value fields, and
# folding those into a directory name would make it unreadable and unstable.
# Dots become 'p' so a name carries exactly one dot, the file extension.

import os
import re
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
OUTDIR = os.path.join(PROJECT, "designlib", "teg")
SYMDIR = os.path.join(os.environ["PDK_ROOT"], "ihp-sg13g2", "libs.tech", "xschem", "sg13g2_pr")

# pcell name -> (xschem symbol stem, [primary sizing parameters])
# The symbol stem differs from the PCell name in case for the HBT variants; that is a
# property of the PDK, not a typo here.
DEVICES = [
    ("npn13G2",   "npn13G2",   ["Nx", "le", "we"]),
    ("npn13G2L",  "npn13G2l",  ["Nx", "le", "we"]),
    ("npn13G2V",  "npn13G2v",  ["Nx", "le", "we"]),
    ("rhigh",     "rhigh",     ["w", "l"]),
    ("rppd",      "rppd",      ["w", "l"]),
    ("rsil",      "rsil",      ["w", "l"]),
    ("ntap1",     "ntap1",     ["w", "l"]),
    ("ptap1",     "ptap1",     ["w", "l"]),
    ("dantenna",  "dantenna",  ["w", "l"]),
    ("dpantenna", "dpantenna", ["w", "l"]),
    ("pnpMPA",    "pnpMPA",    ["w", "l"]),
    ("isolbox",   "isolbox",   ["l", "w"]),
    ("bondpad",   "bondpad",   ["diameter"]),
    ("inductor3", "inductor3", ["w", "s", "d", "nr_r"]),
]

XSCHEM_VERSION = "3.4.4"


def slug(value):
    """Make a parameter value safe for a directory name."""
    s = str(value).strip()
    s = s.replace(".", "p").replace("-", "m").replace("+", "")
    return re.sub(r"[^0-9A-Za-z_]", "", s)


def symbol_template(stem):
    """Return the template assignment of a .sym as an ordered list of (key, value).

    The template is the symbol's own declaration of its default parameters, so copying it
    verbatim keeps the generated schematic consistent with what xschem would place by
    hand. Inventing the parameter list here would drift from the PDK on the next pull.
    """
    path = os.path.join(SYMDIR, stem + ".sym")
    text = open(path, encoding="utf-8").read()
    m = re.search(r'template="(.*?)"', text, re.S)
    if not m:
        return []
    out = []
    for token in m.group(1).split("\n"):
        token = token.strip()
        if not token or "=" not in token:
            continue
        k, v = token.split("=", 1)
        out.append((k.strip(), v.strip()))
    return out


def write_schematic(path, stem, params, title):
    """Write a minimal xschem schematic holding one instance of the symbol."""
    lines = []
    lines.append("v {xschem version=%s file_version=1.2" % XSCHEM_VERSION)
    lines.append("}")
    lines.append("G {}")
    lines.append("K {}")
    lines.append("V {}")
    lines.append("S {}")
    lines.append("E {}")
    lines.append("T {%s} -160 -200 0 0 0.4 0.4 {}" % title)
    body = "\n".join("%s=%s" % (k, v) for k, v in params)
    lines.append("C {sg13g2_pr/%s.sym} 0 0 0 0 {%s}" % (stem, body))
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
    if lib is None:
        raise SystemExit("SG13_dev not found. Is KLAYOUT_PATH set and python3-tk installed?")
    liblay = lib.layout()

    os.makedirs(OUTDIR, exist_ok=True)
    made = []

    for pcell, stem, keys in DEVICES:
        decl = liblay.pcell_declaration(pcell)
        defaults = {p.name: p.default for p in decl.get_parameters()}

        missing = [k for k in keys if k not in defaults]
        if missing:
            print("SKIP %s: parameters not found: %s" % (pcell, missing))
            continue

        name = pcell + "".join("_%s%s" % (k, slug(defaults[k])) for k in keys)
        folder = os.path.join(OUTDIR, name)
        os.makedirs(folder, exist_ok=True)

        # --- layout view -----------------------------------------------------------
        ly = pya.Layout()
        ly.dbu = 0.001
        top = ly.create_cell(name)
        variant = ly.add_pcell_variant(lib, liblay.pcell_id(pcell), defaults)
        top.insert(pya.CellInstArray(variant, pya.Trans()))
        gds = os.path.join(folder, name + ".gds")
        ly.write(gds)

        # --- schematic view --------------------------------------------------------
        tmpl = symbol_template(stem)
        if not tmpl:
            print("WARN %s: symbol %s has no template" % (pcell, stem))
        sch = os.path.join(folder, name + ".sch")
        write_schematic(sch, stem, tmpl, name)

        bbox = top.bbox()
        made.append((name, pcell, stem,
                     "%.3f x %.3f um" % (bbox.width() * ly.dbu, bbox.height() * ly.dbu),
                     os.path.getsize(gds), os.path.getsize(sch)))

    print("%-34s %-10s %-10s %-18s %8s %6s" %
          ("folder", "pcell", "symbol", "layout bbox", "gds B", "sch B"))
    for row in made:
        print("%-34s %-10s %-10s %-18s %8d %6d" % row)
    print("built %d device folders under %s" % (len(made), OUTDIR))


main()
