# Tacklet

> Fast, private sticky notes for Ubuntu GNOME.

Tacklet is a small GTK 4 application for keeping short notes visible while you
work. It has no account, cloud service, or telemetry: notes stay in a local
JSON file on your computer.

**Status:** early alpha. Feedback and small, focused pull requests are welcome.

## Features

- Multiple resizable notes with a background colour and opacity.
- Per-note and selected-text font sizes, restored after restart.
- Tray menu: show or hide notes, create a note, open settings, or quit.
- `Alt+S` global show/hide shortcut on Ubuntu GNOME Wayland.
- `Alt+V` creates a new note and pastes plain text from the system clipboard.
- Safe local persistence: atomic writes, private file permissions, and
  migration from the former `sticky-notes` data directory.
- Native GTK text selection and context menu for copy/paste.

## Requirements

- Ubuntu GNOME on Wayland.
- Python 3.10+, `python3-gi`, and `gir1.2-gtk-4.0`.
- The enabled **Ubuntu AppIndicators** extension for the tray icon.
- `xdotool` only for the optional `--x11` mode.

## Run from source

```bash
sudo apt install python3-gi gir1.2-gtk-4.0
python3 tacklet.py
```

To run through XWayland and restore exact window coordinates:

```bash
sudo apt install xdotool
python3 tacklet.py --x11
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
window positions or force an always-on-top state. Tacklet saves text, size,
appearance, text formatting, and visibility in native Wayland mode; `--x11`
provides exact position restoration. A fully native solution for those two
capabilities requires a separate GNOME Shell extension.

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
