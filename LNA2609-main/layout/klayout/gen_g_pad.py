"""Build G_w60u_l80u_top_to_m1_bondpad_fill: 60 x 80 um, TopMetal2 down to Metal1, filled.

TopVia2 goes in a grid across the whole pad area. Owner instruction 2026-08-31.

History of this cell, kept because the reasoning matters and the repository convention is
to supersede rather than overwrite.

    first    one bondpad PCell, stack='t', fill='t'. Measured at 60 x 80 that draws 228
             TopVia2 of which 96 fall fully inside the Passiv opening, and the deck flags
             each of those 96 as Pad.kR.
    then     two overlaid instances, TM2..TM1 with fill='nil' over TM1..M1 with fill='t'.
             Measured, every metal layer stayed one solid 4800 um2 polygon and Passiv and
             DfPad were unchanged, while TopVia2 under the opening went from 96 to 0. That
             cleared Pad.kR, but it left TopVia2 as a ring around the pad rather than
             across it.
    now      back to the single filled instance, on owner instruction, so TopVia2 covers
             the pad area as a grid.

What comes back with it. Pad.kR returns at 96 counts on this cell, and once per G pad in
anything that instances it: two per launch leaf, so 4 x 96 in a 390 um parent. Its text
reads "TopVia2 under Pad not allowed (TopVia2 may be damaged during packaging process, we
recommend not to use them below Passiv.)" It is a recommendation, marked by the R in its
name, and the owner has made the call. It is recorded here so the count is understood
rather than rediscovered.

Not stated in the folder name, so left at the PCell default:
    shape   'square'   the name reads as width by length
    hwquota '2'        the smallest value that reaches the 60 um bondpad floor at this
                       diameter, rather than a larger number implying a ratio the PCell
                       does not honour
"""
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
NAME = "G_w60u_l80u_top_to_m1_bondpad_fill"
DIAM, HWQ = 80.0, "2"

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
if lib is None:
    raise SystemExit("SG13_dev not found. Run under: klayout -z -nc -r <script>")
liblay = lib.layout()
DEF = {p.name: p.default for p in liblay.pcell_declaration("bondpad").get_parameters()}

L = {"Metal1": (8, 0), "Metal2": (10, 0), "Metal3": (30, 0), "Metal4": (50, 0),
     "Metal5": (67, 0), "TopMetal1": (126, 0), "TopMetal2": (134, 0),
     "TopVia1": (125, 0), "TopVia2": (133, 0), "Passiv": (9, 0), "DfPad": (41, 0)}

SCH = """v {xschem version=3.4.4 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {%s : 60 x 80 um, TopMetal2 down to Metal1, solid.} -160 -240 0 0 0.35 0.35 {}
T {bondpad PCell, shape=square, diameter=%gu, hwquota=%s, stack=t, bottomMetal=1,} -160 -222 0 0 0.35 0.35 {}
T {padType=bondpad, fill=t. Width sits on the bondpad floor of 60 um at this diameter.} -160 -204 0 0 0.35 0.35 {}
T {fill=t puts TopVia2 in a grid across the pad area, on owner instruction 2026-08-31.} -160 -186 0 0 0.35 0.35 {}
T {That returns Pad.kR at 96 counts, which recommends no TopVia2 below Passiv because} -160 -168 0 0 0.35 0.35 {}
T {packaging can damage them. It is a recommendation and the owner has accepted it.} -160 -150 0 0 0.35 0.35 {}
C {sg13g2_pr/bondpad.sym} 0 0 0 0 {name=X1
model=bondpad
spiceprefix=X
size=%gu
shape=0
padtype=0}
C {devices/lab_pin.sym} 0 40 0 0 {name=lPAD sig_type=std_logic lab=PAD}
"""

params = dict(DEF)
params.update({"shape": "square", "diameter": "%gu" % DIAM, "hwquota": HWQ,
               "stack": "t", "bottomMetal": "1", "topMetal": "TM2",
               "padType": "bondpad", "fill": "t"})

ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell(NAME)
top.insert(pya.CellInstArray(
    ly.add_pcell_variant(lib, liblay.pcell_id("bondpad"), params), pya.Trans()))

folder = os.path.join(PROJECT, "designlib", "teg", NAME)
os.makedirs(folder, exist_ok=True)
ly.write(os.path.join(folder, NAME + ".gds"))
open(os.path.join(folder, NAME + ".sch"), "w").write(SCH % (NAME, DIAM, HWQ, DIAM))

bb = top.bbox()
tv2 = pya.Region(top.begin_shapes_rec(ly.layer(*L["TopVia2"])))
pas = pya.Region(top.begin_shapes_rec(ly.layer(*L["Passiv"])))
print("rebuilt %s" % os.path.join(folder, NAME + ".gds"))
print("  bbox      %.1f x %.1f um" % (bb.width() * ly.dbu, bb.height() * ly.dbu))
print("  TopVia2   %d total, %d inside the opening -> that many Pad.kR"
      % (tv2.count(), tv2.inside(pas).count()))
for k in ("TopMetal2", "TopMetal1", "Metal5", "Metal4", "Metal3", "Metal2", "Metal1",
          "Passiv", "DfPad"):
    r = pya.Region(top.begin_shapes_rec(ly.layer(*L[k]))).merged()
    print("  %-10s %7.1f um2 in %d polygon(s)" % (k, r.area() * ly.dbu * ly.dbu, r.count()))
