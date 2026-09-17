"""The one writer for a subcircuit symbol and for the sealed schematic that instances it.

These three functions used to live in gen_views.py while gen_gsg_duts.py carried a second,
hard-coded copy of the symbol text. The two disagreed about where a pin sits, and on
2026-09-04 that disagreement cut thirteen sealed schematics loose from their ports: the DUT
instance netlisted onto net1, net2 and net3 instead of IN, OUT and GND. LVS still reported
MATCH, so nothing announced it.

They belong together in one file because write_symbol decides where a pin sits and
write_wrapper draws the wire that has to land on it. Both read the same h, and if that formula
ever changes it must change for both at once.
"""
import io
import os
import re

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
DEV = os.path.join(PROJECT, "designlib", "teg")


def ports_of(cell):
    """Read the port order from the cell's own netlist, not from a list kept here."""
    p = os.path.join(DEV, cell, cell + ".spice")
    for line in io.open(p, encoding="utf-8"):
        m = re.match(r"\.subckt\s+(\S+)\s+(.*)", line.strip(), re.I)
        if m:
            return m.group(2).split()
    raise SystemExit("no .subckt line in %s" % p)


def write_symbol(folder, name, pins, note):
    """A subcircuit symbol whose pins sit down the left and right sides in port order."""
    h = max(60, 30 * ((len(pins) + 1) // 2) + 30)
    w = 90
    out = ["""v {xschem version=3.4.4 file_version=1.2
* %s
%s}
G {}
K {type=subcircuit
format="@name @pinlist @symname"
template="name=X1"
}
V {}
S {}
E {}
L 4 %d %d %d %d {}
L 4 %d %d %d %d {}
L 4 %d %d %d %d {}
L 4 %d %d %d %d {}
T {@symname} %d %d 0 0 0.18 0.18 {}
T {@name} %d %d 0 0 0.2 0.2 {}
""" % (name, note,
       -w, -h, w, -h, w, -h, w, h, -w, h, w, h, -w, -h, -w, h,
       -w + 6, -6, -w, -h - 16)]
    for i, pin in enumerate(pins):
        side = -1 if i % 2 == 0 else 1
        y = -h + 30 + 30 * (i // 2)
        x = side * w
        out.append("B 5 %g %g %g %g {name=%s dir=inout}\n"
                   % (x - 2.5, y - 2.5, x + 2.5, y + 2.5, pin))
        out.append("T {%s} %g %g 0 0 0.18 0.18 {}\n"
                   % (pin, x + (8 if side < 0 else -8 - 7 * len(pin)), y - 8))
    io.open(os.path.join(folder, name + ".sym"), "w", encoding="utf-8",
            newline="\n").write("".join(out))


def write_wrapper(folder, sealed, inner, pins):
    """The sealed cell's schematic: one instance of the bare cell, ports carried straight out."""
    out = ["""v {xschem version=3.4.4 file_version=1.2
* %s
*
* The seal ring adds no device and no net. Extracted, this cell and %s
* return the same devices on the same nets, so the schematic is the bare cell instanced once
* and its ports carried straight out.
}
G {}
K {}
V {}
S {}
E {}
T {%s} -260 -220 0 0 0.4 0.4 {}
C {%s.sym} 0 0 0 0 {name=X1}
""" % (sealed, inner, sealed, inner)]
    h = max(60, 30 * ((len(pins) + 1) // 2) + 30)
    for i, pin in enumerate(pins):
        side = -1 if i % 2 == 0 else 1
        y = -h + 30 + 30 * (i // 2)
        x = side * 90
        xo = x + side * 60
        out.append("N %g %g %g %g { lab=%s}\n" % (x, y, xo, y, pin))
        out.append("C {devices/iopin.sym} %g %g 0 %d {name=p%d lab=%s}\n"
                   % (xo, y, 0 if side < 0 else 0, i + 1, pin))
    io.open(os.path.join(folder, sealed + ".sch"), "w", encoding="utf-8",
            newline="\n").write("".join(out))
