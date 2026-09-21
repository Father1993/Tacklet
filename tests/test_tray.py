"""Regression checks for the Ubuntu AppIndicators DBusMenu contract."""

import unittest

from gi.repository import Gio, GLib

from sticky import tray


class TrayContractTests(unittest.TestCase):
    def test_exports_the_canonical_dbusmenu_interface(self):
        node = Gio.DBusNodeInfo.new_for_xml(tray.MENU_XML)
        interface = node.interfaces[0]
        self.assertEqual(interface.name, 'com.canonical.dbusmenu')
        self.assertEqual(
            {method.name for method in interface.methods},
            {'GetLayout', 'GetProperty', 'Event', 'GetGroupProperties',
             'EventGroup', 'AboutToShow', 'AboutToShowGroup'},
        )

    def test_menu_layout_contains_the_quit_item(self):
        notifier = tray.StatusNotifierItem.__new__(tray.StatusNotifierItem)
        notifier.set_menu([
            (1, 'Показать / скрыть все', None),
            (2, '---', None),
            (3, 'Завершить программу', None),
        ])
        revision, root = notifier._layout().unpack()
        self.assertEqual(revision, 1)
        self.assertEqual(root[0], 0)
        children = root[2]
        self.assertEqual([child[0] for child in children], [1, 2, 3])
        self.assertEqual(children[2][1]['label'], 'Завершить программу')

    def test_clicked_menu_item_invokes_its_callback(self):
        called = []
        notifier = tray.StatusNotifierItem.__new__(tray.StatusNotifierItem)
        notifier.set_menu([(6, 'Завершить программу', lambda: called.append(True))])

        class Invocation:
            def return_value(self, value):
                self.value = value

        invocation = Invocation()
        notifier._on_menu_call(
            None, None, tray.MENU_PATH, tray.DBUSMENU_IFACE, 'Event',
            GLib.Variant('(isvu)', (6, 'clicked', GLib.Variant('s', ''), 0)),
            invocation,
        )
        self.assertEqual(called, [True])
        self.assertIsNone(invocation.value)


if __name__ == '__main__':
    unittest.main()
