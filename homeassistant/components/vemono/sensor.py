"""
Support for VeMono sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.vemono/
"""
import logging

from homeassistant.components import vemono
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the vemono platform for sensors."""
    if not vemono.DEVICES:
        return
    devs = []
    for host in vemono.DEVICES:
        device = vemono.DEVICES[host]
        for plug in range(device.max_plug):
            devs.append(VeMonoSensor(device, plug))

    add_entities(devs)


class VeMonoSensor(vemono.VeMonoDeviceEntity, Entity):
    """Represent the value of a VeMono Sensor child node."""

    @property
    def state(self):
        """Return the state of the device."""
        return self.state_data("watts")

    @property
    def unit_of_measurement(self):
        return 'W'
