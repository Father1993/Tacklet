"""Индикатор в трее через StatusNotifierItem (org.kde.StatusNotifierItem + org.kde.dbusmenu).

GNOME без расширения «AppIndicator» не показывает трей. Если watcher
(org.kde.StatusNotifierWatcher) не активен, индикатор просто не
регистрируется — приложение работает без трея.
"""

import os

from gi.repository import Gio, GLib

WATCHER_NAME = 'org.kde.StatusNotifierWatcher'
SNI_PATH = '/StatusNotifierItem'
MENU_PATH = '/StatusNotifierItem/Menu'
ICON_NAME = 'accessories-text-editor'
SNI_IFACE = 'org.kde.StatusNotifierItem'
DBUSMENU_IFACE = 'org.kde.dbusmenu'
PROPS_IFACE = 'org.freedesktop.DBus.Properties'

SNI_XML = (
    '<node>'
    '<interface name="org.kde.StatusNotifierItem">'
    '<method name="Activate"><arg type="i" direction="in" name="x"/>'
    '<arg type="i" direction="in" name="y"/></method>'
    '<method name="SecondaryActivate"><arg type="i" direction="in" name="x"/>'
    '<arg type="i" direction="in" name="y"/></method>'
    '<method name="ContextMenu"><arg type="i" direction="in" name="x"/>'
    '<arg type="i" direction="in" name="y"/></method>'
    '</interface>'
    '</node>'
)

MENU_XML = (
    '<node>'
    '<interface name="org.kde.dbusmenu">'
    '<method name="GetLayout">'
    '<arg type="i" direction="in" name="parentId"/>'
    '<arg type="i" direction="in" name="recursionDepth"/>'
    '<arg type="as" direction="in" name="propertyNames"/>'
    '<arg type="u" direction="out" name="revision"/>'
    '<arg type="(ia{sv}av)" direction="out" name="layout"/>'
    '</method>'
    '<method name="GetProperty"><arg type="i" direction="in" name="id"/>'
    '<arg type="s" direction="in" name="name"/>'
    '<arg type="v" direction="out" name="value"/></method>'
    '<method name="Event"><arg type="i" direction="in" name="id"/>'
    '<arg type="s" direction="in" name="eventId"/>'
    '<arg type="v" direction="in" name="data"/>'
    '<arg type="u" direction="in" name="timestamp"/></method>'
    '<signal name="LayoutUpdated"><arg type="u" name="revision"/>'
    '<arg type="i" name="parent"/></signal>'
    '</interface>'
    '</node>'
)

PROPS_XML = (
    '<node>'
    '<interface name="org.freedesktop.DBus.Properties">'
    '<method name="Get"><arg type="s" direction="in" name="interface_name"/>'
    '<arg type="s" direction="in" name="property_name"/>'
    '<arg type="v" direction="out" name="value"/></method>'
    '<method name="GetAll"><arg type="s" direction="in" name="interface_name"/>'
    '<arg type="a{sv}" direction="out" name="properties"/></method>'
    '<method name="Set"><arg type="s" direction="in" name="interface_name"/>'
    '<arg type="s" direction="in" name="property_name"/>'
    '<arg type="v" direction="in" name="value"/></method>'
    '</interface>'
    '</node>'
)


class StatusNotifierItem:
    def __init__(self, conn):
        self.conn = conn
        self.registered = False
        self.menu_items = []            # [(id, label, callback)]

    # ---- публичное управление -------------------------------------------

    def set_menu(self, items):
        """items: [(id, label, callback)], label == '---' — разделитель."""
        self.menu_items = list(items)

    def start(self):
        if not self._has_watcher():
            print('[tray] индикатор в трее недоступен (нет StatusNotifierWatcher)')
            return False
        self._export_sni()
        self._export_menu()
        self._export_properties(SNI_PATH)
        self._export_properties(MENU_PATH)
        self._own_name()
        self._register()
        self.registered = True
        print('[tray] индикатор зарегистрирован')
        return True

    def stop(self):
        if not self.registered:
            return
        try:
            self.conn.call_sync(WATCHER_NAME, '/StatusNotifierWatcher',
                                'org.kde.StatusNotifierWatcher',
                                'UnregisterStatusNotifierItem',
                                GLib.Variant('(s)', (self._service_name(),)),
                                None, Gio.DBusCallFlags.NONE, 3000, None)
        except GLib.Error:
            pass
        self.registered = False

    def _service_name(self):
        return f'org.kde.StatusNotifierItem-{os.getpid()}-1'

    # ---- внутреннее ------------------------------------------------------

    def _has_watcher(self):
        try:
            ok = self.conn.call_sync(
                'org.freedesktop.DBus', '/org/freedesktop/DBus',
                'org.freedesktop.DBus', 'NameHasOwner',
                GLib.Variant('(s)', (WATCHER_NAME,)), None,
                Gio.DBusCallFlags.NONE, 3000, None).unpack()[0]
            return bool(ok)
        except GLib.Error:
            return False

    def _own_name(self):
        try:
            reply = self.conn.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                                        'org.freedesktop.DBus', 'RequestName',
                                        GLib.Variant('(su)', (self._service_name(), 4)),
                                        None, Gio.DBusCallFlags.NONE, 3000, None)
            print(f'[tray] RequestName {self._service_name()}: code={reply.unpack()[0]}')
        except GLib.Error as exc:
            print('[tray] RequestName:', exc)

    def _register(self):
        try:
            self.conn.call_sync(WATCHER_NAME, '/StatusNotifierWatcher',
                                'org.kde.StatusNotifierWatcher',
                                'RegisterStatusNotifierItem',
                                GLib.Variant('(s)', (SNI_PATH,)),
                                None, Gio.DBusCallFlags.NONE, 3000, None)
        except GLib.Error as exc:
            print('[tray] RegisterStatusNotifierItem:', exc)

    def _export_sni(self):
        node = Gio.DBusNodeInfo.new_for_xml(SNI_XML)
        self.conn.register_object_with_closures2(
            SNI_PATH, node.interfaces[0], self._on_sni_call, None, None)

    def _export_menu(self):
        node = Gio.DBusNodeInfo.new_for_xml(MENU_XML)
        self.conn.register_object_with_closures2(
            MENU_PATH, node.interfaces[0], self._on_menu_call, None, None)

    def _export_properties(self, path):
        node = Gio.DBusNodeInfo.new_for_xml(PROPS_XML)
        self.conn.register_object_with_closures2(
            path, node.interfaces[0], self._on_props_call, None, None)
        # props_fn возвращает словарь свойств интерфейса SNI/menu

    def _on_props_call(self, connection, sender, object_path, iface_name,
                       method_name, parameters, invocation):
        props = (self._sni_props if object_path == SNI_PATH else self._menu_props)()
        if method_name == 'Get':
            intf, prop = parameters.unpack()
            value = props.get(prop)
            if value is None:
                invocation.return_dbus_error(
                    'org.freedesktop.DBus.Error.InvalidArgs',
                    f'Нет свойства {prop} в {intf}')
            else:
                invocation.return_value(
                    GLib.Variant.new_tuple(GLib.Variant.new_variant(value)))
        elif method_name == 'GetAll':
            # Значения уже являются GVariant. Дополнительная обёртка ``v``
            # превращала их в ``variant of variant`` (<<'IconName'>>), который
            # GNOME AppIndicator не распознаёт как строковое свойство SNI.
            invocation.return_value(GLib.Variant('(a{sv})', (list(props.items()),)))
        elif method_name == 'Set':
            invocation.return_dbus_error('org.freedesktop.DBus.Error.NotSupported',
                                         'Свойства только для чтения')

    def _sni_props(self):
        return {
            'Category': GLib.Variant('s', 'ApplicationStatus'),
            'Id': GLib.Variant('s', 'tacklet'),
            'Title': GLib.Variant('s', 'Tacklet'),
            'Status': GLib.Variant('s', 'Active'),
            'IconName': GLib.Variant('s', ICON_NAME),
            'Menu': GLib.Variant('o', MENU_PATH),
        }

    def _menu_props(self):
        return {
            'version': GLib.Variant('i', 3),
            'text': GLib.Variant('s', 'Tacklet'),
            'icon-name': GLib.Variant('s', ICON_NAME),
            'enabled': GLib.Variant('b', True),
            'visible': GLib.Variant('b', True),
            'children-display': GLib.Variant('s', 'submenu'),
        }

    def _on_sni_call(self, connection, sender, object_path, iface_name,
                     method_name, parameters, invocation):
        if method_name in ('Activate', 'SecondaryActivate'):
            if self.menu_items:
                first_cb = self.menu_items[0][2] if self.menu_items else None
                if first_cb:
                    first_cb()
        invocation.return_value(None)

    def _layout(self):
        children = []
        for item_id, label, callback in self.menu_items:
            if label == '---':
                props = {'type': GLib.Variant('s', 'separator')}
            else:
                props = {
                    'label': GLib.Variant('s', label),
                    'enabled': GLib.Variant('b', True),
                    'visible': GLib.Variant('b', True),
                }
            children.append(GLib.Variant('(ia{sv}av)', (item_id, props, [])))
        root_props = self._menu_props()
        root = GLib.Variant('(ia{sv}av)', (0, root_props, children))
        return GLib.Variant.new_tuple(GLib.Variant('u', 1), root)

    def _on_menu_call(self, connection, sender, object_path, iface_name,
                      method_name, parameters, invocation):
        if method_name == 'GetLayout':
            invocation.return_value(self._layout())
        elif method_name == 'GetProperty':
            item_id, name = parameters.unpack()
            value = None
            for mid, label, callback in self.menu_items:
                if mid == item_id:
                    if name in ('label', 'text') and label != '---':
                        value = GLib.Variant('s', label)
                    elif name == 'type':
                        value = GLib.Variant('s', 'separator' if label == '---' else 'standard')
                    elif name == 'enabled':
                        value = GLib.Variant('b', True)
                    elif name == 'visible':
                        value = GLib.Variant('b', True)
                    break
            if value is None:
                invocation.return_dbus_error('org.freedesktop.DBus.Error.InvalidArgs',
                                             f'Нет свойства {name}')
            else:
                invocation.return_value(
                    GLib.Variant.new_tuple(GLib.Variant.new_variant(value)))
        elif method_name == 'Event':
            item_id, event_id, data, timestamp = parameters.unpack()
            if event_id == 'clicked':
                for mid, label, callback in self.menu_items:
                    if mid == item_id and callback:
                        callback()
            invocation.return_value(None)
