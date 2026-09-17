"""First draft of the three-device cell: draw the devices, nothing else yet.

Owner instruction 2026-08-31: make the cell directory and start by drawing each device's
layout. Interconnect, terminals and any ring come later, step by step.

    npn13G2   Nx=10 le=0.9u we=0.07u   outline 23.350 x  7.110   window 0.070 x 0.900 x10
    npn13G2L  Nx=4  le=2.5u we=0.07u   outline 16.200 x  8.700   window 0.070 x 2.500 x4
    npn13G2V  Nx=8  le=5.0u we=0.12u   outline 24.120 x 11.200   window 0.120 x 5.000 x8

How these values were arrived at, since three of them moved:

    le on the L was asked as 5.0u and is 2.5u. The deck's npn13G2L.b caps it at 2.5, and
        at 5.0u the device raised that rule ten times. npn13G2V.b caps at 5.0, so the same
        5.0u on the V is legal and stayed.
    we on the V was asked as 1.2u and is 0.12u. Owner correction; 1.2u was a typo. It is
        worth noting that nothing would have caught it: the deck has no emitter width rule
        at all, and 1.2u drew and passed DRC cleanly at an emitter area of 60 um2, ten
        times the model's extraction point.
    Nx was asked as 5 on the L and 10 on the V, and is 4 and 8, their declared ceilings.
        Owner instruction to clamp. See check() below for why nothing caught this either.

Orientation is R0, the PCells' own. The DUT work so far uses R270 to put the base toward
the input launch, but which way this cell should face has not been settled, so it is left
as drawn and is one parameter to change.

Placement is a row along x with a 5 um gap, vertically centred. That is a holding
arrangement to have something measurable on screen, not a decision.
"""
import os
import pya

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = _ROOT
NAME = ("npn13G2_Nx10_le0p9u_we0p07u_m1"
        "_npn13G2l_Nx4_le2p5u_we0p07u_m1"
        "_npn13G2v_Nx8_le5p0u_we0p12u_m1")
U = 1000.0
GAP = 5.0

# Emitter length limits, which live in the DRC deck and not on the PCell. From
# drc/docs/extra_rules.md: npn13G2.a gives 0.9 as both the minimum and the maximum, and
# npn13G2L.a/.b and npn13G2V.a/.b give the two ranges below.
LE_LIMITS = {"npn13G2": (0.9, 0.9), "npn13G2L": (1.0, 2.5), "npn13G2V": (1.0, 5.0)}

# PCell names are capitalised while symbol names are not; folder names follow the symbol
# spelling. The pairing is written out rather than derived, because the case difference is
# a property of the PDK and not something to infer.
SPECS = [("npn13G2",  "npn13G2",  10, 0.9, 0.07),
         ("npn13G2L", "npn13G2l",  4, 2.5, 0.07),
         ("npn13G2V", "npn13G2v",  8, 5.0, 0.12)]

WINDOW = {"npn13G2": (33, 0), "npn13G2L": (33, 0), "npn13G2V": (156, 0)}

lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
if lib is None:
    raise SystemExit("SG13_dev not found. Run under: klayout -z -nc -r <script>")
liblay = lib.layout()

ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell(NAME)

def check(pcell, nx, le):
    """Refuse to draw a device whose parameters are outside what is allowed.

    This exists because nothing else catches it. add_pcell_variant applies whatever value
    it is handed without consulting the declaration, the geometry comes out consistent with
    that value, and the DRC deck has no rule on Nx at all, so an out-of-range Nx passes DRC
    and looks correct in the layout. It shows up only in KLayout's instance properties
    dialog, in red, if someone opens it. That is how Nx=5 on npn13G2L and Nx=10 on
    npn13G2V got as far as a written GDS on 2026-09-01.

    The two limits come from different places and neither covers the other: Nx from the
    PCell declaration, le from the DRC deck. Both are checked here.
    """
    bad = []
    nlo = nhi = None
    for p in liblay.pcell_declaration(pcell).get_parameters():
        if p.name == "Nx":
            nlo, nhi = p.min_value, p.max_value
    if nlo is not None and nhi is not None and not (nlo <= nx <= nhi):
        bad.append("Nx=%d outside the declared [%s, %s]" % (nx, nlo, nhi))
    llo, lhi = LE_LIMITS[pcell]
    if not (llo <= le <= lhi):
        bad.append("le=%gu outside the deck's [%gu, %gu]" % (le, llo, lhi))
    if bad:
        raise SystemExit("%s: %s" % (pcell, "; ".join(bad)))
    return "Nx %d in [%s, %s], le %gu in [%gu, %gu]" % (nx, nlo, nhi, le, llo, lhi)


x = 0.0
rows = []
for pcell, sym, nx, le, we in SPECS:
    print("  %-9s %s" % (sym, check(pcell, nx, le)))
    D = {p.name: p.default for p in liblay.pcell_declaration(pcell).get_parameters()}
    D.update({"Nx": nx, "le": "%gu" % le, "we": "%gu" % we})

    # measure it on its own first, so the placement can be worked out from real numbers
    probe = pya.Layout(); probe.dbu = 0.001
    pc = probe.create_cell("p")
    pc.insert(pya.CellInstArray(
        probe.add_pcell_variant(lib, liblay.pcell_id(pcell), D), pya.Trans()))
    pc.flatten(-1, True)
    bb = pc.dbbox()

    dx = x - bb.left
    dy = -(bb.bottom + bb.top) / 2.0
    top.insert(pya.CellInstArray(
        ly.add_pcell_variant(lib, liblay.pcell_id(pcell), D),
        pya.Trans(pya.Trans.R0, int(round(dx * U)), int(round(dy * U)))))

    wi = probe.find_layer(*WINDOW[pcell])
    wr = pya.Region(pc.shapes(wi)).merged() if wi is not None else pya.Region()
    rows.append((sym, nx, le, we, bb.width(), bb.height(),
                 wr.count(), wr.area() * probe.dbu * probe.dbu,
                 x, x + bb.width()))
    x += bb.width() + GAP

folder = os.path.join(PROJECT, "designlib", "teg", NAME)
os.makedirs(folder, exist_ok=True)
out = os.path.join(folder, NAME + ".gds")
ly.write(out)

bb = top.dbbox()
print("wrote %s" % out)
print("  cell bbox  %.3f x %.3f um   (x %.2f..%.2f, y %.2f..%.2f)"
      % (bb.width(), bb.height(), bb.left, bb.right, bb.bottom, bb.top))

# Report, rather than claim, that these are PCell instances. is_pcell_variant is KLayout's
# own answer, and the parameters read back come from the PCell and not from this script.
print()
print("  are these PCell instances?")
for inst in top.each_inst():
    c = inst.cell
    if not c.is_pcell_variant():
        print("     %-28s NOT a PCell variant" % c.name)
        continue
    p = c.pcell_parameters_by_name()
    print("     %-28s PCell variant of %-10s Nx=%-3s le=%-6s we=%s"
          % (c.name, c.pcell_declaration().name(), p.get("Nx"), p.get("le"), p.get("we")))
print("  top cell holds %d shape(s) of its own; everything else is instanced"
      % sum(top.shapes(i).size() for i in ly.layer_indexes()))
print()
print("  %-10s %-3s %-7s %-8s %-16s %-8s %-10s %s"
      % ("device", "Nx", "le", "we", "outline", "windows", "Ae (um2)", "x span"))
for (sym, nx, le, we, w, h, n, a, x0, x1) in rows:
    print("  %-10s %-3d %-7s %-8s %6.3f x %-7.3f %-8d %-10.4f %.2f..%.2f"
          % (sym, nx, "%gu" % le, "%gu" % we, w, h, n, a, x0, x1))
