#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import json
import os
from pathlib import Path



mainloop = None

BLUEZ_SERVICE_NAME      = 'org.bluez'
LE_ADVERTISING_MANAGER  = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE      = 'org.bluez.GattManager1'
DBUS_OM_IFACE           = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE         = 'org.freedesktop.DBus.Properties'
GATT_SERVICE_IFACE      = 'org.bluez.GattService1'
GATT_CHRC_IFACE         = 'org.bluez.GattCharacteristic1'
LE_ADVERTISING_IFACE    = 'org.bluez.LEAdvertisement1'


SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
CHAR_UUID    = '12345678-1234-5678-1234-56789abcdef1'



BUFFER_DIR = Path("/home/francesco/toSendData/buffer")
BUFFER_DIR.mkdir(parents=True, exist_ok=True)




class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'
class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'
class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'
class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'
class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'

# -- Advertisement object --

class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'
    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISING_IFACE:
            raise InvalidArgsException()
        return {
            'Type': 'peripheral',
            'ServiceUUIDs': dbus.Array([SERVICE_UUID], signature='s'),
            'LocalName': dbus.String('PyGATTServer'),
            'Includes': dbus.Array(['tx-power'], signature='s')
        }

    @dbus.service.method(LE_ADVERTISING_IFACE, in_signature='', out_signature='')
    def Release(self):
        print('Advertisement released')

def register_ad_cb():
    print('Advertisement registered')
def register_ad_error_cb(error):
    print('Failed to register advertisement:', error)
    mainloop.quit()

# -- GATT Application --

class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        super().__init__(bus, self.path)
        self.add_service(TestService(bus, 0))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        print('GetManagedObjects called')
        response = {}
        for svc in self.services:
            response[svc.get_path()] = svc.get_properties()
            for ch in svc.get_characteristics():
                response[ch.get_path()] = ch.get_properties()
        return response

class Service(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'
    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    [ch.get_path() for ch in self.characteristics],
                    signature='o')
            }
        }

    def add_characteristic(self, chrc):
        self.characteristics.append(chrc)
    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_SERVICE_IFACE]

class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': dbus.Array(self.flags, signature='s')
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

# -- Your Test Service & Characteristic --

class TestService(Service):
    def __init__(self, bus, index):
        super().__init__(bus, index, SERVICE_UUID, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))


class TestCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, CHAR_UUID,
                         ['write', 'write-without-response'],
                         service)
        self._recv_buffer = bytearray()
        self.batch = []           # accumulo qui i singoli snapshot
        self.batch_id = 0

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        # stesse righe di buffering/parsing
        self._recv_buffer.extend(bytes(value))
        try:
            text = self._recv_buffer.decode('utf-8')
            snapshot = json.loads(text)
        except Exception:
            return
        self._recv_buffer.clear()

        # aggiungo alla batch
        self.batch.append(snapshot)

        # se ho 400 campioni, li salvo tutti insieme e resetto
        if len(self.batch) >= 400:
            final = { 'samples': self.batch }       # rimuovi batchId a monte
            filename = BUFFER_DIR / f'segment{self.batch_id}_raw.json'
            with open(filename, 'w') as f:
                json.dump(final, f, indent=2)
            print(f'Batch {self.batch_id} salvato in {filename}')
            # reset
            self.batch.clear()
            self.batch_id += 1
# -- Helpers --

def register_app_cb():
    print('GATT application registered')
def register_app_error_cb(error):
    print(f'Failed to register application: {error}')
    mainloop.quit()

def find_adapter(bus):
    om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                        DBUS_OM_IFACE)
    objs = om.GetManagedObjects()
    for path, props in objs.items():
        if GATT_MANAGER_IFACE in props and LE_ADVERTISING_MANAGER in props:
            return path
    return None

# -- Main --

def main():
    global mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print('GattManager1 or LEAdvertisingManager1 not found')
        return

    # 1) register advertisement
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        LE_ADVERTISING_MANAGER)
    ad = Advertisement(bus, 0)
    ad_manager.RegisterAdvertisement(
        ad.get_path(), {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb)

    # 2) register GATT application
    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        GATT_MANAGER_IFACE)
    app = Application(bus)
    mainloop = GLib.MainLoop()

    print('Registering GATT application…')
    service_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb)

    mainloop.run()

if __name__ == '__main__':
    main()
