"""Three small tops that isolate what makes the full top's four devices fail to match.

The full top matches 46 of 47 nets and 36 of 40 devices, and the four that do not are
GSG_load's, its two rppd and the two res_topmetal2 of its launches. That same cell passes on
its own. Three cases separate the possibilities, each built the same way the full top is:

    mini_load       GSG_load_sealring alone, inside a ring of its own
    mini_dut        one DUT alone, the control
    mini_load_dut   the two together, which is the first arrangement in which the LOAD's
                    rppd body shares the substrate with a DUT's guard ring

If mini_load passes and mini_load_dut fails, the substrate sharing is the cause. If mini_load
fails on its own, the extra ring around it is.
"""
import io
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
DEV = os.path.join(PROJECT, "designlib", "teg")
LEAF = "G1SG2_pitch100u_lvsres_lauching_metal_cwpg_via_fence"
GAP, KEEPOUT = 20.0, 40.0
INNER_OFF, OPEN_MARGIN = 36.40, 22.80

CASES = [
    ("mini_load", ["GSG_load"]),
    ("mini_dut", ["GSG_dut_npn13g2v_m1_Nx5_le5p0u_we0p12u"]),
    ("mini_load_dut", ["GSG_load", "GSG_dut_npn13g2v_m1_Nx5_le5p0u_we0p12u"]),
]

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
liblay = lib.layout()
pid = liblay.pcell_id("sealring")
decl = liblay.pcell_declaration("sealring")
_BASE = io.open(os.path.join(DEV, LEAF, "xschemrc"), encoding="utf-8").read()

ALL = sorted(d[:-len("_sealring")] for d in os.listdir(DEV) if d.endswith("_sealring"))
RC = "\n".join([_BASE.rstrip(), ""]
               + ["append XSCHEM_LIBRARY_PATH :$::env(DESIGN_ROOT)/designlib/teg/%s" % c
                  for c in ALL]
               + ["append XSCHEM_LIBRARY_PATH :$::env(DESIGN_ROOT)/designlib/teg/%s_sealring" % c
                  for c in ALL]
               + ["", "set lvs_netlist 1", ""])


def ports_of(cell):
    for line in io.open(os.path.join(DEV, cell, cell + ".spice"), encoding="utf-8"):
        if line.lower().startswith(".subckt"):
            return line.split()[2:]
    raise SystemExit("no .subckt in %s" % cell)


for name, cells in CASES:
    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name)

    boxes = []
    for i, cell in enumerate(cells):
        sealed = cell + "_sealring"
        s = pya.Layout()
        s.read(os.path.join(DEV, sealed, sealed + ".gds"))
        bb = s.top_cell().dbbox()
        sub = ly.create_cell(sealed)
        sub.copy_tree(s.top_cell())
        dx = i * (bb.width() + GAP) - bb.left
        top.insert(pya.CellInstArray(sub.cell_index(),
                                     pya.Trans(pya.Trans.R0, int(round(dx * 1000)),
                                               int(round(-bb.bottom * 1000)))))
        boxes.append(bb)

    w = sum(b.width() for b in boxes) + GAP * (len(boxes) - 1)
    h = max(b.height() for b in boxes)
    D = {p.name: p.default for p in decl.get_parameters()}
    D.update({"l": "%.3fu" % (w + 2 * KEEPOUT + OPEN_MARGIN),
              "w": "%.3fu" % (h + 2 * KEEPOUT + OPEN_MARGIN)})
    top.insert(pya.CellInstArray(ly.add_pcell_variant(lib, pid, D),
                                 pya.Trans(pya.Trans.R0,
                                           int(round((-KEEPOUT - INNER_OFF) * 1000)),
                                           int(round((-KEEPOUT - INNER_OFF) * 1000)))))

    folder = os.path.join(DEV, name)
    os.makedirs(folder, exist_ok=True)
    ly.write(os.path.join(folder, name + ".gds"))

    out = ["""v {xschem version=3.4.4 file_version=1.2
* %s
}
G {}
K {}
V {}
S {}
E {}
""" % name]
    for i, cell in enumerate(cells):
        pins = ports_of(cell)
        ox = i * 420
        hh = max(60, 30 * ((len(pins) + 1) // 2) + 30)
        out.append("C {%s_sealring.sym} %d 0 0 0 {name=X%d}\n" % (cell, ox, i + 1))
        for j, pin in enumerate(pins):
            side = -1 if j % 2 == 0 else 1
            y = -hh + 30 + 30 * (j // 2)
            x = ox + side * 90
            xo = x + side * 70
            net = "sub!" if (pin == "GND" and cell.startswith("GSG_dut")) \
                else "c%d_%s" % (i, pin)
            out.append("N %g %g %g %g { lab=%s}\n" % (x, y, xo, y, net))
            out.append("C {devices/lab_pin.sym} %g %g 0 0 "
                       "{name=l%d_%d sig_type=std_logic lab=%s}\n" % (xo, y, i, j, net))
    io.open(os.path.join(folder, name + ".sch"), "w", encoding="utf-8",
            newline="\n").write("".join(out))
    io.open(os.path.join(folder, "xschemrc"), "w", encoding="utf-8",
            newline="\n").write(RC)
    print("%-16s %s   bbox %s" % (name, " + ".join(cells), top.dbbox()))
