"""Окно настроек: прозрачность, размер шрифта, цвет стикеров, глобальная Alt+S."""

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from .util import hex_from_rgba, rgba_from_hex


class SettingsDialog(Gtk.Window):
    def __init__(self, app):
        # Привязка к Gtk.Application делает окно частью одного жизненного
        # цикла с заметками, а не отдельным бесхозным Gtk.Window.
        super().__init__(application=app, title='Настройки заметок')

        self.app = app
        self.set_modal(True)
        self.set_hide_on_close(True)
        self.set_default_size(400, -1)
        # После super(..., application=app) этот диалог уже есть в списке
        # окон приложения. Нельзя назначить окно transient-родителем самому
        # себе: GTK отклоняет это и модальность становится непредсказуемой.
        parent = next((window for window in app.get_windows()
                       if window is not self and hasattr(window, 'note')), None)
        if parent is not None:
            self.set_transient_for(parent)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        self.set_child(box)

        header = Gtk.Label()
        header.set_markup('<span size="x-large"><b>Настройки заметок</b></span>')
        box.append(header)

        self._build_opacity(box, app.config.opacity)
        self._build_font(box, app.config.font_size)
        self._build_color(box, app.config.color)
        self._build_hotkey(box, app.config.hotkey_enabled)
        self._build_trash(box)
        self._build_import_export(box)
        self._build_actions(box)

    # ---- секции ----------------------------------------------------------

    def _build_opacity(self, box, value):
        label = Gtk.Label(label='Прозрачность стикеров')
        label.set_xalign(0)
        box.append(label)

        adjustment = Gtk.Adjustment(lower=15, upper=100, step_increment=1,
                                    page_increment=5, value=value * 100)
        scale = Gtk.Scale(adjustment=adjustment)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        adjustment.connect('value-changed', self._on_opacity_changed)
        box.append(scale)

    def _on_opacity_changed(self, adjustment):
        self.app.apply_opacity(adjustment.get_value() / 100.0)

    def _build_font(self, box, value):
        label = Gtk.Label(label='Размер шрифта (по умолчанию)')
        label.set_xalign(0)
        box.append(label)

        spin = Gtk.SpinButton.new_with_range(8, 48, 1)
        spin.set_value(value)
        spin.set_numeric(True)
        spin.connect('value-changed', self._on_font_changed)
        box.append(spin)

    def _on_font_changed(self, spin):
        self.app.apply_font_size(int(spin.get_value()))

    def _build_color(self, box, color):
        label = Gtk.Label(label='Цвет стикеров (по умолчанию)')
        label.set_xalign(0)
        box.append(label)

        button = Gtk.ColorButton()
        button.set_use_alpha(False)
        button.set_rgba(rgba_from_hex(color))
        button.connect('color-set', self._on_color_set)
        box.append(button)

    def _on_color_set(self, button):
        self.app.apply_color(hex_from_rgba(button.get_rgba()))

    def _build_hotkey(self, box, enabled):
        row = Gtk.Box(spacing=8)
        label = Gtk.Label(label='Глобальная клавиша Alt+S\n(показ/скрытие всех заметок)')
        label.set_xalign(0)
        label.set_hexpand(True)
        row.append(label)

        switch = Gtk.Switch()
        switch.set_active(bool(enabled))
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect('state-set', self._on_hotkey_toggled)
        row.append(switch)
        box.append(row)

        hint = Gtk.Label()
        hint.set_markup(
            'На Ubuntu GNOME сочетание регистрируется в системных настройках '
            'клавиатуры и работает без фокуса на заметке. Отключение удаляет '
            'только привязку, созданную этим приложением.')
        hint.set_wrap(True)
        hint.set_xalign(0)
        hint.set_opacity(0.7)
        box.append(hint)

    def _on_hotkey_toggled(self, switch, state):
        # Не показываем включённое состояние, если GNOME не принял настройку.
        return not self.app.apply_hotkey_enabled(state)

    def _build_import_export(self, box):
        label = Gtk.Label(label='Резервная копия заметок')
        label.set_xalign(0)
        box.append(label)

        row = Gtk.Box(spacing=8)
        import_button = Gtk.Button(label='Импортировать…')
        import_button.connect('clicked', lambda *_: self.app.import_notes(self))
        row.append(import_button)
        export_button = Gtk.Button(label='Экспортировать…')
        export_button.connect('clicked', lambda *_: self.app.export_notes(self))
        row.append(export_button)
        box.append(row)

    def _build_trash(self, box):
        label = Gtk.Label(label='Корзина')
        label.set_xalign(0)
        box.append(label)

        row = Gtk.Box(spacing=8)
        hint = Gtk.Label(label='Удалённые заметки можно восстановить в течение 30 дней.')
        hint.set_xalign(0)
        hint.set_hexpand(True)
        hint.set_wrap(True)
        row.append(hint)
        trash = Gtk.Button(label='Открыть корзину…')
        trash.connect('clicked', lambda *_: self.app.open_trash(self))
        row.append(trash)
        box.append(row)

    def _build_actions(self, box):
        row = Gtk.Box(spacing=8)

        save = Gtk.Button(label='Закрыть')
        save.add_css_class('suggested-action')
        save.connect('clicked', lambda *_: self.close())
        self._close_button = save
        row.append(save)

        row.append(Gtk.Box(hexpand=True))

        quit_btn = Gtk.Button(label='Завершить программу')
        quit_btn.add_css_class('destructive-action')
        quit_btn.connect('clicked', lambda *_: self.app.quit())
        row.append(quit_btn)
        box.append(row)
