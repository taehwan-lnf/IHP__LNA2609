"""Two more cases: is it the outer seal ring, or simply instancing a cell inside a top?

mini_load, mini_dut and mini_load_dut all failed, including mini_dut whose nets, pins and
devices every one matched. Two differences from a sealed cell that passes on its own remain:
the second seal ring around it, and the fact that the cell is now an instance inside a top
rather than the top itself.

    mini_noring   one sealed DUT instanced in a top, with no outer ring at all
    mini_bare     one BARE DUT instanced in a top, with one outer ring

If mini_noring passes, the outer ring is the cause. If it fails too, then instancing is.
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
DUT = "GSG_dut_npn13g2v_m1_Nx5_le5p0u_we0p12u"
KEEPOUT, INNER_OFF, OPEN_MARGIN = 40.0, 36.40, 22.80

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
liblay = lib.layout()
pid = liblay.pcell_id("sealring")
decl = liblay.pcell_declaration("sealring")
RC = io.open(os.path.join(DEV, "mini_dut", "xschemrc"), encoding="utf-8").read()


def ports_of(cell):
    for line in io.open(os.path.join(DEV, cell, cell + ".spice"), encoding="utf-8"):
        if line.lower().startswith(".subckt"):
            return line.split()[2:]
    raise SystemExit("no .subckt in %s" % cell)


for name, inner, ring in (("mini_noring", DUT + "_sealring", False),
                          ("mini_bare", DUT, True)):
    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name)
    s = pya.Layout()
    s.read(os.path.join(DEV, inner, inner + ".gds"))
    bb = s.top_cell().dbbox()
    sub = ly.create_cell(inner)
    sub.copy_tree(s.top_cell())
    top.insert(pya.CellInstArray(sub.cell_index(),
                                 pya.Trans(pya.Trans.R0, int(round(-bb.left * 1000)),
                                           int(round(-bb.bottom * 1000)))))
    if ring:
        D = {p.name: p.default for p in decl.get_parameters()}
        D.update({"l": "%.3fu" % (bb.width() + 2 * KEEPOUT + OPEN_MARGIN),
                  "w": "%.3fu" % (bb.height() + 2 * KEEPOUT + OPEN_MARGIN)})
        top.insert(pya.CellInstArray(ly.add_pcell_variant(lib, pid, D),
                                     pya.Trans(pya.Trans.R0,
                                               int(round((-KEEPOUT - INNER_OFF) * 1000)),
                                               int(round((-KEEPOUT - INNER_OFF) * 1000)))))

    folder = os.path.join(DEV, name)
    os.makedirs(folder, exist_ok=True)
    ly.write(os.path.join(folder, name + ".gds"))

    pins = ports_of(DUT)
    h = max(60, 30 * ((len(pins) + 1) // 2) + 30)
    out = ["v {xschem version=3.4.4 file_version=1.2\n* %s\n}\nG {}\nK {}\nV {}\nS {}\nE {}\n"
           % name, "C {%s.sym} 0 0 0 0 {name=X1}\n" % DUT]
    for j, pin in enumerate(pins):
        side = -1 if j % 2 == 0 else 1
        y = -h + 30 + 30 * (j // 2)
        x = side * 90
        xo = x + side * 70
        out.append("N %g %g %g %g { lab=c_%s}\n" % (x, y, xo, y, pin))
        out.append("C {devices/lab_pin.sym} %g %g 0 0 "
                   "{name=l%d sig_type=std_logic lab=c_%s}\n" % (xo, y, j, pin))
    io.open(os.path.join(folder, name + ".sch"), "w", encoding="utf-8",
            newline="\n").write("".join(out))
    io.open(os.path.join(folder, "xschemrc"), "w", encoding="utf-8",
            newline="\n").write(RC)
    print("%-14s inner %-46s ring %s   bbox %s"
          % (name, inner, "yes" if ring else "no", top.dbbox()))
