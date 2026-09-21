# Changelog

All notable changes to Tacklet are documented in this file.

## Unreleased

## 0.1.3 — 2026-09-21

### Added

- Editable note names and portable JSON import/export from the tray and
  Settings. Imports add notes without overwriting the current collection.

### Changed

- Replace the crowded note toolbar with a compact header: add note, editable
  name, Settings, and delete. Colour and default font controls remain in
  Settings.

## 0.1.2 — 2026-09-21

### Fixed

- Save each note's real XWayland geometry immediately before `Alt+S` hides it
  and restore after the surface is mapped, preventing a centred reappearance.
- Start through XWayland by default so note positions restore reliably after
  `Alt+S` and application restarts; add `--wayland` to opt into native Wayland.
- Export the Canonical DBusMenu interface required by Ubuntu AppIndicators, so
  a right-click on the tray icon opens Tacklet's menu again.

### Added

- `Alt+V` global shortcut to create a note from clipboard text.

## 0.1.1 — 2026-09-18

### Fixed

- GitHub Actions now runs with Ubuntu's system Python, which can import the
  GTK introspection packages installed by the workflow.
- Storage tests no longer import GTK as an incidental dependency.

## 0.1.0 — 2026-09-18

### Added

- GTK 4 sticky notes with colour, opacity, per-note font size, and local text
  size formatting.
- Tray controls and a GNOME `Alt+S` show/hide shortcut.
- JSON persistence with atomic writes and legacy-data migration.
- MIT license, contribution guide, and automated tests.

### Known limitations

- Native GNOME Wayland does not provide an API for an application to restore
  absolute window coordinates or force always-on-top. Use `--x11` when exact
  positioning is required.
