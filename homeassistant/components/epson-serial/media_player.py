"""
Support for Epson Projectors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.epson/
"""
import io
import logging
import serial
import time
import re

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_SELECT_SOURCE)
from homeassistant.const import (CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'epson'

SUPPORT_EPSON = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

# Need to be configured.
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default='Epson'): cv.string,
    vol.Required(CONF_PORT): cv.isdevice,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Epson platform."""

    epson = EpsonEntity(
        config.get(CONF_NAME),
        config.get(CONF_PORT)
    )
    add_entities([epson])
    return True


class EpsonEntity(MediaPlayerEntity):
    """Representation of a Epson device."""

    # pylint: disable=too-many-public-methods, abstract-method
    def __init__(self, name, port):
        """Initialize the Epson device."""
        self._name = name
        self._port = port
        self._pwstate = STATE_OFF
        self._current_source = None
        self._source_list = {'1F' : 'COMPONENT',
                             '21' : 'RGB',
                             '30' : 'HDMI1',
                             '42' : 'SVIDEO',
                             'A0' : 'HDMI2'}
        try:
            ser = serial.serial_for_url(self._port,
                                        baudrate=9600,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        xonxoff=False,
                                        timeout=3,
                                        writeTimeout=1)
        except serial.SerialException as e:
            _LOGGER.error('Unable to open serial port %s to %s: %s' % (port, name, e))
            raise e
        self._ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser),
                                        line_buffering=True,
                                        newline='\r')

    def serial_command(self, command):
        cmd = "{}\r".format(command)
        _LOGGER.info('command:---%s---' % bytes(cmd, 'utf8'))
        self._ser_io.write(cmd)
        timeout = 5
        response_buffer = b''
        while response_buffer == b'' and timeout > 0:
            try:
                response_buffer = self._ser_io.readline()
            except serial.SerialException:
                time.sleep(1)
                pass
            else:
                _LOGGER.info('buffer:---%s---' % bytes(response_buffer, 'utf8'))
            timeout -= 1
        return response_buffer

    def update(self):
        """Get the latest details from the device."""
        raw_power = self.serial_command("PWR?").strip('\r')
        if raw_power == '':
            # We don't have anything on the line, don't change anything.
            return

        m = re.match(r".*PWR=(?P<power>\d{2}).*", raw_power, re.DOTALL)
        if not m:
            _LOGGER.info("Not match for %s" % (raw_power))
            return
        else:
            power = int(m.group('power'), 16)
            if power in [1, 2]:
                self._pwstate = STATE_ON
            if power in [0, 3, 4]:
                self._pwstate = STATE_OFF
        if self._pwstate == STATE_OFF:
            return

        raw_source = self.serial_command("SOURCE?").strip('\r')
        m = re.match(r".*SOURCE=(?P<source>\w{2}).*", raw_source, re.DOTALL)
        if not m:
            _LOGGER.info("Not match for %s" % (raw_source))
        else:
            self._current_source = m.group('source')
        return

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._pwstate

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        return SUPPORT_EPSON

    @property
    def source(self):
        """"Return the current input source of the device."""
        return self._source_list[self._current_source]

    @property
    def source_list(self):
        """List of available input sources."""
        return list(self._source_list.values())

    def select_source(self, source):
        """Set the input source."""
        self.serial_command('SOURCE ' + list(self._source_list.keys())[list(self._source_list.values()).index(source)])

    def turn_off(self):
        """Turn off media player."""
        self.serial_command("PWR OFF")

    def turn_on(self):
        """Turn the media player on."""
        self.serial_command("PWR ON")
