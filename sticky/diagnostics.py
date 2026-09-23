"""Small, reusable runtime preflight checks for Tacklet."""

from __future__ import annotations

from dataclasses import dataclass
import shutil


INSTALL_COMMAND = 'sudo apt install python3-gi gir1.2-gtk-4.0 xdotool'


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    required: bool
    detail: str


def run_checks(require_xdotool: bool = True) -> list[Check]:
    """Return runtime checks without starting a Gtk application."""
    checks: list[Check] = []
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gtk
    except (ImportError, ValueError) as exc:
        checks.append(Check(
            'GTK 4 / PyGObject', False, True,
            f'{exc}. Install it with: {INSTALL_COMMAND}',
        ))
    else:
        checks.append(Check('GTK 4 / PyGObject', True, True, 'available'))
        has_alert_dialog = hasattr(Gtk, 'AlertDialog')
        checks.append(Check(
            'GTK 4.10+', has_alert_dialog, True,
            'available' if has_alert_dialog else
            'Gtk.AlertDialog requires GTK 4.10 or newer. Upgrade gir1.2-gtk-4.0.',
        ))

    has_xdotool = shutil.which('xdotool') is not None
    checks.append(Check(
        'xdotool', has_xdotool, require_xdotool,
        'available' if has_xdotool else
        ('required for XWayland position restoration. Install it with: ' + INSTALL_COMMAND),
    ))
    checks.append(Check(
        'Ubuntu AppIndicators extension', True, False,
        'optional: enable it in GNOME Extensions to display the tray icon.',
    ))
    return checks


def has_blocking_failure(checks: list[Check]) -> bool:
    return any(check.required and not check.ok for check in checks)


def format_report(checks: list[Check]) -> str:
    lines = ['Tacklet diagnostics:']
    for check in checks:
        state = 'OK' if check.ok else ('ERROR' if check.required else 'INFO')
        lines.append(f'[{state}] {check.name}: {check.detail}')
    return '\n'.join(lines)
