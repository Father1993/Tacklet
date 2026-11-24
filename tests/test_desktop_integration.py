"""Exercise installed GTK widgets and the tray wire protocol on a private session."""

import os
import select
import subprocess
import sys
import unittest

from sticky.app import StickyApp
from sticky.tray import DBUSMENU_IFACE, MENU_PATH, SNI_PATH, WATCHER_NAME
from gi.repository import Gdk, Gio, GLib


def run_watcher():
    """Own the watcher name on another process so tray registration can call it."""
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    interface = Gio.DBusNodeInfo.new_for_xml(
        '<node><interface name="org.kde.StatusNotifierWatcher">'
        '<method name="RegisterStatusNotifierItem"><arg type="s" direction="in"/></method>'
        '<method name="UnregisterStatusNotifierItem"><arg type="s" direction="in"/></method>'
        '</interface></node>').interfaces[0]
    bus.register_object('/StatusNotifierWatcher', interface,
                        lambda *args: args[-1].return_value(None))
    bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                  'org.freedesktop.DBus', 'RequestName',
                  GLib.Variant('(su)', (WATCHER_NAME, 4)), None,
                  Gio.DBusCallFlags.NONE, 3000, None)
    print('ready', flush=True)
    GLib.MainLoop().run()


def wait_for_result(begin, finish):
    loop = GLib.MainLoop()
    replies = []

    def complete(source, result, *_):
        replies.append((source, result))
        loop.quit()

    timeout = GLib.timeout_source_new(4000)
    timeout.set_callback(lambda *_: loop.quit())
    timeout.attach()
    try:
        begin(complete)
        loop.run()
    finally:
        timeout.destroy()
    if not replies:
        raise AssertionError('The GTK/D-Bus operation timed out')
    return finish(*replies[0])


@unittest.skipUnless(os.environ.get('TACKLET_DESKTOP_TEST') == '1',
                     'requires an isolated display, session bus, and data directory')
class DesktopIntegrationTests(unittest.TestCase):
    def test_widgets_and_tray_menu(self):
        with subprocess.Popen([sys.executable, __file__, '--watcher'],
                              stdout=subprocess.PIPE, text=True) as watcher:
            try:
                self.assertTrue(select.select([watcher.stdout], [], [], 5)[0])
                self.assertEqual(watcher.stdout.readline().strip(), 'ready')
                self._exercise_app()
            finally:
                watcher.terminate()

    def _exercise_app(self):
        app = StickyApp('/usr/bin/tacklet')
        self.assertTrue(app.register())
        try:
            app.activate()
            window, = app._note_windows()
            self.assertTrue(app._tray.registered)
            self._exercise_widgets(window)
            self._exercise_tray(app, window)
        finally:
            app._cancel_save()
            app._stop_tray()
            for window in app.get_windows():
                window.destroy()
            app.release()

    def _exercise_widgets(self, window):
        blocks = window._blocks
        blocks.add_code()
        code = blocks.get_first_child()
        snippet = 'printf "пример"\n  indented\n\n'
        code._buffer.set_text(snippet)
        code._copy_button.emit('clicked')
        clipboard = Gdk.Display.get_default().get_clipboard()
        pasted = wait_for_result(lambda done: clipboard.read_text_async(None, done),
                                 lambda clipboard, result: clipboard.read_text_finish(result))
        self.assertEqual(pasted, snippet)
        self.assertEqual(code._copy_button.get_label(), 'Copied')
        blocks.add_checklist()
        self.assertIs(blocks.get_first_child(), code)
        checklist = code.get_next_sibling()
        checklist._add_item()
        first, last = checklist.block['items']
        first_row, _ = checklist._item_widgets[first['id']]
        last_row, last_entry = checklist._item_widgets[last['id']]
        last_entry.set_text('Deploy')
        last_row.get_first_child().set_active(True)
        handled = checklist._on_item_key(None, Gdk.KEY_Return, 0, 0, first)
        self.assertTrue(handled)
        inserted = checklist.block['items'][1]
        row, entry = checklist._item_widgets[inserted['id']]
        self.assertIs(first_row.get_next_sibling(), row)
        self.assertIs(row.get_next_sibling(), last_row)
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)
        self.assertTrue(window.get_focus().is_ancestor(entry))
        checklist._delete_item(inserted)
        self.assertIs(last_entry, checklist._item_widgets[last['id']][1])
        self.assertEqual(last, {'id': last['id'], 'text': 'Deploy', 'checked': True})
        blocks.remove_block(checklist)
        self.assertEqual(window.note.blocks, [code.block])
        self.assertIs(blocks.get_first_child(), code)

    def _exercise_tray(self, app, window):
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        destination = app._tray._service_name()

        def call(path, interface, method, args):
            return wait_for_result(
                lambda done: bus.call(destination, path, interface, method, args,
                                      None, Gio.DBusCallFlags.NONE, 3000, None, done),
                lambda connection, result: connection.call_finish(result)).unpack()

        props, = call(SNI_PATH, 'org.freedesktop.DBus.Properties', 'GetAll',
                      GLib.Variant('(s)', ('org.kde.StatusNotifierItem',)))
        self.assertEqual(props['Menu'], MENU_PATH)
        _, (_, _, children) = call(MENU_PATH, DBUSMENU_IFACE, 'GetLayout',
                                   GLib.Variant('(iias)', (0, -1, [])))
        self.assertEqual(children[0][1]['label'], 'Показать / скрыть все')
        app.open_settings()
        for hidden in (True, False):
            call(MENU_PATH, DBUSMENU_IFACE, 'Event',
                 GLib.Variant('(isvu)', (1, 'clicked', GLib.Variant('i', 0), 0)))
            self.assertEqual(window.note.hidden, hidden)
            self.assertTrue(app._settings.get_visible())
        call(SNI_PATH, 'org.kde.StatusNotifierItem', 'Activate',
             GLib.Variant('(ii)', (0, 0)))
        self.assertTrue(window.note.hidden)
        app.lookup_action('new-from-clipboard').activate(None)
        self._wait_for_clipboard_note(app)

    def _wait_for_clipboard_note(self, app):
        def wait(done):
            def check():
                if len(app.notes) < 2:
                    return GLib.SOURCE_CONTINUE
                done(app, app.notes[-1])
                return GLib.SOURCE_REMOVE
            poll.set_callback(lambda *_: check())
            poll.attach()

        poll = GLib.timeout_source_new(10)
        try:
            note = wait_for_result(wait, lambda _app, note: note)
        finally:
            poll.destroy()
        self.assertEqual(note.text, 'printf "пример"\n  indented\n\n')


if __name__ == '__main__' and sys.argv[1:] == ['--watcher']:
    run_watcher()
