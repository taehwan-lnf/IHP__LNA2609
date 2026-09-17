"""At a fixed A_E(final), does raising Nx or raising El give the lower base resistance?

Owner question of 2026-09-03. The answer is not argued from device physics here, it is read
out of the PDK's own model card, libs.tech/ngspice/models/sg13g2_hbt_mod.lib, because that is
what the owner will simulate. Every expression below is quoted from that file verbatim.

    npn13G2     rbx = 6.93E+00*(4/Nx)**0.95     rbi = 2.20E+01*(4/Nx)**0.95
                le is FIXED at 0.90, so this flavour has no El to trade.

    npn13G2l    rbx = 2.54E+00*(2.5/El)**0.7*(4/Nx)
                rbi = 7.26E+00*(2.5/El)**0.7*(4/Nx)
                cjc = 3.83E-15*(El/2.5)**0.85*(Nx*0.25)**0.975
                cbco= 6.33E-15*(El/2.5)**0.85*(Nx*0.25)**0.975

    npn13G2v    rbx = 1.54E+00*(2.5/El)**0.75*(4/Nx)
                rbi = 6.60E+00*(2.5/El)**0.75*(4/Nx)
                cjc = 2.52E-15*(El/2.5)**0.85*(Nx*0.25)**0.975
                cbco= 4.37E-15*(El/2.5)**0.85*(Nx*0.25)**0.975

WHAT THE EXPONENTS SAY BEFORE ANY NUMBER IS PUT IN

Base resistance falls as 1/Nx exactly, and as El to the power 0.7 or 0.75, which is LESS than
one. Hold the area fixed, so that Nx and El trade one for one, and substitute Nx = K/El:

    Rb  proportional to  El**(-p) * Nx**(-1)  =  El**(1-p) / K

with p = 0.7 for npn13G2l and 0.75 for npn13G2v. The exponent 1-p is POSITIVE, so at equal
area a longer emitter gives a HIGHER base resistance. Raising Nx is the way to lower it.

The collector capacitance goes the other way, but by less:

    Cbc proportional to  El**0.85 * Nx**0.975  ->  El**(0.85-0.975) = El**(-0.125)

so the product that sets fmax still favours more fingers:

    Rb*Cbc proportional to  El**(1-p-0.125)     npn13G2l  El**0.175
                                                npn13G2v  El**0.125

The exponents are small, so the effect is real but modest, and the numbers below say how
modest. What is NOT modest is the layout cost, which is measured rather than modelled and is
printed alongside.

Run it with:  wsl python3 tools/rb_split.py
"""
import os

DWE_DLE = {"npn13G2": (0.050, 0.060), "npn13G2L": (0.060, 0.050), "npn13G2V": (0.060, 0.050)}
WE = {"npn13G2": 0.07, "npn13G2L": 0.07, "npn13G2V": 0.12}

# Coefficient, El exponent, Nx exponent, taken from the model card as quoted above.
MODEL = {
    "npn13G2L": {
        "rbx":  (2.54e0, 0.7, 1.0),
        "rbi":  (7.26e0, 0.7, 1.0),
        "rbp":  (15.0, 0.7, 1.0),
        "cjc":  (3.83e-15, 0.85, 0.975),
        "cbco": (6.33e-15, 0.85, 0.975),
        "ikf":  (0.032, 1.0, 1.0),
    },
    "npn13G2V": {
        "rbx":  (1.54e0, 0.75, 1.0),
        "rbi":  (6.60e0, 0.75, 1.0),
        "rbp":  (6.5, 0.75, 1.0),
        "cjc":  (2.52e-15, 0.85, 0.975),
        "cbco": (4.37e-15, 0.85, 0.975),
        "ikf":  (0.022, 1.0, 1.0),
    },
}


def res(flavour, key, el, nx):
    """A resistance term: coefficient * (2.5/El)**p * (4/Nx)."""
    c, p, _ = MODEL[flavour][key]
    return c * (2.5 / el) ** p * (4.0 / nx)


def cap(flavour, key, el, nx):
    """A capacitance term: coefficient * (El/2.5)**0.85 * (Nx*0.25)**0.975."""
    c, p, q = MODEL[flavour][key]
    return c * (el / 2.5) ** p * (nx * 0.25) ** q


def cur(flavour, el, nx):
    c, _, _ = MODEL[flavour]["ikf"]
    return c * (el / 2.5) * (nx * 0.25)


def area_final(flavour, m, nx, le):
    dwe, dle = DWE_DLE[flavour]
    return m * nx * (WE[flavour] + dwe) * (le + dle)


# The measured layout cost, taken from the build log of tools/sweep_dut.py: where the coplanar
# ground has to start once the device and its guard ring are in the slot. The nominal start,
# with nothing in the way, is 19.50 um.
GROUND = {
    ("npn13G2L", 1, 20, 2.5): 38.5,
    ("npn13G2L", 2, 10, 2.5): 41.0,
    ("npn13G2L", 1, 48, 1.0): 77.7,
    ("npn13G2V", 1, 7, 5.0): 19.5,
    ("npn13G2V", 1, 14, 2.5): 27.1,
    ("npn13G2V", 1, 35, 1.0): 51.7,
}

POINTS = {
    "npn13G2L": [(1, 20, 2.5), (2, 10, 2.5), (1, 48, 1.0)],
    "npn13G2V": [(1, 7, 5.0), (1, 14, 2.5), (1, 35, 1.0)],
}

for flavour, pts in POINTS.items():
    print("=== %s ===" % flavour)
    print("   %-4s %-5s %-5s %-10s %-8s %-8s %-8s %-10s %-11s %s"
          % ("m", "Nx", "El", "AE(final)", "rbx", "rbi", "Rb tot", "Cbc", "Rb*Cbc", "ground |y|"))
    rows = []
    for m, nx, el in pts:
        a = area_final(flavour, m, nx, el)
        # m devices in parallel: every resistance divides by m, every capacitance multiplies
        rbx = res(flavour, "rbx", el, nx) / m
        rbi = res(flavour, "rbi", el, nx) / m
        rb = rbx + rbi
        cbc = (cap(flavour, "cjc", el, nx) + cap(flavour, "cbco", el, nx)) * m
        g = GROUND.get((flavour, m, nx, el))
        rows.append((m, nx, el, a, rbx, rbi, rb, cbc, rb * cbc, g))
        print("   %-4d %-5d %-5.1f %-10.4f %-8.3f %-8.3f %-8.3f %-10.3f %-11.4f %s"
              % (m, nx, el, a, rbx, rbi, rb, cbc * 1e15, rb * cbc * 1e12,
                 "%.1f um" % g if g else "-"))

    # normalise to exactly equal area so the comparison is not confounded by the 1 to 4 percent
    # area spread of the integer points above
    base = rows[0]
    print("   같은 면적으로 환산했을 때 (기준: 첫 줄):")
    for m, nx, el, a, rbx, rbi, rb, cbc, rc, g in rows:
        # k is how much the device would have to grow to reach the reference area. Growing a
        # device by k divides its resistance by k and multiplies its capacitance by k, so the
        # normalisation divides Rb and multiplies Cbc. Writing it the other way round, which
        # this line did at first, moved every figure about two points in the wrong direction.
        # The Rb*Cbc product needs no correction at all, one factor cancelling the other,
        # which is a useful check that the normalisation is the right way up.
        k = base[3] / a
        print("      Nx=%-4d El=%-4.1f   Rb %+6.1f %%   Cbc %+6.1f %%   Rb*Cbc %+6.1f %%"
              % (nx, el, (rb / k / base[6] - 1) * 100,
                 (cbc * k / base[7] - 1) * 100,
                 (rc / base[8] - 1) * 100))
    print()

print("npn13G2 는 le 가 0.90 으로 고정이므로 이 선택 자체가 없다.")
print("   rbx = 6.93*(4/Nx)**0.95, rbi = 22.0*(4/Nx)**0.95 로 Nx 하나에만 의존한다.")
for nx in (10, 20, 30, 40, 56):
    rbx = 6.93 * (4.0 / nx) ** 0.95
    rbi = 22.0 * (4.0 / nx) ** 0.95
    print("      Nx=%-4d AE(final)=%.4f um2   rbx %.3f   rbi %.3f   Rb %.3f ohm"
          % (nx, area_final("npn13G2", 1, nx, 0.9), rbx, rbi, rbx + rbi))
