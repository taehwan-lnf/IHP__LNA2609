"""Explain in each corrected symbol why it exists, so the copy is not mistaken for drift.

A local copy of a PDK symbol is a maintenance liability: on the next PDK pull nothing will
tell whoever is reading that the copy is deliberate, or what it changed. The note goes in
the symbol's own header block, where anyone opening it in xschem will see it.
"""
import io
import os

# The project root, found from this file rather than declared: tools/ sits one level
# under it. DESIGN_ROOT still wins when set, and env.sh always sets it. This was a
# literal until 2026-09-07, when the tree was copied to the Rocky VM and the literal
# still named the WSL path, so nothing under tools/ could find its own devices/.
_ROOT = os.environ.get("DESIGN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LIB = os.path.join(_ROOT,
                   "lib", "sym")

NOTE = """*
* ---------------------------------------------------------------------------------
* LOCAL COPY. Only lvs_format is changed: the le and we parameter NAMES are swapped.
*
* Why. The SG13G2 LVS extractor and this symbol disagree on which dimension is called
* which, so a schematic built from the stock symbol cannot match its own layout.
* Measured on 2026-08-31 with npn13G2 Nx=10, the extractor writes
*
*     Q$1 ... npn13G2 we=900n le=70n Nx=10 m=4
*
* while the stock symbol writes le=900e-9 we=70.0n. The symbol is the side that is
* physically right, since this device has an emitter 0.07 um wide and 0.9 um long, so
* le=0.9 and we=0.07. The extractor is the one transposed. LVS compares the two
* regardless, so the netlist has to be written in the extractor's convention, and this
* copy does that and nothing else.
*
* Proof: with the stock symbol LVS reported "Netlists don't match" on
* GSG_dut_npn13G2_Nx10_le0p9u_we0p07u_m4; feeding the same netlist with le and we
* swapped gave "Netlists match", every other thing held equal.
*
* format= is untouched, so ngspice simulation is unaffected. Only the LVS netlist
* changes.
*
* Worth reporting upstream to IHP. If a later PDK release fixes the extractor, delete
* these copies and use sg13g2_pr directly again.
* ---------------------------------------------------------------------------------
"""

for stem in ("npn13G2", "npn13G2l", "npn13G2v"):
    path = os.path.join(LIB, stem + "_lvsfix.sym")
    t = io.open(path, encoding="utf-8").read()
    if "LOCAL COPY" in t:
        print("  %s already annotated" % os.path.basename(path))
        continue
    # The header block is the first line's brace, closed by a lone } on its own line.
    i = t.index("\n}\n")
    t = t[:i] + "\n" + NOTE + t[i:]
    io.open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("  annotated %s" % path)
