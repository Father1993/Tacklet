#!/usr/bin/env bash
# Install Tacklet for this user without sudo, keeping notes separate from code.
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/lib/tacklet"
BIN_DIR="${HOME}/.local/bin"
APPLICATIONS_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
OLD_APP_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/tacklet"
DESKTOP_FILE="${APPLICATIONS_DIR}/io.github.father1993.Tacklet.desktop"

if ! python3 "${SOURCE_DIR}/tacklet.py" --diagnose; then
    echo >&2
    echo "Tacklet was not installed: fix the errors above and run ./install.sh again." >&2
    exit 1
fi

mkdir -p "${APP_DIR}" "${BIN_DIR}" "${APPLICATIONS_DIR}"
cp -R "${SOURCE_DIR}/sticky" "${SOURCE_DIR}/tacklet.py" \
    "${SOURCE_DIR}/tacklet-update.py" "${APP_DIR}/"
chmod +x "${APP_DIR}/tacklet.py" "${APP_DIR}/tacklet-update.py"

ln -sfn "${APP_DIR}/tacklet.py" "${BIN_DIR}/tacklet"
ln -sfn "${APP_DIR}/tacklet-update.py" "${BIN_DIR}/tacklet-update"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Name=Tacklet
Name[ru]=Tacklet — заметки
Comment=Fast, private sticky notes
Comment[ru]=Быстрые приватные заметки
Exec=${BIN_DIR}/tacklet --x11
Icon=accessories-text-editor
Terminal=false
Type=Application
Categories=Utility;TextEditor;
StartupNotify=false
EOF

# Versions before 0.2.0 placed program code next to notes. Remove only the
# known code paths, never the directory or JSON data owned by the user.
if [[ -f "${OLD_APP_DIR}/tacklet.py" ]] && grep -q 'Tacklet' "${OLD_APP_DIR}/tacklet.py"; then
    rm -rf "${OLD_APP_DIR}/sticky"
    rm -f "${OLD_APP_DIR}/tacklet.py"
fi

update-desktop-database "${APPLICATIONS_DIR}" >/dev/null 2>&1 || true

echo "Tacklet installed for the current user."
echo "  Start: tacklet"
echo "  Update: tacklet-update (after installing the .deb package)"
echo "  Notes preserved at: ${XDG_DATA_HOME:-${HOME}/.local/share}/tacklet/notes.json"
