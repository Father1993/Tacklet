# Tacklet

> Fast, private sticky notes for Ubuntu GNOME.

Tacklet is a small GTK 4 application for keeping short notes visible while you
work. It has no account, cloud service, or telemetry: notes stay in a local
JSON file on your computer.

**Status:** early alpha. Feedback and small, focused pull requests are welcome.

## Features

- Multiple resizable notes with names, a compact header, background colour and opacity.
- Per-note and selected-text font sizes, restored after restart.
- Tray menu: show or hide notes, create a note, open settings, or quit.
- `Alt+S` global show/hide shortcut on Ubuntu GNOME Wayland.
- `Alt+V` creates a new note and pastes plain text from the system clipboard.
- Safe local persistence: atomic writes, private file permissions, and
  migration from the former `sticky-notes` data directory.
- Native GTK text selection and context menu for copy/paste.
- Import and export portable JSON backups from the tray menu or Settings.

## Requirements

- Ubuntu GNOME on Wayland.
- Python 3.10+, `python3-gi`, and `gir1.2-gtk-4.0`.
- The enabled **Ubuntu AppIndicators** extension for the tray icon.
- `xdotool` for restoring saved window positions (the default XWayland mode).

## Run from source

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 xdotool
python3 tacklet.py
```

Tacklet uses XWayland by default, while your GNOME desktop remains a Wayland
session. This is intentional: it restores every note to its saved screen
position after `Alt+S` and after restarting the application.

To explicitly use the native Wayland backend instead:

```bash
python3 tacklet.py --wayland
```

## Install locally

```bash
./install.sh
tacklet
```

The installer is user-local and does not need `sudo`. Notes are stored in
`~/.local/share/tacklet/notes.json`. On first run, data from
`~/.local/share/sticky-notes/notes.json` is imported automatically.

## Wayland limitation

GNOME Wayland intentionally does not let ordinary applications set absolute
window positions or force an always-on-top state. For dependable sticky-note
placement, Tacklet defaults to XWayland (`--x11`). This does not switch the
desktop away from Wayland; it only gives Tacklet an X11 surface. Native
Wayland mode (`--wayland`) saves text, size, appearance, text formatting, and
visibility, but its compositor chooses the position. A fully native solution
for exact placement requires a GNOME Shell extension.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q sticky tacklet.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution expectations and
[SECURITY.md](SECURITY.md) for security reporting. Changes are listed in
[CHANGELOG.md](CHANGELOG.md).

## License

Tacklet is released under the [MIT License](LICENSE).
