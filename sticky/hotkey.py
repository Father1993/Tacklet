"""Глобальная клавиша для Ubuntu GNOME.

Wayland намеренно не позволяет приложениям читать клавиатуру вне своих окон.
Для GNOME проверенный путь -- зарегистрировать пользовательское сочетание
GNOME, которое запускает команду приложения. Gtk.Application передаёт эту
команду уже работающему экземпляру по D-Bus.
"""

from __future__ import annotations

import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio


SHORTCUT_PATH = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/tacklet/'
NEW_NOTE_SHORTCUT_PATH = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/tacklet-new-note/'
LEGACY_SHORTCUT_PATH = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/sticky-notes/'
MEDIA_KEYS_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys'
CUSTOM_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys.custom-keybinding'


class GnomeShortcut:
    """Создаёт и удаляет только собственную запись GNOME custom keybindings."""

    def __init__(self, toggle_command: str, new_note_command: str):
        self.toggle_command = toggle_command
        self.new_note_command = new_note_command

    @staticmethod
    def is_supported() -> bool:
        return Gio.SettingsSchemaSource.get_default().lookup(MEDIA_KEYS_SCHEMA, True) is not None

    def enable(self) -> bool:
        if not self.is_supported():
            return False
        media = Gio.Settings.new(MEDIA_KEYS_SCHEMA)
        paths = list(media.get_strv('custom-keybindings'))
        # Перенос с доopen-source имени: не оставляем второй Alt+S, который
        # конфликтует с новой привязкой Tacklet.
        if LEGACY_SHORTCUT_PATH in paths:
            paths.remove(LEGACY_SHORTCUT_PATH)
        for path in (SHORTCUT_PATH, NEW_NOTE_SHORTCUT_PATH):
            if path not in paths:
                paths.append(path)
            media.set_strv('custom-keybindings', paths)
        self._set_binding(SHORTCUT_PATH, 'Tacklet: показать / скрыть',
                          self.toggle_command, '<Alt>s')
        self._set_binding(NEW_NOTE_SHORTCUT_PATH, 'Tacklet: новая заметка из буфера',
                          self.new_note_command, '<Alt>v')
        return True

    def disable(self) -> bool:
        if not self.is_supported():
            return False
        media = Gio.Settings.new(MEDIA_KEYS_SCHEMA)
        paths = [path for path in media.get_strv('custom-keybindings')
                 if path not in (SHORTCUT_PATH, NEW_NOTE_SHORTCUT_PATH)]
        media.set_strv('custom-keybindings', paths)
        return True

    @staticmethod
    def _set_binding(path, name, command, binding_text):
        binding = Gio.Settings.new_with_path(CUSTOM_SCHEMA, path)
        binding.set_string('name', name)
        binding.set_string('command', command)
        binding.set_string('binding', binding_text)


def toggle_command(executable: str) -> str:
    """Команда GNOME для вызова действия уже работающего приложения.

    ``gapplication action`` отправляет D-Bus ActivateAction и сразу
    завершается. Это надёжнее запуска второго GTK-процесса с ``--toggle``.
    Аргумент оставлен в сигнатуре для совместимости с точкой входа.
    """
    del executable
    return 'gapplication action io.github.father1993.Tacklet toggle-all'


def new_note_from_clipboard_command() -> str:
    """Команда GNOME для создания заметки с текстом из буфера обмена."""
    return 'gapplication action io.github.father1993.Tacklet new-from-clipboard'
