# Changelog

All notable changes to Tacklet are documented in this file.

## Unreleased

- Start through XWayland by default so note positions restore reliably after
  `Alt+S` and application restarts; add `--wayland` to opt into native Wayland.

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
