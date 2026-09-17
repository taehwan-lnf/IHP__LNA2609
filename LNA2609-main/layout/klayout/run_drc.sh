#!/usr/bin/env bash
# DRC wrapper.  Usage:  ./tools/run_drc.sh <gds> <topcell> [precheck|full]
#
# The only reason this wrapper exists is --run_dir. Without it, run_drc.py creates a
# timestamped directory under the PDK tree, which would put my results inside the fab's
# read-only database. Everything else here is a thin pass-through to the PDK runner.
set -uo pipefail
set +e

: "${PDK_DRC:?source env.sh first}"
: "${DESIGN_ROOT:?source env.sh first}"

GDS=${1:?usage: run_drc.sh <gds> <topcell> [precheck|full] [extra run_drc.py args]}
TOP=${2:?usage: run_drc.sh <gds> <topcell> [precheck|full] [extra run_drc.py args]}
MODE=${3:-precheck}
shift 3 2>/dev/null || shift $#   # anything further is passed to run_drc.py verbatim


# The PDK runner needs the interpreter that `make env` built; the system python3 lacks the
# klayout module and fails with ModuleNotFoundError before doing any work.
PY=${PDK_PY:-}
if [ -z "$PY" ] || [ ! -x "$PY" ]; then
    echo "PDK_PY is not set or not executable: ${PY:-<unset>}" >&2
    echo "    Build it once with:  cd $PDK_ROOT && make env" >&2
    exit 1
fi

[ -f "$GDS" ] || { echo "no such GDS: $GDS" >&2; exit 1; }

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
RUN="$DESIGN_ROOT/verification/$LIB/$TOP/drc_result/klayout"
# Keep the previous run rather than writing over it. .before_* is git-ignored.
if [ -d "$RUN" ] && [ -n "$(ls -A "$RUN" 2>/dev/null)" ]; then
    mv "$RUN" "${RUN}.before_${STAMP}"
fi
mkdir -p "$RUN"

# precheck  = the minimal set run_drc.py itself describes as "typically required for
#             foundry precheck". Fast, and the right first gate.
# full      = the whole deck. Slower, and what a submission has to survive.
case "$MODE" in
  precheck) EXTRA=(--precheck_drc) ;;
  full)     EXTRA=() ;;
  *)        echo "mode must be precheck or full" >&2; exit 2 ;;
esac

echo "GDS      : $GDS"
echo "topcell  : $TOP"
echo "mode     : $MODE $*"
echo "deck     : $PDK_DRC/ihp-sg13g2.drc"
echo "run_dir  : $RUN"

"$PY" "$PDK_DRC/run_drc.py" \
  --path "$GDS" \
  --topcell "$TOP" \
  --run_dir "$RUN" \
  "${EXTRA[@]}" "$@" \
  2>&1 | tee "$RUN/run.log"
STATUS=${PIPESTATUS[0]}

# Record what this run was actually made of, so the report can be trusted later.
{
  echo "gds        $GDS"
  echo "gds_md5    $(md5sum "$GDS" | cut -d' ' -f1)"
  echo "topcell    $TOP"
  echo "mode       $MODE"
  echo "pdk_root   $PDK_ROOT"
  echo "python     $PY"
  echo "pdk_commit $(git -C "$PDK_ROOT" rev-parse HEAD)"
  echo "pdk_branch $(git -C "$PDK_ROOT" branch --show-current)"
  echo "when       $STAMP"
  echo "exit       $STATUS"
  echo "verdict    $([ "$STATUS" -eq 0 ] && echo clean || echo violations)"
} > "$RUN/PROVENANCE.txt"

echo
echo "results in $RUN"
# Hand the caller the tool's own verdict rather than swallowing it.
exit "$STATUS"
