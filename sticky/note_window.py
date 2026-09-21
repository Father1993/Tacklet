"""Окно-стикер с заметкой (GTK4)."""

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gdk, Gtk

from . import platform
from .storage import MIN_H, MIN_W
from .util import clamp, contrast_color, hex_from_rgba, rgba_from_hex


class NoteWindow(Gtk.ApplicationWindow):
    def __init__(self, app, note):
        super().__init__(application=app)

        self.app = app          # StickyApp
        self.note = note        # NoteData — общий объект состояния заметки

        self._family = None     # семейство системного шрифта (кэш)
        self._tags = {}         # кэш текстовых тегов: размер -> Gtk.TextTag

        self.set_title('Заметка')
        self.set_default_size(max(note.w, MIN_W), max(note.h, MIN_H))
        self.set_size_request(MIN_W, MIN_H)
        self.set_opacity(clamp(note.opacity, 0.05, 1.0))
        self.connect('close-request', self._on_close_request)

        self._build_header()
        self._build_body()

        self._css = Gtk.CssProvider()
        self._render_css()
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ---- интерфейс -------------------------------------------------------

    def _build_header(self):
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_title_buttons(False)

        headerbar.pack_start(self._mk_icon_button(
            'list-add-symbolic', 'Новая заметка',
            lambda *_: self.app.new_note()))

        self._btn_minus = self._mk_icon_button(
            'zoom-out-symbolic', 'Уменьшить шрифт\n(выделенный текст или вся заметка)',
            lambda *_: self.change_font(-1))
        self._btn_plus = self._mk_icon_button(
            'zoom-in-symbolic', 'Увеличить шрифт\n(выделенный текст или вся заметка)',
            lambda *_: self.change_font(1))
        self._btn_reset = self._mk_icon_button(
            'edit-clear-all-symbolic', 'Сбросить форматирование выделения',
            lambda *_: self.reset_format())
        headerbar.pack_start(self._btn_minus)
        headerbar.pack_start(self._btn_plus)
        headerbar.pack_start(self._btn_reset)

        self._color_btn = Gtk.ColorButton()
        self._color_btn.set_rgba(rgba_from_hex(self.note.color))
        self._color_btn.set_tooltip_text('Цвет стикера')
        self._color_btn.connect('color-set', self._on_color_set)
        headerbar.pack_end(self._color_btn)

        self._btn_toggle = self._mk_icon_button('view-restore-symbolic',
                                                'Показать/скрыть все заметки (Alt+S)',
                                                lambda *_: self.app.toggle_all())
        headerbar.pack_end(self._btn_toggle)

        self._btn_settings = self._mk_icon_button('preferences-system-symbolic',
                                                  'Настройки', self._open_settings)
        headerbar.pack_end(self._btn_settings)

        self._btn_delete = self._mk_icon_button('edit-delete-symbolic',
                                                'Удалить заметку',
                                                lambda *_: self.app.delete_note(self))
        headerbar.pack_end(self._btn_delete)

        self.set_titlebar(headerbar)

    @staticmethod
    def _mk_icon_button(icon, tip, handler):
        btn = Gtk.Button()
        btn.set_icon_name(icon)
        btn.set_tooltip_text(tip)
        btn.connect('clicked', handler)
        return btn

    def _build_body(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        view = Gtk.TextView()
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_hexpand(True)
        view.set_vexpand(True)
        for side in (view.set_top_margin, view.set_bottom_margin,
                     view.set_left_margin, view.set_right_margin):
            side(10)
        view.add_css_class('note-text')

        scrolled.set_child(view)
        self.set_child(scrolled)

        self._view = view
        self._buffer = view.get_buffer()
        self._buffer.set_text(self.note.text)
        self._restore_formats()
        self._buffer.connect('changed', lambda *_: self.app.schedule_save())

        # Запасной путь для Alt+S, если глобальной клавиши нет (пока окно в фокусе).
        key = Gtk.EventControllerKey()
        key.connect('key-pressed', self._on_key_pressed)
        self.add_controller(key)

    def _open_settings(self, *_):
        self.app.open_settings()

    def focus_editor(self):
        """Передаёт фокус новой заметке после отображения её поверхности."""
        self._view.grab_focus()
        return GLib.SOURCE_REMOVE

    # ---- стили -----------------------------------------------------------

    def _render_css(self):
        size = clamp(self.note.font_size, 8, 48)
        family = self._font_family()
        text_color = contrast_color(self.note.color)
        css = (
            '.note-text {\n'
            f'  border-radius: 12px;\n'
            f'  font-size: {size}pt;\n'
            f'  font-family: {family};\n'
            '}\n'
            '.note-text, .note-text text {\n'
            f'  background-color: {self.note.color};\n'
            '}\n'
            '.note-text text {\n'
            f'  color: {text_color};\n'
            '}\n'
        )
        self._css.load_from_string(css)

    def _font_family(self):
        if self._family is None:
            desc = self.get_pango_context().get_font_description()
            self._family = (desc.get_family() if desc else None) or 'Sans'
        return self._family

    # ---- шрифты ----------------------------------------------------------

    def change_font(self, delta):
        """Меняет размер шрифта выделенного текста, а без выделения — всей заметки."""
        bounds = self._buffer.get_selection_bounds()
        if bounds:
            start, end = bounds
            size = clamp(self.note.font_size + delta, 6, 72)
            self._apply_font_tag(start, end, size)
        else:
            self.change_font_default(delta)
        self.app.schedule_save()

    def change_font_default(self, delta):
        self.note.font_size = clamp(self.note.font_size + delta, 8, 48)
        self._render_css()
        self.app.schedule_save()

    def reset_format(self):
        bounds = self._buffer.get_selection_bounds()
        if bounds:
            self._buffer.remove_all_tags(bounds[0], bounds[1])
        else:
            self.note.font_size = self.app.config.font_size
            self._render_css()
        self.app.schedule_save()

    def _tag_for(self, size):
        tag = self._tags.get(size)
        if tag is None:
            # CSS задаёт семейство, а тег хранит только сериализуемый размер.
            tag = self._buffer.create_tag(None, size_points=float(size))
            self._tags[size] = tag
        return tag

    def _apply_font_tag(self, start, end, size):
        self._buffer.apply_tag(self._tag_for(size), start, end)

    # ---- прочее ----------------------------------------------------------

    def _on_color_set(self, color_button):
        self.note.color = hex_from_rgba(color_button.get_rgba())
        self._render_css()
        self.app.schedule_save()

    def _on_close_request(self, *_):
        """Закрытие стикера прячет его, а не удаляет."""
        self.finish_hide()
        return True

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_s and (state & Gdk.ModifierType.ALT_MASK):
            self.app.toggle_all()
            return True
        return False

    # ---- показ/скрытие и геометрия --------------------------------------

    def show_note(self):
        self.note.hidden = False
        platform.raise_above(self)
        if platform.supports_geometry():
            # The X11 surface exists only after GTK has mapped the window.
            # Restoring on the next idle cycle was sometimes too early, which
            # let Mutter choose a centred position instead.
            GLib.timeout_add(100, self._restore_position, 0)

    def hide_note(self):
        self.update_geometry_from_screen()
        self.note.hidden = True
        self.hide()

    def finish_hide(self):
        self.update_geometry_from_screen()
        self.note.hidden = True
        self.hide()
        self.app.schedule_save()

    def _restore_position(self, attempt):
        if self.note.hidden:
            return False
        if platform.move(self, self.note.x, self.note.y):
            return False
        # XWayland can map the client surface slightly after GTK reports it
        # visible. Retry briefly instead of accepting the compositor default.
        if attempt < 3:
            GLib.timeout_add(100, self._restore_position, attempt + 1)
        return False

    def refresh_opacity(self):
        self.set_opacity(clamp(self.note.opacity, 0.05, 1.0))

    def update_geometry_from_screen(self):
        """Фиксирует реальную геометрию окна в данных заметки."""
        if not self.get_visible():
            return
        if platform.supports_geometry():
            geometry = platform.geometry(self)
            if geometry:
                # xdotool reports the outer X11 frame. Its width and height
                # include GTK's headerbar, whereas Gtk.Window stores its
                # content size. Keep the two coordinate systems separate so
                # a note cannot grow after each hide/show cycle.
                self.note.x, self.note.y = geometry[:2]
                self.note.w = self.get_size(Gtk.Orientation.HORIZONTAL)
                self.note.h = self.get_size(Gtk.Orientation.VERTICAL)
                return
        self.note.w = self.get_size(Gtk.Orientation.HORIZONTAL)
        self.note.h = self.get_size(Gtk.Orientation.VERTICAL)

    def sync_to_note(self):
        """Переносит текст и локальное форматирование в модель перед JSON."""
        start = self._buffer.get_start_iter()
        end = self._buffer.get_end_iter()
        self.note.text = self._buffer.get_text(start, end, True)
        self.note.formats = self._collect_formats()

    def _restore_formats(self):
        for item in self.note.formats:
            start = self._buffer.get_iter_at_offset(item['start'])
            end = self._buffer.get_iter_at_offset(item['end'])
            self._buffer.apply_tag(self._tag_for(item['font_size']), start, end)

    def _collect_formats(self):
        """Собирает интервалы локального размера шрифта из Gtk.TextBuffer."""
        formats = []
        cursor = self._buffer.get_start_iter()
        end = self._buffer.get_end_iter()
        while cursor.compare(end) < 0:
            next_cursor = cursor.copy()
            if not next_cursor.forward_to_tag_toggle(None):
                next_cursor = end.copy()
            start_offset = cursor.get_offset()
            end_offset = next_cursor.get_offset()
            sizes = [size for size, tag in self._tags.items() if tag in cursor.get_tags()]
            if sizes and end_offset > start_offset:
                formats.append({
                    'start': start_offset,
                    'end': end_offset,
                    'font_size': max(sizes),
                })
            cursor = next_cursor
        return formats
