"""Summarise one DRC results database as "rule count, rule count".

Every inline <category> is counted, whatever its name looks like. This used to require a
dot in the name, on the grounds that the deck's grouping nodes have none and would be
counted as rules. Measured on the top's database on 2026-09-08, the grouping tree writes
<category> as a bare opening tag with the name in a <name> child, so an inline
<category>X</category> only ever occurs inside an <item>: 48023 tags in the file, 47175
of them inline, 1 in the tree, and 47175 is exactly the sum of the per-rule counts.

The dot was not harmless. via2_drw_Offgrid, via3_drw_Offgrid and via4_drw_Offgrid have no
dot, and on the assembled top they hold 14,628 markers each, so the summary reported
3,291 items where the database held 47,175 and the off-grid vias were never seen.
"""
import collections
import io
import re
import sys

b = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
pat = r"<category>'?([A-Za-z0-9_.]+)'?</category>"
c = collections.Counter(re.findall(pat, b))
print(", ".join("%s %d" % (k, v) for k, v in sorted(c.items())) or "clean")
