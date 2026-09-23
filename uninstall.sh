#!/usr/bin/env bash
# Remove a source installation without deleting notes unless explicitly asked.
set -euo pipefail

PURGE_DATA=false
if [[ "${1:-}" == "--purge-data" ]]; then
    PURGE_DATA=true
elif [[ $# -gt 0 ]]; then
    echo "Usage: ./uninstall.sh [--purge-data]" >&2
    exit 2
fi

DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
APP_DIR="${HOME}/.local/lib/tacklet"
BIN_DIR="${HOME}/.local/bin"
APPLICATIONS_DIR="${DATA_HOME}/applications"
DESKTOP_FILE="${APPLICATIONS_DIR}/io.github.father1993.Tacklet.desktop"
DATA_DIR="${DATA_HOME}/tacklet"

remove_link() {
    local path="$1"
    if [[ -L "${path}" ]] && [[ "$(readlink -f "${path}")" == "${APP_DIR}/"* ]]; then
        rm -f "${path}"
    fi
}

remove_link "${BIN_DIR}/tacklet"
remove_link "${BIN_DIR}/tacklet-update"
rm -rf "${APP_DIR}"
rm -f "${DESKTOP_FILE}"
update-desktop-database "${APPLICATIONS_DIR}" >/dev/null 2>&1 || true

if [[ "${PURGE_DATA}" == true ]]; then
    rm -f "${DATA_DIR}/notes.json"
    rmdir "${DATA_DIR}" 2>/dev/null || true
    echo "Tacklet source installation and local notes were removed."
else
    echo "Tacklet source installation was removed. Notes were kept at: ${DATA_DIR}/notes.json"
    echo "Use ./uninstall.sh --purge-data only if you intentionally want to delete notes."
fi
