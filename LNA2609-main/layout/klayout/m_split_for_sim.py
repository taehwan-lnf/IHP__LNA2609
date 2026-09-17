"""Simulate each laid-out device as several in-range ones, and say what that changes.

Owner instruction of 2026-09-03: the layout keeps the twelve single devices, and the
simulation raises m and lowers Nx so that every simulated instance sits inside the range the
model card declares. The ranges are npn13G2 Nx 1 to 10, npn13G2L and npn13G2V Nx 1 to 4.

THE SUBSTITUTION IS NOT FREE, AND THE ARITHMETIC SAYS EXACTLY WHY

Take one term of the model written as C * (Nx*0.25)**q. One device of Nx = N gives

    C * (N*0.25)**q

and m devices of Nx = N/m in parallel give

    m * C * ((N/m)*0.25)**q  =  C * (N*0.25)**q * m**(1-q)

so the split lands on m**(1-q) times the single device. Where q = 1 the two are IDENTICAL, and
that covers is, ikf and, on npn13G2, cjc and cbco. Where q < 1 the split reads HIGH, and the
further q is below one the worse it gets. Resistances written as (4/Nx)**q behave the same way
with the sign reversed, m**(q-1), so a split reads LOW there.

    exponent  q        deviation of the split      worst case in this set
    1.000              none                        exact
    0.975  caps        m**0.025                    +7 % at m = 17
    0.950  cje, cbeo   m**0.050                    +15 % at m = 17
    0.950  Rb npn13G2  m**-0.050                   -9 % at m = 6
    0.880  re          m**-0.120                   -22 % at m = 6
    0.800  cjcp L,G2   m**0.200                    +78 % at m = 13
    0.500  cjcp V      m**0.500                    +124 % at m = 5

The one to watch is cjcp, the collector-to-substrate junction capacitance. It is also the one
the split gets most wrong, and that is physically reasonable rather than a modelling artefact:
m separate devices really do sit in m separate collector tubs, so they really do present more
junction area to the substrate than one long device does. The split therefore OVERSTATES the
substrate loading of the device that is actually on the chip.

The terms that set RF gain come off better. Rb is exact on npn13G2L and npn13G2V, whose
resistances all carry (4/Nx)**1, and Cbc is within a few percent everywhere.

Run it with:  wsl python3 tools/m_split_for_sim.py
"""
NMAX = {"npn13G2": 10, "npn13G2L": 4, "npn13G2V": 4}

# term: (exponent on (Nx*0.25) for a capacitance or current, exponent on (4/Nx) for a
# resistance). Quoted from libs.tech/ngspice/models/sg13g2_hbt_mod.lib.
TERMS = {
    "npn13G2":  {"rbx": ("R", 0.95), "rbi": ("R", 0.95), "re": ("R", 1.0), "rcx": ("R", 1.0),
                 "cje": ("C", 0.975), "cbco": ("C", 1.0), "cjc": ("C", 1.0),
                 "cjcp": ("C", 0.8), "is": ("C", 1.0), "ikf": ("C", 1.0)},
    "npn13G2L": {"rbx": ("R", 1.0), "rbi": ("R", 1.0), "re": ("R", 0.88), "rcx": ("R", 0.9),
                 "cje": ("C", 0.95), "cbco": ("C", 0.975), "cjc": ("C", 0.975),
                 "cjcp": ("C", 0.8), "is": ("C", 1.0), "ikf": ("C", 1.0)},
    "npn13G2V": {"rbx": ("R", 1.0), "rbi": ("R", 1.0), "re": ("R", 0.88), "rcx": ("R", 0.9),
                 "cje": ("C", 0.95), "cbco": ("C", 0.975), "cjc": ("C", 0.975),
                 "cjcp": ("C", 0.5), "is": ("C", 1.0), "ikf": ("C", 1.0)},
}

CELLS = [
    ("npn13G2V", 12, 2.5), ("npn13G2V", 10, 2.5), ("npn13G2V", 8, 2.5), ("npn13G2V", 6, 2.5),
    ("npn13G2L", 17, 2.5), ("npn13G2L", 14, 2.5), ("npn13G2L", 11, 2.5), ("npn13G2L", 8, 2.5),
    ("npn13G2", 48, 0.9), ("npn13G2", 39, 0.9), ("npn13G2", 32, 0.9), ("npn13G2", 22, 0.9),
]


def split(n, nmax):
    """Fewest instances, each within range, sizes as equal as they go.

    Fewest matters: every deviation above grows with the instance count, so a split into five
    is closer to the drawn device than a split into seventeen. An even split is used rather
    than filling instances to nmax, because equal instances keep the schematic to one line.
    """
    k = -(-n // nmax)                       # ceiling division
    base, extra = divmod(n, k)
    return [base + 1] * extra + [base] * (k - extra)


def deviation(flavour, n, parts, kind, q):
    """Ratio of the split's total to the single drawn device, for one model term."""
    if kind == "C":
        one = (n * 0.25) ** q
        tot = sum((p * 0.25) ** q for p in parts)
    else:
        one = (4.0 / n) ** q
        tot = 1.0 / sum(1.0 / (4.0 / p) ** q for p in parts)
    return tot / one


print("%-9s %-4s %-5s %-22s %s" % ("FLAVOUR", "Nx", "le", "SIMULATE AS", "instances"))
rows = []
for flavour, n, le in CELLS:
    parts = split(n, NMAX[flavour])
    grouped = {}
    for p in parts:
        grouped[p] = grouped.get(p, 0) + 1
    txt = " + ".join("m=%d Nx=%d" % (c, k) for k, c in sorted(grouped.items(), reverse=True))
    print("%-9s %-4d %-5.1f %-22s %d" % (flavour, n, le, txt, len(parts)))
    rows.append((flavour, n, parts))

print()
keys = ["rbx", "rbi", "re", "rcx", "cje", "cbco", "cjc", "cjcp", "is", "ikf"]
print("분해가 단일 소자 대비 몇 배가 되는가 (1.000 이면 완전히 같다)")
print("%-9s %-4s %s" % ("FLAVOUR", "Nx", " ".join("%-7s" % k for k in keys)))
for flavour, n, parts in rows:
    vals = []
    for k in keys:
        kind, q = TERMS[flavour][k]
        vals.append("%-7.3f" % deviation(flavour, n, parts, kind, q))
    print("%-9s %-4d %s" % (flavour, n, " ".join(vals)))
