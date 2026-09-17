"""Write the xschem schematics for the OPEN, SHORT and THRU parents.

Each layout holds exactly two devices, the two res_topmetal2 that the 134/29 markers
create, one in each launch. What differs between the three is only what the far end of each
marker is tied to, which is the whole point of the standard set:

    OPEN    IN - R1 - TI        TO - R2 - OUT      the launches face nothing
    SHORT   IN - R1 - GND        GND  - R2 - OUT      each launch tied sideways to ground
    THRU    IN - R1 - T          T    - R2 - OUT      the launches joined through the slot

Pin order follows the symbol: P is the lower terminal and M the upper, so a resistor drawn
with its P wire going down nets out as "R<name> <P net> <M net>". That was confirmed on the
leaf, where P carried S1 and M carried T1 and the netlist came out RR1 S1 T1.

T, TI and TO are declared as pins rather than left as internal nodes. They are the
de-embedding reference planes, so they deserve names, and a plain internal node between two
series resistors is exactly what the netlist simplifier is entitled to collapse.

GND in OPEN and THRU has no device terminal on it, so it gets a stub wire with a pin on the
end, which is how the leaf declares its own GND and how that cell passes LVS in strict port
mode. In SHORT it needs no stub, because both resistors already land on it.
"""
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
*
* Two instances of %s, the second mirrored
* about x=195, giving a 30 um DUT slot at x 180..210 and 390 um overall. The only devices
* are the two TopMetal2 metal resistors the 134/29 markers produce. w and l are the drawn
* markers, 19 um across the signal and 10 um along it, and RES2 compares exactly those two
* while ignoring R.
%s}
G {}
K {}
V {}
S {}
E {}
T {%s} -240 -150 0 0 0.4 0.4 {}
"""

RES = """C {res_topmetal2.sym} %d 0 0 0 {name=%s
model=res_topmetal2
spiceprefix=R
w=19u
l=10u
}
"""

CELLS = {
    "GSG_open": dict(
        note="* The slot is empty, so TI and TO go nowhere, and that is the measurement.\n",
        legs=[(0, "IN", "TI"), (200, "OUT", "TO")],
        stub=("GND", 320),
        pins=[("ipin", 0, -60, "IN"), ("opin", 0, 60, "TI"),
              ("ipin", 200, -60, "OUT"), ("opin", 200, 60, "TO"),
              ("iopin", 320, 30, "GND")], labels=[]),
    "GSG_short": dict(
        note="* Each launch is tied to the coplanar ground beside it by a T on TopMetal2\n"
             "* and Metal1. Bringing the two signals together instead would be THRU.\n",
        legs=[(0, "IN", "GND"), (200, "OUT", "GND")],
        stub=None,
        pins=[("ipin", 0, -60, "IN"), ("ipin", 200, -60, "OUT"),
              ("iopin", 0, 60, "GND")],
        labels=[(200, 60, "GND")]),
    "GSG_thru": dict(
        note="* The two fixture end planes are joined on Metal1, which is the layer the DUT\n"
             "* crosses on. The earlier version bridged the slot on TopMetal2 instead, so it\n"
             "* did not contain the DUT's via stack or its Metal1 run and could not remove\n"
             "* them. Owner correction of 2026-09-02.\n",
        legs=[(0, "IN", "T"), (200, "OUT", "T")],
        stub=("GND", 320),
        pins=[("ipin", 0, -60, "IN"), ("ipin", 200, -60, "OUT"),
              ("opin", 0, 60, "T"), ("iopin", 320, 30, "GND")],
        labels=[(200, 60, "T")]),
    "GSG_load": dict(
        note="* Each fixture end plane sees 50 ohm to ground through an rppd, w=10u and\n"
             "* l=1.655u. The length is not the 1.92u a sheet calculation gives, because\n"
             "* the PDK value expression carries a 70.0e-6/w contact term that is 7.00 ohm\n"
             "* on its own at w=10u: 1.92u lands on 56.89 ohm and 1.655u on 50.00 ohm.\n",
        legs=[(0, "IN", "TI"), (200, "OUT", "TO")],
        stub=None,
        pins=[("ipin", 0, -60, "IN"), ("ipin", 200, -60, "OUT"),
              ("iopin", 400, 60, "GND")],
        labels=[(0, 60, "TI"), (200, 60, "TO"), (600, 60, "GND")],
        loads=[(400, "R3", "TI"), (600, "R4", "TO")]),
}

# body=GND, not body=sub!. GSG_load now carries its own substrate tie, two Activ and pSD
# strips inside the coplanar ground plane, so the extractor returns the rppd body on GND
# rather than on a net of its own. Leaving sub! here would put the schematic body on an
# isolated net and the compare would fail on the third terminal.
RPPD = """C {rppd.sym} %d 0 0 0 {name=%s
model=rppd
spiceprefix=X
body=GND
w=10e-6
l=1.655e-6
b=0
m=1
mm_ok=1
value=50
}
"""

for name, spec in CELLS.items():
    out = [HEAD % (name, LEAF, spec["note"], name)]
    for i, (x, lower, upper) in enumerate(spec["legs"], start=1):
        out.append(RES % (x, "R%d" % i))
        out.append("N %d -60 %d -30 { lab=%s}\n" % (x, x, lower))
        out.append("N %d 30 %d 60 { lab=%s}\n" % (x, x, upper))
    # LOAD hangs a 50 ohm rppd off each reference plane down to ground. Same wiring shape as
    # a leg: the signal net on the lower terminal, GND on the upper.
    for x, nm, net in spec.get("loads", []):
        out.append(RPPD % (x, nm))
        out.append("N %d -60 %d -30 { lab=%s}\n" % (x, x, net))
        out.append("N %d 30 %d 60 { lab=GND}\n" % (x, x))
        out.append("C {devices/lab_pin.sym} %d -60 0 0 {name=q%s sig_type=std_logic lab=%s}\n"
                   % (x, nm, net))
    if spec["stub"]:
        lab, x = spec["stub"]
        out.append("N %d 0 %d 30 { lab=%s}\n" % (x, x, lab))
    for j, (sym, x, y, lab) in enumerate(spec["pins"], start=1):
        out.append("C {devices/%s.sym} %d %d 0 0 {name=p%d lab=%s}\n" % (sym, x, y, j, lab))
    # A lab= attribute on a wire does not name a net on its own; the name comes from a
    # symbol sitting on the wire. The first netlist run proved that, with the second
    # resistor landing on net1 instead of GND. A net that already carries a pin elsewhere
    # gets a plain lab_pin here rather than a second port.
    for j, (x, y, lab) in enumerate(spec["labels"], start=1):
        out.append("C {devices/lab_pin.sym} %d %d 0 0 {name=l%d sig_type=std_logic lab=%s}\n"
                   % (x, y, j, lab))

    folder = os.path.join(PROJECT, "designlib", "teg", name)
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, name + ".sch"), "w").write("".join(out))
    # lvs_netlist is what makes xschem wrap the top level in an uncommented .subckt and
    # honour each symbol's lvs_format. Without it the deck reports no schematic counterpart
    # for the top cell, and the netlist still looks complete.
    open(os.path.join(folder, "xschemrc"), "w").write(
        open(os.path.join(PROJECT, "designlib", "teg", LEAF, "xschemrc")).read()
        + "\nset lvs_netlist 1\n")
    print("wrote %s" % os.path.join(folder, name + ".sch"))
