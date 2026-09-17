#!/usr/bin/env bash
# Netlist, DRC and LVS every cell named on the command line, or every GSG_dut_* if none.
#
# --combine_devices is passed always. Without it the run reports "combine_devices: SKIPPED"
# and the multi-device cells fail, because the layout extractor returns one merged device
# per column while the schematic carries one instance per drawn device.
set -u
cd "$(dirname "$0")/.."
. ./env.sh >/dev/null 2>&1

cells=("$@")
if [ ${#cells[@]} -eq 0 ]; then
  cells=($(ls -d designlib/teg/GSG_dut_* 2>/dev/null | xargs -n1 basename))
fi

printf "%-40s %-8s %-34s %s\n" CELL NETLIST DRC LVS
for c in "${cells[@]}"; do
  d="designlib/teg/$c"
  if [ ! -d "$d" ]; then
    printf "%-40s %s\n" "$c" "no such folder"
    continue
  fi

  # The netlist is taken from --command rather than from -n, and the difference is not
  # cosmetic. With -n xschem writes the netlist during startup, before any hook runs, so
  # "xschem set format lvs_format" arrives too late and the device line comes out in the
  # ngspice format: XQ1 ... npn13g2v Nx=5 El=5 mm_ok=1 rather than the extractor's
  # QQ1 ... npn13g2v we=5e-06 le=120.0n Nx=5. Nothing warns about this. The netlist looks
  # complete and LVS then reports no schematic counterpart for the top cell.
  #
  # set lvs_netlist 1 in the cell's rc handles the .subckt wrapper; it does NOT select
  # lvs_format, which is why both are needed.
  rm -f "$d/$c.spice"
  ( cd "$d" && xschem -x -q -s --rcfile ./xschemrc \
      --command "xschem set format lvs_format; xschem netlist; exit" \
      "$c.sch" -o . >/dev/null 2>&1 )
  # What makes a netlist usable here is the uncommented .subckt line: that is what the deck
  # matches against the top cell, and it is absent whenever lvs_netlist was not set. Looking
  # for a transistor line instead was wrong, because OPEN, SHORT and THRU carry no device
  # and were reported MISSING while their LVS passed.
  if grep -q "IS MISSING" "$d/$c.spice" 2>/dev/null; then
    nl=NOSYM
  elif grep -qi "^\.subckt" "$d/$c.spice" 2>/dev/null; then
    nl=ok
  else
    nl=MISSING
  fi

  rm -rf "$d/drc_report"
  mkdir -p "$d/drc_report"
  "$PDK_PY" "$PDK_DRC/run_drc.py" --path="$PWD/$d/$c.gds" --topcell="$c" \
      --run_dir="$PWD/$d/drc_report" --run_mode=deep --mp=4 \
      > "$d/drc_report/run.log" 2>&1
  db="$d/drc_report/${c}_${c}_full.lyrdb"
  if [ -f "$db" ]; then
    drc=$(python3 tools/sum_drc.py "$db")
  else
    drc="(no rdb)"
  fi

  rm -rf "$d/lvs_report"
  mkdir -p "$d/lvs_report"
  # LVS runs deep, on owner instruction of 2026-09-02. run_lvs.py defaults to flat and this
  # set ran that way for a long time, which cost it two things.
  #
  # Flat collapses the layout into a single circuit, so a schematic that keeps any hierarchy
  # has subcircuits with nothing to pair against. That is what made the assembled top cell
  # mismatch: five small tops ruled out the seal rings, the number of rings and the shared
  # substrate one at a time, and the same layout matched as soon as its top schematic was
  # flattened. Deep keeps the hierarchy on both sides, twenty-six circuits against
  # twenty-six, so the top schematic can stay hierarchical.
  #
  # Flat also carries the R270 placement into the extracted dimensions, reporting
  # we=5000n le=120n where the device is drawn 0.12 by 5.0. That is what the *_lvsfix symbol
  # copies were for. Deep reads the device in its own unrotated frame and reports it as
  # drawn, which is what the stock PDK symbols already emit, so the copies are no longer used.
  "$PDK_PY" "$PDK_LVS/run_lvs.py" --layout="$PWD/$d/$c.gds" --netlist="$PWD/$d/$c.spice" \
      --topcell="$c" --run_dir="$PWD/$d/lvs_report" --run_mode=deep \
      --combine_devices \
      > "$d/lvs_report/run.log" 2>&1
  if grep -qiE "congratulations|lvs successful|netlists match" "$d/lvs_report/run.log"; then
    lvs=PASS
  elif grep -qiE "lvs failed|do not match|mismatch" "$d/lvs_report/run.log"; then
    lvs=FAIL
  else
    lvs="?"
  fi

  # Both reports already live in the cell's own directory. This puts a summary beside each,
  # on the owner's instruction of 2026-09-02: drc_summary.txt and lvs_summary.txt give the
  # number, the title, the description and the count. They are what .gitignore keeps, the
  # logs and databases they come from being regenerable.
  python3 tools/write_summary.py "$c" >/dev/null 2>&1

  printf "%-40s %-8s %-34s %s\n" "$c" "$nl" "$drc" "$lvs"
done
