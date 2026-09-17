#!/usr/bin/env bash
# LVS wrapper.  Usage:  ./tools/run_lvs.sh <gds> <netlist> <topcell>
#
# Same reason as the DRC wrapper: --run_dir keeps the output inside the design tree
# instead of the PDK tree.
set -uo pipefail
set +e

: "${PDK_LVS:?source env.sh first}"
: "${DESIGN_ROOT:?source env.sh first}"

GDS=${1:?usage: run_lvs.sh <gds> <netlist> <topcell>}
NET=${2:?usage: run_lvs.sh <gds> <netlist> <topcell>}
TOP=${3:?usage: run_lvs.sh <gds> <netlist> <topcell> [extra run_lvs.py args]}
shift 3 2>/dev/null || shift $#   # anything further is passed to run_lvs.py verbatim


# The PDK runner needs the interpreter that `make env` built; the system python3 lacks the
# klayout module and fails with ModuleNotFoundError before doing any work.
PY=${PDK_PY:-}
if [ -z "$PY" ] || [ ! -x "$PY" ]; then
    echo "PDK_PY is not set or not executable: ${PY:-<unset>}" >&2
    echo "    Build it once with:  cd $PDK_ROOT && make env" >&2
    exit 1
fi

[ -f "$GDS" ] || { echo "no such GDS: $GDS" >&2; exit 1; }
[ -f "$NET" ] || { echo "no such netlist: $NET" >&2; exit 1; }

STAMP=$(date +%F_%H%M%S)
# Results follow the site layout standard of 2026-09-10:
#   verification/<libname>/<cellname>/<result>/<toolname>
# The library is read off the GDS path (designlib/<lib>/<cell>/...), so moving the cell tree
# moves its results with it instead of stranding them. The <toolname> level exists so KLayout
# and PVS do not overwrite one another.
GDSABS=$(readlink -f "$GDS")   # relative paths must resolve too
case "$GDSABS" in
  */designlib/*) LIB=${GDSABS#*/designlib/}; LIB=${LIB%%/*} ;;
  *)             LIB=teg ;;
esac
[ -n "$LIB" ] || LIB=teg
RUN="$DESIGN_ROOT/verification/$LIB/$TOP/lvs_result/klayout"
# Keep the previous run rather than writing over it. .before_* is git-ignored.
if [ -d "$RUN" ] && [ -n "$(ls -A "$RUN" 2>/dev/null)" ]; then
    mv "$RUN" "${RUN}.before_${STAMP}"
fi
mkdir -p "$RUN"

echo "layout   : $GDS"
echo "netlist  : $NET"
echo "topcell  : $TOP"
echo "deck     : $PDK_LVS/sg13g2.lvs"
echo "run_dir  : $RUN"

"$PY" "$PDK_LVS/run_lvs.py" \
  --layout "$GDS" \
  --netlist "$NET" \
  --topcell "$TOP" \
  --run_dir "$RUN" \
  --run_mode deep \
  "$@" \
  2>&1 | tee "$RUN/run.log"
STATUS=${PIPESTATUS[0]}

{
  echo "gds        $GDS"
  echo "gds_md5    $(md5sum "$GDS" | cut -d' ' -f1)"
  echo "netlist    $NET"
  echo "net_md5    $(md5sum "$NET" | cut -d' ' -f1)"
  echo "topcell    $TOP"
  echo "pdk_root   $PDK_ROOT"
  echo "python     $PY"
  echo "pdk_commit $(git -C "$PDK_ROOT" rev-parse HEAD)"
  echo "when       $STAMP"
  echo "exit       $STATUS"
  echo "verdict    $([ "$STATUS" -eq 0 ] && echo clean || echo violations)"
} > "$RUN/PROVENANCE.txt"

echo
echo "results in $RUN"
# Hand the caller the tool's own verdict rather than swallowing it.
exit "$STATUS"
