"""Split a DRC database into density rules and everything else.

The owner said density errors are acceptable on these, since they are subcells, so the only
number that matters is what is left after those are set aside. Whether a rule is a density
one is taken from its own description in the database rather than from a list of names kept
here, which would go stale the moment the deck grows a rule.
"""
import collections
import io
import re
import sys

b = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
desc = dict(re.findall(r"<name>([A-Za-z0-9_.]+)</name>\s*<description>([^<]*)</description>", b))
counts = collections.Counter(
    re.findall(r"<category>.?([A-Za-z0-9_]+\.[A-Za-z0-9_]+).?</category>", b))

def is_fill(text):
    """Whether a rule belongs to the fill family, by its own words.

    Matching on "density" alone is not enough. AFil.g2 reads "Min. Activ coverage ratio for
    any 800.0 x 800.0 um2 chip area", which is the same family stated differently, and it was
    reported as an ordinary violation on the assembled top cell until this was widened.
    """
    t = text.lower()
    return "density" in t or "coverage ratio" in t


dens, other = [], []
for k, n in sorted(counts.items()):
    d = desc.get(k, "")
    (dens if is_fill(d) else other).append((k, n, d))

print("density  %s" % (", ".join("%s %d" % (k, n) for k, n, _ in dens) or "none"))
if other:
    print("OTHER    %s" % ", ".join("%s %d" % (k, n) for k, n, _ in other))
    for k, n, d in other:
        print("           %-14s %3d  %s" % (k, n, d[:80]))
else:
    print("OTHER    none")
