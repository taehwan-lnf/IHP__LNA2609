# S_w40u_l80u_top_probpad_fill_dfpad
#
# Owner proposal 2026-08-28: keep the probepad and its 40 um width, and draw the pad
# marker by hand so the slit rule stops treating the pad as ordinary wide metal.
#
# Measured outcome: Slt.c.TM2 clears and no Pad.* rule appears in its place, so the cell
# reaches zero items needing a decision while staying 40 um wide. The bondpad route also
# reaches zero but forces the width to 60 um.
#
# The marker is drawn coincident with the TopMetal2 pad, which is where the PCell places
# its own marker when padType is bondpad. It is added at top level, so the PCell instance
# below is untouched.
import os, pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT=_ROOT
NAME="S_w40u_l80u_top_probpad_fill_dfpad"
lib=pya.Library.library_by_name("SG13_dev","sg13g2"); liblay=lib.layout()
DEF={p.name:p.default for p in liblay.pcell_declaration("bondpad").get_parameters()}
p=dict(DEF); p.update({"shape":"square","diameter":"80u","hwquota":"2","stack":"nil",
                       "topMetal":"TM2","padType":"probepad","fill":"t"})
ly=pya.Layout(); ly.dbu=0.001; top=ly.create_cell(NAME)
top.insert(pya.CellInstArray(ly.add_pcell_variant(lib,liblay.pcell_id("bondpad"),p),pya.Trans()))
tm2=pya.Region(top.begin_shapes_rec(ly.layer(134,0))); tm2.merge(); b=tm2.bbox()
top.shapes(ly.layer(41,0)).insert(pya.Box(b.left,b.bottom,b.right,b.top))
folder=os.path.join(PROJECT,"designlib","teg",NAME); os.makedirs(folder,exist_ok=True)
ly.write(os.path.join(folder,NAME+".gds"))
open(os.path.join(folder,NAME+".sch"),"w").write(
"""v {xschem version=3.4.4 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {%s : 40 x 80 um, TopMetal2 only. bondpad PCell, shape=square, diameter=80u, hwquota=2, stack=nil, padType=probepad, fill=t. The DfPad marker on 41/0 is drawn by hand at top level, coincident with the TopMetal2 pad, because the PCell omits it for probepad. That is what lets the slit rule exempt the pad metal while the width stays at 40 um; a bondpad would clear it too but cannot go below 60 um. fill has no effect here, stack=nil leaving no metal below TopMetal2.} -160 -240 0 0 0.35 0.35 {}
C {sg13g2_pr/bondpad.sym} 0 0 0 0 {name=X1
model=bondpad
spiceprefix=X
size=80u
shape=0
padtype=0}
C {devices/lab_pin.sym} 0 40 0 0 {name=lPAD sig_type=std_logic lab=PAD}
""" % NAME)
NM={9:"Passiv",134:"TopMetal2",41:"DfPad"}
rows=[]
for i in ly.layer_indexes():
    r=pya.Region(top.begin_shapes_rec(i))
    if r.count():
        inf=ly.get_info(i); r.merge()
        rows.append("%s %.0fum2"%(NM.get(inf.layer,str(inf.layer)),r.area()*ly.dbu*ly.dbu))
bb=top.bbox()
print("%s"%NAME)
print("   %.2f x %.2f um | %s"%(bb.width()*ly.dbu,bb.height()*ly.dbu," ".join(sorted(rows))))
print("   cells in file: %s   (marker drawn at top level, PCell instance untouched)"
      % [c.name for c in ly.each_cell()])
