#!/usr/bin/env bash
# Push-Wrapper für 'main': bumpt PACKAGE_VERSION in app/core/config.py,
# amendet den Bump in den letzten Commit und pusht dann regulär.
#
# Vorteil gegenüber dem reinen pre-push-Hook: der Push läuft in einem
# Rutsch durch, ohne "failed to push some refs"-Fehlermeldung, weil der
# gepushte HEAD bereits den Bump enthält.
#
# Nutzung:  scripts/push-main.sh
#
# Der pre-push-Hook bleibt als Fallback erhalten. Damit er beim Push des
# Wrappers nicht erneut bumpt, wird hier mit --no-verify gepusht.

set -euo pipefail

TARGET_BRANCH="main"
CONFIG_FILE="app/core/config.py"
REMOTE="${1:-origin}"

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$TARGET_BRANCH" ]; then
    echo "[push-main] Abbruch: HEAD ist '$current_branch', nicht '$TARGET_BRANCH'." >&2
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[push-main] Abbruch: $CONFIG_FILE nicht gefunden." >&2
    exit 1
fi

# Working tree muss sauber sein (außer in $CONFIG_FILE), sonst lehnen wir ab.
if ! git diff --quiet -- . ":(exclude)$CONFIG_FILE" \
   || ! git diff --cached --quiet -- . ":(exclude)$CONFIG_FILE"; then
    echo "[push-main] Working tree hat unbestätigte Änderungen außerhalb von $CONFIG_FILE." >&2
    echo "[push-main] Bitte zuerst committen oder stashen, dann erneut pushen." >&2
    exit 1
fi

# HEAD darf noch nicht auf dem Remote sein, sonst würde --amend einen
# bereits gepushten Commit umschreiben.
remote_ref="refs/remotes/${REMOTE}/${TARGET_BRANCH}"
if git rev-parse --verify --quiet "$remote_ref" >/dev/null; then
    remote_sha=$(git rev-parse "$remote_ref")
    if git merge-base --is-ancestor HEAD "$remote_sha" 2>/dev/null; then
        echo "[push-main] Abbruch: HEAD ist bereits auf ${REMOTE}/${TARGET_BRANCH}." >&2
        echo "[push-main] Es gibt nichts zu pushen." >&2
        exit 1
    fi
fi

last_msg=$(git log -1 --pretty=%B)
if printf '%s' "$last_msg" | grep -q '\[skip-bump\]'; then
    echo "[push-main] Letzter Commit enthält [skip-bump] → kein Bump, direkter Push." >&2
    git push --no-verify "$REMOTE" "HEAD:refs/heads/${TARGET_BRANCH}"
    exit 0
fi

PYTHON_BIN="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

bump_output=$(
    CONFIG_FILE="$CONFIG_FILE" "$PYTHON_BIN" - <<'PY'
import os
import pathlib
import re
import sys

path = pathlib.Path(os.environ["CONFIG_FILE"])
src = path.read_text(encoding="utf-8")
pat = re.compile(r'^(PACKAGE_VERSION\s*=\s*")(\d+)\.(\d+)\.(\d+)(")', re.M)
m = pat.search(src)
if not m:
    sys.stderr.write("PACKAGE_VERSION nicht gefunden\n")
    sys.exit(2)
major, minor, patch = int(m[2]), int(m[3]), int(m[4])
new_version = f"{major}.{minor}.{patch + 1}"
old_version = f"{major}.{minor}.{patch}"
new_src = pat.sub(rf'\g<1>{new_version}\5', src, count=1)
path.write_text(new_src, encoding="utf-8")
print(f"{old_version} {new_version}")
PY
)

old_version=$(echo "$bump_output" | awk '{print $1}')
new_version=$(echo "$bump_output" | awk '{print $2}')

echo "[push-main] PACKAGE_VERSION: $old_version → $new_version" >&2

git add -- "$CONFIG_FILE"
git commit --amend --no-edit --no-verify >/dev/null

echo "[push-main] Pushe ${REMOTE}/${TARGET_BRANCH}…" >&2
# --no-verify: pre-push-Hook bleibt aus, weil wir den Bump bereits erledigt haben.
git push --no-verify "$REMOTE" "HEAD:refs/heads/${TARGET_BRANCH}"
