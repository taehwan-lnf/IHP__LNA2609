"""Build GSG_dut_npn13g2v_m1_Nx5_le5p0u_we0p12u: layout, schematic and symbol.

The butt scheme from the owner's cross-section sketch, at one npn13G2V:

    the signal comes DOWN outside the HBT, through the whole stack to Metal1, and the
    Metal1 strap then meets the device's own terminal rail end face to end face
    the emitter needs no routing, since the PCell already straps it on Metal2 across the
    device; the ground simply continues that Metal2 outward on the other axis

Zero overlap at the joint is deliberate, on owner instruction 2026-09-01: if a later edit
shifts one side and opens a gap, LVS catches it. That is not a guess about LVS. Earlier in
this work a missing TopVia2 column left the base unreachable, and neither the geometry nor
DRC showed anything wrong while LVS failed immediately.

Measured for Nx=5 le=5.0u we=0.12u after R270:

    bbox        x 0.000..11.200   y -17.100..0.000
    left rail   x 1.450..2.100    y -13.755..-3.345    0.650 wide, 10.410 tall
    right rail  x 9.100..9.750    y -14.400..-2.700    0.650 wide, 11.700 tall
    emitter M2  x 2.820..8.380    y -14.400..-2.700    5.560 wide

The device is placed so the emitter's Metal2 centre sits on y=0, which puts the whole
device inside +-8.55 um. That matters: it fits within the 19 um signal, so the ground
bridge can stay at the coplanar edge of 19.5 um exactly as in GSG_open, instead of being
pushed outward as it had to be for the four-device column. The DUT and the OPEN therefore
carry the same ground geometry, which is what de-embedding wants.

Which rail is the base and which the collector is not assumed here. The left one is wired
to the input and LVS is left to confirm it; if it is the other way round the netlist will
say so.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pya
import gsg_frame as F

NAME = "GSG_dut_npn13g2v_m1_Nx5_le5p0u_we0p12u"
PCELL, SYM = "npn13G2V", "npn13G2v"
NX, LE, WE = 5, 5.0, 0.12

M1, M2, M3, M4, M5, TM1 = (8, 0), (10, 0), (30, 0), (50, 0), (67, 0), (126, 0)
UP = [M1, M2, M3, M4, M5, TM1, F.TM2]
UP_VIA = [((19, 0), 0.19, 0.6), ((29, 0), 0.19, 0.6), ((49, 0), 0.19, 0.6),
          ((66, 0), 0.19, 0.6), ((125, 0), 0.42, 1.2), ((133, 0), 0.90, 2.2)]
VIA_INSET, EPS = 0.8, 1e-6
STACK_W = 3.0          # via stack footprint across
STACK_GAP = 3.0        # from the device outline to the stack

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
if lib is None:
    raise SystemExit("SG13_dev not found. Run under: klayout -z -nc -r <script>")
liblay = lib.layout()

# ---- check the parameters before drawing, both sources ------------------------------
decl = liblay.pcell_declaration(PCELL)
for p in decl.get_parameters():
    if p.name == "Nx" and not (p.min_value <= NX <= p.max_value):
        raise SystemExit("Nx=%d outside the declared [%s, %s]" % (NX, p.min_value, p.max_value))
if not (1.0 <= LE <= 5.0):
    raise SystemExit("le=%gu outside the deck's [1.0u, 5.0u] for npn13G2V" % LE)
print("  parameters ok: Nx=%d in [1,8], le=%gu in [1,5], we=%gu" % (NX, LE, WE))

D = {p.name: p.default for p in decl.get_parameters()}
D.update({"Nx": NX, "le": "%gu" % LE, "we": "%gu" % WE})

# ---- measure the device on its own ---------------------------------------------------
probe = pya.Layout(); probe.dbu = 0.001
pc = probe.create_cell("p")
pc.insert(pya.CellInstArray(probe.add_pcell_variant(lib, liblay.pcell_id(PCELL), D),
                            pya.Trans(pya.Trans.R270, 0, 0)))
pc.flatten(-1, True)
g = {}
for s in pc.shapes(probe.find_layer(8, 0)).each():
    d = s.dbbox()
    k = (round(d.left, 3), round(d.right, 3))
    v = g.setdefault(k, [1e9, -1e9])
    v[0] = min(v[0], d.bottom); v[1] = max(v[1], d.top)
wins = sorted((l, r, v[0], v[1]) for (l, r), v in g.items())
Lx0, Lx1, Ly0, Ly1 = wins[0]           # leftmost rail
Rx0, Rx1, Ry0, Ry1 = wins[-1]          # rightmost rail
em2 = pya.Region(pc.shapes(probe.find_layer(10, 0))).merged().bbox().to_dtype(probe.dbu)
bb = pc.dbbox()

ox = F.XC - bb.width() / 2.0 - bb.left            # centre the device in the slot
oy = -(em2.bottom + em2.top) / 2.0                # emitter Metal2 centre onto y=0
print("  device placed at (%.3f, %.3f); it spans y %.3f..%.3f"
      % (ox, oy, bb.bottom + oy, bb.top + oy))

# ---- build ---------------------------------------------------------------------------
f = F.Frame(NAME, yg=F.GI)                        # ground stays at the coplanar edge
f.ground_bridge()
f.top.insert(pya.CellInstArray(
    f.ly.add_pcell_variant(lib, liblay.pcell_id(PCELL), D),
    pya.Trans(pya.Trans.R270, int(round(ox * F.U)), int(round(oy * F.U)))))

sides = [("in", Lx0 + ox, Ly0 + oy, Ly1 + oy, -1), ("out", Rx1 + ox, Ry0 + oy, Ry1 + oy, +1)]
for tag, xj, y0, y1, sgn in sides:
    if sgn < 0:
        sx1 = bb.left + ox - STACK_GAP
        sx0 = sx1 - STACK_W
        f.put(M1, sx0, y0, xj, y1)                # strap, butting the rail at xj
    else:
        sx0 = bb.right + ox + STACK_GAP
        sx1 = sx0 + STACK_W
        f.put(M1, xj, y0, sx1, y1)
    for spec in UP:
        f.put(spec, sx0, y0, sx1, y1)
    for spec, sz, pitch in UP_VIA:
        gy = y0 + VIA_INSET
        while gy + sz <= y1 - VIA_INSET + EPS:
            gx = sx0 + VIA_INSET
            while gx + sz <= sx1 - VIA_INSET + EPS:
                f.put(spec, gx, gy, gx + sz, gy + sz)
                gx += pitch
            gy += pitch
    if sgn < 0:
        f.put(F.TM2, F.X0, -F.SIG_W / 2, sx1, F.SIG_W / 2)
        lbl_x = (sx0 + sx1) / 2.0
    else:
        f.put(F.TM2, sx0, -F.SIG_W / 2, F.X1, F.SIG_W / 2)
        lbl_x = (sx0 + sx1) / 2.0
    sides[0 if sgn < 0 else 1] = (tag, xj, y0, y1, sgn, lbl_x)

# the emitter carried out to the ground bridge on its own Metal2
f.put(M2, em2.left + ox, -F.GI - 5.0, em2.right + ox, F.GI + 5.0)

f.finish([("IN", 40.0, 0.0), ("OUT", F.TOTAL - 40.0, 0.0), ("GND", 20.0, 100.0),
          ("B", sides[0][5], 0.0), ("C", sides[1][5], 0.0)])

folder = os.path.join(F.PROJECT, "designlib", "teg", NAME)

# ---- schematic -----------------------------------------------------------------------
SCH = """v {xschem version=3.4.4 file_version=1.2
* %s
*
* Two instances of the launch leaf, the second mirrored about x=195, with one npn13G2V in
* the 30 um slot between them. Common emitter: base to the input launch, collector to the
* output launch, emitter to the coplanar ground.
*
* The two res_topmetal2 come from the 134/29 markers inside the leaves and are what splits
* each launch into a named net either side of the marker.
*
* El carries the drawn emitter length. The symbol maps it onto the extractor's transposed
* name when it writes the LVS netlist; the width is fixed at 0.12u for this device.
}
G {}
K {}
V {}
S {}
E {}
T {%s} -260 -200 0 0 0.4 0.4 {}
C {res_topmetal2.sym} 0 0 0 0 {name=R1
model=res_topmetal2
spiceprefix=R
w=19u
l=10u
}
N 0 -60 0 -30 { lab=IN}
N 0 30 0 60 { lab=B}
C {res_topmetal2.sym} 200 0 0 0 {name=R2
model=res_topmetal2
spiceprefix=R
w=19u
l=10u
}
N 200 -60 200 -30 { lab=OUT}
N 200 30 200 60 { lab=C}
C {devices/ipin.sym} 0 -60 0 0 {name=p1 lab=IN}
C {devices/ipin.sym} 200 -60 0 0 {name=p2 lab=OUT}
C {devices/lab_pin.sym} 0 60 0 0 {name=lb sig_type=std_logic lab=B}
C {devices/lab_pin.sym} 200 60 0 0 {name=lc sig_type=std_logic lab=C}
C {devices/iopin.sym} 420 30 0 0 {name=p3 lab=GND}
N 420 0 420 30 { lab=GND}
C {%s_lvsfix.sym} 400 200 0 0 {name=Q1
model=%s
spiceprefix=X
Nx=%d
El=%g
mm_ok=1}
N 420 170 460 170 { lab=C}
N 380 200 340 200 { lab=B}
N 420 230 460 230 { lab=GND}
N 420 200 500 200 { lab=SUB}
C {devices/lab_pin.sym} 460 170 0 0 {name=lqc sig_type=std_logic lab=C}
C {devices/lab_pin.sym} 340 200 0 0 {name=lqb sig_type=std_logic lab=B}
C {devices/lab_pin.sym} 460 230 0 0 {name=lqe sig_type=std_logic lab=GND}
C {devices/lab_pin.sym} 500 200 0 0 {name=lqs sig_type=std_logic lab=SUB}
"""
io.open(os.path.join(folder, NAME + ".sch"), "w", encoding="utf-8", newline="\n").write(
    SCH % (NAME, NAME, SYM, SYM, NX, LE))

# ---- symbol for the cell, so it can be instanced higher up ---------------------------
SYMF = """v {xschem version=3.4.4 file_version=1.2
* Symbol for %s.
*
* A GSG de-embedding DUT: two probe launches with one npn13G2V between them. IN and OUT are
* the two signal launches at the pads; GND is the coplanar ground and also the emitter.
}
G {}
K {type=subcircuit
format="@name @pinlist @symname"
template="name=X1"
}
V {}
S {}
E {}
L 4 -60 -40 60 -40 {}
L 4 60 -40 60 40 {}
L 4 -60 40 60 40 {}
L 4 -60 -40 -60 40 {}
B 5 -62.5 -22.5 -57.5 -17.5 {name=IN dir=inout}
B 5 57.5 -22.5 62.5 -17.5 {name=OUT dir=inout}
B 5 -2.5 37.5 2.5 42.5 {name=GND dir=inout}
T {@symname} -55 -3 0 0 0.25 0.25 {}
T {@name} -60 -52 0 0 0.2 0.2 {}
T {IN} -52 -24 0 0 0.2 0.2 {}
T {OUT} 34 -24 0 0 0.2 0.2 {}
T {GND} -8 22 0 0 0.2 0.2 {}
T {npn13G2V Nx=%d le=%gu we=%gu} -55 8 0 0 0.2 0.2 {layer=13}
""" % (NAME, NX, LE, WE)
io.open(os.path.join(folder, NAME + ".sym"), "w", encoding="utf-8", newline="\n").write(SYMF)

io.open(os.path.join(folder, "xschemrc"), "w", encoding="utf-8", newline="\n").write(
    io.open(os.path.join(F.PROJECT, "designlib", "teg", F.LEAF, "xschemrc"), encoding="utf-8").read())
print("  wrote the schematic, the symbol and xschemrc")
