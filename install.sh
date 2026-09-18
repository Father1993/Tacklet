#!/usr/bin/env bash
# Установка Tacklet в ~/.local (без sudo).
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/tacklet"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"

mkdir -p "$DEST" "$BIN" "$APPS"

cp -r "$SRC/sticky" "$SRC/tacklet.py" "$DEST/"
chmod +x "$DEST/tacklet.py"

ln -sf "$DEST/tacklet.py" "$BIN/tacklet"

cat > "$APPS/io.github.father1993.Tacklet.desktop" <<EOF
[Desktop Entry]
Name=Tacklet
Name[ru]=Tacklet — заметки
Comment=Lightweight desktop sticky notes
Comment[ru]=Лёгкие заметки для рабочего стола
Exec=$DEST/tacklet.py
Icon=accessories-text-editor
Terminal=false
Type=Application
Categories=Utility;TextEditor;
StartupNotify=false
EOF

update-desktop-database "$APPS" >/dev/null 2>&1 || true

echo "Tacklet установлен."
echo "  Запуск из меню приложений или командой: tacklet"
echo "  Позиции окон сохраняются: tacklet --x11"
echo "  Глобальная клавиша Alt+S (показ/скрытие всех заметок)"
echo "  Данные: ~/.local/share/tacklet/notes.json"
