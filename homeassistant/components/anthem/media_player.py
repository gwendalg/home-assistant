"""
Support for Anthem Network Receivers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.anthem/
"""
import io
import logging
import serial
import re

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET,
    SUPPORT_SELECT_SOURCE)
from homeassistant.const import (CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'anthem'

SUPPORT_ANTHEM = (
    SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
)

# Need to be configured.
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default='Anthem'): cv.string,
        vol.Required(CONF_PORT): cv.isdevice,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Anthem platform."""

    anthem = AnthemEntity(
        config.get(CONF_NAME),
        config.get(CONF_PORT)
    )
    add_entities([anthem])
    return True


class AnthemEntity(MediaPlayerEntity):
    """Representation of a Anthem device."""

    # pylint: disable=too-many-public-methods, abstract-method
    def __init__(self, name, port):
        """Initialize the Anthem device."""
        self._name = name
        self._port = port
        self._pwstate = STATE_OFF
        self._volume = 0
        self._muted = False
        self._current_source = None
        self._source_list = {'1': 'BDP',
                             '2': 'CD',
                             '3': 'TV',
                             '4': 'SAT',
                             '5': 'GAME',
                             '6': 'AUX'}
        try:
            ser = serial.serial_for_url(self._port,
                                        baudrate=115200,
                                        xonxoff=True,
                                        timeout=2,
                                        writeTimeout=1)
        except serial.SerialException as e:
            _LOGGER.error('Unable to open serial port %s to %s: %s' % (port, name, e))
            raise e
        self._ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser),
                                        line_buffering=True,
                                        newline='\n')

    def serial_single_command(self, command):
        cmd = '{};'.format(command)
        _LOGGER.info('command:---%s---' % (cmd))
        self._ser_io.write(cmd)
        self._ser_io.flush()
        timeout = 2
        response_buffer = b''
        while response_buffer == b'' and timeout > 0:
            response_buffer = self._ser_io.readline()
            _LOGGER.info('buffer:---%s---' % (bytes(response_buffer, 'utf8')))
            timeout -= 1
        return response_buffer

    def serial_command(self, command):
        # To be sure the MCU is awake.
        if self._pwstate == STATE_OFF:
            self.serial_single_command('P1P?')
        return self.serial_single_command(command)

    def update(self):
        """Get the latest details from the device."""
        raw_power = self.serial_command('P1P?').strip()
        if raw_power == '':
            # We don't have anything on the line, don't change anything.
            return

        m = re.match(r'.*P1P(?P<power>\d{1}).*', raw_power, re.DOTALL)
        if not m:
            _LOGGER.info('Not match for %s' % (raw_power))
            return
        else:
            power = int(m.group('power'))
            if power == 1:
                self._pwstate = STATE_ON
            if power == 0:
                self._pwstate = STATE_OFF
        if self._pwstate == STATE_OFF:
            return
        raw_state = self.serial_command('P1?').strip()
        if raw_state.find('Main Off') != -1:
            # The AVR is switching off, no need to wait for confirmation.
            self._pwstate = STATE_OFF
            return

        m = re.match(r'.*P1S(?P<source>\d{1})V(?P<volume>-*\d{2})M(?P<mute>\d{1}).*',
                     raw_state, re.DOTALL)
        if m:
            # -60dB is 0%
            self._volume = (60 + int(m.group('volume'))) / 60
            self._muted = (m.group('mute') == '1')
            self._current_source = m.group('source')
        else:
            _LOGGER.info('Not match for status: %s' % (raw_state))

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
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        return SUPPORT_ANTHEM

    @property
    def source(self):
        """Return the current input source of the device."""
        return self._source_list[self._current_source]

    @property
    def source_list(self):
        """List of available input sources."""
        return list(self._source_list.values())

    def turn_off(self):
        """Turn off media player."""
        self.serial_command('P1P0')

    def turn_on(self):
        """Turn the media player on."""
        self.serial_command('P1P1')

    def volume_up(self):
        """Volume up media player."""
        self.serial_command('P1VU')

    def volume_down(self):
        """Volume down media player."""
        self.serial_command('P1VD')

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        # 60dB max
        self.serial_command('P1V' + str(round(volume * 60) - 60).zfill(2))

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self.serial_command('P1M' + str(1 if mute else 0))

    def select_source(self, source):
        """Set the input source."""
        self.serial_command('P1S' + list(self._source_list.keys())[list(self._source_list.values()).index(source)])
