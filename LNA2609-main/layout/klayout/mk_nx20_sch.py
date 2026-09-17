"""Write the two candidate schematics for the Nx=20 cell and see which one LVS accepts.

The owner's expectation was that a schematic drawn as npn13g2 m=2 with Nx=10 would match a
layout of 20 fingers. Extraction says otherwise: the layout comes back as one device with
Nx=20 and m=1, so both candidates are written and both are run.

    _asNx20   one instance, Nx=20
    _asm2     two instances, Nx=10 each, combined by --combine_devices into m=2

The stock symbol is used here, not npn13G2_lvsfix. The lvsfix copies swap the le and we
parameter names, and that swap belongs with an R270 placement read by flat extraction: the
DUT cells place the device rotated and extract we=900n le=70n for a 0.07 x 0.9 emitter. This
cell is unrotated and extracts we=70n le=900n, the drawn convention, so the stock symbol is
the one that matches.
"""
import io
import os

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
LEAF = "G1SG2_pitch100u_lvsres_lauching_metal_cwpg_via_fence"

HEAD = """v {xschem version=3.4.4 file_version=1.2
* %s
%s}
G {}
K {}
V {}
S {}
E {}
T {%s} -300 -200 0 0 0.4 0.4 {}
C {devices/iopin.sym} -100 -60 0 0 {name=p1 lab=B}
C {devices/iopin.sym} -100 0 0 0 {name=p2 lab=C}
C {devices/iopin.sym} -100 60 0 0 {name=p3 lab=E}
C {devices/iopin.sym} -100 120 0 0 {name=p4 lab=SUB}
"""

DEV = """C {npn13G2.sym} 200 %d 0 0 {name=Q%d
model=npn13G2
spiceprefix=X
Nx=%d
le=0.9u
we=0.07u
mm_ok=1}
N 220 %d 280 %d { lab=C}
N 180 %d 120 %d { lab=B}
N 220 %d 280 %d { lab=E}
N 220 %d 320 %d { lab=SUB}
C {devices/lab_pin.sym} 280 %d 0 0 {name=lc%d sig_type=std_logic lab=C}
C {devices/lab_pin.sym} 120 %d 0 0 {name=lb%d sig_type=std_logic lab=B}
C {devices/lab_pin.sym} 280 %d 0 0 {name=le%d sig_type=std_logic lab=E}
C {devices/lab_pin.sym} 320 %d 0 0 {name=ls%d sig_type=std_logic lab=SUB}
"""


def write(cell, tag, insts, nx, note):
    out = [HEAD % (cell, note, cell + tag)]
    for k in range(insts):
        y = 0 + k * 140
        out.append(DEV % (y, k + 1, nx, y - 30, y - 30, y, y, y + 30, y + 30, y, y,
                          y - 30, k + 1, y, k + 1, y + 30, k + 1, y, k + 1))
    folder = os.path.join(PROJECT, "designlib", "teg", cell)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, cell + tag + ".sch")
    io.open(path, "w", encoding="utf-8", newline="\n").write("".join(out))
    io.open(os.path.join(folder, "xschemrc"), "w", encoding="utf-8", newline="\n").write(
        io.open(os.path.join(PROJECT, "designlib", "teg", LEAF, "xschemrc"), encoding="utf-8").read()
        + "\nset lvs_netlist 1\n")
    print("wrote %s" % path)


# The we=0.08u cell these were also written for is gone, removed on 2026-09-02 because the
# LVS deck extracts no device from an emitter of any width but 0.07. See gen_nx20.py, which
# keeps the reasoning and the commit to read it back from.
for cell in ("npn13g2_m1_Nx20_le0p9u_we0p07u",):
    write(cell, "", 1, 20,
          "* One instance at Nx=20, which is what extraction reports for this layout.\n")
    # The _asm2 variant, two instances at Nx=10, was written here too and came back with
    # "Netlists don't match": the layout extracts as one device at Nx=20 with m=1, and
    # --combine_devices merges identical devices in parallel rather than renumbering fingers.
    # It is no longer written, for a practical reason as well as a settled one. xs opens a
    # folder's schematic only when there is exactly one .sch in it; with two, the bare
    # command refuses with "several .sch files ... name the one you want" and no window
    # appears. Every other cell folder holds one .sch named after the cell, and this one
    # now does too.
