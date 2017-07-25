#!/usr/bin/env python

import os
import time
import json
import logging
import asyncio
import datetime

import yaml

from bluepy import btle
from hbmqtt.client import (MQTTClient, ConnectException)

_LOGGER = logging.getLogger(__name__)

SCAN_TIME = 3
MAX_MISSING = 3
ARMA_CONSTANT = 0.25
STARTUP_READINGS = 4
SLEEP_TIME = 30
NO_RECEPTION_RSSI = -200
DISCOVERY_PREFIX = 'homeassistant'

MQTT_CONFIG = {
    'keep_alive': 10,
    'ping_delay': 1,
}


class _Device:
    def __init__(self):
        self.rssi = 0
        self.missing = NO_RECEPTION_RSSI
        self.readings = 0

class DeviceScanner:

    def __init__(self, user, password, host, hci=0,
                 prefix=DISCOVERY_PREFIX, loop=None):
        self.user = user
        self.password = password
        self.host = host
        self.scanner = btle.Scanner(hci)
        self.loop = loop or asyncio.get_event_loop()
        self.mqtt = MQTTClient(config=MQTT_CONFIG)
        self._prefix = prefix
        self._results = {}

    @asyncio.coroutine
    def start(self):
        yield from self.mqtt.connect('mqtt://{0}:{1}@{2}/'.format(
            self.user, self.password, self.host))

    @asyncio.coroutine
    def scan_and_print(self):
        # Look for devices
        devices = yield from self.loop.run_in_executor(
            None, self.scanner.scan, SCAN_TIME)

        # Increase "missing" counter to find unavailable devices
        for dev in self._results.values():
            dev.missing += 1

        # Handle found devices (decrease missing counter)
        for device in devices:
            yield from self._handle_scan_result(device)

        # "Remove" missing devices
        for addr, dev in self._results.items():
            if dev.missing == MAX_MISSING:
                _LOGGER.debug('Device %s no longer available', addr)
                dev.rssi = NO_RECEPTION_RSSI
                yield from self._publish(addr, 'state', int(dev.rssi))

    @asyncio.coroutine
    def _handle_scan_result(self, device):
        is_new_device = False
        if device.addr not in self._results:
            is_new_device = True
            self._results[device.addr] = _Device()

        dev = self._results[device.addr]
        dev.missing = 0

        if dev.rssi == NO_RECEPTION_RSSI:
            dev.readings = 0
        else:
            dev.readings += 1

        # Simple ARMA filter for smoother readings
        dev.rssi = dev.rssi - ARMA_CONSTANT * (dev.rssi - device.rssi)

        _LOGGER.debug('[%s] Addr: %s, RSSI: %s',
                      datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      device.addr, dev.rssi)

        if dev.readings < STARTUP_READINGS:
            _LOGGER.info('Device %s still in startup phase', device.addr)

        try:
            yield from self._update_mqtt(
                device.addr.replace(':', ''), dev.rssi, is_new_device)
        except Exception as ex:
            _LOGGER.exception('Failed to update MQTT')

    @asyncio.coroutine
    def _update_mqtt(self, addr, rssi, is_new_device):
        if self.mqtt.reconnect():
            if is_new_device:
                payload = {'name': addr, 'unit_of_measurement': 'dBm'}
                yield from self._publish(
                    addr, 'config', json.dumps(payload), retain=True)
            else:
                yield from self._publish(addr, 'state', int(rssi))
        else:
            _LOGGER.warning('Failed to connect')

    @asyncio.coroutine
    def _publish(self, addr, topic, value, retain=False):
        path = '{0}/sensor/{1}/{2}'.format(self._prefix, addr, topic)
        yield from self.mqtt.publish(
            path, str(value).encode('utf-8'), retain=retain)


@asyncio.coroutine
def run_loop(scanner, loop):
    # Try to re-connect for a long, long time...
    while True:
        try:
            _LOGGER.info('Connecting...')
            yield from scanner.start()
            break
        except Exception:
            _LOGGER.exception('Failed to connect')
            yield from asyncio.sleep(10)  # Wait some time until reconnect


    _LOGGER.info('Connected!')
    while True:
        try:
            yield from scanner.scan_and_print()
            yield from asyncio.sleep(SLEEP_TIME, loop=loop)
        except Exception:
            _LOGGER.exception('Got exception while starting')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    settings = None
    with open(os.path.expanduser('~/.homeassistant/secrets.yaml'), 'r') as fh:
        settings = yaml.load(fh)

    loop = asyncio.get_event_loop()
    scanner = DeviceScanner(
        settings['mqtt_user'],
        settings['mqtt_password'],
        '{0}:{1}'.format(settings['mqtt_host'], settings['mqtt_port']),
        prefix=settings['mqtt_prefix'],
        loop=loop)
    loop.run_until_complete(run_loop(scanner, loop))
