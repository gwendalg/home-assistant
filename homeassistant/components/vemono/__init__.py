"""
Connect to a VeMono device via pyvemono API.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.vemono/
"""
import logging
import requests
from datetime import timedelta
import urllib.request, urllib.error
import voluptuous as vol
import xmltodict

import homeassistant.bootstrap as bootstrap
from homeassistant.const import CONF_HOST
from homeassistant.helpers import discovery
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

DOMAIN = 'vemono'
DEPENDENCIES = []

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)

DEVICES = None

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): vol.Schema([cv.string])
    }),
}, extra=vol.ALLOW_EXTRA)

class VeMonoStripErr(Exception):
    pass

def setup(hass, config):  # pylint: disable=too-many-locals
    """Setup the VeMono component."""
    # Setup all devices from config
    global DEVICES
    DEVICES = {}

    for device in config.get(DOMAIN, {}).get(CONF_HOST):
        DEVICES[device] = VeMonoWrapper(device)

    for component in 'sensor', 'switch':
        discovery.load_platform(hass, component, DOMAIN, None, config)

    return True


class VeMonoWrapper(object):
    """Gateway wrapper class."""

    # pylint: disable=too-few-public-methods
    def __init__(self, host):
        """Setup class attributes on instantiation.

        Args:
        host (str): Address to log to.

        Attributes:
        _wrapped_device (vemono.SerialGateway): Wrapped device.
        version (str): Version of vemono API.
        platform_callbacks (list): Callback functions, one per platform.
        optimistic (bool): Send values to actuators without feedback state.
        __initialised (bool): True if VeMonoWrapper is initialised.
        """
        self.url_base="http://%s" % (host)
        self.update()
        sockets = self.doc["strip"]["status"]["socket"]
        if type(sockets) is list:
            self.max_plug = len(sockets)
        else:
            self.max_plug = 1

        self.base_name = self.doc["strip"]["identity"]["name"]

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        url = self.url_base + "/status.xml"
        try:
          request = urllib.request.urlopen(url, timeout=10)
        except urllib.error.URLError as e:
          raise VeMonoStripErr("Unable to access %s: %s" % (url, e))
        self.doc = xmltodict.parse(request.read())

    def socket(self, plug):
        """ Return socket dictionary for a given plug."""
        if self.max_plug == 1:
            return self.doc["strip"]["status"]["socket"]
        else:
            return self.doc["strip"]["status"]["socket"][plug]



class VeMonoDeviceEntity(Entity):
    """Represent a VeMono entity."""

    def __init__(self, device, plug):
        """
        Setup class attributes on instantiation.

        Args:
        device (VeMonoWrapper): Gateway object.
        plug: id of the plug.
        """
        self.device = device
        self.plug = plug

    @property
    def name(self):
        """The name of this entity."""
        if self.device.max_plug == 1:
            return self.device.base_name
        else:
            return '%s %d' % (self.device.base_name, self.plug)

    def update(self):
        self.device.update()

    def state_data(self, field):
        return self.device.socket(self.plug)[field]

    def set_state(self, value):
        url = "%s/%d/set.xml?value=%s" % (
                self.device.url_base,
                self.plug, value)
        try:
            urllib.request.urlopen(url,timeout=2)
        except urllib.error.URLError as e:
          raise VeMonoStripErr("Unable to access %s: %s" % (url, e))
