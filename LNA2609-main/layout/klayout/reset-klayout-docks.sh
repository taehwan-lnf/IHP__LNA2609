#!/usr/bin/env bash
# Put KLayout's docked panels back where they belong.
#
#     ./tools/reset-klayout-docks.sh            # reset the dock arrangement
#     ./tools/reset-klayout-docks.sh --geometry # also reset the main window size/position
#
# Try the menu first
# ------------------
# KLayout has a built-in command for this and it needs no restart:
#
#     View > Restore Window          (menu path view_menu.reset_window_state)
#
# It puts every panel back in its default place with the session still open, which is
# almost always what is wanted when a panel has been torn off. Reach for this script only
# when that does not help, which means the saved state itself is the problem: the panel
# comes back floating on every start, or KLayout will not start cleanly at all.
#
# This was not in the original header because the menu was never looked for. Corrected
# 2026-08-31 after listing the main window's actions and finding reset_window_state there.
#
# Why this script exists
# ----------------------
# KLayout keeps its panel arrangement in ~/.klayout/klayoutrc under <window-state>, a
# base64 Qt QMainWindow::saveState() blob. Decoding it shows the panels by object name:
#
#     navigator_dock_widget  hp_dock_widget      libs_dock_widget   eo_dock_widget
#     bookmarks_dock_widget  lp_dock_widget      lt_dock_widget     toolbar
#
# lp_dock_widget is the Layers panel. Once a panel is torn off into its own top-level
# window, dragging it back relies on Qt tracking the pointer over the main window while a
# button is held. Under WSLg each floating dock is a separate X11 window and that tracking
# is unreliable, so the panel can end up impossible to re-dock by mouse. Clearing the saved
# state makes Qt fall back to KLayout's built-in default arrangement on the next start.
#
# The geometry is left alone by default: it holds the window size and position, which is
# usually worth keeping. Pass --geometry to reset that too.
set -uo pipefail

RC="$HOME/.klayout/klayoutrc"
RESET_GEOMETRY=0
[ "${1:-}" = "--geometry" ] && RESET_GEOMETRY=1

if [ ! -f "$RC" ]; then
    echo "no klayoutrc at $RC" >&2
    exit 1
fi

# KLayout rewrites klayoutrc when it exits, so editing it under a running instance would
# simply be overwritten. Refuse rather than appear to work.
# Match the executable itself and not any command line that merely mentions klayout: an
# earlier version listed this very script as a running instance, which read as nonsense.
RUNNING=$(pgrep -a -x klayout 2>/dev/null)
if [ -n "$RUNNING" ]; then
    echo "KLayout is running. It rewrites $RC on exit, so this edit would be lost." >&2
    echo "    Close every KLayout window first, then run this again." >&2
    printf '    %s\n' "$RUNNING" >&2
    exit 1
fi

BAK="$RC.bak-$(date +%F_%H%M%S)"
cp "$RC" "$BAK"

python3 - "$RC" "$RESET_GEOMETRY" <<'PY'
import io
import re
import sys

rc, reset_geom = sys.argv[1], sys.argv[2] == "1"
t = io.open(rc, encoding="utf-8", errors="replace").read()

def clear(text, key):
    pat = re.compile(r"(<%s>)(.*?)(</%s>)" % (key, key), re.S)
    m = pat.search(text)
    if not m:
        print("  %-16s (not present)" % key)
        return text
    print("  %-16s cleared (%d chars)" % (key, len(m.group(2))))
    return pat.sub(r"\1\3", text, count=1)

t = clear(t, "window-state")
if reset_geom:
    t = clear(t, "window-geometry")

io.open(rc, "w", encoding="utf-8", newline="").write(t)
PY

echo "backup: $BAK"
echo "Start KLayout again; the panels come back in their default places."
